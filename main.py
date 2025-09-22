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


async def main() -> None:
	logger.info("Starting the bot...")
	load_dotenv()

	client = MyClient()

	if __debug__:
		token = os.getenv("DEBUG_TOKEN")
		logger.info("Running in debug mode")
	else:
		token = os.getenv("TOKEN")
		logger.info("Running in production mode")

	await client.start(token)


if __name__ == "__main__":
	asyncio.run(main())
