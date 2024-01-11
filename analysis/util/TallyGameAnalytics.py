import configparser
import json
import math
import os
import sys
from collections import defaultdict
from filelock import FileLock
from math import isnan
from pathlib import Path
from sys import argv
from statistics import mean
from time import time, ctime
from typing import Any, DefaultDict, Dict, Union, List

from .Config import config
from .GameData import datasets_used
from .Glicko2Analytics import Glicko2Analytics
from .GorAnalytics import GorAnalytics
from .InMemoryStorage import InMemoryStorage
from .RatingMath import rating_config, rating_to_rank
from .EGFGameData import EGFGameData
from .AGAGameData import AGAGameData

__all__ = ["TallyGameAnalytics", "num2rank"]


egfdb = EGFGameData()
agadb = AGAGameData()
ALL: int = 999
EGF_OFFSET = 1000000000
AGA_OFFSET = 2000000000
LAST_ORG_GAME_PLAYED_CUTOFF = 1559347200 # 2019-06-01
MIN_ORG_GAMES_PLAYED_CUTOFF = 6
PROVISIONAL_DEVIATION_CUTOFF = 100


# Result storage is indexed by size, speed, rank, handicap
# Board size, `ALL` for all
# Game speed, `ALL` for all, 1=blitz, 2=live, 3=correspondence
# rank, or rank+5 for 5 rank bands (the str "0+5", "5+5", "10+5", etc), `ALL` for all
# Handicap, 0-9 or `ALL` for all
ResultStorageType = DefaultDict[
    int, DefaultDict[int, DefaultDict[Union[int, str], DefaultDict[int, Union[int, float]]]],
]


