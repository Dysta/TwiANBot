from loguru import logger

from src.components import client, task

# @task.loop(seconds=3)
# async def create_post(client: client.Client) -> None:
#     logger.debug("Running post scrutins loop")

#     assert client.get_data("scrutins"), "No scrutins to post"

#     ready_to_post = [scrutin for scrutin in client.get_data(
#         "scrutins") if not scrutin.posted]

#     scrutin_to_post = ready_to_post.pop()

#     scrutin_analyse = await get_scrutin_details(scrutin_to_post)

#     tweet_image = generate_vote_image(scrutin_to_post, scrutin_analyse)
#     img = client.tw_api_V1.media_upload(
#         filename=tweet_image.name, file=tweet_image)
#     scrutin_to_post.media_id = img.media_id

#     txt = short_tweet(scrutin_to_post)
#     txt2 = tweet_reply(scrutin_to_post)

#     assert len(txt) <= 280, f"Tweet too long for scrutin {scrutin_to_post.id}"

#     client.tw_client.create_tweet(
#         media_ids=[
#             scrutin_to_post.media_id] if scrutin_to_post.media_id else None
#     )

#     scrutin_to_post.posted = True
#     client.get_data("posted_scrutins").append(scrutin_to_post.id)
#     client.dispatch("scrutins_updated")
