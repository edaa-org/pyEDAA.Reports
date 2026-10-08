"""Conversion of lengths to meters."""


def ToMeters(value: float, unit: str) -> float:
	"""
	Convert a length to meters.

	The doc-string spans lines, as a lexer has to see it whole.
	"""
	if unit == "m":
		return value
	elif unit == "cm":
		return value / 100
	elif unit == "mm":
		return value / 1000

	raise ValueError(f"Unknown unit '{unit}'.")
