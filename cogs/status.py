import asyncio
import logging
import random

import discord
from discord.ext import commands, tasks

from main import MyClient


class Status(commands.Cog, command_attrs=dict(hidden=True)):
	def __init__(self, client):
		self.client: MyClient = client

	@commands.Cog.listener()
	async def on_ready(self):
		self.update_status.start()
		logging.info("Status ready!")

	@commands.Cog.listener()
	async def on_disconnect(self):
		self.update_status.stop()
		logging.info("Status stopped gracefully.")

	@commands.Cog.listener()
	async def on_connect(self):
		self.update_status.restart()
		logging.info("Status update restarted.")

	@tasks.loop(seconds=30)
	async def update_status(self):
		asyncio.create_task(self.statusupdate())

	async def statusupdate(self) -> None:
		await self.client.change_presence(
			activity=discord.CustomActivity(
				name=f"{len(self.client.guilds)} servers | ?!{random.choice([command.qualified_name for command in self.client.commands])}"
			),
			status=discord.Status.online,  # type: ignore
		)

	async def cog_unload(self) -> None:
		self.update_status.cancel()

	async def cog_load(self) -> None:
		if self.client.is_ready():
			logging.info("The status string was probably updated. Restarting the status loop.")
			await self.on_connect()


async def setup(client: commands.AutoShardedBot):
	await client.add_cog(Status(client))
