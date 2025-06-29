import asyncio
import datetime
import json
import logging
import os
import pathlib
import platform
import socket
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Optional, Literal, Union, Any, Sequence

import aiohttp
import asyncpg
import discord
from discord import app_commands
from discord.ext import commands, localization
from dotenv import load_dotenv

import helpers
from helpers import custom_response, emojis

for handler in logging.root.handlers[:]:
	# prevent double logging
	logging.root.removeHandler(handler)

discord.utils.setup_logging(level=logging.INFO, root=True)
logger = logging.getLogger()

load_dotenv()
TOKEN = os.getenv("TOKEN")
DEBUG = False
"""Whether the bot is in debug mode or not. This controls which token and prefix to use and where to send error reports.
If you're on Windows, this will be set to True automatically."""
if platform.system() == "Windows":
	DEBUG = True

if DEBUG:
	TOKEN = os.getenv("DEBUG_TOKEN")

slash_command_localization: Optional[localization.Localization] = None

def update_slash_localizations():
	slash_localizations = { }

	# load the slash localization files and combine them into one dictionary
	for file_path in pathlib.Path("./slash_localization").glob("*.l10n.json"):
		lang = file_path.stem.removesuffix(".l10n")
		try:
			with open(file_path, encoding="utf-8") as f:
				data = json.load(f)
				if not isinstance(data, dict):
					raise ValueError(f"Expected dict in {file_path}, got {type(data).__name__}")
				if lang not in slash_localizations:
					slash_localizations[lang] = { }
				slash_localizations[lang].update(data)
		except Exception as e:
			logger.warning(f"Failed to load {file_path}: {e}")
	global slash_command_localization
	slash_command_localization = localization.Localization(slash_localizations, default_locale="en", separator="-")

if __name__ == '__main__':
	if platform.system() != "Windows":
		import uvloop  # type: ignore

		uvloop.install()
		asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
		logger.info("Using uvloop event loop policy")
	else:
		asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
		logger.info("Using default event loop policy")

@dataclass
class Command:
	name: str
	description: str
	usage: str
	prefix: str

	@classmethod
	def from_ctx(cls, ctx: commands.Context):
		prefix = ctx.prefix.replace(ctx.me.mention, f"@{ctx.me.display_name}") if ctx.prefix else "?!"
		if ctx.command and slash_command_localization:
			usage = slash_command_localization(ctx.command.usage, ctx) if ctx.command.usage else ctx.command.qualified_name
			description = slash_command_localization(ctx.command.description, ctx)
			return cls(
				name=ctx.command.qualified_name, description=description if isinstance(description, str) and description else "-",
				usage=f"{prefix}{usage}", prefix=prefix
			)

@dataclass
class Argument:
	name: str
	description: str
	default: Any
	annotation: Any
	required: bool

	@classmethod
	def from_param(cls, param: commands.Parameter, ctx: commands.Context):
		if slash_command_localization:
			localized_name = slash_command_localization(param.displayed_name or param.name, ctx)
			description = slash_command_localization(param.description, ctx) if param.description else "-"
			return cls(
				name=localized_name if isinstance(localized_name, str) else "arg", description=description if isinstance(description, str) and description else "-",
				default=param.default, annotation=param.annotation, required=param.required
			)

