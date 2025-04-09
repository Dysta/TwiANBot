from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import List

from .depute import Depute


@dataclass(eq=False, frozen=True)
class ScrutinAnalyse:
    id: int
    date: str
    title: str
    adopted: bool
    visualizer: str
    vote_for: List[Depute]
    vote_against: List[Depute]
    vote_abstention: List[Depute]
    vote_absent: List[Depute]
