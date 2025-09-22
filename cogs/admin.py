from logging import getLogger
from time import perf_counter
from typing import Literal, Optional

import discord
from core import Context, MyClient, update_slash_localizations
from discord import app_commands
from discord.ext import commands

logger = getLogger(__name__)


class Admin(commands.Cog):
	def __init__(self, client: MyClient):
		self.client: MyClient = client

	@commands.hybrid_command(
		hidden=True, name="reload", description="reload_specs-description", usage="reload_specs-usage"
	)
	@commands.is_owner()
	@app_commands.describe(cog="reload_specs-args-cog-description")
	@app_commands.rename(cog="reload_specs-args-cog-name")
	async def reload(self, ctx: Context, cog: str):
		try:
			benchmark = perf_counter()
			await self.client.reload_extension(f"cogs.{cog}")
			end = perf_counter() - benchmark
			await ctx.reply(content=f"Reloaded extension `{cog}` in **{end:.2f}s**")
			logger.info(f"{ctx.author.name} reloaded {cog}.py")
		except Exception as e:
			await ctx.reply(content=f"Failed to reload extension `{cog}`: {e}")

	@commands.hybrid_command(hidden=True, name="load", description="load_specs-description", usage="load_specs-usage")
	@commands.is_owner()
	@app_commands.describe(cog="load_specs-args-cog-description")
	@app_commands.rename(cog="load_specs-args-cog-name")
	async def load(self, ctx: Context, cog: str):
		try:
			benchmark = perf_counter()
			await self.client.load_extension(f"cogs.{cog}")
			end = perf_counter() - benchmark
			await ctx.reply(content=f"Loaded extension `{cog}` in **{end:.2f}s**")
			logger.info(f"{ctx.author.name} loaded {cog}.py")
		except Exception as e:
			await ctx.reply(content=f"Failed to load extension `{cog}`: {e}")

	@commands.hybrid_command(
		hidden=True, name="unload", description="unload_specs-description", usage="unload_specs-usage"
	)
	@commands.is_owner()
	@app_commands.describe(cog="unload_specs-args-cog-description")
	@app_commands.rename(cog="unload_specs-args-cog-name")
	async def unload(self, ctx: Context, cog: str):
		try:
			benchmark = perf_counter()
			await self.client.unload_extension(f"cogs.{cog}")
			end = perf_counter() - benchmark
			await ctx.reply(content=f"Unloaded extension `{cog}` in **{end:.2f}s**")
			logger.info(f"{ctx.author.name} unloaded {cog}.py")
		except Exception as e:
			await ctx.reply(content=f"Failed to unload extension `{cog}`: {e}")

	@commands.hybrid_command(
		hidden=True, name="l10nreload", description="l10nreload_specs-description", usage="l10nreload_specs-usage"
	)
	@commands.is_owner()
	@app_commands.describe(path="l10nreload_specs-args-path-description")
	@app_commands.rename(path="l10nreload_specs-args-path-name")
	async def l10nreload(self, ctx: Context, path: str = "./localization"):
		ctx.bot.custom_response.load_localizations(path)
		await ctx.reply(content="Reloaded localization files.")
		logger.info(f"{ctx.author.name} reloaded localization files.")

	@commands.hybrid_command(hidden=True, name="sync", description="sync_specs-description", usage="sync_specs-usage")
	@commands.is_owner()
	@app_commands.describe(guilds="sync_specs-args-guilds-description", scope="sync_specs-args-scope-description")
	@app_commands.rename(guilds="sync_specs-args-guilds-name", scope="sync_specs-args-scope-name")
	@app_commands.choices(
		scope=[
			app_commands.Choice(name="sync_specs-args-scope-local", value="~"),
			app_commands.Choice(name="sync_specs-args-scope-global", value="*"),
			app_commands.Choice(name="sync_specs-args-scope-resync", value="^"),
			app_commands.Choice(name="sync_specs-args-scope-slash", value="/"),
		]
	)
	async def sync(
		self,
		ctx: Context,
		guilds: commands.Greedy[discord.Object] = None,
		scope: Optional[Literal["~", "*", "^", "/"]] = None,
	) -> None:
		tree: discord.app_commands.CommandTree[ctx.bot] = ctx.bot.tree  # type: ignore
		benchmark = perf_counter()

		if not guilds:
			if scope == "~":
				synced = await tree.sync(guild=ctx.guild)
			elif scope == "*":
				tree.copy_global_to(guild=ctx.guild)
				synced = await tree.sync(guild=ctx.guild)
			elif scope == "^":
				tree.clear_commands(guild=ctx.guild)
				await tree.sync(guild=ctx.guild)
				synced = []
			elif scope == "/":
				update_slash_localizations()
				await ctx.reply(content="Reloaded slash localizations")
				return
			else:
				update_slash_localizations()
				synced = await tree.sync()

			end = perf_counter() - benchmark
			await ctx.reply(
				content=f"Synced **{len(synced)}** {'commands' if len(synced) != 1 else 'command'} {'globally' if scope is None else 'to the current guild'}, took **{end:.2f}s**"
			)
		else:
			update_slash_localizations()
			guilds_synced = 0
			for guild in guilds:
				try:
					await tree.sync(guild=guild)
				except discord.HTTPException:
					pass
				else:
					guilds_synced += 1

			end = perf_counter() - benchmark
			await ctx.reply(content=f"Synced the tree to **{guilds_synced}/{len(guilds)}** guilds, took **{end:.2f}s**")


async def setup(client: MyClient):
	await client.add_cog(Admin(client))
