import asyncio
import logging
import os
import platform

import discord
from dotenv import load_dotenv

from core.bot import MyClient

for handler in logging.root.handlers[:]:
	# prevent double logging
	logging.root.removeHandler(handler)

discord.utils.setup_logging(level=logging.INFO, root=True)
logger = logging.getLogger()

load_dotenv()
TOKEN = os.getenv("TOKEN")

if __debug__:
	TOKEN = os.getenv("DEBUG_TOKEN")

if __name__ == "__main__":
	if platform.system() != "Windows":
		import uvloop  # type: ignore

		uvloop.install()
		asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
		logger.info("Using uvloop event loop policy")
	else:
		asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
		logger.info("Using default event loop policy")

logger.info("Starting the bot...")
client = MyClient()


async def main():
	try:
		await client.start(TOKEN)
	except KeyboardInterrupt:
		logger.error("KeyboardInterrupt: Bot shut down by console")
		await client.close()


if __name__ == "__main__":
	if __debug__:
		logger.info("Running in debug mode")
	else:
		logger.info("Running in production mode")
	try:
		asyncio.run(main())
	except KeyboardInterrupt:
		logger.error("KeyboardInterrupt: Bot shut down by console")
	else:
		logger.info("Bot shut down")
