import logging

from rich.logging import RichHandler

FORMAT = "%(message)s"


def get_logger():
    logging.basicConfig(
        level="NOTSET", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
    )

    logger = logging.getLogger("rich")
    return logger
