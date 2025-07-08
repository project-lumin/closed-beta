import re

DISCORD_INVITE = re.compile(
	r"(https?://)?(www\.)?(discord\.(gg|io|me|li)|discordapp\.com/invite)/.+[a-z]"
)
DISCORD_TEMPLATE = re.compile(r"(?:https?://)?discord\.new/([a-zA-Z0-9]+)")