class Context(commands.Context):
	async def send(  # type: ignore
		self, key: Optional[str] = None, *, content: Optional[str] = None, tts: bool = False,
		embed: Optional[discord.Embed] = None, embeds: Optional[Sequence[discord.Embed]] = None,
		file: Optional[discord.File] = None, files: Optional[Sequence[discord.File]] = None,
		stickers: Optional[Sequence[Union[discord.GuildSticker, discord.StickerItem]]] = None,
		delete_after: Optional[float] = None, nonce: Optional[Union[str, int]] = None,
		allowed_mentions: Optional[discord.AllowedMentions] = None,
		reference: Optional[Union[discord.Message, discord.MessageReference, discord.PartialMessage]] = None,
		mention_author: Optional[bool] = None, view: Optional[discord.ui.View] = None, suppress_embeds: bool = False,
		ephemeral: bool = False, silent: bool = False, poll: Optional[discord.Poll] = None, **format_kwargs: object
	) -> discord.Message:
		"""
		Sends a localized or raw message by merging the arguments passed to send with a
		localized payload (if a localization key is provided) and then delegating to
		super().send.

		Exactly one of the following must be provided:
		  - A localization key as the first positional argument (key)
		  - A raw message string via the keyword-only argument `content`

		No errors will be raised if both or neither are provided.
		"""
		base_args = { "content": content, "tts": tts, "embed": embed, "embeds": embeds, "file": file, "files": files,
			"stickers": stickers, "nonce": nonce, "allowed_mentions": allowed_mentions, "reference": reference,
			"mention_author": mention_author, "view": view, "suppress_embeds": suppress_embeds, "ephemeral": ephemeral,
			"silent": silent, "poll": poll }

		locale_str = self.guild.preferred_locale if self.guild and self.guild.preferred_locale else "en"

		if key is not None:
			localized_payload = await self.bot.custom_response.get_message(key, locale_str, **format_kwargs)
		else:
			localized_payload = content

		if isinstance(localized_payload, dict):
			base_args.update(localized_payload)
		else:
			base_args["content"] = localized_payload

		merged_args = { k: v for k, v in base_args.items() if v is not None }

		msg = await super().send(**merged_args)
		if delete_after is not None:
			await msg.delete(delay=delete_after)
		return msg

	async def reply(self, *args, **kwargs) -> discord.Message:
		"""
		Behaves like send, but automatically sets reference to self.message. Don't use this unless it's necessary.
		"""
		kwargs.setdefault("reference", self.message)
		return await self.send(*args, **kwargs)

class SlashCommandLocalizer(app_commands.Translator):
	"""Localizes slash commands and their arguments using discord-localization.
	This uses the localization set by the user, not the guild's locale."""

	async def translate(
		self, string: app_commands.locale_str, locale: discord.Locale, context: app_commands.TranslationContext
		) -> str | None:
		if slash_command_localization:
			localized: Union[str, list[str], dict[str, Any]] = slash_command_localization.translate(string.message, str(locale))
			if isinstance(localized, (list, dict)):
				return None
			return localized

	async def unload(self) -> None:
		benchmark = perf_counter()
		logger.info("Unloading Slash Localizer...")
		await super().unload()
		end = perf_counter() - benchmark
		logger.info(f"Unloaded Slash Localizer in {end:.2f}s")

	async def load(self) -> None:
		benchmark = perf_counter()
		logger.info("Loading Slash Localizer...")
		await super().load()
		end = perf_counter() - benchmark
		logger.info(f"Loaded Slash Localizer in {end:.2f}s")

