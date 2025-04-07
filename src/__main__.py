from __future__ import annotations

import asyncio
import random

from loguru import logger

from .components import get_client_instance, task
from .tasks import scrutins

client = get_client_instance()


@task.loop(seconds=1, count=1)
async def simple_task() -> None:
    n = random.randint(1, 10)
    logger.debug(f"Hello, world from task {n}!")


@client.listen()
async def on_scrutins_updated() -> None:
    logger.debug("Scrutins updated func called from main")


async def main():
    client.add_task(simple_task)
    client.add_task(scrutins.task)

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
