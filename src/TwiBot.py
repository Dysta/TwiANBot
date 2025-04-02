from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List

import tweepy
from loguru import logger

from .utils import task


@dataclass(init=False, order=False, eq=False, unsafe_hash=False)
class TwiBot:
    tasks: List[task.Task]
    tw_client: tweepy.Client

    def __init__(self) -> None:
        self.tw_client = tweepy.Client(
            consumer_key=os.getenv("API_KEY"),
            consumer_secret=os.getenv("API_SECRET"),
            access_token=os.getenv("ACCESS_TOKEN"),
            access_token_secret=os.getenv("ACCESS_SECRET"),
            wait_on_rate_limit=True,
        )
        self.tasks = []

    def add_task(self, task: task.Task, *args, **kwargs) -> None:
        """
        Add a task to the list of tasks and start it.

        :param task: The task to be added and started.
        :param args: Arguments to be passed to the task when it is started.
        :param kwargs: Keyword arguments to be passed to the task when it is started.
        """
        self.tasks.append(task)
        task.start(*args, **kwargs)

    def stop(self) -> None:
        for task in self.tasks:
            task.stop()

        self.tasks = []
        logger.info("Bot shutdown")
