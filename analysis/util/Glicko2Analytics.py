from goratings.interfaces import GameAnalytics, GameRecord


__all__ = ["Glicko2Analytics"]


class Glicko2Analytics(GameAnalytics):
    expected_win_rate: float  # probability that black will win
    black_rating: float
    white_rating: float
    black_deviation: float
    white_deviation: float
    black_rank: float
    white_rank: float

    def __init__(
        self,
        skipped: bool,
        game: GameRecord,
        expected_win_rate: float,
        black_rating: float,
        white_rating: float,
        black_deviation: float,
        white_deviation: float,
        black_rank: float,
        white_rank: float,
    ) -> None:
        super().__init__(skipped, game)
        self.expected_win_rate = expected_win_rate
        self.black_rating = black_rating
        self.white_rating = white_rating
        self.black_deviation = black_deviation
        self.white_deviation = white_deviation
        self.black_rank = black_rank
        self.white_rank = white_rank

    def __str__(self) -> str:
        return "%.1f vs %.1f (hc: %d)  Expected win rate: %.1f" % (
            self.black_rating,
            self.white_rating,
            self.game.handicap,
            self.expected_win_rate,
        )
