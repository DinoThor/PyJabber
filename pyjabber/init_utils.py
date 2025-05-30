import socket

from loguru import logger


def setup_query_local_ip():
    """
    Return the local IP of the host machine
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        # doesn't even have to be reachable
        s.connect(('10.254.254.254', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP


def setup_ip_by_host(host: str):
    try:
        return socket.gethostbyname(host)
    except socket.gaierror as e:
        logger.error(e)
        return None
