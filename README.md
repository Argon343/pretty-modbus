<!--
SPDX-FileCopyrightText: 2022 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH

SPDX-License-Identifier: GPL-3.0-or-later
-->

# pretty-modbus

[![Linux (install, test)](https://github.com/maltekliemann/pretty-modbus/actions/workflows/linux.yaml/badge.svg)](https://github.com/maltekliemann/pretty-modbus/actions/workflows/linux.yaml)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**pretty-modbus** is a wrapper for [pymodbus] servers and clients with allows
defining a memory layout for convenient writing and reading of data.

It also offers abstractions over the [pymodbus] client and server
classes for utility and convenience.

## Documentation

-   For a tutorial outlining the basic concepts of **pretty-modbus**, see
    [tutorial]
-   For an example of **pretty-modbus** use, see [example]
-   For documentation, refer to the docstrings in `src/pretty_modbus`

## License

This project is [REUSE 3.0](https://reuse.software) compliant. It is licensed
under GPL-3.0-or-later. See `LICENSES/` for details.

## Technical notes for devs

### Style guide

-   Our Python code follows the [Black](https://github.com/psf/black) style
    guide
-   The formatting of our Python docstrings follows
    [3.8 Comments and Docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
    of the Google Python Style Guide

### Workflow

We use the standard
[gitflow](https://nvie.com/posts/a-successful-git-branching-model/) branching
model. Pull requests should only go into the `develop` branch. The `develop`
branch will be regularly merged into `master`.

<!-- Links -->

[pymodbus]: https://github.com/riptideio/pymodbus
[example]: examples/threaded_network.py
[bitstruct]: https://github.com/eerimoq/bitstruct
[tutorial]: docs/tutorial.md
