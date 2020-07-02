#!/usr/bin/env -S PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=..:. pypy3

from analysis.util import (
    Glicko2Analytics,
    InMemoryStorage,
    OGSGameData,
    TallyGameAnalytics,
    cli,
    config,
    get_handicap_adjustment,
    rating_to_rank,
)
from goratings.interfaces import GameRecord, RatingSystem, Storage
from goratings.math.glicko2 import Glicko2Entry, glicko2_update


class DailyWindows(RatingSystem):
    _storage: Storage

    def __init__(self, storage: Storage) -> None:
        self._storage = storage

    def process_game(self, game: GameRecord) -> Glicko2Analytics:
        ## Only count the first timeout in correspondence games as a ranked loss
        if game.timeout and game.speed == 3: # correspondence timeout
            player_that_timed_out = game.black_id if game.black_id != game.winner_id else game.white_id
            skip = self._storage.get_timeout_flag(game.black_id) or self._storage.get_timeout_flag(game.white_id)
            self._storage.set_timeout_flag(player_that_timed_out, True)
            if skip:
                return Glicko2Analytics(skipped=True, game=game)
        if game.speed == 3: # clear corr. timeout flags
            self._storage.set_timeout_flag(game.black_id, True)
            self._storage.set_timeout_flag(game.white_id, True)


        window = (int(game.ended) // 86400) * 86400
        black_base = self._storage.get_first_rating_older_than(game.black_id, window)
        white_base = self._storage.get_first_rating_older_than(game.white_id, window)
        black_cur = self._storage.get(game.black_id)
        white_cur = self._storage.get(game.white_id)

        self._storage.add_match_history(game.black_id, game.ended, (game, white_cur))
        self._storage.add_match_history(game.white_id, game.ended, (game, black_cur))

        updated_black = glicko2_update(
            black_base,
            [
                (
                    opponent.copy(get_handicap_adjustment(opponent.rating, game.handicap)),
                    game.winner_id == game.black_id
                )
                for game, opponent in self._storage.get_matches_newer_or_equal_to(
                    game.black_id, window
                )
            ]
        )

        updated_white = glicko2_update(
            white_base,
            [
                (
                    opponent.copy(get_handicap_adjustment(opponent.rating, game.handicap)),
                    game.winner_id == game.white_id
                )
                for game, opponent in self._storage.get_matches_newer_or_equal_to(
                    game.white_id, window
                )
            ]
        )

        self._storage.set(game.black_id, updated_black)
        self._storage.set(game.white_id, updated_white)
        self._storage.add_rating_history(game.black_id, game.ended, updated_black)
        self._storage.add_rating_history(game.white_id, game.ended, updated_white)

        return Glicko2Analytics(
            skipped=False,
            game=game,
            expected_win_rate=black_cur.expected_win_probability(
                white_cur, get_handicap_adjustment(black_cur.rating, game.handicap)
            ),
            black_rating=black_cur.rating,
            white_rating=white_cur.rating,
            black_deviation=black_cur.deviation,
            white_deviation=white_cur.deviation,
            black_rank=rating_to_rank(black_cur.rating),
            white_rank=rating_to_rank(white_cur.rating),
        )



# Run
config(cli.parse_args())
ogs_game_data = OGSGameData()
storage = InMemoryStorage(Glicko2Entry)
engine = DailyWindows(storage)
tally = TallyGameAnalytics(storage)

for game in ogs_game_data:
    analytics = engine.process_game(game)
    tally.add_glicko2_analytics(analytics)

tally.print()
