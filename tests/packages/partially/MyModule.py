from pyTooling.Decorators import export

MODULE_VARIABLE = 24  #: ModulVariable documentation


@export
class ModuleClass:
	"""
	ModuleClass documentation
	"""
	ModuleClassField: str

	def __init__(self) -> None:
		pass

	def Method(self) -> None:
		"""Method documentation"""
		pass

	def __str__(self) -> str:
		pass


class DerivedModuleClass(ModuleClass):
	pass
