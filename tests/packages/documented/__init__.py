"""
Package documentation
"""
from pyTooling.Decorators import export


PACKAGE_VARIABLE = 24  #: PackageVariable documentation


@export
class PackageClass:
	"""
	PackageClass documentation
	"""
	PackageClassField: str  #: Field documentation

	def __init__(self) -> None:
		"""Initializer documentation"""
		pass

	def Method(self) -> None:
		"""Method documentation"""
		pass

	def __str__(self) -> str:
		"""Dunder documentation"""
		pass


class DerivedPackageClass(PackageClass):
	"""Derived package class documentation"""
	pass
