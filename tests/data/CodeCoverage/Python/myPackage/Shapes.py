"""Shapes with an area."""
from math import pi


class Circle:
	def __init__(self, radius: float) -> None:
		if radius < 0:
			raise ValueError("Negative radius.")
		self.radius = radius

	def Area(self) -> float:
		return pi * self.radius ** 2


class Rectangle:
	def __init__(self, width: float, height: float) -> None:
		self.width = width
		self.height = height

	def Area(self) -> float:
		return self.width * self.height

	def IsSquare(self) -> bool:
		if self.width == self.height:
			return True
		return False

	def __repr__(self) -> str:  # pragma: no cover
		return f"Rectangle({self.width}, {self.height})"
