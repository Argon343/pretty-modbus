# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from pretty_modbus import exceptions
from pretty_modbus import async_io
from pretty_modbus.layout import ServerContextLayout, SlaveContextLayout
from pretty_modbus import registers
from pretty_modbus import coils


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


@pytest.fixture
def server_context_layout(
    holding_register_layout, input_register_layout, coil_layout, discrete_input_layout
):
    return ServerContextLayout(
        {
            0: SlaveContextLayout(
                holding_registers=holding_register_layout,
                input_registers=input_register_layout,
                coils=coil_layout,
            ),
            1: SlaveContextLayout(
                holding_registers=registers.RegisterLayout(
                    [
                        registers.Number("a", "u16", address=0),
                        registers.Number("b", "u16"),
                        registers.Number("c", "u16"),
                        registers.Str("str", length=5, address=12),
                    ],
                    byteorder=">",
                ),
                input_registers=registers.RegisterLayout(
                    [
                        registers.Number("a", "u16", address=0),
                        registers.Number("b", "u16"),
                        registers.Number("c", "u16"),
                        registers.Str("str", length=5, address=12),
                    ],
                    byteorder=">",
                ),
                discrete_inputs=discrete_input_layout,
            ),
            # This layout refers to a non-existent unit:
            2: SlaveContextLayout(
                holding_registers=registers.RegisterLayout(
                    [registers.Number("a", "i32")]
                ),
                input_registers=registers.RegisterLayout(
                    [registers.Number("a", "i32")]
                ),
                coils=coils.CoilLayout([coils.Variable("a")]),
                discrete_inputs=coils.CoilLayout([coils.Variable("a")]),
            ),
            # Empty layout for testing errors for missing layouts.
            3: SlaveContextLayout(),
        },
    )


@pytest.fixture
def protocol(client, server_context_layout):
    return async_io.Protocol(client.protocol, server_context_layout)


