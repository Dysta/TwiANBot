from __future__ import annotations

from typing import Any, Dict

import aiohttp


async def get(url: str) -> Dict[str, Any]:
    """
    Asynchronous GET request to the given URL.

    The response body is expected to contain a JSON object which is returned as a dictionary.

    :param url: The URL to request
    :return: The JSON object from the response body as a dictionary
    :raises Exception: If the response status is not between 200 and 300
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if not 200 <= response.status < 300:
                raise Exception(f"Request failed with status {response.status}")

            return await response.json(encoding="utf-8")
