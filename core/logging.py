import logging

from discord.utils import setup_logging

setup_logging(level=logging.INFO, root=True)
logger = logging.getLogger(__name__)
