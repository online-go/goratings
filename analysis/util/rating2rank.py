from typing import Callable
from math import exp, log

from .cli import cli


__all__ = [
    "rank_to_rating",
    "rating_to_rank",
    "get_handicap_adjustment",
]




cli.add_argument('--ranks', type=str, dest='ranks', choices=('log', 'linear', 'auto'), default='auto', help='Use logarithmic or linear ranking')

logarithmic = cli.add_argument_group('logarithmic ranking variables', 'rating to ranks converted with `log(rating / a) * c`')
logarithmic.add_argument('-a', dest='a', type=float, default=850.0, help='a')
logarithmic.add_argument('-c', dest='c', type=float, default=31.25, help='c')

linear = cli.add_argument_group('linear ranking variables', 'rating to ranks converted with `rating / m + b`')
linear.add_argument('-m', dest='m', type=float, default=100.0, help='m')
linear.add_argument('-b', dest='b', type=float, default=9.0, help='b')


_rank_to_rating: Callable[[float], float]
_rating_to_rank: Callable[[float], float]

def rank_to_rating(rank: float) -> float:
    return _rank_to_rating(rank)

def rating_to_rank(rating: float) -> float:
    return _rating_to_rank(rating)

def get_handicap_adjustment(rating: float, handicap: int) -> float:
    return rank_to_rating(rating_to_rank(rating) + handicap) - rating

def configure_rating_to_rank(args):
    global _rank_to_rating
    global _rating_to_rank

    system:str = args.ranks
    a:float = args.a
    c:float = args.c
    m:float = args.m
    b:float = args.b

    if system == 'auto':
        system = 'log'

    if system == 'linear':
        _rank_to_rating = lambda rank: (rank - b) * m
        _rating_to_rank = lambda rating: (rating / m) + b
    elif system == 'log':
        _rank_to_rating = lambda rank: a * exp(rank / c)
        _rating_to_rank = lambda rating: log(rating / a) * c
    else:
        raise NotImplementedError

    assert get_handicap_adjustment(1000.0, 0) == 0
