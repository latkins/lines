import logging

from rich.logging import RichHandler

FORMAT = "%(message)s"


def get_logger():
    logging.basicConfig(
        level=logging.INFO, format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
    )

    logger = logging.getLogger("rich")
    return logger
