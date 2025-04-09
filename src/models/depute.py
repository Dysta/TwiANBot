from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, eq=False)
class Depute:
    first_name: str
    last_name: str
    party: str
