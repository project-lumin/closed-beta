import discord
from discord.ext import commands

import main


class ClosedBeta(commands.GroupCog, group_name="beta"):
	def __init__(self, client):
		self.client = client

	@commands.Cog.listener()
	async def on_guild_join(self, guild: discord.Guild):
		whitelist = [
			record["guild_id"]
			for record in await self.client.db.fetch("SELECT guild_id FROM closed_beta WHERE guild_id = $1", guild.id)
		]
		if guild.id not in whitelist:
			await guild.leave()

	@commands.hybrid_command(name="add")
	async def add_guild_to_closed_beta(self, ctx: main.Context, guild_id):
		if not ctx.author.id in self.client.devs:
			return await ctx.reply(content="You are not a developer.")
		await self.client.db.execute(
			"INSERT INTO closed_beta(guild_id, added_by) VALUES ($1, $2)",
			guild_id,
			ctx.author.id,
		)
		await ctx.reply(f"Guild **{guild_id}** added to closed beta.")

	@commands.hybrid_command(name="remove")
	async def remove_guild_from_closed_beta(self, ctx: main.Context, guild_id):
		if not ctx.author.id in self.client.devs:
			return await ctx.reply(content="You are not a developer.")
		await self.client.db.execute("DELETE FROM closed_beta WHERE guild_id = $1", guild_id)
		await ctx.reply(f"Guild **{guild_id}** removed from closed beta.")


async def setup(client: main.MyClient):
	await client.add_cog(ClosedBeta(client))
