import argparse

__all__ = ["cli", "defaults"]

cli = argparse.ArgumentParser(
    description="Go ratings analysis test code",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)

defaults = {
    'data': 'ogs',
    'ranking': 'log',
}
