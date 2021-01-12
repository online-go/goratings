#!/usr/bin/env -S PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=..:. pypy3

# Computes one game at a time, for all 16 speed / size combinations

import configparser
from analysis.util import (
    Glicko2Analytics,
    InMemoryStorage,
    GameData,
    TallyGameAnalytics,
    cli,
    config,
    get_handicap_adjustment,
    rating_to_rank,
    rank_to_rating,
)
from goratings.interfaces import GameRecord, RatingSystem, Storage
from goratings.math.glicko2 import Glicko2Entry, glicko2_update
from typing import Dict

cli.add_argument(
    "--always-use-overall-rating", dest="always_use_overall_rating", const=1, default=False, action="store_const", help="Always use our opponents overall rating when updating ratings on a per speed/size basis",
)

ALWAYS_USE_OVERALL = False

class OneGameAtATimeRatingGrid(RatingSystem):
    _storages: Dict[str, Storage]

    def __init__(self, storages: Dict[str, Storage]) -> None:
        self._storages = storages

    def process_game(self, game: GameRecord) -> Dict[str, Glicko2Analytics]:
        global ALWAYS_USE_OVERALL
        ret = {}
        overall_storage = self._storages['999-999']

        for speed in [game.speed, 999]:
            for size in [game.size, 999]:
                k = '%d-%d' % (speed, size)
                storage = self._storages[k]
                if game.black_manual_rank_update is not None:
                    storage.set(game.black_id, Glicko2Entry(rank_to_rating(game.black_manual_rank_update)))

                if game.white_manual_rank_update is not None:
                    storage.set(game.white_id, Glicko2Entry(rank_to_rating(game.white_manual_rank_update)))

                ## Only count the first timeout in correspondence games as a ranked loss
                if game.timeout and game.speed == 3: # correspondence timeout
                    player_that_timed_out = game.black_id if game.black_id != game.winner_id else game.white_id
                    skip = storage.get_timeout_flag(game.black_id) or storage.get_timeout_flag(game.white_id)
                    storage.set_timeout_flag(player_that_timed_out, True)
                    if skip:
                         ret[k] =Glicko2Analytics(skipped=True, game=game)
                         continue
                if game.speed == 3: # clear corr. timeout flags
                    storage.set_timeout_flag(game.black_id, True)
                    storage.set_timeout_flag(game.white_id, True)

                black = storage.get(game.black_id)
                white = storage.get(game.white_id)
                if ALWAYS_USE_OVERALL:
                    src_black = overall_storage.get(game.black_id)
                    src_white = overall_storage.get(game.white_id)
                else:
                    src_black = black
                    src_white = white

                updated_black = glicko2_update(
                    black,
                    [
                        (
                            src_white.copy(-get_handicap_adjustment(src_white.rating, game.handicap)),
                            game.winner_id == game.black_id,
                        )
                    ],
                )

                updated_white = glicko2_update(
                    white,
                    [
                        (
                            src_black.copy(get_handicap_adjustment(src_black.rating, game.handicap)),
                            game.winner_id == game.white_id,
                        )
                    ],
                )

                storage.set(game.black_id, updated_black)
                storage.set(game.white_id, updated_white)
                #storage.add_rating_history(game.black_id, game.ended, updated_black)
                #storage.add_rating_history(game.white_id, game.ended, updated_white)


                ret[k] = Glicko2Analytics(
                    skipped=False,
                    game=game,
                    expected_win_rate=black.expected_win_probability(
                        white, get_handicap_adjustment(black.rating, game.handicap), ignore_g=True
                    ),
                    black_rating=black.rating,
                    white_rating=white.rating,
                    black_deviation=black.deviation,
                    white_deviation=white.deviation,
                    black_rank=rating_to_rank(black.rating),
                    white_rank=rating_to_rank(white.rating),
                    black_updated_rating=updated_black.rating,
                    white_updated_rating=updated_white.rating,
                )


        return ret


# Run
config(cli.parse_args(), "glicko2-one-game-at-a-time")
ALWAYS_USE_OVERALL = config.args.always_use_overall_rating
game_data = GameData()
storages = {
    '999-999': InMemoryStorage(Glicko2Entry),
    '999-9': InMemoryStorage(Glicko2Entry),
    '999-13': InMemoryStorage(Glicko2Entry),
    '999-19': InMemoryStorage(Glicko2Entry),

    '1-999': InMemoryStorage(Glicko2Entry),
    '1-9': InMemoryStorage(Glicko2Entry),
    '1-13': InMemoryStorage(Glicko2Entry),
    '1-19': InMemoryStorage(Glicko2Entry),

    '2-999': InMemoryStorage(Glicko2Entry),
    '2-9': InMemoryStorage(Glicko2Entry),
    '2-13': InMemoryStorage(Glicko2Entry),
    '2-19': InMemoryStorage(Glicko2Entry),

    '3-999': InMemoryStorage(Glicko2Entry),
    '3-9': InMemoryStorage(Glicko2Entry),
    '3-13': InMemoryStorage(Glicko2Entry),
    '3-19': InMemoryStorage(Glicko2Entry),
}
engine = OneGameAtATimeRatingGrid(storages)
tallies = {}
for k in storages.keys():
    tallies[k] = TallyGameAnalytics(storages[k], k if not ALWAYS_USE_OVERALL else ('overall-' + k))

for game in game_data:
    analytics = engine.process_game(game)
    for speed in [game.speed, 999]:
        for size in [game.size, 999]:
            k = '%d-%d' % (speed, size)
            tallies[k].add_glicko2_analytics(analytics[k])

for speed in [999, 1, 2, 3]:
    for size in [999, 9, 13, 19]:
        k = '%d-%d' % (speed, size)
        print(">>>>>>>>>>>>>  %s  <<<<<<<<<<<<<" % k)
        tallies[k].print()

fname = "players_to_inspect.ini"
ini = configparser.ConfigParser()
ini.optionxform = lambda s: s  # type: ignore
ini.read(fname)
for name in ini['ogs']:
    id = int(ini['ogs'][name])
    print('')
    print('%s' % name)
    for size in (999, 9, 13, 19):
        line = ''
        for speed in (999, 1, 2, 3):
            k = '%d-%d' % (speed, size)
            entry = storages[k].get(id)
            line += '%.0f\t' % entry.rating
        print(line)

print('')


self_reported_ratings = tallies['999-999'].get_self_reported_rating()
if self_reported_ratings:
    aga_1d = (self_reported_ratings['aga'][30] if 'aga' in self_reported_ratings else [1950.123456])
    avg_1d_aga = sum(aga_1d) / len(aga_1d)
    egf_1d = (self_reported_ratings['egf'][30] if 'egf' in self_reported_ratings else [1950.123456])
    avg_1d_egf = sum(egf_1d) / len(egf_1d)
    ratings_1d = ((self_reported_ratings['egf'][30] if 'egf' in self_reported_ratings else [1950.123456]) +
                  (self_reported_ratings['aga'][30] if 'aga' in self_reported_ratings else [1950.123456]))
    avg_1d_rating = sum(ratings_1d) / len(ratings_1d)

    print("Avg 1d rating egf: %6.1f    aga: %6.1f     egf+aga: %6.1f" % (avg_1d_egf, avg_1d_aga, avg_1d_rating))


