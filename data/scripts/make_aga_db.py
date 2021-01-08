#!/usr/bin/env pypy3

import csv
import gzip
import json
import sqlite3
import sys
from collections import defaultdict
from math import isnan
from dateutil import parser

AGA_OFFSET = 2000000000


"""
SELECT
0  `Game_ID`,
1  `Tournament_Code`,
2  `Game_Date`,
3  `Round`,
4  `Pin_Player_1`,
5  `Color_1`,
6  `Rank_1`,
7  `Pin_Player_2`,
8  `Color_2`,
9  `Rank_2`,
10  `Handicap`,
11  `Komi`,
12  `Result`,
13  `Online`,
14  `Exclude`,
15  `Rated`,
16  `Elab_Date`
INTO OUTFILE 'games.csv'
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
FROM `games`;

2,"albu405","1994-04-30",1,3794,"W","6d",407,"B","4d",2,0,"B",0,0,1,"1994-05-07"



SELECT
  `Pin_Player`,
  '' as `Name`,
  `Rating`,
  `Sigma`,
  `Elab_Date`
INTO OUTFILE 'players.csv'
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
FROM `players`;

3,"",-2.09381,0.42635,"2004-11-01"


SELECT
  `Pin_Player`,
  `Rating`,
  `Sigma`,
  `Elab_Date`
INTO OUTFILE 'ratings.csv'
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
FROM `ratings`;

10459,0.00000,0.00000,"0000-00-00"
24698,1.41766,0.96060,"2019-07-13"



SELECT
  `Tournament_Code`,
  `Tournament_Descr`,
  `Tournament_Date`
INTO OUTFILE 'tournaments.csv'
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
FROM `tournaments`;

"albu405","Albuquerque Spring Tournament,","1994-04-30"

"""


conn = sqlite3.connect("aga-data.db")
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
        ended INTEGER
    );
"""
)



##
## Import games
##


ct = 0
rows = []
with open("aga/games.csv", "rt") as games_f:
    games_csv = csv.reader(games_f, delimiter=",")
    for row in games_csv:
        ct += 1
        if ct % 1000 == 0:
            sys.stdout.write("%d\r" % ct)
            sys.stdout.flush()
        rows.append(row)

rows = sorted(rows, key=lambda x: "%s-%02d-%04d" % (x[2], int(x[3]), int(x[0]))) # sort by date , round , game_id

last_manual_rank = {}

game_id = AGA_OFFSET

print('')
ct = 0

for row in rows:
    ct += 1
    if ct % 1000 == 0:
        sys.stdout.write("%d\r" % ct)
        sys.stdout.flush()

    exclude = int(row[14])
    if exclude:
        continue

    game_id += 1 # we use our own id's so by id they are ordered by date, round, game id
    ended = parser.parse(row[2]).timestamp()
    p1_id = int(row[4]) + AGA_OFFSET
    p1_color = row[5]
    p2_id = int(row[7]) + AGA_OFFSET
    handicap = int(row[10])

    winner = row[12]

    if winner == "B" or winner == "W":
        winner = 1 if p1_color == winner else 2
    else:
        raise Exception("Invalid winner value: " + winner)


    if p1_color == 'B':
        black_id = p1_id
        white_id = p2_id

    elif p1_color == 'W':
        white_id = p1_id
        black_id = p2_id

    else:
        raise Exception("Bad p1 color: " + p1_color)

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
                ended
            )
        VALUES
            (
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
        ),
    )

c.execute(
    """
    CREATE INDEX black_ended ON game_records (black_id, -ended);
    """
)

c.execute(
    """
    CREATE INDEX white_ended ON game_records (white_id, -ended);
    """
)

conn.commit()
c.close()
conn.execute("VACUUM")
conn.close()
