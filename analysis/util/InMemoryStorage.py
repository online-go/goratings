from typing import Dict

from goratings.interfaces import Storage
from goratings.math.glicko2 import Glicko2Entry

__all__ = ["InMemoryStorage"]


class InMemoryStorage:
    _data: Dict[int, Glicko2Entry]

    def __init__(self) -> None:
        self._data = {}

    def getGlicko2Entry(self, player_id: int) -> Glicko2Entry:
        if player_id not in self._data:
            self._data[player_id] = Glicko2Entry()
        return self._data[player_id]

    def setGlicko2Entry(self, player_id: int, entry: Glicko2Entry) -> None:
        self._data[player_id] = entry
