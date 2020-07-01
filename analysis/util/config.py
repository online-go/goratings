__all__ = ['config']


class Config:
    def __init__(self):
        pass

    def __call__(self, args):
        self.args = args


config = Config()
