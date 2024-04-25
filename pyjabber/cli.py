
import click
# import os
# import socket
import sys
# import yaml

from loguru import logger
from pyjabber.server import Server


# def CommandWithConfigFile(config_file_param_name):
#     """This class load the configuration file and overrides the parameters.

#     :param config_file_param_name: Parameter cointaing the path of the configuration file.
#     :type config_file_param_name: click.Path
#     :return: Custom command parser
#     :rtype: CustomCommandClass
#     """

#     class CustomCommandClass(click.Command):
#         def invoke(self, ctx):
#             config_file = ctx.params[config_file_param_name]
#             if config_file is not None:
#                 with open(config_file) as f:
#                     config_data = yaml.safe_load(f)
#                     for param, value in ctx.params.items():
#                         if param in config_data:
#                             ctx.params[param] = config_data[param]

#             return super(CustomCommandClass, self).invoke(ctx)

#     return CustomCommandClass


@click.option("--log_level", default="INFO", type=str, help="Sets the logging level")
@click.option("--log_file", default="pyjabber.log", type=str, help="Sets the logging filename")
@click.option(
    "--log_format",
    default="<green>{time}</green> - <level>{level}: {message}</level>",
    type=str,
    help="Sets the logging format",
)
@click.option("--log_rotation", default=None, type=str, help="Sets the logging file rotation mode")
@click.option("--host", default="localhost", type=str, help="Server hostname")
@click.option("--client_port", default=5222, type=int, help="Client connections port")
@click.option("--server_port", default=5269, type=int, help="Server connections port")
@click.option(
    "--family",
    default="IPV4",
    type=click.Choice(["IPV4", "IPV6", "NONE"]),
    help="Server connections port",
)
# @click.option(
#     "--cert_file",
#     default=os.path.realpath("certs/server.crt"),
#     help="Sets the certificate file path for TLS connections"
# )
# @click.option(
#     "--key_file",
#     default=os.path.realpath("certs/server.key"),
#     help="Sets the private key file path for TLS connections"
# )
# @click.option(
#     "--sasl_mechanisms",
#     default=["PLAIN", "SCRAM-SHA-1", "SCRAMPLUS"],
#     help="Supported SASL mechanisms",
# )
# @click.option(
#     "--sasl_max_retries",
#     default=3,
#     help="Max retries on failed sasl authentication",
# )
@click.option(
    "-t",
    "--timeout",
    default=60,
    type=int,
    help="Connection timeout in seconds")
@click.option(
    "-c",
    "--config_file",
    type=click.Path(exists=True),
    help="Loads configuration from a yaml file. Overrides other parameters",
)
# @click.command(cls=CommandWithConfigFile("config_file"))
def main():

    logger.add(
        "pyjabber.log",
        enqueue     = True,
        format      = "<green>{time}</green> - <level>{level}: {message}</level>",
        rotation    = None,
        level       = "DEBUG",
    )

    server = Server()
    server.run_server()

    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
