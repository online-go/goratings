#!/usr/bin/env pypy3

import csv
import gzip
import json
import sqlite3
import sys
from collections import defaultdict
from math import isnan
from dateutil import parser

EGF_OFFSET = 1000000000


"""
Original .csv.gz file generated with the following query

SELECT
	games.Tournament_Code,
	games.Game_Date,
	games.Round,
	games.Pin_Player_1,
	games.Color_1,
	games.Pin_Player_2,
	games.Color_2,
	games.Handicap,
	games.Reconstructed_hp,
	games.Explicit_hp,
	games.Result,
	games.Sgf_Code,
	games.Elab_Date,
	placements_1.Precedent_Gor AS gor_before_1,
	placements_1.Following_Gor AS gor_after_1,
	placements_1.Grade_Declared AS declared_rank_1,
	placements_1.Placement AS placement_1,
	placements_2.Precedent_Gor AS gor_before_2,
	placements_2.Following_Gor AS gor_after_2,
	placements_2.Grade_Declared AS declared_rank_2,
	placements_2.Placement AS placement_2
FROM
	games
	INNER JOIN placements AS placements_1 ON placements_1.Tournament_Code = games.Tournament_Code
	AND placements_1.Pin_Player = games.Pin_Player_1
	INNER JOIN placements AS placements_2 ON placements_2.Tournament_Code = games.Tournament_Code
	AND placements_2.Pin_Player = games.Pin_Player_2

"""


conn = sqlite3.connect("egf-data.db")
c = conn.cursor()
c.execute("DROP TABLE IF EXISTS game_records")
c.execute(
    """
    CREATE TABLE IF NOT EXISTS game_records
    (
        id INTEGER PRIMARY KEY,
        black_id INTEGER,
        white_id INTEGER,
        handicap INTEGER,
        winner_id INTEGER,
        ended INTEGER,
        black_manual_rank_update INTEGER,
        white_manual_rank_update INTEGER
    );
"""
)



##
## Import games
##
def num2rank(num: float) -> str:
    if isnan(num) or (not num and num != 0):
        return "N/A"
    if int(num) < 30:
        return "%dk" % (30 - int(num))
    return "%dd" % ((int(num) - 30) + 1)


ct = 0
rows = []
with gzip.open("games_goratings_eu_2020-07-12.csv.gz", "rt") as games_f:
    games_csv = csv.reader(games_f, delimiter=",")
    for row in games_csv:
        ct += 1
        if ct % 1000 == 0:
            sys.stdout.write("%d\r" % ct)
            sys.stdout.flush()
        rows.append(row)

rows = sorted(rows, key=lambda x: "%s-%2d" % (x[1], int(x[2]))) # sort by date / round

last_manual_rank = {}

game_id = EGF_OFFSET

print('')
ct = 0

for row in rows:
    ct += 1
    if ct % 1000 == 0:
        sys.stdout.write("%d\r" % ct)
        sys.stdout.flush()

    game_id += 1
    ended = parser.parse(row[1]).timestamp()
    p1_id = int(row[3]) + EGF_OFFSET
    p1_color = row[4]
    p2_id = int(row[5]) + EGF_OFFSET
    p1_rating = row[13]
    p1_rating_after = row[14]
    p2_rating = row[17]
    p2_rating_after = row[18]
    p1_manual_rank = None if '.' in p1_rating else (int(p1_rating) / 100.0) + 9
    p2_manual_rank = None if '.' in p2_rating else (int(p2_rating) / 100.0) + 9
    handicap = int(row[7])

    if p1_manual_rank and p1_id in last_manual_rank and last_manual_rank[p1_id] == p1_manual_rank:
        p1_manual_rank = None
    if p2_manual_rank and p2_id in last_manual_rank and last_manual_rank[p2_id] == p2_manual_rank:
        p2_manual_rank = None

    for (id, rank) in [(p1_id, p1_manual_rank), (p2_id, p2_manual_rank)]:
        if rank:
            if id not in last_manual_rank:
                last_manual_rank[id] = rank
            if last_manual_rank[id] != rank:
                last_manual_rank[id] = rank


    winner = row[10]

    if winner == "b" or winner == "w":
        winner = 1 if p1_color == winner else 2

    elif winner == "1" or winner == "2":
        winner = int(winner)

    else:
        # drop game if it's "=" I guess, I'm not sure what the appropriate
        # action here is. There's only a few games where this is true,
        # shouldn't change things *that* much.
        continue

    if p1_color == 'b' or p1_color == '':
        black_id = p1_id
        black_rating = p1_rating
        black_manual_rank = p1_manual_rank
        white_id = p2_id
        white_rating = p2_rating
        white_manual_rank = p2_manual_rank

    elif p1_color == 'w' or p1_color == '':
        white_id = p1_id
        white_rating = p1_rating
        white_manual_rank = p1_manual_rank
        black_id = p2_id
        black_rating = p2_rating
        black_manual_rank = p2_manual_rank

    else:
        assert(False)

    winner_id = p1_id if winner == 1 else p2_id


    c.execute(
        """
        INSERT INTO game_records
            (
                id,
                black_id,
                white_id,
                handicap,
                winner_id,
                ended,
                black_manual_rank_update,
                white_manual_rank_update
            )
        VALUES
            (
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?
            )
    """,
        (
            game_id,
            black_id,
            white_id,
            handicap,
            winner_id,
            ended,
            black_manual_rank,
            white_manual_rank
        ),
    )

conn.commit()
c.close()
conn.execute("VACUUM")
conn.close()
