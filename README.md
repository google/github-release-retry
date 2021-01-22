# github-release-retry

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)


`github-release-retry` is a
tool for creating GitHub Releases and uploading assets **reliably**.
It differs from other
tools because it uploads
assets reliably by
verifying that the asset
exists,
and retries (deleting partial assets) if not.

This is not an officially supported Google product.

## Install

Requires Python 3.6+.

To ensure you use the `pip` module associated with your
preferred Python 3.6+ binary:

```bash
python3 -m pip install --user github-release-retry
# where `python3` is your preferred Python 3.6+ binary.
# Omit `--user` to install for all users.
```

Or just:

```bash
pip3 install --user github-release-retry
# where `pip3` is your version of pip for Python 3.6+.
# Omit `--user` to install for all users.
```

## Usage

If your [Python user scripts directory](https://www.python.org/dev/peps/pep-0370/)
is not on your `PATH`,
you can use:

```bash
python3 -m github_release_retry.github_release_retry
# where `python3` is your preferred Python 3.6+ binary.
```

Otherwise:

```bash
$ github-release-retry -h
usage: github-release-retry [-h] --user USER --repo REPO --tag_name TAG_NAME
                            [--target_commitish TARGET_COMMITISH]
                            [--release_name RELEASE_NAME]
                            (--body_string BODY_STRING | --body_file BODY_FILE)
                            [--draft] [--prerelease]
                            [--github_api_url GITHUB_API_URL]
                            [--retry_limit RETRY_LIMIT]
                            [files [files ...]]

Creates a GitHub release (if it does not already exist) and uploads files to the release.
Please set the GITHUB_TOKEN environment variable.
EXAMPLE:
github-release-retry \
  --user paul \
  --repo hello-world \
  --tag_name v1.0 \
  --target_commitish 448301eb \
  --body_string "My first release." \
  hello-world.zip RELEASE_NOTES.txt

positional arguments:
  files                 The files to upload to the release. (default: None)

optional arguments:
  -h, --help            show this help message and exit
  --user USER           Required: The GitHub username or organization name in
                        which the repo resides. (default: None)
  --repo REPO           Required: The GitHub repo name in which to make the
                        release. (default: None)
  --tag_name TAG_NAME   Required: The name of the tag to create or use.
                        (default: None)
  --target_commitish TARGET_COMMITISH
                        The commit-ish value where the tag will be created.
                        Unused if the tag already exists. (default: None)
  --release_name RELEASE_NAME
                        The name of the release. Leave unset to use the
                        tag_name (recommended). (default: None)
  --body_string BODY_STRING
                        Required (or use --body_file): Text describing the
                        release. Ignored if the release already exists.
                        (default: None)
  --body_file BODY_FILE
                        Required (or use --body_string): Text describing the
                        release, which will be read from BODY_FILE. Ignored if
                        the release already exists. (default: None)
  --draft               Creates a draft release, which means it is
                        unpublished. (default: False)
  --prerelease          Creates a prerelease release, which means it will be
                        marked as such. (default: False)
  --github_api_url GITHUB_API_URL
                        The GitHub API URL without a trailing slash. (default:
                        https://api.github.com)
  --retry_limit RETRY_LIMIT
                        The number of times to retry creating/getting the
                        release and/or uploading each file. (default: 10)
```

## Development

> Optional: if you have just done `git pull`
and `Pipfile.lock` was updated,
you can delete `.venv/` to start from a fresh virtual environment.

> On Windows, you can use the Git Bash shell, or adapt the commands (including those inside `dev_shell.sh.template`) for the Windows command prompt.

Clone this repo and change to the directory that contains this README file. Execute `./dev_shell.sh.template`. If the default settings don't work, make a copy of the file called `dev_shell.sh` and modify according to the comments before executing. `pip` must be installed for the version of Python you wish to use. Note that you can do e.g. `export PYTHON=python3` first to set your preferred Python binary.
We currently target Python 3.6+.

> Pip for Python 3.6 may be broken on certain Debian distributions.
> You can just use the newer Python 3.7+ version provided by your
> distribution.
> Alternatively, see "Installing Python" below if you want to use Python 3.6.

The script generates a Python virtual environment (located at `.venv/`) with all dependencies installed.
Activate the Python virtual environment via:

* `source .venv/bin/activate` (on Linux)
* `source .venv/Scripts/activate` (on Windows with the Git Bash shell)
* `.venv/Scripts/activate.bat` (on Windows with cmd)


### Presubmit checks

* Execute `./check_all.sh` to run various presubmit checks, linters, etc.
* Execute `./fix_all.sh` to automatically fix certain issues, such as formatting.


### PyCharm

Use PyCharm to open the directory containing this README file.
It should pick up the Python virtual environment
(at `.venv/`) automatically
for both the code
and when you open a `Terminal` or `Python Console` tab.

Install and configure plugins:

* File Watchers (may already be installed)
  * The watcher task should already be under version control.
* Mypy: the built-in PyCharm type checking uses Mypy behind-the-scenes, but this plugin enhances it by using the latest version and allowing the use of stricter settings, matching the settings used by the `./check_all.sh` script.

Add `dictionary.dic` as a custom dictionary (search for "Spelling" in Actions). Do not add words via PyCharm's "Quick Fixes" feature, as the word will only be added to your personal dictionary. Instead, manually add the word to `dictionary.dic`.

## [Coding conventions](docs/conventions.md)

## Terminal

The `Terminal` tab in PyCharm is useful and will use the project's Python virtual environment.

## Installing Python

To manually install Python on your Linux distribution, you can use `pyenv`.

https://github.com/pyenv/pyenv#basic-github-checkout

In summary:

* Install the required packages recommended [here](https://github.com/pyenv/pyenv/wiki/Common-build-problems).

* Then:

```sh
git clone https://github.com/pyenv/pyenv.git ~/.pyenv

# Add the following two lines to your ~/.bashrc file.
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"

# In a new terminal:
eval "$(pyenv init -)"
pyenv install 3.6.9
pyenv global 3.6.9

# Now execute the development shell script, as usual.
export PYTHON="python"
./dev_shell.sh.template
```

You can reactivate the virtual environment later
using `source .venv/bin/activate`,
without having to re-execute the above `pyenv` commands.
