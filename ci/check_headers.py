#!/usr/bin/env python3

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

import os
import io
import sys
import re

path = os.path.join


def exclude_dirname(f: str):
    return (
        f.endswith(".egg-info") or f.startswith(".") or f in ["venv", "__pycache__",]
    )


def exclude_dirpath(f: str):
    parts = os.path.split(f)
    return (
        # Ignore /*build*/
        len(parts) == 2
        and "build" in parts[1]
        or f
        in [
            path(os.curdir, "build"),
            path(os.curdir, "dist"),
            path(os.curdir, "out"),
            path(os.curdir, "temp"),
            path(os.curdir, "third_party"),
        ]
    )


def exclude_filepath(f: str):
    return f in []


def exclude_filename(f: str):
    return (
        f.startswith(".attach_pid")
        or f.endswith(".iml")
        or f.endswith(".png")
        or f.endswith(".md")
        or f.endswith(".json")
        or f.endswith(".primitives")
        or f.endswith(".jar")
        or f.endswith(".spv")
        or f.endswith(".dic")
        or f
        in [
            ".clang-format",
            ".clang-tidy",
            ".editorconfig",
            ".gitmodules",
            ".gitignore",
            ".gitattributes",
            "settings.gradle",
            "AUTHORS",
            "CODEOWNERS",
            "CONTRIBUTORS",
            "LICENSE",
            "LICENSE.TXT",
            "OPEN_SOURCE_LICENSES.TXT",
            "local.properties",
            "gradlew",
            "gradlew.bat",
            "dependency-reduced-pom.xml",
            "gradle-wrapper.properties",
            "Pipfile.lock",
        ]
    )


def go():
    fail = False
    copyright_pattern = re.compile(
        r"Copyright 20(18|19|20|21) The github-release-retry Project Authors"
    )

    for (dirpath, dirnames, filenames) in os.walk(os.curdir):

        # dirnames[:] = <--- modifies in-place to ignore certain directories

        if exclude_dirpath(dirpath):
            dirnames[:] = []
            continue

        dirnames[:] = [d for d in dirnames if not exclude_dirname(d)]

        for file in [path(dirpath, f) for f in filenames if not exclude_filename(f)]:
            if exclude_filepath(file):
                continue
            try:
                with io.open(file, "r") as fin:
                    contents = fin.read()

                first_lines = "\n".join(contents.split("\n")[:10])

                # Must contain a header for any year within the first few lines.
                if copyright_pattern.search(first_lines) is None:
                    fail = True
                    print("Missing license header " + file)
                    continue

                    # This file is OK. Continue to the next file.
            except Exception as ex:
                print("Failed to check license header of file " + file)
                print(ex)
                fail = True

    if fail:
        sys.exit(1)


if __name__ == "__main__":
    go()
