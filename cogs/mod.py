import datetime
from copy import deepcopy
from enum import Enum
from typing import Any, Literal, Self

import asyncpg
import discord
from discord import app_commands
from discord.ext import commands

import main
from helpers import (
	CustomGuild,
	CustomMember,
	CustomTextChannel,
	CustomUser,
	FormatDateTime,
	convert_to_query,
	custom_response,
	seconds_to_text,
	text_to_seconds,
)
from main import MyClient


class CaseType(Enum):
	WARN = 1
	MUTE = 2
	KICK = 3
	BAN = 4


class Case:
	def __init__(
		self,
		_type: CaseType,
		_id: int,
		guild: discord.Guild,
		user: discord.Member | discord.User,
		moderator: discord.User,
		created: datetime.datetime | None = None,
		reason: str | None = None,
		expires: datetime.datetime | None = None,
		message: str | None = None,
	):
		self.type: CaseType = _type
		self.id: int = _id
		self._guild: discord.Guild = guild
		self._user: discord.Member | discord.User = user
		self._reason: str | None = reason
		self._moderator: discord.User = moderator
		self.expires: datetime.datetime | None = expires
		self.message: str | None = message
		self.length: str | None = discord.utils.format_dt(self.expires, "R") if self.expires else self.expires
		self._created: datetime.datetime = created or datetime.datetime.now()

	def __repr__(self):
		return f"Case(type={self.type} user={self._user} reason={self.reason} moderator={self._moderator} duration={self.expires} message={self.message} id={self.id})"

	def __eq__(self, other):
		return self.id == other.id

	def __ne__(self, other):
		return self.id != other.id

	def __lt__(self, other):
		return self.expires < other.expires

	def __le__(self, other):
		return self.expires <= other.expires

	def __gt__(self, other):
		return self.expires > other.expires

	def __ge__(self, other):
		return self.expires >= other.expires

	def __int__(self):
		return self.id

	def __bool__(self):
		if self.expires is None:
			return True
		return self.expires > datetime.datetime.now()

	def __len__(self):
		if self.expires is None:
			return 0
		return datetime.datetime.now() - self.expires

	@classmethod
	def from_dict(cls, data: dict, client: discord.Client, get_type: bool = False) -> Self:
		"""Create a `Case` from a dictionary.

		Parameters
		----------
		data: `dict`
		        The dictionary to create the `Case` from.
		client: `discord.Client`
		        The client to get the guilds with.
		get_type: `bool`
		        Whether to return the type of the case in the dictionary.
		"""
		data = dict(data)
		data.pop("id")
		case_type = CaseType(data.pop("type"))
		data["_type"] = case_type
		data["_id"] = data.pop("case_id")
		data["guild"] = client.get_guild(data.pop("guild_id"))
		data["user"] = client.get_user(data.pop("user_id"))
		data["moderator"] = client.get_user(data.pop("moderator_id"))

		if not get_type:
			data.pop("_type", None)
		return cls(**data)

	@classmethod
	async def from_user(
		cls,
		db: asyncpg.Pool,
		user: discord.Member | discord.User,
		client: discord.Client,
		guild: discord.Guild,
		limit: int | None = None,
		get_type: bool = True,
	) -> list[Self]:
		"""Generate a list of `Case`s from a user.

		Parameters
		----------
		db: `asyncpg.Pool`
		        The database connection pool.
		user: Union[`discord.Member`, `discord.User`]
		        The user to get the cases from.
		client: `discord.Client`
		        The client to get the guilds with.
		guild: `discord.Guild`
		        The guild to get the cases from.
		limit: `int`
		        The limit of cases to get. If None, it will get all cases.
		get_type: `bool`
		        Whether to return the type of the case in the result dictionary.

		Returns
		-------
		list[`Case`]
		        The list of cases.
		"""
		return await cls.from_db(db, client, guild, limit=limit, get_type=get_type, user=user)

	@classmethod
	async def from_moderator(
		cls,
		db: asyncpg.Pool,
		moderator: discord.User,
		client: discord.Client,
		guild: discord.Guild,
		limit: int | None = None,
	) -> list[Self]:
		"""Generate a list of `Case`s given by a moderator.

		Parameters
		----------
		db: `asyncpg.Pool`
		        The database connection pool.
		moderator: `discord.User`
		        The moderator to get the cases from.
		client: `discord.Client`
		        The client to get the guilds with.
		guild: `discord.Guild`
		        The guild to get the cases from.
		limit: `int`
		        The limit of cases to get. If None, it will get all cases.

		Returns
		-------
		list[`Case`]
		        The list of cases.
		"""
		return await cls.from_db(db, client, guild, limit=limit, moderator=moderator)

	@classmethod
	async def from_id(
		cls,
		db: asyncpg.Pool,
		client: discord.Client,
		guild: discord.Guild,
		case_id: int,
		get_type: bool = False,
	) -> Self | None:
		"""Get a `Case` from an ID.

		Parameters
		----------
		db: `asyncpg.Pool`
		        The database connection pool.
		client: `discord.Client`
		        The client to get the guilds with.
		guild: `discord.Guild`
		        The guild to get the case from.
		case_id: `int`
		        The ID of the case.
		get_type: `bool`
		        Whether to return the type of the case in the result dictionary.

		Returns
		-------
		Optional[`Case`]
		        The case.
		"""
		result = await db.fetch(
			"SELECT * FROM cases WHERE case_id = $1 AND guild_id = $2",
			case_id,
			guild.id,
		)
		if not result:
			return None
		return cls.from_dict(result[0], client, get_type)

	@classmethod
	async def from_db(
		cls,
		db: asyncpg.Pool,
		client: discord.Client,
		guild: discord.Guild | None = None,
		*,
		limit: int | None = None,
		get_type: bool = False,
		**filters: Any,
	) -> list[Any]:
		"""
		Retrieve cases from the database based on the provided attributes.

		Parameters
		----------
		db: `asyncpg.Pool`
		        The database connection pool.
		client: `discord.Client`
		        The client instance.
		guild: `discord.Guild`
		        The guild to get the cases for. Defaults to None.
		limit: `int`
		        The limit of cases to retrieve. If None, retrieves all cases.
		get_type: `bool`
		        Set to true if you want a Case object. Set to false if you want a corresponding mod action object.
		**filters: Any
		        Additional filters for querying cases (e.g., user=..., moderator=...).

		Returns
		-------
		list[`Case`]
		        A list of cases matching the filters.
		"""
		query, query_parameters = convert_to_query("cases", guild, limit, **filters)

		result = await db.fetch(query, *query_parameters)

		case_mapping = {
			CaseType.WARN: Warn,
			CaseType.MUTE: Mute,
			CaseType.KICK: Kick,
			CaseType.BAN: Ban,
		}

		cases = []
		for case_data in result:
			base_case = cls.from_dict(case_data, client, get_type)
			case_class = case_mapping.get(base_case.type, cls)
			as_dict = base_case.to_dict()
			if as_dict.get("_type") is None:
				cases.append(cls(**as_dict))  # type: ignore
			else:
				as_dict.pop("_type", None)
				cases.append(case_class(**as_dict))
		return cases

	def to_dict(
		self,
	) -> dict[
		str,
		CaseType | int | discord.Guild | discord.Member | discord.User | str | datetime.datetime | None,
	]:
		"""Convert the `Case` to a dictionary."""
		return {
			"_type": self.type,
			"_id": self.id,
			"guild": self._guild,
			"user": self._user,
			"moderator": self._moderator,
			"reason": self.reason,
			"expires": self.expires,
			"message": self.message,
		}

	async def before_deletion(self):
		"""An overrideable method that is called before a case is deleted. The default implementation does nothing.

		Example usage: when deleting a Case(type=CaseType.MUTE), you want to remove the timeout from the user."""
		pass

	async def after_deletion(self):
		"""An overrideable method that is called after a case is deleted. The default implementation does nothing.

		Example usage: when deleting a Case(type=CaseType.MUTE), you want to remove the timeout from the user."""
		pass

	async def delete(self, db: asyncpg.Pool) -> None:
		"""Delete the case from the database. This will also call `before_deletion` and `after_deletion`.

		Parameters
		----------
		db: `asyncpg.Pool`
		        The database connection pool.
		"""
		if self._user not in self._guild.members:
			return

		await self.before_deletion()
		await db.execute("DELETE FROM cases WHERE case_id = $1", self.id)
		await self.after_deletion()

	async def before_creation(self) -> None:
		"""An overrideable method that is called before a case is created. The default implementation does nothing."""
		pass

	async def after_creation(self) -> None:
		"""An overrideable method that is called after a case is created. The default implementation does nothing."""
		pass

	async def create(self, db: asyncpg.Pool) -> Self | None:
		"""Create the case in the database.

		Parameters
		----------
		db: `asyncpg.Pool`
		        The database connection pool.

		Returns
		-------
		`Case`
		        The created case.
		"""
		if self._user not in self._guild.members:
			return None

		await self.before_creation()
		await db.execute(
			"INSERT INTO cases (type, guild_id, case_id, user_id, moderator_id, reason, expires, message) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
			self.type.value,
			self._guild.id,
			self.id,
			self._user.id,
			self._moderator.id,
			self.reason,
			self.expires,
			self.message,
		)
		await self.after_creation()
		return self

	@staticmethod
	def generate_id(message: discord.Message) -> int:
		"""Generate a case ID from a message."""
		return message.id

	async def edit(self, db: asyncpg.Pool, case: Self) -> None:
		"""Edit the case in the database.

		Parameters
		----------
		db: `asyncpg.Pool`
		        The database connection pool.
		case: `Case`
		        The new case data; if something is not set in the new case, it will be set to the old case's data.
		"""
		await db.execute(
			"UPDATE cases SET user_id = $1, reason = $2, expires = $3, message = $4 WHERE case_id = $5",
			case._user.id,
			case.reason,
			case.expires,
			case.message,
			self.id,
		)

	def copy(self) -> Self:
		"""Copy the case."""
		return deepcopy(self)

	@property
	def created(self) -> FormatDateTime:
		"""The creation date of the case."""
		return FormatDateTime(self._created, "R")

	@property
	def reason(self) -> str | None:
		return self._reason

	@reason.setter
	def reason(self, value: str) -> None:
		self._reason = value

	@property
	def guild(self) -> CustomGuild:
		return CustomGuild.from_guild(self._guild)

	@property
	def user(self) -> CustomUser:
		return (
			CustomUser.from_user(self._user)
			if isinstance(self._user, discord.User)
			else CustomMember.from_member(self._user)
		)

	@property
	def moderator(self) -> CustomUser:
		return CustomUser.from_user(self._moderator)


