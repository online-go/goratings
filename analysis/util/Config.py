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

    def __call__(self, args: argparse.Namespace) -> None:
        self.args = args
        configure_rating_to_rank(args)
        configure_glicko2(args)


glicko2_config = cli.add_argument_group("glicko2 configuration")
glicko2_config.add_argument("--tao", dest="tao", type=float, default=0.5, help="tao")
glicko2_config.add_argument(
    "--min-rd", dest="min_rd", type=float, default=10.0, help="minimum rating deviation"
)
glicko2_config.add_argument(
    "--max-rd",
    dest="max_rd",
    type=float,
    default=500.0,
    help="maximum rating deviation",
)


def configure_glicko2(args: argparse.Namespace) -> None:
    glicko2_configure(
        tao=args.tao, min_rd=args.min_rd, max_rd=args.max_rd,
    )


config = Config()