class TallyGameAnalytics:
    games_ignored: int
    black_wins: ResultStorageType
    predictions: ResultStorageType
    predicted_outcome: ResultStorageType
    prediction_cost: ResultStorageType
    count: ResultStorageType
    count_black_wins: ResultStorageType
    storage: InMemoryStorage
    prefix: str

    def __init__(self, storage: InMemoryStorage, prefix: str = '') -> None:
        self.prefix = prefix
        self.games_ignored = 0
        self.storage = storage
        self.black_wins = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: 0))))
        self.predictions = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: 0.0))))
        self.predicted_outcome = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: 0.0))))
        self.prediction_cost = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: 0.0))))
        self.count = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: 0))))
        self.count_black_wins = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: 0))))

    def add_glicko2_analytics(self, result: Glicko2Analytics) -> None:
        if result.skipped:
            return
        if result.black_deviation > PROVISIONAL_DEVIATION_CUTOFF or result.white_deviation > PROVISIONAL_DEVIATION_CUTOFF:
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
                        if isinstance(rank, int) or isinstance(rank, str):  # this is just to make mypy happy
                            if abs(result.black_rank + result.game.handicap - result.white_rank) <= 1:
                                self.count_black_wins[size][speed][rank][handicap] += 1
                                if black_won:
                                    self.black_wins[size][speed][rank][handicap] += 1
                            self.predictions[size][speed][rank][handicap] += result.expected_win_rate
                            self.predicted_outcome[size][speed][rank][handicap] += (
                                black_won
                                if result.expected_win_rate > 0.5
                                else (not black_won if result.expected_win_rate < 0.5 else 0.5)
                            )
                            self.prediction_cost[size][speed][rank][handicap] += - math.log(result.expected_win_rate if black_won else 1 - result.expected_win_rate)
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
                        if isinstance(rank, int) or isinstance(rank, str):  # this is just to make mypy happy
                            if black_won:
                                self.black_wins[size][speed][rank][handicap] += 1
                            self.predictions[size][speed][rank][handicap] += result.expected_win_rate
                            self.count[size][speed][rank][handicap] += 1

    def print(self) -> None:
        self.print_handicap_performance()
        self.print_handicap_prediction()
        self.print_handicap_cost()
        self.print_inspected_players()
        #self.print_median_games_per_timewindow()
        self.print_compact_stats()
        self.print_self_reported_stats()
        self.update_visualizer_data()

    def print_compact_stats(self) -> None:
        prediction = (
            self.prediction_cost[ALL][ALL][ALL][ALL] / max(1, self.count[ALL][ALL][ALL][ALL])
        )
        prediction_h0 = (
            self.prediction_cost[ALL][ALL][ALL][0] / max(1, self.count[ALL][ALL][ALL][0])
        )
        prediction_h1 = (
            self.prediction_cost[ALL][ALL][ALL][1] / max(1, self.count[ALL][ALL][ALL][1])
        )
        prediction_h2 = (
            self.prediction_cost[ALL][ALL][ALL][2] / max(1, self.count[ALL][ALL][ALL][2])
        )

        #unexp_change = (
        #    self.unexpected_rank_changes[ALL][ALL][ALL][ALL] / max(1, self.count[ALL][ALL][ALL][ALL]) / 2
        #)

        #print("")
        #print("")
        #print("| Algorithm name |   all   |    h0   |    h1   |    h2   | rating changed in the wrong direction |")
        #print("|:---------------|--------:|--------:|--------:|--------:|---------------------------------------:")
        #print(
        #    "| {name:>s} | {prediction:>7.5f} | {prediction_h0:>7.5f} "
        #    "| {prediction_h1:>7.5f} | {prediction_h2:>7.5f} | {unexp_change:>8.5%} |".format(
        print("")
        print("")
        print("| Algorithm name | Rating quality | h0 | h1 | h2 |")
        print("|:---------------|---------------:|---:|---:|---:|")
        print(
            "| {name:>s} | {prediction:>13.1%} | {prediction_h0:>5.1%} "
            "| {prediction_h1:>5.1%} | {prediction_h2:>5.1%} |".format(
                name=Path(argv[0]).name.replace("analyze_", "")[0:14],
                prediction=prediction,
                prediction_h0=prediction_h0,
                prediction_h1=prediction_h1,
                prediction_h2=prediction_h2,
            )
        )

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
                    last_game = self.storage.get_first_timestamp_older_than(id, 999999999999)
                    if last_game is None:
                        rh = []
                    else:
                        rh = self.storage.get_ratings_newer_or_equal_to(id, last_game - 86400 * 28)
                    print(
                        "%20s    %3s     %s     %4.0f  %4.0f     %3.0f  %3.0f"
                        % (
                            name,
                            num2rank(rating_to_rank(entry.rating)),
                            str(entry),
                            min(rh, key=lambda x: x.rating, default=entry).rating,
                            max(rh, key=lambda x: x.rating, default=entry).rating,
                            min(rh, key=lambda x: x.deviation, default=entry).deviation
                            if (hasattr(entry, "deviation"))
                            else 0,
                            max(rh, key=lambda x: x.deviation, default=entry).deviation
                            if (hasattr(entry, "deviation"))
                            else 0,
                        )
                    )

    def print_handicap_performance(self) -> None:
        print("")
        print("")
        print("How often black wins:")
        for size in [9, 13, 19, ALL]:
            print("")
            if size == ALL:
                print("Overall:   %d games" % self.count_black_wins[size][ALL][ALL][ALL])
            else:
                print("%dx%d:   %d games" % (size, size, self.count_black_wins[size][ALL][ALL][ALL]))

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
                        "%5.1f%%   " % ((self.black_wins[size][ALL][rankband][handicap] / ct if ct else 0) * 100.0)
                    )
                sys.stdout.write("\n")

    def print_handicap_prediction(self) -> None:
        print("")
        print("")
        print("How often the predicted winner wins:")
        for size in [9, 13, 19, ALL]:
            print("")
            if size == ALL:
                print("Overall:   %d games" % self.count[size][ALL][ALL][ALL])
            else:
                print("%dx%d:   %d games" % (size, size, self.count[size][ALL][ALL][ALL]))

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
                        % ((self.predicted_outcome[size][ALL][rankband][handicap] / ct if ct else 0) * 100.0)
                    )
                sys.stdout.write("\n")

    def print_self_reported_stats(self) -> None:
        stats = self.get_self_reported_stats()
        if not stats:
            return
        print('')
        print('')

        BAND_WIDTH = 3

        header   = '                '
        line = defaultdict(lambda: '')

        for band in range(0, 40, BAND_WIDTH):
            header += '%-4s - %-4s\t' % (num2rank(band), num2rank(band + (BAND_WIDTH - 1)))
        for key in stats.keys():
            line[key] = '%8s [%3d]:\t' % (key, len([item for sublist in stats[key] for item in sublist]))

            for band in range(0, 40, BAND_WIDTH):
                flat = [item for sublist in stats[key][band:band + BAND_WIDTH] for item in sublist]
                if len(flat):
                    avg = mean(flat)
                    size = len(flat)
                    line[key] += '%4.1f [%2d] \t' % (avg, size)
                else:
                    line[key] += '            \t'

        print(header)
        for key in stats.keys():
            print(line[key])







    def get_self_reported_stats(self) -> Dict[str, Dict[int, List[float]]]:
        datasets = datasets_used()

        if not datasets["ogs"]:
            return


        if os.path.exists('./data'):
            pathname = './data/'
        elif os.path.exists('../data'):
            pathname = '../data/'
        else:
            raise Exception('Failed to find data directory')

        if os.path.exists(pathname + 'self_reported_account_links.full.json'):
            pathname += 'self_reported_account_links.full.json'
        elif os.path.exists(pathname + 'self_reported_account_links.json'):
            pathname = 'self_reported_account_links.json'
        else:
            raise Exception('Failed to find self_reported_account_links json file')


        with open(pathname, 'r') as f:
            stats = json.loads(f.read())

        def get_org_rank(entry, org_country):
            for org in ['org1', 'org2', 'org3']:
                if org in entry and entry[org] == org_country:
                    if org + '_rank' in entry:
                        return entry[org + '_rank']
            return None

        def get_org_id(entry, org_country):
            for org in ['org1', 'org2', 'org3']:
                if org in entry and entry[org] == org_country:
                    if org + '_id' in entry:
                        try:
                            return int(entry[org + '_id'])
                        except:
                            return None
            return None

        def date(timestamp) -> str:
            return ctime(timestamp) if timestamp else ''


        egf_count = 0
        aga_count = 0

        bins     = defaultdict(lambda: defaultdict(lambda: list()))

        for e in stats:
            id = e[0]
            username = e[1]
            entry = e[2]
            player = self.storage.get(id)
            rank = rating_to_rank(player.rating)

            aga = get_org_rank(entry, 'us')
            egf = get_org_rank(entry, 'eu')
            aga_id = get_org_id(entry, 'us')
            egf_id = get_org_id(entry, 'eu')

            if (aga and aga > 100) or (egf and egf > 100):
                pass # throwout pros for our purposes


            aga_num_games_played = agadb.num_games_played(aga_id + AGA_OFFSET) if aga_id else 0
            aga_last_game_played = agadb.last_game_played(aga_id + AGA_OFFSET) if aga_id else 0
            egf_num_games_played = egfdb.num_games_played(egf_id + EGF_OFFSET) if egf_id else 0
            egf_last_game_played = egfdb.last_game_played(egf_id + EGF_OFFSET) if egf_id else 0

            jan_2019 = 1546300800
            #if aga and aga_last_game_played > 0:
            if aga and aga_last_game_played > jan_2019 and aga_num_games_played > 5:
                bins['aga'][aga].append(rank - aga)

            #if egf and egf_last_game_played > 0:
            if egf and egf_last_game_played > jan_2019 and egf_num_games_played > 5:
                bins['egf'][egf].append(rank - egf)


            for server in ['dgs', 'fox', 'kgs', 'igs', 'fox', 'yike', 'golem', 'tygem', 'goquest', 'wbaduk']:
                if ('%s_rank' % server) in entry:
                    server_rank = int(entry[('%s_rank' % server)])
                    bins[server][server_rank].append(rank - server_rank)

        ret = {}

        for k in bins.keys():
            ret[k] = []
            for rank in range(0, 40):
                if bins[k][rank]:
                    ret[k].append(bins[k][rank])
                else:
                    ret[k].append([])

        return ret


    def get_self_reported_rating(self) -> Dict[str, Dict[int, List[float]]]:
        datasets = datasets_used()

        if not datasets["ogs"]:
            return


        if os.path.exists('./data'):
            pathname = './data/'
        elif os.path.exists('../data'):
            pathname = '../data/'
        else:
            raise Exception('Failed to find data directory')

        if os.path.exists(pathname + 'self_reported_account_links.full.json'):
            pathname += 'self_reported_account_links.full.json'
        elif os.path.exists(pathname + 'self_reported_account_links.json'):
            pathname = 'self_reported_account_links.json'
        else:
            raise Exception('Failed to find self_reported_account_links json file')


        with open(pathname, 'r') as f:
            stats = json.loads(f.read())

        def get_org_rank(entry, org_country):
            for org in ['org1', 'org2', 'org3']:
                if org in entry and entry[org] == org_country:
                    if org + '_rank' in entry:
                        return entry[org + '_rank']
            return None

        def get_org_id(entry, org_country):
            for org in ['org1', 'org2', 'org3']:
                if org in entry and entry[org] == org_country:
                    if org + '_id' in entry:
                        try:
                            return int(entry[org + '_id'])
                        except:
                            return None
            return None

        def date(timestamp) -> str:
            return ctime(timestamp) if timestamp else ''


        egf_count = 0
        aga_count = 0

        bins     = defaultdict(lambda: defaultdict(lambda: list()))

        for e in stats:
            id = e[0]
            username = e[1]
            entry = e[2]
            player = self.storage.get(id)
            rank = rating_to_rank(player.rating)
            if player.rating == 1500:
                continue

            aga = get_org_rank(entry, 'us')
            egf = get_org_rank(entry, 'eu')
            aga_id = get_org_id(entry, 'us')
            egf_id = get_org_id(entry, 'eu')

            if (aga and aga > 100) or (egf and egf > 100):
                continue # throwout pros for our purposes


            aga_num_games_played = agadb.num_games_played(aga_id + AGA_OFFSET) if aga_id else 0
            aga_last_game_played = agadb.last_game_played(aga_id + AGA_OFFSET) if aga_id else 0
            egf_num_games_played = egfdb.num_games_played(egf_id + EGF_OFFSET) if egf_id else 0
            egf_last_game_played = egfdb.last_game_played(egf_id + EGF_OFFSET) if egf_id else 0

            jan_2019 = 1546300800
            #if aga and aga_last_game_played > 0:
            if aga and aga_last_game_played > jan_2019 and aga_num_games_played > 5:
                bins['aga'][aga].append(player.rating)

            #if egf and egf_last_game_played > 0:
            if egf and egf_last_game_played > jan_2019 and egf_num_games_played > 5:
                bins['egf'][egf].append(player.rating)


            for server in ['dgs', 'fox', 'kgs', 'igs', 'fox', 'yike', 'golem', 'tygem', 'goquest', 'wbaduk']:
                if ('%s_rank' % server) in entry:
                    server_rank = int(entry[('%s_rank' % server)])
                    bins[server][server_rank].append(player.rating)

        ret = {}

        for k in bins.keys():
            ret[k] = []
            for rank in range(0, 40):
                if bins[k][rank]:
                    ret[k].append(bins[k][rank])
                else:
                    ret[k].append([])

        return ret

    def print_handicap_cost(self) -> None:
        print("")
        print("")
        print("Quality of the rating (lower is better):")
        for size in [9, 13, 19, ALL]:
            print("")
            if size == ALL:
                print("Overall:   %d games" % self.count[size][ALL][ALL][ALL])
            else:
                print("%dx%d:   %d games" % (size, size, self.count[size][ALL][ALL][ALL]))

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
                        "%5.3f   "
                        % (self.prediction_cost[size][ALL][rankband][handicap] / max(1,ct))
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
        if "d" in cfg["rating_config"]:
            lst.append(str(cfg["rating_config"]["d"]))
        if "p" in cfg["rating_config"]:
            lst.append(str(cfg["rating_config"]["p"]))

        return self.prefix + '-' + (":".join(lst))

    def get_visualizer_data(self) -> Any:
        obj: Any = {}

        obj["name"] = self.get_descriptive_name()
        obj["timestamp"] = time()
        obj["black_wins"] = self.black_wins
        obj["predictions"] = self.predictions
        obj["count"] = self.count
        obj["ignored"] = self.games_ignored
        obj["config"] = self.get_config()

        rank_distribution = [0 for x in range(40)]
        for _id, player in self.storage.all_players().items():
            rank = max(0, min(39, int(rating_to_rank(player.rating))))
            rank_distribution[rank] += 1

        obj["rank_distribution"] = rank_distribution
        obj["org_stats"] = self.get_self_reported_stats()

        return obj

    def update_visualizer_data(self) -> Any:
        fname: str = "data.json"

        if os.path.exists("visualizer/"):
            fname = "visualizer/data.json"
        elif os.path.exists("analysis/visualizer/"):
            fname = "analysis/visualizer/data.json"
        else:
            raise Exception("Can't find visualizer directory")

        data: Any = {}
        obj = self.get_visualizer_data()

        with FileLock(fname + ".lock"):
            if os.path.exists(fname):
                with open(fname, "r") as f:
                    data = json.load(f)

            data[obj["name"]] = obj

            with open(fname, "w") as f:
                json.dump(data, f)

        return obj


def num2rank(num: float) -> str:
    if isnan(num) or (not num and num != 0):
        return "N/A"
    if int(num) < 30:
        return "%dk" % (30 - int(num))
    return "%dd" % ((int(num) - 30) + 1)
