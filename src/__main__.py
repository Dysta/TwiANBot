from __future__ import annotations

import os

import tweepy
from loguru import logger


def main():
    bot = tweepy.Client(
        consumer_key=os.getenv("API_KEY"),
        consumer_secret=os.getenv("API_SECRET"),
        access_token=os.getenv("ACCESS_TOKEN"),
        access_token_secret=os.getenv("ACCESS_SECRET"),
    )

    logger.debug(os.getenv("API_KEY"))
    logger.debug(os.getenv("API_SECRET"))
    logger.debug(os.getenv("ACCESS_TOKEN"))
    logger.debug(os.getenv("ACCESS_SECRET"))

    bot.create_tweet(text="Hello, world!")


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    main()
