"""A helper for a pagination class."""

from typing import Optional

import discord


class Pagination(discord.ui.View):
	def __init__(
		self, pages: list[dict], user: discord.User, timeout: Optional[int] = None
	):
		self.page = 0
		self.pages = pages
		self.user = user
		super().__init__(timeout=timeout)

	async def interaction_check(self, interaction: discord.Interaction) -> bool:
		return interaction.user == self.user

	@discord.ui.button(emoji="◀️", style=discord.ButtonStyle.gray, custom_id="prev")
	async def prev_button(
		self, interaction: discord.Interaction, button: discord.ui.Button
	):
		if self.page > 0:
			self.page -= 1
		else:
			self.page = len(self.pages) - 1
		if len(self.pages) == 1:
			view = None
		else:
			view = self
		await interaction.edit_original_response(**self.pages[self.page], view=view)

	@discord.ui.button(emoji="▶️", style=discord.ButtonStyle.gray, custom_id="next")
	async def next_button(
		self, interaction: discord.Interaction, button: discord.ui.Button
	):
		if self.page < len(self.pages) - 1:
			self.page += 1
		else:
			self.page = 0
		if len(self.pages) == 1:
			view = None
		else:
			view = self
		await interaction.edit_original_response(**self.pages[self.page], view=view)


# Example:

# put the leaderboard into pages, split by 5, and display them with pagination

# pages = []
# index = 0
# n = 5
# for i in range(0, len(rows), n):
#     embed = discord.Embed(title=_("leaderboard"), color=ecolor, timestamp=datetime.datetime.now())
#     for j, row in enumerate(rows[i:i+n]):
#         user = self.client.get_user(row['user_id'])
#         if index == 0:
#             embed.description = _("leaderboard_no1_data", ctx, user=user, cash=row["cash"], bank=row["bank"])
#             index += 1
#             continue
#         number = "🥈" if index == 1 else "🥉" if index == 2 else f"#{i+j+1}"
#         embed.add_field(name=f"{number} {user.name}", value=_("leaderboard_others_data", ctx, cash=row["cash"], bank=row["bank"]), inline=False)
#         index += 1
#     embed.set_footer(text=_("page_footer", ctx, current_page=i//n+1, total_pages=len(rows)//n+1))
#     pages.append({
#         "embed": embed
#     })

# view = pagination.Pagination(pages, ctx.author)
# await ctx.reply(**pages[0], view=view)
