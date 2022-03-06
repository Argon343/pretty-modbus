# SPDX-FileCopyrightText: 2022 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

import setuptools

with open("README.md") as readme:
    long_description = readme.read()

setuptools.setup(
    name="pretty-modbus",
    version="0.1.0",
    author="Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="GPL-3.0-or-later",
    packages=setuptools.find_packages("src"),
    package_dir={"": "src"},
    include_package_data=True,
    python_requires=">=3.9",
)
