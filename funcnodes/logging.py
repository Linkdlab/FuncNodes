import logging


FUNCNODES_LOGGER = logging.getLogger("funcnodes")

FUNCNODES_LOGGER.setLevel("DEBUG")


ch = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
# Add the handler to the logger
FUNCNODES_LOGGER.addHandler(ch)


def get_logger(name):
    sublogger = FUNCNODES_LOGGER.getChild(name)

    # _init_logger(sublogger)
    return sublogger
