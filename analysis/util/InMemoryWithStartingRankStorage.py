import logging
import os
import json

from collections import defaultdict
from typing import Any, DefaultDict, Dict, List, Tuple

from goratings.interfaces import Storage
from .CLI import cli
from analysis.util import config
from analysis.util import rank_to_rating


STORE_AFTER_N_GAMES = 10
#STORE_AFTER_N_GAMES = 30
INITIAL_DEVIATION = 250
STORED_RATINGS_FILE = "starting_ratings.json"
#STORED_RATINGS_FILE = "starting_ratings-30.json"

__all__ = ["InMemoryStorageWithStartingRankStorage"]


logger = logging.getLogger(__name__)

# The starting rank system relies on a two pass system, the first pass we start
# everyone at Glicko 1500 and after a few games we store what their rating is.
# Subsequent runs will then use the stored rating to determine their starting
# rank band.

cli.add_argument(
    "--first-pass",
    dest="first_pass",
    action="store_true",
    help="Compute starting ranks and save them for a second run. This implies *not* loading previous ranks.",
)

_30k = 0
_25k = 30 - 25
_22k = 30 - 22
_20k = 30 - 20
_15k = 30 - 15
_17k = 30 - 17
_18k = 30 - 18
_19k = 30 - 19
_12k = 30 - 12
_10k = 30 - 10
_5k = 30 - 5
_2k = 30 - 2
_1d = 30

# Proposal:
#   beginner = 25k
#   basic = 22k
#   intermediate = 12k
#   advanced = 12k

if False:
    _new = _25k
    _basic = _22k
    _intermediate = _12k
    _advanced = _2k
else:
    _new = _20k
    _basic = _17k
    _intermediate = _12k
    _advanced = _2k


def bin_(rating: float) -> float:
    if rating < (rank_to_rating(_new) + rank_to_rating(_basic)) / 2:
        return rank_to_rating(_new)
    elif rating < (rank_to_rating(_basic) + rank_to_rating(_intermediate)) / 2:
        return rank_to_rating(_basic)
    elif rating < (rank_to_rating(_intermediate) + rank_to_rating(_advanced)) / 2:
        return rank_to_rating(_intermediate)
    else:
        return rank_to_rating(_advanced)


cli.add_argument(
    "--new",
    dest="new",
    type=float,
    default=_new,
    help="New player starting rank.",
)

cli.add_argument(
    "--basic",
    dest="basic",
    type=float,
    default=_basic,
    help="Basic player starting rank.",
)

cli.add_argument(
    "--intermediate",
    dest="intermediate",
    type=float,
    default=_intermediate,
    help="Intermediate player starting rank.",
)

cli.add_argument(
    "--advanced",
    dest="advanced",
    type=float,
    default=_advanced,
    help="Advanced player starting rank.",
)


def bin(rating: float) -> float:
    if (
        rating
        < (rank_to_rating(config.args.new) + rank_to_rating(config.args.basic)) / 2
    ):
        return rank_to_rating(config.args.new)
    elif (
        rating
        < (rank_to_rating(config.args.basic) + rank_to_rating(config.args.intermediate))
        / 2
    ):
        return rank_to_rating(config.args.basic)
    elif (
        rating
        < (
            rank_to_rating(config.args.intermediate)
            + rank_to_rating(config.args.advanced)
        )
        / 2
    ):
        return rank_to_rating(config.args.intermediate)
    else:
        return rank_to_rating(config.args.advanced)


