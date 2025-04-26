from __future__ import annotations

from loguru import logger

from src.components import client, task

BASE_URL: str = "https://dysta.github.io/ANDataParser/data/dyn/17"
TWEET_URL: str = BASE_URL + "/tweets.json"


@task.loop(seconds=2)
async def get_latest_bot_tweets_task(client: client.Client) -> None:
    logger.debug("Running tweets loop")