class Warn(Case):
	def __init__(
		self,
		_id: int,
		guild: discord.Guild,
		user: discord.Member | discord.User,
		moderator: discord.User,
		reason: str | None = None,
		expires: datetime.datetime | None = None,
		message: str | None = None,
		created: datetime.datetime = datetime.datetime.now(),
	):
		self._user = user
		self._guild = guild
		super().__init__(
			CaseType.WARN,
			_id,
			guild,
			user,
			moderator,
			created,
			reason,
			expires,
			message,
		)

	async def after_creation(self) -> None:
		"""Notifies the user about the warning."""
		self._custom_response = custom_response.CustomResponse(MyClient, "mod")
		message = await self._custom_response.get_message("mod.warn.notify", self._guild, warn=self)

		try:
			if isinstance(message, dict):
				await self._user.send(**message)
		except discord.Forbidden:
			pass

	async def after_deletion(self) -> None:
		"""Notifies the user about the removal of the warning."""
		self._custom_response = custom_response.CustomResponse(MyClient, "mod")
		message = await self._custom_response.get_message("mod.warn.unwarned", self._guild, warn=self)

		try:
			if isinstance(message, dict):
				await self._user.send(**message)
		except discord.Forbidden:
			pass


class Kick(Case):
	def __init__(
		self,
		_id: int,
		guild: discord.Guild,
		user: discord.Member | discord.User,
		moderator: discord.User,
		reason: str | None = None,
		message: str | None = None,
		created: datetime.datetime = datetime.datetime.now(),
		expires=None,
	):
		super().__init__(
			CaseType.KICK,
			_id,
			guild,
			user,
			moderator,
			created,
			reason,
			expires,
			message,
		)

	async def before_creation(self) -> None:
		"""Notifies the user about the kick."""
		self._custom_response = custom_response.CustomResponse(MyClient, "mod")
		message = await self._custom_response.get_message("mod.kick.notify", self._guild, kick=self)

		try:
			if isinstance(message, dict):
				await self._user.send(**message)
		except discord.Forbidden:
			pass

	async def after_creation(self) -> None:
		"""Kicks the user."""
		if isinstance(self._user, discord.Member):
			await self._user.kick(reason=f"Kicked by {self._moderator}")


