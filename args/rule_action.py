import datetime
from dataclasses import dataclass, field

import discord
from helpers.convert import seconds_to_text

from args.channel import Channel, convert_to_custom_channel


@dataclass(slots=True)
class RuleAction:
	type: str
	"""The action's type."""
	_channel: discord.TextChannel | None = field(repr=False)
	_duration: datetime.timedelta | None = field(repr=False)

	@classmethod
	def from_action(cls, action: discord.AutoModRuleAction, guild: discord.Guild):
		channel = guild.get_channel(action.channel_id) if action.channel_id else None
		return cls(type=action.type.name, _channel=channel, _duration=action.duration)  # type: ignore

	@property
	def channel(self) -> Channel | None:
		"""The channel the action is sent to."""
		return convert_to_custom_channel(self._channel)

	@property
	def duration(self) -> str | None:
		"""The duration of the timeout."""
		return seconds_to_text(int(self._duration.total_seconds())) if self._duration else None
