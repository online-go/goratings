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

        ## store games in the match history
        self._storage.add_match_history(game.black_id, game.ended, (game, white_base))
        self._storage.add_match_history(game.white_id, game.ended, (game, black_base))

        ## update ratings
        updated_black = glicko2_update(
            black_base,
            [
                (
                    opponent.copy(get_handicap_adjustment(
                            "black" if past_game.black_id != game.black_id else "white",
                            opponent.rating, past_game.handicap,
                            komi=past_game.komi, size=past_game.size, rules=past_game.rules,
                            )),
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
                    opponent.copy(get_handicap_adjustment(
                            "black" if past_game.black_id != game.black_id else "white",
                            opponent.rating, past_game.handicap,
                            komi=past_game.komi, size=past_game.size, rules=past_game.rules,
                            )),
                    past_game.winner_id == past_game.white_id
                )
                for past_game, opponent in self._storage.get_matches_newer_or_equal_to(
                    game.white_id, window
                )
            ]
        )

        # do not decrease rating if player won or increase if she lost
        # users complain when their rating drops after they won a game, even if it is only by a few points. This happens
        # regular since the deviation becomes lower with each game played in a period.
        # Here we accept the rating system to be slightly less accurate for the sake of user experience. Since we use
        # the base rating of  both players when updating the ratings, this only affects future rating updates if this
        # game happens to be the last game in the rating period of the affected player.
        black_cur = self._storage.get(game.black_id).copy()
        white_cur = self._storage.get(game.white_id).copy()
        if (game.winner_id == game.black_id and updated_black.rating - black_cur.rating < 0) or \
            (game.winner_id != game.black_id and updated_black.rating - black_cur.rating > 0):
            updated_black = Glicko2Entry(rating=black_cur.rating, deviation=updated_black.deviation, volatility=updated_black.volatility)
        if (game.winner_id == game.white_id and updated_white.rating - white_cur.rating < 0) or \
            (game.winner_id != game.white_id and updated_white.rating - white_cur.rating > 0):
            updated_white = Glicko2Entry(rating=white_cur.rating, deviation=updated_white.deviation, volatility=updated_white.volatility)

        self._storage.set(game.black_id, updated_black)
        self._storage.set(game.white_id, updated_white)
        self._storage.add_rating_history(game.black_id, game.ended, updated_black)
        self._storage.add_rating_history(game.white_id, game.ended, updated_white)

        return Glicko2Analytics(
            skipped=False,
            game=game,
            expected_win_rate=black_cur.expected_win_probability(
                white_cur, get_handicap_adjustment("black", black_cur.rating, game.handicap,
                    komi=game.komi, size=game.size, rules=game.rules,
                    ), ignore_g=True
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
config(cli.parse_args(), name="glicko2-week-window-no-unexpected-changes")
ogs_game_data = GameData()
storage = InMemoryStorage(Glicko2Entry)
engine = DailyWindows(storage)
tally = TallyGameAnalytics(storage)

for game in ogs_game_data:
    analytics = engine.process_game(game)
    tally.add_glicko2_analytics(analytics)

tally.print()
