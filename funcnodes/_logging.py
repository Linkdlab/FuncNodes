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
    _old_add_handler = logger.addHandler

    def _new_add_handler(hdlr):
        hdlr.setFormatter(formatter)
        if hdlr not in logger.handlers:
            _old_add_handler(hdlr)

    logger.addHandler = _new_add_handler


_overwrite_add_handler(FUNCNODES_LOGGER)

FUNCNODES_LOGGER.addHandler(ch)
FUNCNODES_LOGGER.addHandler(fh)


def get_logger(name, propagate=True):
    sublogger = FUNCNODES_LOGGER.getChild(name)
    _overwrite_add_handler(sublogger)
    sublogger.propagate = propagate

    # _init_logger(sublogger)
    return sublogger
