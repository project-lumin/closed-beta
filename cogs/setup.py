from discord import app_commands

import main
from discord.ext import commands
from typing import Optional


class Setup(commands.Cog, name="Setup"):
	def __init__(self, client):
		self.client = client

	@commands.hybrid_command(name="prefix", description="prefix_specs-description")
	@commands.has_permissions(administrator=True)
	@app_commands.rename(prefix="prefix_specs-args-prefix-name", mention="prefix_specs-args-mention-name")
	@app_commands.describe(
		prefix="prefix_specs-args-prefix-description",
		mention="prefix_specs-args-mention-description",
	)
	async def prefix(self, ctx: main.Context, prefix: str, mention: Optional[bool] = True):
		if len(prefix) > 10:
			return await ctx.send("setup.prefix.errors.long", prefix=prefix, limit=10)
		await self.client.db.execute(
			"UPDATE guilds SET prefix = $1, mention = $2 WHERE guild_id = $3",
			prefix,
			mention,
			ctx.guild.id,
		)
		await ctx.send("setup.prefix.set", prefix=prefix)


async def setup(client):
	await client.add_cog(Setup(client))
