import configparser
import json
import os
import sys
from collections import defaultdict
from math import isnan
from time import time
from typing import Any, DefaultDict, Dict, Union

from goratings.interfaces import Storage

from .Config import config
from .GameData import datasets_used
from .Glicko2Analytics import Glicko2Analytics
from .GorAnalytics import GorAnalytics
from .RatingMath import rating_config, rating_to_rank

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
                            if black_won:
                                self.black_wins[size][speed][rank][handicap] += 1
                            self.predictions[size][speed][rank][
                                handicap
                            ] += result.expected_win_rate
                            self.count[size][speed][rank][handicap] += 1

    def add_gor_analytics(self, result: GorAnalytics) -> None:
        if result.skipped:
            return

        if result.black_games_played < 5 or result.white_games_played < 5:
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
                    str((int(result.black_rank) // 5) * 5) + "+5",
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
        self.update_visualizer_data()

    def print_inspected_players(self) -> None:
        ini = configparser.ConfigParser()
        ini.optionxform = lambda s: s  # type: ignore
        fname = "players_to_inspect.ini"
        if os.path.exists(fname):
            pass
        if os.path.exists("analysis/" + fname):
            fname = "analysis/" + fname
        if os.path.exists("../" + fname):
            fname = "../" + fname
        if os.path.exists(fname):
            ini.read(fname)

            sections = []

            datasets = datasets_used()

            if datasets["ogs"]:
                sections.append("ogs")

            if datasets["egf"]:
                sections.append("egf")

            for section in sections:
                print("")
                print("Inspected %s users from %s" % (section, fname))
                for name in ini[section]:
                    id = int(ini[section][name])
                    entry = self.storage.get(id)
                    print(
                        "%20s    %3s     %s"
                        % (name, num2rank(rating_to_rank(entry.rating)), str(entry))
                    )

    def print_handicap_performance(self) -> None:
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
                                self.black_wins[size][ALL][rankband][handicap] / ct
                                if ct
                                else 0
                            )
                            * 100.0
                        )
                    )
                sys.stdout.write("\n")

    def get_config(self) -> Any:
        ret: Dict[str, Any] = {}

        ds_used = datasets_used()
        datasets = []
        for key in ds_used:
            if ds_used[key]:
                datasets.append(key)
        ret["name"] = config.name
        ret["datasets"] = datasets
        ret["num_games"] = config.args.num_games
        ret["rating_config"] = rating_config

        return ret

    def get_descriptive_name(self) -> str:
        cfg = self.get_config()

        lst = [
            cfg["name"],
            ",".join(cfg["datasets"]),
            str(cfg["num_games"]),
            cfg["rating_config"]["system"],
        ]

        if "a" in cfg["rating_config"]:
            lst.append(str(cfg["rating_config"]["a"]))
        if "b" in cfg["rating_config"]:
            lst.append(str(cfg["rating_config"]["b"]))
        if "c" in cfg["rating_config"]:
            lst.append(str(cfg["rating_config"]["c"]))
        if "m" in cfg["rating_config"]:
            lst.append(str(cfg["rating_config"]["m"]))

        return ":".join(lst)

    def update_visualizer_data(self) -> Any:
        fname: str = "data.json"

        if os.path.exists("visualizer/"):
            fname = "visualizer/data.json"
        elif os.path.exists("analysis/visualizer/"):
            fname = "analysis/visualizer/data.json"
        else:
            raise Exception("Can't find visualizer directory")

        data: Any = {}

        if os.path.exists(fname):
            with open(fname, "r") as f:
                data = json.load(f)

        obj: Any = {}
        obj["name"] = self.get_descriptive_name()
        obj["timestamp"] = time()
        obj["black_wins"] = self.black_wins
        obj["predictions"] = self.predictions
        obj["count"] = self.count
        obj["ignored"] = self.games_ignored
        obj["config"] = self.get_config()

        rank_distribution: Any = defaultdict(lambda: 0)
        for _id, player in self.storage.all_players().items():
            rank = num2rank(rating_to_rank(player.rating))
            rank_distribution[rank] += 1

        obj["rank_distribution"] = rank_distribution

        data[obj["name"]] = obj

        with open(fname, "w") as f:
            json.dump(data, f)


def num2rank(num: float) -> str:
    if isnan(num) or (not num and num != 0):
        return "N/A"
    if int(num) < 30:
        return "%dk" % (30 - int(num))
    return "%dd" % ((int(num) - 30) + 1)
