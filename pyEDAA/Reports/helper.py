from typing import Callable

from pyTooling.Decorators import export


@export
def InheritDocumentation(baseClass: type, merge: bool = False) -> Callable[[type], type]:
	"""xxx"""
	def decorator(c: type) -> type:
		"""yyy"""
		if merge:
			if c.__doc__ is None:
				c.__doc__ = baseClass.__doc__
			elif baseClass.__doc__ is not None:
				c.__doc__ = baseClass.__doc__ + "\n\n" + c.__doc__
		else:
			c.__doc__ = baseClass.__doc__
		return c

	return decorator
