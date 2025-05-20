import logging
import os
import socket
import sys
import click

from pyjabber.server_parameters import Parameters

if sys.platform != 'win32':
    from uvloop import run
else:
    from winloop import run

from loguru import logger
from pyjabber.server import Server

FILE_PATH = os.path.dirname(os.path.abspath(__file__))


class InterceptHandler(logging.Handler):
    """
    Redirects all logging from stdlib to loguru
    """
    def emit(self, record):
        try:
            lvl = logger.level(record.levelname).name
        except ValueError:
            lvl = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(lvl, record.getMessage())


@click.command
@click.option('--host', type=str, default='localhost',
              show_default=True, help='Host name')
@click.option('--client_port', type=int, default=5222,
              show_default=True, help='Server-to-client port')
@click.option('--server_port', type=int, default=5269,
              show_default=True, help='Server-to-server port')
@click.option('--server_out_port', type=int, default=5269,
              show_default=True, help='Server-to-server port (Out coming connection)')
@click.option('--family',
              type=click.Choice(['ipv4',
                                 'ipv6'],
                                case_sensitive=False),
              default='ipv4',
              show_default=True,
              help='(ipv4 / ipv6)')
@click.option('--timeout', type=int, default=60,
              show_default=True, help='Timeout for connection')
@click.option('--database_path', type=str, default=os.path.join(os.getcwd(), "pyjabber.db"),
              show_default=True, help='Path for database file')
@click.option('--database_purge', is_flag=True, help='Restore database file to default state (empty)')
@click.option('--database_in_memory', is_flag=True,
              help='Database in memory. The data will be erased after server shutdown')
@click.option('--message_persistence', is_flag=True,
              help='Keep the unsent messages in memory waiting for the receiver client to connect')
@click.option(
              "-v",
              "--verbose",
              count=True,
              help="Show verbose debug level: -v INFO -vv DEBUG, -vvv level TRACE, ")
@click.option('--log_path', type=str, help='Path to log dumpfile')
@click.option('--debug', '-D', is_flag=True,
              help='Enables debug mode in Asyncio')

def main(
        host,
        client_port,
        server_port,
        server_out_port,
        family,
        timeout,
        database_path,
        database_purge,
        database_in_memory,
        message_persistence,
        verbose,
        log_path,
        debug):
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    logger.remove()

    if log_path:
        log_file = open(os.path.join(log_path, "pyjabber.log"), 'w')
        logger.add(
            log_file,
            enqueue=True,
            format="<green>{time}</green> - <level>{level}: {message}</level>",
            level=set_verbosity(verbose),
        )

    level = set_verbosity(verbose)

    logger.add(
        sys.stderr,
        enqueue=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> - <level>{level}: {message}</level>",
        level=level,
    )

    logging.getLogger("sqlalchemy.engine").setLevel(logging.NOTSET)
    logging.getLogger("alembic").setLevel(logging.NOTSET)

    param = Parameters(
        host=host,
        client_port=client_port,
        server_port=server_port,
        server_out_port=server_out_port,
        family=socket.AF_INET if family == "ipv4" else socket.AF_INET6,
        connection_timeout=timeout,
        database_path=database_path,
        database_purge=database_purge,
        database_in_memory=database_in_memory,
        message_persistence=message_persistence
    )

    server = Server(param)

    run(server.start(), debug=debug)

    return 0


def set_verbosity(verbose):
    if verbose == 1:
        return 'INFO'
    elif verbose == 2:
        return 'DEBUG'
    elif verbose == 3:
        return 'TRACE'
    else:
        return 'SUCCESS'


"""Allow cookiecutter to be executable through `python -m pyjabber`."""

if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
