import pickle
import sqlite3
import os
from typing import Iterator, List

from goratings.interfaces import GameRecord
from .cli import cli
from .config import config

__all__ = ["OGSGameData"]



cli.add_argument('--games', dest="num_games", type=int, default=0, help="Number of games to process, 0 for all")

class OGSGameData:
    _conn: sqlite3.Connection

    def __init__(self, sqlite_filename: str = "data/ogs-data.db") -> None:
        if not os.path.exists(sqlite_filename) and os.path.exists("../" + sqlite_filename):
            sqlite_filename = '../' + sqlite_filename

        self._conn = sqlite3.connect(sqlite_filename)

    def __iter__(self) -> Iterator[GameRecord]:
        c = self._conn.cursor()
        max_games_left = config.args.num_games or 99999999999
        for row in c.execute(
            """
                SELECT
                    id,
                    size,
                    handicap,
                    komi,
                    black_id,
                    white_id,
                    time_per_move,
                    timeout,
                    winner_id,
                    ended
                FROM
                    game_records ORDER BY ended
            """
        ):
            if max_games_left <= 0:
                break
            max_games_left -= 1

            yield GameRecord(
                row[0],
                row[1],
                row[2],
                row[3],
                row[4],
                row[5],
                row[6],
                row[7],
                row[8],
                row[9],
            )
        c.close()
