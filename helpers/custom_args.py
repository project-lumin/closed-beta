"""Custom arguments to make user-specified responses easier to configure"""
import datetime
from dataclasses import dataclass, field
from typing import Union, Optional, Literal, Sequence
from cpuinfo import get_cpu_info
from emoji import demojize
import discord
import psutil

class CustomColor:
	"""Custom colors for formatting purposes.

	Operations
	----------
	`str(x)`: Returns the color in hex format.

	Examples
	--------
	>>> color = CustomColor(discord.Color.red())
	>>> color
	#FF0000

	>>> color.image  # type: ignore
	'https://dummyimage.com/500x500/FF0000/000000&text=+'
	"""

	def __init__(self, color: Optional[discord.Color]):
		self.__color = color or discord.Color.light_grey()

	def __str__(self):
		return f'#{self.__color.value:0>6X}'  # '#RRGGBB' - '#AB12CD'

	@property
	def color(self) -> str:
		"""The color in hex format."""
		return str(self)

	colour = color

	@property
	def rgb(self) -> str:
		"""The color in RGB format."""
		colors = self.__color.to_rgb()
		return f"({colors[0]}, {colors[1]}, {colors[2]})"

	@property
	def image(self):
		return f'https://dummyimage.com/500x500/{self.__color.value:0>6X}/000000&text=+'

	pic = picture = image

	__repr__ = __str__

DatetimeFormat = Literal["time", "seconds", "date", "month", "short", "long", "relative", discord.utils.TimestampStyle]
"""The format to use for Discord timestamps."""

class Formattable:
	def __init__(self, data, *, style: discord.utils.TimestampStyle):
		"""A class that allows you to format a datetime object into a Discord timestamp.

		Parameters
		----------
		data: `FormatDateTime`
			The datetime object to format.
		"""
		self._parent_data = data
		self._style = style

	@property
	def value(self) -> str:
		return discord.utils.format_dt(self._parent_data.data, style=self._style)

	def __repr__(self):
		return self.value

	__str__ = __repr__

