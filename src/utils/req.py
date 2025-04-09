from __future__ import annotations

from typing import Dict

import aiohttp


async def fetch_url(url: str) -> Dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise Exception(f"Échec de la requête: {response.status}")
