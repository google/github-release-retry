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
import traceback
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
    print(message, file=sys.stderr)  # noqa: T001


def log_exception(message: str) -> None:
    log(message)
    traceback.print_exc(file=sys.stderr)
    log("")


def log_response(response: requests.Response) -> None:
    log(f"status_code: {response.status_code}")
    if response.content:
        try:
            content = response.content.decode(encoding="utf-8", errors="ignore")
            log(f"content: {content}")
        except Exception:  # pylint: disable=broad-except;
            log(f"content: {response.content!r}")
    log("")


def release_asset_node_id_to_asset_id(node_id: str) -> str:
    """
    Extracts and returns the asset id from the given Release Asset |node_id|.

    The "id" returned from the GraphQL v4 API is called the "node_id" in the REST API v3.
    We can get back to the REST "id" by decoding the "node_id" (it is base64 encoded)
    and extracting the id number at the end, but this is undocumented and may change.

    :param node_id: The Release Asset node_id.
    :return: The extracted REST API v3 asset id.
    """
    # There is a new format and an old format.

    if node_id.startswith("RA_"):
        # New format: "RA_[base64 encoded bytes]".
        # The last four bytes (big-endian, unsigned) of the base64 encoded bytes are the node id.

        # Strip off the "RA_".
        base64_string = node_id[3:]

        asset_id = str(int.from_bytes(base64.b64decode(base64_string)[-4:], "big"))
    else:
        # Old format: just a base64 encoded string.
        # Once decoded, the format is similar to "012:ReleaseAsset18381577".  # noqa: SC100
        # The asset id part is 18381577.
        node_id_decoded: str = base64.b64decode(node_id).decode(
            encoding="utf-8", errors="ignore"
        )
        if "ReleaseAsset" not in node_id_decoded:
            raise AssertionError(
                f"Unrecognized node_id format: {node_id}. Decoded (base64) string: {node_id_decoded}."
            )

        asset_id = node_id_decoded.split("ReleaseAsset")[1]

    return asset_id


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
    id: Optional[str] = None  # noqa: VNE003, A003
    name: Optional[str] = None
    label: Optional[str] = None
    state: Optional[str] = None
    content_type: Optional[str] = None
    size: Optional[int] = None