class Mute(Case):
	def __init__(
		self,
		_id: int,
		guild: discord.Guild,
		user: discord.Member | discord.User,
		moderator: discord.User,
		expires: datetime.datetime,
		reason: str | None = None,
		message: str | None = None,
		created: datetime.datetime = datetime.datetime.now(),
	):
		super().__init__(
			CaseType.MUTE,
			_id,
			guild,
			user,
			moderator,
			created,
			reason,
			expires,
			message,
		)

	async def before_creation(self) -> None:
		"""Mutes the user."""
		self._custom_response = custom_response.CustomResponse(MyClient, "mod")
		reason = await self._custom_response("mod.mute.reason", self._guild, mute=self)
		if isinstance(self._user, discord.Member) and self.expires is not None:
			await self._user.timeout(
				self.expires.astimezone(datetime.timezone.utc),
				reason=reason if isinstance(reason, str) else None,
			)

	async def after_creation(self) -> None:
		"""Notifies the user about the mute."""
		self._custom_response = custom_response.CustomResponse(MyClient, "mod")
		message = await self._custom_response.get_message("mod.mute.notify", self._guild, mute=self)

		try:
			if isinstance(message, dict):
				await self._user.send(**message)
		except discord.Forbidden:
			pass

	async def before_deletion(self) -> None:
		"""Unmutes the user."""
		as_member: discord.Member | None = self._guild.get_member(self._user.id)  # type: ignore
		if not as_member or not as_member.timed_out_until:
			return

		await as_member.edit(timed_out_until=None, reason=self.reason)

	async def after_deletion(self) -> None:
		"""Notifies the user about the unmute."""
		self._custom_response = custom_response.CustomResponse(MyClient, "mod")
		message = await self._custom_response.get_message("mod.unmute.notify", self._guild, mute=self)

		try:
			if isinstance(message, dict):
				await self._user.send(**message)
		except discord.Forbidden:
			pass


