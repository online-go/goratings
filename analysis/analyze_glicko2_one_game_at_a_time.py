#!/usr/bin/env -S PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=..:. pypy3

import sys
import logging
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
    should_skip_game,
)
from analysis.util.InMemoryWithStartingRankStorage import (
    InMemoryStorageWithStartingRankStorage,
)
from goratings.interfaces import GameRecord, RatingSystem, Storage
from goratings.math.glicko2 import Glicko2Entry, glicko2_update


class OneGameAtATime(RatingSystem):
    _storage: Storage

    def __init__(self, storage: Storage) -> None:
        self._storage = storage

    def process_game(self, game: GameRecord) -> Glicko2Analytics:
        if game.black_manual_rank_update is not None:
            self._storage.set(
                game.black_id,
                Glicko2Entry(rank_to_rating(game.black_manual_rank_update)),
            )

        if game.white_manual_rank_update is not None:
            self._storage.set(
                game.white_id,
                Glicko2Entry(rank_to_rating(game.white_manual_rank_update)),
            )

        if should_skip_game(game, self._storage):
            return Glicko2Analytics(skipped=True, game=game)

        black = self._storage.get(game.black_id)
        white = self._storage.get(game.white_id)

        updated_black = glicko2_update(
            black,
            [
                (
                    white.copy(
                        get_handicap_adjustment(
                            "white",
                            white.rating,
                            game.handicap,
                            komi=game.komi,
                            size=game.size,
                            rules=game.rules,
                        )
                    ),
                    game.winner_id == game.black_id,
                )
            ],
            timestamp=game.ended,
        )

        updated_white = glicko2_update(
            white,
            [
                (
                    black.copy(
                        get_handicap_adjustment(
                            "black",
                            black.rating,
                            game.handicap,
                            komi=game.komi,
                            size=game.size,
                            rules=game.rules,
                        )
                    ),
                    game.winner_id == game.white_id,
                )
            ],
            timestamp=game.ended,
        )

        self._storage.set(game.black_id, updated_black)
        self._storage.set(game.white_id, updated_white)
        # self._storage.add_rating_history(game.black_id, game.ended, updated_black)
        # self._storage.add_rating_history(game.white_id, game.ended, updated_white)

        return Glicko2Analytics(
            skipped=False,
            game=game,
            expected_win_rate=black.expected_win_probability(
                white,
                get_handicap_adjustment(
                    "black",
                    black.rating,
                    game.handicap,
                    komi=game.komi,
                    size=game.size,
                    rules=game.rules,
                ),
                ignore_g=True,
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


# Run
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

cli.add_argument(
    "--starting-ranks",
    dest="starting_ranks",
    action="store_true",
    help="Use a two pass system to bin players into an appropriate starting rank.",
)

config(cli.parse_args(), "glicko2-one-game-at-a-time")
game_data = GameData()

if config.args.starting_ranks:
    storage = InMemoryStorageWithStartingRankStorage(Glicko2Entry)
else:
    storage = InMemoryStorage(Glicko2Entry)

engine = OneGameAtATime(storage)
tally = TallyGameAnalytics(storage)

for game in game_data:
    analytics = engine.process_game(game)
    tally.add_glicko2_analytics(analytics)

tally.print()

storage.finalize()

self_reported_ratings = tally.get_self_reported_rating()
if self_reported_ratings:
    aga_1d = (
        self_reported_ratings["aga"][30]
        if "aga" in self_reported_ratings
        else [1950.123456]
    )
    avg_1d_aga = sum(aga_1d) / len(aga_1d)
    egf_1d = (
        self_reported_ratings["egf"][30]
        if "egf" in self_reported_ratings
        else [1950.123456]
    )
    avg_1d_egf = sum(egf_1d) / len(egf_1d)
    ratings_1d = (
        self_reported_ratings["egf"][30]
        if "egf" in self_reported_ratings
        else [1950.123456]
    ) + (
        self_reported_ratings["aga"][30]
        if "aga" in self_reported_ratings
        else [1950.123456]
    )
    avg_1d_rating = sum(ratings_1d) / len(ratings_1d)

    print(
        "Avg 1d rating egf: %6.1f    aga: %6.1f     egf+aga: %6.1f"
        % (avg_1d_egf, avg_1d_aga, avg_1d_rating)
    )