class MyClient(commands.AutoShardedBot):
	"""Represents the bot client. Inherits from `commands.AutoShardedBot`."""

	def __init__(self):
		update_slash_localizations()
		self.uptime: Optional[datetime.datetime] = None
		self.loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()
		intents: discord.Intents = discord.Intents.all()
		self.db: asyncpg.Pool = None  # type: ignore
		self.ready_event = asyncio.Event()
		error_log_channel_id_str = os.getenv("ERROR_LOG_CHANNEL_ID")
		self.error_log_channel_id = int(error_log_channel_id_str) if error_log_channel_id_str else None
		self.devs = [648168353453572117,  # pearoo
			657350415511322647,  # liba
			452133888047972352,  # aki26
			1051181672508444683,  # sarky
		]
		super().__init__(
			command_prefix=self.get_prefix, # type: ignore
			heartbeat_timeout=150.0, intents=intents, case_insensitive=False,
			activity=discord.CustomActivity(name="Bot starting...", emoji="🟡"), status=discord.Status.idle,
			chunk_guilds_at_startup=False, loop=self.loop,
			member_cache_flags=discord.MemberCacheFlags.from_intents(intents), max_messages=20000,
			allowed_contexts=app_commands.AppCommandContext(
				guild=True,
				dm_channel=True,
				private_channel=True
			),
			allowed_installs=app_commands.AppInstallationType(guild=True, user=True)
		)
		self.custom_response = custom_response.CustomResponse(self)

	async def request(self, url: str):
		async with self.session as session:
			async with session.get(url) as response:
				return await response.json()

	async def get_prefix(self, message: discord.Message) -> Union[str, list[str]]:
		if DEBUG:
			return "?"
		if not message.guild:
			return "?!"
		prefix = await self.db.fetchrow("SELECT * FROM guilds WHERE guild_id = $1", message.guild.id)
		if not prefix:
			return commands.when_mentioned_or("?!")(self, message)
		else:
			if prefix["mention"]:
				return commands.when_mentioned_or(prefix["prefix"])(self, message)
			else:
				return prefix["prefix"]

	async def on_guild_join(self, guild: discord.Guild):
		row = await self.db.fetchrow("SELECT * FROM guilds WHERE guild_id = $1", guild.id)
		if not row:
			await self.db.execute("INSERT INTO guilds (guild_id) VALUES ($1)", guild.id)

	async def get_context( # type: ignore # pyright is crying because of mismatched arguments, we can disregard it
		self, origin: Union[discord.Message, discord.Interaction], /, *,
		cls=Context, ) -> Any:
		return await super().get_context(origin, cls=cls)

	async def setup_hook(self):
		logger.info("Running initial setup hook...")
		benchmark = perf_counter()

		await self.database_initialization()
		await self.first_time_database()
		await self.load_cogs()
		await self.tree.set_translator(SlashCommandLocalizer())
		self.session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(resolver=aiohttp.AsyncResolver(), family=socket.AF_INET))
		end = perf_counter() - benchmark
		logger.info(f"Initial setup hook complete in {end:.2f}s")

	@staticmethod
	async def db_connection_init(connection: asyncpg.connection.Connection):
		await connection.set_type_codec(
			"jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
		)
		await connection.set_type_codec(
			"json",
			encoder=json.dumps,
			decoder=json.loads,
			schema="pg_catalog"
		)

	async def database_initialization(self):
		logger.info("Connecting to database...")
		benchmark = perf_counter()
		# Connects to database
		self.db = await asyncpg.create_pool(
			host=os.getenv("DB_HOST"), database="lumin_beta",
			# ! Replace with default database name when ran for the first time
			# ! Any subsequent executions of this code must use `database="lumin"`
			user="lumin", password=os.getenv("DB_PASSWORD"), port=os.getenv("DB_PORT"), timeout=None, init=self.db_connection_init,
			max_inactive_connection_lifetime=120  # timeout is 2 mins
		)
		end = perf_counter() - benchmark
		logger.info(f"Connected to database in {end:.2f}s")

	async def first_time_database(self):
		logger.info("Running first time database setup...")
		benchmark = perf_counter()
		database_exists = await self.db.fetchval(
			"SELECT 1 FROM information_schema.schemata WHERE schema_name = 'public'"
			)  # type: ignore
		if not database_exists:
			await self.db.execute("CREATE DATABASE lumin_beta OWNER lumin")
			logger.info("Created database 'lumin'!")

		# integer\s+default\s+nextval\('(\w+)_\w+_seq'::regclass\)\s+not\s+null\s+constraint\s+\1_\w+_pkey\s+primary\s+key,

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
		logger.info(
			f"First time database setup complete in {end:.2f}s, you may now comment out the execution of this method in setup_hook"
			)

	async def load_cogs(self):
		logger.info("Loading cogs...")
		benchmark = perf_counter()

		# Load all cogs within the cogs folder
		allowed: list[str] = ["afk", "basic", "economy", "info", "mod", "setup", "snapshot", "status","log"]
		if DEBUG:
			allowed.extend(("log",))

		cogs = Path("./cogs").glob("*.py")
		for cog in cogs:
			if cog.stem in allowed:  # if you're having issues with cogs not loading, check this list
				await self.load_extension(f"cogs.{cog.stem}")
				logger.info(f"Loaded extension {cog.name}")
		end = perf_counter() - benchmark
		logger.info(f"Loaded cogs in {end:.2f}s")

	async def on_ready(self):
		if not hasattr(self, "uptime"):
			self.uptime = discord.utils.utcnow()
		logger.info("Bot is ready!")
		logger.info(f"Servers: {len(self.guilds)}, Commands: {len(self.commands)}, Shards: {self.shard_count}")
		logger.info(f"Loaded cogs: {', '.join([cog for cog in self.cogs])}")
		logger.info(f"discord-localization v{localization.__version__}")

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
				permissions = [(await self.custom_response(f"permissions.{permission}", ctx)) for permission in
				               error.missing_permissions]

				await ctx.send("errors.bot_missing_permissions", command=command, permissions=", ".join(permissions))
			case commands.BadArgument():
				await ctx.send("errors.bad_argument", command=command)
				raise error
			case commands.MissingPermissions() | app_commands.MissingPermissions():
				error: commands.MissingPermissions
				permissions = [(await self.custom_response(f"permissions.{permission}", ctx)) for permission in
				               error.missing_permissions]

				await ctx.send("errors.missing_permissions", command=command, permissions=", ".join(permissions))
			case commands.CommandOnCooldown():
				error: commands.CommandOnCooldown
				retry_after = helpers.convert_time_to_text(int(error.retry_after))
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
				if not self.error_log_channel_id:
					raise error
				channel: discord.TextChannel = await self.fetch_channel(self.error_log_channel_id)
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
				report_channel: Optional[discord.TextChannel] = None
				if DEBUG and ctx and ctx.channel:
					report_channel = ctx.channel
				elif self.error_log_channel_id:
					report_channel = await self.fetch_channel(self.error_log_channel_id)

				if not report_channel:
					logger.error(f"An unhandled error occurred, and no error reporting channel is configured.")
					raise error

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
					await report_channel.webhooks(), name=f"{self.user.display_name} Errors"
					)
				if not webhook:
					avatar_data = await ctx.me.avatar.read() if ctx.me.avatar else None
					webhook = await report_channel.create_webhook(
						name=f"{self.user.display_name} Errors", avatar=avatar_data
						)
				await webhook.send(
					content=f"**ID:** {ctx.message.id}\n"
					        f"**Guild:** {ctx.guild.name if ctx.guild else "DMs"} / {ctx.guild.id if ctx.guild else 0}\n"
					        f"**User:** {ctx.author} / {ctx.author.id}\n"
					        f"**Command:** {ctx.command}\n"
					        f"```{stack}```",
					file=file if too_long and file else discord.abc.MISSING
					)  # type: ignore
				await ctx.reply(
					f"An error has occured and has been reported to the developers. Report ID: `{ctx.message.id}`",
					mention_author=False
					)
				raise error

	async def on_command_error(self, ctx: Context, error: discord.errors.DiscordException):
		await self.handle_error(ctx, error)

	async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
		await self.handle_error(await Context.from_interaction(interaction), error)

