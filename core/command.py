from dataclasses import dataclass
from typing import Optional

from discord.ext import commands

from core.slash_localization import slash_command_localization


@dataclass
class Command:
	name: str
	description: str
	usage: str
	prefix: str
	aliases: Optional[str]

	@classmethod
	def from_ctx(cls, ctx: commands.Context):
		if ctx.command and slash_command_localization:
			usage = (
				slash_command_localization(ctx.command.usage, ctx) if ctx.command.usage else ctx.command.qualified_name
			)
			description = slash_command_localization(ctx.command.description, ctx)
			return cls(
				name=ctx.command.qualified_name,
				description=description if isinstance(description, str) and description else "-",
				usage=f"{ctx.clean_prefix}{usage}",
				prefix=ctx.clean_prefix,
				aliases=", ".join(ctx.command.aliases) if len(ctx.command.aliases) > 0 else None,
			)
		return None

	@classmethod
	def from_command(cls, command: commands.Command, ctx: commands.Context):
		if slash_command_localization:
			usage = slash_command_localization(command.usage, ctx) if command.usage else command.qualified_name
			description = slash_command_localization(command.description, ctx)
			return cls(
				name=command.qualified_name,
				description=description if isinstance(description, str) and description else "-",
				usage=f"{ctx.clean_prefix}{usage}",
				prefix=ctx.clean_prefix,
				aliases=", ".join(command.aliases) if len(command.aliases) > 0 else None,
			)
		return None
