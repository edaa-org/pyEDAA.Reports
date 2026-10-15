"""Fixture of the documentation coverage tests: fields and variables, documented in the forms Sphinx' autodoc reads."""
from enum   import Enum
from typing import ClassVar, Final, NewType, TypeAlias, TypeVar

__all__ = ["Shape"]

T = TypeVar("T")                   #: A trailing comment.
Length = NewType("Length", float)
"""A string literal after the statement."""
#: A comment line above.
#: A second comment line above.
MAXIMUM: Final = 10
Alias: TypeAlias = "int | str"
undocumented = 1
#:
emptyComment = 2
first, second = 1, 2               #: Both names of a tuple.
chained = other = 3
"""Only the first target."""
lookup = {                         #: Behind an opening bracket.
	"a": 1,
}
table = {
	"a": 1,
}                                  #: Behind a closing bracket.
formatted = f"{T}"                 #: Behind an f-string.
semicolon = 1; afterSemicolon = 2  #: Behind a second statement.

if MAXIMUM > 5:
	conditional = 1                  #: In an 'if' block.
else:
	conditional = 2

try:
	guarded = 1
	"""In a 'try' block."""
except ImportError:
	handled = 2                      #: In an 'except' block.


class Color(Enum):
	"""An enumeration."""

	Red = 1                          #: Red.
	Green = 2


class Shape:
	"""A class."""

	_name:         str               #: A trailing comment.
	#: A comment line above.
	_size:         int
	_counter:      ClassVar[int] = 0
	_plain =       3
	_undocumented: int
	_initialized:  int

	class Inner:
		"""A nested class."""

		_value: int                    #: A field of a nested class.

	def __init__(self) -> None:
		"""Initializes a shape."""
		self._initialized = 1          #: Documented in '__init__'.
		self._onlyInInit = 2           #: Not declared in the class' body.
