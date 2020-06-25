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


import requests
import requests_mock  # type: ignore

from github_release_retry.github_release_retry import GithubApi, Release
from github_release_retry_tests.testcase import GitHubTestCase


class TestGithubApi(GitHubTestCase):
    @staticmethod
    def test_github_api_invalid_token() -> None:
        github = GithubApi(  # noqa: S106
            github_api_url="https://api.github.com",
            user="google",
            repo="github-release-retry",
            token="INVALID_TOKEN",
            retry_limit=10,
        )
        assert github.token == "INVALID_TOKEN"

        release = Release(
            tag_name="v1.0",
            target_commitish=None,
            name=None,
            body="Test",
            draft=None,
            prerelease=None,
        )

        github_release = github.create_release(release)

        assert github_release.status_code == requests.codes.unauthorized

    def test_create_release_with_mock_requests_already_exists(self) -> None:
        github = GithubApi(  # noqa: S106
            github_api_url="https://api.github.com",
            user="google",
            repo="github-release-retry",
            token="VALID_MOCK_TOKEN",
            retry_limit=10,
        )
        assert github.token == "VALID_MOCK_TOKEN"

        release = Release(
            tag_name="v1.0",
            target_commitish=None,
            name=None,
            body="Test",
            draft=None,
            prerelease=None,
        )

        with requests_mock.Mocker() as mocker:
            mocker.register_uri(
                "POST",
                f"{github.github_api_url}/repos/{github.user}/{github.repo}/releases",
                json=self.get_fixture("release_already_exists.json"),
                status_code=requests.codes.unprocessable_entity,
            )
            mocker.register_uri(
                "GET",
                f"{github.github_api_url}/repos/{github.user}/{github.repo}/releases/tags/{release.tag_name}",
                json=self.get_fixture("get_release_by_tag.json"),
            )

            github_release = github.create_release(release)

            assert github_release.status_code == requests.codes.unprocessable_entity

    def test_get_release_by_tag_mock_data(self) -> None:
        github = GithubApi(  # noqa: S106
            github_api_url="https://api.github.com",
            user="google",
            repo="github-release-retry",
            token="VALID_MOCK_TOKEN",
            retry_limit=10,
        )
        assert github.token == "VALID_MOCK_TOKEN"

        release = Release(
            tag_name="v1.0",
            target_commitish=None,
            name=None,
            body="Test",
            draft=None,
            prerelease=None,
        )

        with requests_mock.Mocker() as mocker:
            mocker.register_uri(
                "GET",
                f"{github.github_api_url}/repos/{github.user}/{github.repo}/releases/tags/{release.tag_name}",
                json=self.get_fixture("get_release_by_tag.json"),
                status_code=requests.codes.ok,
            )

            github_release = github.get_release_by_tag("v1.0")

            assert github_release.status_code == requests.codes.ok
