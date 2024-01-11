import os
import sqlite3
import sys
from time import time
from typing import Iterator

from goratings.interfaces import GameRecord

from .Config import config

__all__ = ["OGSGameData"]


class OGSGameData:
    _conn: sqlite3.Connection
    quiet: bool
    size: int
    speed: int

    def __init__(self, sqlite_filename: str = "data/ogs-data.db", quiet: bool = False, size: int = 0, speed: int = 0) -> None:
        if not os.path.exists(sqlite_filename) and os.path.exists("../" + sqlite_filename):
            sqlite_filename = "../" + sqlite_filename

        self._conn = sqlite3.connect(sqlite_filename)
        self.quiet = quiet
        self.size = size
        self.speed = speed

    def __iter__(self) -> Iterator[GameRecord]:
        c = self._conn.cursor()
        limit = config.args.num_games or 99999999999
        offset = config.args.games_offset
        t = 0.0
        ct = 0
        num_records = 0

        where = ""
        if self.size or self.speed:
            where = 'WHERE '
            if self.size:
                where += ' size = %d ' % self.size
            if self.size and self.speed:
                where += ' AND '
            if self.speed:
                if self.speed >= 3:
                    where += ' (time_per_move = 0 OR time_per_move > 3600) '
                else:
                    where += ' (time_per_move > 0 AND time_per_move < 3600) '

        for row in c.execute(
            """
                SELECT count(*) from game_records %s
            """ % where
        ):
            num_records = int(row[0])
            if offset > num_records:
                num_records = 0
            else:
                num_records = num_records - offset
            if limit < num_records:
                num_records = limit

        NO_BAD_BOTS = True
        join = ''
        if NO_BAD_BOTS:
            join =  ' LEFT JOIN players black_players ON black_id = black_players.id'
            join += ' LEFT JOIN players white_players ON white_id = white_players.id'
            if where != '':
                where += ' AND '
            else:
                where = 'WHERE '
            where += ' (black_players.is_bot = 0 OR black_players.id > 50000) '
            where += ' AND (white_players.is_bot = 0 OR white_players.id > 50000) '
            where += ' AND black_id != 82957 ' # randombot
            where += ' AND white_id != 82957 ' # randombot
            where += ' AND (black_players.is_bot != 1 OR timeout = 0)'
            where += ' AND (white_players.is_bot != 1 OR timeout = 0)'



        started = time()
        for row in c.execute(
            """
                SELECT
                    game_records.id,
                    size,
                    handicap,
                    komi,
                    black_id,
                    white_id,
                    time_per_move,
                    timeout,
                    winner_id,
                    ended,
                    rules
                FROM
                    game_records
                %s
                %s
                ORDER BY ended
                LIMIT
                    ?
                OFFSET
                    ?
            """ % (join, where),
            (limit, offset),
        ):
            ct += 1
            if not self.quiet and time() - t > 0.05:
                t = time()
                records_per_second = ct / (time() - started)
                seconds_left = (num_records - ct) / records_per_second
                sys.stdout.write(
                    f"\r{ct:12n} / {num_records:12n} games processed. " + f"{seconds_left:6.1f}s remaining"
                )
                sys.stdout.flush()

            # Clean the rules field.
            if row[10] in ["aga", "chinese", "ing", "japanese", "korean", "nz"]:
                rules = row[10]
            elif row[10] == "Japanese":
                rules = "japanese"
            elif row[10] == "age":
                rules = "aga"
            elif row[10] == "ing sst":
                rules = "ing"
            elif row[10] == "ogs":
                rules = "japanese"
            else:
                # Report new, unknown, rules spellings so we can clean them properly.
                raise Exception("Unknown rules: '" + row[10] + "'")

            yield GameRecord(
                row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9],
                rules,
            )

        if not self.quiet:
            time_elapsed = time() - started
            sys.stdout.write(f"\n{ct:n} games processed in {time_elapsed:.1f} seconds\n")
            sys.stdout.flush()
        c.close()
