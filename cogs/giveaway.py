import asyncio
import discord
from discord.ext import commands
from datetime import datetime, timedelta
import random
from discord import app_commands

from helpers import CustomResponse, convert_time, FormatDateTime
from main import Context, logger
import helpers


class GiveawayView(discord.ui.View):
	def __init__(self, client: discord.Client, end_time: datetime):
		super().__init__(timeout=None)
		self.participants = set()
		self.end_time = end_time
		self.ended = False
		self.custom_response = CustomResponse(client)

	@discord.ui.button(
		label="🎉", style=discord.ButtonStyle.primary, custom_id="join_giveaway"
	)  # type: ignore
	async def join_button(
		self, interaction: discord.Interaction, button: discord.ui.Button
	):
		if self.ended:
			button.disabled = True
			await interaction.response.edit_message(view=self)  # type: ignore

			message = await self.custom_response("giveaway.message.ended", interaction)

			await interaction.followup.send(**message)
			return

		if interaction.user.id in self.participants:
			message = await self.custom_response(
				"giveaway.message.already_joined", interaction
			)

			await interaction.followup.send(**message)
			return

		self.participants.add(interaction.user.id)
		button.label = await self.custom_response(
			"giveaway.message.button", interaction, participants=len(self.participants)
		)
		await interaction.response.edit_message(view=self)  # type: ignore
		message = await self.custom_response("giveaway.message.joined", interaction)

		await interaction.followup.send(**message)

	def disable_button(self):
		self.ended = True
		self.children[0].disabled = True  # type: ignore
		self.children[0].style = discord.ButtonStyle.secondary  # type: ignore


class Giveaway(commands.Cog):
	def __init__(self, client):
		self.client = client
		self.custom_response = CustomResponse(client)
		self.active_giveaways = {}

	async def end_giveaway(
		self, ctx: Context, message_id: int, channel_id: int, right_now: bool = False
	):
		if message_id not in self.active_giveaways:
			return

		time_until_end = (
			self.active_giveaways[message_id]["end_time"] - datetime.now()
		).total_seconds()
		if time_until_end > 0 and not right_now:
			await asyncio.sleep(time_until_end)

		channel = self.client.get_channel(channel_id)
		if not channel:
			return

		try:
			message = await channel.fetch_message(message_id)
			view = self.active_giveaways[message_id]["view"]

			if view.ended:
				return

			view.disable_button()  # Disable the button when manually ending
			winners = []
			if view.participants:
				num_winners = self.active_giveaways[message_id]["winners"]
				winner_ids = random.sample(
					list(view.participants), min(num_winners, len(view.participants))
				)
				winners = [f"<@{winner_id}>" for winner_id in winner_ids]

			if winners:
				response = await self.custom_response(
					"giveaway.end.success", ctx, winners=", ".join(winners)
				)

				await message.reply(**response)
			else:
				response = await self.custom_response("giveaway.end.no_winners", ctx)
				await message.reply(**response)

			await message.edit(view=view)
			del self.active_giveaways[message_id]

		except discord.NotFound:
			if message_id in self.active_giveaways:
				del self.active_giveaways[message_id]
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
	async def giveaway(
		self, ctx: Context, duration: str, winners: str = None, *, prize: str = None
	):
		try:
			duration_dt = datetime.now() + timedelta(
				seconds=helpers.convert_time(duration)
			)
		except (ValueError, TypeError):
			# If duration parsing fails, treat everything as part of the prize
			prize = " ".join(filter(None, [duration, winners, prize]))
			winners = 1  # Default to 1 winner
			raise commands.BadArgument

		# If winners is specified, try to parse it as a number
		if winners is not None:
			try:
				winners_count = int(winners)
				if winners_count < 1:
					winners_count = 1
			except ValueError:
				# If winners isn't a valid number, treat it as part of the prize
				prize = " ".join(filter(None, [winners, prize]))
				winners_count = 1
		else:
			winners_count = 1

		# Continue with giveaway creation using duration_dt, winners_count and prize...

		if winners_count < 1 or not prize:
			raise commands.BadArgument("winners,prize")

		end_time = datetime.now() + timedelta(seconds=convert_time(duration))

		view = GiveawayView(self.client, end_time)
		message = await ctx.send(
			"giveaway.start.response",
			view=view,
			prize=prize,
			winners=winners_count,
			ends=FormatDateTime(end_time, "R"),
		)

		self.active_giveaways[message.id] = {
			"view": view,
			"end_time": end_time,
			"winners": winners_count,
		}

		self.client.loop.create_task(self.end_giveaway(ctx, message.id, ctx.channel.id))

	@giveaway.command(
		name="end", description="gw_end-description", usage="gw_end-usage"
	)
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

		view = self.active_giveaways[message_id]["view"]

		if view.ended:
			await ctx.send("giveaway.message.ended")
			return

		await self.end_giveaway(ctx, int(message_id), ctx.channel.id, False)
		await ctx.send("giveaway.end.success")


async def setup(bot):
	await bot.add_cog(Giveaway(bot))
