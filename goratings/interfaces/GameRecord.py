from typing import Optional

__all__ = ["GameRecord"]


class GameRecord:
    game_id: int
    size: int
    handicap: int
    komi: float
    black_id: int
    white_id: int
    time_per_move: int
    timeout: bool
    winner_id: int
    ended: int  # timestamp, seconds since epoch
    black_manual_rank_update: Optional[int]  #
    white_manual_rank_update: Optional[int]  #

    def __init__(
        self,
        game_id: int,
        size: int,
        handicap: int,
        komi: float,
        black_id: int,
        white_id: int,
        time_per_move: int,
        timeout: bool,
        winner_id: int,
        ended: int,
        black_manual_rank_update: Optional[int] = None,
        white_manual_rank_update: Optional[int] = None,
    ):
        self.game_id = game_id
        self.size = size
        self.handicap = handicap
        self.komi = komi
        self.black_id = black_id
        self.white_id = white_id
        self.time_per_move = time_per_move
        self.timeout = timeout
        self.winner_id = winner_id
        self.ended = ended
        self.black_manual_rank_update = black_manual_rank_update
        self.white_manual_rank_update = white_manual_rank_update

    def __str__(self) -> str:
        return "%d\t%d %d vs. %d" % (
            self.ended,
            self.game_id,
            self.black_id,
            self.white_id,
        )

    @property
    def speed(self) -> int:
        if self.time_per_move == 0 or self.time_per_move > 3600:
            return 3  # correspondence
        if self.time_per_move > 15:
            return 2  # live
        return 1  # blitz
