"""A helper for custom messages."""

import datetime
import json
import logging
import pathlib
import random
import time
from typing import Any, Optional, Union, overload

import discord
from .custom_args import CustomGuild, CustomMember
from discord.ext import commands, localization

from helpers import emojis

logger = logging.getLogger(__name__)


class CustomResponse:
	"""A class to handle custom responses with localization."""

	def __init__(self, client: discord.Client | type[discord.Client], name: Optional[str] = None) -> None:
		"""A custom message instance.

		Parameters
		----------
		client: `discord.Client`
			The client object with a `db` attribute.
		name: `str`
			The name of the cog that uses this class.
		"""
		self.client = client
		self.name = name
		self.localizations: dict[str, dict] = {}
		self._localizer = None
		self._last_debug_reload: float = 0

		self.load_localizations()

	@staticmethod
	def convert_embeds(data: Any) -> Any:
		"""Converts `data`'s embed (dict) or embeds (list) keys' values into a discord.Embed.

		This converts in a smart way: if there are both an `embed` and `embeds` key, `embed` will be merged into `embeds`.

		Parameters
		----------
		data: `Any`
		        The data that might contain an `embed` or an `embeds` key. Conversion is only performed if this is a `dict`.

		Raises
		------
		ValueError
		        If there are more than 10 embeds.

		Returns
		--------
		Any
		        The original data, but with usable `discord.Embed`s.
		"""
		if isinstance(data, dict) and (data.get("embed") or data.get("embeds")):
			if len(data.get("embeds", [])) > 10:
				raise ValueError(f"The maximum number of embeds is 10. You have {len(data['embeds'])} embeds.")
			if data.get("embed") and not data.get("embeds"):
				data["embeds"] = [data.pop("embed")]

			cleaned_embeds = []
			for embed_dict in data.get("embeds", []):
				if not isinstance(embed_dict, dict):
					continue
				fields = embed_dict.get("fields", [])
				cleaned_fields = []

				for field in fields:
					value = field.get("value")
					if value in ("None", "0", ""):
						continue  # skip empty fields
					if value == "True":
						field["value"] = emojis.CHECK
					if value == "False":
						field["value"] = emojis.XMARK
					cleaned_fields.append(field)

				embed_dict["fields"] = cleaned_fields
				cleaned_embeds.append(discord.Embed.from_dict(embed_dict))

			data["embeds"] = cleaned_embeds
		return data

	@overload
	def update_localizations(self, data: dict): ...

	@overload
	def update_localizations(self, path: str): ...

	def update_localizations(self, data: Union[dict, str]):
		if isinstance(data, dict):
			self.localizations.update(data)
		elif isinstance(data, str):
			self.load_localizations(data)

	def load_localizations(self, path: str = "./localization"):
		localization_path = pathlib.Path(path)
		for file_path in localization_path.glob("*.l10n.json"):
			lang = file_path.stem.removesuffix(".l10n")
			try:
				with open(file_path, encoding="utf-8") as f:
					data = json.load(f)
					if not isinstance(data, dict):
						raise ValueError(f"Expected dict in {file_path}, got {type(data).__name__}")
					self.localizations.setdefault(lang, {}).update(data)
			except Exception as e:
				logger.warning(f"Failed to load {file_path}: {e}")

		self._localizer = localization.Localization(self.localizations, default_locale="en")

	async def get_message(
		self,
		name: str,
		locale: Union[str, discord.Locale, discord.Guild, discord.Interaction, commands.Context],
		*,
		convert_embeds: bool = True,
		**kwargs: Any,
	) -> Union[dict, str, list, int, float, bool]:
		"""Gets a custom message from the database, or if not found, gets the default message.

		Parameters
		----------
		name: str
		        The name of the message.
		locale: Union[str, discord.Locale, discord.Guild, discord.Interaction, commands.Context]
		        The locale to use or the context to derive it.
		convert_embeds: bool
		        Whether to convert the embeds in the message to discord.Embeds.

		Returns
		-------
		Union[dict, str, list, int, float, bool]
		        The message payload.
		"""
		from main import DEBUG

		original = locale

		if isinstance(locale, (discord.Interaction, commands.Context)):
			locale = locale.guild.preferred_locale if (locale.guild and locale.guild.preferred_locale) else "en"
		elif isinstance(locale, discord.Guild):
			locale = locale.preferred_locale or "en"
		elif isinstance(locale, discord.Message):
			locale = locale.guild.preferred_locale or "en" if locale.guild else "en"
		else:
			locale = str(locale)

		match original:
			case discord.Guild():
				guild_id = original.id
			case discord.Interaction() | commands.Context():
				guild_id = original.guild.id
			case _:
				guild_id = None

		context_formatting = {
			"author": CustomMember.from_member(original.author)
			if isinstance(original, commands.Context)
			else CustomMember.from_member(original.user)
			if isinstance(original, discord.Interaction)
			else None,
			"guild": (
				CustomGuild.from_guild(original.guild)
				if isinstance(original, (discord.Interaction, commands.Context)) and hasattr(original, "guild")
				else CustomGuild.from_guild(original)
				if isinstance(original, discord.Guild)
				else None
			),
			"now": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
		}

		if __debug__:
			now = time.time()
			if now - self._last_debug_reload > 5:
				self.load_localizations("../localization")
				self._last_debug_reload = now

		payload = self._localizer.localize(name, locale, **kwargs, random=r"{random}", **context_formatting)

		if isinstance(payload, dict):
			if random_value := payload.get("random"):
				payload = localization.Localization.format_strings(payload, random=random.choice(random_value))
			payload.pop("random", None)
			payload = self.convert_embeds(payload) if convert_embeds else payload

			if payload.get("reply"):
				payload["reference"] = (
					original.message if isinstance(original, (discord.Interaction, commands.Context)) else None
				)
			payload.pop("reply", None)

			if allowed_mentions := payload.get("allowed_mentions"):
				if "all" in allowed_mentions:
					payload["allowed_mentions"] = discord.AllowedMentions.all()
				elif "none" in allowed_mentions:
					payload["allowed_mentions"] = discord.AllowedMentions.none()
				else:
					payload["allowed_mentions"] = discord.AllowedMentions(**allowed_mentions)

			if payload.get("ephemeral") or payload.get("delete_after"):
				if not isinstance(original, discord.Interaction):
					payload.pop("ephemeral", None)
				else:
					payload.pop("delete_after", None)
		return payload

	__call__ = get_message
