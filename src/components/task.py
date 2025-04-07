from __future__ import annotations

import asyncio
import contextlib
import inspect
import random
from typing import Any, Awaitable, Callable

from loguru import logger


class Task:
    def __init__(self, callback: Callable[[], Awaitable[None]], delay: float, count: int) -> None:
        """
        Initialize a Task instance. Avoid using this directly, use the loop decorator instead.

        :param callback: An asynchronous callable that will be run in a loop.
        :param delay: The delay in seconds between each execution of the callback.
        """
        self.callback = callback
        self.delay = delay
        self.count = count
        self._task: asyncio.Task[None] | None = None

        self._internal_count = 1

    def __await__(self):
        """
        Implements the awaitable protocol to allow awaiting on a task. If the task is running, this
        method will wait for the task to finish and return its result. If the task is not running,
        this method will return None.

        :return: The result of the task, or None if the task is not running.
        """
        if self._task:
            with contextlib.suppress(asyncio.CancelledError):
                yield from self._task

    def start(self, *args, **kwargs):
        """
        Start the loop.

        This method will start the loop if it is not already running. If the loop is already running,
        a RuntimeError will be raised.

        :param args: Arguments to be passed to the callback.
        :param kwargs: Keyword arguments to be passed to the callback.
        :raise RuntimeError: If the loop is already running.
        """
        if self._task:
            raise RuntimeError("loop is already running")
        self._task = asyncio.create_task(
            self._run(*args, **kwargs),
            name=f"{self.callback.__name__}-{random.randint(1, 999):03d}",
        )

    def stop(self):
        """
        Stop the loop.

        This method will stop the loop if it is running. If the loop is not running,
        a no-op is performed.
        """
        if self._task:
            self._task.cancel()
            self._task = None

    async def _run(self, *args, **kwargs):
        """
        Run the task loop.

        This method is an internal implementation detail of the Task class.

        It runs the callback in a loop until the task is stopped or the specified number of
        iterations is reached.

        :param args: Arguments to be passed to the callback.
        :param kwargs: Keyword arguments to be passed to the callback.
        """
        while True:
            try:
                await self.callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Task {self._task.get_name()} failed: {e}")

            if self.count != -1 and self._internal_count >= self.count:
                break

            await asyncio.sleep(self.delay)
            self._internal_count += 1

        self.stop()


def loop(*, hours: int = 0, minutes: int = 0, seconds: int = 0, count: int = -1):
    """
    Decorator to create a looping task.

    This decorator is used to create a Task that repeatedly executes an asynchronous callable
    at specified intervals. The interval is defined by the cumulative time of hours, minutes,
    and seconds. The task can be limited to a specific number of executions.

    :param hours: The number of hours to wait between each execution.
    :param minutes: The number of minutes to wait between each execution.
    :param seconds: The number of seconds to wait between each execution.
    :param count: The number of times to execute the task. If set to -1, the task will run indefinitely.
    :return: A Task object that can be started and stopped.
    :raises AssertionError: If the callback is not an asynchronous function or if the delay is non-positive.
    """

    def wrapper(callback: Callable[[Any], Awaitable[None]]):
        assert inspect.iscoroutinefunction(callback)

        delay = hours * 3600 + minutes * 60 + seconds
        assert delay > 0

        return Task(callback, delay, count)

    return wrapper
