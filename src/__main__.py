from __future__ import annotations

import asyncio

from loguru import logger

from .components import client, task
from .tasks import scrutins, tweets

bot = client.instance()


async def main():
    scrutins.get_scrutins_task.start(bot)
    scrutins.post_scrutins_task.start(bot)

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
