from __future__ import annotations

import argparse
import asyncio
import locale

from loguru import logger

from .components import MockedTwitter, client
from .tasks import scrutins


async def main():
    bot = client.instance()
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true",
                        default=False, help="Run in development mode")
    args = parser.parse_args()

    if args.dev:
        logger.info("Running in development mode")
        bot.tw_client = bot.tw_api_V1 = MockedTwitter()  # type: ignore

    scrutins.get_scrutins_task.start(bot)
    scrutins.create_post.start(bot)
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
