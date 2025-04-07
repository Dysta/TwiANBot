from __future__ import annotations

import inspect
import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

import tweepy
from loguru import logger

from .task import Task

_client = None


def get_client_instance():
    """
    Retrieve a singleton instance of the Client.

    If the instance does not exist, it is created and returned. Subsequent calls
    will return the same instance.

    :return: A singleton instance of the Client.
    """
    global _client
    if _client is None:
        _client = Client()
    return _client


@dataclass(init=False, order=False, eq=False, unsafe_hash=False)
class Client:
    tasks: List[Task]
    listeners: Dict[str, List[Callable[..., Any]]]
    tw_client: tweepy.Client
    data: Dict[Any, Any]

    def __init__(self) -> None:
        """
        Initialize the client.

        The twitter client is initialized with the credentials from the environment variables
        API_KEY, API_SECRET, ACCESS_TOKEN, and ACCESS_SECRET. If any of these variables
        are not set, the client will not be able to perform any actions.

        The client is also initialized with an empty list of tasks, an empty dictionary
        of listeners, and an empty dictionary of data.

        Its recommended to not instanciate yourself a client and use the get_client_instance()
        function instead to be able to reuse the same client and attach listeners.
        """
        self.tw_client = tweepy.Client(
            consumer_key=os.getenv("API_KEY"),
            consumer_secret=os.getenv("API_SECRET"),
            access_token=os.getenv("ACCESS_TOKEN"),
            access_token_secret=os.getenv("ACCESS_SECRET"),
            wait_on_rate_limit=True,
        )
        self.tasks = []
        self.listeners = {}
        self.data = {}

    def add_task(self, task: Task, *args, **kwargs) -> None:
        """
        Add a task to the list of tasks and start it.

        :param task: The task to be added and started.
        :param args: Arguments to be passed to the task when it is started.
        :param kwargs: Keyword arguments to be passed to the task when it is started.
        """
        self.tasks.append(task)
        task.start(*args, **kwargs)

    def stop(self) -> None:
        """
        Stop the bot.

        This method will stop all the tasks that are currently running, and prevent any new tasks from being added.
        It is recommended to call this method when the bot is shutting down, to prevent any tasks from attempting to
        run after the bot has been stopped.

        :return: None
        """
        for task in self.tasks:
            task.stop()

        self.tasks = []

    def add_listener(
        self,
        callback: Callable[..., Any],
        event: Optional[str] = None,
    ) -> None:
        """
        Add a listener to the list of listeners.
        A listener is a special task that will be triggered when an event is dispatched.
        The task is instantly fired and will run once.

        :param callback: The listener to be added. Must be an asynchronous function.
        :param event: The event to which the listener is listening. If not specified, it is
            assumed to be the name of the callback prefixed with "on_".
        """
        assert inspect.iscoroutinefunction(callback)

        event = callback.__name__ if not event else "on_" + event

        if event not in self.listeners:
            self.listeners[event] = [callback]
        else:
            self.listeners[event].append(callback)

    def remove_listener(
        self,
        callback: Callable[..., Any],
        event: Optional[str] = None,
    ) -> None:
        """
        Remove a listener from the list of listeners.

        :param callback: The listener to be removed.
        :param event: The event to which the listener is listening. If not specified, it is
            assumed to be the name of the callback prefixed with "on_".
        """
        assert inspect.iscoroutinefunction(callback)

        if event in self.listeners:
            try:
                self.listeners[event].remove(callback)
            except ValueError:
                pass

    def dispatch(self, event: str, *args, **kwargs) -> None:
        """
        Dispatch an event to all listeners registered for that event.
        A listener is a special task that will be triggered instantly and will run once.

        :param event: The event to be dispatched.
        :param args: Arguments to be passed to the listeners.
        :param kwargs: Keyword arguments to be passed to the listeners.
        """
        logger.debug(f"Dispatching event {event}")
        event = "on_" + event if not event.startswith("on_") else event

        listeners = self.listeners.get(event, [])
        for callback in listeners:
            Task(callback, 0, 1).start(*args, **kwargs)

    def listen(self, event: Optional[str] = None) -> Callable[..., Any]:
        """
        A decorator to add a listener to the list of listeners.

        :param event: The event to which the listener is listening. If not specified, it is
            assumed to be the name of the callback prefixed with "on_".
        :return: The same function that was passed as an argument, but with the listener added.
        """

        def decorator(callback: Callable[..., Any]) -> Callable[..., Any]:
            assert inspect.iscoroutinefunction(callback)

            self.add_listener(callback, event)
            return callback

        return decorator
