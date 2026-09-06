class VPSProvider:
	@property
	def name(self):
		return "PlayClan"

	@property
	def url(self):
		return "https://www.playclan.org/"

	def __str__(self):
		return f"[{self.name}]({self.url})"
