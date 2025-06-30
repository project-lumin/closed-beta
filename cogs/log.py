import sys
from typing import Iterable, Union, Optional
from datetime import datetime

from discord import app_commands

from helpers import *
from main import MyClient, Context

class LogCommands(commands.GroupCog, name="log"):
	def __init__(self, client: MyClient) -> None:
		self.client = client

	@commands.hybrid_group(name="log", fallback="log-specs_fallback", description="log-specs_description")
	@commands.has_permissions(manage_guild=True)
	@app_commands.checks.has_permissions(manage_guild=True)
	async def log_toggle(self, ctx: Context, state: Literal["on", "off"] = "on", channel: discord.TextChannel = None):
		is_on = state == "on"
		if is_on:
			if not channel:
				raise commands.MissingRequiredArgument(ctx.command.params["channel"])
			webhook = discord.utils.get(
				await channel.webhooks(), name=f"{ctx.me.display_name} - Log"
			) or await channel.create_webhook(
				name=f"{ctx.me.display_name} - Log", avatar=await ctx.me.avatar.read()
			)
		else:
			await self.client.db.execute("UPDATE log SET is_on = FALSE WHERE guild_id = $1", ctx.guild.id)
			await ctx.send("log.toggle.off")
			return

		await self.client.db.execute(
			"INSERT INTO log (guild_id, webhook, channel, is_on) VALUES ($1, $2, $3, $4)"
			" ON CONFLICT (guild_id) DO UPDATE"
			" SET webhook = excluded.webhook, channel = excluded.channel, is_on = excluded.is_on", ctx.guild.id,
			webhook.url, channel.id, is_on
		)
		await ctx.send(content="log.toggle.on")

	@log_toggle.command(name="add")
	async def log_module_add(self, ctx: Context, module: str):
		if module == "all":
			await self.client.db.execute(
				"UPDATE log SET modules = DEFAULT WHERE guild_id = $1", ctx.guild.id
			)
		else:
			await self.client.db.execute(
				"UPDATE log SET modules = array_append(modules, $1) WHERE guild_id = $2",
				module, ctx.guild.id
			)

		await ctx.send("log.module.add")

	@log_toggle.command(name="remove")
	async def log_module_remove(self, ctx: Context, module: str):
		if module == "all":
			await self.client.db.execute(
				"UPDATE log SET modules = ARRAY[] WHERE guild_id = $1", ctx.guild.id
			)
		else:
			await self.client.db.execute(
				"UPDATE log SET modules = array_remove(modules, $1) WHERE guild_id = $2",
				module, ctx.guild.id
			)

		await ctx.send("log.module.add")

