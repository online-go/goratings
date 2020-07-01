#!/usr/bin/env pypy3

import csv
import gzip
import json
import sqlite3
import sys

from dateutil import parser

"""
Imports .csv files generated from our production database with the following
commands and stores them into a sqlite database for test usage

COPY (SELECT
    id,
    ladder_id,
    tournament_id,
    width,
    handicap,
    komi,
    black_id,
    white_id,
    time_per_move,
    time_control_parameters,
    outcome,
    rules,
    black_lost,
    white_lost,
    started,
    ended
    FROM go_app_game
    WHERE
        source='play'
        AND ranked = TRUE
        AND annulled = FALSE
        AND ended IS NOT NULL
        AND black_id > 0
        AND white_id > 0
        AND ((width = 9 AND height = 9) OR (width = 13 AND height = 13) OR (width = 19 AND height = 19))
) TO '/tmp/games.csv' WITH CSV DELIMITER ';';

COPY (SELECT
    id,
    username,
    date_joined,
    rating,
    deviation,
    is_bot
    FROM go_app_player
) TO '/tmp/players.csv' WITH CSV DELIMITER ';';
"""


conn = sqlite3.connect("ogs-data.db")
c = conn.cursor()
c.execute("DROP TABLE IF EXISTS game_records")
c.execute("DROP TABLE IF EXISTS players")
c.execute(
    """
    CREATE TABLE IF NOT EXISTS game_records
    (
        id INTEGER PRIMARY KEY,
        size INTEGER,
        handicap INTEGER,
        komi REAL,
        black_id INTEGER,
        white_id INTEGER,
        time_per_move INTEGER,
        timeout INTEGER,
        winner_id INTEGER,
        ended INTEGER
    );
"""
)

c.execute(
    """
    CREATE TABLE IF NOT EXISTS players
    (
        id INTEGER PRIMARY KEY,
        date_joined INTEGER,
        is_bot BOOLEAN
    );
"""
)


def computeAverageMoveTime(time_control, old_time_per_move):
    if not time_control:
        return old_time_per_move or 0

    if time_control:
        try:
            time_control = json.loads(time_control)
        except:
            return old_time_per_move or 0

    system = (
        time_control["system"]
        if "system" in time_control
        else time_control["time_control"]
    )
    if system == "fischer":
        return time_control["initial_time"] / 90 + time_control["time_increment"]
    if system == "byoyomi":
        return time_control["main_time"] / 90 + time_control["period_time"]
    if system == "simple":
        return time_control["per_move"]
    if system == "canadian":
        return (
            time_control["main_time"] / 90
            + time_control["period_time"] / time_control["stones_per_period"]
        )
    if system == "absolute":
        return time_control["total_time"] / 90
    if system == "none":
        return 0

    print("Unhandled system: %s", system)
    return 0


##
## Import games
##

ct = 0
with gzip.open("games.csv.gz", "rt") as games_f:
    games_csv = csv.reader(games_f, delimiter=";")
    for row in games_csv:
        ct += 1
        if ct % 100 == 0:
            sys.stdout.write("%d\r" % ct)
            sys.stdout.flush()

        id = int(row[0])
        ladder_id = int(row[1]) if row[1] else 0
        tournament_id = int(row[2]) if row[2] else 0
        size = int(row[3])
        handicap = int(row[4])
        komi = float(row[5]) if row[5] else 0
        black_id = int(row[6])
        white_id = int(row[7])
        time_per_move = computeAverageMoveTime(row[9], int(row[8]))
        time_control_parameters = row[9]
        outcome = row[10]
        rules = row[11]
        black_lost = row[12] == "t"
        white_lost = row[13] == "t"
        started = parser.parse(row[14]).timestamp()
        ended = parser.parse(row[15]).timestamp()

        timeout = "timeout" in outcome.lower()
        winner_id = 0
        if black_lost and not white_lost:
            winner_id = white_id
        if white_lost and not black_lost:
            winner_id = black_id

        c.execute(
            """
            INSERT INTO game_records
                (
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
                )
            VALUES
                ( ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                id,
                # ladder_id,
                # tournament_id,
                size,
                handicap,
                komi,
                black_id,
                white_id,
                time_per_move,
                # time_control_parameters,
                # rules,
                timeout,
                winner_id,
                # outcome,
                # started,
                ended,
            ),
        )


##
## Import players
##
ct = 0
with gzip.open("players.csv.gz", "rt") as players_f:
    players_csv = csv.reader(players_f, delimiter=";")
    for row in players_csv:
        ct += 1
        if ct % 100 == 0:
            sys.stdout.write("%d\r" % ct)
            sys.stdout.flush()

        c.execute(
            """
            INSERT INTO players
                (
                    id,
                    date_joined,
                    is_bot
                )
            VALUES
                (
                    ?,
                    ?,
                    ?
                )
        """,
            (
                int(row[0]),
                parser.parse(row[2]).timestamp(),
                row[5] == "t",
            ),
        )


c.execute(
    """
    CREATE INDEX IF NOT EXISTS game_ended_idx ON game_records(ended)
"""
)

c.execute(
    """
    CREATE INDEX IF NOT EXISTS bots_idx ON players(is_bot)
"""
)

conn.commit()
c.close()
conn.execute("VACUUM")
conn.close()
