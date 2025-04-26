from __future__ import annotations

from dataclasses import dataclass


@dataclass(eq=False)
class Scrutin:
    id: int
    name: str
    url: str
    text_url: str
    date: str
    adopted: bool
    vote_for: int
    vote_against: int
    vote_abstention: int

    posted: bool = False
    media_id: int = 0
