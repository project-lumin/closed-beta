import datetime
import sys
from typing import Literal, Optional, Union, overload
import discord

from discord import app_commands
from discord.ext import commands

from helpers import (
	CustomResponse,
	CustomMessage,
	CustomAutoModRule,
	CustomAutoModAction,
	CustomInvite,
	FormatDateTime,
	convert_to_custom_channel,
	CustomUser,
	CustomTextChannel,
)
from main import MyClient, Context


class LogCommands(commands.Cog, name="Logging"):
	def __init__(self, client: MyClient) -> None:
		self.client = client

	@commands.hybrid_group(
		name="log", fallback="log_specs-fallback", description="log_specs-description", usage="log_specs-usage"
	)
	@commands.has_permissions(manage_guild=True)
	@app_commands.rename(state="log_specs-args-state-name", channel="log_specs-args-channel-name")
	@app_commands.describe(
		state="log_specs-args-state-description",
		channel="log_specs-args-channel-description",
	)
	async def log_toggle(
		self,
		ctx: Context,
		state: Literal["on", "off"] = "on",
		channel: discord.TextChannel = None,
	):
		is_on = state == "on"
		if is_on:
			if not channel:
				raise commands.MissingRequiredArgument(ctx.command.params["channel"])
			webhook = discord.utils.get(
				await channel.webhooks(), name=f"{ctx.me.display_name} - Log"
			) or await channel.create_webhook(name=f"{ctx.me.display_name} - Log", avatar=await ctx.me.avatar.read())
		else:
			await self.client.db.execute("UPDATE log SET is_on = FALSE WHERE guild_id = $1", ctx.guild.id)
			await ctx.send("log.toggle.off")
			return

		await self.client.db.execute(
			"INSERT INTO log (guild_id, webhook, channel, is_on) VALUES ($1, $2, $3, $4)"
			" ON CONFLICT (guild_id) DO UPDATE"
			" SET webhook = excluded.webhook, channel = excluded.channel, is_on = excluded.is_on",
			ctx.guild.id,
			webhook.url,
			channel.id,
			is_on,
		)
		await ctx.send(content="log.toggle.on", channel=CustomTextChannel.from_channel(channel))

	@log_toggle.command(name="add", description="logadd_specs-description", usage="logadd_specs-usage")
	@app_commands.rename(module="logadd_specs-args-module-name")
	@app_commands.describe(module="logadd_specs-args-module-description")
	@commands.has_permissions(manage_guild=True)
	async def log_module_add(self, ctx: Context, module: str):
		if module == "all":
			await self.client.db.execute("UPDATE log SET modules = DEFAULT WHERE guild_id = $1", ctx.guild.id)
		else:
			await self.client.db.execute(
				"UPDATE log SET modules = array_append(modules, $1) WHERE guild_id = $2",
				module,
				ctx.guild.id,
			)

		await ctx.send("log.module.add", module=module)

	@log_toggle.command(name="remove", description="logremove_specs-description", usage="logremove_specs-usage")
	@app_commands.rename(module="logremove_specs-args-module-name")
	@app_commands.describe(module="logremove_specs-args-module-description")
	@commands.has_permissions(manage_guild=True)
	async def log_module_remove(self, ctx: Context, module: str):
		if module == "all":
			await self.client.db.execute("UPDATE log SET modules = ARRAY[] WHERE guild_id = $1", ctx.guild.id)
		else:
			await self.client.db.execute(
				"UPDATE log SET modules = array_remove(modules, $1) WHERE guild_id = $2",
				module,
				ctx.guild.id,
			)

		await ctx.send("log.module.remove", module=module)


