import asyncio
import re
from typing import Optional

import discord
import pypokedex
import requests
from core import Context, MyClient
from discord import app_commands
from discord.ext import commands
from emoji.unicode_codes import EMOJI_DATA
from helpers.custom_args import (
	BotInfo,
	CustomCategoryChannel,
	CustomEmoji,
	CustomForumChannel,
	CustomGuild,
	CustomMember,
	CustomPartialEmoji,
	CustomRole,
	CustomStageChannel,
	CustomTemplate,
	CustomTextChannel,
	CustomUser,
	CustomVoiceChannel,
	IPAddress,
)
from helpers.regex import DISCORD_TEMPLATE


class Info(commands.Cog, name="Information"):
	def __init__(self, client: MyClient):
		self.client = client

	@commands.hybrid_group(name="info", description="info_specs-description")
	@app_commands.rename(argument="info_specs-args-argument-name")
	@app_commands.describe(argument="info_specs-args-argument-description")
	async def info(
		self,
		ctx: Context,
		argument: discord.User | discord.abc.GuildChannel | discord.Role | discord.Emoji | discord.PartialEmoji,
	):
		if isinstance(argument, discord.User):
			await ctx.invoke(self.info.get_command("user"), argument)  # type: ignore
		elif isinstance(argument, discord.abc.GuildChannel):
			await ctx.invoke(self.info.get_command("channel"), argument)  # type: ignore
		elif isinstance(argument, discord.Role):
			await ctx.invoke(self.info.get_command("role"), argument)  # type: ignore
		elif isinstance(argument, (discord.Emoji, discord.PartialEmoji)):
			await ctx.invoke(self.info.get_command("emoji"), argument)  # type: ignore
		else:
			raise commands.BadArgument

	@info.command(name="user", description="userinfo_specs-description")
	@app_commands.rename(user="userinfo_specs-args-user-name")
	@app_commands.describe(user="userinfo_specs-args-user-description")
	async def user(self, ctx: Context, user: discord.Member | discord.User | None = None):
		user = user or ctx.author

		if not ctx.guild and type(user) is discord.User:
			await ctx.send("info.user.not_member", member=CustomUser.from_user(user))
			return

		if isinstance(user, discord.Member):
			await ctx.send("info.user.member", member=CustomMember.from_member(user))
			return

		try:
			member = await ctx.guild.fetch_member(user.id)
			await ctx.send("info.user.member", member=CustomMember.from_member(member))
		except discord.NotFound:
			await ctx.send("info.user.not_member", member=CustomUser.from_user(user))

	@info.command(name="server", description="serverinfo_specs-description")
	@commands.guild_only()
	async def server(self, ctx: Context):
		await ctx.send("info.server", server=CustomGuild.from_guild(ctx.guild))

	@info.command(name="role", description="roleinfo_specs-description")
	@commands.guild_only()
	@app_commands.rename(role="roleinfo_specs-args-role-name")
	@app_commands.describe(role="roleinfo_specs-args-role-description")
	async def role(self, ctx: Context, role: Optional[discord.Role] = None):
		role = role or ctx.author.top_role
		if not role:
			raise commands.BadArgument("role")
		await ctx.send("info.role", role=CustomRole.from_role(role))

	@info.command(name="ip", description="ipinfo_specs-description")
	@app_commands.rename(ip_addr="ipinfo_specs-args-ip-name")
	@app_commands.describe(ip_addr="ipinfo_specs-args-ip-description")
	async def ip(self, ctx: Context, ip_addr: str):
		try:
			ip_json = await self.client.request(f"https://ipinfo.io/{ip_addr}/json")
		except RuntimeError:
			raise commands.BadArgument("ip")
		ip = IPAddress(ip_json)
		await ctx.send("info.ip", ip=ip)

	@info.command(name="bot", description="botinfo_specs-description")
	async def bot(self, ctx: Context):
		await ctx.send("info.bot", bot=BotInfo(self.client))

	@info.command(name="emoji", description="emojiinfo_specs-description")
	@app_commands.rename(emoji_name="emojiinfo_specs-args-emoji-name")
	@app_commands.describe(emoji_name="emojiinfo_specs-args-emoji-description")
	async def emoji(self, ctx: Context, emoji_name: str):
		try:
			emoji = await commands.EmojiConverter().convert(ctx, emoji_name)
		except commands.BadArgument:
			emoji = discord.PartialEmoji.from_str(emoji_name)
		if isinstance(emoji, discord.Emoji):
			await ctx.send("info.emoji.custom_emoji", emoji=CustomEmoji.from_emoji(emoji))
		elif isinstance(emoji, discord.PartialEmoji) and emoji.name in EMOJI_DATA:
			await ctx.send("info.emoji.unicode_emoji", emoji=CustomPartialEmoji.from_emoji(emoji))
		else:
			raise commands.BadArgument("emoji")

	@info.command(name="channel", description="chinfo_specs-description")
	@commands.guild_only()
	@app_commands.rename(channel="chinfo_specs-args-channel-name")
	@app_commands.describe(channel="chinfo_specs-args-channel-description")
	async def channel(self, ctx: Context, channel: discord.abc.GuildChannel):
		if isinstance(channel, discord.TextChannel):
			await ctx.send("info.channel.text", channel=CustomTextChannel.from_channel(channel))
		elif isinstance(channel, discord.VoiceChannel):
			await ctx.send("info.channel.voice", channel=CustomVoiceChannel.from_channel(channel))
		elif isinstance(channel, discord.CategoryChannel):
			await ctx.send("info.channel.category", category=CustomCategoryChannel.from_category(channel))
		elif isinstance(channel, discord.ForumChannel):
			await ctx.send("info.channel.forum", channel=CustomForumChannel.from_channel(channel))
		elif isinstance(channel, discord.StageChannel):
			await ctx.send("info.channel.stage", channel=CustomStageChannel.from_channel(channel))
		else:
			raise commands.BadArgument("channel")

	@info.command(name="pokemon", description="pokeinfo_specs-description")
	@app_commands.rename(pokemon_name="pokeinfo_specs-args-pokemon-name")
	@app_commands.describe(pokemon_name="pokeinfo_specs-args-pokemon-description")
	async def pokemon(self, ctx: Context, pokemon_name: str):
		try:
			pokemon = await asyncio.get_event_loop().run_in_executor(None, lambda: pypokedex.get(name=pokemon_name))  # type: ignore
		except requests.HTTPError:
			raise commands.BadArgument("pokemon")
		pokemon.type = "\n".join(pokemon.types)
		pokemon.image = f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{pokemon.dex}.png"

		await ctx.send("info.pokemon", pokemon=pokemon)

	@info.command(name="template", description="tmplteinfo_specs-description")
	@app_commands.rename(template="tmplteinfo_specs-args-tmpl-name")
	@app_commands.describe(template="tmplteinfo_specs-args-tmpl-description")
	async def template(self, ctx: Context, template: str):
		regex = DISCORD_TEMPLATE.search(template)
		if regex:
			template_code = regex.group(1)
		elif re.fullmatch(r"[a-zA-Z0-9]{5,}", template):
			template_code = template
		else:
			template_code = None

		if template_code:
			try:
				template_obj = await self.client.fetch_template(template_code)
				return await ctx.send("info.template", template=CustomTemplate.from_template(template_obj))
			except discord.NotFound:
				pass

		template_code = await self.client.db.fetchrow("SELECT * FROM snapshots WHERE code = $1", template.lower())
		if template_code:
			return await ctx.send("info.template", template=await CustomTemplate.from_dict(self.client, template_code))
		raise commands.BadArgument("template")


async def setup(client: MyClient):
	await client.add_cog(Info(client))
