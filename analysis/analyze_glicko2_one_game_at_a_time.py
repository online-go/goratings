#!/usr/bin/env -S PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=..:. pypy3

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
from goratings.interfaces import GameRecord, RatingSystem, Storage
from goratings.math.glicko2 import Glicko2Entry, glicko2_update

class OneGameAtATime(RatingSystem):
    _storage: Storage

    def __init__(self, storage: Storage) -> None:
        self._storage = storage

    def process_game(self, game: GameRecord) -> Glicko2Analytics:
        if game.black_manual_rank_update is not None:
            self._storage.set(game.black_id, Glicko2Entry(rank_to_rating(game.black_manual_rank_update)))

        if game.white_manual_rank_update is not None:
            self._storage.set(game.white_id, Glicko2Entry(rank_to_rating(game.white_manual_rank_update)))

        if should_skip_game(game, self._storage):
            return Glicko2Analytics(skipped=True, game=game)

        black = self._storage.get(game.black_id)
        white = self._storage.get(game.white_id)

        updated_black = glicko2_update(
            black,
            [
                (
                    white.copy(get_handicap_adjustment("white", white.rating, game.handicap,
                                                        komi=game.komi, size=game.size,
                                                        rules=game.rules,
                            )),
                    game.winner_id == game.black_id,
                )
            ],
            timestamp=game.ended,
        )

        updated_white = glicko2_update(
            white,
            [
                (
                    black.copy(get_handicap_adjustment("black", black.rating, game.handicap,
                                                       komi=game.komi, size=game.size,
                                                       rules=game.rules,
                            )),
                    game.winner_id == game.white_id,
                )
            ],
            timestamp=game.ended,
        )

        self._storage.set(game.black_id, updated_black)
        self._storage.set(game.white_id, updated_white)
        #self._storage.add_rating_history(game.black_id, game.ended, updated_black)
        #self._storage.add_rating_history(game.white_id, game.ended, updated_white)

        return Glicko2Analytics(
            skipped=False,
            game=game,
            expected_win_rate=black.expected_win_probability(
                white, get_handicap_adjustment("black", black.rating, game.handicap,
                                               komi=game.komi, size=game.size,
                                               rules=game.rules,
                    ), ignore_g=True
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

cli.add_argument(
    "--detect-starting-ratings", dest="detect_starting_ratings",
    const=1, default=False, action="store_const",
    help="Detect starting ratings by running analysis twice",
)

def detect_starting_ratings(storage: InMemoryStorage):
    detection_storage = InMemoryStorage(Glicko2Entry)
    detection_engine = OneGameAtATime(detection_storage)
    detection_data = GameData()

    def parse_rank(rank: str) -> float:
        if rank[-1:] == "k":
            return 30 - float(rank[:-1])
        if rank[-1:] == "d":
            return 30 + float(rank[:-1]) - 1
        raise ValueError("invalid rank")

    STARTING_RANK_DEVIATION = 250
    PROVISIONAL_RANK_CUTOFF = 160
    def make_starting_rating(rank: str) -> Glicko2Entry:
        rating = rank_to_rating(parse_rank(rank))
        return Glicko2Entry(rating=rating, deviation=STARTING_RANK_DEVIATION)

    starting_rating_newtogo = make_starting_rating("25k")
    starting_rating_basic = make_starting_rating("22k")
    starting_rating_intermediate = make_starting_rating("12k")
    starting_rating_advanced = make_starting_rating("2k")

    weaker_threshold_detect_newtogo = rank_to_rating(parse_rank("35k"))
    weaker_threshold_detect_basic = rank_to_rating(parse_rank("20k"))
    weaker_threshold_detect_intermediate = rank_to_rating(parse_rank("10k"))
    stronger_threshold_detect_advanced = rank_to_rating(parse_rank("4k"))
    def update_starting_rating(player: int, rating: float, deviation: float) -> None:
        # Ever worse than 35k? New to Go.
        if rating < weaker_threshold_detect_newtogo:
            storage.set(player, starting_rating_newtogo)
            return

        # Ever worse than 20k, but not new to Go? Basic.
        if rating < weaker_threshold_detect_basic:
            if storage.get(player).rating != starting_rating_newtogo.rating:
                storage.set(player, starting_rating_basic)
            return

        # First non-provisional rating is weaker than 10k. Intermediate.
        if rating < weaker_threshold_detect_intermediate and deviation <= PROVISIONAL_RANK_CUTOFF:
            if storage.get(player).deviation > STARTING_RANK_DEVIATION:
                storage.set(player, starting_rating_intermediate)
            return

        # First non-provisional rating is stronger than 4k. Advanced.
        if rating > stronger_threshold_detect_advanced and deviation <= PROVISIONAL_RANK_CUTOFF:
            if storage.get(player).deviation > STARTING_RANK_DEVIATION:
                storage.set(player, starting_rating_advanced)
            return

    for game in detection_data:
        result = detection_engine.process_game(game)
        update_starting_rating(result.game.black_id, result.black_rating, result.black_deviation)
        update_starting_rating(result.game.white_id, result.white_rating, result.white_deviation)


# Run
config(cli.parse_args(), "glicko2-one-game-at-a-time")

game_data = GameData()
storage = InMemoryStorage(Glicko2Entry)
engine = OneGameAtATime(storage)
tally = TallyGameAnalytics(storage)

if config.args.detect_starting_ratings:
    detect_starting_ratings(storage)

for game in game_data:
    analytics = engine.process_game(game)
    tally.add_glicko2_analytics(analytics)

tally.print()

self_reported_ratings = tally.get_self_reported_rating()
if self_reported_ratings:
    aga_1d = (self_reported_ratings['aga'][30] if 'aga' in self_reported_ratings else [1950.123456])
    avg_1d_aga = sum(aga_1d) / len(aga_1d)
    egf_1d = (self_reported_ratings['egf'][30] if 'egf' in self_reported_ratings else [1950.123456])
    avg_1d_egf = sum(egf_1d) / len(egf_1d)
    ratings_1d = ((self_reported_ratings['egf'][30] if 'egf' in self_reported_ratings else [1950.123456]) +
                  (self_reported_ratings['aga'][30] if 'aga' in self_reported_ratings else [1950.123456]))
    avg_1d_rating = sum(ratings_1d) / len(ratings_1d)

    print("Avg 1d rating egf: %6.1f    aga: %6.1f     egf+aga: %6.1f" % (avg_1d_egf, avg_1d_aga, avg_1d_rating))



