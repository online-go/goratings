#!/usr/bin/env -S PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=..:. pypy3

from analysis.util import (
    cli,
    config,
    Glicko2Analytics,
    InMemoryStorage,
    OGSGameData,
    TallyGameAnalytics,
    rating_to_rank,
    get_handicap_adjustment,
)

from goratings.interfaces import (
    GameRecord,
    RatingSystem,
    Storage,
)

from goratings.math.glicko2 import Glicko2Entry, glicko2_update


class OneGameAtATime(RatingSystem):
    _storage: Storage

    def __init__(self, storage: Storage) -> None:
        self._storage = storage

    def process_game(self, game: GameRecord) -> Glicko2Analytics:
        black = self._storage.get(game.black_id)
        white = self._storage.get(game.white_id)

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

        self._storage.set(game.black_id, updated_black)
        self._storage.set(game.white_id, updated_white)

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



# Run
config(cli.parse_args())
ogs_game_data = OGSGameData()
storage = InMemoryStorage(Glicko2Entry)
engine = OneGameAtATime(storage)
tally = TallyGameAnalytics(storage)

for game in ogs_game_data:
    analytics = engine.process_game(game)
    tally.addGlicko2Analytics(analytics)

tally.print()
