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

CLEAN_PARENTHESIS = re.compile(r"\s*\([^)]*\)", re.IGNORECASE)

FONT_TITLE = ImageFont.truetype("assets/JunePro-Medium.ttf", 52)
FONT_TEXT = ImageFont.truetype("assets/JunePro-Regular.ttf", 47)
FONT_TEXT_SMALLER = ImageFont.truetype("assets/JunePro-Regular.ttf", 32)
FONT_NUMBERS = ImageFont.truetype("assets/JunePro-Extrabold.ttf", 55)


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

        scrutins = [Scrutin(**scrut)
                    for scrut in scrutins_json["scrutins"][:50]]

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


@task.loop(seconds=3, count=5)
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
        media_ids=[scrutin_to_post.media_id] if scrutin_to_post.media_id else None)

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

    cleaned_name = clean_scrutin_name(scrutin.name)
    splited_name = wrap(cleaned_name, width=30)
    for i, line in enumerate(splited_name):
        draw.text((410, 15 + i * 42), line, font=FONT_TITLE, fill="#233f6b")

    date = datetime.strptime(scrutin.date, "%Y-%m-%d")
    boxed_text(
        draw,
        f"{date:%d/%m/%Y}",
        (10, 15),
        FONT_TEXT,
        "#fcfcfc",
        "#233f6b",
    )

    boxed_text(
        draw,
        f"{scrutin.id}",
        (10, 140),
        FONT_TEXT_SMALLER,
        "#fcfcfc",
        "#233f6b",
    )

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

        bg.paste(hemi_img, (width - 675, height - 400))

    reading = extract_parenthesis(scrutin.name)
    boxed_text(
        draw,
        reading,
        (700, 590),
        FONT_TEXT,
        "#fcfcfc",
        "#2c2d32",
    )

    boxed_text(draw, "Détails du scrutin :", (10, 260),
               FONT_TITLE, "#fcfcfc", "#2c2d32")

    if scrutin.adopted:
        boxed_text(draw, f"{scrutin.vote_for}", (30, 335),
                   FONT_NUMBERS, "#fcfcfc", "#5890bd")
    else:
        draw.text((30, 335), f"{scrutin.vote_for}",
                  font=FONT_NUMBERS, fill="#5890bd")

    if not scrutin.adopted:
        boxed_text(draw, f"{scrutin.vote_against}",
                   (200, 335), FONT_NUMBERS, "#fcfcfc", "#ea707d")
    else:
        draw.text((200, 335), f"{scrutin.vote_against}",
                  font=FONT_NUMBERS, fill="#ea707d")

    draw.text((390, 335), f"{scrutin.vote_abstention}",
              font=FONT_NUMBERS, fill="#696969")

    draw.line([(10, 410), (450, 410)], fill="#2c2d32", width=3)

    draw.text(
        (200, 420),
        f"{scrutin.vote_abstention + scrutin.vote_against + scrutin.vote_for}",
        font=FONT_NUMBERS,
        fill="#2c2d32",
    )

    buffer = BytesIO()
    buffer.name = f"scrutin_{scrutin.id}.jpg"
    bg.save(buffer, format="JPEG")
    buffer.seek(0)
    return buffer


def extract_parenthesis(text: str) -> str:
    """Extract the last parenthesis content from the text.

    :param text: The text to extract from.
    :return: The content inside the last parenthesis, cleaned of parentheses.
    """
    rmatch = list(re.finditer(CLEAN_PARENTHESIS, text))
    if rmatch:
        return rmatch[-1].group().strip().replace("(", "").replace(")", "")
    return ""


def clean_scrutin_name(name: str) -> str:
    """
    Clean the scrutin name by removing the "Scrutin public n°" part and any leading/trailing whitespace.

    :param name: The original scrutin name.
    :return: The cleaned scrutin name.
    """
    cleaned_name = CLEAN_PARENTHESIS.sub("", name).strip()
    cleaned_name = re.sub(CLEAN_TITLE_PATTERN, "", cleaned_name).strip()

    match = re.search(r"\b(\w+)\s+de loi\b", cleaned_name, re.IGNORECASE)
    if not match:
        return cleaned_name[:1].upper() + cleaned_name[1:]

    start = match.start(1)

    cleaned_name = cleaned_name[start:]
    cleaned_name = cleaned_name[:1].upper() + cleaned_name[1:]

    return cleaned_name


def boxed_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    pos: tuple[int, int],
    font: ImageFont.FreeTypeFont,
    font_color: str,
    bg_color: str,
    padding: int = 10,
) -> None:
    """
    Draw a text with a background box.

    :param text: The text to draw.
    :param pos: The position to draw the text at.
    :param font: The font to use for the text.
    :param draw: The ImageDraw object to use for drawing.
    :param padding: The padding around the text.
    """
    bbox = draw.textbbox(pos, text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x, y = pos

    draw.rectangle([x - padding, y, x + text_width + padding,
                   y + text_height + (padding * 2)], fill=bg_color)
    draw.text(pos, text, font=font, fill=font_color)
