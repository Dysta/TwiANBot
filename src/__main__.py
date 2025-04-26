from __future__ import annotations

import asyncio

from loguru import logger

from .components import client
from .tasks import scrutins


async def main():
    bot = client.instance()
    scrutins.get_scrutins_task.start(bot)
    scrutins.post_scrutins_task.start(bot)
    # scrutins.upload_scrutin_media.start(bot)

    # ? run the bot forever
    event = asyncio.Event()
    await event.wait()


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv(".env")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot shutdown")
