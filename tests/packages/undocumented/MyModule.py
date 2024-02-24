from pyTooling.Decorators import export

MODULE_VARIABLE = 24


@export
class ModuleClass:
	ModuleClassField: str

	def __init__(self) -> None:
		pass

	def Method(self) -> None:
		pass

	def __str__(self) -> str:
		pass


class DerivedModuleClass(ModuleClass):
	pass
