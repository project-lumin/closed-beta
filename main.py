import asyncio
import os

from core.bot import MyClient
from core.logging import logger
from dotenv import load_dotenv

try:
	import uvloop  # type: ignore

	asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
	if os.name == "nt":
		asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
	else:
		asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

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
