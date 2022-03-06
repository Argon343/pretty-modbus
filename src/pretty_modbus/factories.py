# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Module with non_async versions of the
``pymodbus.server.async_io.Start*`` factories. Based on the code of
``pymodbus.server.async_io``.

Only call the factories when an event loop is already running.

"""


# TODO All factories must be called when an event loop is already
# running. So it only makes sense to actually put them into coroutines?

from __future__ import annotations

import asyncio

from pymodbus.server.async_io import (
    ModbusTcpServer,
    ModbusTlsServer,
    ModbusUdpServer,
    ModbusSerialServer,
)
from pymodbus.datastore.context import ModbusServerContext
from pymodbus.transaction import ModbusAsciiFramer


class ServerCloseFailure(Exception):
    pass


class SerialServer(ModbusSerialServer):
    def __init__(self, *args, **kwargs) -> None:
        """Implementation of ``ModbusSerialServer`` from pymodbus
        that allows interrupting the ``serve_forever`` method.

        All arguments are as in the parent class ``ModbusSerialServer``.

        Note that interrupting the ``serve_forever`` method has nothing
        to do with actually stopping the underlying serial server.
        """
        super().__init__(*args, **kwargs)
        self._event = asyncio.Event()

    async def serve_forever(self):
        await self.start()  # This is unique to the serial server
        await self._event.wait()

    def server_close(self):
        if self.transport is None:
            raise ServerCloseFailure("Failed to close server; transport is `None`")
        self.transport.close()
        self.transport = None
        self.protocol = None
        self._event.set()


def create_tcp_server(
    context: Optional[ModbusServerContext] = None,
    identity=None,
    address=None,
    custom_functions: Optional[Iterable] = None,
    **kwargs,
) -> None:
    """Create an async Modbus TCP server.

    This is a non-async version of
    ``pymodbus.server.async_io.StartTcpServer``. The function is the
    same, except that the ``defer_start`` parameter is not used and the
    server is not started by default. See pymodbus docs for details.
    """
    server = ModbusTcpServer(
        context=context, identity=identity, address=address, **kwargs
    )
    _register_custom_functions(server, custom_functions)
    return server


def create_tls_server(
    context: Optional[ModbusServerContext] = None,
    identity=None,
    address=None,
    sslctx=None,
    certfile=None,
    keyfile=None,
    allow_reuse_address=False,
    allow_reuse_port=False,
    custom_functions: Optional[Iterable] = None,
    **kwargs,
) -> None:
    server = ModbusTlsServer(
        context=context,
        identity=identity,
        address=address,
        sslctx=sslctx,
        certfile=certfile,
        keyfile=keyfile,
        allow_reuse_address=allow_reuse_address,
        allow_reuse_port=allow_reuse_port,
        **kwargs,
    )
    _register_custom_functions(server, custom_functions)
    return server


def create_udp_server(
    context: Optional[ModbusServerContext] = None,
    identity=None,
    address=None,
    custom_functions: Optional[Iterable] = None,
    **kwargs,
) -> None:
    server = ModbusUdpServer(
        context=context, identity=identity, address=address, **kwargs
    )
    _register_custom_functions(server, custom_functions)
    return server


def create_serial_server(
    context: Optional[ModbusServerContext] = None,
    identity=None,
    custom_functions: Optional[Iterable] = None,
    **kwargs,
) -> None:
    # This is due to the unfortunatly inconsistent double booking of the
    # default values for ``framer``.
    framer = kwargs.pop("framer", ModbusAsciiFramer)
    # Note that we use our own class instead of the pymodbus class.
    server = SerialServer(context=context, framer=framer, identity=identity, **kwargs)
    _register_custom_functions(server, custom_functions)
    return server


def _register_custom_functions(
    server: Union[
        ModbusTcpServer, ModbusTlsServer, ModbusUdpServer, ModbusSerialServer
    ],
    custom_functions: Optional[Iterable],
) -> None:
    if custom_functions is None:
        return
    for f in custom_functions:
        server.decoder.register(f)
