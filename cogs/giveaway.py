import asyncio
from typing import Optional

import discord
from discord.ext import commands
from datetime import datetime, timedelta
import random
from discord import app_commands

from helpers import CustomResponse, FormatDateTime
from main import Context, logger
import helpers


class Giveaway(commands.Cog):
	def __init__(self, client):
		self.client = client
		self.custom_response = CustomResponse(client)
		self.active_giveaways = {}
		self.GIVEAWAY_EMOJI = "🎉"

	async def load_active_giveaways(self):
		giveaways = await self.client.db.fetch("SELECT * FROM giveaways WHERE ended = FALSE")

		for giveaway in giveaways:
			end_time = giveaway["ends_at"]

			# Load all giveaways regardless of whether they're expired
			self.active_giveaways[giveaway["message_id"]] = {
				"end_time": end_time,
				"winners": giveaway["winners"],
				"channel_id": giveaway["channel_id"],
			}

			# If expired, end immediately, otherwise schedule for later
			if datetime.now() >= end_time:
				self.client.loop.create_task(
					self.end_giveaway(None, giveaway["message_id"], giveaway["channel_id"], True)
				)
			else:
				self.client.loop.create_task(self.end_giveaway(None, giveaway["message_id"], giveaway["channel_id"]))

	async def cog_load(self):
		await self.load_active_giveaways()

	async def end_giveaway(self, ctx: Context | None, message_id: int, channel_id: int, right_now: bool = False):
		if message_id not in self.active_giveaways:
			return

		time_until_end = (self.active_giveaways[message_id]["end_time"] - datetime.now()).total_seconds()
		if time_until_end > 0 and not right_now:
			await asyncio.sleep(time_until_end)

		channel = await self.client.fetch_channel(channel_id)
		if not channel:
			return

		try:
			message = await channel.fetch_message(message_id)

			# Get reaction users
			reaction: Optional[discord.Reaction] = discord.utils.get(message.reactions, emoji=self.GIVEAWAY_EMOJI)
			if not reaction:
				participants = []
			else:
				participants = [user.id async for user in reaction.users() if user.id != self.client.user.id]

			winners = []
			winner_ids = []
			if participants:
				num_winners = self.active_giveaways[message_id]["winners"]
				winner_ids = random.sample(participants, min(num_winners, len(participants)))
				winners = [f"<@{winner_id}>" for winner_id in winner_ids]

			if winners:
				response = await self.custom_response(
					"giveaway.end.success", ctx or message, winners=", ".join(winners)
				)
				await message.reply(**response)
			else:
				response = await self.custom_response("giveaway.end.no_winners", ctx or message)
				await message.reply(**response)


			await self.client.db.execute(
				"UPDATE giveaways SET ended = TRUE, won_by = $1 WHERE message_id = $2",
				winner_ids,
				message_id,
			)
			del self.active_giveaways[message_id]

		except discord.NotFound:
			await self.client.db.execute("DELETE FROM giveaways WHERE message_id = $1", message_id)
		except Exception as e:
			logger.error(f"Error ending giveaway: {e}")
			raise e

	@commands.hybrid_group(
		name="giveaway",
		description="gw_specs-description",
		usage="gw_specs-usage",
		fallback="gw_specs-fallback",
	)
	@app_commands.rename(
		winners="gw_specs-args-winners-name",
		duration="gw_specs-args-duration-name",
		prize="gw_specs-args-prize-name",
	)
	@app_commands.describe(
		winners="gw_specs-args-winners-description",
		duration="gw_specs-args-duration-description",
		prize="gw_specs-args-prize-description",
	)
	async def giveaway(self, ctx: Context, duration: str, winners: str = None, *, prize: str = None):
		try:
			end_time = datetime.now() + timedelta(seconds=helpers.convert_time(duration))
		except (ValueError, TypeError):
			raise commands.BadArgument

		if winners is not None:
			try:
				winners_count = max(int(winners), 1)
			except ValueError:
				prize = " ".join(filter(None, [winners, prize]))
				winners_count = 1
		else:
			winners_count = 1

		if winners_count < 1 or not prize:
			raise commands.BadArgument("winners,prize")

		message = await ctx.send(
			"giveaway.start.response",
			prize=prize,
			winners=winners_count,
			ends=FormatDateTime(end_time, "R"),
		)

		await message.add_reaction(self.GIVEAWAY_EMOJI)

		await self.client.db.execute(
			"INSERT INTO giveaways"
			" (guild_id, channel_id, message_id, author_id, prize, winners, ends_at, ended, won_by)"
			" VALUES ($1, $2, $3, $4, $5, $6, $7, FALSE, NULL)",
			ctx.guild.id,
			ctx.channel.id,
			message.id,
			ctx.author.id,
			prize,
			winners_count,
			end_time,
		)

		self.active_giveaways[message.id] = {
			"end_time": end_time,
			"winners": winners_count,
			"channel_id": ctx.channel.id,
		}

		self.client.loop.create_task(self.end_giveaway(ctx, message.id, ctx.channel.id))

	@giveaway.command(name="end", description="gw_end-description", usage="gw_end-usage", aliases=["reroll"])
	@app_commands.rename(message_id="gw_end-args-message_id-name")
	@app_commands.describe(message_id="gw_end-args-message_id-description")
	@commands.has_permissions(manage_guild=True)
	async def endgiveaway(self, ctx, message_id: str):
		try:
			message_id = int(message_id)
		except ValueError:
			raise commands.BadArgument("message_id")

		if message_id not in self.active_giveaways:
			raise commands.BadArgument("message_id")

		await self.end_giveaway(ctx, message_id, ctx.channel.id, True)


async def setup(bot):
	await bot.add_cog(Giveaway(bot))