@dataclass
class Release(DataClassJsonMixin):
    upload_url: Optional[str] = None
    id: Optional[str] = None  # noqa: VNE003, A003
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
        # We are unlikely to reach official rate limits, BUT repeated polling can look like abuse.
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

        This relies on undocumented behavior; see release_asset_node_id_to_asset_id.

        :returns the asset id or None if the asset was not found.
        """
        if not release.tag_name:
            raise AssertionError("Expected tag_name")

        # We get the asset id via GitHub's v4 GraphQL API, as this seems to be more reliable.
        # But most other operations still require using the REST v3 API.

        log(f"Finding asset id using v4 API of {file_name}.")

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
            node_id: str = assets[0]["id"]
        except KeyError:
            raise UnexpectedResponseError(response)

        return release_asset_node_id_to_asset_id(node_id)

    def verify_asset_size_and_state_via_v3_api(
        self, file_name: str, file_size: int, tag_name: str, release: Optional[Release]
    ) -> bool:
        if not release:
            log("Getting the current release again to check asset status.")
            response = self.get_release_by_tag(tag_name)
            if response.status_code != requests.codes.ok:
                raise UnexpectedResponseError(response)
            log("Decoding release info.")
            try:
                release = Release.from_json(response.content)
            except json.JSONDecodeError:
                raise UnexpectedResponseError(response)

        if release.assets:
            for asset in release.assets:
                if (
                    asset.name == file_name
                    and asset.size == file_size
                    and asset.state == "uploaded"
                ):
                    log("The asset has the correct size and state. Asset done.\n")
                    return True
        return False


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


class ReachedRetryLimitError(Exception):
    pass


def upload_file(  # pylint: disable=too-many-branches,too-many-nested-blocks,too-many-statements;
    g: GithubApi, release: Release, file_path: Path  # noqa: VNE001
) -> None:

    log(f"\nUpload: {file_path.name}")

    file_size = file_path.stat().st_size

    retry_count = 0
    wait_time = 2

    if not release.tag_name:
        raise AssertionError("Expected tag_name")

    # Optimization:
    # The v3 API does not always show assets that are in a bad state, but if the asset *does* exist with the correct
    # size and state, then we can assume the asset was successfully uploaded.
    # We use the existing |release| object, which means we might be able to skip making any further remote API calls.
    try:
        if g.verify_asset_size_and_state_via_v3_api(
            file_name=file_path.name,
            file_size=file_size,
            tag_name=release.tag_name,
            release=release,
        ):
            return
    except Exception:  # pylint: disable=broad-except;
        log_exception(
            "Ignoring exception that occurred when trying to check asset status with the v3 API."
        )

    # Only exit the loop if we manage to verify that the asset has the expected size and state, or if we reach the retry
    # limit.
    while True:
        # We use try-except liberally so that we always at least try to blindly upload the asset (towards the end of the
        # loop), because this may well succeed and then the asset checking code may also be more likely to succeed on
        # subsequent iterations.

        # Optimization:
        # The v3 API does not always show assets that are in a bad state, but if the asset *does* exist with the
        # correct size and state, then we can assume the asset was successfully uploaded, without relying on
        # undocumented behavior.
        # We pass release=None, which forces a fresh fetch of the Release object.
        try:
            if g.verify_asset_size_and_state_via_v3_api(
                file_name=file_path.name,
                file_size=file_size,
                tag_name=release.tag_name,
                release=None,
            ):
                return
        except Exception:  # pylint: disable=broad-except;
            log_exception(
                "Ignoring exception that occurred when trying to check asset status with the v3 API."
            )

        # We now try to get the asset details via the v4 API.
        # This allows us to delete the asset if it is in a bad state, but relies on undocumented behavior.
        try:
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

                if (
                    existing_asset.size == file_size
                    and existing_asset.state == "uploaded"
                ):
                    log("The asset has the correct size and state. Asset done.\n")
                    return

                log('The asset looks bad (wrong size or state was not "uploaded").')

                log("Deleting asset.")

                response = g.delete_asset(existing_asset_id)
                if response.status_code != requests.codes.no_content:
                    log("Ignoring failed deletion.")
                    log_response(response)
            else:
                log("Asset does not exist.")
        except Exception:  # pylint: disable=broad-except;
            log_exception(
                "Ignoring exception that occurred when trying to check asset status with the v4 API."
            )

        # Asset does not exist, has been deleted, or an error occurred.
        # Upload the asset, regardless.

        if retry_count >= g.retry_limit:
            raise ReachedRetryLimitError("Reached upload retry limit.")

        if retry_count > 0:
            log(f"Waiting {wait_time} seconds before retrying upload.")
            time.sleep(wait_time)

        retry_count += 1
        wait_time = wait_time * 2

        log("Uploading asset.")
        try:
            response = g.upload_asset(file_path, release)
            if response.status_code != requests.codes.created:
                log("Ignoring failed upload.")
                log_response(response)
        except Exception:  # pylint: disable=broad-except;
            log_exception("Ignoring upload exception.")

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

    retry_count = 0
    wait_time = 2

    while True:
        try:
            log("Creating the release.")
            response = g.create_release(release)
            if response.status_code != requests.codes.created:
                log("Failed...")
                # Try to decode the error.
                try:
                    error: GithubClientError = GithubClientError.from_json(
                        response.content
                    )
                except json.JSONDecodeError:
                    raise UnexpectedResponseError(response)

                if not error.errors:
                    raise UnexpectedResponseError(response)

                if (
                    (not error.errors)
                    or error.errors[0].resource != "Release"
                    or error.errors[0].code != "already_exists"
                ):
                    raise UnexpectedResponseError(response)

                log("...but this is OK, because the release already exists.")
                log("Getting the current release.")
                response = g.get_release_by_tag(release.tag_name)
                if response.status_code != requests.codes.ok:
                    raise UnexpectedResponseError(response)

        except UnexpectedResponseError:
            log_exception(
                "Unexpected response when creating the release or getting the existing release info."
            )
            # Note: GitHub will sometimes return a custom error for the Release resource with a message:
            # "Published releases must have a valid tag".
            # I suspect this is a race condition that occurs when multiple clients try to create the release at the same
            # time, or this is a race condition that occurs within GitHub itself when creating the tag as part of
            # creating the release. Thus, we retry creating/getting the release.
            if retry_count >= g.retry_limit:
                raise ReachedRetryLimitError(
                    "Reached retry limit for creating release."
                )
            log("...retrying.")
            time.sleep(wait_time)
            retry_count += 1
            wait_time = wait_time * 2
            continue

        # Exit the loop.
        break

    log("Decoding release info.")
    try:
        # noinspection PyUnboundLocalVariable
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
        help="The number of times to retry creating/getting the release and/or uploading each file. ",
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
