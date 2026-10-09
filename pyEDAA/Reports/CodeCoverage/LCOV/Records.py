# ==================================================================================================================== #
#              _____ ____    _        _      ____                       _                                              #
#  _ __  _   _| ____|  _ \  / \      / \    |  _ \ ___ _ __   ___  _ __| |_ ___                                        #
# | '_ \| | | |  _| | | | |/ _ \    / _ \   | |_) / _ \ '_ \ / _ \| '__| __/ __|                                       #
# | |_) | |_| | |___| |_| / ___ \  / ___ \ _|  _ <  __/ |_) | (_) | |  | |_\__ \                                       #
# | .__/ \__, |_____|____/_/   \_\/_/   \_(_)_| \_\___| .__/ \___/|_|   \__|___/                                       #
# |_|    |___/                                        |_|                                                              #
# ==================================================================================================================== #
# Authors:                                                                                                             #
#   Patrick Lehmann                                                                                                    #
#                                                                                                                      #
# License:                                                                                                             #
# ==================================================================================================================== #
# Copyright 2026-2026 Electronic Design Automation Abstraction (EDA²)                                                  #
#                                                                                                                      #
# Licensed under the Apache License, Version 2.0 (the "License");                                                      #
# you may not use this file except in compliance with the License.                                                     #
# You may obtain a copy of the License at                                                                              #
#                                                                                                                      #
#   http://www.apache.org/licenses/LICENSE-2.0                                                                         #
#                                                                                                                      #
# Unless required by applicable law or agreed to in writing, software                                                  #
# distributed under the License is distributed on an "AS IS" BASIS,                                                    #
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.                                             #
# See the License for the specific language governing permissions and                                                  #
# limitations under the License.                                                                                       #
#                                                                                                                      #
# SPDX-License-Identifier: Apache-2.0                                                                                  #
# ==================================================================================================================== #
#
"""
The records of lcov's tracefile format: a section, and its functions, lines, branches and conditions.
"""
from __future__                         import annotations

from collections.abc                    import Mapping
from pathlib                            import Path
from typing                             import TYPE_CHECKING, Optional as Nullable

from pyTooling.Common                   import getFullyQualifiedName
from pyTooling.Decorators               import export, readonly
from pyTooling.MetaClasses              import ExtendedType

from pyEDAA.Reports.CodeCoverage        import CodeCoverageError

if TYPE_CHECKING:
	from pyEDAA.Reports.CodeCoverage.LCOV import Tracefile


