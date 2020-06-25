#!/usr/bin/env bash

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

set -x
set -e
set -u

# Check for some known files for sanity.
test -f ./Pipfile

if [ -z ${VIRTUAL_ENV+x} ]; then
  source .venv/bin/activate
fi

python ci/check_headers.py
mypy --strict --show-absolute-path github_release_retry github_release_retry_tests
pylint github_release_retry github_release_retry_tests
# Flake checks formatting via black.
flake8 .

pytest github_release_retry_tests
