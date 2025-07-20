import random

import discord
from discord import app_commands
from discord.ext import commands

from helpers import custom_response, random_helper
from helpers.custom_args import CustomRole, CustomUser, CustomMember
from main import MyClient, Context
from typing import Literal, Optional, Union


class ShopItem:
	def __init__(self, name: str, price: int, description: str, role: discord.Role):
		"""Create a new shop item.

		Parameters
		----------
		name: `str`
		        The name of the item.
		price: `int`
		        The price of the item.
		description: `str`
		        The description of the item.
		role: `discord.Role`
		        The role that is given to the user when they buy the item.
		"""
		self._name = name
		self._price = price
		self._description = description
		self._role = CustomRole.from_role(role)

	@property
	def name(self) -> str:
		"""The name of the item."""
		return self._name

	@property
	def price(self) -> int:
		"""The price of the item."""
		return self._price

	@property
	def description(self) -> str:
		"""The description of the item."""
		return self._description

	@property
	def role(self) -> CustomRole:
		"""The role that is given to the user when they buy the item."""
		return self._role

	def __str__(self) -> str:
		return self.name

	def __int__(self) -> int:
		return self.price


class EconomyHelper:
	def __init__(self, client):
		self.client: MyClient = client

	async def add_money(
		self,
		user_id: int,
		guild_id: int,
		amount: int,
		wallet: Literal["cash", "bank"] = "cash",
	) -> int:
		"""
		Add money to a user's balance.

		Parameters
		----------
		user_id: `int`
		        The user's ID.
		guild_id: `int`
		        The guild's ID.
		amount: `int`
		        The amount to add to the user's balance.
		wallet: Literal[`"cash"`, `"bank"`], optional
		        Whether to use the cash or bank wallet. Defaults to `cash`. If the user is in debt, it will always use the cash wallet.

		Returns
		-------
		`int`
		        The user's new balance.
		"""
		cash, bank = await self.get_balance(user_id, guild_id, None)

		if bank < 0:
			need = abs(bank)
			amount -= need
			await self.remove_money(user_id, guild_id, -need, "bank")

		if wallet == "cash":
			await self.client.db.execute(
				"UPDATE economy SET cash = $1 WHERE user_id = $2 AND guild_id = $3",
				cash + amount,
				user_id,
				guild_id,
			)
			return cash + amount
		else:
			await self.client.db.execute(
				"UPDATE economy SET bank = $1 WHERE user_id = $2 AND guild_id = $3",
				bank + amount,
				user_id,
				guild_id,
			)
			return bank + amount

	async def remove_money(
		self,
		user_id: int,
		guild_id: int,
		amount: int,
		wallet: Literal["cash", "bank"] = "cash",
	) -> int:
		"""
		Remove money from a user's balance.

		Parameters
		----------
		user_id: `int`
		        The user's ID.
		guild_id: `int`
		        The guild's ID.
		amount: `int`
		        The amount to remove from the user's balance.
		wallet: Literal[`"cash"`, `"bank"`]
		        Whether to use the cash or bank wallet. Defaults to `cash`.

		Returns
		-------
		`int`
		        The user's new balance.

		Raises
		------
		ValueError
		        If the user doesn't have enough money in the cash wallet.
		"""
		cash, bank = await self.get_balance(user_id, guild_id, None)

		if wallet == "cash":
			if cash - amount < 0:
				raise ValueError("Not enough money")
			await self.client.db.execute(
				"UPDATE economy SET cash = $1 WHERE user_id = $2 AND guild_id = $3",
				cash - amount,
				user_id,
				guild_id,
			)
			return int(cash - amount)
		else:
			await self.client.db.execute(
				"UPDATE economy SET bank = $1 WHERE user_id = $2 AND guild_id = $3",
				bank - amount,
				user_id,
				guild_id,
			)
			return int(bank - amount)

	async def get_balance(
		self,
		user_id: int,
		guild_id: int,
		wallet: Optional[Literal["cash", "bank"]] = "cash",
	) -> Union[int, tuple[int, int]]:
		"""
		Get a user's balance.

		Parameters
		----------
		user_id: `int`
		        The user's ID.
		guild_id: `int`
		        The guild's ID.
		wallet: Optional[Literal[`"cash"`, `"bank"`]]
		        Whether to get the cash or bank balance. Defaults to `cash`. If `None`, returns a tuple of both balances.

		Returns
		-------
		Union[`int`, tuple[`int`]]
		        The user's cash or bank balance, or a tuple of both balances.
		"""
		try:
			await self.register_user(user_id, guild_id)
			return (0, 0) if wallet is None else 0
		except ValueError:
			pass

		match wallet:
			case "cash":
				balance = await self.client.db.fetchval(
					"SELECT cash FROM economy WHERE user_id = $1 AND guild_id = $2",
					user_id,
					guild_id,
				)
			case "bank":
				balance = await self.client.db.fetchval(
					"SELECT bank FROM economy WHERE user_id = $1 AND guild_id = $2",
					user_id,
					guild_id,
				)
			case _:
				row = await self.client.db.fetchrow(
					"SELECT * FROM economy WHERE user_id = $1 AND guild_id = $2",
					user_id,
					guild_id,
				)
				return int(row["cash"]), int(row["bank"])
		return int(balance)

	async def register_user(self, user_id: int, guild_id: int) -> None:
		"""
		Registers a user in the database.

		Parameters
		----------
		user_id: `int`
		        The user's ID.
		guild_id: `int`
		        The guild's ID.

		Raises
		------
		ValueError
		        If the user is already in the database.
		"""
		row = await self.client.db.fetchrow(
			"SELECT * FROM economy WHERE user_id = $1 AND guild_id = $2",
			user_id,
			guild_id,
		)
		if not row:
			await self.client.db.execute(
				"INSERT INTO economy(user_id, guild_id) VALUES($1, $2)",
				user_id,
				guild_id,
			)
		else:
			raise ValueError("User already registered ({} @ {})".format(user_id, guild_id))

	async def set_balance(
		self,
		user_id: int,
		guild_id: int,
		amount: int,
		wallet: Literal["cash", "bank"] = "cash",
	) -> None:
		"""
		Sets the balance of a user.

		Parameters
		----------
		user_id: `int`
		        The user's ID.
		guild_id: `int`
		        The guild's ID.
		amount: `int`
		        The amount to set the user's balance to.
		wallet: Literal[`"cash"`, `"bank"`]
		        The wallet to set the balance of. Defaults to cash.
		"""
		row = await self.client.db.fetchrow(
			"SELECT * FROM economy WHERE user_id = $1 AND guild_id = $2",
			user_id,
			guild_id,
		)
		if not row:
			if wallet == "cash":
				await self.client.db.execute(
					"INSERT INTO economy(user_id, guild_id, cash) VALUES($1, $2, $3)",
					user_id,
					guild_id,
					amount,
				)
			else:
				await self.client.db.execute(
					"INSERT INTO economy(user_id, guild_id, bank) VALUES($1, $2, $3)",
					user_id,
					guild_id,
					amount,
				)
		if wallet == "cash":
			await self.client.db.execute(
				"UPDATE economy SET cash = $1 WHERE user_id = $2 AND guild_id = $3",
				amount,
				user_id,
				guild_id,
			)
		else:
			await self.client.db.execute(
				"UPDATE economy SET bank = $1 WHERE user_id = $2 AND guild_id = $3",
				amount,
				user_id,
				guild_id,
			)


