import sys

from typing import Iterator
from goratings.interfaces import GameRecord

from .CLI import cli
from .Config import config
from .EGFGameData import EGFGameData
from .OGSGameData import OGSGameData


__all__ = ["GameData"]

cli.add_argument(
    "--egf",
    dest="use_egf_data",
    const=1,
    default=False,
    action='store_const',
    help="Use EGF dataset",
)

cli.add_argument(
    "--ogs",
    dest="use_ogs_data",
    const=1,
    default=False,
    action='store_const',
    help="Use OGS dataset",
)

cli.add_argument(
    "--all",
    dest="use_all_data",
    const=1,
    default=False,
    action='store_const',
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
        self.ogsdata = OGSGameData(quiet = quiet)
        self.egfdata = EGFGameData(quiet = quiet)

    def __iter__(self) -> Iterator[GameRecord]:
        if config.args.use_all_data or config.args.use_ogs_data or (not config.args.use_egf_data):
            if not self.quiet:
                sys.stdout.write(
                    f"\nProcessing OGS data\n"
                )
            for entry in self.ogsdata:
                yield entry

        if config.args.use_all_data or config.args.use_egf_data:
            if not self.quiet:
                sys.stdout.write(
                    f"\nProcessing EGF data\n"
                )
            for entry in self.egfdata:
                yield entry

