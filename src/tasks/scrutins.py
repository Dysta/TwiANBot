from __future__ import annotations

from typing import List

from loguru import logger

from src.components import get_client_instance, req, task
from src.models import Scrutin

BASE_URL: str = "https://dysta.github.io/ANDataParser/data/dyn/17"
SCRUTIN_URL: str = BASE_URL + "/scrutins.json"

client = get_client_instance()


@task.loop(seconds=2, count=1)
async def task() -> None:
    logger.debug("Running scrutins loop")

    scrutins_json = await req.get(SCRUTIN_URL)

    scrutins: List[Scrutin] = [Scrutin(**scrut) for scrut in scrutins_json["scrutins"]]
    logger.debug(scrutins)

    client.data["scrutins"] = scrutins
    client.data["scrutins_count"] = scrutins_json["total"]

    client.dispatch("scrutins_updated")


@client.listen()
async def on_scrutins_updated() -> None:
    logger.debug("Scrutins updated func called")

    raise ValueError("test")
