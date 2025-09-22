import asyncio
import datetime
import json
import os
import socket
import traceback
from logging import getLogger
from pathlib import Path
from time import perf_counter
from typing import Any, Optional, Union

import aiohttp
import asyncpg
import discord
from discord import app_commands
from discord.ext import commands, localization
from helpers.emojis import LOADING

from core import Command, Context, SlashCommandLocalizer, slash_command_localization, update_slash_localizations
from helpers import custom_response, seconds_to_text


class MyClient(commands.AutoShardedBot):
	"""Represents the bot client. Inherits from `commands.AutoShardedBot`."""

	def __init__(self):
		update_slash_localizations()
		self.logger = getLogger(__name__)
		self.uptime: Optional[datetime.datetime] = None
		self.loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
		intents: discord.Intents = discord.Intents.all()
		self.db: asyncpg.Pool | None = None
		self.session: aiohttp.ClientSession | None = None
		self.ready_event = asyncio.Event()
		self.owner_ids = {
			648168353453572117,  # pearoo
			657350415511322647,  # liba
			452133888047972352,  # aki26
			1051181672508444683,  # sarky
		}
		super().__init__(
			command_prefix=self.get_prefix,
			heartbeat_timeout=150.0,
			intents=intents,
			case_insensitive=False,
			activity=discord.CustomActivity(name="Bot starting...", emoji="🟡"),
			status=discord.Status.idle,
			chunk_guilds_at_startup=False,
			loop=self.loop,
			member_cache_flags=discord.MemberCacheFlags.from_intents(intents),
			max_messages=20000,
			allowed_contexts=app_commands.AppCommandContext(guild=True, dm_channel=True, private_channel=True),
			allowed_installs=app_commands.AppInstallationType(guild=True, user=True),
			allowed_mentions=discord.AllowedMentions(everyone=False, roles=False),
		)
		self.custom_response = custom_response.CustomResponse(self)

	async def request(self, url: str):
		async with self.session.get(url) as response:
			return await response.json()

	async def get_prefix(self, message: discord.Message) -> Union[str, list[str]]:
		if __debug__:
			return "?"
		if not message.guild:
			return "?!"
		row = await self.db.fetchrow("SELECT prefix, mention FROM guilds WHERE guild_id = $1", message.guild.id)
		prefix, mention = row.get("prefix", "?!"), row.get("mention", True)
		if mention:
			return commands.when_mentioned_or(prefix)(self, message)
		else:
			return prefix

	async def on_guild_join(self, guild: discord.Guild):
		row = await self.db.fetchrow("SELECT * FROM guilds WHERE guild_id = $1", guild.id)
		if not row:
			await self.db.execute("INSERT INTO guilds (guild_id) VALUES ($1)", guild.id)

	async def get_context(self, origin: Union[discord.Message, discord.Interaction], /, *, cls=Context) -> Any:
		return await super().get_context(origin, cls=cls)

	async def setup_hook(self):
		self.logger.info("Running initial setup hook...")
		benchmark = perf_counter()

		await self.database_initialization()
		await self.first_time_database()
		await self.load_cogs()
		await self.tree.set_translator(SlashCommandLocalizer())
		self.session = aiohttp.ClientSession(
			connector=aiohttp.TCPConnector(resolver=aiohttp.AsyncResolver(), family=socket.AF_INET)
		)
		end = perf_counter() - benchmark
		self.logger.info(f"Initial setup hook complete in {end:.2f}s")

	@staticmethod
	async def db_connection_init(connection: asyncpg.connection.Connection):
		await connection.set_type_codec("jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")
		await connection.set_type_codec("json", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")

	async def database_initialization(self):
		self.logger.info("Connecting to database...")
		benchmark = perf_counter()
		# Connects to database
		self.db = await asyncpg.create_pool(
			host=os.getenv("DB_HOST"),
			database="lumin_beta",
			# ! Replace with default database name when ran for the first time
			# ! Any subsequent executions of this code must use `database="lumin"`
			user="lumin",
			password=os.getenv("DB_PASSWORD"),
			port=os.getenv("DB_PORT"),
			timeout=None,
			init=self.db_connection_init,
			max_inactive_connection_lifetime=120,  # timeout is 2 mins
		)
		end = perf_counter() - benchmark
		self.logger.info(f"Connected to database in {end:.2f}s")

	async def first_time_database(self):
		self.logger.info("Running first time database setup...")
		benchmark = perf_counter()
		database_exists = await self.db.fetchval(
			"SELECT 1 FROM information_schema.schemata WHERE schema_name = 'public'"
		)
		if not database_exists:
			await self.db.execute("CREATE DATABASE lumin_beta OWNER lumin")
			self.logger.info("Created database 'lumin'!")

		with open("first_time.sql", encoding="utf-8") as f:
			# "ok ok but pearoo how do i update this if i
			# feel like updating the db structure for no
			# particular reason"

			# please just use pycharm its actually goated,
			# if you add the db to the project and select
			# lumin.public.tables then press Ctrl + Alt + G
			# it will generate the SQL for you which is crazy
			# tbh like wtf
			await self.db.execute(f.read())

		end = perf_counter() - benchmark
		self.logger.info(
			f"First time database setup complete in {end:.2f}s, you may now comment out the execution of this method in setup_hook"
		)

	async def load_cogs(self):
		self.logger.info("Loading cogs...")
		benchmark = perf_counter()

		# Load all cogs within the cogs folder
		allowed: list[str] = [
			"afk",
			"basic",
			"economy",
			"giveaway",
			"help",
			"imagesinfo",
			"log",
			"mod",
			"say",
			"setup",
			"snapshot",
			"status",
		]

		cogs = Path("cogs").glob("*.py")
		for cog in cogs:
			if cog.stem in allowed:  # if you're having issues with cogs not loading, check this list
				await self.load_extension(f"cogs.{cog.stem}")
				self.logger.info(f"Loaded extension {cog.name}")
		end = perf_counter() - benchmark
		self.logger.info(f"Loaded cogs in {end:.2f}s")

	async def on_ready(self):
		if not hasattr(self, "uptime"):
			self.uptime = discord.utils.utcnow()
		self.logger.info("Bot is ready!")
		self.logger.info(f"Servers: {len(self.guilds)}, Commands: {len(self.commands)}, Shards: {self.shard_count}")
		self.logger.info(f"Loaded cogs: {', '.join([cog for cog in self.cogs])}")
		self.logger.info(f"discord-localization v{localization.__version__}")

	async def handle_error(
		self, ctx: Context, error: Union[discord.errors.DiscordException, app_commands.AppCommandError]
	):
		command = None
		if isinstance(ctx, (Context, commands.Context)):
			command = Command.from_ctx(ctx)
		elif hasattr(ctx, "command") and ctx.command:
			command = Command.from_ctx(ctx)

		if isinstance(error, commands.HybridCommandError):
			error = error.original  # type: ignore

		match error:
			case commands.MissingRequiredArgument():
				error: commands.MissingRequiredArgument
				name = slash_command_localization(error.param.name, ctx)
				parameter = f"[{name if error.param.required else f'({name})'}]"

				await ctx.send("errors.missing_required_argument", command=command, parameter=parameter)
			case commands.BotMissingPermissions() | app_commands.BotMissingPermissions():
				error: commands.BotMissingPermissions
				permissions = [
					(await self.custom_response(f"permissions.{permission}", ctx))
					for permission in error.missing_permissions
				]

				await ctx.send("errors.bot_missing_permissions", command=command, permissions=", ".join(permissions))
			case commands.BadArgument():
				await ctx.send("errors.bad_argument", command=command)
				raise error
			case commands.MissingPermissions() | app_commands.MissingPermissions():
				error: commands.MissingPermissions
				permissions = [
					(await self.custom_response(f"permissions.{permission}", ctx))
					for permission in error.missing_permissions
				]

				await ctx.send("errors.missing_permissions", command=command, permissions=", ".join(permissions))
			case commands.CommandOnCooldown():
				error: commands.CommandOnCooldown
				retry_after = seconds_to_text(int(error.retry_after))
				await ctx.send("errors.command_on_cooldown", command=command, retry_after=retry_after)
			case commands.ChannelNotFound():
				await ctx.send("errors.channel_not_found", command=command)
			case commands.EmojiNotFound():
				await ctx.send("errors.emoji_not_found", command=command)
			case commands.MemberNotFound():
				await ctx.send("errors.member_not_found", command=command)
			case commands.UserNotFound():
				await ctx.send("errors.user_not_found", command=command)
			case commands.RoleNotFound():
				await ctx.send("errors.role_not_found", command=command)
			case discord.Forbidden():
				await ctx.send("errors.forbidden", command=command)
			case commands.NotOwner():
				await ctx.send("errors.not_owner", command=command)
			case commands.CommandNotFound() | app_commands.CommandNotFound():
				return
			case discord.RateLimited():
				channel: discord.TextChannel = await self.fetch_channel(1268260404677574697)
				webhook: discord.Webhook | None = discord.utils.get(
					await channel.webhooks(), name=f"{self.user.display_name} Rate Limit"
				)
				if not webhook:
					webhook = await channel.create_webhook(name=f"{self.user.display_name} Rate Limit")
				await webhook.send(
					content=f"# ⚠️ RATE LIMIT\n**Guild:** {ctx.guild.name} / {ctx.guild.id}\n**User:** {ctx.author} / {ctx.author.id}\n**Command:** {ctx.command} {'- failed' if ctx.command_failed else ''}\n**Error:** {error}"
				)
				raise error
			case _:
				# if the error is unknown, log it
				channel: discord.TextChannel = (
					ctx.channel if __debug__ and ctx and ctx.channel else await self.fetch_channel(1268260404677574697)
				)
				stack = "".join(traceback.format_exception(type(error), error, error.__traceback__))
				# if stack is more than 1700 characters, turn it into a .txt file and store it as an attachment
				too_long = len(stack) > 1700
				file: discord.File | None = None
				if too_long:
					with open("auto-report_stack-trace.txt", "w") as f:
						f.write(stack)
					file = discord.File(fp="auto-report_stack-trace.txt", filename="error.txt")
					stack = "The stack trace was too long to send in a message, so it was saved as a file."
				webhook: discord.Webhook = discord.utils.get(
					await channel.webhooks(), name=f"{self.user.display_name} Errors"
				)
				if not webhook:
					webhook = await channel.create_webhook(
						name=f"{self.user.display_name} Errors", avatar=await ctx.me.avatar.read()
					)
				await webhook.send(
					content=f"**ID:** {ctx.message.id}\n"
					f"**Guild:** {ctx.guild.name if ctx.guild else 'DMs'} / {ctx.guild.id if ctx.guild else 0}\n"
					f"**User:** {ctx.author} / {ctx.author.id}\n"
					f"**Command:** {ctx.command}\n"
					f"```{stack}```",
					file=file if too_long and file else discord.abc.MISSING,
				)  # type: ignore
				await ctx.reply(
					f"An error has occured and has been reported to the developers. Report ID: `{ctx.message.id}`",
					mention_author=False,
				)
				raise error

	async def on_command_error(self, ctx: Context, error: discord.errors.DiscordException):
		await self.handle_error(ctx, error)

	async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
		await self.handle_error(await Context.from_interaction(interaction), error)

	async def before_invoke(self, ctx: Context):
		if ctx.guild:
			is_set_up = await self.db.fetchrow("SELECT * FROM guilds WHERE guild_id = $1", ctx.guild.id)
			if not is_set_up:
				await self.db.execute("INSERT INTO guilds (guild_id) VALUES ($1)", ctx.guild.id)
		try:
			# Signals that the bot is still thinking / performing a task
			if ctx.interaction and ctx.interaction.type == discord.InteractionType.application_command:
				await ctx.interaction.response.defer(thinking=True)  # type: ignore
			else:
				await ctx.message.add_reaction(LOADING)
		except discord.HTTPException:
			pass

	async def after_invoke(self, ctx: Context):
		try:
			await ctx.message.remove_reaction(LOADING, ctx.me)
		except discord.HTTPException:
			pass
