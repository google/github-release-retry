#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright 2020 The github-release-retry Project Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Creates a GitHub release and uploads files."""

import argparse
import base64
import json
import os
import sys
import time
import typing
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

if typing.TYPE_CHECKING:
    from dataclasses_json.api import DataClassJsonMixin
else:
    from dataclasses_json import DataClassJsonMixin


def remove_none_fields(dic: Any) -> Any:
    return {k: v for k, v in dic.items() if v is not None}


def to_dict(obj: DataClassJsonMixin) -> Any:  # pylint: disable=used-before-assignment;
    return remove_none_fields(obj.to_dict())


def log(message: str) -> None:
    print(message)  # noqa: T001


@dataclass
class GithubResourceError(DataClassJsonMixin):
    resource: Optional[str] = None
    field: Optional[str] = None
    code: Optional[str] = None


@dataclass
class GithubClientError(DataClassJsonMixin):
    message: Optional[str] = None
    errors: Optional[List[GithubResourceError]] = None


@dataclass
class Asset(DataClassJsonMixin):
    url: Optional[str] = None
    browser_download_url: Optional[str] = None
    id: Optional[str] = None  # noqa: VNE003
    name: Optional[str] = None
    label: Optional[str] = None
    state: Optional[str] = None
    content_type: Optional[str] = None
    size: Optional[int] = None


@dataclass
class Release(DataClassJsonMixin):
    upload_url: Optional[str] = None
    id: Optional[str] = None  # noqa: VNE003
    tag_name: Optional[str] = None
    target_commitish: Optional[str] = None
    name: Optional[str] = None
    body: Optional[str] = None
    draft: Optional[bool] = None
    prerelease: Optional[bool] = None
    assets: Optional[List[Asset]] = None


@dataclass
class GithubApi(DataClassJsonMixin):
    github_api_url: str
    user: str
    repo: str
    token: str
    retry_limit: int

    def _headers_v3(self) -> Dict[str, str]:
        return {
            "Accept": "application/vnd.github.v3.text-match+json",
            "Authorization": f"token {self.token}",
            "User-Agent": f"{self.user} {self.repo}",
        }

    def _headers_v4(self) -> Dict[str, str]:
        return {
            "Authorization": f"bearer {self.token}",
            "User-Agent": f"{self.user} {self.repo}",
        }

    @staticmethod
    def _wait() -> None:
        # Don't make too many requests per second.
        # We are unlikely to hit official rate limits, BUT repeated polling can look like abuse.
        # TODO: revisit this if needed.
        time.sleep(1)

    def create_release(self, release: Release) -> requests.Response:
        self._wait()
        return requests.post(
            url=f"{self.github_api_url}/repos/{self.user}/{self.repo}/releases",
            json=to_dict(release),
            headers=self._headers_v3(),
        )

    def get_release_by_tag(self, tag_name: str) -> requests.Response:
        self._wait()
        return requests.get(
            url=f"{self.github_api_url}/repos/{self.user}/{self.repo}/releases/tags/{tag_name}",
            headers=self._headers_v3(),
        )

    def get_asset_by_id(self, asset_id: str) -> requests.Response:
        self._wait()
        return requests.get(
            url=f"{self.github_api_url}/repos/{self.user}/{self.repo}/releases/assets/{asset_id}",
            headers=self._headers_v3(),
        )

    def delete_asset(self, asset_id: str) -> requests.Response:
        self._wait()
        return requests.delete(
            url=f"{self.github_api_url}/repos/{self.user}/{self.repo}/releases/assets/{asset_id}",
            headers={**self._headers_v3(), "Content-type": "application/json"},
        )

    def upload_asset(self, file_path: Path, release: Release) -> requests.Response:

        if not release.upload_url:
            raise AssertionError("Need release object with upload_url.")

        # Upload URL looks like:
        #  https://uploads.github.com/repos/octocat/Hello-World/releases/1/assets{?name,label}
        # We want the part before {.
        upload_url = release.upload_url.split("{")[0]
        # Then we add the name.
        upload_url = f"{upload_url}?name={file_path.name}"

        self._wait()
        with file_path.open(mode="rb") as f:
            return requests.post(
                url=upload_url,
                headers={
                    **self._headers_v3(),
                    "Content-Type": "application/octet-stream",
                },
                data=f,
            )

    def graphql_query(self, query: str) -> requests.Response:
        self._wait()
        return requests.post(
            f"{self.github_api_url}/graphql",
            headers=self._headers_v4(),
            json={"query": query},
        )

    def find_asset_id_by_file_name(
        self, file_name: str, release: Release
    ) -> Optional[str]:
        """
        Returns the asset id.

        :returns the asset id or 0 if the asset was not found.
        """
        # We get the asset id via GitHub's v4 GraphQL API, as this seems to be more reliable.
        # But most other operations still require using the REST v3 API.

        log(f"Finding asset id of {file_name}.")

        query = f"""
query {{
  repository(owner:"{self.user}", name:"{self.repo}") {{
    release(tagName:"{release.tag_name}") {{
      releaseAssets(first: 1, name:"{file_name}") {{
        nodes {{
          id
        }}
      }}
    }}
  }}
}}
"""
        response = self.graphql_query(query)

        # Even on errors, the response should be "OK".
        if response.status_code != requests.codes.ok:
            raise UnexpectedResponseError(response)

        try:
            response_json = json.loads(response.content)
        except json.JSONDecodeError:
            raise UnexpectedResponseError(response)

        # The response should look a bit like this:
        # {
        #   "data": {
        #     "repository": {
        #       "release": {
        #         "releaseAssets": {
        #           "nodes": [
        #             {
        #               "id": "MDEyOlJlbGVhc2VBc3NldDE4MzgxNTc3"  # noqa: SC100
        #             }
        #           ]
        #         }
        #       }
        #     }
        #   }
        # }

        try:
            assets = response_json["data"]["repository"]["release"]["releaseAssets"][
                "nodes"
            ]
        except KeyError:
            raise UnexpectedResponseError(response)

        if not assets:
            # Asset not found.
            return None

        try:
            node_id = assets[0]["id"]
        except KeyError:
            raise UnexpectedResponseError(response)

        # The id we get from the GraphQL API is called the "node_id" in the REST API v3.
        # We can get back to the REST id by decoding the node_id (it is base64 encoded)
        # and extracting the number at the end.
        # Once decoded, the node_id is similar to "012:ReleaseAsset18381577".  # noqa: SC100
        # The id part is 18381577.

        node_id_decoded: str = base64.b64decode(node_id).decode(
            encoding="utf-8", errors="ignore"
        )

        asset_id = node_id_decoded.split("ReleaseAsset")[1]

        return asset_id


