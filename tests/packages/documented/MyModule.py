"""
Module documentation
"""
from pyTooling.Decorators import export

MODULE_VARIABLE = 24  #: ModuleVariable documentation


@export
class ModuleClass:
	"""
	ModuleClass documentation
	"""
	ClassClassField: str  #: Field documentation

	def __init__(self) -> None:
		"""Initializer documentation"""
		pass

	def Method(self) -> None:
		"""Method documentation"""
		pass

	def __str__(self) -> str:
		"""Dunder documentation"""
		pass


class DerivedModuleClass(ModuleClass):
	"""Derived module class documentation"""
	pass
