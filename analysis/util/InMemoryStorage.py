import sqlite3
from collections import defaultdict
from typing import Any, DefaultDict, Dict, List, Tuple

from analysis.util import cli
from goratings.interfaces import Storage

from .Config import config

__all__ = ["InMemoryStorage"]

cli.add_argument(
    "--rating-history-db", dest="rating_history_db", type=str,
    help="Path to DB for ratings history (not saved by default)",
)

class InMemoryStorage(Storage):
    _data: Dict[int, Any]
    _timeout_flags: DefaultDict[int, bool]
    _match_history: DefaultDict[int, List[Tuple[int, Any]]]
    _rating_history: DefaultDict[int, List[Tuple[int, Any]]]
    _set_count: DefaultDict[int, int]
    entry_type: Any

    def __init__(self, entry_type: type) -> None:
        self._data = {}
        self._timeout_flags = defaultdict(lambda: False)
        self._match_history = defaultdict(lambda: [])
        self._rating_history = defaultdict(lambda: [])
        self._set_count = defaultdict(lambda: 0)
        self.entry_type = entry_type

    def get(self, player_id: int) -> Any:
        if player_id not in self._data:
            self._data[player_id] = self.entry_type()
        return self._data[player_id]

    def set(self, player_id: int, entry: Any) -> None:
        self._data[player_id] = entry
        self._set_count[player_id] += 1

    def clear_set_count(self, player_id: int) -> None:
        self._set_count[player_id] = 0

    def get_set_count(self, player_id: int) -> int:
        return self._set_count[player_id]

    def all_players(self) -> Dict[int, Any]:
        return self._data

    def get_timeout_flag(self, player_id: int) -> bool:
        return self._timeout_flags[player_id]

    def set_timeout_flag(self, player_id: int, tf: bool) -> None:
        self._timeout_flags[player_id] = tf

    # We assume we add these entries in ascending order (by timestamp).
    def add_rating_history(self, player_id: int, timestamp: int, entry: Any) -> None:
        self._rating_history[player_id].append((timestamp, entry))

    def add_match_history(self, player_id: int, timestamp: int, entry: Any) -> None:
        self._match_history[player_id].append((timestamp, entry))

    def get_last_game_timestamp(self, player_id: int) -> int:
        if player_id in self._rating_history:
            return self._rating_history[player_id][-1][0]
        return 0

    def get_first_rating_older_than(self, player_id: int, timestamp: int) -> Any:
        for e in reversed(self._rating_history[player_id]):
            if e[0] < timestamp:
                return e[1]
        return self.entry_type()

    def get_ratings_newer_or_equal_to(self, player_id: int, timestamp: int) -> Any:
        ct = 0
        for e in reversed(self._rating_history[player_id]):
            if e[0] >= timestamp:
                ct += 1
            else:
                break
        return [e[1] for e in self._rating_history[player_id][-ct:]]

    def get_first_timestamp_older_than(self, player_id: int, timestamp: int) -> Any:
        for e in reversed(self._rating_history[player_id]):
            if e[0] < timestamp:
                return e[0]
        return None

    def get_matches_newer_or_equal_to(self, player_id: int, timestamp: int) -> Any:
        ct = 0
        for e in reversed(self._match_history[player_id]):
            if e[0] >= timestamp:
                ct += 1
            else:
                break
        return [e[1] for e in self._match_history[player_id][-ct:]]

    def save_rating_history(self, category: str) -> None:
        if config.args.rating_history_db is None:
            return
        connection = sqlite3.connect(config.args.rating_history_db)
        cursor = connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rating_history(
                category TEXT,
                player_id INTEGER,
                timestamp INTEGER,
                rating REAL,
                deviation REAL,
                volatility REAL
            )""")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS index_ratings_by_player
                ON rating_history
                (player_id,timestamp)
            """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS index_ratings_by_category
                ON rating_history
                (category,player_id,timestamp)
            """)
        cursor.executemany("""
            INSERT INTO rating_history(category,player_id,timestamp,rating,deviation,volatility)
                VALUES (?,?,?,?,?,?)
            """,
            ((category, player, timestamp, r.rating, r.deviation, r.volatility)
                for (player,history) in self._rating_history.items()
                for (timestamp, r) in history
            ),
            )
        connection.commit()
        connection.close()
