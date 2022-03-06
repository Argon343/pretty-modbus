# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import asyncio

from pymodbus.register_read_message import (
    ReadInputRegistersResponse,
    ReadHoldingRegistersResponse,
)
from pymodbus.bit_read_message import ReadCoilsResponse, ReadDiscreteInputsResponse
from pymodbus.bit_write_message import WriteMultipleCoilsResponse
from pymodbus.register_write_message import WriteMultipleRegistersResponse

from pretty_modbus.const import DEFAULT_SLAVE
from pretty_modbus.layout import ServerContextLayout
from pretty_modbus.exceptions import ModbusResponseError


class Protocol:
    """``asyncio`` protocol object for writing/reading using specified
    memory layouts.
    """

    def __init__(
        self,
        protocol: pymodbus.client.asynchronous.async_io.ModbusClientProtocol,
        layout: ServerContextLayout,
    ):
        """
        Args:
            protocol: The `pymodbus` protocol to wrap around
            layout:
                A ``dict`` that maps slave IDs to their slave layout
        """
        self._protocol = protocol
        self._layout = layout

    async def read_input_registers(
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
            ModbusResponseError: If reading the slave failed
            VariableNotFound:
                If one or more items of ``variables`` are not mapped
                by the input register layout of ``unit``
            MissingSubLayoutError:
                If there is no memory layout defined for input registers

        Note that this method will always execute a complete readout of
        the slave's input register layout's range.
        """
        slave_layout = self._layout.get_input_register_layout(unit)
        response = await self._protocol.read_input_registers(
            slave_layout.address, slave_layout.size, unit=unit
        )
        if response.function_code != ReadInputRegistersResponse.function_code:
            raise ModbusResponseError(response)
        return slave_layout.decode_registers(response.registers, variables)

    async def read_input_register(
        self, var: str, unit: KeyType = DEFAULT_SLAVE
    ) -> ValueType:
        """Read ``var`` from input register of ``unit``.

        Args:
            var: The variable to read
            unit: The unit to read from

        Returns: The value of the variable

        Raises:
            ModbusResponseError: If reading the slave failed
            VariableNotFound:
                If ``var`` is not mapped by the input register layout
                of ``unit``
            MissingSubLayoutError:
                If there is no memory layout defined for input registers

        Note that this method will always execute a complete readout of
        the slave's input register layout's range.
        """
        d = await self.read_input_registers(unit=unit)
        return d[var]

    async def read_holding_registers(
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
            ModbusResponseError: If reading the slave failed
            VariableNotFound:
                If one or more items of ``variables`` are not mapped by
                the holding register layout
            MissingSubLayoutError:
                If there is no memory layout defined for holding
                registers

        Note that this method will always execute a complete readout of
        the slave's holding register layout's range.
        """
        slave_layout = self._layout.get_holding_register_layout(unit)
        response = await self._protocol.read_holding_registers(
            slave_layout.address, slave_layout.size, unit=unit
        )
        if response.function_code != ReadHoldingRegistersResponse.function_code:
            raise ModbusResponseError(response)
        return slave_layout.decode_registers(response.registers, variables)

    async def read_holding_register(
        self, var: str, unit: KeyType = DEFAULT_SLAVE
    ) -> ValueType:
        """Read ``var`` from holding register of ``unit``.

        Args:
            var: The variable to read
            unit: The unit to read from

        Returns: The value of the variable

        Raises:
            ModbusResponseError: If reading the slave failed
            VariableNotFound:
                If ``var`` is not mapped by the holding register
                layout of ``unit``
            MissingSubLayoutError:
                If there is no memory layout defined for holding
                registers

        Note that this method will always execute a complete readout of
        the slave's holding register layout's range.
        """
        d = await self.read_holding_registers(unit=unit)
        return d[var]

    async def write_holding_registers(
        self, values: dict[str, ValueType], unit: KeyType = DEFAULT_SLAVE
    ) -> None:
        """Write ``values`` to holding register memory of ``unit``.

        Args:
            values:
                A ``dict`` mapping variable names to the values to write
            unit: The unit to write to

        Raises:
            ModbusResponseError: If reading the slave failed
            VariableNotFound:
                If one or more keys of ``values`` are not mapped by
                the holding register layout of ``unit``
            MissingSubLayoutError:
                If there is no memory layout defined for holding
                registers

        This method will group values which occur back-to-back in memory
        into payload chunks in order to minimize the amount of write
        requests to the server.
        """
        slave_layout = self._layout.get_holding_register_layout(unit)
        payloads = slave_layout.build_payload(values)
        for payload in payloads:
            response = await self._protocol.write_registers(
                payload.address, payload.values, skip_encode=True, unit=unit
            )
            if response.function_code != WriteMultipleRegistersResponse.function_code:
                raise ModbusResponseError(response)

    async def write_holding_register(
        self, var: str, value: ValueType, unit: KeyType = DEFAULT_SLAVE
    ) -> None:
        """Set ``var`` in the holding register to ``value``.

        Args:
            var: The variable to modify
            value: The new value of ``var``
            unit: The unit to write to

        Raises:
            ModbusResponseError: If reading the slave failed
            VariableNotFound:
                If ``var`` is not mapped by the holding register layout
                of ``unit``
            MissingSubLayoutError:
                If there is no memory layout defined for holding
                registers
        """
        await self.write_holding_registers({var: value}, unit)

    async def write_coils(
        self, values: dict[str, ValueType], unit: KeyType = DEFAULT_SLAVE
    ) -> None:
        """Write ``values`` to coil memory of ``unit``.

        Args:
            values:
                A ``dict`` mapping variable names to the values to write
            unit: The unit to write to

        Raises:
            ModbusResponseError: If reading the slave failed
            VariableNotFound:
                If one or more keys of ``values`` are not mapped by
                the coil layout of ``unit``
            MissingSubLayoutError:
                If there is no memory layout defined for coils

        This method will group values which occur back-to-back in memory
        into payload chunks in order to minimize the amount of write
        requests to the server.
        """
        slave_layout = self._layout.get_coil_layout(unit)
        payloads = slave_layout.build_payload(values)
        for payload in payloads:
            response = await self._protocol.write_coils(
                payload.address, payload.values, unit=unit
            )
            if response.function_code != WriteMultipleCoilsResponse.function_code:
                raise ModbusResponseError(response)

    async def write_coil(
        self, var: str, value: ValueType, unit: KeyType = DEFAULT_SLAVE
    ) -> None:
        """Set ``var`` in coil memory to ``value``

        Args:
            var: The variable to modify
            value: The new value of ``var``
            unit: The unit to write to

        Raises:
            ModbusResponseError: If reading the slave failed
            VariableNotFound:
                If ``var`` is not mapped by the coil layout of ``unit``
            MissingSubLayoutError:
                If there is no memory layout defined for coils
        """
        await self.write_coils({var: value}, unit)

    async def read_coils(
        self, variables: Optional[Iterable[str]] = None, unit: KeyType = DEFAULT_SLAVE
    ) -> dict[str, ValueTypes]:
        """Read ``variables`` from coils of ``unit``.

        Args:
            variables: The variables to read (all by default)
            unit: The unit to read from

        Returns:
            A ``dict`` mapping the queried variable's names to their
            values

        Raises:
            ModbusResponseError: If reading the slave failed
            VariableNotFound:
                If one or more items of ``variables`` are not mapped by
                the coil layout
            MissingSubLayoutError:
                If there is no memory layout defined for coils

        Note that this method will always execute a complete readout of
        the slave's coil layout's range.
        """
        slave_layout = self._layout.get_coil_layout(unit)
        response = await self._protocol.read_coils(
            slave_layout.address, slave_layout.size, unit=unit
        )
        if response.function_code != ReadCoilsResponse.function_code:
            raise ModbusResponseError(response)
        return slave_layout.decode_coils(response.bits, variables)

    async def read_coil(self, var: str, unit: KeyType = DEFAULT_SLAVE) -> list[bool]:
        """Read ``var`` from coil memory of ``unit``.

        Args:
            var: The variable to read
            unit: The unit to read from

        Returns: The value of the variable

        Raises:
            ModbusResponseError: If reading the slave failed
            VariableNotFound:
                If ``var`` is not mapped by the coil layout of ``unit``
            MissingSubLayoutError:
                If there is no memory layout defined for coils

        Note that this method will always execute a complete readout of
        the slave's coil layout's range.
        """
        d = await self.read_coils(unit=unit)
        return d[var]

    async def read_discrete_inputs(
        self, variables: Optional[Iterable[str]] = None, unit: KeyType = DEFAULT_SLAVE
    ) -> dict[str, list[bool]]:
        """Read ``variables`` from discrete inputs of ``unit``.

        Args:
            variables: The variables to read (all by default)
            unit: The unit to read from

        Returns:
            A ``dict`` mapping the queried variable's names to their
            values

        Raises:
            ModbusResponseError: If reading the slave failed
            VariableNotFound:
                If one or more items of ``variables`` are not mapped by
                the discrete input layout
            MissingSubLayoutError:
                If there is no memory layout defined for discrete inputs

        Note that this method will always execute a complete readout of
        the slave's discrete input layout's range.
        """
        slave_layout = self._layout.get_discrete_input_layout(unit)
        response = await self._protocol.read_discrete_inputs(
            slave_layout.address, slave_layout.size, unit=unit
        )
        if response.function_code != ReadDiscreteInputsResponse.function_code:
            raise ModbusResponseError(response)
        return slave_layout.decode_coils(response.bits, variables)

    async def read_discrete_input(
        self, variable: str, unit: KeyType = DEFAULT_SLAVE
    ) -> list[bool]:
        """Read ``var`` from discrete input memory of ``unit``.

        Args:
            var: The variable to read
            unit: The unit to read from

        Returns: The value of the variable

        Raises:
            ModbusResponseError: If reading the slave failed
            VariableNotFound:
                If ``var`` is not mapped by the discrete input register
                layout of ``unit``
            MissingSubLayoutError:
                If there is no memory layout defined for discrete inputs

        Note that this method will always execute a complete readout of
        the slave's discrete input layout's range.
        """
        d = await self.read_discrete_inputs(unit=unit)
        return d[variable]

    @property
    def protocol(self) -> pymodbus.client.asynchronous.async_io.ModbusClientProtocol:
        return self._protocol


class Server:
    def __init__(self, server) -> None:
        """Wraps a ``pymodbus`` server.

        Args:
            server: The ``pymodbus`` server to wrap
        """
        self._server = server

    def start(self, defer_server: bool = False):
        """Start the server.

        Args:
            defer_server: Set to ``True`` if server is already running
        """
        if not defer_server:
            asyncio.create_task(self._server.serve_forever())

    async def stop(self):
        if self._server.server is None:
            raise NoServerError("Attempting to stop server with NoneType server field")
        self._server.server_close()


class Client:
    def __init__(
        self,
        loop,
        client: ModbusClient,
        layout: ServerContextLayout,
    ) -> None:
        """Stores a modbus client and the layouted protocol.

        Args:
            loop: The ``asyncio`` event loop that ``client`` runs on
            client: The modbus client to store
            layout: The layout of the datastore that the client operates on

        This is purely a utility class which keeps the event loop and
        the client object safe from garbage collection while allowing
        access to the protocol (plus layout) for writing and reading.
        """
        assert client.protocol
        self._loop = loop  # pymodbus doesn't save this loop, so we must protect it from garbage collection!
        self._client = client
        self._protocol = Protocol(client.protocol, layout)

    @property
    def protocol(self) -> Protocol:
        return self._protocol
