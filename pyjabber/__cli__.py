import sys
import click


from loguru import logger
from pyjabber.server import Server

@click.command()
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

if __name__ == "__main__":
    main()  # pragma: no cover
