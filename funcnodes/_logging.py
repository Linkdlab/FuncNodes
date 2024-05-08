import logging
from logging.handlers import RotatingFileHandler
from .config import CONFIG_DIR
import os

LOGGINGDIR = os.path.join(CONFIG_DIR, "logs")
if not os.path.exists(LOGGINGDIR):
    os.makedirs(LOGGINGDIR)

FUNCNODES_LOGGER = logging.getLogger("funcnodes")

FUNCNODES_LOGGER.setLevel(logging.DEBUG)


ch = logging.StreamHandler()
fh = RotatingFileHandler(
    os.path.join(LOGGINGDIR, "funcnodes.log"), maxBytes=1024 * 1024 * 5, backupCount=5
)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Add the handler to the logger


def _overwrite_add_handler(logger):
    """
    Overwrites the addHandler method of the given logger.

    Args:
      logger (Logger): The logger to overwrite the addHandler method for.

    Returns:
      None.

    Examples:
      >>> _overwrite_add_handler(FUNCNODES_LOGGER)
    """
    _old_add_handler = logger.addHandler

    def _new_add_handler(hdlr):
        """
    Adds a handler to the given logger.

    Args:
      hdlr (Handler): The handler to add to the logger.

    Returns:
      None.

    Examples:
      >>> _new_add_handler(ch)
    """
        hdlr.setFormatter(formatter)
        if hdlr not in logger.handlers:
            _old_add_handler(hdlr)

    logger.addHandler = _new_add_handler


_overwrite_add_handler(FUNCNODES_LOGGER)

FUNCNODES_LOGGER.addHandler(ch)
FUNCNODES_LOGGER.addHandler(fh)


def get_logger(name, propagate=True):
    """
    Returns a logger with the given name.

    Args:
      name (str): The name of the logger.
      propagate (bool): Whether to propagate the logger's messages to its parent logger.

    Returns:
      Logger: The logger with the given name.

    Examples:
      >>> get_logger("funcnodes")
    """
    sublogger = FUNCNODES_LOGGER.getChild(name)
    _overwrite_add_handler(sublogger)
    sublogger.propagate = propagate
    sublogger.addHandler(ch)
    # _init_logger(sublogger)
    return sublogger
