# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
import pymodbus.datastore
import pymodbus.datastore.context

from pretty_modbus import context
from pretty_modbus.layout import ServerContextLayout, SlaveContextLayout
from pretty_modbus import registers
from pretty_modbus import coils
from pretty_modbus import exceptions


# Need a different pymodbus context here, as we need to check the correct
# initialization (the "session" modbus_context may have been written
# to already).
@pytest.fixture
def modbus_context():
    return pymodbus.datastore.ModbusServerContext(
        slaves={
            0: pymodbus.datastore.ModbusSlaveContext(
                hr=pymodbus.datastore.ModbusSequentialDataBlock(0, [0] * 100),
                ir=pymodbus.datastore.ModbusSequentialDataBlock(0, [0] * 100),
                co=pymodbus.datastore.ModbusSequentialDataBlock(0, [0] * 100),
                di=pymodbus.datastore.ModbusSequentialDataBlock(0, [0] * 100),
                zero_mode=True,
            ),
            1: pymodbus.datastore.ModbusSlaveContext(
                hr=pymodbus.datastore.ModbusSequentialDataBlock(0, [0] * 100),
                ir=pymodbus.datastore.ModbusSequentialDataBlock(0, [0] * 100),
                co=pymodbus.datastore.ModbusSequentialDataBlock(0, [0] * 100),
                di=pymodbus.datastore.ModbusSequentialDataBlock(0, [0] * 100),
                zero_mode=True,
            ),
        },
        single=False,
    )


