# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import importlib

import pymodbus.datastore
import pymodbus.exceptions

from pretty_modbus.layout import ServerContextLayout
from pretty_modbus.const import DEFAULT_SLAVE
from pretty_modbus.exceptions import (
    NoSuchSlaveLayoutError,
    MissingSubLayoutError,
    NoSuchSlaveError,
)


class ServerContext:
    def __init__(
        self,
        context: pymodbus.datastore.context.ModbusServerContext,
        layout: ServerContextLayout,
    ) -> None:
        """Server context with a layout for each slave.

        Args:
            context: The underlying server context
            slave_layout:
                A single slave layout or a ``dict`` which maps a unit id
                to the unit's layout
        """
        self._context = context
        self._layout = layout

    def _get_store(self, unit: Key, item: str) -> ModbusDatastore:
        """Get a datastore from slave.

        Args:
            unit: The slave
            item:
                The usage of the datastore (``"h"``, ``"i"``, ``"c"`` or
                ``"d"``)

        Raises:
            NoSuchSlaveError:
                If ``unit`` is not an item of the context
        """
        try:
            return self._context[unit].store[item]
        except pymodbus.exceptions.NoSuchSlaveException as e:
            raise NoSuchSlaveError from e

    def get_input_registers(
        self, variables: Optional[Iterable[str]] = None, unit: KeyType = DEFAULT_SLAVE
    ) -> dict[str, ValueType]:
        """Read ``variables`` from input register of ``unit``.

        Args:
            variables: The variables to read (all by default)
            unit: The unit to read from

        Returns:
            A ``dict`` mapping the queried variable's names to their
            values

        Raises:
            VariableNotFound:
                If one or more items of ``variables`` are not mapped
                by the input register layout of ``unit``
            MissingLayoutError:
                If there is not slave layout defined for ``unit``
            MissingSubLayoutError:
                If there is no memory layout defined for input registers
            NoSuchSlaveError:
                If ``unit`` is not an item of the context

        Note that this method will always execute a complete readout of
        the slave's input register layout's range.
        """
        slave_layout = self._layout.get_input_register_layout(unit)
        store = self._get_store(unit, "i")
        registers = store.getValues(slave_layout.address, slave_layout.size)
        return slave_layout.decode_registers(registers, variables)

    def set_input_registers(
        self, values: dict[str, ValueType], unit: KeyType = DEFAULT_SLAVE
    ) -> None:
        """Write ``values`` to input register of ``unit``.

        Args:
            values: Dictionary that maps variable to value
            unit: The unit to write to

        Raises:
            VariableNotFound:
                If one or more items of ``variables`` are not mapped
                by the input register layout of ``unit``
            MissingLayoutError:
                If there is not slave layout defined for ``unit``
            MissingSubLayoutError:
                If there is no memory layout defined for input registers
            NoSuchSlaveError:
                If ``unit`` is not an item of the context
        """
        slave_layout = self._layout.get_input_register_layout(unit)
        payloads = slave_layout.build_payload(values)
        for payload in payloads:
            # For some reason, pymodbus stores each register as big-endian
            # integer in memory, so we need to convert.
            self._get_store(unit, "i").setValues(
                payload.address, [_bytes_to_16bit_int(x) for x in payload.values]
            )

    def get_holding_registers(
        self, variables: Optional[Iterable[str]] = None, unit: KeyType = DEFAULT_SLAVE
    ) -> dict[str, ValueType]:
        """Read ``variables`` from holding register of ``unit``.

        Args:
            variables: The variables to read (all by default)
            unit: The unit to read from

        Returns:
            A ``dict`` mapping the queried variable's names to their
            values

        Raises:
            VariableNotFound:
                If one or more items of ``variables`` are not mapped
                by the input register layout of ``unit``
            MissingLayoutError:
                If there is not slave layout defined for ``unit``
            MissingSubLayoutError:
                If there is no memory layout defined for input registers
            NoSuchSlaveError:
                If ``unit`` is not an item of the context

        Note that this method will always execute a complete readout of
        the slave's holding register layout's range.
        """
        slave_layout = self._layout.get_holding_register_layout(unit)
        store = self._get_store(unit, "h")
        registers = store.getValues(slave_layout.address, slave_layout.size)
        return slave_layout.decode_registers(registers, variables)

    def set_holding_registers(
        self, values: dict[str, ValueType], unit: KeyType = DEFAULT_SLAVE
    ) -> None:
        """Write ``values`` to holding register of ``unit``.

        Args:
            values: Dictionary that maps variable to value
            unit: The unit to write to

        Raises:
            VariableNotFound:
                If one or more items of ``variables`` are not mapped
                by the input register layout of ``unit``
            MissingLayoutError:
                If there is not slave layout defined for ``unit``
            MissingSubLayoutError:
                If there is no memory layout defined for input registers
            NoSuchSlaveError:
                If ``unit`` is not an item of the context
        """
        slave_layout = self._layout.get_holding_register_layout(unit)
        payloads = slave_layout.build_payload(values)
        # For some reason, pymodbus stores each register as big-endian
        # integer in memory, so we need to convert.
        for payload in payloads:
            self._get_store(unit, "h").setValues(
                payload.address, [_bytes_to_16bit_int(x) for x in payload.values]
            )

    def get_coils(
        self, variables: Optional[Iterable[str]] = None, unit: KeyType = DEFAULT_SLAVE
    ) -> dict[str, ValueType]:
        """Read ``variables`` from coils of ``unit``.

        Args:
            variables: The variables to read (all by default)
            unit: The unit to read from

        Returns:
            A ``dict`` mapping the queried variable's names to their
            values

        Raises:
            VariableNotFound:
                If one or more items of ``variables`` are not mapped
                by the input register layout of ``unit``
            MissingLayoutError:
                If there is not slave layout defined for ``unit``
            MissingSubLayoutError:
                If there is no memory layout defined for input registers
            NoSuchSlaveError:
                If ``unit`` is not an item of the context

        Note that this method will always execute a complete readout of
        the slave's coil layout's range.
        """
        slave_layout = self._layout.get_coil_layout(unit)
        store = self._get_store(unit, "c")
        coils = store.getValues(slave_layout.address, slave_layout.size)
        return slave_layout.decode_coils(coils, variables)

    def set_coils(
        self, values: dict[str, ValueType], unit: KeyType = DEFAULT_SLAVE
    ) -> None:
        """Write ``values`` to coils of ``unit``.

        Args:
            values: Dictionary that maps variable to value
            unit: The unit to write to

        Raises:
            VariableNotFound:
                If one or more items of ``variables`` are not mapped
                by the input register layout of ``unit``
            MissingLayoutError:
                If there is not slave layout defined for ``unit``
            MissingSubLayoutError:
                If there is no memory layout defined for input registers
            NoSuchSlaveError:
                If ``unit`` is not an item of the context
        """
        slave_layout = self._layout.get_coil_layout(unit)
        payloads = slave_layout.build_payload(values)
        for payload in payloads:
            self._get_store(unit, "c").setValues(payload.address, payload.values)

    def get_discrete_inputs(
        self, variables: Optional[Iterable[str]] = None, unit: KeyType = DEFAULT_SLAVE
    ) -> dict[str, ValueType]:
        """Read ``variables`` from discrete inputs of ``unit``.

        Args:
            variables: The variables to read (all by default)
            unit: The unit to read from

        Returns:
            A ``dict`` mapping the queried variable's names to their
            values

        Raises:
            VariableNotFound:
                If one or more items of ``variables`` are not mapped
                by the input register layout of ``unit``
            MissingLayoutError:
                If there is not slave layout defined for ``unit``
            MissingSubLayoutError:
                If there is no memory layout defined for input registers
            NoSuchSlaveError:
                If ``unit`` is not an item of the context

        Note that this method will always execute a complete readout of
        the slave's discrete input layout's range.
        """
        slave_layout = self._layout.get_discrete_input_layout(unit)
        store = self._get_store(unit, "d")
        coils = store.getValues(slave_layout.address, slave_layout.size)
        return slave_layout.decode_coils(coils, variables)

    def set_discrete_inputs(
        self, values: dict[str, ValueType], unit: KeyType = DEFAULT_SLAVE
    ) -> None:
        """Write ``values`` to discrete inputs of ``unit``.

        Args:
            values: Dictionary that maps variable to value
            unit: The unit to write to

        Raises:
            VariableNotFound:
                If one or more items of ``variables`` are not mapped
                by the input register layout of ``unit``
            MissingLayoutError:
                If there is not slave layout defined for ``unit``
            MissingSubLayoutError:
                If there is no memory layout defined for input registers
            NoSuchSlaveError:
                If ``unit`` is not an item of the context
        """
        slave_layout = self._layout.get_discrete_input_layout(unit)
        payloads = slave_layout.build_payload(values)
        for payload in payloads:
            self._get_store(unit, "d").setValues(payload.address, payload.values)

    async def get_input_registers_coro(
        self, variables: Optional[Iterable[str]] = None, unit: KeyType = DEFAULT_SLAVE
    ) -> dict[str, ValueType]:
        """Coroutine version of ``get_input_registers`` for convenience.

        Use this coroutine to prevent race conditions between server and
        client access to the underlying datastore.
        """
        return self.get_input_registers(variables, unit)

    async def set_input_registers_coro(self, values: dict[str, ValueType]) -> None:
        """Coroutine version of ``set_input_registers`` for convenience.

        Use this coroutine to prevent race conditions between server and
        client access to the underlying datastore.
        """
        self.set_input_registers(values)

    async def get_holding_registers_coro(
        self, variables: Optional[Iterable[str]] = None, unit: KeyType = DEFAULT_SLAVE
    ) -> dict[str, ValueType]:
        """Coroutine version of ``get_holding_registers`` for convenience.

        Use this coroutine to prevent race conditions between server and
        client access to the underlying datastore.
        """
        return self.get_holding_registers(variables, unit)

    async def set_holding_registers_coro(self, values: dict[str, ValueType]) -> None:
        """Coroutine version of ``set_holding_registers`` for convenience.

        Use this coroutine to prevent race conditions between server and
        client access to the underlying datastore.
        """
        self.set_holding_registers(values)

    async def get_discrete_inputs_coro(
        self, variables: Optional[Iterable[str]] = None, unit: KeyType = DEFAULT_SLAVE
    ) -> dict[str, ValueType]:
        """Coroutine version of ``get_discrete_inputs`` for convenience.

        Use this coroutine to prevent race conditions between server and
        client access to the underlying datastore.
        """
        return self.get_discrete_inputs(variables, unit)

    async def set_discrete_inputs_coro(self, values: dict[str, ValueType]) -> None:
        """Coroutine version of ``set_discrete_inputs`` for convenience.

        Use this coroutine to prevent race conditions between server and
        client access to the underlying datastore.
        """
        self.set_discrete_inputs(values)

    async def get_coils_coro(
        self, variables: Optional[Iterable[str]] = None, unit: KeyType = DEFAULT_SLAVE
    ) -> dict[str, ValueType]:
        """Coroutine version of ``get_coils`` for convenience.

        Use this coroutine to prevent race conditions between server and
        client access to the underlying datastore.
        """
        return self.get_coils(variables, unit)

    async def set_coils_coro(self, values: dict[str, ValueType]) -> None:
        """Coroutine version of ``set_coils`` for convenience.

        Use this coroutine to prevent race conditions between server and
        client access to the underlying datastore.
        """
        self.set_coils(values)


def _bytes_to_16bit_int(b: bytes) -> int:
    """Convert two bytes to integer.

    Args:
        b: Sequence of bytes of length at least 2

    Wordorder and byteorder are big-endian.
    """
    assert len(b) > 1
    return 256 * b[0] + b[1]
