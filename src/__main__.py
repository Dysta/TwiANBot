from __future__ import annotations

import asyncio
import random

from loguru import logger

from . import TwiBot
from .tasks import scrutins
from .utils import task


@task.loop(seconds=1, count=3)
async def simple_task() -> None:
    n = random.randint(1, 10)
    logger.debug(f"Hello, world from task {n}!")


async def main():
    bot = TwiBot()

    bot.add_task(simple_task)
    bot.add_task(scrutins.task, bot)

    # bot.create_tweet(text="Hello, world!")

    # ? run the bot forever
    event = asyncio.Event()
    await event.wait()


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot shutdown")
