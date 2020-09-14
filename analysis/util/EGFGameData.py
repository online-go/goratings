import os
import sqlite3
import sys
from time import time
from typing import Iterator

from goratings.interfaces import GameRecord

from .Config import config

__all__ = ["EGFGameData"]


class EGFGameData:
    _conn: sqlite3.Connection
    quiet: bool

    def __init__(
        self, sqlite_filename: str = "data/egf-data.db", quiet: bool = False
    ) -> None:
        if not os.path.exists(sqlite_filename) and os.path.exists(
            "../" + sqlite_filename
        ):
            sqlite_filename = "../" + sqlite_filename

        self._conn = sqlite3.connect(sqlite_filename)
        self.quiet = quiet

    def __iter__(self) -> Iterator[GameRecord]:
        c = self._conn.cursor()
        limit = config.args.num_games or 99999999999
        t = 0.0
        ct = 0
        num_records = 0

        for row in c.execute(
            """
                SELECT count(*) from game_records
            """
        ):
            num_records = int(row[0])
            if limit < num_records:
                num_records = limit

        started = time()
        for row in c.execute(
            """
                SELECT
                    id,
                    19,
                    handicap,
                    0,
                    black_id,
                    white_id,
                    60,
                    FALSE,
                    winner_id,
                    ended,
                    black_manual_rank_update,
                    white_manual_rank_update
                FROM
                    game_records ORDER BY ended
                LIMIT
                    ?
            """,
            [limit],
        ):
            ct += 1
            if not self.quiet and time() - t > 0.05:
                t = time()
                records_per_second = ct / (time() - started)
                seconds_left = (num_records - ct) / records_per_second
                sys.stdout.write(
                    f"\r{ct:12n} / {num_records:12n} games processed. "
                    + f"{seconds_left:6.1f}s remaining"
                )
                sys.stdout.flush()

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
                row[10],
                row[11],
            )

        if not self.quiet:
            time_elapsed = time() - started
            sys.stdout.write(
                f"\n{ct:n} games processed in {time_elapsed:.1f} seconds\n"
            )
            sys.stdout.flush()
        c.close()
