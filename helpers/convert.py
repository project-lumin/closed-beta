"""A helper for converting stuff."""

import re
from typing import Optional

import discord


def text_to_seconds(time: str) -> int:
	"""
	Converts text into seconds. ex.: 5m = 300, 1d3min = 86400

	Arguments
	---------
	time: `str`
	        String containing the time(s). Examples are:

	        - 3min2s (3 minutes and 2 seconds) = 182 seconds

	        - 5h30m (5 hours and 30 minutes) = 19000

	        Supported time units:

	        - years (365d)

	        - months (31d)

	        - weeks

	        - days

	        - hours

	        - minutes

	        - seconds

	Returns
	-------
	`int`
	        Seconds.

	Raises
	----------
	ValueError
	        If the string doesn't contain time units.
	"""
	pattern = re.compile(
		r"(\d+)(y|yr|yrs|year|years|mo|mos|month|months|w|wk|wks|week|weeks|d|dy|dys|day|days|h|hr|hrs|hour|hours|m|mn|mns|min|mins|minutes|s|sc|scs|sec|secs|seconds)"
	)
	time_units = {
		"y": 60 * 60 * 24 * 365,
		"yr": 60 * 60 * 24 * 365,
		"yrs": 60 * 60 * 24 * 365,
		"year": 60 * 60 * 24 * 365,
		"years": 60 * 60 * 24 * 365,
		"mo": 60 * 60 * 24 * 31,
		"mos": 60 * 60 * 24 * 31,
		"month": 60 * 60 * 24 * 31,
		"months": 60 * 60 * 24 * 31,
		"w": 60 * 60 * 24 * 7,
		"wk": 60 * 60 * 24 * 7,
		"wks": 60 * 60 * 24 * 7,
		"week": 60 * 60 * 24 * 7,
		"weeks": 60 * 60 * 24 * 7,
		"d": 60 * 60 * 24,
		"dy": 60 * 60 * 24,
		"dys": 60 * 60 * 24,
		"day": 60 * 60 * 24,
		"days": 60 * 60 * 24,
		"h": 60 * 60,
		"hr": 60 * 60,
		"hrs": 60 * 60,
		"hour": 60 * 60,
		"hours": 60 * 60,
		"m": 60,
		"mn": 60,
		"mns": 60,
		"min": 60,
		"mins": 60,
		"minutes": 60,
		"s": 1,
		"sec": 1,
		"secs": 1,
		"seconds": 1,
	}

	total_seconds = 0
	matches = pattern.findall(time)

	if not matches:
		raise ValueError(f"String doesn't contain time units ('{time}')")

	for value, unit in matches:
		total_seconds += int(value) * time_units.get(unit)

	return total_seconds


def seconds_to_text(seconds: int) -> str:
	"""
	Converts seconds into a human-readable format. ex.: 300 = 5m, 86400 = 1d

	Arguments
	---------
	seconds: `int`
	        Seconds to convert.

	Returns
	-------
	`str`
	        Human-readable time.
	"""
	time_units = {
		"y": 60 * 60 * 24 * 365,
		"mo": 60 * 60 * 24 * 31,
		"w": 60 * 60 * 24 * 7,
		"d": 60 * 60 * 24,
		"h": 60 * 60,
		"m": 60,
		"s": 1,
	}

	time = ""
	for unit, value in time_units.items():
		if seconds >= value:
			time += f"{seconds // value}{unit[0]} "
			seconds %= value

	return time.strip()


def convert_to_query(
	table: str,
	guild: Optional[discord.Guild] = None,
	limit: Optional[int] = None,
	**filters,
):
	"""Converts a set of filters to an SQL query.

	Parameters
	----------
	table: `str`
	        The table to get the results from.
	guild: Optional[`discord.Guild`]
	        The guild to get the results from.
	limit: Optional[`int`]
	        The number of results to return. If ``None``, all results will be returned.
	**filters
	        The conditions to filter the results by.

	Returns
	-------
	(`str`, list[Any])
	        The query string and the query parameters.
	"""
	processed_filters = {}
	for key, value in filters.items():
		if isinstance(value, (discord.User, discord.Guild, discord.Member, discord.Message)):
			processed_filters[f"{key}_id"] = value.id
		else:
			processed_filters[key] = value

	if guild:
		processed_filters["guild_id"] = guild.id

	# Construct WHERE clause from processed filters
	where_clauses = []
	query_parameters = []
	for idx, (key, value) in enumerate(processed_filters.items(), start=1):
		where_clauses.append(f"{key} = ${idx}")
		query_parameters.append(value)

	where_statement = " AND ".join(where_clauses) if where_clauses else "1=1"
	query = f"SELECT * FROM {table} WHERE {where_statement}"
	if limit is not None:
		query += f" LIMIT ${len(query_parameters) + 1}"
		query_parameters.append(limit)

	return query, query_parameters

def text_to_emoji(text: str) -> list[str]:
	"""Converts a string to an emoji."""
	base = 0x1f1e6
	result = []
	for char in text.upper():
		if "A" <= char <= "Z":
			result.append(chr(base + ord(char) - ord("A")))
		else:
			result.append(char)
	return result