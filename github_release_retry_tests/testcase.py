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

import json
import os
from typing import Any


class GitHubTestCase:
    @classmethod
    def get_fixture(cls, filename: str) -> Any:
        location = os.path.realpath(
            os.path.join(os.getcwd(), os.path.dirname(__file__))
        )
        fixture = os.path.join(location, "fixtures", filename)
        with open(fixture, encoding="utf-8", errors="ignore") as json_file:
            data = json.load(json_file)
            return data
