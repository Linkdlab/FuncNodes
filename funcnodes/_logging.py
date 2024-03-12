import logging
from logging.handlers import RotatingFileHandler
from .config import CONFIG_DIR
import os

LOGGINGDIR = os.path.join(CONFIG_DIR, "logs")
if not os.path.exists(LOGGINGDIR):
    os.makedirs(LOGGINGDIR)

FUNCNODES_LOGGER = logging.getLogger("funcnodes")

FUNCNODES_LOGGER.setLevel("DEBUG")


ch = logging.StreamHandler()
fh = RotatingFileHandler(
    os.path.join(LOGGINGDIR, "funcnodes.log"), maxBytes=1024 * 1024 * 5, backupCount=5
)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
fh.setFormatter(formatter)
# Add the handler to the logger
FUNCNODES_LOGGER.addHandler(ch)
FUNCNODES_LOGGER.addHandler(fh)


def get_logger(name):
    sublogger = FUNCNODES_LOGGER.getChild(name)

    # _init_logger(sublogger)
    return sublogger