class TestProtocol:
    @pytest.mark.asyncio
    async def test_variable_not_found(self, protocol):
        with pytest.raises(exceptions.VariableNotFoundError):
            await protocol.write_holding_register("spam", 123)

    @pytest.mark.asyncio
    async def test_write_holding_registers_failure(self, protocol):
        with pytest.raises(exceptions.ModbusResponseError):
            await protocol.write_holding_registers({"a": 1}, unit=2)

    @pytest.mark.asyncio
    async def test_write_holding_register_failure(self, protocol):
        with pytest.raises(exceptions.ModbusResponseError):
            await protocol.write_holding_register("a", 1, unit=2)

    @pytest.mark.asyncio
    async def test_write_coils_failure(self, protocol):
        with pytest.raises(exceptions.ModbusResponseError):
            await protocol.write_coils({"a": 1}, unit=2)

    @pytest.mark.asyncio
    async def test_write_coil_failure(self, protocol):
        with pytest.raises(exceptions.ModbusResponseError):
            await protocol.write_coil("a", 1, unit=2)

    @pytest.mark.asyncio
    async def test_read_holding_register_failure(self, protocol):
        with pytest.raises(exceptions.ModbusResponseError):
            await protocol.read_holding_register("a", unit=2)

    @pytest.mark.asyncio
    async def test_read_holding_registers_failure(self, protocol):
        with pytest.raises(exceptions.ModbusResponseError):
            await protocol.read_holding_registers("a", unit=2)

    @pytest.mark.asyncio
    async def test_read_input_register_failure(self, protocol):
        with pytest.raises(exceptions.ModbusResponseError):
            await protocol.read_input_register("a", unit=2)

    @pytest.mark.asyncio
    async def test_read_input_registers_failure(self, protocol):
        with pytest.raises(exceptions.ModbusResponseError):
            await protocol.read_input_registers("a", unit=2)

    @pytest.mark.asyncio
    async def test_read_coil_failure(self, protocol):
        with pytest.raises(exceptions.ModbusResponseError):
            await protocol.read_coil("a", unit=2)

    @pytest.mark.asyncio
    async def test_read_coils_failure(self, protocol):
        with pytest.raises(exceptions.ModbusResponseError):
            await protocol.read_coils("a", unit=2)

    @pytest.mark.asyncio
    async def test_read_discrete_input_failure(self, protocol):
        with pytest.raises(exceptions.ModbusResponseError):
            await protocol.read_discrete_input("a", unit=2)

    @pytest.mark.asyncio
    async def test_read_discrete_input_failure(self, protocol):
        with pytest.raises(exceptions.ModbusResponseError):
            await protocol.read_discrete_inputs({}, unit=2)

    @pytest.mark.asyncio
    async def test_write_holding_registers_read_holding_registers(self, protocol):
        await protocol.write_holding_registers(
            {
                "str": "hello",
                "i": 12,
                "struct": {
                    "CHANGED": 1,
                    "ELEMENT_TYPE": 33,
                    "ELEMENT_ID": 7,
                },
                "f": 3.4,
            }
        )
        assert await protocol.read_holding_registers() == {
            "str": "hello",
            "i": 12,
            "struct": {
                "CHANGED": 1,
                "ELEMENT_TYPE": 33,
                "ELEMENT_ID": 7,
            },
            "f": pytest.approx(3.4, abs=0.001),
        }
        await protocol.write_holding_register("str", "world")
        assert await protocol.read_holding_register("str") == "world"
        assert await protocol.read_holding_register("i") == 12
        assert await protocol.read_holding_register("struct") == {
            "CHANGED": 1,
            "ELEMENT_TYPE": 33,
            "ELEMENT_ID": 7,
        }
        assert await protocol.read_holding_register("f") == pytest.approx(
            3.4, abs=0.001
        )
        assert await protocol.read_holding_registers({"i", "str"}) == {
            "i": 12,
            "str": "world",
        }

    @pytest.mark.asyncio
    async def test_read_input_registers(self, protocol):
        result = await protocol.read_input_registers(unit=1)
        assert result["a"] == 0
        assert result["b"] == 0
        assert result["c"] == 0

    @pytest.mark.asyncio
    async def test_multiple_slaves(self, protocol):
        await protocol.write_holding_registers({"a": 1, "b": 2, "c": 3}, unit=1)
        await protocol.write_holding_register("str", "world", unit=0)
        await protocol.write_holding_register("str", "hello", unit=1)
        assert await protocol.read_holding_register("str", unit=0) == "world"
        assert await protocol.read_holding_register("str", unit=1) == "hello"

    @pytest.mark.asyncio
    async def test_write_coils_read_coils(self, protocol):
        values = {
            "x": [0, 1, 0],
            "y": 1,
            "z": [0, 1, 1, 0, 1],
            "u": 0,
            "v": [1, 1],
        }
        await protocol.write_coils(values)
        assert await protocol.read_coils() == values

    @pytest.mark.asyncio
    async def test_read_discrete_inputs(self, protocol):
        assert await protocol.read_discrete_inputs(unit=1) == {
            "a": 0,
            "b": [0, 0],
            "c": [0, 0, 0],
        }

    @pytest.mark.parametrize(
        "unit, error",
        [
            (3, exceptions.MissingSubLayoutError),
            (4, exceptions.NoSuchSlaveLayoutError),
        ],
    )
    @pytest.mark.asyncio
    async def test_read_input_registers_missing_layout(self, unit, error, protocol):
        with pytest.raises(error):
            await protocol.read_input_registers(unit=unit)

    @pytest.mark.parametrize(
        "unit, error",
        [
            (3, exceptions.MissingSubLayoutError),
            (4, exceptions.NoSuchSlaveLayoutError),
        ],
    )
    @pytest.mark.asyncio
    async def test_read_input_register_missing_layout(self, unit, error, protocol):
        with pytest.raises(error):
            await protocol.read_input_register("", unit=unit)

    @pytest.mark.parametrize(
        "unit, error",
        [
            (3, exceptions.MissingSubLayoutError),
            (4, exceptions.NoSuchSlaveLayoutError),
        ],
    )
    @pytest.mark.asyncio
    async def test_read_discrete_inputs_missing_layout(self, unit, error, protocol):
        with pytest.raises(error):
            await protocol.read_discrete_inputs(unit=unit)

    @pytest.mark.parametrize(
        "unit, error",
        [
            (3, exceptions.MissingSubLayoutError),
            (4, exceptions.NoSuchSlaveLayoutError),
        ],
    )
    @pytest.mark.asyncio
    async def test_read_discrete_input_missing_layout(self, unit, error, protocol):
        with pytest.raises(error):
            await protocol.read_discrete_input("", unit=unit)

    @pytest.mark.parametrize(
        "unit, error",
        [
            (3, exceptions.MissingSubLayoutError),
            (4, exceptions.NoSuchSlaveLayoutError),
        ],
    )
    @pytest.mark.asyncio
    async def test_read_holding_registers_missing_layout(self, unit, error, protocol):
        with pytest.raises(error):
            await protocol.read_holding_registers(unit=unit)

    @pytest.mark.parametrize(
        "unit, error",
        [
            (3, exceptions.MissingSubLayoutError),
            (4, exceptions.NoSuchSlaveLayoutError),
        ],
    )
    @pytest.mark.asyncio
    async def test_read_holding_register_missing_layout(self, unit, error, protocol):
        with pytest.raises(error):
            await protocol.read_holding_register("", unit=unit)

    @pytest.mark.parametrize(
        "unit, error",
        [
            (3, exceptions.MissingSubLayoutError),
            (4, exceptions.NoSuchSlaveLayoutError),
        ],
    )
    @pytest.mark.asyncio
    async def test_write_holding_registers_missing_layout(self, unit, error, protocol):
        with pytest.raises(error):
            await protocol.write_holding_registers({}, unit=unit)

    @pytest.mark.parametrize(
        "unit, error",
        [
            (3, exceptions.MissingSubLayoutError),
            (4, exceptions.NoSuchSlaveLayoutError),
        ],
    )
    @pytest.mark.asyncio
    async def test_write_holding_register_missing_layout(self, unit, error, protocol):
        with pytest.raises(error):
            await protocol.write_holding_register("", 0, unit=unit)

    @pytest.mark.parametrize(
        "unit, error",
        [
            (3, exceptions.MissingSubLayoutError),
            (4, exceptions.NoSuchSlaveLayoutError),
        ],
    )
    @pytest.mark.asyncio
    async def test_read_coils_missing_layout(self, unit, error, protocol):
        with pytest.raises(error):
            await protocol.read_coils(unit=unit)

    @pytest.mark.parametrize(
        "unit, error",
        [
            (3, exceptions.MissingSubLayoutError),
            (4, exceptions.NoSuchSlaveLayoutError),
        ],
    )
    @pytest.mark.asyncio
    async def test_read_coil_missing_layout(self, unit, error, protocol):
        with pytest.raises(error):
            await protocol.read_coil("", unit=unit)

    @pytest.mark.parametrize(
        "unit, error",
        [
            (3, exceptions.MissingSubLayoutError),
            (4, exceptions.NoSuchSlaveLayoutError),
        ],
    )
    @pytest.mark.asyncio
    async def test_write_coils_missing_layout(self, unit, error, protocol):
        with pytest.raises(error):
            await protocol.write_coils({}, unit=unit)

    @pytest.mark.parametrize(
        "unit, error",
        [
            (3, exceptions.MissingSubLayoutError),
            (4, exceptions.NoSuchSlaveLayoutError),
        ],
    )
    @pytest.mark.asyncio
    async def test_write_coil_missing_layout(self, unit, error, protocol):
        with pytest.raises(error):
            await protocol.write_coil("", 0, unit=unit)
