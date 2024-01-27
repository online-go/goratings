import argparse
import locale

from goratings.math.glicko2 import glicko2_configure

from .CLI import cli
from .RatingMath import configure_rating_to_rank

__all__ = ["config"]


locale.setlocale(locale.LC_ALL, "")


class Config:
    def __init__(self) -> None:
        pass

    def __call__(self, args: argparse.Namespace, name: str) -> None:
        self.args = args
        configure_rating_to_rank(args)
        configure_glicko2(args)
        self.name = name


glicko2_config = cli.add_argument_group("glicko2 configuration")
glicko2_config.add_argument("--tao", dest="tao", type=float, default=0.5, help="tao")
glicko2_config.add_argument("--min-rd", dest="min_rd", type=float, default=10.0, help="minimum rating deviation")
glicko2_config.add_argument(
    "--max-rd", dest="max_rd", type=float, default=500.0, help="maximum rating deviation",
)
glicko2_config.add_argument(
    "--aging-period", dest="aging_period", type=float,
    help="number of days in the aging period, or --no-aging-period to disable",
)
glicko2_config.add_argument(
    "--no-aging-period", dest="aging_period", action='store_const', const=None,
    help="turn off aging period",
)


def configure_glicko2(args: argparse.Namespace) -> None:
    glicko2_configure(
        tao=args.tao, min_rd=args.min_rd, max_rd=args.max_rd,
        aging_period_days=args.aging_period,
    )


config = Config()