class TestServerContext:
    def test_set_input_registers_get_input_registers(self, pylab_context):
        values = {"a": 7, "b": 8, "c": 9}
        pylab_context.set_input_registers(values)
        assert pylab_context.get_input_registers() == values

    def test_set_holding_registers_get_holding_registers(self, pylab_context):
        pylab_context.set_holding_registers(
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
        assert pylab_context.get_holding_registers() == {
            "str": "hello",
            "i": 12,
            "struct": {
                "CHANGED": 1,
                "ELEMENT_TYPE": 33,
                "ELEMENT_ID": 7,
            },
            "f": pytest.approx(3.4, abs=0.001),
        }

    def test_set_coils_get_coils(self, pylab_context):
        values = {"x": [0, 1, 0], "y": 0, "z": [1, 0, 1, 0, 0], "u": 1, "v": [1, 1]}
        pylab_context.set_coils(values)
        assert pylab_context.get_coils() == values

    def test_set_coils_unknown_variable(self, pylab_context):
        with pytest.raises(exceptions.VariableNotFoundError):
            pylab_context.set_coils({"spam": 12})

    def test_set_holding_registers_unknown_variable(self, pylab_context):
        with pytest.raises(exceptions.VariableNotFoundError):
            pylab_context.set_holding_registers({"spam": 12})

    def test_set_discrete_inputs_get_discrete_inputs(self, pylab_context):
        values = {"a": 1, "b": [1, 0], "c": [1, 0, 0]}
        pylab_context.set_discrete_inputs(values)
        assert pylab_context.get_discrete_inputs(values) == values

    @pytest.fixture
    def pylab_context(self, modbus_context, server_layout):
        return context.ServerContext(modbus_context, server_layout)

    @pytest.fixture
    def server_layout(self):
        return ServerContextLayout(
            {
                0: SlaveContextLayout(
                    holding_registers=registers.RegisterLayout(
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
                    ),
                    input_registers=registers.RegisterLayout(
                        [
                            registers.Number("a", "u16"),
                            registers.Number("b", "u16"),
                            registers.Number("c", "u16"),
                        ],
                        byteorder=">",
                    ),
                    coils=coils.CoilLayout(
                        [
                            coils.Variable("x", 3),
                            coils.Variable("y", 1, address=7),
                            coils.Variable("z", 5),
                            coils.Variable("u", 1),
                            coils.Variable("v", 2),
                        ]
                    ),
                    discrete_inputs=coils.CoilLayout(
                        [
                            coils.Variable("a", 1),
                            coils.Variable("b", 2),
                            coils.Variable("c", 3),
                        ]
                    ),
                )
            }
        )

    @pytest.fixture
    def dummy_context(self, modbus_context):
        return context.ServerContext(
            modbus_context,
            ServerContextLayout(
                {
                    0: SlaveContextLayout(),
                    # Minimum functioning slave context.
                    2: SlaveContextLayout(
                        holding_registers=registers.RegisterLayout(
                            [registers.Number("", "i32")]
                        ),
                        input_registers=registers.RegisterLayout(
                            [registers.Number("", "i32")]
                        ),
                        coils=coils.CoilLayout([coils.Variable("")]),
                        discrete_inputs=coils.CoilLayout([coils.Variable("")]),
                    ),
                }
            ),
        )

    @pytest.mark.parametrize(
        "unit, error",
        [
            (0, exceptions.MissingSubLayoutError),
            (1, exceptions.NoSuchSlaveLayoutError),
            (2, exceptions.NoSuchSlaveError),
        ],
    )
    def test_get_input_registers_missing_layout(self, unit, error, dummy_context):
        with pytest.raises(error):
            dummy_context.get_input_registers({}, unit=unit)

    @pytest.mark.parametrize(
        "unit, error",
        [
            (0, exceptions.MissingSubLayoutError),
            (1, exceptions.NoSuchSlaveLayoutError),
            (2, exceptions.NoSuchSlaveError),
        ],
    )
    def test_set_input_registers_failure(self, unit, error, dummy_context):
        with pytest.raises(error):
            dummy_context.set_input_registers({"": 1}, unit=unit)

    @pytest.mark.parametrize(
        "unit, error",
        [
            (0, exceptions.MissingSubLayoutError),
            (1, exceptions.NoSuchSlaveLayoutError),
            (2, exceptions.NoSuchSlaveError),
        ],
    )
    def test_get_holding_registers_missing_layout(self, unit, error, dummy_context):
        with pytest.raises(error):
            dummy_context.get_holding_registers({}, unit=unit)

    @pytest.mark.parametrize(
        "unit, error",
        [
            (0, exceptions.MissingSubLayoutError),
            (1, exceptions.NoSuchSlaveLayoutError),
            (2, exceptions.NoSuchSlaveError),
        ],
    )
    def test_set_holding_registers_missing_layout(self, unit, error, dummy_context):
        with pytest.raises(error):
            dummy_context.set_holding_registers({"": 1}, unit=unit)

    @pytest.mark.parametrize(
        "unit, error",
        [
            (0, exceptions.MissingSubLayoutError),
            (1, exceptions.NoSuchSlaveLayoutError),
            (2, exceptions.NoSuchSlaveError),
        ],
    )
    def test_get_coils_missing_layout(self, unit, error, dummy_context):
        with pytest.raises(error):
            dummy_context.get_coils({}, unit=unit)

    @pytest.mark.parametrize(
        "unit, error",
        [
            (0, exceptions.MissingSubLayoutError),
            (1, exceptions.NoSuchSlaveLayoutError),
            (2, exceptions.NoSuchSlaveError),
        ],
    )
    def test_set_coils_missing_layout(self, unit, error, dummy_context):
        with pytest.raises(error):
            dummy_context.set_coils({"": 1}, unit=unit)

    @pytest.mark.parametrize(
        "unit, error",
        [
            (0, exceptions.MissingSubLayoutError),
            (1, exceptions.NoSuchSlaveLayoutError),
            (2, exceptions.NoSuchSlaveError),
        ],
    )
    def test_get_discrete_inputs_missing_layout(self, unit, error, dummy_context):
        with pytest.raises(error):
            dummy_context.get_discrete_inputs({}, unit=unit)

    @pytest.mark.parametrize(
        "unit, error",
        [
            (0, exceptions.MissingSubLayoutError),
            (1, exceptions.NoSuchSlaveLayoutError),
            (2, exceptions.NoSuchSlaveError),
        ],
    )
    def test_set_discrete_inputs_missing_layout(self, unit, error, dummy_context):
        with pytest.raises(error):
            dummy_context.set_discrete_inputs({"": 1}, unit=unit)
