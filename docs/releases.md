# Releases

1. Double-check the current version number in setup.py; it should be a version number that is not yet released.
2. Follow https://packaging.python.org/tutorials/packaging-projects/

Rough summary:

In the developer shell:

```sh
python3 -m pip install --upgrade build
python3 -m pip install --upgrade twine

python3 -m build
python3 -m twine upload --repository testpypi dist/*
# Username: __token__
# Password: [TestPyPI API token, including the pypi- prefix]

# Check: https://test.pypi.org/project/github-release-retry/
# There should be a new version.
```

In some other terminal:

```sh
# Test the test package in some temporary virtual environment.

python3 -m venv .venv

source .venv/bin/activate

python3 -m pip install dataclasses-json
python3 -m pip install requests
python3 -m pip install -i https://test.pypi.org/simple/ --no-deps github-release-retry

github-release-retry -h
```

Now, from the developer shell, repeat the `twine` command above, but omit `--repository testpypi`. Note that the token will be different. There should then be a new package version at: https://pypi.org/project/github-release-retry/

Then, in some other terminal:

```sh
# Test the package in some temporary virtual environment.

python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install github-release-retry
github-release-retry -h
```

## Git tag
Create a git tag of the form "1.0.x" (check the current version number in setup.py) and push it.

## Finally:

Increment the version number in setup.py in preparation for a future release. Do a PR to update the version number.
