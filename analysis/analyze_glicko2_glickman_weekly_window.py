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
    should_skip_game,
)
from goratings.interfaces import GameRecord, RatingSystem, Storage
from goratings.math.glicko2 import Glicko2Entry, glicko2_update

window_width = (7 * 24 * 60 * 60)
no_games_window_witdh = window_width

class DailyWindows(RatingSystem):
    _storage: Storage

    def __init__(self, storage: Storage) -> None:
        self._storage = storage

    def process_game(self, game: GameRecord) -> Glicko2Analytics:
        if should_skip_game(game, self._storage):
            return Glicko2Analytics(skipped=True, game=game)

        ## read base rating (last rating before the current rating period)
        window = (int(game.ended) // window_width) * window_width
        black_base = self._storage.get_first_rating_older_than(game.black_id, window).copy()
        white_base = self._storage.get_first_rating_older_than(game.white_id, window).copy()

        ## since we do not update deviation in periods without games, we have to do update it now if there are empty periods size the base rating was calclulated
        black_base_time = self._storage.get_first_timestamp_older_than(game.black_id, window)
        white_base_time = self._storage.get_first_timestamp_older_than(game.white_id, window)
        
        if black_base_time is not None:
            black_base.expand_deviation_because_no_games_played(int((game.ended - black_base_time) / no_games_window_witdh))
        if white_base_time is not None:
            white_base.expand_deviation_because_no_games_played(int((game.ended - white_base_time) / no_games_window_witdh))

        black_cur = black_base.copy()
        white_cur = white_base.copy()

        ## store games in the match history
        self._storage.add_match_history(game.black_id, game.ended, (game, white_base))
        self._storage.add_match_history(game.white_id, game.ended, (game, black_base))

        ## update ratings
        updated_black = glicko2_update(
            black_base,
            [
                (
                    opponent.copy((1 if past_game.black_id != game.black_id else -1) * get_handicap_adjustment(opponent.rating, past_game.handicap)),
                    past_game.winner_id == past_game.black_id
                )
                for past_game, opponent in self._storage.get_matches_newer_or_equal_to(
                    game.black_id, window
                )
            ]
        )

        updated_white = glicko2_update(
            white_base,
            [
                (
                    opponent.copy((1 if past_game.black_id != game.white_id else -1) * get_handicap_adjustment(opponent.rating, past_game.handicap)),
                    past_game.winner_id == past_game.white_id
                )
                for past_game, opponent in self._storage.get_matches_newer_or_equal_to(
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
                white_cur, get_handicap_adjustment(black_cur.rating, game.handicap), ignore_g=True
            ),
            black_rating=black_cur.rating,
            white_rating=white_cur.rating,
            black_deviation=black_cur.deviation,
            white_deviation=white_cur.deviation,
            black_rank=rating_to_rank(black_cur.rating),
            white_rank=rating_to_rank(white_cur.rating),
            black_updated_rating=updated_black.rating,
            white_updated_rating=updated_white.rating,
        )



# Run
config(cli.parse_args(), name="glicko2-glickman-1-week-window")
ogs_game_data = GameData()
storage = InMemoryStorage(Glicko2Entry)
engine = DailyWindows(storage)
tally = TallyGameAnalytics(storage)

for game in ogs_game_data:
    analytics = engine.process_game(game)
    tally.add_glicko2_analytics(analytics)

tally.print()