class Ban(Case):
	def __init__(
		self,
		_id: int,
		guild: discord.Guild,
		user: discord.Member | discord.User,
		moderator: discord.User,
		reason: str | None = None,
		expires: datetime.datetime | None = None,
		message: str | None = None,
		created: datetime.datetime = datetime.datetime.now(),
	):
		super().__init__(CaseType.BAN, _id, guild, user, moderator, created, reason, expires, message)

	async def before_creation(self) -> None:
		"""Notifies the user about the ban."""
		self._custom_response = custom_response.CustomResponse(MyClient, "mod")
		message = await self._custom_response.get_message("mod.ban.notify", self._guild, ban=self)

		try:
			if isinstance(message, dict):
				await self._user.send(**message)
		except discord.Forbidden:
			pass

	async def after_creation(self) -> None:
		"""Bans the user."""
		await self._guild.ban(self._user, reason=f"Banned by {self._moderator}", delete_message_days=0)

	async def before_deletion(self) -> None:
		"""Unbans the user."""
		try:
			await self._guild.unban(self._user, reason="Ban removed")
		except discord.NotFound:
			pass

	async def after_deletion(self) -> None:
		"""Notifies the user about the unban."""
		if self._guild.get_member(self._user.id):  # to avoid spamming non-members
			self._custom_response = custom_response.CustomResponse(MyClient, "mod")
			message = await self._custom_response.get_message("mod.unban.notify", self._guild, ban=self)

			try:
				if isinstance(message, dict):
					await self._user.send(**message)
			except discord.Forbidden:
				pass


