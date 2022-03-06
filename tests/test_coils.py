# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from pretty_modbus import coils
from pretty_modbus.exceptions import (
    InvalidAddressLayoutError,
    VariableNotFoundError,
    DuplicateVariableError,
    NoVariablesError,
    NegativeAddressError,
)


class TestVariable:
    @pytest.mark.parametrize(
        "size, address, exception",
        [
            (1, -1, NegativeAddressError),
            (0, 77, coils.InvalidSizeError),
            (-3, 7, coils.InvalidSizeError),
        ],
    )
    def test_init_failure(self, size, address, exception):
        with pytest.raises(exception):
            coils.Variable("", size, address)


class TestCoilLayout:
    @pytest.mark.parametrize(
        "variables, exception",
        [
            (
                [coils.Variable("foo", 1, 2), coils.Variable("bar", 77, 2)],
                InvalidAddressLayoutError,
            ),
            (
                [coils.Variable("foo", 2, 2), coils.Variable("foo", 5)],
                DuplicateVariableError,
            ),
            ([], NoVariablesError),
        ],
    )
    def test_init_failure(self, variables, exception):
        with pytest.raises(exception) as e:
            coils.CoilLayout(variables)

    def test_build_payload_failure(self, layout):
        with pytest.raises(VariableNotFoundError):
            layout.build_payload({"x": [1, 2, 3], "a": 0})

    @pytest.fixture
    def layout(self):
        return coils.CoilLayout(
            [
                coils.Variable("x", 3, address=2),
                coils.Variable("y", 1, address=7),
                coils.Variable("z", 5),
                coils.Variable("u", 1),
                coils.Variable("v", 2),
            ]
        )

    def test_build_payload(self, layout):
        payload = layout.build_payload(
            {"x": [0, 1, 0], "y": 1, "z": [0, 0, 1, 1, 0], "v": [0, 1]}
        )
        assert payload == [
            coils.Chunk(2, [0, 1, 0]),
            coils.Chunk(7, [1, 0, 0, 1, 1, 0]),
            coils.Chunk(14, [0, 1]),
        ]

    def test_build_payload_empty(self, layout):
        assert layout.build_payload({}) == []

    @pytest.fixture
    def data(self):
        return [
            {"name": "x", "size": 3, "address": 2},
            {"name": "y", "size": 1, "address": 7},
            {"name": "z", "size": 5},
            {"name": "u", "size": 1},
            {"name": "v", "size": 2},
        ]

    def test_load(self, layout, data):
        loaded = coils.CoilLayout.load(data)
        assert loaded._variables == layout._variables
