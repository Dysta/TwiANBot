from __future__ import annotations

from loguru import logger

from src import TwiBot
from src.models import Scrutin
from src.utils import task


@task.loop(seconds=2)
async def task(bot: TwiBot) -> None:
    logger.debug("Running scrutins loop")
    logger.debug(bot)
