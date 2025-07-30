from __future__ import annotations

import base64
import re
from datetime import datetime, timedelta
from io import BytesIO
from textwrap import wrap
from typing import List

from loguru import logger
from PIL import Image, ImageDraw, ImageFont

from src.components import client, req, task
from src.models import Scrutin, ScrutinAnalyse

CLEAN_TITLE_PATTERN = re.compile(
    r"Scrutin public n.?°\d+\s+sur\s+(l[’']|le|la)\s*", re.IGNORECASE)

FONT_TITLE = ImageFont.truetype("assets/JunePro-Medium.ttf", 32)
FONT_TEXT = ImageFont.truetype("assets/JunePro-Regular.ttf", 22)


BASE_URL: str = "https://dysta.github.io/ANDataParser/data"
SCRUTIN_URL: str = BASE_URL + "/dyn/17/scrutins.json"

AN_BASE_URL: str = "https://www.assemblee-nationale.fr"

MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB = 5_242_880 octets

bot = client.instance()


@task.loop(seconds=1, count=1)
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


@task.loop(seconds=3)
async def create_post(client: client.Client) -> None:
    logger.debug("Running post scrutins loop")

    assert client.get_data("scrutins"), "No scrutins to post"

    ready_to_post = [scrutin for scrutin in client.get_data(
        "scrutins") if not scrutin.posted]

    scrutin_to_post = ready_to_post.pop()

    scrutin_analyse = await get_scrutin_details(scrutin_to_post)

    tweet_image = generate_vote_image(scrutin_to_post, scrutin_analyse)
    img = client.tw_api_V1.media_upload(
        filename=tweet_image.name, file=tweet_image)
    scrutin_to_post.media_id = img.media_id

    txt = short_tweet(scrutin_to_post)
    txt2 = tweet_reply(scrutin_to_post)

    assert len(txt) <= 280, f"Tweet too long for scrutin {scrutin_to_post.id}"

    client.tw_client.create_tweet(
        media_ids=[
            scrutin_to_post.media_id] if scrutin_to_post.media_id else None
    )

    scrutin_to_post.posted = True
    client.get_data("posted_scrutins").append(scrutin_to_post.id)
    client.dispatch("scrutins_updated")


async def get_scrutin_details(scrutin: Scrutin) -> ScrutinAnalyse:
    """
    Fetch the details of a scrutin.

    :param scrutin: The scrutin to fetch details for.
    :return: The scrutin details.
    """
    target_url = BASE_URL + scrutin.url + ".json"
    fetch_scrutin_details = await req.get(target_url)
    return ScrutinAnalyse(**fetch_scrutin_details)


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
    if scrutin.text_url != "":
        rep += f"\n📜 Texte de loi ici : {AN_BASE_URL + scrutin.text_url}\n"

    return rep


def generate_vote_image(scrutin: Scrutin, scrutin_analyse: ScrutinAnalyse) -> BytesIO:
    bg = Image.open("assets/bg_an.jpg").convert("RGB")
    width, height = bg.size
    draw = ImageDraw.Draw(bg)

    cleaned_name = re.sub(CLEAN_TITLE_PATTERN, "", scrutin.name).strip()
    cleaned_name = cleaned_name[:1].upper() + cleaned_name[1:]

    splited_name = wrap(cleaned_name, width=50)
    for i, line in enumerate(splited_name):
        draw.text((410, 20 + i * 38), line,
                  font=FONT_TITLE, fill="#233f6b")

    bbox = draw.textbbox((0, 0), str(scrutin.id), font=FONT_TEXT)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    padding = 10
    draw.rectangle(
        [0, 15, 10 + text_width +
            padding, 15 + text_height + padding],
        fill="#233f6b"
    )

    draw.text((10, 15), str(scrutin.id),
              font=FONT_TEXT, fill="#fcfcfc")

    date = datetime.strptime(scrutin.date, "%Y-%m-%d")

    bbox = draw.textbbox((0, 0), f"{date:%d/%m/%Y}", font=FONT_TEXT)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    padding = 10
    draw.rectangle(
        [0, 60, 10 + text_width +
            padding, 60 + text_height + padding],
        fill="#233f6b"
    )

    draw.text((10, 60), f"{date:%d/%m/%Y}",
              font=FONT_TEXT, fill="#fcfcfc")

    if scrutin_analyse.visualizer:
        vizualizer = BytesIO(base64.b64decode(scrutin_analyse.visualizer))

        hemi_img = Image.open(vizualizer).convert("RGB")
        datas = hemi_img.getdata()

        new_data = []
        for item in datas:
            if item[:3] == (255, 255, 255):  # blanc pur
                new_data.append((252, 252, 252))  # blanc cassé
            else:
                new_data.append(item)

        hemi_img.putdata(new_data)
        hemi_img = hemi_img.resize((650, 400))
        bg.paste(hemi_img, (width - 700, height - 430))

    draw.text((30, 240), "Détails du scrutin :",
              font=FONT_TITLE, fill="#2c2d32")

    draw.text(
        (30, 300), f"Pour l'adoption : {scrutin.vote_for}", font=FONT_TEXT, fill="#4CAF50")
    draw.text(
        (30, 330), f"Contre l'adoption : {scrutin.vote_against}", font=FONT_TEXT, fill="#C52D22")
    draw.text(
        (30, 360), f"Abstentions : {scrutin.vote_abstention}", font=FONT_TEXT, fill="#555555")

    draw.text(
        (30, 420), f"Votants : {scrutin.vote_abstention + scrutin.vote_against + scrutin.vote_for}", font=FONT_TEXT, fill="#2c2d32")

    draw.text(
        (30, 450), f"Suffrages exprimés : { scrutin.vote_against + scrutin.vote_for}", font=FONT_TEXT, fill="#2c2d32")

    draw.text(
        (30, 480), f"Majorité absolue : { (scrutin.vote_abstention + scrutin.vote_against + scrutin.vote_for) // 2}", font=FONT_TEXT, fill="#2c2d32")

    if scrutin.adopted:
        stamp = Image.open("assets/valid.jpg").convert("RGB")
    else:
        stamp = Image.open("assets/denied.jpg").convert("RGB")

    stamp = stamp.resize((90, 90))
    bg.paste(stamp, (350, 530))

    buffer = BytesIO()
    buffer.name = f"scrutin_{scrutin.id}.jpg"
    bg.save(buffer, format="JPEG")
    buffer.seek(0)
    return buffer
