import random
from urllib.parse import quote_plus

import discord
from art import text2art
from discord import app_commands
from discord.ext import commands

from core import Context, MyClient
from helpers import CustomResponse
from helpers.convert import text_to_emoji
from helpers.regex import DISCORD_MESSAGE_URL


class Say(commands.Cog, name="Says"):
	def __init__(self, client: MyClient):
		self.client = client
		self.custom_response: CustomResponse = CustomResponse(client)

	@commands.hybrid_group(
		name="say", description="say_specs-description", fallback="say_specs-fallback", usage="say_specs-usage"
	)
	@commands.has_permissions(manage_messages=True)
	@app_commands.rename(message="say_specs-args-message-name")
	@app_commands.describe(message="say_specs-args-message-description")
	async def say(self, ctx: Context, *, message: commands.Range[str, 1, 2000]):
		await ctx.send("say.message", message=message)

	@say.command(name="channel", description="chsay_specs-description", usage="chsay_specs-usage")
	@commands.has_permissions(manage_messages=True)
	@app_commands.rename(channel="chsay_specs-args-channel-name", message="chsay_specs-args-message-name")
	@app_commands.describe(
		channel="chsay_specs-args-channel-description", message="chsay_specs-args-message-description"
	)
	async def channel_say(self, ctx: Context, channel: discord.TextChannel, *, message: commands.Range[str, 1, 2000]):
		await channel.send(message, allowed_mentions=discord.AllowedMentions.none())

	@say.command(name="edit", description="editmsg_specs-description", usage="editmsg_specs-usage")
	@commands.has_permissions(manage_messages=True)
	@app_commands.rename(message_link="editmsg_specs-args-link-name", content="editmsg_specs-args-content-name")
	@app_commands.describe(
		message_link="editmsg_specs-args-link-description", content="editmsg_specs-args-content-description"
	)
	async def edit_message(self, ctx: Context, message_link: str, *, content: commands.Range[str, 1, 2000]):
		match = DISCORD_MESSAGE_URL.search(message_link)
		try:
			if match:
				guild_id, channel_id, message_id = match.groups()
				message = await self.client.get_channel(int(channel_id)).fetch_message(int(message_id))
			else:
				message = await ctx.channel.fetch_message(int(message_link))
		except (discord.NotFound, discord.Forbidden):
			raise commands.BadArgument("message_link")
		try:
			await message.edit(content=content, allowed_mentions=discord.AllowedMentions.none())
		except discord.Forbidden:
			raise commands.MissingPermissions(["manage_messages"])
		except discord.NotFound:
			raise commands.BadArgument("message_link")
		await ctx.send("say.edit")

	@say.command(name="ascii", description="asciisay_specs-description", usage="asciisay_specs-usage")
	@commands.has_permissions(manage_messages=True)
	@app_commands.rename(message="asciisay_specs-args-message-name")
	@app_commands.describe(message="asciisay_specs-args-message-description")
	async def ascii_say(self, ctx: Context, *, message: commands.Range[str, 1, 20]):
		await ctx.send("say.ascii", ascii=text2art(message))

	@say.command(name="emoji", description="emojisay_specs-description", usage="emojisay_specs-usage")
	@commands.has_permissions(manage_messages=True)
	@app_commands.rename(message="emojisay_specs-args-message-name")
	@app_commands.describe(message="emojisay_specs-args-message-description")
	async def emoji_say(self, ctx: Context, *, message: commands.Range[str, 1, 20]):
		await ctx.send("say.emoji", emoji=" ".join(text_to_emoji(message)))

	@say.command(name="achievement", description="mcsay_specs-description", usage="mcsay_specs-usage")
	@commands.has_permissions(manage_messages=True)
	@app_commands.rename(message="mcsay_specs-args-message-name")
	@app_commands.describe(message="mcsay_specs-args-message-description")
	async def achievement_say(self, ctx: Context, *, message: commands.Range[str, 1, 50]):
		icon = random.randint(1, 29)
		localized_title = await self.custom_response("say.achievement.title", ctx)
		achievement_title = quote_plus(localized_title)
		achievement_text = quote_plus(message)
		url = f"https://skinmc.net/achievement/{icon}/{achievement_title}/{achievement_text}"
		await ctx.send("say.achievement.response", achievement=url)

	@say.command(name="qr", description="qr_specs-description", usage="qr_specs-usage")
	@commands.has_permissions(manage_messages=True)
	@app_commands.rename(data="qr_specs-args-data-name")
	@app_commands.describe(data="qr_specs-args-data-description")
	async def qr_code(self, ctx: Context, *, data: commands.Range[str, 1, 500]):
		data = quote_plus(data)
		qr = f"https://api.qrserver.com/v1/create-qr-code/?data={data}&size=1000x1000&qzone=2"
		await ctx.send("say.qr", qr=qr)

	@say.command(name="reverse", description="reversesay_specs-description", usage="reversesay_specs-usage")
	@commands.has_permissions(manage_messages=True)
	@app_commands.rename(message="reversesay_specs-args-msg-name")
	@app_commands.describe(message="reversesay_specs-args-msg-description")
	async def reverse_say(self, ctx: Context, *, message: commands.Range[str, 1, 2000]):
		await ctx.send("say.reverse", message=message[::-1])

	@say.command(name="clap", description="clapsay_specs-description", usage="clapsay_specs-usage")
	@commands.has_permissions(manage_messages=True)
	@app_commands.rename(message="clapsay_specs-args-message-name")
	@app_commands.describe(message="clapsay_specs-args-message-description")
	async def clap_say(self, ctx: Context, *, message: commands.Range[str, 1, 500]):
		await ctx.send("say.clap", message=message.replace(" ", "👏"))


async def setup(client: MyClient):
	await client.add_cog(Say(client))
