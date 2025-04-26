from __future__ import annotations

import base64
from io import BytesIO
from typing import List

from loguru import logger

from src.components import client, req, task
from src.models import Scrutin, ScrutinAnalyse

BASE_URL: str = "https://dysta.github.io/ANDataParser/data"
SCRUTIN_URL: str = BASE_URL + "/dyn/17/scrutins.json"

AN_BASE_URL: str = "https://www.assemblee-nationale.fr"

bot = client.instance()


@task.loop(seconds=2, count=1)
async def get_scrutins_task(client: client.Client) -> None:
    logger.debug("Running scrutins loop")

    scrutins_json = await req.get(SCRUTIN_URL)

    scrutins: List[Scrutin] = [Scrutin(**scrut) for scrut in scrutins_json["scrutins"] if scrut["date"] >= "2025-04-01"]

    client.add_data("scrutins", scrutins)
    client.add_data("scrutins_count", len(scrutins))

    client.dispatch("scrutins_updated")


@task.loop(seconds=5)
async def post_scrutins_task(client: client.Client) -> None:
    logger.debug("Running post scrutins loop")

    not_posted_scrutins = [scrutin for scrutin in client.get_data("scrutins") if not scrutin.posted]

    scrutin_to_post = not_posted_scrutins.pop()

    target_url = BASE_URL + scrutin_to_post.url + ".json"
    fetch_scrutin_details = await req.get(target_url)

    scrutin_analyse = ScrutinAnalyse(**fetch_scrutin_details)
    img = None
    if scrutin_analyse.visualizer:
        img_data = BytesIO(base64.b64decode(scrutin_analyse.visualizer))
        img_data.name = "visualizer.png"
        # img = client.tw_api_V1.media_upload(filename=img_data.name, file=img_data)

    txt = short_tweet(scrutin_to_post)
    txt2 = tweet_reply(scrutin_to_post)

    client.tw_api_V1.update_status_with_media(status=txt, filename="visualizer.png", file=img_data)
    tweet = client.tw_client.create_tweet(text=txt, media_ids=[img.media_id] if img else None)
    client.tw_client.create_tweet(text=txt2, in_reply_to_tweet_id=tweet.data["id"])

    client.get_data("posted_scrutins").append(scrutin_to_post.id)
    client.dispatch("scrutins_updated")


@bot.listen()
async def on_scrutins_updated() -> None:
    logger.debug("Scrutins updated func called")

    for scrutin in bot.get_data("scrutins"):
        scrutin.posted = scrutin.id in bot.get_data("posted_scrutins")


def short_tweet(scrutin: Scrutin) -> str:
    status = "✅ Adopté" if scrutin.adopted else "❌ Rejeté"
    return (
        f"{status} : {scrutin.name}\n"
        f"🗳️ {scrutin.vote_for} pour / {scrutin.vote_against} contre / {scrutin.vote_abstention} abst.\n"
    )


def tweet_reply(scrutin: Scrutin) -> str:
    return f"Plus d'info ici : {AN_BASE_URL + scrutin.url}\n" f"Texte de loi ici : {AN_BASE_URL + scrutin.text_url}\n"
