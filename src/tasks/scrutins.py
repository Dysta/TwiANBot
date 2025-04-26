from __future__ import annotations

import base64
from datetime import datetime, timedelta
from io import BytesIO
from typing import List

from loguru import logger

from src.components import client, req, task
from src.models import Scrutin, ScrutinAnalyse

BASE_URL: str = "https://dysta.github.io/ANDataParser/data"
SCRUTIN_URL: str = BASE_URL + "/dyn/17/scrutins.json"

AN_BASE_URL: str = "https://www.assemblee-nationale.fr"

MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB = 5_242_880 octets

bot = client.instance()


@task.loop(hours=6)
async def get_scrutins_task(client: client.Client) -> None:
    logger.debug("Running scrutins loop")

    scrutins_json = await req.get(SCRUTIN_URL)

    today = datetime.now()
    yesterday = today - timedelta(days=1)

    scrutins: List[Scrutin] = [
        Scrutin(**scrut) for scrut in scrutins_json["scrutins"] if scrut["date"] >= yesterday.strftime("%Y-%m-%d")
    ]
    if not scrutins:
        logger.debug("No scrutins to post today, taking the last 50 scrutins")

        scrutins = [
            Scrutin(**scrut) for scrut in scrutins_json["scrutins"][:50]
        ]

    linked_media = client.get_data("linked_media")
    posted_scrutins = client.get_data("posted_scrutins")
    for scrutin in scrutins:
        scrutin.posted = scrutin.id in posted_scrutins
        # ? must convert in str to get the key
        if media := linked_media.get(str(scrutin.id)):
            scrutin.media_id = media

    client.add_data("scrutins", scrutins)
    client.add_data("scrutins_count", len(scrutins))

    client.dispatch("scrutins_updated")


async def upload_scrutin_media(client: client.Client, scrutin: Scrutin) -> None:
    """
    Upload media for not yet posted scrutins.

    This task is used to upload media for scrutins that have not yet been posted.
    It will upload the first scrutin it finds that has not yet been posted and has
    a visualizer.

    :param client: The client instance.
    """
    logger.debug("Running upload media loop")

    target_url = BASE_URL + scrutin.url + ".json"
    fetch_scrutin_details = await req.get(target_url)

    scrutin_analyse = ScrutinAnalyse(**fetch_scrutin_details)
    img = None

    if not scrutin.media_id and scrutin_analyse.visualizer:
        img_data = BytesIO(base64.b64decode(scrutin_analyse.visualizer))
        img_data.name = "visualizer.png"

        assert img_data.getbuffer(
        ).nbytes < MAX_IMAGE_SIZE, f"Image too big for scrutin {scrutin.id}"

        img = client.tw_api_V1.media_upload(
            filename=img_data.name, file=img_data)
        scrutin.media_id = img.media_id

        client.get_data("linked_media")[str(scrutin.id)] = img.media_id

        client.dispatch("scrutins_updated")


@task.loop(hours=1)
async def post_scrutins_task(client: client.Client) -> None:
    logger.debug("Running post scrutins loop")

    assert client.get_data("scrutins"), "No scrutins to post"

    ready_to_post = [scrutin for scrutin in client.get_data(
        "scrutins") if not scrutin.posted]

    scrutin_to_post = ready_to_post.pop()

    if not scrutin_to_post.media_id:
        await upload_scrutin_media(client, scrutin_to_post)

    txt = short_tweet(scrutin_to_post)
    txt2 = tweet_reply(scrutin_to_post)

    assert len(txt) <= 280, f"Tweet too long for scrutin {scrutin_to_post.id}"

    tweet = client.tw_client.create_tweet(
        text=txt, media_ids=[
            scrutin_to_post.media_id] if scrutin_to_post.media_id else None
    )
    client.tw_client.create_tweet(
        text=txt2, in_reply_to_tweet_id=tweet.data["id"])

    scrutin_to_post.posted = True
    client.get_data("posted_scrutins").append(scrutin_to_post.id)
    client.dispatch("scrutins_updated")


@bot.listen()
async def on_scrutins_updated() -> None:
    logger.debug("Scrutins updated func called")

    await bot.save_data()


def short_tweet(scrutin: Scrutin) -> str:
    status = "✅ Adopté" if scrutin.adopted else "❌ Rejeté"
    return (
        f"{status} : {scrutin.name}\n\n"
        f"🗳️ {scrutin.vote_for} pour / {scrutin.vote_against} contre / {scrutin.vote_abstention} abst.\n"
    )


def tweet_reply(scrutin: Scrutin) -> str:
    rep = f"❔ Plus d'info sur le scrutin ici : {AN_BASE_URL + scrutin.url}"
    if scrutin.text_url:
        rep += f"\nTexte de loi ici : {AN_BASE_URL + scrutin.text_url}\n"

    return rep