class LogListeners(commands.Cog):
	def __init__(self, client: MyClient) -> None:
		self.client = client

	# TODO:
	# 'on_guild_update', 'on_guild_emojis_update', 'on_guild_stickers_update',
	# 'on_guild_integrations_update', 'on_webhooks_update', 'on_raw_integration_delete', 'on_member_join',
	# 'on_member_remove', 'on_member_update', 'on_member_ban', 'on_member_ban', 'on_member_unban',
	# 'on_message_delete', 'on_bulk_message_delete', 'on_poll_vote_add', 'on_poll_vote_remove', 'on_reaction_add',
	# 'on_reaction_remove', 'on_reaction_clear', 'on_reaction_clear_emoji', 'on_guild_role_create',
	# 'on_guild_role_delete', 'on_scheduled_event_create', 'on_scheduled_event_delete', 'on_scheduled_event_update',
	# 'on_soundboard_sound_create', 'on_soundboard_sound_delete', 'on_soundboard_sound_update',
	# 'on_stage_instance_create', 'on_stage_instance_delete', 'on_stage_instance_update', 'on_thread_create',
	# 'on_thread_join', 'on_thread_update', 'on_thread_remove', 'on_thread_delete', 'on_thread_member_join',
	# 'on_thread_member_remove', 'on_voice_state_update'

	# DONE:
	# 'on_invite_create', 'on_invite_delete', 'on_guild_channel_create', 'on_guild_channel_delete',
	# 'on_guild_channel_pins_update', 'on_guild_channel_update', 'on_automod_rule_create', 'on_automod_rule_update',
	# 'on_automod_rule_delete', 'on_automod_action', 'on_message_edit'

	@staticmethod
	async def _get_actor(
		guild: discord.Guild,
		target_id: int,
		actions: discord.AuditLogAction | int | list[discord.AuditLogAction | int],
		changed_attribute: Optional[str] = None,
	) -> Optional[CustomUser]:
		"""Retreives the actor from the audit logs for a specific action on a channel or role."""
		try:
			async for entry in guild.audit_logs(
				limit=15, action=actions if isinstance(actions, (discord.AuditLogAction, int)) else discord.abc.MISSING
			):
				target_channel_matches = False
				if (
					entry.target
					and isinstance(entry.target, (discord.abc.GuildChannel, discord.Role, discord.Member, discord.User))
					and entry.target.id == target_id
				):
					target_channel_matches = True
				if hasattr(entry.extra, "channel") and entry.extra.channel and entry.extra.channel.id == target_id:
					target_channel_matches = True

				if not target_channel_matches:
					continue

				if changed_attribute:
					if changed_attribute == "position":
						return CustomUser.from_user(entry.user)

					if hasattr(entry.changes.before, changed_attribute) or hasattr(
						entry.changes.after, changed_attribute
					):
						return CustomUser.from_user(entry.user)
					# If the attribute doesn't match, this isn't the right log entry.
					continue

				# If not looking for a specific attribute, the first match is good enough (for create/delete/permissions)
				return CustomUser.from_user(entry.user)

		except Exception as e:
			print(f"Error getting actor from audit logs: {e}")
		return None

	@staticmethod
	def _get_permission_diff_string(before_overwrites: dict, after_overwrites: dict) -> Optional[str]:
		diff_blocks = []

		before_map = {o.id: (o, p) for o, p in before_overwrites.items()}
		after_map = {o.id: (o, p) for o, p in after_overwrites.items()}
		all_target_ids = set(before_map.keys()) | set(after_map.keys())

		def get_sort_key(target_id):
			target_obj, _ = after_map.get(target_id, before_map.get(target_id))
			return -getattr(target_obj, "position", -1) if isinstance(target_obj, discord.Role) else 0

		sorted_ids = sorted(list(all_target_ids), key=get_sort_key)

		for target_id in sorted_ids:
			p_before = before_map.get(target_id, (None, None))[1]
			p_after = after_map.get(target_id, (None, None))[1]

			if p_before == p_after:
				continue

			target_obj = after_map.get(target_id, before_map.get(target_id))[0]

			before_perms = dict(iter(p_before)) if p_before else {}
			after_perms = dict(iter(p_after)) if p_after else {}

			all_perm_names = set(before_perms.keys()) | set(after_perms.keys())
			added_perms, removed_perms, reset_perms = [], [], []

			for perm in sorted(list(all_perm_names)):
				val_before = before_perms.get(perm)
				val_after = after_perms.get(perm)

				if val_before != val_after:
					perm_name = perm.replace("_", " ").title()
					if val_after:
						added_perms.append(perm_name)
					elif not val_after:
						removed_perms.append(perm_name)
					elif val_after is None:
						reset_perms.append(perm_name)

			if added_perms or removed_perms or reset_perms:
				block = [f"{target_obj.mention}"]
				if added_perms:
					block.append("```diff\n+ [{}]\n```".format(", ".join(added_perms)))
				if removed_perms:
					block.append("```diff\n- [{}]\n```".format(", ".join(removed_perms)))
				if reset_perms:
					block.append("```diff\n/ [{}]\n```".format(", ".join(reset_perms)))
				diff_blocks.append("\n".join(block))

		if not diff_blocks:
			return None

		return "\n\n".join(diff_blocks)

	async def _get_webhook(self, guild_id: int) -> Optional[discord.Webhook]:
		"""
		Retreives the webhook associated with the given ``guild_id``

		Parameters
		----------
		guild_id: `int`
			The guild's ID

		Returns
		-------
		Optional[`discord.Webhook`]
			The webhook associated with the given ``guild_id``
		"""
		webhook = await self.client.db.fetchval("SELECT webhook FROM log WHERE guild_id = $1", guild_id)
		if not webhook:
			return None
		return discord.Webhook.from_url(webhook, client=self.client)

	async def send_webhook(self, guild_id: int, event: str, **kwargs):
		"""
		Sends a message to a guild's logging webhook.

		Parameters
		----------
		kwargs
			Kwargs that will be passed during localization
		"""
		if not await self._log_check(guild_id):
			return

		# automatically retreive the name of the function that calls this function and use it as the key
		key = f"log.{sys._getframe(1).f_code.co_name}.{event}"  # type: ignore

		webhook: Optional[discord.Webhook] = await self._get_webhook(guild_id)  # type: ignore
		if not webhook:
			return

		custom_response = CustomResponse(self.client)
		message: dict | str = await custom_response.get_message(key, self.client.get_guild(guild_id), **kwargs)
		if isinstance(message, dict):
			message.pop("delete_after", None)
			message.pop("ephemeral", None)
			await webhook.send(**message)
		else:
			await webhook.send(content=message)

	@overload
	async def _log_check(self, guild: int): ...

	@overload
	async def _log_check(self, guild: discord.Guild): ...

	async def _log_check(self, guild: Union[int, discord.Guild]) -> bool:
		"""
		Returns whether the guild should receive log messages

		Parameters
		----------
		guild: Union[`int`, `discord.Guild`]
			The guild to check

		Returns
		-------
		`bool`
			Whether the guild should receive log messages
		"""
		if isinstance(guild, int):
			guild_id = guild
		elif isinstance(guild, discord.Guild):
			guild_id = guild.id

		# retrieve calling function name
		func_name = sys._getframe(1).f_code.co_name  # type: ignore

		result = await self.client.db.fetchval("SELECT is_on FROM log WHERE guild_id = $1", guild_id)
		return result

	@commands.Cog.listener()
	async def on_message_edit(self, before: discord.Message, after: discord.Message):
		if before.content != after.content:
			before = CustomMessage.from_message(before)
			before.content = before.content or " "
			await self.send_webhook(
				before.guild.id,
				"content",
				before=before,
				after=CustomMessage.from_message(after),
			)
		if before.embeds != after.embeds and len(before.embeds) != 0:
			await self.send_webhook(
				before.guild.id,
				"embeds",
				before=CustomMessage.from_message(before),
				after=CustomMessage.from_message(after),
			)
		if before.attachments != after.attachments:
			await self.send_webhook(
				before.guild.id,
				"attachments",
				before=CustomMessage.from_message(before),
				after=CustomMessage.from_message(after),
			)
		if before.pinned != after.pinned:
			await self.send_webhook(
				before.guild.id,
				"pinned",
				before=CustomMessage.from_message(before),
				after=CustomMessage.from_message(after),
			)

	@commands.Cog.listener()
	async def on_automod_rule_create(self, rule: discord.AutoModRule):
		await self.send_webhook(rule.guild.id, "create", rule=await CustomAutoModRule.from_rule(rule))

	@commands.Cog.listener()
	async def on_automod_rule_update(self, rule: discord.AutoModRule):
		await self.send_webhook(rule.guild.id, "update", rule=await CustomAutoModRule.from_rule(rule))

	@commands.Cog.listener()
	async def on_automod_rule_delete(self, rule: discord.AutoModRule):
		await self.send_webhook(rule.guild.id, "delete", rule=await CustomAutoModRule.from_rule(rule))

	@commands.Cog.listener()
	async def on_automod_action(self, execution: discord.AutoModAction):
		await self.send_webhook(
			execution.guild.id,
			"action",
			execution=CustomAutoModAction.from_action(execution),
		)

	@commands.Cog.listener()
	async def on_invite_create(self, invite: discord.Invite):
		custom_invite = CustomInvite.from_invite(invite)
		await self.send_webhook(invite.guild.id, "create", invite=custom_invite)

	@commands.Cog.listener()
	async def on_invite_delete(self, invite: discord.Invite):
		if not invite.guild:
			return

		actor = None
		found_entry = None
		async for entry in invite.guild.audit_logs(action=discord.AuditLogAction.invite_delete, limit=5):  # type: ignore
			# deletion data is useless for invites by itself, so we parse the 'before' state
			if entry.before.code == invite.code:
				actor = CustomUser.from_user(entry.user) if entry.user else None
				found_entry = entry
				break

		if found_entry:
			custom_invite = CustomInvite.from_audit_log_diff(found_entry.before)
			custom_invite._inviter = actor
			await self.send_webhook(invite.guild.id, "delete", invite=custom_invite)

	@commands.Cog.listener()
	async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
		custom_channel = convert_to_custom_channel(channel)
		if custom_channel:
			created_by = await self._get_actor(channel.guild, channel.id, discord.AuditLogAction.channel_create)
			await self.send_webhook(channel.guild.id, "create", channel=custom_channel, created_by=created_by)

	@commands.Cog.listener()
	async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
		custom_channel = convert_to_custom_channel(channel)
		if custom_channel:
			deleted_by = None
			async for entry in channel.guild.audit_logs(limit=5, action=discord.AuditLogAction.channel_delete):  # type: ignore
				if entry.before.name == channel.name and entry.before.type == channel.type:
					deleted_by = CustomUser.from_user(entry.user)
					break
			await self.send_webhook(channel.guild.id, "delete", channel=custom_channel, deleted_by=deleted_by)

	@commands.Cog.listener()
	async def on_guild_channel_pins_update(
		self,
		channel: Union[discord.TextChannel, discord.VoiceChannel, discord.Thread],
		last_pin: Optional[datetime.datetime],
	):
		custom_channel = convert_to_custom_channel(channel)
		if custom_channel:
			await self.send_webhook(
				channel.guild.id,
				"pins",
				channel=custom_channel,
				last_pin=FormatDateTime(last_pin, "R") if last_pin else None,
			)

	@commands.Cog.listener()
	async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
		custom_before = convert_to_custom_channel(before)
		custom_after = convert_to_custom_channel(after)

		if not custom_before or not custom_after:
			return

		attributes_to_check = ["name", "topic", "nsfw", "slowmode_delay"]
		for attr in attributes_to_check:
			if hasattr(custom_before, attr) and hasattr(custom_after, attr):
				if getattr(custom_before, attr) != getattr(custom_after, attr):
					updated_by = await self._get_actor(
						after.guild, after.id, discord.AuditLogAction.channel_update, changed_attribute=attr
					)
					await self.send_webhook(
						before.guild.id, attr, before=custom_before, after=custom_after, updated_by=updated_by
					)

		if custom_before.name != custom_after.name:
			updated_by = await self._get_actor(
				after.guild, after.id, discord.AuditLogAction.channel_update, changed_attribute="name"
			)
			await self.send_webhook(
				before.guild.id, "name", before=custom_before, after=custom_after, updated_by=updated_by
			)
		if custom_before.topic != custom_after.topic:
			updated_by = await self._get_actor(
				after.guild, after.id, discord.AuditLogAction.channel_update, changed_attribute="topic"
			)
			await self.send_webhook(
				before.guild.id, "topic", before=custom_before, after=custom_after, updated_by=updated_by
			)
		if custom_before.nsfw != custom_after.nsfw:
			updated_by = await self._get_actor(
				after.guild, after.id, discord.AuditLogAction.channel_update, changed_attribute="nsfw"
			)
			await self.send_webhook(
				before.guild.id, "nsfw", before=custom_before, after=custom_after, updated_by=updated_by
			)
		if custom_before.slowmode_delay != custom_after.slowmode_delay:
			updated_by = await self._get_actor(
				after.guild, after.id, discord.AuditLogAction.channel_update, changed_attribute="slowmode_delay"
			)
			await self.send_webhook(
				before.guild.id, "slowmode", before=custom_before, after=custom_after, updated_by=updated_by
			)
		if custom_before.position != custom_after.position:
			await self.send_webhook(before.guild.id, "position", before=custom_before, after=custom_after)

		if before.overwrites != after.overwrites:
			actions_to_check = [
				discord.AuditLogAction.overwrite_create,
				discord.AuditLogAction.overwrite_update,
				discord.AuditLogAction.overwrite_delete,
			]
			updated_by = await self._get_actor(after.guild, after.id, actions_to_check)
			diff_string = self._get_permission_diff_string(before.overwrites, after.overwrites)
			if diff_string:
				await self.send_webhook(
					before.guild.id, "permissions", diff=diff_string, updated_by=updated_by, channel=custom_after
				)


async def setup(client: MyClient) -> None:
	await client.add_cog(LogCommands(client))
	await client.add_cog(LogListeners(client))