class LogListeners(commands.Cog):
	def __init__(self, client: MyClient) -> None:
		self.client = client

	# TODO:
	# 'on_guild_update', 'on_guild_emojis_update', 'on_guild_stickers_update', 
	# 'on_guild_integrations_update', 'on_webhooks_update', 'on_raw_integration_delete', 'on_member_join',
	# 'on_member_remove', 'on_member_update', 'on_member_ban', 'on_member_ban', 'on_member_unban', 'on_message_edit',
	# 'on_message_delete', 'on_bulk_message_delete', 'on_poll_vote_add', 'on_poll_vote_remove', 'on_reaction_add',
	# 'on_reaction_remove', 'on_reaction_clear', 'on_reaction_clear_emoji', 'on_guild_role_create',
	# 'on_guild_role_delete', 'on_scheduled_event_create', 'on_scheduled_event_delete', 'on_scheduled_event_update',
	# 'on_soundboard_sound_create', 'on_soundboard_sound_delete', 'on_soundboard_sound_update',
	# 'on_stage_instance_create', 'on_stage_instance_delete', 'on_stage_instance_update', 'on_thread_create',
	# 'on_thread_join', 'on_thread_update', 'on_thread_remove', 'on_thread_delete', 'on_thread_member_join',
	# 'on_thread_member_remove', 'on_voice_state_update'

	# DONE:

	async def _get_custom_channel(self, channel: discord.abc.GuildChannel):
		if isinstance(channel, discord.TextChannel):
			return CustomTextChannel.from_channel(channel)
		elif isinstance(channel, discord.VoiceChannel):
			return CustomVoiceChannel.from_channel(channel)
		elif isinstance(channel, discord.CategoryChannel):
			return CustomCategoryChannel.from_category(channel)
		elif isinstance(channel, discord.ForumChannel):
			return CustomForumChannel.from_channel(channel)
		elif isinstance(channel, discord.StageChannel):
			return CustomStageChannel.from_channel(channel)
		return None

	async def _get_actor_string(self, guild: discord.Guild, target_id: int, actions: list[discord.AuditLogAction], changed_attribute: Optional[str] = None) -> str:
		"""Gets the actor's ID and formats it into a string for the logs."""
		try:
			async for entry in guild.audit_logs(limit=15):
				if entry.action not in actions:
					continue

				# Check if the entry is for the correct channel
				target_channel_matches = False
				if entry.target and isinstance(entry.target, (discord.abc.GuildChannel, discord.Role, discord.Member, discord.User)) and entry.target.id == target_id:
					target_channel_matches = True
				elif hasattr(entry.extra, 'channel') and entry.extra.channel and entry.extra.channel.id == target_id:
					target_channel_matches = True

				if not target_channel_matches:
					continue

				# If we are looking for a specific attribute change, check for it.
				if changed_attribute:
					# Position updates are not reliably logged with a specific change key,
					# so we'll just grab the most recent channel_update entry.
					if changed_attribute == 'position':
						return f" by <@{entry.user.id}>"

					if hasattr(entry.changes.before, changed_attribute) or hasattr(entry.changes.after, changed_attribute):
						return f" by <@{entry.user.id}>"
					# If the attribute doesn't match, this isn't the right log entry.
					continue
				
				# If not looking for a specific attribute, the first match is good enough (for create/delete/permissions)
				return f" by <@{entry.user.id}>"

		except Exception as e:
			print(f"Error getting actor from audit logs: {e}")
		return ""

	def _get_permission_diff_string(self, before_overwrites: dict, after_overwrites: dict) -> Optional[str]:
		diff_blocks = []
		
		before_map = {o.id: (o, p) for o, p in before_overwrites.items()}
		after_map = {o.id: (o, p) for o, p in after_overwrites.items()}
		all_target_ids = set(before_map.keys()) | set(after_map.keys())

		def get_sort_key(target_id):
			target_obj, _ = after_map.get(target_id, before_map.get(target_id))
			return -getattr(target_obj, 'position', -1) if isinstance(target_obj, discord.Role) else 0

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
					perm_name = perm.replace('_', ' ').title()
					if val_after is True:
						added_perms.append(perm_name)
					elif val_after is False:
						removed_perms.append(perm_name)
					elif val_after is None:
						reset_perms.append(perm_name)
			
			if added_perms or removed_perms or reset_perms:
				block = [f"For {target_obj.mention}:"]
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

	@commands.Cog.listener()
	async def on_automod_rule_create(self, rule: discord.AutoModRule):
		await self.send_webhook(
			rule.guild.id, "create", rule=await CustomAutoModRule.from_rule(rule)
		)

	@commands.Cog.listener()
	async def on_automod_rule_update(self, rule: discord.AutoModRule):
		await self.send_webhook(
			rule.guild.id, "update", rule=await CustomAutoModRule.from_rule(rule)
		)

	@commands.Cog.listener()
	async def on_automod_rule_delete(self, rule: discord.AutoModRule):
		await self.send_webhook(
			rule.guild.id, "delete", rule=await CustomAutoModRule.from_rule(rule)
		)

	@commands.Cog.listener()
	async def on_automod_action(self, execution: 'discord.AutoModAction'):
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
		
		actor_id = None
		found_entry = None
		async for entry in invite.guild.audit_logs(action=discord.AuditLogAction.invite_delete, limit=5):
			# The invite object from the event is sparse. The audit log 'before' object has the real data.
			if hasattr(entry.before, 'code') and entry.before.code == invite.code:
				actor_id = entry.user.id
				found_entry = entry
				break
		
		# If we found the audit log entry, use its data. Otherwise, we can't log anything useful.
		if found_entry:
			# Use the invite object from the audit log's 'before' state.
			custom_invite = CustomInvite.from_audit_log_diff(found_entry.before, invite.guild.id)
			actor_string = f" by <@{actor_id}>" if actor_id else ""
			await self.send_webhook(invite.guild.id, "delete", invite=custom_invite, actor_string=actor_string)

	@commands.Cog.listener()
	async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
		custom_channel = await self._get_custom_channel(channel)
		if custom_channel:
			actor_string = await self._get_actor_string(channel.guild, channel.id, [discord.AuditLogAction.channel_create])
			await self.send_webhook(channel.guild.id, "create", channel=custom_channel, actor_string=actor_string)

	@commands.Cog.listener()
	async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
		custom_channel = await self._get_custom_channel(channel)
		if custom_channel:
			actor_id = None
			async for entry in channel.guild.audit_logs(limit=5, action=discord.AuditLogAction.channel_delete):
				# For deletions, we match by the stored name and type in the 'before' changes,
				# as the target can be unreliable.
				if hasattr(entry.before, 'name') and hasattr(entry.before, 'type'):
					if entry.before.name == channel.name and entry.before.type == channel.type:
						actor_id = entry.user.id
						break
			actor_string = f" by <@{actor_id}>" if actor_id else ""
			await self.send_webhook(channel.guild.id, "delete", channel=custom_channel, actor_string=actor_string)

	@commands.Cog.listener()
	async def on_guild_channel_pins_update(self, channel: Union[discord.TextChannel, discord.VoiceChannel, discord.Thread], last_pin: Optional[datetime]):
		custom_channel = await self._get_custom_channel(channel)
		if custom_channel:
			await self.send_webhook(channel.guild.id, "pins", channel=custom_channel, last_pin=FormatDateTime(last_pin, "f") if last_pin else "N/A")

	@commands.Cog.listener()
	async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
		custom_before = await self._get_custom_channel(before)
		custom_after = await self._get_custom_channel(after)

		if not custom_before or not custom_after:
			return
		
		attributes_to_check = ['name', 'topic', 'nsfw', 'slowmode_delay']
		for attr in attributes_to_check:
			if hasattr(custom_before, attr) and hasattr(custom_after, attr):
				if getattr(custom_before, attr) != getattr(custom_after, attr):
					actor_string = await self._get_actor_string(after.guild, after.id, [discord.AuditLogAction.channel_update], changed_attribute=attr)
					await self.send_webhook(before.guild.id, attr, before=custom_before, after=custom_after, actor_string=actor_string)
		
		if custom_before.position != custom_after.position:
			await self.send_webhook(before.guild.id, "position", before=custom_before, after=custom_after, actor_string="")

		if before.overwrites != after.overwrites:
			actions_to_check = [
				discord.AuditLogAction.overwrite_create,
				discord.AuditLogAction.overwrite_update,
				discord.AuditLogAction.overwrite_delete
			]
			actor_string = await self._get_actor_string(after.guild, after.id, actions_to_check)
			diff_string = self._get_permission_diff_string(before.overwrites, after.overwrites)
			if diff_string:
				await self.send_webhook(before.guild.id, "permissions", diff=diff_string, actor_string=actor_string, channel=custom_after)


	async def get_webhook(self, guild_id: int) -> Optional[discord.Webhook]:
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
		if not await self.log_check(guild_id):
			return

		# automatically retreive the name of the function that calls this function and use it as the key
		key = f"log.{sys._getframe(1).f_code.co_name}.{event}"  # type: ignore

		webhook: Optional[discord.Webhook] = await self.get_webhook(guild_id)  # type: ignore
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
	async def log_check(self, guild: int):
		...

	@overload
	async def log_check(self, guild: discord.Guild):
		...

	async def log_check(self, guild: Union[int, discord.Guild]) -> bool:
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

		result = await self.client.db.fetchval(
			"SELECT is_on FROM log WHERE guild_id = $1",
			guild_id
		)
		return result

	@commands.Cog.listener()
	async def on_message_edit(self, before: discord.Message, after: discord.Message):
		if before.content != after.content:
			await self.send_webhook(before.guild.id, "content", before=CustomMessage.from_message(before), after=CustomMessage.from_message(after))
		if before.embeds != after.embeds:
			await self.send_webhook(before.guild.id, "embeds", before=CustomMessage.from_message(before),
									after=CustomMessage.from_message(after))
		if before.attachments != after.attachments:
			await self.send_webhook(before.guild.id, "attachments", before=CustomMessage.from_message(before), after=CustomMessage.from_message(after))
		if before.pinned != after.pinned:
			await self.send_webhook(before.guild.id, "pinned", before=CustomMessage.from_message(before), after=CustomMessage.from_message(after))

async def setup(client: MyClient) -> None:
	await client.add_cog(LogCommands(client))
	await client.add_cog(LogListeners(client))