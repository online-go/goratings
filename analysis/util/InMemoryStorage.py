from typing import Dict, Any

from goratings.interfaces import Storage
from goratings.math.glicko2 import Glicko2Entry

__all__ = ["InMemoryStorage"]


class InMemoryStorage(Storage):
    _data: Dict[int, Any]
    entry_type: Any

    def __init__(self, entry_type: type) -> None:
        self._data = {}
        self.entry_type = entry_type

    def get(self, player_id: int) -> Any:
        if player_id not in self._data:
            #self._data[player_id] = Glicko2Entry()
            self._data[player_id] = self.entry_type()
        return self._data[player_id]

    def set(self, player_id: int, entry: Any) -> None:
        self._data[player_id] = entry
