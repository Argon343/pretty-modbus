# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

import asyncio
import time
import pytest

from pymodbus.server.async_io import StartTcpServer

from pretty_modbus import async_io
from pretty_modbus.context import ServerContext
from pretty_modbus.layout import ServerContextLayout, SlaveContextLayout
from pretty_modbus import registers
from pretty_modbus import coils
from pretty_modbus.daemon import (
    AsyncDaemon,
    NegativePeriodError,
    DaemonThread,
)


@pytest.fixture
def context(modbus_context, server_context_layout):
    return ServerContext(modbus_context, server_context_layout)


@pytest.fixture
def server_context_layout():
    return ServerContextLayout(
        {
            0: SlaveContextLayout(
                holding_registers=registers.RegisterLayout(
                    [
                        registers.Number("x", "i32", address=19),
                        registers.Number("y", "i32", address=37),
                    ],
                ),
                discrete_inputs=coils.CoilLayout([coils.Variable("result", address=3)]),
            ),
        }
    )


@pytest.fixture
def protocol(client, server_context_layout):
    return async_io.Protocol(client.protocol, server_context_layout)


def job(context):
    """Compare holding register variables ``x`` and ``y`` and write
    result to discrete inputs.
    """
    values = context.get_holding_registers()
    x = values["x"]
    y = values["y"]
    result = x > y
    context.set_discrete_inputs({"result": result})


@pytest.fixture
async def daemon(context):
    daemon = AsyncDaemon(job, 0.01)
    daemon.serve(context)
    yield daemon
    task = daemon.stop()
    await task


@pytest.fixture
def daemon_thread(context):
    daemon = DaemonThread(job, 0.01)
    daemon.serve(context)
    yield
    daemon.stop(timeout=3.33)


class TestAsyncDaemon:
    def test_init_raises_on_negative_period(self):
        with pytest.raises(NegativePeriodError):
            AsyncDaemon(lambda: None, -1.2)

    @pytest.mark.asyncio
    async def test_daemon_raises_error(self):
        def error():
            raise ValueError()

        daemon = AsyncDaemon(error, 0.01)
        daemon.serve()
        await asyncio.sleep(0.1)
        with pytest.raises(ValueError):
            await daemon.stop()

    @pytest.mark.parametrize(
        "x, y, expected",
        [
            (3, 5, False),
            (7, 7, False),
            (9, 4, True),
        ],
    )
    @pytest.mark.asyncio
    async def test_output_is_correct_without_client(
        self, daemon, context, x, y, expected
    ):
        await context.set_holding_registers_coro({"x": x, "y": y})
        await asyncio.sleep(0.1)
        result = await context.get_discrete_inputs_coro(variables={"result"})
        assert result == {"result": expected}

    # Note that there is no test ``test_output_is_correct_with_client``.
    # This is because the client blocks our event loop and preventst the
    # daemon from doing its job!


class TestDaemonThread:
    def test_init_raises_on_negative_period(self):
        with pytest.raises(NegativePeriodError):
            DaemonThread(lambda: None, -1.2)

    def test_daemon_raises_error(self):
        def error():
            raise ValueError()

        daemon = DaemonThread(error, 0.01)
        daemon.serve()
        time.sleep(0.1)
        with pytest.raises(ValueError):
            daemon.stop()

    @pytest.mark.parametrize(
        "x, y, expected",
        [
            (3, 5, False),
            (9, 4, True),
            (7, 7, False),
        ],
    )
    def test_daemon_out_is_correct_without_client(
        self, daemon_thread, context, x, y, expected
    ):
        context.set_holding_registers({"x": x, "y": y})
        time.sleep(0.1)
        result = context.get_discrete_inputs(variables={"result"})
        assert result == {"result": expected}
