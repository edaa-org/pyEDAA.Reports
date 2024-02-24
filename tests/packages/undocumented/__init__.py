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
		pass


class DerivedPackageClass(PackageClass):
	pass
