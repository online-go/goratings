from collections import defaultdict
from math import isnan
from typing import DefaultDict, Union
from goratings.interfaces import Storage
import os
import configparser
import sys

from .Glicko2Analytics import Glicko2Analytics
from .rating2rank import rating_to_rank

__all__ = ["TallyGameAnalytics"]


ALL: int = 999

# Result storage is indexed by size, speed, rank, handicap
# Board size, `ALL` for all
# Game speed, `ALL` for all, 1=blitz, 2=live, 3=correspondence
# rank, or rank+5 for 5 rank bands (the str "0+5", "5+5", "10+5", etc), `ALL` for all
# Handicap, 0-9 or `ALL` for all
ResultStorageType = DefaultDict[
    int,
    DefaultDict[int, DefaultDict[Union[int, str], DefaultDict[int, Union[int, float]]]],
]


class TallyGameAnalytics:
    games_ignored: int
    black_wins: ResultStorageType
    predictions: ResultStorageType
    count: ResultStorageType
    storage: Storage

    def __init__(self, storage: Storage) -> None:
        self.games_ignored = 0
        self.storage = storage
        self.black_wins = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: 0)))
        )
        self.predictions = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: 0.0)))
        )
        self.count = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: 0)))
        )

    def addGlicko2Analytics(self, result: Glicko2Analytics) -> None:
        if result.black_deviation > 160 or result.white_deviation > 160:
            self.games_ignored += 1
            return

        if abs(result.black_rank + result.game.handicap - result.white_rank) > 1:
            self.games_ignored += 1
            return

        black_won = result.game.winner_id == result.game.black_id

        for size in [ALL, result.game.size]:
            for speed in [ALL, result.game.speed]:
                for rank in [
                    ALL,
                    str((int(result.black_rank) // 5)*5) + "+5",
                    int(result.black_rank),
                ]:
                    for handicap in [ALL, result.game.handicap]:
                        if isinstance(rank, int) or isinstance(
                            rank, str
                        ):  # this is just to make mypy happy
                            if black_won:
                                self.black_wins[size][speed][rank][handicap] += 1
                            self.predictions[size][speed][rank][
                                handicap
                            ] += result.expected_win_rate
                            self.count[size][speed][rank][handicap] += 1

    def print(self) -> None:
        self.print_handicap_performance()
        self.print_inspected_players()

    def print_inspected_players(self) -> None:
        config = configparser.ConfigParser()
        config.optionxform = str
        fname = 'players_to_inspect.ini'
        if os.path.exists(fname):
            pass
        if os.path.exists('analytics/' + fname):
            fname = 'analytics/' + fname
        if os.path.exists('../' + fname):
            fname = '../' + fname
        if os.path.exists(fname):
            config.read(fname)
            if 'ogs' in config:
                print('')
                print('Inspected users from %s' % fname)
                for name in config['ogs']:
                    id = int(config['ogs'][name])
                    entry = self.storage.get(id)
                    print('%20s    %3s     %s' % (name, num2rank(rating_to_rank(entry.rating)), str(entry)))


    def print_handicap_performance(self) -> None:
        for size in [9, 13, 19, ALL]:
            print('')
            if size == ALL:
                print('Overall:   %d games' % self.count[size][ALL][ALL][ALL])
            else:
                print('%dx%d:   %d games' % (size, size, self.count[size][ALL][ALL][ALL]))

            sys.stdout.write('         ')
            for handicap in range(10):
                sys.stdout.write('  hc %d   ' % handicap)
            sys.stdout.write('\n')

            for rank in range(0, 35, 5):
                rankband = '%d+5' % rank
                sys.stdout.write('%3s-%3s  ' % (num2rank(rank), num2rank(rank+4)))
                for handicap in range(10):
                    ct = self.count[size][ALL][rankband][handicap]
                    sys.stdout.write('%5.1f%%   ' %
                        ((self.black_wins[size][ALL][rankband][handicap] / ct if ct else 0) * 100.0)
                    )
                sys.stdout.write('\n')





def num2rank(num: int) -> str:
    if isnan(num) or (not num and num != 0):
        return "N/A"
    if int(num) < 30:
        return "%dk" % (30 - int(num))
    return "%dd" % ((int(num) - 30) + 1)