@app_commands.guild_only()
@commands.guild_only()
class Economy(commands.GroupCog, name="Economy", group_name="economy"):
	def __init__(self, client):
		self.client: MyClient = client
		self.helper = EconomyHelper(client)
		self.custom_response = custom_response.CustomResponse(client)

	@commands.hybrid_command(name="leaderboard", description="leaderboard_specs-description")
	async def leaderboard(self, ctx: commands.Context):
		rows = await self.client.db.fetch(
			"SELECT * FROM economy WHERE guild_id = $1 ORDER BY cash+bank DESC LIMIT 10",
			ctx.guild.id,
		)
		message: dict = await self.custom_response("leaderboard", ctx)
		embeds: list[discord.Embed] = message.get("embeds")
		if not rows:
			if embeds:
				embeds[0].remove_field(0)
			return await ctx.send(**message)

		if embeds:
			template = embeds[0].to_dict().get("fields", [None])[0]
			if not template:
				return await ctx.send(**message)
			embeds[0].clear_fields()
			for i in rows:
				user = CustomUser.from_user(self.client.get_user(i["user_id"]))
				number = rows.index(i) + 1
				cash, bank = await self.helper.get_balance(i["user_id"], ctx.guild.id, wallet=None)
				formatted = discord.ext.localization.Localization.format_strings(
					template, user=user, number=number, cash=cash, bank=bank
				)
				embeds[0].add_field(**formatted)
			message["embeds"] = custom_response.CustomResponse.convert_embeds(embeds)

		await ctx.send(**message)

	@commands.hybrid_command(name="work", description="work_specs-description")
	@commands.cooldown(1, 3600, commands.BucketType.user)
	async def work(self, ctx: Context):
		amount: int = random.randint(300, 1500)
		await self.helper.add_money(ctx.author.id, ctx.guild.id, amount)

		await ctx.send("work", amount=amount)

	@commands.hybrid_command(name="crime", description="crime_specs-description")
	async def crime(self, ctx: Context):
		amount = random.randint(500, 2000)
		await self.helper.add_money(ctx.author.id, ctx.guild.id, amount)

		await ctx.send("crime", amount=amount)

	@commands.hybrid_command(name="daily", description="daily_specs-description")
	@commands.cooldown(1, 86400, commands.BucketType.user)
	async def daily(self, ctx: Context):
		amount = 5000
		await self.helper.add_money(ctx.author.id, ctx.guild.id, amount)

		await ctx.send("allowance", amount=amount)

	@app_commands.rename(member="global-member", amount="global-amount", account="global-account")
	@app_commands.describe(
		member="addmoney_specs-args-member-description",
		amount="addmoney_specs-args-amount-description",
		account="addmoney_specs-args-account-description",
	)
	@app_commands.choices(
		account=[
			app_commands.Choice(name="global-cash", value="cash"),
			app_commands.Choice(name="global-bank", value="bank"),
		]
	)
	@commands.hybrid_command(
		name="addmoney",
		description="addmoney_specs-description",
		usage="addmoney_specs-usage",
	)
	@app_commands.checks.has_permissions(administrator=True)
	@commands.has_permissions(administrator=True)
	async def addmoney(
		self,
		ctx: Context,
		member: discord.Member,
		amount: commands.Range[int, 1],
		account: Literal["cash", "bank"] = "cash",
	):
		if amount > 0:
			await self.helper.add_money(member.id, ctx.guild.id, amount, account)

			await ctx.send(
				"addmoney.success",
				amount=amount,
				member=CustomMember.from_member(member),
			)
		else:
			await ctx.send("addmoney.errors.positive")

	@app_commands.rename(member="global-member", amount="global-amount", account="global-account")
	@app_commands.describe(
		member="removemoney_specs-args-member-description",
		amount="removemoney_specs-args-amount-description",
		account="removemoney_specs-args-account-description",
	)
	@app_commands.choices(
		account=[
			app_commands.Choice(name="global-cash", value="cash"),
			app_commands.Choice(name="global-bank", value="bank"),
		]
	)
	@commands.hybrid_command(
		name="removemoney",
		description="removemoney_specs-description",
		usage="removemoney_specs-usage",
	)
	@app_commands.checks.has_permissions(administrator=True)
	@commands.has_permissions(administrator=True)
	async def removemoney(
		self,
		ctx: Context,
		member: discord.Member,
		amount: discord.app_commands.Range[int, 1],
		account: Literal["cash", "bank"] = "cash",
	):
		if amount > 0:
			try:
				await self.helper.remove_money(member.id, ctx.guild.id, amount, account)
			except ValueError:
				await ctx.send("removemoney.errors.balance")

			await ctx.send("removemoney.success", amount=amount, member=member)
		else:
			await ctx.send("removemoney.errors.positive")

	@commands.hybrid_command(name="luck", description="luck_specs-description")
	@commands.cooldown(1, 3600, commands.BucketType.user)
	async def luck(self, ctx: Context):
		balance = await self.helper.get_balance(ctx.author.id, ctx.guild.id)
		minimum_balance = 1000
		if balance < minimum_balance:
			await ctx.send("luck.errors.balance", amount=minimum_balance)

		amount = random.randint(200, 1000)
		if balance - amount < 0:
			await ctx.send("luck.errors.balance", amount=minimum_balance)

		won = random_helper.randbool()
		if won:
			await self.helper.add_money(ctx.author.id, ctx.guild.id, amount)
			await ctx.send("luck.win", amount=amount)
		else:
			await self.helper.remove_money(ctx.author.id, ctx.guild.id, amount)
			await ctx.send("luck.lose", amount=amount)

	@app_commands.rename(member="global-member", amount="global-amount")
	@app_commands.describe(
		member="pay_specs-args-member-description",
		amount="pay_specs-args-amount-description",
	)
	@commands.hybrid_command(name="pay", description="pay_specs-description", usage="pay_specs-usage")
	async def pay(
		self,
		ctx: Context,
		member: discord.Member,
		amount: discord.app_commands.Range[int, 1],
	):
		if amount < 1:
			return await ctx.send("pay.errors.positive")
		if member == ctx.author:
			return await ctx.send(content="??? xd")

		author_balance = await self.helper.get_balance(ctx.author.id, ctx.guild.id)
		if author_balance < amount:
			return await ctx.send("pay.errors.balance")

		await self.helper.add_money(member.id, ctx.guild.id, amount)
		await self.helper.remove_money(ctx.author.id, ctx.guild.id, amount)

		await ctx.send("pay.success", amount=amount, member=CustomMember.from_member(member))

	@app_commands.rename(member="global-member")
	@app_commands.describe(member="balance_specs-args-member-description")
	@commands.hybrid_command(
		name="balance",
		description="balance_specs-description",
		usage="balance_specs-usage",
		aliases=["bal"],
	)
	async def balance(self, ctx: Context, member: Optional[discord.Member]):
		member = member or ctx.author
		cash, bank = await self.helper.get_balance(member.id, ctx.guild.id, wallet=None)

		message: dict = await self.custom_response("balance", ctx, member=member, cash=cash, bank=bank)

		if bank >= 0:
			if message.get("embeds"):  # remove the debt alert embed field
				for index, embed in enumerate(message["embeds"]):
					if len(embed.fields) > 2:
						message["embeds"][index].remove_field(2)

		await ctx.send(content="", **message)

	@app_commands.rename(bet="slots_specs-args-bet-name")
	@app_commands.describe(bet="slots_specs-args-bet-description")
	@commands.hybrid_command(name="slots", description="slots_specs-description", usage="slots_specs-usage")
	@commands.cooldown(1, 3600, commands.BucketType.user)
	async def slots(self, ctx: Context, bet: int):
		balance = await self.helper.get_balance(ctx.author.id, ctx.guild.id)

		if bet > balance or balance < 0:
			return await ctx.send("slots.errors.balance")

		bet = bet * 2

		slots_choices = ["🍇", "🍉", "🍊", "🍋"]
		results = [random.choice(slots_choices) for _ in range(3)]

		if results.count(results[0]) == len(results):
			await self.helper.add_money(ctx.author.id, ctx.guild.id, bet)
			await ctx.send("slots.win", results=" ".join(results), amount=bet)
		else:
			try:
				new_balance = await self.helper.remove_money(ctx.author.id, ctx.guild.id, bet)
			except ValueError:
				new_balance = await self.helper.set_balance(ctx.author.id, ctx.guild.id, balance - bet, "bank")

			message: dict = await self.custom_response(
				"slots.lose",
				ctx,
				convert_embeds=False,
				results=" ".join(results),
				amount=bet,
			)
			if new_balance >= 0:  # remove the debt alert embed field
				if message.get("embeds"):
					for index, embed in enumerate(message["embeds"]):
						if len(embed.fields) > 2:
							message["embeds"][index].remove_field(2)

			await ctx.send(**message)

	@app_commands.rename(amount="global-amount")
	@app_commands.describe(amount="deposit_specs-args-amount-description")
	@commands.hybrid_command(
		name="deposit",
		description="deposit_specs-description",
		usage="deposit_specs-usage",
	)
	async def deposit(self, ctx: Context, amount: discord.app_commands.Range[int, 1] = None):
		cash, bank = await self.helper.get_balance(ctx.author.id, ctx.guild.id, wallet=None)
		amount = amount or cash
		try:
			amount = int(amount)
		except ValueError:
			if amount.lower() in await self.custom_response("deposit.all", ctx):
				amount = cash
			else:
				return await ctx.send("deposit.errors.invalid_amount")

		if amount < 1:
			return await ctx.send("deposit.errors.invalid_amount")

		if cash < amount:
			return await ctx.send("deposit.errors.balance")

		await self.helper.remove_money(ctx.author.id, ctx.guild.id, amount, "cash")
		await self.helper.add_money(ctx.author.id, ctx.guild.id, amount, "bank")

		await ctx.send("deposit.success", amount=amount)

	@app_commands.rename(amount="global-amount")
	@app_commands.describe(amount="withdraw_specs-args-amount-description")
	@commands.hybrid_command(
		name="withdraw",
		description="withdraw_specs-description",
		usage="withdraw_specs-usage",
	)
	async def withdraw(self, ctx: Context, amount: discord.app_commands.Range[int, 1] = None):
		cash, bank = await self.helper.get_balance(ctx.author.id, ctx.guild.id, wallet=None)
		amount = amount or bank
		try:
			amount = int(amount)
		except ValueError:
			if amount.lower() in await self.custom_response("withdraw.all", ctx):
				amount = bank
			else:
				return await ctx.send("withdraw.errors.invalid_amount")

		if amount < 1:
			return await ctx.send("withdraw.errors.invalid_amount")

		if bank < amount:
			return await ctx.send("withdraw.errors.balance")

		await self.helper.remove_money(ctx.author.id, ctx.guild.id, amount, "bank")
		await self.helper.add_money(ctx.author.id, ctx.guild.id, amount, "cash")

		await ctx.send("withdraw.success", amount=amount)


