#!/usr/bin/env -S PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=..:. pypy3

import sys
from math import exp, isnan, log, pi, sqrt
from typing import Set

from analysis.util import (
    cli,
    config,
    Glicko2Analytics,
    InMemoryStorage,
    OGSGameData,
    TallyGameAnalytics,
)

from goratings.interfaces import (
    GameRecord,
    RatingSystem,
    Storage,
)

from goratings.math.glicko2 import Glicko2Entry, glicko2_update


MIN_RATING = 100
MAX_RATING = 6000

class OneGameAtATime(RatingSystem):
    _storage: Storage

    def __init__(self, storage: Storage) -> None:
        self._storage = storage

    def process_game(self, game: GameRecord) -> Glicko2Analytics:
        black = self._storage.getGlicko2Entry(game.black_id)
        white = self._storage.getGlicko2Entry(game.white_id)

        updated_black = glicko2_update(
            black,
            [
                (
                    white.copy(-get_handicap_adjustment(white.rating, game.handicap)),
                    game.winner_id == game.black_id,
                )
            ],
        )

        updated_white = glicko2_update(
            white,
            [
                (
                    black.copy(get_handicap_adjustment(black.rating, game.handicap)),
                    game.winner_id == game.white_id,
                )
            ],
        )

        self._storage.setGlicko2Entry(game.black_id, updated_black)
        self._storage.setGlicko2Entry(game.white_id, updated_white)

        return Glicko2Analytics(
            skipped=False,
            game=game,
            expected_win_rate=black.expected_win_probability(
                white, get_handicap_adjustment(black.rating, game.handicap)
            ),
            black_rating=black.rating,
            white_rating=white.rating,
            black_deviation=black.deviation,
            white_deviation=white.deviation,
            black_rank=rating_to_rank(black.rating),
            white_rank=rating_to_rank(white.rating),
        )


def rank_to_rating(rank: float) -> float:
    return 850 * exp(0.032 * rank)

def rating_to_rank(rating: float) -> float:
    return log(min(MAX_RATING, max(MIN_RATING, rating)) / 850.0) / 0.032

def get_handicap_adjustment(rating: float, handicap: int) -> float:
    return rank_to_rating(rating_to_rank(rating) + handicap) - rating



def main():
    cli.add_argument('--rd', dest='rd', type=int, default=350, help="Default rating deviation")
    config(cli.parse_args())


    ogs_game_data = OGSGameData()
    memory_glicko_storage = InMemoryStorage()
    engine = OneGameAtATime(memory_glicko_storage)
    tally = TallyGameAnalytics()

    ct = 0
    for game in ogs_game_data:
        analytics = engine.process_game(game)
        tally.addGlicko2Analytics(analytics)

        ct += 1
        if ct % 10000 == 0:
            sys.stdout.write("\r%d games processed" % ct)

        # if ct >= 10000:
        #    break

    print("\r%d games processed (complete)" % ct)

    tally.print()


main()
