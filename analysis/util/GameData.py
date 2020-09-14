import sys
from typing import Dict, Iterator

from goratings.interfaces import GameRecord

from .CLI import cli, defaults
from .Config import config
from .EGFGameData import EGFGameData
from .OGSGameData import OGSGameData

__all__ = ["GameData", "datasets_used"]

cli.add_argument(
    "--egf",
    dest="use_egf_data",
    const=1,
    default=False,
    action="store_const",
    help="Use EGF dataset",
)

cli.add_argument(
    "--ogs",
    dest="use_ogs_data",
    const=1,
    default=False,
    action="store_const",
    help="Use OGS dataset",
)

cli.add_argument(
    "--all",
    dest="use_all_data",
    const=1,
    default=False,
    action="store_const",
    help="Use all datasets",
)

cli.add_argument(
    "--games",
    dest="num_games",
    type=int,
    default=0,
    help="Number of games to process from each dataset, 0 for all",
)


class GameData:
    quiet: bool
    ogsdata: OGSGameData

    def __init__(self, quiet: bool = False):
        self.quiet = quiet
        self.ogsdata = OGSGameData(quiet=quiet)
        self.egfdata = EGFGameData(quiet=quiet)

    def __iter__(self) -> Iterator[GameRecord]:
        data_to_use = datasets_used()

        if data_to_use["ogs"]:
            if not self.quiet:
                sys.stdout.write("\nProcessing OGS data\n")
            for entry in self.ogsdata:
                yield entry

        if data_to_use["egf"]:
            if not self.quiet:
                sys.stdout.write("\nProcessing EGF data\n")
            for entry in self.egfdata:
                yield entry


def datasets_used() -> Dict[str, bool]:
    ret = {
        "egf": config.args.use_all_data or config.args.use_egf_data,
        "ogs": config.args.use_all_data or config.args.use_ogs_data,
        # 'aga': config.args.use_all_data or config.args.use_aga_data,
    }
    if not ret["egf"] and not ret["ogs"]:  # and not ret['aga']:
        ret[defaults["data"]] = True

    return ret
