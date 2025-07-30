import uuid
from io import BytesIO
from pathlib import Path


class MockedMedia:
    def __init__(self, media_id: str, media_url: str):
        self.media_id = media_id
        self.media_url = media_url


class MockedTwitter:
    def media_upload(self, filename, *, file: BytesIO = None, chunked=False,
                     media_category=None, additional_owners=None, **kwargs):
        """media_upload(filename, *, file, chunked, media_category, \
                        additional_owners)

        Mocked method to simulate media upload. Saves the file to a local directory.
        """
        out_dir = Path("dev_output")
        out_dir.mkdir(exist_ok=True)
        img_path = out_dir / f"{filename}"
        with open(img_path, "wb") as f:
            f.write(file.read())

        return MockedMedia(media_id=str(uuid.uuid4()), media_url=f"file://{img_path}")

    def create_tweet(
        self, *, direct_message_deep_link=None, for_super_followers_only=None,
        place_id=None, media_ids=None, media_tagged_user_ids=None,
        poll_duration_minutes=None, poll_options=None, quote_tweet_id=None,
        exclude_reply_user_ids=None, in_reply_to_tweet_id=None,
        reply_settings=None, text=None, user_auth=True
    ):
        """create_tweet(*, direct_message_deep_link=None, \
        for_super_followers_only=None, place_id=None, media_ids=None, \
        media_tagged_user_ids=None, poll_duration_minutes=None, \
        poll_options=None, quote_tweet_id=None, exclude_reply_user_ids=None, \
        in_reply_to_tweet_id=None, reply_settings=None, text=None, \
        user_auth=True)

        Mocked method to simulate tweet creation. Does not perform any action.
        """
        return True
