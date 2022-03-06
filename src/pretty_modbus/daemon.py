# SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import asyncio
import queue
import threading
import time

from pretty_modbus.exceptions import ModbusBackendException


class NegativePeriodError(ModbusBackendException):
    pass


class AsyncDaemon:
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
        self._event = asyncio.Event()
        self._task = None

    def serve(self, *args, **kwargs) -> None:
        """Execute the daemon on the current event loop.

        Args:
            *args: The args to pass to the job
            **kwargs: The kwargs to pass to the job
        """
        self._task = asyncio.create_task(
            self._serve_coro(*args, **kwargs), name="daemon"
        )

    async def _serve_coro(self, *args, **kwargs) -> None:
        while not self._event.is_set():
            start = time.perf_counter()
            self._job(*args, **kwargs)
            diff = start - time.perf_counter()
            wait = max(self._period - diff, 0.0)
            await asyncio.sleep(wait)

    def stop(self) -> asyncio.Task:
        """Gracefully stop the daemon.

        Returns:
            The cancelled task.
        """
        self._event.set()
        return self._task

    def cancel(self) -> asyncio.Task:
        """Cancel the running job.

        Returns:
            The cancelled task.
        """
        self._task.cancel()
        return self._task


class DaemonThread:
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
        self._event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._queue = queue.Queue()

    def serve(self, *args, **kwargs) -> None:
        self._thread = threading.Thread(
            target=self._serve, args=args, kwargs=kwargs, daemon=True
        )
        self._thread.start()

    def stop(self, timeout: Optional[float] = None) -> None:
        try:
            raise self._queue.get_nowait()
        except queue.Empty:
            pass
        self._event.set()
        self._thread.join(timeout=timeout)

    def _serve(self, *args, **kwargs) -> None:
        try:
            while not self._event.is_set():
                start_time = time.perf_counter()
                self._job(*args, **kwargs)
                diff = time.perf_counter() - start_time
                wait = max(0, self._period - diff)
                time.sleep(wait)
        except Exception as e:
            self._queue.put(e)
