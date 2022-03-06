# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

import asyncio

import pytest

from pretty_modbus import layout
from pretty_modbus import registers
from pretty_modbus import coils
from pretty_modbus import async_io


@pytest.fixture
def holding_register_layout():
    return registers.RegisterLayout(
        [
            registers.Str("str", length=5, address=2),
            registers.Number("i", "i32"),
            registers.Struct(
                "struct",
                [
                    registers.Field("CHANGED", "u1"),
                    registers.Field("ELEMENT_TYPE", "u7"),
                    registers.Field("ELEMENT_ID", "u5"),
                ],
                address=19,
            ),
            registers.Number("f", "f16"),
        ]
    )


@pytest.fixture
def input_register_layout():
    return registers.RegisterLayout(
        [
            registers.Number("a", "u16"),
            registers.Number("b", "u16"),
            registers.Number("c", "u16"),
        ],
        byteorder=">",
    )


@pytest.fixture
def coil_layout():
    return coils.CoilLayout(
        [
            coils.Variable("x", 3),
            coils.Variable("y", 1, address=7),
            coils.Variable("z", 5),
            coils.Variable("u", 1),
            coils.Variable("v", 2),
        ]
    )


@pytest.fixture
def discrete_input_layout():
    return coils.CoilLayout(
        [
            coils.Variable("a", 1),
            coils.Variable("b", 2),
            coils.Variable("c", 3),
        ]
    )
