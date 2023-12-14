from goratings.interfaces import (
    GameRecord,
    Storage,
)

from .RatingMath import get_handicap_rank_difference

__all__ = [
    "should_skip_game",
]

def should_skip_game(game: GameRecord, storage: Storage) -> bool:
    ## Only count the first timeout in correspondence games as a ranked loss
    if game.timeout and game.speed == 3: # correspondence timeout
        player_that_timed_out = game.black_id if game.black_id != game.winner_id else game.white_id
        other_player = game.black_id if game.black_id == game.winner_id else game.white_id
        skip = storage.get_timeout_flag(game.black_id) or self._storage.get_timeout_flag(game.white_id)
        storage.set_timeout_flag(player_that_timed_out, True)
        storage.set_timeout_flag(other_player, False)
        if skip:
            return True
    elif game.speed == 3: # correspondence non timeout, clear flags for both
        storage.set_timeout_flag(game.black_id, False)
        storage.set_timeout_flag(game.white_id, False)

    # Skip games with effective handicap > 9, which shouldn't be rated, since
    # they're too noisy. This is mostly old 9x9 and 13x13 games.
    if get_handicap_rank_difference(
            handicap=game.handicap, size=game.size,
            komi=game.komi, rules=game.rules) > 9:
        return True

    return False
