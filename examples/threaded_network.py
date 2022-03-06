# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

import time

from pymodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusSlaveContext,
    ModbusServerContext,
)
from pymodbus.server.sync import StartTcpServer
from pymodbus.client.sync import ModbusTcpClient

from pretty_modbus.context import ServerContext
from pretty_modbus.threaded import Client, Daemon, Server
from pretty_modbus.layout import SlaveContextLayout, ServerContextLayout
from pretty_modbus.registers import RegisterLayout, Number
from pretty_modbus.coils import CoilLayout, Variable

PORT = 5020
LOCALHOST = "0.0.0.0"
GRACE = 0.1


def job(context):
    """Check if ``x > y`` and write result into ``result``."""
    hr = context.get_holding_registers()
    result = hr["x"] > hr["y"]
    context.set_discrete_inputs({"result": result})


def main():
    modbus_slave_context = ModbusSlaveContext(
        hr=ModbusSequentialDataBlock(0, [0] * 100),
        di=ModbusSequentialDataBlock(0, [0] * 100),
        zero_mode=True,
    )
    modbus_server_context = ModbusServerContext(
        slaves={0: modbus_slave_context}, single=False
    )

    slave_context_layout = SlaveContextLayout(
        holding_registers=RegisterLayout(
            variables=[
                Number(name="x", type="i16", address=2),
                Number(name="y", type="i16"),
            ],
        ),
        discrete_inputs=CoilLayout(
            variables=[
                Variable(name="result"),  # size=1, address=0
            ],
        ),
    )
    server_context_layout = ServerContextLayout({0: slave_context_layout})

    daemon = Daemon(job, 0.01)
    server = Server(
        StartTcpServer,
        daemons=[daemon],
        layout=server_context_layout,
        context=modbus_server_context,
        address=(LOCALHOST, 5020),
    )
    client = Client(
        factory=ModbusTcpClient,
        layout=server_context_layout,
        address=LOCALHOST,
        port=PORT,
    )

    server.start()
    time.sleep(GRACE)
    print("Server started...")
    client.start()
    time.sleep(GRACE)
    print("Client started...")

    hr = client.read_holding_registers()
    assert hr == {"x": 0, "y": 0}
    di = client.read_discrete_inputs()
    assert di == {"result": False}

    client.write_holding_registers({"x": 5, "y": 4})
    time.sleep(GRACE)

    hr = client.read_holding_registers()
    assert hr == {"x": 5, "y": 4}
    di = client.read_discrete_inputs()
    assert di == {"result": True}

    client.write_holding_registers({"x": 4, "y": 5})
    time.sleep(GRACE)

    hr = client.read_holding_registers()
    assert hr == {"x": 4, "y": 5}
    di = client.read_discrete_inputs()
    assert di == {"result": False}

    print("All ok!")

    client.stop(GRACE)
    print("Client closed!")

    server.stop()
    print("Server closed!")


if __name__ == "__main__":
    main()
