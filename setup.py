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

from pathlib import Path

try:
    from setuptools import setup, Extension
except Exception:
    from distutils.core import setup, Extension


def get_long_description() -> str:
    readme_path = Path(__file__).parent / "README.md"
    return readme_path.read_text(encoding="utf-8")


setup(
    name="github-release-retry",
    version="1.0.8",
    description="A tool for creating GitHub Releases and uploading assets reliably.",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    keywords="GitHub Release Releases reliable retry upload assets",
    author="The github-release-retry Project Authors",
    author_email="android-graphics-tools-team@google.com",
    url="https://github.com/google/github-release-retry",
    license="Apache License 2.0",
    packages=["github_release_retry"],
    python_requires=">=3.6",
    install_requires=[
        'dataclasses;python_version=="3.6"',
        "dataclasses-json",
        "requests",
    ],
    package_data={"github_release_retry": ["py.typed"]},
    classifiers=[
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3 :: Only",
    ],
    project_urls={
        "Documentation": "https://github.com/google/github-release-retry",
        "Source": "https://github.com/google/github-release-retry",
    },
    entry_points={
        "console_scripts": [
            "github-release-retry = github_release_retry.github_release_retry:main",
        ]
    },
)
