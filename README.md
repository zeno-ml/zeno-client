# Zeno Python Client

[![PyPI version](https://badge.fury.io/py/zeno-client.svg)](https://badge.fury.io/py/zeno-client)
![Github Actions CI tests](https://github.com/zeno-ml/zeno-client/actions/workflows/ci.yml/badge.svg)
[![MIT license](https://img.shields.io/badge/License-MIT-blue.svg)](https://lbesson.mit-license.org/)
[![DOI](https://img.shields.io/badge/doi-10.1145%2F3544548.3581268-red)](https://cabreraalex.com/paper/zeno)
[![Discord](https://img.shields.io/discord/1086004954872950834)](https://discord.gg/km62pDKAkE)

The Zeno Python client lets you create and manage Zeno projects from Python.

Check out example projects at [hub.zenoml.com](http://hub.zenoml.com), [learn how to use the API](https://zenoml.com/docs/intro#creating-a-project), or [see the full API documentation](https://zenoml.com/docs/python-client).

## Release Instructions

To create a new release, first send a PR with a bumped package version in `pyproject.toml`.

Then, in GitHub, click on "Releases" and "Draft a new Release".
From here click on "tag" and create a new tag of the form `vX.X.X` for your new version.
Make the release title the same as the tag.
Click "Generate release notes", and publish the release.
