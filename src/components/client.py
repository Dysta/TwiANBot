from __future__ import annotations

import inspect
import json
import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

import aiofiles
import tweepy
from loguru import logger

from .task import Task

_client = None


def instance():
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


def anon_key(key: str) -> str:
    """
    Anonymize a key by replacing it with asterisks.

    :param key: The key to be anonymized.
    :return: The anonymized key.
    """
    return key[:4] + "*" * 12 + key[-4:]


@dataclass(init=False, order=False, eq=False, unsafe_hash=False)
class Client:
    tasks: List[Task]
    listeners: Dict[str, List[Callable[..., Any]]]
    tw_client: tweepy.Client
    tw_api_V1: tweepy.API
    data: Dict[Any, Any]

    def __init__(self) -> None:
        """
        Initialize the client.

        The twitter client is initialized with the credentials from the environment variables
        API_KEY, API_SECRET, ACCESS_TOKEN, and ACCESS_SECRET. If any of these variables
        are not set, the client will not be able to perform any actions.

        The client is also initialized with an empty dictionary
        of listeners, and an empty dictionary of data.

        Its recommended to not instanciate yourself a client and use the instance()
        function instead to be able to reuse the same client and attach listeners.
        """
        api_key = os.getenv("API_KEY")
        api_secret = os.getenv("API_SECRET")
        access_token = os.getenv("ACCESS_TOKEN")
        access_secret = os.getenv("ACCESS_SECRET")

        if not api_key or not api_secret or not access_token or not access_secret:
            raise ValueError(
                "Twitter API credentials are not set. Please set the environment variables "
                "API_KEY, API_SECRET, ACCESS_TOKEN, and ACCESS_SECRET."
            )

        logger.debug(f"API_KEY: {anon_key(api_key)}")
        logger.debug(f"API_SECRET: {anon_key(api_secret)}")
        logger.debug(f"ACCESS_TOKEN: {anon_key(access_token)}")
        logger.debug(f"ACCESS_SECRET: {anon_key(access_secret)}")

        self.tw_client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_secret,
            wait_on_rate_limit=True,
        )
        self.tw_api_V1 = tweepy.API(
            tweepy.OAuth1UserHandler(
                consumer_key=api_key,
                consumer_secret=api_secret,
                access_token=access_token,
                access_token_secret=access_secret,
            )
        )
        self.listeners = {}
        self.data = {}

        self._load_data()

    def _load_data(self) -> None:
        # ? posted scrutin is a json formated like
        # ? { "<scrutin_id>": "<media_id>", ???? }
        with open("data/linked_media.json", "r") as f:
            data = json.load(f)
            self.add_data("linked_media", data)

        with open("data/posted_scrutins.json", "r") as f:
            data = json.load(f)
            self.add_data("posted_scrutins", data["id"])

    async def save_data(self) -> None:
        async with aiofiles.open("data/posted_scrutins.json", "w") as f:
            await f.write(json.dumps({"id": self.get_data("posted_scrutins")}))

        async with aiofiles.open("data/linked_media.json", "w") as f:
            await f.write(json.dumps(self.get_data("linked_media")))

    def add_data(self, key: Any, value: Any) -> None:
        """
        Set a key-value pair in the client's data dictionary. If key already exists, it will be overwritten.

        :param key: The key to be set.
        :param value: The value to be set.
        :return: None
        """
        self.data[key] = value

    def remove_data(self, key: Any) -> None:
        """
        Remove a key from the client's data dictionary.

        :param key: The key to be removed.
        :return: None
        """
        self.data.pop(key, None)

    def get_data(self, key: Any) -> Optional[Any]:
        """
        Get the value associated with a key from the client's data dictionary. If the key is not found, return None.

        :param key: The key to retrieve the value for.
        :return: The value associated with the key, or None if the key is not found.
        """
        return self.data.get(key, None)

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