@commands.guild_only()
@app_commands.guild_only()
class Moderation(commands.GroupCog, name="Moderation", group_name="mod"):
	def __init__(self, client: MyClient) -> None:
		self.client = client
		self.custom_response = custom_response.CustomResponse(client, "mod")

	async def case_removal(self):
		await self.client.wait_until_ready()

		case_rows = await self.client.db.fetch(
			"SELECT * FROM cases WHERE expires IS NOT NULL AND expires <= $1",
			datetime.datetime.now(),
		)
		for row in case_rows:
			case = Case.from_dict(row, self.client, get_type=True)

			if not case._guild:
				continue

			if not case._guild.chunked:
				await case._guild.chunk()

			match case.type:
				case CaseType.WARN:
					case = Warn.from_dict(row, self.client)
				case CaseType.MUTE:
					case = Mute.from_dict(row, self.client)
				case CaseType.KICK:
					case = Kick.from_dict(row, self.client)
				case CaseType.BAN:
					case = Ban.from_dict(row, self.client)
			await case.delete(self.client.db)

	async def cog_load(self):
		self.client.loop.create_task(self.case_removal())

	@commands.hybrid_command(name="warn", description="warn_specs-description", usage="warn_specs-usage")
	@app_commands.rename(
		user="warn_specs-args-member-name",
		expires="warn_specs-args-duration-name",
		reason="warn_specs-args-reason-name",
	)
	@app_commands.describe(
		user="warn_specs-args-member-description",
		expires="warn_specs-args-duration-description",
		reason="warn_specs-args-reason-description",
	)
	@app_commands.checks.has_permissions(moderate_members=True)
	@commands.has_permissions(moderate_members=True)
	async def warn(
		self,
		ctx: main.Context,
		user: discord.Member,
		expires: str = None,
		*,
		reason: str = None,
	):
		try:
			user = await commands.MemberConverter().convert(
				ctx, str(user.name) if isinstance(user, discord.Member) else user
			)
		except commands.MemberNotFound:
			if not ctx.message.reference:
				reason = " ".join([user, expires, reason] if reason else [user, expires])
			else:
				raise commands.MemberNotFound(str(user))
		try:
			expires = (
				datetime.datetime.now() + datetime.timedelta(seconds=text_to_seconds(expires)) if expires else None
			)
		except (ValueError, TypeError):
			reason = " ".join([expires, reason] if reason else [expires])
			expires = None

		if user == ctx.me:
			return await ctx.send("mod.warn.errors.bot")

		if user.top_role >= ctx.author.top_role:
			return await ctx.send("mod.warn.errors.hierarchy")

		warn = Warn(
			Case.generate_id(ctx.message),
			ctx.guild,
			user,
			ctx.author,
			reason,
			expires,
			ctx.message.reference.resolved.content if ctx.message.reference else None,
		)
		await warn.create(self.client.db)

		await ctx.send("mod.warn.response", warn=warn)

	@commands.bot_has_permissions(moderate_members=True)
	@app_commands.checks.bot_has_permissions(moderate_members=True)
	@commands.hybrid_command(name="mute", description="mute_specs-description", usage="mute_specs-usage")
	@app_commands.rename(
		user="mute_specs-args-user-name",
		expires="mute_specs-args-expires-name",
		reason="mute_specs-args-reason-name",
	)
	@app_commands.describe(
		user="mute_specs-args-user-description",
		expires="mute_specs-args-expires-description",
		reason="mute_specs-args-reason-description",
	)
	@app_commands.checks.has_permissions(moderate_members=True)
	@commands.has_permissions(moderate_members=True)
	async def mute(
		self,
		ctx: main.Context,
		user: discord.Member,
		expires: str,
		*,
		reason: str = None,
	):
		try:
			expires = datetime.datetime.now() + datetime.timedelta(seconds=text_to_seconds(expires))
		except (ValueError, TypeError):
			raise commands.BadArgument
		if user == ctx.me:
			return await ctx.send("mod.mute.errors.bot")
		mute = Mute(
			Case.generate_id(ctx.message),
			ctx.guild,
			user,
			ctx.author,
			expires,
			reason,
			ctx.message.reference.resolved.content if ctx.message.reference else None,
		)
		await mute.create(self.client.db)

		await ctx.send("mod.mute.response", mute=mute)

	@commands.bot_has_permissions(moderate_members=True)
	@app_commands.checks.bot_has_permissions(moderate_members=True)
	@commands.hybrid_command(
		name="unmute",
		description="unmute_specs-description",
		usage="unmute_specs-usage",
	)
	@app_commands.rename(user="unmute_specs-args-user-name")
	@app_commands.describe(user="unmute_specs-args-user-description")
	@app_commands.checks.has_permissions(moderate_members=True)
	@commands.has_permissions(moderate_members=True)
	async def unmute(self, ctx: main.Context, user: discord.Member):
		if user.timed_out_until:
			cases = await Mute.from_db(
				self.client.db,
				self.client,
				ctx.guild,
				user=user,
				expires=user.timed_out_until.astimezone(datetime.timezone.utc).replace(tzinfo=None),
			)
			if cases:
				for case in cases:
					await case.delete(self.client.db)
			else:
				await user.edit(timed_out_until=None)
		await user.edit(timed_out_until=None)

		await ctx.send("mod.unmute.response", user=CustomMember.from_member(user))

	@commands.bot_has_permissions(kick_members=True)
	@app_commands.checks.bot_has_permissions(kick_members=True)
	@commands.hybrid_command(name="kick", description="kick_specs-description", usage="kick_specs-usage")
	@app_commands.rename(user="kick_specs-args-user-name", reason="kick_specs-args-reason-name")
	@app_commands.describe(
		user="kick_specs-args-user-description",
		reason="kick_specs-args-reason-description",
	)
	@app_commands.checks.has_permissions(kick_members=True)
	@commands.has_permissions(kick_members=True)
	async def kick(self, ctx: main.Context, user: discord.Member, *, reason: str = None):
		if user == ctx.me:
			return await ctx.send("mod.kick.errors.bot")
		kick = Kick(
			Case.generate_id(ctx.message),
			ctx.guild,
			user,
			ctx.author,
			reason,
			ctx.message.reference.resolved.content if ctx.message.reference else None,
		)
		await kick.create(self.client.db)

		await ctx.send("mod.kick.response", kick=kick)

	@commands.bot_has_permissions(ban_members=True)
	@app_commands.checks.bot_has_permissions(ban_members=True)
	@commands.hybrid_command(name="ban", description="ban_specs-description", usage="ban_specs-usage")
	@app_commands.rename(
		user="ban_specs-args-user-name",
		reason="ban_specs-args-reason-name",
		expires="ban_specs-args-expires-name",
	)
	@app_commands.describe(
		user="ban_specs-args-user-description",
		reason="ban_specs-args-reason-description",
		expires="ban_specs-args-expires-description",
	)
	@app_commands.checks.has_permissions(ban_members=True)
	@commands.has_permissions(ban_members=True)
	async def ban(
		self,
		ctx: main.Context,
		user: discord.User,
		expires: str = None,
		*,
		reason: str = None,
	):
		try:
			expires = (
				datetime.datetime.now() + datetime.timedelta(seconds=text_to_seconds(expires)) if expires else None
			)
		except (ValueError, TypeError):
			raise commands.BadArgument
		if user == ctx.me:
			return await ctx.send("mod.ban.errors.bot")
		ban = Ban(
			Case.generate_id(ctx.message),
			ctx.guild,
			user,
			ctx.author,
			reason,
			expires,
			ctx.message.reference.resolved.content if ctx.message.reference else None,
		)
		await ban.create(self.client.db)

		await ctx.send("mod.ban.response", ban=ban)

	@commands.bot_has_permissions(ban_members=True)
	@app_commands.checks.bot_has_permissions(ban_members=True)
	@commands.hybrid_command(name="unban", description="unban_specs-description", usage="unban_specs-usage")
	@app_commands.rename(user="unban_specs-args-user-name")
	@app_commands.describe(user="unban_specs-args-user-description")
	@app_commands.checks.has_permissions(ban_members=True)
	@commands.has_permissions(ban_members=True)
	async def unban(self, ctx: main.Context, user: discord.User):
		cases = await Ban.from_db(self.client.db, self.client, ctx.guild, user=user)
		if cases:
			for case in cases:
				case._custom_response = self.custom_response
				await case.delete(self.client.db)
		else:
			try:
				await ctx.guild.unban(user, reason=f"Ban removed by {ctx.author}")
			except discord.NotFound:
				pass

		await ctx.send("mod.unban.response", user=CustomUser.from_user(user))

	@commands.bot_has_permissions(manage_channels=True)
	@app_commands.checks.bot_has_permissions(manage_channels=True)
	@commands.has_permissions(manage_channels=True)
	@app_commands.checks.has_permissions(manage_channels=True)
	@commands.hybrid_command(name="slowmode", description="sm_specs-description", usage="sm_specs-usage")
	async def slowmode(self, ctx: main.Context, seconds: str, channel: discord.TextChannel = None):
		channel = channel or ctx.channel
		max_slowmode_delay = 60 * 60 * 6  # 6 hours
		slowmode_before = channel.slowmode_delay
		try:
			seconds = text_to_seconds(seconds, channel.slowmode_delay)
		except ValueError:
			raise commands.BadArgument
		seconds = max(0, min(seconds, max_slowmode_delay))
		reason = await self.custom_response("mod.slowmode.reason", ctx, moderator=CustomMember.from_member(ctx.author))
		await ctx.channel.edit(slowmode_delay=seconds, reason=reason)
		await ctx.send(
			"mod.slowmode.response",
			channel=CustomTextChannel.from_channel(channel),
			time_before=seconds_to_text(slowmode_before),
			time=seconds_to_text(seconds),
		)