class InMemoryStorageWithStartingRankStorage(Storage):
    _data: Dict[int, Any]
    _timeout_flags: DefaultDict[int, bool]
    _match_history: DefaultDict[int, List[Tuple[int, Any]]]
    _rating_history: DefaultDict[int, List[Tuple[int, Any]]]
    _set_count: DefaultDict[int, int]
    entry_type: Any
    first_pass: bool
    _initial_ratings: Dict[int, Any]

    def __init__(self, entry_type: type) -> None:
        self.first_pass = config.args.first_pass or not os.path.exists(
            STORED_RATINGS_FILE
        )

        if not self.first_pass:
            logger.info("Loading ranks from previous run.")
            with open(STORED_RATINGS_FILE, "r") as f:
                self._initial_ratings = {
                    int(k): v for k, v in json.loads(f.read()).items()
                }
            logger.info(f"{len(self._initial_ratings)} initial ratings loaded.")

        if self.first_pass:
            logger.info("Starting rank storage is in first pass mode.")
            self._initial_ratings = {}

        self._data = {}
        self._timeout_flags = defaultdict(lambda: False)
        self._match_history = defaultdict(lambda: [])
        self._rating_history = defaultdict(lambda: [])
        self._set_count = defaultdict(lambda: 0)
        self.entry_type = entry_type

    def get(self, player_id: int) -> Any:
        if player_id not in self._data:
            if player_id in self._initial_ratings:
                self._data[player_id] = self.entry_type(
                    rating=bin(self._initial_ratings[player_id]["rating"]),
                    deviation=INITIAL_DEVIATION,
                )
            else:
                self._data[player_id] = self.entry_type()
        return self._data[player_id]

    def set(self, player_id: int, entry: Any) -> None:
        self._data[player_id] = entry
        self._set_count[player_id] += 1
        if self.first_pass and self._set_count[player_id] == STORE_AFTER_N_GAMES:
            self._initial_ratings[player_id] = entry

    def clear_set_count(self, player_id: int) -> None:
        self._set_count[player_id] = 0

    def get_set_count(self, player_id: int) -> int:
        return self._set_count[player_id]

    def all_players(self) -> Dict[int, Any]:
        return self._data

    def get_timeout_flag(self, player_id: int) -> bool:
        return self._timeout_flags[player_id]

    def set_timeout_flag(self, player_id: int, tf: bool) -> None:
        self._timeout_flags[player_id] = tf

    # We assume we add these entries in ascending order (by timestamp).
    def add_rating_history(self, player_id: int, timestamp: int, entry: Any) -> None:
        self._rating_history[player_id].append((timestamp, entry))

    def add_match_history(self, player_id: int, timestamp: int, entry: Any) -> None:
        self._match_history[player_id].append((timestamp, entry))

    def get_last_game_timestamp(self, player_id: int) -> int:
        if player_id in self._rating_history:
            return self._rating_history[player_id][-1][0]
        return 0

    def get_first_rating_older_than(self, player_id: int, timestamp: int) -> Any:
        for e in reversed(self._rating_history[player_id]):
            if e[0] < timestamp:
                return e[1]
        return self.entry_type()

    def get_ratings_newer_or_equal_to(self, player_id: int, timestamp: int) -> Any:
        ct = 0
        for e in reversed(self._rating_history[player_id]):
            if e[0] >= timestamp:
                ct += 1
            else:
                break
        return [e[1] for e in self._rating_history[player_id][-ct:]]

    def get_first_timestamp_older_than(self, player_id: int, timestamp: int) -> Any:
        for e in reversed(self._rating_history[player_id]):
            if e[0] < timestamp:
                return e[0]
        return None

    def get_matches_newer_or_equal_to(self, player_id: int, timestamp: int) -> Any:
        ct = 0
        for e in reversed(self._match_history[player_id]):
            if e[0] >= timestamp:
                ct += 1
            else:
                break
        return [e[1] for e in self._match_history[player_id][-ct:]]

    def finalize(self) -> None:
        if self.first_pass:
            logger.info("Saving starting ranks.")
            with open(STORED_RATINGS_FILE, "w") as f:
                f.write(
                    json.dumps(
                        {k: v.to_dict() for k, v in self._initial_ratings.items()},
                        indent=2,
                    )
                )
            logger.info("Starting ranks saved.")
