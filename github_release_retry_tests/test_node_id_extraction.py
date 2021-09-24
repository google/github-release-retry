# -*- coding: utf-8 -*-

# Copyright 2021 The github-release-retry Project Authors
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

import base64

from github_release_retry import github_release_retry


def test_release_asset_node_id_to_asset_id() -> None:

    old_format_node_id = "MDEyOlJlbGVhc2VBc3NldDQyMTY0NTg2"
    old_format_expected_asset_id = "42164586"

    old_format_actual_asset_id = github_release_retry.release_asset_node_id_to_asset_id(
        old_format_node_id
    )

    assert old_format_actual_asset_id == old_format_expected_asset_id

    new_format_node_id = "RA_kwDODNhc0c4CrJ0q"
    new_format_expected_asset_id = "44866858"

    new_format_actual_asset_id = github_release_retry.release_asset_node_id_to_asset_id(
        new_format_node_id
    )

    assert new_format_actual_asset_id == new_format_expected_asset_id


def test_release_asset_node_id_to_asset_id_exception() -> None:
    # The release_asset_node_id_to_asset_id(...) function expects a node id with "ReleaseAsset", not "ReleaseBadAsset".
    node_id_decoded = b"012:ReleaseBadAsset18381577"
    node_id_encoded = base64.b64encode(node_id_decoded).decode(
        encoding="utf-8", errors="none"
    )

    try:
        github_release_retry.release_asset_node_id_to_asset_id(node_id_encoded)
    except AssertionError as error:
        message = str(error)
        assert "format" in message
        return

    raise AssertionError("Expected an exception")
