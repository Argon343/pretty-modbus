# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

import asyncio

from copy import deepcopy

from pymodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusSlaveContext,
    ModbusServerContext,
)
from pymodbus.server.async_io import StartTcpServer

PORT = 5020
LOCALHOST = "0.0.0.0"


async def main():
    modbus_slave_context = ModbusSlaveContext(
        di=ModbusSequentialDataBlock(0, [0] * 100),
        co=ModbusSequentialDataBlock(0, [0] * 100),
        hr=ModbusSequentialDataBlock(0, [0] * 100),
        ir=ModbusSequentialDataBlock(0, [0] * 100),
        zero_mode=True,
    )
    modbus_server_context = ModbusServerContext(
        slaves={
            0: deepcopy(modbus_slave_context),
            1: deepcopy(modbus_slave_context),
            0: deepcopy(modbus_slave_context),
        },
        single=False,
    )
    await StartTcpServer(
        modbus_server_context,
        address=(LOCALHOST, PORT),
        defer_start=False,
    )


if __name__ == "__main__":
    asyncio.run(main())