logger.info("Starting the bot...")
client = MyClient()

@client.before_invoke
async def before_invoke(ctx: commands.Context):
	if ctx.guild:
		is_set_up = await client.db.fetchrow("SELECT * FROM guilds WHERE guild_id = $1", ctx.guild.id)
		if not is_set_up:
			await client.db.execute("INSERT INTO guilds (guild_id) VALUES ($1)", ctx.guild.id)
	try:
		# Signals that the bot is still thinking / performing a task
		if ctx.interaction and ctx.interaction.type == discord.InteractionType.application_command:
			await ctx.interaction.response.defer(thinking=True)  # type: ignore
		else:
			await ctx.message.add_reaction(emojis.LOADING)
	except discord.HTTPException:
		pass

@client.after_invoke
async def after_invoke(ctx: commands.Context):
	try:
		await ctx.message.remove_reaction(emojis.LOADING, ctx.me)
	except discord.HTTPException:
		pass

@client.hybrid_command(name="reload", description="reload_specs-description", usage="reload_specs-usage")
@commands.is_owner()
@app_commands.describe(cog="reload_specs-args-cog-description")
@app_commands.rename(cog="reload_specs-args-cog-name")
async def reload(ctx: commands.Context, cog: str):
	try:
		benchmark = perf_counter()
		await client.reload_extension(f"cogs.{cog}")
		end = perf_counter() - benchmark
		await ctx.reply(content=f"Reloaded extension `{cog}` in **{end:.2f}s**")
		logger.info(f"{ctx.author.name} reloaded {cog}.py")
	except Exception as e:
		await ctx.reply(content=f"Failed to reload extension `{cog}`: {e}")

