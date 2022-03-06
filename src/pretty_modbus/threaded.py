# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import dataclasses
import multiprocessing
import threading
import queue
import time

from pymodbus.register_read_message import (
    ReadInputRegistersResponse,
    ReadHoldingRegistersResponse,
)
from pymodbus.bit_read_message import ReadCoilsResponse, ReadDiscreteInputsResponse
from pymodbus.bit_write_message import WriteMultipleCoilsResponse
from pymodbus.register_write_message import WriteMultipleRegistersResponse

from pretty_modbus.const import DEFAULT_SLAVE
from pretty_modbus.exceptions import (
    ModbusResponseError,
    NotConnectedError,
    NegativePeriodError,
)
from pretty_modbus.context import ServerContext

CONNECTED = "__pretty_modbus__connected__"
DISCONNECT = "__pretty_modbus__disconnect__"


@dataclasses.dataclass
class UnhandledException:
    error: Exception


class Daemon:
    def __init__(self, job: Callable, period: float) -> None:
        """One-shot daemon which periodically executes a job.

        Args:
            job: The job to execute
            period: The period (in seconds)
        """
        if period < 0:
            raise NegativePeriodError(
                f"Expected non-negative period for daemon. Received: {period}."
            )
        self._job = job
        self._period = period
        self._thread: Optional[threading.Thread] = None

    def serve(self, *args, **kwargs) -> None:
        self._thread = threading.Thread(
            target=self._serve, args=args, kwargs=kwargs, daemon=True
        )
        self._thread.start()

    def _serve(self, *args, **kwargs) -> None:
        while True:
            start_time = time.perf_counter()
            self._job(*args, **kwargs)
            diff = time.perf_counter() - start_time
            wait = max(0, self._period - diff)
            time.sleep(wait)


class Server:
    def __init__(
        self,
        factory,
        daemons: list[Daemon] = None,
        layout: Optional[ServerContextLayout] = None,
        **kwargs,
    ) -> None:
        """Modbus server running in a child process.

        Args:
            factory: The pymodbus factory for creating the server
            daemons:
                A list of daemons to run on the server's context, if available
            layout: A layout to apply to the server's context
            kwargs: Keyworded arguments passed to the factory

        The point of using a child process is to make the server
        non-blocking. The daemon is part of the class, as we need to
        make sure that the daemon operates on the same context as the
        server. This is not possible if they run in separate processes.
        """
        if daemons:
            assert layout is not None
            assert "context" in kwargs
        daemons = daemons or []
        self._process = multiprocessing.Process(
            target=_server_main, args=(factory, daemons, layout), kwargs=kwargs
        )

    def __del__(self):
        # Just in case the user forgot to clean up the server, this
        # might prevent some unnecessary blocking.
        self.stop()

    def start(self) -> None:
        """Start the server."""
        self._process.start()

    def stop(self):
        """Stop the server.

        Note that this is a graceless close. pymodbus leaves us no other
        option but to kill the containing process.
        """
        self._process.terminate()
        self._process.join()


def _server_main(factory, daemons, layout, **kwargs) -> None:
    for daemon in daemons:
        context = kwargs["context"]
        server_context = ServerContext(context, layout)
        daemon.serve(server_context)
    factory(**kwargs)


class RpcCall:
    def __init__(self, _fn: str, *args, **kwargs) -> None:
        self._fn = _fn
        self._args = args
        self._kwargs = kwargs

    def execute(self, obj):
        f = getattr(obj, self._fn)
        return f(*self._args, **self._kwargs)


def _client_main(
    factory,
    response_queue: queue.Queue,
    command_queue: queue.Queue,
    *args,
    **kwargs,
) -> None:
    try:
        client = factory(*args, **kwargs)
        client.connect()
        response_queue.put(CONNECTED)
        while True:
            rpc = command_queue.get()
            if rpc == DISCONNECT:
                response_queue.put(DISCONNECT)
                break
            result = rpc.execute(client)
            response_queue.put(result)
    except Exception as e:
        response_queue.put(UnhandledException(e))