class FormatDateTime:
	"""Formats a datetime object into a dynamic Discord timestamp.

	You have to specify a default style, which will be used if no style is provided by the end user.
	This is needed because by passing this class as a value for a property, users can call it with or without brackets.
	So for example, ``created_at``, ``created_at()`` and ``created_at("long")`` will all work. The one without the
	brackets will always use the default style."""

	def __init__(self, data: datetime.datetime, default_style: discord.utils.TimestampStyle):
		self.data = data
		self.default_style = default_style

	@property
	def timestamp(self) -> str:
		return self.data.astimezone(datetime.timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

	@property
	def time(self) -> Formattable:
		"""Returns the hours and minutes of the timestamp.

		Examples
		--------
		>>> FormatDateTime(datetime.datetime.now(), "F").time
		22:57
		"""
		return Formattable(self, style="f")

	@property
	def seconds(self) -> Formattable:
		"""Returns the seconds of the timestamp.

		Examples
		--------
		>>> FormatDateTime(datetime.datetime.now(), "F").seconds
		22:57:43
		"""
		return Formattable(self, style="f")

	@property
	def date(self) -> Formattable:
		"""Returns the date of the timestamp.

		Examples
		--------
		>>> FormatDateTime(datetime.datetime.now(), "F").date
		2022-02-17
		"""
		return Formattable(self, style="D")

	@property
	def short(self) -> Formattable:
		"""Returns the short version of the timestamp.

		Examples
		--------
		>>> FormatDateTime(datetime.datetime.now(), "F").short
		17 Feb 2022
		"""
		return Formattable(self, style="f")

	@property
	def long(self) -> Formattable:
		"""Returns the long version of the timestamp.

		Examples
		--------
		>>> FormatDateTime(datetime.datetime.now(), "F").long
		Thursday, 17 February 2022
		"""
		return Formattable(self, style="F")

	@property
	def relative(self) -> Formattable:
		"""Returns the relative version of the timestamp.

		Examples
		--------
		>>> FormatDateTime(datetime.datetime.now(), "F").relative
		1 minute ago
		"""
		return Formattable(self, style="R")

	def __repr__(self) -> str:
		return Formattable(self, style=self.default_style).value

if __name__ == "__main__":
	pass

@dataclass
class CustomUser:
	_name: str = field(repr=False)
	id: int
	"""Returns the user's ID."""
	_discriminator: str = field(repr=False)
	global_name: str = field(repr=False)
	"""Returns the user's global display name. The hierarchy is as follows:
	
	1. ``name#discriminator`` if the user has a discriminator (only bots).
	2. ``global_name`` if the user has a global name.
	3. ``name`` if the user has neither a discriminator nor a global name."""
	display_name: str = field(repr=False)
	"""Returns the user's display name. This is the name that is shown in the server if they are a member.
	Otherwise, it is the same as ``global_name``."""
	bot: bool
	"""Returns whether or not the user is a Discord bot."""
	_color: Optional[CustomColor] = field(repr=False)
	_avatar: str = field(repr=False)
	_decoration: Optional[str] = field(repr=False)
	_banner: Optional[str] = field(repr=False)
	_created_at: datetime.datetime = field(repr=False)
	mention: str
	"""Returns a string that mentions the user."""

	@classmethod
	def from_user(cls, user: discord.User):
		"""Creates a ``CustomUser`` from a ``discord.User`` object."""
		return cls(
			_name=f"{user.name}#{user.discriminator}" if user.discriminator != "0" else user.name, id=user.id,
			_discriminator=user.discriminator if user.discriminator != "0" else None,
			global_name=user.global_name,
			display_name=user.display_name, bot=user.bot, _color=CustomColor(user.accent_color),
			_avatar=user.display_avatar.url, _decoration=user.avatar_decoration.url if user.avatar_decoration else "",
			_banner=user.banner.url if user.banner else CustomColor(user.accent_color).image,
			_created_at=user.created_at, mention=user.mention
		)

	@property
	def name(self) -> str:
		"""Returns the username of the user."""
		return self._name

	user_name = user = username = name

	@property
	def discriminator(self) -> str:
		"""Returns the discriminator of the user. This is a legacy concept that only applies to bots."""
		return self._discriminator

	tag = discriminator

	@property
	def color(self) -> CustomColor:
		"""Returns the user's accent color."""
		return self._color

	colour = color

	@property
	def avatar(self) -> str:
		"""Returns the user's avatar URL."""
		return self._avatar

	icon = avatar

	@property
	def created_at(self):
		"""Returns the date the user was created as a Discord timestamp. You can call this with or without brackets.
		If you call it with braces you can pass a ``DatetimeFormat`` to format the timestamp."""
		return FormatDateTime(self._created_at, "F")

	created = created_at

	def __str__(self):
		return self.global_name

	def __int__(self):
		return self.id

@dataclass
class CustomMember(CustomUser):
	_nickname: Optional[str] = field(repr=False)
	_color: Optional[CustomColor] = field(repr=False)
	_accent_color: Optional[CustomColor] = field(repr=False)
	_joined_at: datetime.datetime = field(repr=False)
	_roles: list[discord.Role] = field(repr=False)

	@classmethod
	def from_member(cls, member: discord.Member):
		return cls(
			_name=f"{member.name}#{member.discriminator}" if member.discriminator != "0" else member.name, id=member.id,
			_discriminator=member.discriminator if member.discriminator != "0" else None, global_name=member.global_name, display_name=member.display_name,
			_nickname=member.nick, bot=member.bot, _color=CustomColor(member.color),
			_accent_color=CustomColor(member.accent_color), _avatar=member.display_avatar.url,
			_decoration=member.avatar_decoration.url if member.avatar_decoration else None,
			_banner=member.avatar_decoration.url if member.banner else None, _created_at=member.created_at,
			_joined_at=member.joined_at, _roles=member.roles, mention=member.mention
		)

	@property
	def nickname(self) -> str:
		"""Returns the nickname of the member."""
		return self._nickname

	nick = nickname

	@property
	def color(self) -> CustomColor:
		"""Returns the member's chat display color, aka. the color of their top role."""
		return self._color

	@property
	def joined_at(self):
		"""Returns the date the member joined the server as a Discord timestamp. You can call this with or without
		brackets. If you call it with braces you can pass a ``DatetimeFormat`` to format the timestamp."""
		return FormatDateTime(self._joined_at, "F")

	joined = joined_at

	@property
	def roles(self) -> Optional[str]:
		"""Returns the roles the user has (excluding @everyone)"""
		self._roles.pop(0)
		roles_string = ', '.join([role.mention for role in self._roles])
		if len(roles_string) > 512:
			return None
		return roles_string

	@property
	def roles_reverse(self) -> Optional[str]:
		self._roles.pop(0)
		roles_string = ', '.join([role.mention for role in reversed(self._roles)])
		if len(roles_string) > 512:
			return None
		return roles_string

	def __str__(self):
		return self.display_name or self.name

@dataclass
class CustomRole:
	name: str
	"""Returns the role's name."""
	id: int
	"""Returns the role's ID."""
	hoist: bool
	"""Returns whether or not the role is hoisted (aka. shown seperately from other members)."""
	position: int
	"""Returns the role's position in the hierarchy."""
	managed: bool
	"""Returns whether or not the role is managed by an integration, such as Twitch or Patreon."""
	mentionable: bool
	"""Returns whether or not the role is mentionable by everyone."""
	_default: bool = field(repr=False)
	_bot: bool = field(repr=False)
	_boost: bool = field(repr=False)
	_integration: bool = field(repr=False)
	_assignable: bool = field(repr=False)
	_color: Optional[CustomColor] = field(repr=False)
	icon: str = field(repr=False)
	"""Returns the role's icon URL, or an emoji, if the role has one. This is only available for guilds that are
	boosted to at least level 2."""
	_created_at: datetime.datetime = field(repr=False)
	mention: str
	"""Returns a string that mentions the role."""
	_members: list[discord.Member] = field(repr=False)
	_purchaseable: bool = field(repr=False)
	_permissions: discord.Permissions = field(repr=False)

	@classmethod
	def from_role(cls, role: discord.Role):
		return cls(
			name=role.name, id=role.id, hoist=role.hoist, position=role.position, managed=role.managed,
			mentionable=role.mentionable, _default=role.is_default(), _bot=role.is_bot_managed(),
			_boost=role.is_premium_subscriber(), _integration=role.is_integration(), _assignable=role.is_assignable(),
			_color=CustomColor(role.color),
			icon=role.display_icon.url or role.display_icon if role.display_icon else None, _created_at=role.created_at,
			mention=role.mention, _members=role.members,
			_purchaseable=role.tags.is_available_for_purchase() if role.tags else False, _permissions=role.permissions
		)

	@property
	def members(self) -> int:
		return len(self._members)

	@property
	def everyone(self) -> bool:
		"""Returns whether or not the role is the everyone role."""
		return self._default

	default = is_default = everyone

	@property
	def bot(self) -> bool:
		"""Returns whether or not the role is managed by a bot."""
		return self._bot

	is_bot = is_bot_managed = bot

	@property
	def boost(self) -> bool:
		"""Returns whether or not the role is a boost role."""
		return self._boost

	is_boost = is_premium_subscriber = boost

	@property
	def integration(self) -> bool:
		"""Returns whether or not the role is managed by an integration."""
		return self._integration

	is_integration_managed = integration_managed = is_integration = integration

	@property
	def assignable(self) -> bool:
		"""Returns whether or not the role is assignable by the bot itself."""
		return self._assignable

	allowed = is_assignable = assignable

	@property
	def purchaseable(self) -> bool:
		"""Returns whether or not the role is purchaseable."""
		return self._purchaseable

	buy = buyable = is_buyable = purchase = is_purchaseable = purchaseable

	@property
	def color(self) -> CustomColor:
		"""Returns the role's color."""
		return CustomColor(self._color)

	colour = color

	@property
	def created_at(self):
		"""Returns the date the role was created as a Discord timestamp. You can call this with or without brackets.
		If you call it with braces you can pass a ``DatetimeFormat`` to format the timestamp."""
		return FormatDateTime(self._created_at, "F")

	created = created_at

	@property
	def permissions(self):
		"""Returns the role's permissions."""
		return ", ".join([str(perm[0]).upper() for perm in self._permissions if perm[1]])[:1024]

	def __str__(self):
		return self.name

	def __int__(self):
		return self.id

	# TODO: we need to add permissions somehow... no idea how, though

@dataclass
class CustomGuild:
	name: str
	"""Returns the guild's name."""
	id: int
	"""Returns the guild's ID."""
	_icon: Optional[discord.Asset] = field(repr=False)
	_banner: Optional[discord.Asset] = field(repr=False)
	_splash: Optional[discord.Asset] = field(repr=False)
	_discovery_splash: Optional[discord.Asset] = field(repr=False)
	description: Optional[str] = field(repr=False)
	"""Returns the guild's description, if it has one."""
	members: Optional[int] = field(repr=False)
	"""Returns the number of members in the guild."""
	_owner: discord.Member = field(repr=False)
	boosts: int = field(repr=False)
	"""Returns how many boosts the guild has."""
	_created_at: datetime.datetime = field(repr=False)
	_verification_level: discord.VerificationLevel = field(repr=False)
	_default_notifications: discord.NotificationLevel = field(repr=False)
	_explicit_content_filter: discord.ContentFilter = field(repr=False)
	_mfa_level: discord.MFALevel = field(repr=False)
	_system_channel: Optional[discord.TextChannel] = field(repr=False)
	_rules_channel: Optional[discord.TextChannel] = field(repr=False)
	_public_updates_channel: Optional[discord.TextChannel] = field(repr=False)
	_preferred_locale: discord.Locale = field(repr=False)
	_afk_channel: Optional[Union[discord.VoiceChannel, discord.StageChannel]] = field(repr=False)
	"""Returns the guild's AFK channel."""
	_afk_timeout: int = field(repr=False)
	"""Returns the guild's AFK timeout."""
	_vanity_url: Optional[str] = field(repr=False)
	_premium_tier: int = field(repr=False)
	_premium_subscribers: list[discord.Member] = field(repr=False)
	_premium_subscriber_role: Optional[discord.Role] = field(repr=False)
	_nsfw_level: discord.NSFWLevel = field(repr=False)
	_channels: Sequence[discord.abc.GuildChannel] = field(repr=False)
	_voice_channels: list[discord.VoiceChannel] = field(repr=False)
	_stage_channels: list[discord.StageChannel] = field(repr=False)
	_text_channels: list[discord.TextChannel] = field(repr=False)
	_categories: list[discord.CategoryChannel] = field(repr=False)
	_forums: list[discord.ForumChannel] = field(repr=False)
	_threads: Sequence[discord.Thread] = field(repr=False)
	_roles: Sequence[discord.Role] = field(repr=False)
	_emojis: tuple[discord.Emoji, ...] = field(repr=False)
	emoji_limit: int = field(repr=False)
	"""Returns the max amount of emojis the guild can have."""
	_stickers: tuple[discord.GuildSticker, ...] = field(repr=False)
	_sticker_limit: int = field(repr=False)
	_bitrate_limit: float = field(repr=False)
	_filesize_limit: int = field(repr=False)
	_scheduled_events: Sequence[discord.ScheduledEvent] = field(repr=False)
	_shard_id: int = field(repr=False)

	@classmethod
	def from_guild(cls, guild: discord.Guild):
		return cls(
			name=guild.name, id=guild.id, _icon=guild.icon, _banner=guild.banner, _splash=guild.splash,
			_discovery_splash=guild.discovery_splash, description=guild.description, members=guild.member_count,
			_owner=guild.owner, boosts=guild.premium_subscription_count, _created_at=guild.created_at,
			_verification_level=guild.verification_level, _default_notifications=guild.default_notifications,
			_explicit_content_filter=guild.explicit_content_filter, _mfa_level=guild.mfa_level,
			_system_channel=guild.system_channel, _rules_channel=guild.rules_channel,
			_public_updates_channel=guild.public_updates_channel, _preferred_locale=guild.preferred_locale,
			_afk_channel=guild.afk_channel, _afk_timeout=guild.afk_timeout, _vanity_url=guild.vanity_url,
			_premium_tier=guild.premium_tier, _premium_subscribers=guild.premium_subscribers,
			_premium_subscriber_role=guild.premium_subscriber_role, _nsfw_level=guild.nsfw_level,
			_channels=guild.channels, _voice_channels=guild.voice_channels, _stage_channels=guild.stage_channels,
			_text_channels=guild.text_channels, _categories=guild.categories, _forums=guild.forums,
			_threads=guild.threads, _roles=guild.roles, _emojis=guild.emojis, emoji_limit=guild.emoji_limit,
			_stickers=guild.stickers, _sticker_limit=guild.sticker_limit, _bitrate_limit=guild.bitrate_limit,
			_filesize_limit=guild.filesize_limit, _scheduled_events=guild.scheduled_events, _shard_id=guild.shard_id
		)

	@property
	def owner(self) -> CustomMember:
		return CustomMember.from_member(self._owner)

	@property
	def icon(self) -> Optional[str]:
		"""Returns the guild's icon URL."""
		return self._icon.url if self._icon else ""

	@property
	def banner(self) -> Optional[str]:
		"""Returns the guild's banner URL."""
		return self._banner.url if self._banner else ""

	@property
	def splash(self) -> Optional[str]:
		"""Returns the guild's splash URL."""
		return self._splash.url if self._splash else ""

	@property
	def discovery_splash(self) -> Optional[str]:
		"""Returns the guild's discovery splash URL."""
		return self._discovery_splash.url if self._discovery_splash else ""

	@property
	def created_at(self):
		"""Returns the date the guild was created as a Discord timestamp. You can call this with or without brackets.
		If you call it with braces you can pass a ``DatetimeFormat`` to format the timestamp."""
		return FormatDateTime(self._created_at, "F")

	created = created_at

	@property
	def verification_level(self) -> str:
		"""Returns the guild's verification level."""
		mapping = { discord.VerificationLevel.none: r"{verification.none}",
			discord.VerificationLevel.low: r"{verification.low}",
			discord.VerificationLevel.medium: r"{verification.medium}",
			discord.VerificationLevel.high: r"{verification.high}",
			discord.VerificationLevel.highest: r"{verification.highest}" }
		return mapping.get(mapping)

	@property
	def default_notifications(self) -> str:
		"""Returns the guild's default notification level."""
		mapping = { discord.NotificationLevel.all_messages: r"{notification.all_messages}",
			discord.NotificationLevel.only_mentions: r"{notification.only_mentions}" }
		return mapping.get(mapping)

	@property
	def explicit_content_filter(self) -> str:
		"""Returns the guild's explicit content filter level."""
		mapping = { discord.ContentFilter.disabled: r"{content_filter.disabled}",
			discord.ContentFilter.no_role: r"{content_filter.no_role}",
			discord.ContentFilter.all_members: r"{content_filter.all_members}" }
		return mapping.get(mapping)

	@property
	def mfa_level(self) -> str:
		"""Returns the guild's MFA level."""
		mapping = { discord.MFALevel.disabled: r"{mfa.disabled}", discord.MFALevel.require_2fa: r"{mfa.require_2fa}", }
		return mapping.get(mapping)

	@property
	def system_channel(self) -> str:
		"""Returns the guild's system channel."""
		return self._system_channel.mention

	@property
	def rules_channel(self) -> str:
		"""Returns the guild's rules channel."""
		return self._rules_channel.mention

	@property
	def public_updates_channel(self) -> str:
		"""Returns the guild's public updates channel."""
		return self._public_updates_channel.mention

	@property
	def preferred_locale(self) -> str:
		"""Returns the guild's preferred locale."""
		return str(self._preferred_locale)

	locale = language = preferred_locale

	@property
	def afk_channel(self) -> str:
		"""Returns the guild's AFK channel."""
		return self._afk_channel.mention

	@property
	def vanity_url(self) -> str:
		"""Returns the guild's vanity URL."""
		return self._vanity_url

	@property
	def premium_tier(self) -> int:
		"""Returns the guild's premium tier."""
		return self._premium_tier

	boost_tier = premium_tier

	@property
	def premium_subscribers(self) -> int:
		"""Returns the guild's premium subscribers."""
		return len(self._premium_subscribers)

	boosters = premium_subscribers

	@property
	def premium_subscriber_role(self) -> str:
		"""Returns the guild's premium subscriber role."""
		return self._premium_subscriber_role.mention if self._premium_subscriber_role else None

	boost_role = premium_subscriber_role

	@property
	def nsfw_level(self) -> str:
		"""Returns the guild's NSFW level."""
		mapping = { discord.NSFWLevel.default: r"{nsfw.default}", discord.NSFWLevel.explicit: r"{nsfw.explicit}",
			discord.NSFWLevel.safe: r"{nsfw.safe}", discord.NSFWLevel.age_restricted: r"{nsfw.age_restricted}" }
		return mapping.get(mapping)

	@property
	def channels(self) -> int:
		"""Returns the number of channels in the guild."""
		return len(self._channels)

	@property
	def voice_channels(self) -> int:
		"""Returns the number of voice channels in the guild."""
		return len(self._voice_channels)

	@property
	def stage_channels(self) -> int:
		"""Returns the number of stage channels in the guild."""
		return len(self._stage_channels)

	@property
	def text_channels(self) -> int:
		"""Returns the number of text channels in the guild."""
		return len(self._text_channels)

	@property
	def categories(self) -> int:
		"""Returns the number of categories in the guild."""
		return len(self._categories)

	@property
	def forums(self) -> int:
		"""Returns the number of forums in the guild."""
		return len(self._forums)

	@property
	def threads(self) -> int:
		"""Returns the number of threads in the guild."""
		return len(self._threads)

	@property
	def roles(self) -> int:
		"""Returns the number of roles in the guild."""
		return len(self._roles)

	@property
	def emojis(self) -> int:
		"""Returns the number of emojis in the guild."""
		return len(self._emojis)

	@property
	def stickers(self) -> int:
		"""Returns the number of stickers in the guild."""
		return len(self._stickers)

	@property
	def bitrate_limit(self) -> int:
		"""Returns the bitrate limit of the guild."""
		return int(self._bitrate_limit / 1000)

	bitrate = max_bitrate = bitrate_limit

	@property
	def filesize_limit(self) -> int:
		"""Returns the filesize limit of the guild in megabytes."""
		return int(self._filesize_limit / 1048576)  # Converts bytes to megabytes

	upload_limit = file_limit = file_size = max_file_size = filesize_limit

	@property
	def shard_id(self) -> int:
		"""Returns the shard ID of the guild."""
		return self._shard_id

	shard = shard_id

	@property
	def scheduled_events(self) -> int:
		"""Returns the number of scheduled events in the guild."""
		return len(self._scheduled_events)

	def __str__(self):
		return self.name

	def __int__(self):
		return self.id

	def __len__(self):
		return self.members

class IPAddress:
	def __init__(self, data: dict[str, str]):
		self._data = data

	@property
	def ip(self) -> str:
		return self._data.get("ip")

	@property
	def code(self) -> str:
		return self._data.get("country")

	country = code

	@property
	def hostname(self) -> str:
		return self._data.get("hostname")

	@property
	def city(self) -> str:
		return self._data.get("city")

	@property
	def region(self) -> str:
		return self._data.get("region")

	@property
	def postal(self) -> str:
		return self._data.get("postal")

	@property
	def timezone(self) -> str:
		return self._data.get("timezone")

	@property
	def organization(self) -> str:
		return self._data.get("org")

	org = organization

	@property
	def loc(self) -> str:
		return self._data.get("loc")

class CPU:
	@property
	def name(self):
		return get_cpu_info().get("brand_raw")

	@property
	def usage(self):
		return psutil.cpu_percent()

	@property
	def threads(self):
		return psutil.cpu_count()

	def __str__(self):
		return self.name

	cores = count = threads

class RAM:
	def __init__(self):
		self._memory = psutil.virtual_memory()

	@property
	def current(self):
		return round(self._memory.total / 1073741824, 2)

	@property
	def available(self):
		return round(self._memory.available / 1073741824, 2)

	@property
	def usage(self):
		return f"{self.current} GB / {self.available} GB"

	def __str__(self):
		return self.usage

class VPSProvider:
	@property
	def name(self):
		return "Bladehost VPS"

	@property
	def url(self):
		return "https://www.bladehost.eu/"

	def __str__(self):
		return f"[{self.name}]({self.url})"

class Disk:
	def __init__(self):
		self._disk = psutil.disk_usage("/")

	@property
	def percent(self):
		return self._disk.percent

	@property
	def total(self):
		return self._disk.total / 1073741824

	@property
	def used(self):
		return self._disk.total / 1073741824

	@property
	def free(self):
		return self._disk.total / 1073741824

	def __str__(self):
		return f"{self.percent}%"

class Network:
	def __init__(self):
		self._network = psutil.net_io_counters()

	@property
	def sent(self):
		return round(self._network.bytes_sent / 1073741824, 2)

	@property
	def received(self):
		return round(self._network.bytes_recv / 1073741824, 2)

	def __str__(self):
		return f"{self.sent} GB / {self.received} GB"

class BotInfo:
	def __init__(self, client: discord.Client):
		self.avatar = client.user.avatar.url
		self.name = client.user.name

	@property
	def provider(self):
		return VPSProvider()

	@property
	def processor(self):
		return CPU()

	cpu = processor

	@property
	def memory(self):
		return RAM()

	ram = memory

	@property
	def disk(self):
		return Disk()

	@property
	def boot_time(self):
		return FormatDateTime(datetime.datetime.fromtimestamp(psutil.boot_time()), "R")

	@property
	def network(self):
		return Network()

	@property
	def library_version(self):
		return discord.__version__

@dataclass
class CustomMessage:
	"""A class that represents a Discord message with useful formatting properties.
	
	This class is designed to be used in localization strings and provides
	easy access to message properties that are commonly used in logs.
	"""
	id: int
	"""Returns the message's ID."""
	content: str
	"""Returns the message's content."""
	_embeds: list[discord.Embed] = field(repr=False)
	_attachments: list[discord.Attachment] = field(repr=False)
	_stickers: list[discord.StickerItem] = field(repr=False)
	_author: CustomMember = field(repr=False)
	_channel: discord.TextChannel = field(repr=False)
	_guild: CustomGuild = field(repr=False)
	_created_at: datetime.datetime = field(repr=False)
	_edited_at: Optional[datetime.datetime] = field(repr=False)
	_pinned: bool = field(repr=False)
	_tts: bool = field(repr=False)
	_mention_everyone: bool = field(repr=False)
	_mentions: list[discord.Member] = field(repr=False)
	_role_mentions: list[discord.Role] = field(repr=False)
	_channel_mentions: list[discord.abc.GuildChannel | discord.Thread] = field(repr=False)
	_reference: Optional[discord.MessageReference] = field(repr=False)
	_flags: discord.MessageFlags = field(repr=False)
	_components: list[discord.ActionRow | discord.ui.Button | discord.SelectMenu | discord.ui.TextInput] = field(repr=False)
	_poll: Optional[discord.Poll] = field(repr=False)

	@classmethod
	def from_message(cls, message: discord.Message):
		"""Creates a CustomMessage from a discord.Message object."""
		return cls(
			id=message.id,
			content=message.content,
			_embeds=message.embeds,
			_attachments=message.attachments,
			_stickers=message.stickers,
			_author=CustomUser.from_user(message.author),
			_channel=message.channel,
			_guild=CustomGuild.from_guild(message.guild) if message.guild else None,
			_created_at=message.created_at,
			_edited_at=message.edited_at,
			_pinned=message.pinned,
			_tts=message.tts,
			_mention_everyone=message.mention_everyone,
			_mentions=message.mentions,
			_role_mentions=message.role_mentions,
			_channel_mentions=message.channel_mentions,  # type: ignore
			_reference=message.reference,
			_flags=message.flags,
			_components=message.components,
			_poll=message.poll
		)

	@property
	def embeds(self) -> int:
		"""Returns the number of embeds in the message."""
		return len(self._embeds)

	@property
	def attachments(self) -> int:
		"""Returns the number of attachments in the message."""
		return len(self._attachments)

	@property
	def stickers(self) -> int:
		"""Returns the number of stickers in the message."""
		return len(self._stickers)

	@property
	def author(self) -> CustomUser:
		"""Returns the message's author."""
		return self._author

	@property
	def channel(self) -> str:
		"""Returns the message's channel mention."""
		return self._channel.mention

	@property
	def guild(self) -> CustomGuild:
		"""Returns the message's guild."""
		return self._guild

	@property
	def created_at(self):
		"""Returns the date the message was created as a Discord timestamp."""
		return FormatDateTime(self._created_at, "F")

	created = created_at

	@property
	def edited_at(self):
		"""Returns the date the message was edited as a Discord timestamp."""
		return FormatDateTime(self._edited_at, "F") if self._edited_at else None

	edited = edited_at

	@property
	def pinned(self) -> bool:
		"""Returns whether the message is pinned."""
		return self._pinned

	@property
	def tts(self) -> bool:
		"""Returns whether the message is TTS."""
		return self._tts

	@property
	def mention_everyone(self) -> bool:
		"""Returns whether the message mentions everyone."""
		return self._mention_everyone

	@property
	def mentions(self) -> int:
		"""Returns the number of user mentions in the message."""
		return len(self._mentions)

	@property
	def role_mentions(self) -> int:
		"""Returns the number of role mentions in the message."""
		return len(self._role_mentions)

	@property
	def channel_mentions(self) -> int:
		"""Returns the number of channel mentions in the message."""
		return len(self._channel_mentions)

	@property
	def reference(self) -> Optional[str]:
		"""Returns the message's reference if it exists."""
		return self._reference.message_id if self._reference else None

	@property
	def flags(self) -> int:
		"""Returns the message's flags as an integer."""
		return self._flags.value

	@property
	def components(self) -> int:
		"""Returns the number of components in the message."""
		return len(self._components)

	@property
	def poll(self) -> bool:
		"""Returns whether the message has a poll."""
		return bool(self._poll)

	def __str__(self):
		return self.content

	def __int__(self):
		return self.id



@dataclass
class CustomCategoryChannel:
	name: str
	"""Returns the category's name."""
	_guild: discord.Guild
	id: int
	"""Returns the category's ID."""
	position: int
	"""Returns the category's position."""
	nsfw: bool
	"""Returns the category's nsfw status."""
	_channels: list[discord.abc.GuildChannel]
	_text_channels: list[discord.TextChannel]
	_voice_channels: list[discord.VoiceChannel]
	_stage_channels: list[discord.StageChannel]
	_forums: list[discord.ForumChannel]
	_created_at: datetime.datetime
	_jump_url: str
	mention: str
	"""Returns the category's mention string."""
	_overwrites: dict[discord.Role | discord.Member | discord.Object, discord.PermissionOverwrite]
	permissions_synced: bool
	"""Returns whether or not the permissions are synced to the parent category."""

	@classmethod
	def from_category(cls, category: discord.CategoryChannel):
		return cls(
			name=category.name,
			_guild=category.guild,
			id=category.id,
			position=category.position,
			nsfw=category.nsfw,
			_channels=category.channels,
			_text_channels=category.text_channels,
			_voice_channels=category.voice_channels,
			_stage_channels=category.stage_channels,
			_forums=category.forums,
			_created_at=category.created_at,
			_jump_url=category.jump_url,
			mention=category.mention,
			_overwrites=category.overwrites,
			permissions_synced=category.permissions_synced,
		)

	@property
	def guild(self) -> CustomGuild:
		"""Returns the category's guild."""
		return CustomGuild.from_guild(self._guild)

	@property
	def channels(self) -> int:
		"""Returns the number of channels in the category."""
		return len(self._channels)

	@property
	def text_channels(self) -> int:
		"""Returns the number of text channels in the category."""
		return len(self._text_channels)

	@property
	def voice_channels(self) -> int:
		"""Returns the number of voice channels in the category."""
		return len(self._voice_channels)

	@property
	def stage_channels(self) -> int:
		"""Returns the number of stage channels in the category."""
		return len(self._stage_channels)

	@property
	def forums(self) -> int:
		"""Returns the number of forums in the category."""
		return len(self._forums)

	@property
	def created_at(self) -> FormatDateTime:
		"""Returns the category's creation date."""
		return FormatDateTime(self._created_at, "f")

	created = created_at

	@property
	def jump_url(self) -> str:
		"""Returns the category's jump URL."""
		return self._jump_url

	url = jump_url

	@property
	def overwrites(self) -> int:
		"""Returns the number of overwrites in the category."""
		return len(self._overwrites)

	def __str__(self) -> str:
		return self.name

@dataclass
class CustomTextChannel:
	name: str
	"""Returns the channel's name."""
	_guild: discord.Guild
	id: int
	"""Returns the channel's id."""
	topic: Optional[str]
	"""Returns the channel's topic."""
	position: int
	"""Returns the channel's position."""
	_slowmode_delay: int
	nsfw: bool
	"""Returns the channel's nsfw status."""
	_default_auto_archive_duration: int
	_default_thread_slowmode_delay: int
	_members: list[discord.Member]
	_threads: list[discord.Thread]
	news: bool
	"""Returns the channel's news status."""
	_category: discord.CategoryChannel
	_created_at: datetime.datetime
	_jump_url: str
	mention: str
	"""Returns the channel's mention string."""
	_overwrites: dict[discord.Role | discord.Member | discord.Object, discord.PermissionOverwrite]
	permissions_synced: bool
	"""Returns whether or not the permissions are synced to the parent category."""

	@classmethod
	def from_channel(cls, channel: discord.TextChannel):
		return cls(
			name=channel.name,
			_guild=channel.guild,
			id=channel.id,
			topic=channel.topic,
			position=channel.position,
			_slowmode_delay=channel.slowmode_delay,
			nsfw=channel.nsfw,
			_default_auto_archive_duration=channel.default_auto_archive_duration,
			_default_thread_slowmode_delay=channel.default_thread_slowmode_delay,
			_members=channel.members,
			_threads=channel.threads,
			news=channel.is_news(),
			_category=channel.category,
			_created_at=channel.created_at,
			_jump_url=channel.jump_url,
			mention=channel.mention,
			_overwrites=channel.overwrites,
			permissions_synced=channel.permissions_synced,
		)

	@property
	def guild(self) -> CustomGuild:
		"""Returns the channel's guild."""
		return CustomGuild.from_guild(self._guild)

	@property
	def slowmode(self) -> int:
		"""Returns the slowmode delay in seconds."""
		return self._slowmode_delay

	slowmode_delay = slowmode

	@property
	def auto_archive(self) -> int:
		"""Returns how long threads have to be inactive to be archived in minutes."""
		return self._default_auto_archive_duration

	@property
	def thread_slowmode(self) -> int:
		"""Returns the channel's thread slowmode delay in minutes."""
		return self._slowmode_delay

	thread_slowmode_delay = thread_slowmode

	@property
	def members(self):
		"""Returns how many members can see the channel."""
		return len(self._members)

	@property
	def threads(self):
		"""Returns how many threads are in the channel."""
		return len(self._threads)

	@property
	def category(self) -> Optional[CustomCategoryChannel]:
		"""Returns the channel's category."""
		return CustomCategoryChannel.from_category(self._category) if self._category else None

	@property
	def created_at(self) -> FormatDateTime:
		"""Returns the channel's creation date."""
		return FormatDateTime(self._created_at, "f")

	created = created_at

	@property
	def url(self) -> str:
		"""Returns the channel's jump URL."""
		return self._jump_url

	jump_url = url

	@property
	def overwrites(self) -> int:
		"""Returns the number of channel overwrites."""
		return len(self._overwrites)

	def __str__(self) -> str:
		return self.name

@dataclass
class CustomVoiceChannel:
	name: str
	"""Returns the channel's name."""
	_guild: discord.Guild
	id: int
	"""Returns the channel's id."""
	nsfw: bool
	"""Returns the channel's nsfw status."""
	position: int
	"""Returns the channel's position."""
	bitrate: int
	"""Returns the channel's bitrate."""
	user_limit: int
	"""Returns the channel's user limit."""
	_rtc_region: Optional[str]
	_slowmode_delay: int
	_category: Optional[discord.CategoryChannel]
	_created_at: datetime.datetime
	_jump_url: str
	mention: str
	"""Returns the channel's mention string."""
	_overwrites: dict[discord.Role | discord.Member | discord.Object, discord.PermissionOverwrite]
	permissions_synced: bool
	"""Returns whether or not the permissions are synced to the parent category."""
	_scheduled_events: list[discord.ScheduledEvent]

	@classmethod
	def from_channel(cls, channel: discord.VoiceChannel):
		return cls(
			name=channel.name,
			_guild=channel.guild,
			id=channel.id,
			nsfw=channel.nsfw,
			position=channel.position,
			bitrate=int(channel.bitrate / 1000),
			user_limit=channel.user_limit,
			_rtc_region=channel.rtc_region,
			_slowmode_delay=channel.slowmode_delay,
			_category=channel.category,
			_created_at=channel.created_at,
			_jump_url=channel.jump_url,
			mention=channel.mention,
			_overwrites=channel.overwrites,
			permissions_synced=channel.permissions_synced,
			_scheduled_events=channel.scheduled_events,
		)

	@property
	def guild(self):
		"""Returns the channel's guild."""
		return CustomGuild.from_guild(self._guild)

	@property
	def rtc_region(self):
		"""Returns the channel's RTC region."""
		return self._rtc_region

	region = rtc_region

	@property
	def slowmode_delay(self) -> int:
		"""Returns the channel's slowmode delay in seconds."""
		return self._slowmode_delay

	slowmode = slowmode_delay

	@property
	def category(self) -> Optional[CustomCategoryChannel]:
		"""Returns the channel's category."""
		return CustomCategoryChannel.from_category(self._category) if self._category else None

	@property
	def created_at(self) -> FormatDateTime:
		"""Returns the channel's creation date."""
		return FormatDateTime(self._created_at, "f")

	created = created_at

	@property
	def jump_url(self) -> str:
		"""Returns the channel's jump URL."""
		return self._jump_url

	url = jump_url

	@property
	def overwrites(self) -> int:
		"""Returns the number of channel overwrites."""
		return len(self._overwrites)

	@property
	def scheduled_events(self) -> int:
		"""Returns the number of scheduled events in the channel."""
		return len(self._scheduled_events)

	def __str__(self) -> str:
		return self.name

@dataclass
class CustomStageChannel:
	name: str
	"""Returns the stage channel's name."""
	_guild: discord.Guild
	id: int
	nsfw: bool
	"""Returns the stage channel's nsfw status."""
	topic: Optional[str]
	"""Returns the stage channel's topic."""
	position: int
	"""Returns the stage channel's position."""
	_bitrate: int
	user_limit: int
	"""Returns the stage channel's user limit."""
	_rtc_region: str
	"""Returns the stage channel's RTC region."""
	_slowmode_delay: int
	_requesting_to_speak: list[discord.Member]
	_speakers: list[discord.Member]
	_listeners: list[discord.Member]
	_moderators: list[discord.Member]
	_category: Optional[discord.CategoryChannel]
	_created_at: datetime.datetime
	_jump_url: str
	_members: list[discord.Member]
	mention: str
	"""Returns the stage channel's mention string."""
	_overwrites: dict[discord.Role | discord.Member | discord.Object, discord.PermissionOverwrite]
	permissions_synced: bool
	"""Returns whether or not the permissions are synced to the parent category."""
	_scheduled_events: list[discord.ScheduledEvent]

	@classmethod
	def from_channel(cls, channel: discord.StageChannel):
		return cls(
			name=channel.name,
			_guild=channel.guild,
			id=channel.id,
			nsfw=channel.nsfw,
			topic=channel.topic,
			position=channel.position,
			_bitrate=channel.bitrate,
			user_limit=channel.user_limit,
			_rtc_region=channel.rtc_region,
			_slowmode_delay=channel.slowmode_delay,
			_requesting_to_speak=channel.requesting_to_speak,
			_speakers=channel.speakers,
			_listeners=channel.listeners,
			_moderators=channel.moderators,
			_category=channel.category,
			_created_at=channel.created_at,
			_jump_url=channel.jump_url,
			_members=channel.members,
			mention=channel.mention,
			_overwrites=channel.overwrites,
			permissions_synced=channel.permissions_synced,
			_scheduled_events=channel.scheduled_events,
		)

	@property
	def guild(self) -> CustomGuild:
		"""Returns the stage channel's guild."""
		return CustomGuild.from_guild(self._guild)

	@property
	def bitrate(self) -> int:
		"""Returns the stage channel's bitrate in kbps."""
		return int(self._bitrate / 1000)

	@property
	def rtc_region(self) -> str:
		"""Returns the stage channel's RTC region."""
		return self._rtc_region

	region = rtc_region

	@property
	def slowmode_delay(self) -> int:
		"""Returns the channel's slowmode delay in seconds."""
		return self._slowmode_delay

	slowmode = slowmode_delay

	@property
	def requesting_to_speak(self) -> int:
		"""Returns the number of requesting speakers."""
		return len(self._requesting_to_speak)

	@property
	def speakers(self) -> int:
		"""Returns the number of speakers."""
		return len(self._speakers)

	@property
	def listeners(self) -> int:
		return len(self._listeners)

	@property
	def moderators(self) -> int:
		"""Returns the number of moderators."""
		return len(self._moderators)

	@property
	def category(self) -> Optional[CustomCategoryChannel]:
		"""Returns the channel's category.'"""
		return CustomCategoryChannel.from_category(self._category) if self._category else None

	@property
	def created_at(self) -> FormatDateTime:
		"""Returns the channel's creation date.'"""
		return FormatDateTime(self._created_at, "f")

	created = created_at

	@property
	def jump_url(self) -> str:
		"""Returns the channel's jump URL.'"""
		return self._jump_url

	url = jump_url

	@property
	def members(self) -> int:
		"""Returns the number of members that can see this channel."""
		return len(self._members)

	@property
	def overwrites(self) -> int:
		"""Returns the number of channel overwrites."""
		return len(self._overwrites)

	@property
	def scheduled_events(self) -> int:
		"""Returns the number of scheduled events in the channel."""
		return len(self._scheduled_events)

	events = scheduled_events

	def __str__(self) -> str:
		return self.name

@dataclass
class CustomPartialEmoji:
	_name: Optional[str]
	animated: bool
	id: Optional[int]
	_created_at: Optional[datetime.datetime]
	_url: Optional[str]
	_is_unicode: bool
	display: str

	@classmethod
	def from_emoji(cls, emoji: discord.PartialEmoji):
		return cls(
			_name=emoji.name,
			animated=emoji.animated,
			id=emoji.id,
			_created_at=emoji.created_at,
			_url=emoji.url,
			_is_unicode=emoji.is_unicode_emoji(),
			display=str(emoji)
		)

	@property
	def name(self) -> str:
		if self._is_unicode:
			name = demojize(self._name)
			return name.strip(":")
		return self._name

	def __str__(self) -> str:
		return self.display

	@property
	def created_at(self) -> FormatDateTime:
		return FormatDateTime(self._created_at, "f") if self._created_at else None

	created = created_at

	@property
	def url(self) -> Optional[str]:
		codepoints = "-".join(f"{ord(code):x}" for code in self._name)
		return self._url if self._url != "" else f"https://cdn.jsdelivr.net/gh/twitter/twemoji@latest/assets/72x72/{codepoints}.png"

@dataclass
class CustomEmoji(CustomPartialEmoji):
	managed: bool
	_roles: list[discord.Role]
	_guild: discord.Guild
	_is_application_owned: bool

	@classmethod
	def from_emoji(cls, emoji: discord.Emoji):
		return cls(
			_name=emoji.name,
			id=emoji.id,
			animated=emoji.animated,
			managed=emoji.managed,
			_created_at=emoji.created_at,
			_url=emoji.url,
			_roles=emoji.roles,
			_guild=emoji.guild,
			_is_application_owned=emoji.is_application_owned(),
			_is_unicode=False
		)

	@property
	def name(self) -> str:
		return self._name

	@property
	def roles(self) -> bool:
		"""Returns whether or not this emoji is specific to a role or multiple or roles."""
		return len(self._roles) != 0

	__str__ = name

	@property
	def guild(self) -> CustomGuild:
		return CustomGuild.from_guild(self._guild)

	@property
	def is_application_owned(self) -> bool:
		"""Returns whether or not this emoji is only usable by a bot."""
		return self._is_application_owned

	application_owned = bot_owned = is_application_owned

@dataclass
class CustomForumChannel:
	name: str
	"""Returns the forum channel's name."""
	_guild: discord.Guild
	id: int
	"""Returns the forum channel's ID."""
	topic: str
	"""Returns the forum channel's topic."""
	position: int
	"""Returns the forum channel's position."""
	_slowmode_delay: int
	nsfw: bool
	"""Returns the forum channel's nsfw status."""
	_default_auto_archive_duration: int
	_default_thread_slowmode_delay: int
	_default_reaction_emoji: Optional[discord.PartialEmoji]
	_members: list[discord.Member]
	_threads: list[discord.Thread]
	_available_tags: Sequence[discord.ForumTag]
	media: bool
	"""Returns whether or not the channel is a media channel."""
	_category: Optional[discord.CategoryChannel]
	_created_at: datetime.datetime
	_jump_url: str
	mention: str
	"""Returns a string to mention the channel."""
	_overwrites: dict[discord.Role | discord.Member | discord.Object, discord.PermissionOverwrite]
	permissions_synced: bool
	"""Returns whether or not the permissions are synced to the parent category."""

	@classmethod
	def from_channel(cls, channel: discord.ForumChannel):
		return cls(
			name=channel.name,
			_guild=channel.guild,
			id=channel.id,
			topic=channel.topic,
			position=channel.position,
			_slowmode_delay=channel.slowmode_delay,
			nsfw=channel.nsfw,
			_default_auto_archive_duration=channel.default_auto_archive_duration,
			_default_thread_slowmode_delay=channel.default_thread_slowmode_delay,
			_default_reaction_emoji=channel.default_reaction_emoji,
			_members=channel.members,
			_threads=channel.threads,
			_available_tags=channel.available_tags,
			media=channel.is_media(),
			_category=channel.category,
			_created_at=channel.created_at,
			_jump_url=channel.jump_url,
			mention=channel.mention,
			_overwrites=channel.overwrites,
			permissions_synced=channel.permissions_synced,
		)

	@property
	def guild(self) -> CustomGuild:
		return CustomGuild.from_guild(self._guild)

	@property
	def slowmode_delay(self) -> int:
		"""Returns the channel's slowmode delay in seconds."""
		return self._slowmode_delay

	slowmode = slowmode_delay

	@property
	def default_auto_archive_duration(self) -> int:
		"""Returns the channel's default auto-archive duration in seconds."""
		return self._default_auto_archive_duration

	auto_archive_duration = auto_archive = default_auto_archive_duration

	@property
	def default_thread_slowmode_delay(self) -> int:
		"""Returns the channel's default thread slowmode delay in seconds."""
		return self._default_thread_slowmode_delay

	thread_slowmode = default_thread_slowmode_delay

	@property
	def default_reaction_emoji(self) -> Optional[CustomPartialEmoji]:
		return CustomPartialEmoji.from_emoji(self._default_reaction_emoji) if self._default_reaction_emoji else None

	@property
	def members(self) -> int:
		"""Returns the number of members that can see this channel."""
		return len(self._members)

	@property
	def threads(self) -> int:
		"""Returns the number of threads (forum posts) in the channel."""
		return len(self._threads)

	@property
	def available_tags(self) -> int:
		"""Returns the number of available tags."""
		return len(self._available_tags)

	tags = available_tags

	@property
	def category(self) -> Optional[CustomCategoryChannel]:
		"""Returns the channel's category."""
		return CustomCategoryChannel.from_category(self._category) if self._category else None

	@property
	def created_at(self) -> FormatDateTime:
		"""Returns the channel's creation date."""
		return FormatDateTime(self._created_at, "f")

	created = created_at

	@property
	def jump_url(self) -> str:
		"""Returns the channel's URL."""
		return self._jump_url

	url = jump_url

	@property
	def overwrites(self) -> int:
		"""Returns the number of channel overwrites."""
		return len(self._overwrites)

	def __str__(self) -> str:
		return self.name

@dataclass
class CustomTemplate:
	name: str
	_guild: discord.Guild
	_author: discord.User
	_created_at: datetime.datetime
	code: str
	roles: int
	channels: int
	uses: int
	description: Optional[str]
	_updated_at: Optional[datetime.datetime]
	_is_dirty: Optional[bool]
	url: Optional[str]

	@classmethod
	async def from_dict(cls, client: discord.Client, data: dict):
		return cls(
			name=data["name"],
			_guild=await client.fetch_guild(data["guild_id"]),
			_author=await client.fetch_user(data["author_id"]),
			_created_at=data["date"],
			code=data["code"],
			roles=len(data["payload"].get("roles", [])),
			channels=len(data["payload"].get("channels", [])),
			uses=0,
			description=None,
			_updated_at=None,
			_is_dirty=None,
			url=None
		)

	@classmethod
	def from_template(cls, template: discord.Template):
		return cls(
			name=template.name,
			_guild=template.source_guild,
			_author=template.creator,
			_created_at=template.created_at,
			code=template.code,
			roles=0,
			channels=0,
			uses=template.uses,
			description=template.description,
			_updated_at=template.updated_at,
			_is_dirty=template.is_dirty,
			url=template.url
		)

	@property
	def guild(self) -> CustomGuild:
		return CustomGuild.from_guild(self._guild) if self._guild else None

	@property
	def author(self) -> CustomUser:
		return CustomUser.from_user(self._author) if self._author else None

	@property
	def created_at(self) -> FormatDateTime:
		return FormatDateTime(self._created_at, "f")

	created = created_at

	@property
	def updated_at(self) -> Optional[FormatDateTime]:
		return FormatDateTime(self._updated_at, "f") if self._updated_at else None

	updated = updated_at

	@property
	def is_dirty(self) -> bool:
		return self._is_dirty

	unsynced = dirty = is_dirty

@dataclass
class CustomRuleAction:
	type: str
	"""Returns the action's type."""
	_channel: Optional[discord.TextChannel] = field(repr=False)
	_duration: Optional[datetime.timedelta] = field(repr=False)

	@classmethod
	def from_action(cls, action: 'discord.AutoModRuleAction', guild: discord.Guild):
		channel = guild.get_channel(action.channel_id) if action.channel_id else None
		return cls(
			type=action.type.name,
			_channel=channel,
			_duration=action.duration
		)
	
	@property
	def channel(self) -> Optional[str]:
		"""Returns the channel the action is sent to."""
		return self._channel.mention if self._channel else None
	
	@property
	def duration(self) -> Optional[str]:
		"""Returns the duration of the timeout."""
		if not self._duration:
			return None
		
		days = self._duration.days
		seconds = self._duration.seconds
		hours = seconds // 3600
		minutes = (seconds % 3600) // 60
		
		return f"{days}d {hours}h {minutes}m"

@dataclass
class CustomAutoModRule:
	name: str
	"""Returns the rule's name."""
	id: int
	"""Returns the rule's ID."""
	enabled: bool
	"""Returns whether the rule is enabled."""
	trigger_type: str
	"""Returns the rule's trigger type."""
	_creator: discord.Member = field(repr=False)
	_guild: discord.Guild = field(repr=False)
	_actions: list['discord.AutoModRuleAction'] = field(repr=False)
	_exempt_roles: list[discord.Role] = field(repr=False)
	_exempt_channels: list[discord.abc.GuildChannel] = field(repr=False)
	_created_at: datetime.datetime = field(repr=False)

	@classmethod
	async def from_rule(cls, rule: discord.AutoModRule):
		creator = rule.guild.get_member(rule.creator_id) or await rule.guild.fetch_member(rule.creator_id)
		return cls(
			name=rule.name,
			id=rule.id,
			enabled=rule.enabled,
			trigger_type=rule.trigger.type.name,
			_creator=creator,
			_guild=rule.guild,
			_actions=rule.actions,
			_exempt_roles=rule.exempt_roles,
			_exempt_channels=rule.exempt_channels,
			_created_at=discord.utils.snowflake_time(rule.id)
		)

	@property
	def creator(self) -> CustomMember:
		"""Returns the rule's creator."""
		return CustomMember.from_member(self._creator)

	@property
	def guild(self) -> CustomGuild:
		"""Returns the rule's guild."""
		return CustomGuild.from_guild(self._guild)

	@property
	def actions(self) -> str:
		"""Returns the rule's actions."""
		if not self._actions:
			return "None"
		
		action_strings = []
		for action in self._actions:
			if action.type.name == "send_alert_message":
				channel = self._guild.get_channel(action.channel_id)
				if channel:
					action_strings.append(f"Send Alert to {channel.mention}")
				else:
					action_strings.append("Send Alert (Channel not found)")
			elif action.type.name == "timeout":
				duration_seconds = action.duration.total_seconds()
				minutes, seconds = divmod(duration_seconds, 60)
				hours, minutes = divmod(minutes, 60)
				days, hours = divmod(hours, 24)
				
				duration_str = ""
				if days > 0:
					duration_str += f"{int(days)}d "
				if hours > 0:
					duration_str += f"{int(hours)}h "
				if minutes > 0:
					duration_str += f"{int(minutes)}m "
				if seconds > 0:
					duration_str += f"{int(seconds)}s"
				
				action_strings.append(f"Timeout ({duration_str.strip()})")
			else:
				action_strings.append(action.type.name.replace("_", " ").title())
				
		return ", ".join(action_strings)

	@property
	def exempt_roles(self) -> str:
		"""Returns the rule's exempt roles."""
		return ", ".join([role.mention for role in self._exempt_roles]) if self._exempt_roles else "None"

	@property
	def exempt_channels(self) -> str:
		"""Returns the rule's exempt channels."""
		return ", ".join([channel.mention for channel in self._exempt_channels]) if self._exempt_channels else "None"
	
	@property
	def created_at(self) -> FormatDateTime:
		"""Returns when the rule was created."""
		return FormatDateTime(self._created_at, "f")

	def __str__(self) -> str:
		return self.name

@dataclass
class CustomAutoModAction:
	action: CustomRuleAction = field(repr=False)
	"""The action that was taken."""
	rule_trigger_type: str = field(repr=False)
	"""The trigger type of the rule that was executed."""
	rule_id: int = field(repr=False)
	"""The ID of the rule that was executed."""
	guild: CustomGuild = field(repr=False)
	"""The guild where the action was executed."""
	member: CustomMember = field(repr=False)
	"""The member who triggered the action."""
	channel: Optional[str] = field(repr=False)
	"""The channel where the action was executed."""
	message_id: Optional[int] = field(repr=False)
	"""The ID of the message that triggered the action."""
	matched_keyword: Optional[str] = field(repr=False)
	"""The keyword that was matched."""
	matched_content: Optional[str] = field(repr=False)
	"""The content that was matched."""

	@classmethod
	def from_action(cls, execution: 'discord.AutoModAction'):
		return cls(
			action=CustomRuleAction.from_action(execution.action, execution.guild),
			rule_trigger_type=execution.rule_trigger_type.name,
			rule_id=execution.rule_id,
			guild=CustomGuild.from_guild(execution.guild),
			member=CustomMember.from_member(execution.member),
			channel=execution.channel.mention if execution.channel else None,
			message_id=execution.message_id,
			matched_keyword=execution.matched_keyword,
			matched_content=execution.matched_content,
		)