class MissingTokenError(Exception):
    pass


class MissingFilesError(Exception):
    def __init__(self, missing_paths: List[Path]):
        self.missing_paths = missing_paths
        missing_paths_str = [str(p) for p in missing_paths]
        missing_paths_joined = "\n" + "\n".join(missing_paths_str) + "\n"
        super().__init__(f"Missing: {missing_paths_joined}")


class UnexpectedResponseError(Exception):
    def __init__(self, response: requests.Response):
        self.response = response
        super().__init__(f"Unexpected response: {response.__dict__}")


class HitRetryLimitError(Exception):
    pass


def upload_file(
    g: GithubApi, release: Release, file_path: Path  # noqa: VNE001
) -> None:

    log(f"\nUpload: {file_path.name}")

    file_size = file_path.stat().st_size

    retry_count = 0
    wait_time = 2

    # Only exit the loop if we manage to verify that the asset has the expected size and state, or if we hit the retry limit.
    while True:

        existing_asset_id = g.find_asset_id_by_file_name(file_path.name, release)
        if existing_asset_id:
            log("Asset exists.")
            log("Getting asset info.")
            response = g.get_asset_by_id(existing_asset_id)
            if response.status_code != requests.codes.ok:
                raise UnexpectedResponseError(response)

            log("Decoding asset info.")
            try:
                existing_asset = Asset.from_json(response.content)
            except json.JSONDecodeError:
                raise UnexpectedResponseError(response)

            if existing_asset.size == file_size and existing_asset.state == "uploaded":
                log("The asset has the correct size and state. Asset done.\n")
                return

            log('The asset looks bad (wrong size or state was not "uploaded").')

            log("Deleting asset.")

            response = g.delete_asset(existing_asset_id)
            if response.status_code != requests.codes.no_content:
                log(f"Ignoring failed deletion: {response}")
        else:
            log("Asset does not exist.")

        # Asset does not exist or has now been deleted.

        if retry_count >= g.retry_limit:
            raise HitRetryLimitError("Hit upload retry limit.")

        if retry_count > 0:
            log(f"Waiting {wait_time} seconds before retrying upload.")
            time.sleep(wait_time)

        retry_count += 1
        wait_time = wait_time * 2

        log("Uploading asset.")
        try:
            response = g.upload_asset(file_path, release)
            if response.status_code != requests.codes.created:
                log(f"Ignoring failed upload: {response}")
        except Exception as ex:  # pylint: disable=broad-except;
            log(f"Ignoring upload exception: {ex}")

        # And now we loop.


