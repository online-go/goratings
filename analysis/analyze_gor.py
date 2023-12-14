#!/usr/bin/env -S PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=..:. pypy3

from analysis.util import (
    GorAnalytics,
    InMemoryStorage,
    GameData,
    TallyGameAnalytics,
    cli,
    config,
    defaults,
    get_handicap_adjustment,
    rating_to_rank,
    rank_to_rating,
    should_skip_game,
)
from goratings.interfaces import GameRecord, RatingSystem, Storage
from goratings.math.gor import GorEntry, gor_update

ID = 1016213560
defaults['data'] = 'egf';
defaults['ranking'] = 'gor';


class OneGameAtATime(RatingSystem):
    _storage: Storage

    def __init__(self, storage: Storage) -> None:
        self._storage = storage

    def process_game(self, game: GameRecord) -> GorAnalytics:
        if game.black_manual_rank_update is not None:
            storage.clear_set_count(game.black_id)
            storage.set(game.black_id, GorEntry(rank_to_rating(game.black_manual_rank_update)))

        if game.white_manual_rank_update is not None:
            storage.clear_set_count(game.white_id)
            storage.set(game.white_id, GorEntry(rank_to_rating(game.white_manual_rank_update)))

        if should_skip_game(game, self._storage):
            return GorAnalytics(skipped=True, game=game)

        black = self._storage.get(game.black_id)
        white = self._storage.get(game.white_id)


        updated_black = gor_update(
            black.with_handicap(get_handicap_adjustment(black.rating, game.handicap,
                    komi=game.komi, size=game.size, rules=game.rules,
                    )),
            #white.with_handicap(-get_handicap_adjustment(white.rating, game.handicap, ...)),
            white,
            1 if game.winner_id == game.black_id else 0,
        )

        updated_white = gor_update(
            white,
            black.with_handicap(get_handicap_adjustment(black.rating, game.handicap,
                    komi=game.komi, size=game.size, rules=game.rules,
                    )),
            1 if game.winner_id == game.white_id else 0,
        )

        self._storage.set(game.black_id, updated_black)
        self._storage.set(game.white_id, updated_white)

        black_games_played = self._storage.get_set_count(game.black_id)
        white_games_played = self._storage.get_set_count(game.white_id)

        return GorAnalytics(
            skipped=False,
            game=game,
            expected_win_rate=black.with_handicap(get_handicap_adjustment(white.rating, game.handicap,
                    komi=game.komi, size=game.size, rules=game.rules,
                    )).expected_win_probability(
                #white.copy(-get_handicap_adjustment(white.rating, game.handicap, ...))
                white
            ),
            black_rating=black.rating,
            white_rating=white.rating,
            black_rank=rating_to_rank(black.rating),
            white_rank=rating_to_rank(white.rating),
            black_games_played = black_games_played,
            white_games_played = white_games_played,
        )



# Run
config(cli.parse_args(), "gor")
game_data = GameData()
storage = InMemoryStorage(GorEntry)
engine = OneGameAtATime(storage)
tally = TallyGameAnalytics(storage)

for game in game_data:
    analytics = engine.process_game(game)
    #analytics = engine.process_game(game)
    tally.add_gor_analytics(analytics)

tally.print()
