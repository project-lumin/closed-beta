from dataclasses import dataclass, field
from typing import Self

import wavelink
from helpers import seconds_to_text


def format_ms(ms: int) -> str:
	total_seconds = max(0, ms // 1000)
	minutes, seconds = divmod(total_seconds, 60)
	hours, minutes = divmod(minutes, 60)
	if hours > 0:
		return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
	return f"{minutes:02d}:{seconds:02d}"


@dataclass(slots=True)
class Track:
	_title: str = field(repr=False)
	_uri: str | None = field(repr=False)
	_author: str = field(repr=False)
	_length: int = field(repr=False)
	_is_stream: bool = field(repr=False)
	_artwork: str | None = field(repr=False)
	_identifier: str | None = field(repr=False)
	_source: str | None = field(repr=False)
	_isrc: str | None = field(repr=False)

	@classmethod
	def from_track(cls, track: wavelink.Playable) -> Self:
		"""Creates a ``Track`` object from a ``wavelink.Playable`` instance."""
		return cls(
			_title=track.title,
			_uri=track.uri,
			_author=track.author or "Unknown",
			_length=track.length,
			_is_stream=track.is_stream,
			_artwork=track.artwork,
			_identifier=track.identifier,
			_source=track.source,
			_isrc=track.isrc,
		)

	from_playable = from_track

	@property
	def title(self) -> str:
		"""The title of the track."""
		return self._title

	@property
	def uri(self) -> str:
		"""The URI / link of the track."""
		return self._uri or ""

	url = link = uri

	@property
	def author(self) -> str:
		"""The author / artist of the track."""
		return self._author

	author_name = artist = uploader = author

	@property
	def length(self) -> int:
		"""The length of the track in milliseconds."""
		return self._length

	duration_ms = length

	@property
	def duration(self) -> str:
		"""The duration in human readable text (e.g. '3 minutes and 20 seconds', or 'Live')."""
		if self._is_stream:
			return "Live"
		return seconds_to_text(max(1, int(self._length / 1000)))

	@property
	def formatted_duration(self) -> str:
		"""The duration formatted as MM:SS or HH:MM:SS."""
		if self._is_stream:
			return "Live"
		return format_ms(self._length)

	timestamp = formatted_duration

	@property
	def is_stream(self) -> bool:
		"""Whether the track is a livestream."""
		return self._is_stream

	@property
	def artwork(self) -> str:
		"""The artwork / thumbnail URL of the track."""
		return self._artwork or ""

	thumbnail = image = artwork

	@property
	def identifier(self) -> str:
		"""The unique identifier for the track."""
		return self._identifier or ""

	@property
	def source(self) -> str:
		"""The source of the track (e.g. youtube, soundcloud, spotify)."""
		return self._source or ""

	@property
	def isrc(self) -> str | None:
		"""The International Standard Recording Code of the track, if available."""
		return self._isrc

	def __str__(self) -> str:
		return self._title