@export
class Line(metaclass=ExtendedType, slots=True):
	"""
	A ``DA`` record: how often a line ran, and the line's checksum.
	"""

	_parent:   Nullable[Section]  #: The section the line belongs to.
	_number:   int                #: Line number.
	_count:    int                #: How often the line ran; the sum, if the section lists the line twice.
	_checksum: Nullable[str]      #: Checksum of the line's source text, if stated.

	def __init__(
		self,
		number: int,
		count: int,
		checksum: Nullable[str] = None,
		*,
		parent: Nullable[Section] = None
	) -> None:
		"""
		Initialize a line, and add it to the lines of its section.

		:param number:             Line number.
		:param count:              How often the line ran.
		:param checksum:           Optional, checksum of the line's source text. Default: ``None``.
		:param parent:             Optional, the section the line belongs to; the line is added to its lines by
		                           :attr:`Number`. Default: ``None``.
		:raises ValueError:        If parameter ``number`` is ``None``.
		:raises TypeError:         If parameter ``number`` isn't of type :class:`int`.
		:raises ValueError:        If parameter ``number`` is less than 1.
		:raises ValueError:        If parameter ``count`` is ``None``.
		:raises TypeError:         If parameter ``count`` isn't of type :class:`int`.
		:raises ValueError:        If parameter ``count`` is negative.
		:raises TypeError:         If parameter ``checksum`` isn't of type :class:`str`.
		:raises ValueError:        If parameter ``checksum`` is empty.
		:raises TypeError:         If parameter ``parent`` isn't of type :class:`Section`.
		:raises CodeCoverageError: If the section already has a line of this number.
		"""
		if number is None:
			raise ValueError(f"Parameter 'number' is None.")
		elif not isinstance(number, int):
			ex = TypeError(f"Parameter 'number' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(number)}'.")
			raise ex
		elif number < 1:
			ex = ValueError(f"Parameter 'number' is less than 1.")
			ex.add_note(f"Got value '{number}'.")
			raise ex

		if count is None:
			raise ValueError(f"Parameter 'count' is None.")
		elif not isinstance(count, int):
			ex = TypeError(f"Parameter 'count' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(count)}'.")
			raise ex
		elif count < 0:
			ex = ValueError(f"Parameter 'count' is negative.")
			ex.add_note(f"Got value '{count}'.")
			raise ex

		if checksum is not None and not isinstance(checksum, str):
			ex = TypeError(f"Parameter 'checksum' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(checksum)}'.")
			raise ex
		elif checksum == "":
			raise ValueError(f"Parameter 'checksum' is empty.")

		if parent is not None and not isinstance(parent, Section):
			ex = TypeError(f"Parameter 'parent' is not of type 'Section'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =   parent
		self._number =   number
		self._count =    count
		self._checksum = checksum

		if parent is not None:
			if number in parent._lines:
				raise CodeCoverageError(f"Line {number} of the section of '{parent._sourceFile.as_posix()}' is added twice.")

			parent._lines[number] = self

	@readonly
	def Parent(self) -> Nullable[Section]:
		"""
		Read-only property to access the section the line belongs to (:attr:`_parent`).

		:returns: The section; ``None`` if the line belongs to no section.
		"""
		return self._parent

	@readonly
	def Number(self) -> int:
		"""
		Read-only property to access the line number (:attr:`_number`).

		:returns: The line number.
		"""
		return self._number

	@readonly
	def Count(self) -> int:
		"""
		Read-only property to access how often the line ran (:attr:`_count`).

		:returns: The execution count.
		"""
		return self._count

	@readonly
	def Checksum(self) -> Nullable[str]:
		"""
		Read-only property to access the checksum of the line's source text (:attr:`_checksum`).

		lcov writes an MD5 hash in base64.

		:returns: The checksum, or ``None`` if not stated.
		"""
		return self._checksum


@export
class Branch(metaclass=ExtendedType, slots=True):
	"""
	A ``BRDA`` record: a branch of a line, and how often it was taken.
	"""

	_parent:      Nullable[Section]  #: The section the branch belongs to.
	_lineNumber:  int                #: Line number of the branch.
	_block:       int                #: Number of the branch's block - the conditional - in its line.
	_expression:  str                #: Index or expression identifying the branch in its block.
	_taken:       Nullable[int]      #: How often the branch was taken; ``None``, if it was never evaluated.
	_isException: bool               #: Whether the branch is taken by an exception.

	def __init__(
		self,
		lineNumber: int,
		block: int,
		expression: str,
		taken: Nullable[int],
		isException: bool,
		*,
		parent: Nullable[Section] = None
	) -> None:
		"""
		Initialize a branch, and append it to the branches of its section.

		:param lineNumber:  Line number of the branch.
		:param block:       Number of the branch's block in its line.
		:param expression:  Index or expression identifying the branch in its block.
		:param taken:       How often the branch was taken; ``None``, if it was never evaluated.
		:param isException: Whether the branch is taken by an exception.
		:param parent:      Optional, the section the branch belongs to; the branch is appended to its branches.
		                    Default: ``None``.
		:raises ValueError: If parameter ``lineNumber`` is ``None``.
		:raises TypeError:  If parameter ``lineNumber`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``lineNumber`` is less than 1.
		:raises ValueError: If parameter ``block`` is ``None``.
		:raises TypeError:  If parameter ``block`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``block`` is negative.
		:raises ValueError: If parameter ``expression`` is ``None``.
		:raises TypeError:  If parameter ``expression`` isn't of type :class:`str`.
		:raises ValueError: If parameter ``expression`` is empty.
		:raises TypeError:  If parameter ``taken`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``taken`` is negative.
		:raises ValueError: If parameter ``isException`` is ``None``.
		:raises TypeError:  If parameter ``isException`` isn't of type :class:`bool`.
		:raises TypeError:  If parameter ``parent`` isn't of type :class:`Section`.
		"""
		if lineNumber is None:
			raise ValueError(f"Parameter 'lineNumber' is None.")
		elif not isinstance(lineNumber, int):
			ex = TypeError(f"Parameter 'lineNumber' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(lineNumber)}'.")
			raise ex
		elif lineNumber < 1:
			ex = ValueError(f"Parameter 'lineNumber' is less than 1.")
			ex.add_note(f"Got value '{lineNumber}'.")
			raise ex

		if block is None:
			raise ValueError(f"Parameter 'block' is None.")
		elif not isinstance(block, int):
			ex = TypeError(f"Parameter 'block' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(block)}'.")
			raise ex
		elif block < 0:
			ex = ValueError(f"Parameter 'block' is negative.")
			ex.add_note(f"Got value '{block}'.")
			raise ex

		if expression is None:
			raise ValueError(f"Parameter 'expression' is None.")
		elif not isinstance(expression, str):
			ex = TypeError(f"Parameter 'expression' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(expression)}'.")
			raise ex
		elif expression == "":
			raise ValueError(f"Parameter 'expression' is empty.")

		if taken is not None and not isinstance(taken, int):
			ex = TypeError(f"Parameter 'taken' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(taken)}'.")
			raise ex
		elif taken is not None and taken < 0:
			ex = ValueError(f"Parameter 'taken' is negative.")
			ex.add_note(f"Got value '{taken}'.")
			raise ex

		if isException is None:
			raise ValueError(f"Parameter 'isException' is None.")
		elif not isinstance(isException, bool):
			ex = TypeError(f"Parameter 'isException' is not of type 'bool'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(isException)}'.")
			raise ex

		if parent is not None and not isinstance(parent, Section):
			ex = TypeError(f"Parameter 'parent' is not of type 'Section'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =      parent
		self._lineNumber =  lineNumber
		self._block =       block
		self._expression =  expression
		self._taken =       taken
		self._isException = isException

		if parent is not None:
			parent._branches.append(self)

	@readonly
	def Parent(self) -> Nullable[Section]:
		"""
		Read-only property to access the section the branch belongs to (:attr:`_parent`).

		:returns: The section; ``None`` if the branch belongs to no section.
		"""
		return self._parent

	@readonly
	def LineNumber(self) -> int:
		"""
		Read-only property to access the line number of the branch (:attr:`_lineNumber`).

		:returns: The line number.
		"""
		return self._lineNumber

	@readonly
	def Block(self) -> int:
		"""
		Read-only property to access the number of the branch's block in its line (:attr:`_block`).

		:returns: The block number, counted from 0.
		"""
		return self._block

	@readonly
	def Expression(self) -> str:
		"""
		Read-only property to access the index or expression identifying the branch in its block (:attr:`_expression`).

		Each tool identifies a branch its own way, e.g. GCC by an index like ``1``, coverage.py by a text like
		``jump to line 8``.

		:returns: The identifier.
		"""
		return self._expression

	@readonly
	def Taken(self) -> Nullable[int]:
		"""
		Read-only property to access how often the branch was taken (:attr:`_taken`).

		:returns: The count, or ``None`` if the branch was never evaluated - stated as ``-``.
		"""
		return self._taken

	@readonly
	def IsException(self) -> bool:
		"""
		Read-only property to access whether the branch is taken by an exception (:attr:`_isException`).

		:returns: ``True``, if the branch is marked by the prefix ``e``.
		"""
		return self._isException


@export
class Condition(metaclass=ExtendedType, slots=True):
	"""
	An ``MCDC`` record: whether the outcome of a line's expression changed, when one of its conditions changed.
	"""

	_parent:     Nullable[Section]  #: The section the condition belongs to.
	_lineNumber: int                #: Line number of the expression.
	_groupSize:  int                #: Number of conditions in the expression's group.
	_sense:      bool               #: ``True`` for a change from false to true; ``False`` for the converse.
	_taken:      int                #: How often - or whether - the condition was sensitized.
	_index:      int                #: Index of the condition in its group.
	_expression: str                #: The condition's expression.

	def __init__(
		self,
		lineNumber: int,
		groupSize: int,
		sense: bool,
		taken: int,
		index: int,
		expression: str,
		*,
		parent: Nullable[Section] = None
	) -> None:
		"""
		Initialize a condition, and append it to the conditions of its section.

		:param lineNumber:  Line number of the expression.
		:param groupSize:   Number of conditions in the expression's group.
		:param sense:       ``True`` for a change of the condition from false to true; ``False`` for the converse.
		:param taken:       How often - or whether - the condition was sensitized.
		:param index:       Index of the condition in its group.
		:param expression:  The condition's expression.
		:param parent:      Optional, the section the condition belongs to; the condition is appended to its conditions.
		                    Default: ``None``.
		:raises ValueError: If parameter ``lineNumber`` is ``None``.
		:raises TypeError:  If parameter ``lineNumber`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``lineNumber`` is less than 1.
		:raises ValueError: If parameter ``groupSize`` is ``None``.
		:raises TypeError:  If parameter ``groupSize`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``groupSize`` is negative.
		:raises ValueError: If parameter ``sense`` is ``None``.
		:raises TypeError:  If parameter ``sense`` isn't of type :class:`bool`.
		:raises ValueError: If parameter ``taken`` is ``None``.
		:raises TypeError:  If parameter ``taken`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``taken`` is negative.
		:raises ValueError: If parameter ``index`` is ``None``.
		:raises TypeError:  If parameter ``index`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``index`` is negative.
		:raises ValueError: If parameter ``expression`` is ``None``.
		:raises TypeError:  If parameter ``expression`` isn't of type :class:`str`.
		:raises ValueError: If parameter ``expression`` is empty.
		:raises TypeError:  If parameter ``parent`` isn't of type :class:`Section`.
		"""
		if lineNumber is None:
			raise ValueError(f"Parameter 'lineNumber' is None.")
		elif not isinstance(lineNumber, int):
			ex = TypeError(f"Parameter 'lineNumber' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(lineNumber)}'.")
			raise ex
		elif lineNumber < 1:
			ex = ValueError(f"Parameter 'lineNumber' is less than 1.")
			ex.add_note(f"Got value '{lineNumber}'.")
			raise ex

		if groupSize is None:
			raise ValueError(f"Parameter 'groupSize' is None.")
		elif not isinstance(groupSize, int):
			ex = TypeError(f"Parameter 'groupSize' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(groupSize)}'.")
			raise ex
		elif groupSize < 0:
			ex = ValueError(f"Parameter 'groupSize' is negative.")
			ex.add_note(f"Got value '{groupSize}'.")
			raise ex

		if sense is None:
			raise ValueError(f"Parameter 'sense' is None.")
		elif not isinstance(sense, bool):
			ex = TypeError(f"Parameter 'sense' is not of type 'bool'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(sense)}'.")
			raise ex

		if taken is None:
			raise ValueError(f"Parameter 'taken' is None.")
		elif not isinstance(taken, int):
			ex = TypeError(f"Parameter 'taken' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(taken)}'.")
			raise ex
		elif taken < 0:
			ex = ValueError(f"Parameter 'taken' is negative.")
			ex.add_note(f"Got value '{taken}'.")
			raise ex

		if index is None:
			raise ValueError(f"Parameter 'index' is None.")
		elif not isinstance(index, int):
			ex = TypeError(f"Parameter 'index' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(index)}'.")
			raise ex
		elif index < 0:
			ex = ValueError(f"Parameter 'index' is negative.")
			ex.add_note(f"Got value '{index}'.")
			raise ex

		if expression is None:
			raise ValueError(f"Parameter 'expression' is None.")
		elif not isinstance(expression, str):
			ex = TypeError(f"Parameter 'expression' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(expression)}'.")
			raise ex
		elif expression == "":
			raise ValueError(f"Parameter 'expression' is empty.")

		if parent is not None and not isinstance(parent, Section):
			ex = TypeError(f"Parameter 'parent' is not of type 'Section'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =     parent
		self._lineNumber = lineNumber
		self._groupSize =  groupSize
		self._sense =      sense
		self._taken =      taken
		self._index =      index
		self._expression = expression

		if parent is not None:
			parent._conditions.append(self)

	@readonly
	def Parent(self) -> Nullable[Section]:
		"""
		Read-only property to access the section the condition belongs to (:attr:`_parent`).

		:returns: The section; ``None`` if the condition belongs to no section.
		"""
		return self._parent

	@readonly
	def LineNumber(self) -> int:
		"""
		Read-only property to access the line number of the expression (:attr:`_lineNumber`).

		:returns: The line number.
		"""
		return self._lineNumber

	@readonly
	def GroupSize(self) -> int:
		"""
		Read-only property to access the number of conditions in the expression's group (:attr:`_groupSize`).

		:returns: The group size.
		"""
		return self._groupSize

	@readonly
	def Sense(self) -> bool:
		"""
		Read-only property to access the sense of the condition's change (:attr:`_sense`).

		:returns: ``True`` for a change from false to true - stated as ``t`` -, ``False`` for the converse - ``f``.
		"""
		return self._sense

	@readonly
	def Taken(self) -> int:
		"""
		Read-only property to access how often - or whether - the condition was sensitized (:attr:`_taken`).

		:returns: The count; ``0``, if the condition was never sensitized.
		"""
		return self._taken

	@readonly
	def Index(self) -> int:
		"""
		Read-only property to access the index of the condition in its group (:attr:`_index`).

		:returns: The index, counted from 0.
		"""
		return self._index

	@readonly
	def Expression(self) -> str:
		"""
		Read-only property to access the condition's expression (:attr:`_expression`).

		The text depends on the tool, e.g. GCC states ``0``.

		:returns: The expression.
		"""
		return self._expression


@export
class Function(metaclass=ExtendedType, slots=True):
	"""
	A function: an ``FN`` record with the count of its ``FNDA`` record, or an ``FNL`` record with its ``FNA`` aliases.

	The aliases of a function - e.g. instances of a C++ template - share its lines.
	"""

	_parent:    Nullable[Section]         #: The section the function belongs to.
	_index:     Nullable[int]             #: Index of the ``FNL`` record; ``None`` for an ``FN`` record.
	_startLine: int                       #: The function's first line.
	_endLine:   Nullable[int]             #: The function's last line, if stated.
	_aliases:   dict[str, Nullable[int]]  #: The function's names, and how often each was called, if stated.

	def __init__(
		self,
		startLine: int,
		endLine: Nullable[int],
		aliases: Mapping[str, Nullable[int]],
		index: Nullable[int] = None,
		*,
		parent: Nullable[Section] = None
	) -> None:
		"""
		Initialize a function, and append it to the functions of its section.

		:param startLine:   The function's first line.
		:param endLine:     The function's last line, or ``None`` if not stated.
		:param aliases:     The function's names, and how often each was called - ``None``, if not stated -; the first
		                    name is the function's name.
		:param index:       Optional, index of the ``FNL`` record. Default: ``None``, for an ``FN`` record.
		:param parent:      Optional, the section the function belongs to; the function is appended to its functions.
		                    Default: ``None``.
		:raises ValueError: If parameter ``startLine`` is ``None``.
		:raises TypeError:  If parameter ``startLine`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``startLine`` is less than 1.
		:raises TypeError:  If parameter ``endLine`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``endLine`` is less than 1.
		:raises ValueError: If parameter ``aliases`` is ``None``.
		:raises TypeError:  If parameter ``aliases`` isn't a mapping.
		:raises ValueError: If parameter ``aliases`` is empty.
		:raises TypeError:  If parameter ``aliases`` contains a name not of type :class:`str`.
		:raises ValueError: If parameter ``aliases`` contains an empty name.
		:raises TypeError:  If parameter ``aliases`` contains a count not of type :class:`int`.
		:raises ValueError: If parameter ``aliases`` contains a negative count.
		:raises TypeError:  If parameter ``index`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``index`` is negative.
		:raises TypeError:  If parameter ``parent`` isn't of type :class:`Section`.
		"""
		if startLine is None:
			raise ValueError(f"Parameter 'startLine' is None.")
		elif not isinstance(startLine, int):
			ex = TypeError(f"Parameter 'startLine' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(startLine)}'.")
			raise ex
		elif startLine < 1:
			ex = ValueError(f"Parameter 'startLine' is less than 1.")
			ex.add_note(f"Got value '{startLine}'.")
			raise ex

		if endLine is not None and not isinstance(endLine, int):
			ex = TypeError(f"Parameter 'endLine' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(endLine)}'.")
			raise ex
		elif endLine is not None and endLine < 1:
			ex = ValueError(f"Parameter 'endLine' is less than 1.")
			ex.add_note(f"Got value '{endLine}'.")
			raise ex

		if aliases is None:
			raise ValueError(f"Parameter 'aliases' is None.")
		elif not isinstance(aliases, Mapping):
			ex = TypeError(f"Parameter 'aliases' is not a mapping.")
			ex.add_note(f"Got type '{getFullyQualifiedName(aliases)}'.")
			raise ex
		elif len(aliases) == 0:
			raise ValueError(f"Parameter 'aliases' is empty.")

		if index is not None and not isinstance(index, int):
			ex = TypeError(f"Parameter 'index' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(index)}'.")
			raise ex
		elif index is not None and index < 0:
			ex = ValueError(f"Parameter 'index' is negative.")
			ex.add_note(f"Got value '{index}'.")
			raise ex

		if parent is not None and not isinstance(parent, Section):
			ex = TypeError(f"Parameter 'parent' is not of type 'Section'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =    parent
		self._index =     index
		self._startLine = startLine
		self._endLine =   endLine
		self._aliases =   {}

		for name, count in aliases.items():
			if not isinstance(name, str):
				ex = TypeError(f"Parameter 'aliases' contains a name not of type 'str'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(name)}'.")
				raise ex
			elif name == "":
				raise ValueError(f"Parameter 'aliases' contains an empty name.")
			elif count is not None and not isinstance(count, int):
				ex = TypeError(f"Parameter 'aliases' contains a count not of type 'int'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(count)}'.")
				raise ex
			elif count is not None and count < 0:
				ex = ValueError(f"Parameter 'aliases' contains a negative count.")
				ex.add_note(f"Got value '{count}'.")
				raise ex

			self._aliases[name] = count

		if parent is not None:
			parent._functions.append(self)

	@readonly
	def Parent(self) -> Nullable[Section]:
		"""
		Read-only property to access the section the function belongs to (:attr:`_parent`).

		:returns: The section; ``None`` if the function belongs to no section.
		"""
		return self._parent

	@readonly
	def Index(self) -> Nullable[int]:
		"""
		Read-only property to access the index of the ``FNL`` record (:attr:`_index`).

		:returns: The index, or ``None`` for an ``FN`` record.
		"""
		return self._index

	@readonly
	def StartLine(self) -> int:
		"""
		Read-only property to access the function's first line (:attr:`_startLine`).

		:returns: The line number.
		"""
		return self._startLine

	@readonly
	def EndLine(self) -> Nullable[int]:
		"""
		Read-only property to access the function's last line (:attr:`_endLine`).

		Not every tool states it, e.g. llvm-cov doesn't.

		:returns: The line number, or ``None`` if not stated.
		"""
		return self._endLine

	@readonly
	def Aliases(self) -> dict[str, Nullable[int]]:
		"""
		Read-only property to access the function's names, and how often each was called (:attr:`_aliases`).

		:returns: The counts by name, in the tracefile's order; a count is ``None``, if no ``FNDA`` record states it.
		"""
		return self._aliases

	@readonly
	def Name(self) -> str:
		"""
		Read-only property to return the function's name: its first alias.

		:returns: The name.
		"""
		return next(iter(self._aliases))

	@readonly
	def Count(self) -> Nullable[int]:
		"""
		Read-only property to return how often the function was called: the sum over its aliases.

		:returns: The count, or ``None`` if no alias' count is stated.
		"""
		counts = [count for count in self._aliases.values() if count is not None]
		return sum(counts) if len(counts) > 0 else None


@export
class Section(metaclass=ExtendedType, slots=True):
	"""
	A section from ``SF`` to ``end_of_record``: a source file's coverage, as a test measured it, and the summaries the
	section states.
	"""

	_parent:          Nullable[Tracefile]  #: The tracefile the section belongs to.
	_testName:        str                  #: Name of the test, stated by the last ``TN`` record before the section.
	_sourceFile:      Path                 #: Path of the source file.
	_version:         Nullable[str]        #: Version ID of the source file, if stated.
	_functions:       list[Function]       #: The functions, in the tracefile's order.
	_lines:           dict[int, Line]      #: The lines, by number.
	_branches:        list[Branch]         #: The branches, in the tracefile's order.
	_conditions:      list[Condition]      #: The conditions of MC/DC coverage, in the tracefile's order.
	_functionsFound:  Nullable[int]        #: Number of functions, as the section states it.
	_functionsHit:    Nullable[int]        #: Number of functions called, as the section states it.
	_branchesFound:   Nullable[int]        #: Number of branches, as the section states it.
	_branchesHit:     Nullable[int]        #: Number of branches taken, as the section states it.
	_conditionsFound: Nullable[int]        #: Number of conditions, as the section states it.
	_conditionsHit:   Nullable[int]        #: Number of conditions sensitized, as the section states it.
	_linesFound:      Nullable[int]        #: Number of instrumented lines, as the section states it.
	_linesHit:        Nullable[int]        #: Number of lines, which ran, as the section states it.

	def __init__(self, testName: str, sourceFile: Path, *, parent: Nullable[Tracefile] = None) -> None:
		"""
		Initialize an empty section, and append it to the sections of its tracefile.

		:param testName:    Name of the test; empty, if not stated.
		:param sourceFile:  Path of the source file.
		:param parent:      Optional, the tracefile the section belongs to; the section is appended to its sections.
		                    Default: ``None``.
		:raises ValueError: If parameter ``testName`` is ``None``.
		:raises TypeError:  If parameter ``testName`` isn't of type :class:`str`.
		:raises ValueError: If parameter ``sourceFile`` is ``None``.
		:raises TypeError:  If parameter ``sourceFile`` isn't of type :class:`~pathlib.Path`.
		:raises TypeError:  If parameter ``parent`` isn't of type :class:`~pyEDAA.Reports.CodeCoverage.LCOV.Tracefile`.
		"""
		from pyEDAA.Reports.CodeCoverage.LCOV import Tracefile

		if testName is None:
			raise ValueError(f"Parameter 'testName' is None.")
		elif not isinstance(testName, str):
			ex = TypeError(f"Parameter 'testName' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(testName)}'.")
			raise ex

		if sourceFile is None:
			raise ValueError(f"Parameter 'sourceFile' is None.")
		elif not isinstance(sourceFile, Path):
			ex = TypeError(f"Parameter 'sourceFile' is not of type 'Path'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(sourceFile)}'.")
			raise ex

		if parent is not None and not isinstance(parent, Tracefile):
			ex = TypeError(f"Parameter 'parent' is not of type 'Tracefile'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =          parent
		self._testName =        testName
		self._sourceFile =      sourceFile
		self._version =         None
		self._functions =       []
		self._lines =           {}
		self._branches =        []
		self._conditions =      []
		self._functionsFound =  None
		self._functionsHit =    None
		self._branchesFound =   None
		self._branchesHit =     None
		self._conditionsFound = None
		self._conditionsHit =   None
		self._linesFound =      None
		self._linesHit =        None

		if parent is not None:
			parent._sections.append(self)

	@readonly
	def Parent(self) -> Nullable[Tracefile]:
		"""
		Read-only property to access the tracefile the section belongs to (:attr:`_parent`).

		:returns: The tracefile; ``None`` if the section belongs to no tracefile.
		"""
		return self._parent

	@readonly
	def TestName(self) -> str:
		"""
		Read-only property to access the name of the test (:attr:`_testName`).

		:returns: The name; empty, if no ``TN`` record states it.
		"""
		return self._testName

	@readonly
	def SourceFile(self) -> Path:
		"""
		Read-only property to access the path of the source file (:attr:`_sourceFile`).

		:returns: The path, as the tracefile states it: absolute, or relative to the directory the tool ran in; a
		          backslash of a tracefile written on Windows is a separator.
		"""
		return self._sourceFile

	@readonly
	def Version(self) -> Nullable[str]:
		"""
		Read-only property to access the version ID of the source file (:attr:`_version`).

		:returns: The version ID, or ``None`` if not stated.
		"""
		return self._version

	@readonly
	def Functions(self) -> list[Function]:
		"""
		Read-only property to access the functions (:attr:`_functions`).

		:returns: The functions, in the tracefile's order.
		"""
		return self._functions

	@readonly
	def Lines(self) -> dict[int, Line]:
		"""
		Read-only property to access the lines (:attr:`_lines`).

		:returns: The lines, by number.
		"""
		return self._lines

	@readonly
	def Branches(self) -> list[Branch]:
		"""
		Read-only property to access the branches (:attr:`_branches`).

		:returns: The branches, in the tracefile's order.
		"""
		return self._branches

	@readonly
	def Conditions(self) -> list[Condition]:
		"""
		Read-only property to access the conditions of MC/DC coverage (:attr:`_conditions`).

		:returns: The conditions, in the tracefile's order.
		"""
		return self._conditions

	@readonly
	def FunctionsFound(self) -> Nullable[int]:
		"""
		Read-only property to access the number of functions, as the section states it (:attr:`_functionsFound`).

		:returns: The number from record ``FNF``, or ``None`` if not stated.
		"""
		return self._functionsFound

	@readonly
	def FunctionsHit(self) -> Nullable[int]:
		"""
		Read-only property to access the number of functions called, as the section states it (:attr:`_functionsHit`).

		:returns: The number from record ``FNH``, or ``None`` if not stated.
		"""
		return self._functionsHit

	@readonly
	def BranchesFound(self) -> Nullable[int]:
		"""
		Read-only property to access the number of branches, as the section states it (:attr:`_branchesFound`).

		:returns: The number from record ``BRF``, or ``None`` if not stated.
		"""
		return self._branchesFound

	@readonly
	def BranchesHit(self) -> Nullable[int]:
		"""
		Read-only property to access the number of branches taken, as the section states it (:attr:`_branchesHit`).

		:returns: The number from record ``BRH``, or ``None`` if not stated.
		"""
		return self._branchesHit

	@readonly
	def ConditionsFound(self) -> Nullable[int]:
		"""
		Read-only property to access the number of conditions, as the section states it (:attr:`_conditionsFound`).

		:returns: The number from record ``MCF``, or ``None`` if not stated.
		"""
		return self._conditionsFound

	@readonly
	def ConditionsHit(self) -> Nullable[int]:
		"""
		Read-only property to access the number of conditions sensitized, as the section states it
		(:attr:`_conditionsHit`).

		:returns: The number from record ``MCH``, or ``None`` if not stated.
		"""
		return self._conditionsHit

	@readonly
	def LinesFound(self) -> Nullable[int]:
		"""
		Read-only property to access the number of instrumented lines, as the section states it (:attr:`_linesFound`).

		:returns: The number from record ``LF``, or ``None`` if not stated.
		"""
		return self._linesFound

	@readonly
	def LinesHit(self) -> Nullable[int]:
		"""
		Read-only property to access the number of lines, which ran, as the section states it (:attr:`_linesHit`).

		:returns: The number from record ``LH``, or ``None`` if not stated.
		"""
		return self._linesHit
