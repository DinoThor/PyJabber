from pyjabber.utils import Singleton


class Metadata(metaclass=Singleton):
    def __init__(self, host=None, config_path=None):
        if host:
            self._host = host
        if config_path:
            self._config_path = config_path

        self._locked = True

    def __setattr__(self, key, value):
        if getattr(self, '_locked', False):
            raise AttributeError("Metadata is immutable")
        super().__setattr__(key, value)

    def __delattr__(self, key):
        raise AttributeError("Metadata is immutable")

    @property
    def host(self):
        return self._host

    @property
    def config_path(self):
        return self._config_path