@commands.guild_only()
@app_commands.guild_only()
class Cases(commands.Cog, name="Cases"):
	def __init__(self, client: MyClient) -> None:
		self.client = client
		self.custom_response = custom_response.CustomResponse(client, "mod")

	@commands.hybrid_group(
		name="case",
		description="caseinfo_specs-description",
		usage="caseinfo_specs-usage",
		fallback="caseinfo_specs-fallback",
	)
	@app_commands.rename(case_id="caseinfo_specs-args-case_id-name")
	@app_commands.describe(case_id="caseinfo_specs-args-case_id-description")
	async def case(self, ctx: main.Context, case_id: str):
		try:
			case_id = int(case_id)
		except ValueError:
			raise commands.BadArgument

		case = await Case.from_id(self.client.db, self.client, ctx.guild, case_id, get_type=True)
		if not case:
			return await ctx.send("mod.info.errors.not_found", case_id=case_id)

		# since we need the case's information but we don't want to duplicate db calls,
		# we check inside the actual command
		if case._user.id != ctx.author.id and not ctx.author.guild_permissions.moderate_members:  # type: ignore
			raise commands.MissingPermissions(["moderate_members"])

		await ctx.send("mod.info.response", case=case)

	@commands.bot_has_permissions(moderate_members=True, ban_members=True)
	@app_commands.checks.bot_has_permissions(moderate_members=True, ban_members=True)
	@case.command(
		name="delete",
		description="casedel_specs-description",
		usage="casedel_specs-usage",
		aliases=["del", "remove"],
	)
	@app_commands.describe(case_id="casedel_specs-args-case_id-description")
	@app_commands.rename(case_id="casedel_specs-args-case_id-name")
	@app_commands.checks.has_permissions(moderate_members=True)
	@commands.has_permissions(moderate_members=True)
	async def delete(self, ctx: main.Context, case_id: str):
		try:
			case_id = int(case_id)
		except ValueError:
			raise commands.BadArgument
		case = await Case.from_id(self.client.db, self.client, ctx.guild, case_id, get_type=True)
		if not case:
			return await ctx.send("mod.delete.errors.not_found", case_id=case_id)

		match case.type:  # type: ignore
			case CaseType.WARN:
				case = await Warn.from_id(self.client.db, self.client, ctx.guild, case_id)
			case CaseType.MUTE:
				case = await Mute.from_id(self.client.db, self.client, ctx.guild, case_id)
			case CaseType.KICK:
				case = await Kick.from_id(self.client.db, self.client, ctx.guild, case_id)
			case CaseType.BAN:
				case = await Ban.from_id(self.client.db, self.client, ctx.guild, case_id)
		case._custom_response = self.custom_response
		await case.delete(self.client.db)  # type: ignore

		await ctx.send("mod.delete.response", case=case)

	@commands.bot_has_permissions(moderate_members=True, ban_members=True)
	@app_commands.checks.bot_has_permissions(moderate_members=True, ban_members=True)
	@case.command(
		name="edit",
		description="caseedit_specs-description",
		usage="caseedit_specs-usage",
	)
	@app_commands.rename(
		case_id="caseedit_specs-args-case_id-name",
		value="caseedit_specs-args-value-name",
		new_value="caseedit_specs-args-nvalue-name",
	)
	@app_commands.describe(
		case_id="caseedit_specs-args-case_id-description",
		value="caseedit_specs-args-value-description",
		new_value="caseedit_specs-args-nvalue-description",
	)
	@app_commands.choices(
		value=[
			app_commands.Choice(name="caseedit_specs-args-value-expires", value="expires"),
			app_commands.Choice(name="caseedit_specs-args-value-reason", value="reason"),
			app_commands.Choice(name="caseedit_specs-args-value-message", value="message"),
		]
	)
	@app_commands.checks.has_permissions(moderate_members=True)
	@commands.has_permissions(moderate_members=True)
	async def edit(
		self,
		ctx: main.Context,
		case_id: str,
		value: Literal["expires", "reason", "message"],
		*,
		new_value: str,
	):
		try:
			case_id = int(case_id)
		except ValueError:
			raise commands.BadArgument
		case: Case = await Case.from_id(self.client.db, self.client, ctx.guild, case_id, get_type=True)
		if case is None:
			return await ctx.send("mod.edit.errors.not_found", case_id=case_id)

		if value == "expires":
			try:
				new_value = datetime.datetime.now() + datetime.timedelta(seconds=text_to_seconds(new_value))
			except (ValueError, TypeError):
				return await ctx.send("mod.edit.errors.invalid_time", case_id=case_id)

		new_case = case.copy()
		setattr(new_case, value, new_value)
		await case.edit(self.client.db, new_case)

		await ctx.send("mod.edit.response", case=case)

	@case.command(
		name="list",
		description="caselist_specs-description",
		usage="caselist_specs-usage",
	)
	@app_commands.describe(user="caselist_specs-args-user-description")
	@app_commands.rename(user="caselist_specs-args-user-name")
	async def list(self, ctx: main.Context, user: discord.Member = None):
		user = user or ctx.author

		cases = await Case.from_user(self.client.db, user, self.client, ctx.guild, 10)

		# since we need the case's information but we don't want to duplicate db calls,
		# we check inside the actual command
		if user.id != ctx.author.id and not ctx.author.guild_permissions.moderate_members:
			raise commands.MissingPermissions(["moderate_members"])

		message: dict | str | list | int | float = await self.custom_response.get_message(
			"mod.list.response", ctx, cases=cases
		)
		if not isinstance(message, dict):
			return await ctx.send(content=message)

		embeds: list[discord.Embed] = message.get("embeds")
		if not cases:
			if embeds:
				embeds[0].remove_field(0)
			return await ctx.send(**message)

		if embeds:
			template = embeds[0].to_dict().get("fields", [None])[0]
			if not template:
				return await ctx.send(**message)
			embeds[0].clear_fields()
			for case in cases:
				formatted = discord.ext.localization.Localization.format_strings(template, case=case)
				embeds[0].add_field(**formatted)

		await ctx.send(**message)


async def setup(client: MyClient):
	await client.add_cog(Moderation(client))
	await client.add_cog(Cases(client))
