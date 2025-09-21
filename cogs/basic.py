from time import perf_counter

from discord.ext import commands

from core import Context, MyClient


class Basic(commands.Cog, name="Basic"):
	def __init__(self, client: MyClient):
		self.client = client

	@commands.hybrid_command(name="ping", description="ping_specs-description")
	async def ping(self, ctx: Context):
		# Database ping calculation
		database_start = perf_counter()
		await self.client.db.execute("SELECT 1")
		database = perf_counter() - database_start

		await ctx.send("ping", latency=float(self.client.latency), db=float(database))


async def setup(client: MyClient):
	await client.add_cog(Basic(client))
