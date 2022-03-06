# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

import asyncio
import threading
import time
import warnings

from pymodbus.client.sync import ModbusTcpClient
import pymodbus.datastore
import pymodbus.server.async_io
import pymodbus.client.asynchronous.tcp
import pymodbus.client.asynchronous.schedulers
import pytest

from pretty_modbus import async_io
from pretty_modbus.factories import create_tcp_server
from pretty_modbus import threaded


@pytest.fixture
def host():
    return "0.0.0.0"


@pytest.fixture
def port():
    return 5020


@pytest.fixture
def client(event_loop, host, port):
    _, client = pymodbus.client.asynchronous.tcp.AsyncModbusTCPClient(
        pymodbus.client.asynchronous.schedulers.ASYNC_IO,
        # host=host,
        port=port,
        loop=event_loop,
    )
    assert client.protocol
    return client


@pytest.fixture
def threaded_client(client, server_context_layout, port):
    client = threaded.Client(
        ModbusTcpClient, server_context_layout, address="0.0.0.0", port=port
    )
    client.start()
    yield client
    client.stop(timeout=3.33)


@pytest.fixture
def modbus_context():
    return pymodbus.datastore.ModbusServerContext(
        slaves={
            # Blank datastore for writing & reading:
            0: pymodbus.datastore.ModbusSlaveContext(
                hr=pymodbus.datastore.ModbusSequentialDataBlock(0, [0] * 100),
                ir=pymodbus.datastore.ModbusSequentialDataBlock(-1, [0] * 100),
                co=pymodbus.datastore.ModbusSequentialDataBlock(0, [0] * 100),
                di=pymodbus.datastore.ModbusSequentialDataBlock(0, [0] * 100),
                zero_mode=True,
            ),
            # For testing the `unit` parameter:
            1: pymodbus.datastore.ModbusSlaveContext(
                hr=pymodbus.datastore.ModbusSequentialDataBlock(0, [0] * 100),
                ir=pymodbus.datastore.ModbusSequentialDataBlock(0, list(range(100))),
                co=pymodbus.datastore.ModbusSequentialDataBlock(0, [0] * 100),
                di=pymodbus.datastore.ModbusSequentialDataBlock(
                    0, [0, 0, 1, 0, 0, 1] + [0] * 94
                ),
                zero_mode=True,
            ),
            # Context without layout:
            3: pymodbus.datastore.ModbusSlaveContext(
                hr=pymodbus.datastore.ModbusSequentialDataBlock(0, [0] * 100),
                ir=pymodbus.datastore.ModbusSequentialDataBlock(0, list(range(100))),
                co=pymodbus.datastore.ModbusSequentialDataBlock(0, [0] * 100),
                di=pymodbus.datastore.ModbusSequentialDataBlock(
                    0, [0, 0, 1, 0, 0, 1] + [0] * 94
                ),
                zero_mode=True,
            ),
        },
        single=False,
    )
