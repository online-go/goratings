from goratings.interfaces import GameAnalytics, GameRecord

__all__ = ["GorAnalytics"]


class GorAnalytics(GameAnalytics):
    expected_win_rate: float  # probability that black will win
    black_rating: float
    white_rating: float
    black_rank: float
    white_rank: float

    def __init__(
        self,
        skipped: bool,
        game: GameRecord,
        expected_win_rate: float = 0,
        black_rating: float = 0,
        white_rating: float = 0,
        black_rank: float = 0,
        white_rank: float = 0,
    ) -> None:
        super().__init__(skipped, game)
        self.expected_win_rate = expected_win_rate
        self.black_rating = black_rating
        self.white_rating = white_rating
        self.black_rank = black_rank
        self.white_rank = white_rank

    def __str__(self) -> str:
        return "%.1f vs %.1f (hc: %d)  Expected win rate: %.1f" % (
            self.black_rating,
            self.white_rating,
            self.game.handicap,
            self.expected_win_rate,
        )
