import os
import socket
import sys

import click
from loguru import logger

from pyjabber.server import Server


@click.command
@click.option('--host', type=str, default='localhost',
              show_default=True, help='Host name')
@click.option('--client_port', type=int, default=5222,
              show_default=True, help='Server-to-client port')
@click.option('--server_port', type=int, default=5269,
              show_default=True, help='Server-to-server port')
@click.option('--server_out_port', type=int, default=5269,
              show_default=True, help='Server-to-server port (Outcoming connection)')
@click.option('--family',
              type=click.Choice(['ipv4',
                                 'ipv6'],
                                case_sensitive=False),
              default='ipv4',
              show_default=True,
              help='(ipv4 / ipv6)')
@click.option('--tls1_3', is_flag=True, help='Enables TLSv1_3')
@click.option('--timeout', type=int, default=60,
              show_default=True, help='Timeout for connection')
@click.option('--log_level',
              type=click.Choice(['INFO',
                                 'DEBUG'],
                                case_sensitive=False),
              default='INFO',
              show_default=True,
              help='Log level alert')
@click.option('--log_path', type=str, help='Path to log dumpfile')
@click.option('--debug', '-D', is_flag=True,
              help='Enables debug mode in Asyncio')

def main(
        host,
        client_port,
        server_port,
        server_out_port,
        family,
        tls1_3,
        timeout,
        log_level,
        log_path,
        debug):

    log_file = os.devnull

    if log_path:
        log_file = open(os.path.join(log_path, "pyjabber.log"), 'w')

    logger.add(
        log_file,
        enqueue=True,
        format="<green>{time}</green> - <level>{level}: {message}</level>",
        level=log_level,
    )
    logger.configure(handlers=[{"sink": sys.stderr, "level": log_level}])

    server = Server(
        host=host,
        client_port=client_port,
        server_port=server_port,
        server_out_port=server_out_port,
        family=socket.AF_INET if family == "ipv4" else socket.AF_INET6,
        connection_timeout=timeout,
        enable_tls1_3=tls1_3,
    )

    server.start(debug)

    return 0


"""Allow cookiecutter to be executable through `python -m vangare`."""

if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