def make_release(
    g: GithubApi, release: Release, file_paths: List[Path]  # noqa: VNE001
) -> None:

    # Some basic sanity checks.
    missing_files = list(filter(lambda p: not p.is_file(), file_paths))
    if missing_files:
        raise MissingFilesError(missing_files)

    if not release.tag_name:
        raise AssertionError("tag_name must be provided")

    log("Creating the release.")
    response = g.create_release(release)
    if response.status_code != requests.codes.created:
        log(f"Failed...")
        # Try to decode the error.
        try:
            error: GithubClientError = GithubClientError.from_json(response.content)
        except json.JSONDecodeError:
            raise UnexpectedResponseError(response)

        if not error.errors:
            raise UnexpectedResponseError(response)

        if (
            error.errors[0].resource != "Release"
            or error.errors[0].code != "already_exists"
        ):
            raise UnexpectedResponseError(response)

        log("...but this is OK, because the release already exists.")
        log("Getting the current release.")
        response = g.get_release_by_tag(release.tag_name)
        if response.status_code != requests.codes.ok:
            raise UnexpectedResponseError(response)

    log("Decoding release info.")
    try:
        release = Release.from_json(response.content)
    except json.JSONDecodeError:
        raise UnexpectedResponseError(response)

    for file_path in file_paths:
        upload_file(g, release, file_path)


class ArgumentDefaultsWithRawDescriptionHelpFormatter(
    argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter
):
    pass


def main_with_args(args: List[str]) -> None:
    parser = argparse.ArgumentParser(
        description="""Creates a GitHub release (if it does not already exist) and uploads files to the release.
Please set the GITHUB_TOKEN environment variable.
EXAMPLE:
github-release-retry \\
  --user paul \\
  --repo hello-world \\
  --tag_name v1.0 \\
  --target_commitish 448301eb \\
  --body_string "My first release." \\
  hello-world.zip RELEASE_NOTES.txt
""",
        formatter_class=ArgumentDefaultsWithRawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--user",
        help="Required: The GitHub username or organization name in which the repo resides. ",
        type=str,
        required=True,
    )

    parser.add_argument(
        "--repo",
        help="Required: The GitHub repo name in which to make the release. ",
        type=str,
        required=True,
    )

    parser.add_argument(
        "--tag_name",
        help="Required: The name of the tag to create or use. ",
        type=str,
        required=True,
    )

    parser.add_argument(
        "--target_commitish",
        help="The commit-ish value where the tag will be created. Unused if the tag already exists. ",
        type=str,
        default=None,
    )

    parser.add_argument(
        "--release_name",
        help="The name of the release. Leave unset to use the tag_name (recommended). ",
        type=str,
        default=None,
    )

    # --body_string XOR --body_file
    body_group = parser.add_mutually_exclusive_group(required=True)
    body_group.add_argument(
        "--body_string",
        help="Required (or use --body_file): Text describing the release. Ignored if the release already exists.",
        type=str,
    )
    body_group.add_argument(
        "--body_file",
        help="Required (or use --body_string): Text describing the release, which will be read from BODY_FILE. Ignored if the release already exists.",
        type=str,
    )

    parser.add_argument(
        "--draft",
        help="Creates a draft release, which means it is unpublished. ",
        action="store_true",
    )

    parser.add_argument(
        "--prerelease",
        help="Creates a prerelease release, which means it will be marked as such. ",
        action="store_true",
    )

    parser.add_argument(
        "--github_api_url",
        help="The GitHub API URL without a trailing slash. ",
        type=str,
        default="https://api.github.com",
    )

    parser.add_argument(
        "--retry_limit",
        help="The number of times to retry uploading a file. ",
        type=int,
        default=10,
    )

    parser.add_argument(
        "files",
        metavar="files",
        type=str,
        nargs="*",
        help="The files to upload to the release.",
    )

    parsed_args = parser.parse_args(args)

    token: Optional[str] = os.environ.get("GITHUB_TOKEN", None)

    if not token:
        raise MissingTokenError("Please set the GITHUB_TOKEN environment variable. ")

    g = GithubApi(  # noqa: VNE001
        github_api_url=parsed_args.github_api_url,
        user=parsed_args.user,
        repo=parsed_args.repo,
        token=token,
        retry_limit=parsed_args.retry_limit,
    )

    if parsed_args.body_string:
        body_text = parsed_args.body_string
    else:
        body_text = Path(parsed_args.body_file).read_text(
            encoding="utf-8", errors="ignore"
        )

    release = Release(
        tag_name=parsed_args.tag_name,
        target_commitish=parsed_args.target_commitish or None,
        name=parsed_args.release_name or None,
        body=body_text,
        draft=parsed_args.draft or None,
        prerelease=parsed_args.prerelease or None,
    )

    files_str: List[str] = parsed_args.files
    files = [Path(f) for f in files_str]

    make_release(g, release, files)


def main() -> None:
    main_with_args(sys.argv[1:])


if __name__ == "__main__":
    main()
