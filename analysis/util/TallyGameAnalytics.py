import configparser
import os
import sys
from collections import defaultdict
from math import isnan
from typing import DefaultDict, Union

from goratings.interfaces import Storage

from .Glicko2Analytics import Glicko2Analytics
from .RatingMath import rating_to_rank

from sys import argv
from pathlib import Path

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
    predicted_outcome: ResultStorageType
    count: ResultStorageType
    count_black_wins: ResultStorageType
    storage: Storage
    unexpected_rank_changes: ResultStorageType

    def __init__(self, storage: Storage) -> None:
        self.games_ignored = 0
        self.storage = storage
        self.black_wins = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: 0)))
        )
        self.predictions = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: 0.0)))
        )
        self.predicted_outcome = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: 0.0))))
        self.count = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: 0)))
        )
        self.count_black_wins = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: 0)))
        )
        self.unexpected_rank_changes = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: 0)))
        )


    def add_glicko2_analytics(self, result: Glicko2Analytics) -> None:
        if result.skipped:
            return
        if result.black_deviation > 160 or result.white_deviation > 160:
            self.games_ignored += 1
            return

        if abs(result.black_rank + result.game.handicap - result.white_rank) > 1:
            self.games_ignored += 1
            return

        black_won = result.game.winner_id == result.game.black_id
        white_won = result.game.winner_id == result.game.white_id

        for size in [ALL, result.game.size]:
            for speed in [ALL, result.game.speed]:
                for rank in [
                    ALL,
                    str((int(result.black_rank) // 5) * 5) + "+5",
                    int(result.black_rank),
                ]:
                    for handicap in [ALL, result.game.handicap]:
                        if isinstance(rank, int) or isinstance(
                            rank, str
                        ):  # this is just to make mypy happy
                            if abs(result.black_rank + result.game.handicap - result.white_rank) <= 1:
                                self.count_black_wins[size][speed][rank][handicap] += 1
                                if black_won:
                                    self.black_wins[size][speed][rank][handicap] += 1
                            self.predictions[size][speed][rank][handicap] += result.expected_win_rate
                            self.predicted_outcome[size][speed][rank][handicap] += black_won if result.expected_win_rate > 0.5 else (not black_won if result.expected_win_rate < 0.5 else 0.5)
                            self.count[size][speed][rank][handicap] += 1
                            if black_won and not white_won and (result.black_updated_rating - result.black_rating < 0 or
                                                                result.white_updated_rating - result.white_rating > 0):
                                # black won the game but her rating droped
                                self.unexpected_rank_changes[size][speed][rank][handicap] += 1
                            if white_won and not black_won and (result.white_updated_rating - result.white_rating < 0 or
                                                                result.black_updated_rating - result.black_rating > 0):
                                # black won the game but her rating droped
                                self.unexpected_rank_changes[size][speed][rank][handicap] += 1

    def print(self) -> None:
        self.print_handicap_performance()
        self.print_handicap_prediction()
        self.print_inspected_players()
        self.print_compact_stats()

    def print_compact_stats(self) -> None:
        print("")
        print("")
        print("| Algorithm name | Stronger wins | h0 | h1 | h2 | rating changed in the wrong direction |")
        print("|:---------------|--------------:|---:|---:|--------------:|---------------------------------------:")
        print("| {name:>s} | {prediction:>5.1%} | {prediction_h0:>5.1%} | {prediction_h1:>5.1%} | {prediction_h2:>5.1%} | {unexp_change:>8.4%} |".format(name=Path(argv[0]).name,
                                                                                                                     prediction=self.predicted_outcome[19][ALL][ALL][ALL]/self.count[19][ALL][ALL][ALL],
                                                                                                                     prediction_h0=self.predicted_outcome[19][ALL][ALL][0]/self.count[19][ALL][ALL][0],
                                                                                                                     prediction_h1=self.predicted_outcome[19][ALL][ALL][1]/self.count[19][ALL][ALL][1],
                                                                                                                     prediction_h2=self.predicted_outcome[19][ALL][ALL][2]/self.count[19][ALL][ALL][2],
                                                                                                                     unexp_change=self.unexpected_rank_changes[ALL][ALL][ALL][ALL]/self.count[ALL][ALL][ALL][ALL]/2))

    def print_inspected_players(self) -> None:
        config = configparser.ConfigParser()
        config.optionxform = lambda s: s  # type: ignore
        fname = "players_to_inspect.ini"
        if os.path.exists(fname):
            pass
        if os.path.exists("analysis/" + fname):
            fname = "analysis/" + fname
        if os.path.exists("../" + fname):
            fname = "../" + fname
        if os.path.exists(fname):
            config.read(fname)
            if "ogs" in config:
                print("")
                print("Inspected users from %s" % fname)
                for name in config["ogs"]:
                    id = int(config["ogs"][name])
                    entry = self.storage.get(id)
                    last_game = self.storage.get_first_timestamp_older_than(id, 999999999999)
                    if last_game is None:
                        rh = []
                    else:
                        rh = self.storage.get_ratings_newer_or_equal_to(id, last_game - 86400 * 28)
                    print(
                        "%20s    %3s     %s     %4.0f  %4.0f     %3.0f  %3.0f"
                        % (name, num2rank(rating_to_rank(entry.rating)), str(entry), min(rh, key=lambda x: x.rating, default=entry).rating, max(rh, key=lambda x: x.rating, default=entry).rating, min(rh, key=lambda x: x.deviation, default=entry).deviation, max(rh, key=lambda x: x.deviation, default=entry).deviation)
                    )

    def print_handicap_performance(self) -> None:
        for size in [9, 13, 19, ALL]:
            print("")
            if size == ALL:
                print("Overall:   %d games" % self.count_black_wins[size][ALL][ALL][ALL])
            else:
                print(
                    "%dx%d:   %d games" % (size, size, self.count_black_wins[size][ALL][ALL][ALL])
                )

            sys.stdout.write("         ")
            for handicap in range(10):
                sys.stdout.write("  hc %d   " % handicap)
            sys.stdout.write("\n")

            for rank in range(0, 35, 5):
                rankband = "%d+5" % rank
                sys.stdout.write("%3s-%3s  " % (num2rank(rank), num2rank(rank + 4)))
                for handicap in range(10):
                    ct = self.count_black_wins[size][ALL][rankband][handicap]
                    sys.stdout.write(
                        "%5.1f%%   "
                        % (
                            (
                                self.black_wins[size][ALL][rankband][handicap] / ct
                                if ct
                                else 0
                            )
                            * 100.0
                        )
                    )
                sys.stdout.write("\n")

    def print_handicap_prediction(self) -> None:
        for size in [9, 13, 19, ALL]:
            print("")
            if size == ALL:
                print("Overall:   %d games" % self.count[size][ALL][ALL][ALL])
            else:
                print(
                    "%dx%d:   %d games" % (size, size, self.count[size][ALL][ALL][ALL])
                )

            sys.stdout.write("         ")
            for handicap in range(10):
                sys.stdout.write("  hc %d   " % handicap)
            sys.stdout.write("\n")

            for rank in range(0, 35, 5):
                rankband = "%d+5" % rank
                sys.stdout.write("%3s-%3s  " % (num2rank(rank), num2rank(rank + 4)))
                for handicap in range(10):
                    ct = self.count[size][ALL][rankband][handicap]
                    sys.stdout.write(
                        "%5.1f%%   "
                        % (
                            (
                                self.predicted_outcome[size][ALL][rankband][handicap] / ct
                                if ct
                                else 0
                            )
                            * 100.0
                        )
                    )
                sys.stdout.write("\n")


def num2rank(num: float) -> str:
    if isnan(num) or (not num and num != 0):
        return "N/A"
    if int(num) < 30:
        return "%dk" % (30 - int(num))
    return "%dd" % ((int(num) - 30) + 1)
