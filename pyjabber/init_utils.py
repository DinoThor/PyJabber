import socket

from loguru import logger


def setup_query_local_ip():
    """Return the local IP of the host machine"""
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


def get_migrations_path() -> str:
    # Localiza la carpeta migrations dentro del paquete instalado
    return str(pkg_resources.files("my_package").joinpath("migrations"))


def run_db_migrations() -> None:
    # 1) Crea la Config de Alembic “en memoria”
    cfg = Config()
    cfg.set_main_option("script_location", get_migrations_path())
    cfg.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL"))
    # 2) Sube la base de datos hasta la última revisión
    command.upgrade(cfg, "head")