@client.hybrid_command(name="load", description="load_specs-description", usage="load_specs-usage")
@commands.is_owner()
@app_commands.describe(cog="load_specs-args-cog-description")
@app_commands.rename(cog="load_specs-args-cog-name")
async def load(ctx: commands.Context, cog: str):
	try:
		benchmark = perf_counter()
		await client.load_extension(f"cogs.{cog}")
		end = perf_counter() - benchmark
		await ctx.reply(content=f"Loaded extension `{cog}` in **{end:.2f}s**")
		logger.info(f"{ctx.author.name} loaded {cog}.py")
	except Exception as e:
		await ctx.reply(content=f"Failed to load extension `{cog}`: {e}")

@client.hybrid_command(name="unload", description="unload_specs-description", usage="unload_specs-usage")
@commands.is_owner()
@app_commands.describe(cog="unload_specs-args-cog-description")
@app_commands.rename(cog="unload_specs-args-cog-name")
async def unload(ctx: commands.Context, cog: str):
	try:
		benchmark = perf_counter()
		await client.unload_extension(f"cogs.{cog}")
		end = perf_counter() - benchmark
		await ctx.reply(content=f"Unloaded extension `{cog}` in **{end:.2f}s**")
		logger.info(f"{ctx.author.name} unloaded {cog}.py")
	except Exception as e:
		await ctx.reply(content=f"Failed to unload extension `{cog}`: {e}")

@client.hybrid_command(name="l10n-reload", description="l10n-reload_specs-description", usage="l10n-reload_specs-usage")
@commands.is_owner()
@app_commands.describe(path="l10n-reload_specs-args-path-description")
@app_commands.rename(path="l10n-reload_specs-args-path-name")
async def l10nreload(ctx: commands.Context, path: str = "./localization"):
	ctx.bot.custom_response.load_localizations(path)
	await ctx.reply(content="Reloaded localization files.")
	logger.info(f"{ctx.author.name} reloaded localization files.")

@client.hybrid_command(name="sync", description="sync_specs-description", usage="sync_specs-usage")
@commands.is_owner()
@app_commands.describe(guilds="sync_specs-args-guilds-description", scope="sync_specs-args-scope-description")
@app_commands.rename(guilds="sync_specs-args-guilds-name", scope="sync_specs-args-scope-name")
@app_commands.choices(
	scope=[app_commands.Choice(name="sync_specs-args-scope-local", value="~"),
		app_commands.Choice(name="sync_specs-args-scope-global", value="*"),
		app_commands.Choice(name="sync_specs-args-scope-resync", value="^"),
	    app_commands.Choice(name="sync_specs-args-scope-slash", value="/")]
)
async def sync(
	ctx: commands.Context, guilds: commands.Greedy[discord.Object] = None,
	scope: Optional[Literal["~", "*", "^", "/"]] = None
	) -> None:
	tree: discord.app_commands.CommandTree[ctx.bot] = ctx.bot.tree  # type: ignore
	benchmark = time.perf_counter()

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

		end = time.perf_counter() - benchmark
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

		end = time.perf_counter() - benchmark
		await ctx.reply(content=f"Synced the tree to **{guilds_synced}/{len(guilds)}** guilds, took **{end:.2f}s**")

async def start():
	try:
		await client.start(TOKEN)
	except KeyboardInterrupt:
		logger.error("KeyboardInterrupt: Bot shut down by console")
		await client.close()

if __name__ == "__main__":
	if DEBUG:
		TOKEN = os.getenv("DEBUG_TOKEN")
		logger.info("Running in debug mode")
	try:
		loop = asyncio.new_event_loop()
		loop.run_until_complete(start())
	except KeyboardInterrupt:
		logger.error("KeyboardInterrupt: Bot shut down by console")