class Client:
    def __init__(self, factory, layout: ServerContextLayout, *args, **kwargs) -> None:
        self._layout = layout
        self._response_queue = queue.Queue()
        self._command_queue = queue.Queue()
        self._thread = threading.Thread(
            target=_client_main,
            args=(
                factory,
                self._response_queue,
                self._command_queue,
                *args,
            ),
            kwargs=kwargs,
            daemon=True,
        )
        self._active = False

    def start(self, timeout: Optional[float] = None) -> None:
        self._thread.start()
        assert self._response_queue.get(timeout=timeout) == CONNECTED
        self._active = True

    def stop(self, timeout: Optional[float] = None) -> None:
        # Check for errors before joining
        self._command_queue.put(DISCONNECT)
        assert self._response_queue.get() == DISCONNECT
        self._thread.join(timeout=timeout)
        if self._thread.is_alive():
            raise TimeoutError()

    def _execute(self, _fn: str, *args, **kwargs):
        if not self._active:
            raise NotConnectedError()
        rpc = RpcCall(_fn, *args, **kwargs)
        self._command_queue.put(rpc)
        result = self._response_queue.get()
        if isinstance(result, UnhandledException):
            raise result.error
        return result

    def write(self, var: str, value: ValueType) -> None:
        # FIXME This is not a good solution.
        unit, type_ = self._layout.find(var)
        assert type_ in {"holding_registers", "coils"}
        dispatch = "write_" + type_[:-1]
        fn = getattr(self, dispatch)
        fn(var, value, unit)

    def read_input_registers(
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
        response = self._execute(
            "read_input_registers", slave_layout.address, slave_layout.size, unit=unit
        )
        if response.function_code != ReadInputRegistersResponse.function_code:
            raise ModbusResponseError(response)
        return slave_layout.decode_registers(response.registers, variables)

    def read_input_register(self, var: str, unit: KeyType = DEFAULT_SLAVE) -> ValueType:
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
        return self.read_input_registers(unit=unit)[var]

    def read_holding_registers(
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
        response = self._execute(
            "read_holding_registers", slave_layout.address, slave_layout.size, unit=unit
        )
        if response.function_code != ReadHoldingRegistersResponse.function_code:
            raise ModbusResponseError(response)
        return slave_layout.decode_registers(response.registers, variables)

    def read_holding_register(
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
        return self.read_holding_registers(unit=unit)[var]

    def write_holding_registers(
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
            response = self._execute(
                "write_registers",
                payload.address,
                payload.values,
                skip_encode=True,
                unit=unit,
            )
            if response.function_code != WriteMultipleRegistersResponse.function_code:
                raise ModbusResponseError(response)

    def write_holding_register(
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
        self.write_holding_registers({var: value}, unit)

    def write_coils(
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
            response = self._execute(
                "write_coils", payload.address, payload.values, unit=unit
            )
            if response.function_code != WriteMultipleCoilsResponse.function_code:
                raise ModbusResponseError(response)

    def write_coil(
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
        self.write_coils({var: value}, unit)

    def read_coils(
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
        response = self._execute(
            "read_coils", slave_layout.address, slave_layout.size, unit=unit
        )
        if response.function_code != ReadCoilsResponse.function_code:
            raise ModbusResponseError(response)
        return slave_layout.decode_coils(response.bits, variables)

    def read_coil(self, var: str, unit: KeyType = DEFAULT_SLAVE) -> list[bool]:
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
        return self.read_coils(unit=unit)[var]

    def read_discrete_inputs(
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
        response = self._execute(
            "read_discrete_inputs", slave_layout.address, slave_layout.size, unit=unit
        )
        if response.function_code != ReadDiscreteInputsResponse.function_code:
            raise ModbusResponseError(response)
        return slave_layout.decode_coils(response.bits, variables)

    def read_discrete_input(
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
        return self.read_discrete_inputs(unit=unit)[variable]
