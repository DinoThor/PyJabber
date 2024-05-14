import sys

from loguru import logger
from pyjabber.server import Server

def main():
    logger.add(
        "pyjabber.log",
        enqueue     = True,
        format      = "<green>{time}</green> - <level>{level}: {message}</level>",
        rotation    = None,
        level       = "DEBUG",
    )

    server = Server()
    server.start()

    return 0

"""Allow cookiecutter to be executable through `python -m vangare`."""

if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
