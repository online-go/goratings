import argparse
from math import exp, log
from typing import Callable

from .CLI import cli, defaults

__all__ = [
    "rank_to_rating",
    "rating_to_rank",
    "get_handicap_adjustment",
]


cli.add_argument(
    "--ranks",
    type=str,
    dest="ranks",
    choices=("log", "linear", "gor", "auto"),
    default="auto",
    help="Use logarithmic, linear, or GoR ranking",
)

logarithmic = cli.add_argument_group(
    "logarithmic ranking variables",
    "rating to ranks converted with `log(rating / a) * c`",
)
logarithmic.add_argument("-a", dest="a", type=float, default=850.0, help="a")
logarithmic.add_argument("-c", dest="c", type=float, default=31.25, help="c")

linear = cli.add_argument_group(
    "linear ranking variables", "rating to ranks converted with `rating / m + b`"
)
linear.add_argument("-m", dest="m", type=float, default=100.0, help="m")
linear.add_argument("-b", dest="b", type=float, default=9.0, help="b")


_rank_to_rating: Callable[[float], float]
_rating_to_rank: Callable[[float], float]


def rank_to_rating(rank: float) -> float:
    return _rank_to_rating(rank)


def rating_to_rank(rating: float) -> float:
    return _rating_to_rank(rating)


def get_handicap_adjustment(rating: float, handicap: int) -> float:
    return rank_to_rating(rating_to_rank(rating) + handicap) - rating


def configure_rating_to_rank(args: argparse.Namespace) -> None:
    global _rank_to_rating
    global _rating_to_rank

    system: str = args.ranks
    a: float = args.a
    c: float = args.c
    m: float = args.m
    b: float = args.b

    if system == "auto":
        system = defaults["ranking"]

    if system == "linear":
        def __rank_to_rating(rank: float) -> float:
            return (rank - b) * m

        def __rating_to_rank(rating: float) -> float:
            return (rating / m) + b

        _rank_to_rating = __rank_to_rating
        _rating_to_rank = __rating_to_rank
    elif system == "gor":
        def __rank_to_rating(rank: float) -> float:
            return (rank - 9) * 100

        def __rating_to_rank(rating: float) -> float:
            return (rating / 100.0)  + 9

        _rank_to_rating = __rank_to_rating
        _rating_to_rank = __rating_to_rank
    elif system == "log":

        def __rank_to_rating(rank: float) -> float:
            return a * exp(rank / c)

        def __rating_to_rank(rating: float) -> float:
            return log(rating / a) * c

        _rank_to_rating = __rank_to_rating
        _rating_to_rank = __rating_to_rank
    else:
        raise NotImplementedError

    assert get_handicap_adjustment(1000.0, 0) == 0