class Shop(commands.Cog, name="Shop"):
	def __init__(self, client):
		self.client: MyClient = client
		self.helper = EconomyHelper(client)
		self.custom_response = custom_response.CustomResponse(client, name="shop")

	@commands.hybrid_group(
		name="shop",
		description="shop_specs-description",
		fallback="shop_specs-fallback",
	)
	async def shop(self, ctx: Context):
		row = await self.client.db.fetch("SELECT * FROM shop WHERE guild_id = $1", str(ctx.guild.id))
		if not row:
			return await ctx.send("shop.list.empty")

		message: dict = await self.custom_response.get_message("shop.list.show", ctx)
		embeds: list[discord.Embed] = message.get("embeds")
		if message.get("embeds"):
			template = embeds[0].to_dict().get("fields", [None])[0]
			if not template:
				return await ctx.send(**message)
			embeds[0].clear_fields()
			for i in row:
				role = ctx.guild.get_role(i["role"])
				if not role:
					continue
				item = ShopItem(i["item_name"], i["item_price"], i["item_description"], role)
				formatted = discord.ext.localization.Localization.format_strings(template, item=item)
				embeds[0].add_field(**formatted)
			message["embeds"] = custom_response.CustomResponse.convert_embeds(embeds)

		await ctx.send(**message)

	@shop.command(name="buy", description="buy_specs-description", usage="buy_specs-usage")
	@app_commands.rename(item="buy_specs-args-item-name")
	@app_commands.describe(item="buy_specs-args-item-description")
	async def buy(self, ctx: Context, item: str):
		row = await self.client.db.fetchrow(
			"SELECT * FROM shop WHERE guild_id = $1 AND LOWER(item_name) = $2",
			ctx.guild.id,
			item.lower(),
		)
		if not row:
			return await ctx.send("shop.buy.errors.not_found")

		item = ShopItem(
			row["item_name"],
			row["item_price"],
			row["item_description"],
			ctx.guild.get_role(row["role"]),
		)
		if not item.role:
			return await ctx.send("shop.buy.errors.role_not_found")

		user_balance = await self.helper.get_balance(ctx.author.id, ctx.guild.id)
		if user_balance < item.price:
			return await ctx.send("shop.buy.errors.balance")

		await ctx.author.add_roles(item.role)
		await self.helper.remove_money(ctx.author.id, ctx.guild.id, item.price)

		await ctx.send("shop.buy.success", item=item)

	@shop.command(
		name="set_item",
		description="set_item_specs-description",
		usage="set_item_specs-usage",
	)
	@app_commands.rename(
		item="global-item",
		price="global-price",
		role="global-role",
		description="global-description",
	)
	@app_commands.describe(
		item="set_item_specs-args-item-description",
		price="set_item_specs-args-price-description",
		role="set_item_specs-args-role-description",
		description="set_item_specs-args-description-description",
	)
	@app_commands.checks.has_permissions(manage_guild=True, manage_roles=True)
	@commands.has_permissions(manage_guild=True, manage_roles=True)
	async def set_item(self, ctx: Context, item: str, price: int, description: str, role: discord.Role):
		row = await self.client.db.fetchrow(
			"SELECT * FROM shop WHERE guild_id = $1 AND LOWER(item_name) = $2",
			str(ctx.guild.id),
			item.lower(),
		)
		if row:
			return await ctx.send("shop.set.errors.already_item")

		items = await self.client.db.fetch("SELECT * FROM shop WHERE guild_id = $1", ctx.guild.id)
		if len(items) + 1 >= 10:
			return await ctx.send("shop.set.errors.limit")

		if ctx.author.top_role.position <= role.position:
			return await ctx.send("shop.set.errors.role_higher")

		await self.client.db.execute(
			"INSERT INTO shop(item_name, item_description, item_price, role, guild_id, creator_id) VALUES($1, $2, $3, $4, $5, $6)",
			item,
			description,
			price,
			role.id,
			ctx.guild.id,
			ctx.author.id,
		)

		item = ShopItem(item, price, description, role)
		await ctx.send("shop.set.success", item=item)

	@shop.command(
		name="remove_item",
		description="remove_item_specs-description",
		usage="remove_item_specs-usage",
	)
	@app_commands.rename(item="global-item")
	@app_commands.describe(item="remove_item_specs-args-item-description")
	@app_commands.checks.has_permissions(manage_guild=True)
	async def remove_item(self, ctx: Context, item: str):
		row = await self.client.db.fetchrow(
			"SELECT * FROM shop WHERE guild_id = $1 AND LOWER(item_name) = $2",
			ctx.guild.id,
			item.lower(),
		)
		if not row:
			return await ctx.send("shop.remove.errors.not_found")

		item = ShopItem(
			row["item_name"],
			row["item_price"],
			row["item_description"],
			ctx.guild.get_role(row["role"]),
		)
		if ctx.author.top_role.position <= item.role.position:
			return await ctx.send("shop.remove.errors.role_higher")

		await self.client.db.execute(
			"DELETE FROM shop WHERE guild_id = $1 AND LOWER(item_name) = $2",
			ctx.guild.id,
			item.name.lower(),
		)
		await ctx.send("shop.remove.success", item=item)


async def setup(client: MyClient):
	await client.add_cog(Economy(client))
	await client.add_cog(Shop(client))
