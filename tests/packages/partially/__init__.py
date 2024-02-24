"""
Package documentation
"""
from pyTooling.Decorators import export

PACKAGE_VARIABLE = 24


@export
class PackageClass:
	PackageClassField: str

	def __init__(self) -> None:
		pass

	def Method(self) -> None:
		pass

	def __str__(self) -> str:
		"""Dunder documentation"""
		pass


class DerivedPackageClass(PackageClass):
	"""Derived package class documentation"""
	pass
