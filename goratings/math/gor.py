from math import exp
from typing import Callable

__all__ = ["GorEntry", "gor_update", "gor_configure"]

EPSILON: float = 0.016
RATING_TO_RANK: Callable[[float], float] = lambda rating: rating / 100 + 9


class GorEntry:
    rating: float
    handicap: float

    def __init__(self, rating: float = 1200.0, handicap: float = 0.0) -> None:
        self.rating = rating
        self.handicap = handicap

    def expected_win_probability(self, opponent: "GorEntry") -> float:
        D = (opponent.rating + opponent.handicap) - (self.rating + self.handicap)
        a = compute_a(min(self.rating + self.handicap, opponent.rating + opponent.handicap))  # self.rating)
        # print("D = %f  a = %f" % (D, a))
        return 1 / (exp(D / a) + 1) - (EPSILON / 2)

    def with_handicap(self, handicap: float = 0.0) -> "GorEntry":
        ret = GorEntry(self.rating, handicap)
        return ret

    def __str__(self) -> str:
        return "%6.2f" % self.rating


def compute_a(gor: float) -> float:
    global RATING_TO_RANK
    ret: float = max(70, 205 - (RATING_TO_RANK(gor) - 9) * 5)
    return ret


def compute_con(rank: float) -> float:
    conlist = [
        (10, 116),
        (11, 110),
        (12, 105),
        (13, 100),
        (14, 95),
        (15, 90),
        (16, 85),
        (17, 80),
        (18, 75),
        (19, 70),
        (20, 65),
        (21, 60),
        (22, 55),
        (23, 51),
        (24, 47),
        (25, 43),
        (26, 39),
        (27, 35),
        (28, 31),
        (29, 27),
        (30, 24),
        (31, 21),
        (32, 18),
        (33, 15),
        (34, 13),
        (35, 11),
        (36, 10),
    ]

    last_con = 116

    for (r, con) in conlist:
        if rank <= r:
            return (r - rank) * last_con + (1 - (r - rank)) * con
        last_con = con

    return 10


def gor_update(player: GorEntry, opponent: GorEntry, outcome: float) -> GorEntry:
    K = compute_con(RATING_TO_RANK(player.rating))
    # print("K = %f  " % K)
    expected = player.expected_win_probability(opponent)
    return GorEntry(player.rating + K * (outcome - expected))


def gor_configure(
    epsilon: float = 0.016, rating_to_rank: Callable[[float], float] = lambda rating: rating / 100 + 9,
) -> None:
    global EPSILON
    global RATING_TO_RANK

    EPSILON = epsilon
    RATING_TO_RANK = rating_to_rank


gor_configure()
