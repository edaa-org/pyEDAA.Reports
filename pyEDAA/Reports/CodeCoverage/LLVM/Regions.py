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
#
"""
The source regions of LLVM's code coverage export: regions, branch regions and MC/DC records.

A report states a region as a JSON array - a tuple of numbers. A region names its source range by line and column, and
the file by an index into the file paths of its function or expansion. A region's constructor takes typed values; its
classmethod ``Parse`` reads the region's JSON array.
"""
from __future__            import annotations

from enum                  import Enum
from typing                import Any, Iterable, Optional as Nullable, Self

from pyTooling.Common      import getFullyQualifiedName
from pyTooling.Decorators  import export, readonly
from pyTooling.MetaClasses import ExtendedType


@export
class RegionKind(Enum):
	"""The kind of a source region, as LLVM's coverage mapping numbers it."""

	Code =         0  #: Code associated with a counter.
	Expansion =    1  #: The source range of a macro expansion, which maps to a file of its own.
	Skipped =      2  #: Code skipped by the preprocessor - e.g. by ``#if 0`` -, empty lines and comments.
	Gap =          3  #: Code between two regions, whose count is a line's count only, if no other region starts on it.
	Branch =       4  #: A condition with the counts of its true and false outcome.
	MCDCDecision = 5  #: A decision of conditions, measured for MC/DC.
	MCDCBranch =   6  #: A condition of a decision measured for MC/DC, with the counts of its true and false outcome.


@export
class Base(metaclass=ExtendedType, slots=True):
	"""
	Base-class of the source regions: a source range, the file it is in, the file it expands to, and its kind.
	"""

	_lineStart:      int            #: Line the region starts at.
	_columnStart:    int            #: Column the region starts at.
	_lineEnd:        int            #: Line the region ends at.
	_columnEnd:      int            #: Column the region ends at.
	_fileID:         Nullable[int]  #: Index of the region's file in the file paths of its function or expansion.
	_expandedFileID: int            #: Index of the file an expansion region expands to.
	_kind:           RegionKind     #: The kind of the region.

	def __init__(
		self,
		lineStart: int,
		columnStart: int,
		lineEnd: int,
		columnEnd: int,
		fileID: Nullable[int],
		expandedFileID: int,
		kind: RegionKind
	) -> None:
		"""
		Initialize the source range, the region's files and its kind.

		:param lineStart:      Line the region starts at.
		:param columnStart:    Column the region starts at.
		:param lineEnd:        Line the region ends at.
		:param columnEnd:      Column the region ends at.
		:param fileID:         Index of the region's file in the file paths of its function or expansion; ``None``, if not
		                       stated.
		:param expandedFileID: Index of the file an expansion region expands to.
		:param kind:           The kind of the region.
		:raises ValueError:    If parameter ``lineStart``, ``columnStart``, ``lineEnd`` or ``columnEnd`` is ``None``.
		:raises TypeError:     If parameter ``lineStart``, ``columnStart``, ``lineEnd`` or ``columnEnd`` isn't of type
		                       :class:`int`.
		:raises ValueError:    If parameter ``lineStart``, ``columnStart``, ``lineEnd`` or ``columnEnd`` is less than 1.
		:raises TypeError:     If parameter ``fileID`` isn't of type :class:`int`.
		:raises ValueError:    If parameter ``fileID`` is negative.
		:raises ValueError:    If parameter ``expandedFileID`` is ``None``.
		:raises TypeError:     If parameter ``expandedFileID`` isn't of type :class:`int`.
		:raises ValueError:    If parameter ``expandedFileID`` is negative.
		:raises ValueError:    If parameter ``kind`` is ``None``.
		:raises TypeError:     If parameter ``kind`` isn't of type :class:`RegionKind`.
		"""
		for name, position in (
			("lineStart", lineStart), ("columnStart", columnStart), ("lineEnd", lineEnd), ("columnEnd", columnEnd)
		):
			if position is None:
				raise ValueError(f"Parameter '{name}' is None.")
			elif not isinstance(position, int):
				ex = TypeError(f"Parameter '{name}' is not of type 'int'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(position)}'.")
				raise ex
			elif position < 1:
				ex = ValueError(f"Parameter '{name}' is less than 1.")
				ex.add_note(f"Got value '{position}'.")
				raise ex

		if fileID is not None:
			if not isinstance(fileID, int):
				ex = TypeError(f"Parameter 'fileID' is not of type 'int'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(fileID)}'.")
				raise ex
			elif fileID < 0:
				ex = ValueError(f"Parameter 'fileID' is negative.")
				ex.add_note(f"Got value '{fileID}'.")
				raise ex

		if expandedFileID is None:
			raise ValueError(f"Parameter 'expandedFileID' is None.")
		elif not isinstance(expandedFileID, int):
			ex = TypeError(f"Parameter 'expandedFileID' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(expandedFileID)}'.")
			raise ex
		elif expandedFileID < 0:
			ex = ValueError(f"Parameter 'expandedFileID' is negative.")
			ex.add_note(f"Got value '{expandedFileID}'.")
			raise ex

		if kind is None:
			raise ValueError(f"Parameter 'kind' is None.")
		elif not isinstance(kind, RegionKind):
			ex = TypeError(f"Parameter 'kind' is not of type 'RegionKind'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(kind)}'.")
			raise ex

		self._lineStart =      lineStart
		self._columnStart =    columnStart
		self._lineEnd =        lineEnd
		self._columnEnd =      columnEnd
		self._fileID =         fileID
		self._expandedFileID = expandedFileID
		self._kind =           kind

	@readonly
	def LineStart(self) -> int:
		"""
		Read-only property to access the line the region starts at (:attr:`_lineStart`).

		:returns: The line number, counted from 1.
		"""
		return self._lineStart

	@readonly
	def ColumnStart(self) -> int:
		"""
		Read-only property to access the column the region starts at (:attr:`_columnStart`).

		:returns: The column number, counted from 1.
		"""
		return self._columnStart

	@readonly
	def LineEnd(self) -> int:
		"""
		Read-only property to access the line the region ends at (:attr:`_lineEnd`).

		:returns: The line number, counted from 1.
		"""
		return self._lineEnd

	@readonly
	def ColumnEnd(self) -> int:
		"""
		Read-only property to access the column the region ends at (:attr:`_columnEnd`).

		:returns: The column number, counted from 1.
		"""
		return self._columnEnd

	@readonly
	def FileID(self) -> Nullable[int]:
		"""
		Read-only property to access the index of the region's file (:attr:`_fileID`).

		:returns: The index into the file paths of the region's function or expansion; ``None`` for an MC/DC record before
		          format version 3.0.1.
		"""
		return self._fileID

	@readonly
	def ExpandedFileID(self) -> int:
		"""
		Read-only property to access the index of the file an expansion region expands to (:attr:`_expandedFileID`).

		:returns: The index into the file paths of the region's function or expansion; ``0`` for other kinds of regions.
		"""
		return self._expandedFileID

	@readonly
	def Kind(self) -> RegionKind:
		"""
		Read-only property to access the kind of the region (:attr:`_kind`).

		:returns: The kind.
		"""
		return self._kind


@export
class Region(Base):
	"""
	A region of a function or an expansion: a source range with a count.

	A region is ``[lineStart, columnStart, lineEnd, columnEnd, count, fileID, expandedFileID, kind]``.
	"""

	_count: int  #: How often the region's code ran.

	def __init__(
		self,
		lineStart: int,
		columnStart: int,
		lineEnd: int,
		columnEnd: int,
		count: int,
		fileID: int,
		expandedFileID: int,
		kind: RegionKind
	) -> None:
		"""
		Initialize a region.

		:param lineStart:      Line the region starts at.
		:param columnStart:    Column the region starts at.
		:param lineEnd:        Line the region ends at.
		:param columnEnd:      Column the region ends at.
		:param count:          How often the region's code ran.
		:param fileID:         Index of the region's file in the file paths of its function or expansion.
		:param expandedFileID: Index of the file an expansion region expands to.
		:param kind:           The kind of the region.
		:raises ValueError:    If parameter ``fileID`` is ``None``.
		:raises ValueError:    If parameter ``count`` is ``None``.
		:raises TypeError:     If parameter ``count`` isn't of type :class:`int`.
		:raises ValueError:    If parameter ``count`` is negative.
		"""
		super().__init__(lineStart, columnStart, lineEnd, columnEnd, fileID, expandedFileID, kind)

		if fileID is None:
			raise ValueError(f"Parameter 'fileID' is None.")

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

		self._count = count

	@classmethod
	def Parse(cls, region: list[Any]) -> Self:
		"""
		Parse a region from its JSON array.

		:param region: The JSON array of the region.
		:returns:      The region.
		"""
		return cls(*region[:7], RegionKind(region[7]))

	@readonly
	def Count(self) -> int:
		"""
		Read-only property to access how often the region's code ran (:attr:`_count`).

		:returns: The count.
		"""
		return self._count


@export
class BranchRegion(Base):
	"""
	A branch region: a condition with the counts of its true and false outcome.

	A branch region is ``[lineStart, columnStart, lineEnd, columnEnd, trueCount, falseCount, fileID, expandedFileID,
	kind]``.
	"""

	_trueCount:  int  #: How often the condition was true.
	_falseCount: int  #: How often the condition was false.

	def __init__(
		self,
		lineStart: int,
		columnStart: int,
		lineEnd: int,
		columnEnd: int,
		trueCount: int,
		falseCount: int,
		fileID: int,
		expandedFileID: int,
		kind: RegionKind
	) -> None:
		"""
		Initialize a branch region.

		:param lineStart:      Line the branch region starts at.
		:param columnStart:    Column the branch region starts at.
		:param lineEnd:        Line the branch region ends at.
		:param columnEnd:      Column the branch region ends at.
		:param trueCount:      How often the condition was true.
		:param falseCount:     How often the condition was false.
		:param fileID:         Index of the branch region's file in the file paths of its function or expansion.
		:param expandedFileID: Index of the file an expansion region expands to; ``0`` for a branch region.
		:param kind:           The kind of the region: a branch, or a condition measured for MC/DC.
		:raises ValueError:    If parameter ``fileID`` is ``None``.
		:raises ValueError:    If parameter ``trueCount`` or ``falseCount`` is ``None``.
		:raises TypeError:     If parameter ``trueCount`` or ``falseCount`` isn't of type :class:`int`.
		:raises ValueError:    If parameter ``trueCount`` or ``falseCount`` is negative.
		"""
		super().__init__(lineStart, columnStart, lineEnd, columnEnd, fileID, expandedFileID, kind)

		if fileID is None:
			raise ValueError(f"Parameter 'fileID' is None.")

		for name, value in (("trueCount", trueCount), ("falseCount", falseCount)):
			if value is None:
				raise ValueError(f"Parameter '{name}' is None.")
			elif not isinstance(value, int):
				ex = TypeError(f"Parameter '{name}' is not of type 'int'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
				raise ex
			elif value < 0:
				ex = ValueError(f"Parameter '{name}' is negative.")
				ex.add_note(f"Got value '{value}'.")
				raise ex

		self._trueCount =  trueCount
		self._falseCount = falseCount

	@classmethod
	def Parse(cls, branch: list[Any]) -> Self:
		"""
		Parse a branch region from its JSON array.

		:param branch: The JSON array of the branch region.
		:returns:      The branch region.
		"""
		return cls(*branch[:8], RegionKind(branch[8]))

	@readonly
	def TrueCount(self) -> int:
		"""
		Read-only property to access how often the condition was true (:attr:`_trueCount`).

		:returns: The count.
		"""
		return self._trueCount

	@readonly
	def FalseCount(self) -> int:
		"""
		Read-only property to access how often the condition was false (:attr:`_falseCount`).

		:returns: The count.
		"""
		return self._falseCount


@export
class TestVector(metaclass=ExtendedType, slots=True):
	"""
	A test vector of an MC/DC decision - in format version 3.1.0 -: the values of its conditions, and the outcome.
	"""

	_conditions: list[Nullable[bool]]  #: The values of the conditions; ``None`` for a condition not evaluated.
	_executed:   bool                  #: Whether the test vector was executed.
	_result:     Nullable[bool]        #: The outcome of the decision.

	def __init__(self, conditions: Iterable[Nullable[bool]], executed: bool, result: Nullable[bool]) -> None:
		"""
		Initialize a test vector.

		:param conditions:  The values of the conditions; ``None`` for a condition not evaluated.
		:param executed:    Whether the test vector was executed.
		:param result:      The outcome of the decision.
		:raises ValueError: If parameter ``conditions`` is ``None``.
		:raises TypeError:  If parameter ``conditions`` isn't iterable.
		:raises TypeError:  If parameter ``conditions`` contains an element not of type :class:`bool`, other than ``None``.
		:raises ValueError: If parameter ``executed`` is ``None``.
		:raises TypeError:  If parameter ``executed`` isn't of type :class:`bool`.
		:raises TypeError:  If parameter ``result`` isn't of type :class:`bool`.
		"""
		if conditions is None:
			raise ValueError(f"Parameter 'conditions' is None.")
		elif not isinstance(conditions, Iterable):
			ex = TypeError(f"Parameter 'conditions' is not iterable.")
			ex.add_note(f"Got type '{getFullyQualifiedName(conditions)}'.")
			raise ex

		if executed is None:
			raise ValueError(f"Parameter 'executed' is None.")
		elif not isinstance(executed, bool):
			ex = TypeError(f"Parameter 'executed' is not of type 'bool'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(executed)}'.")
			raise ex

		if result is not None and not isinstance(result, bool):
			ex = TypeError(f"Parameter 'result' is not of type 'bool'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(result)}'.")
			raise ex

		self._conditions = []
		self._executed =   executed
		self._result =     result

		for condition in conditions:
			if condition is not None and not isinstance(condition, bool):
				ex = TypeError(f"Parameter 'conditions' contains an element not of type 'bool'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(condition)}'.")
				raise ex

			self._conditions.append(condition)

	@classmethod
	def Parse(cls, testVector: dict[str, Any]) -> Self:
		"""
		Parse a test vector from its JSON object.

		:param testVector: The JSON object of the test vector.
		:returns:          The test vector.
		"""
		return cls(testVector["conditions"], testVector["executed"], testVector["result"])

	@readonly
	def Conditions(self) -> list[Nullable[bool]]:
		"""
		Read-only property to access the values of the conditions (:attr:`_conditions`).

		:returns: The values, by condition; ``None`` for a condition not evaluated.
		"""
		return self._conditions

	@readonly
	def Executed(self) -> bool:
		"""
		Read-only property to access whether the test vector was executed (:attr:`_executed`).

		:returns: ``True`` for an executed test vector; ``False`` for a missing one, listed by
		          ``-show-mcdc-non-executed-vectors``.
		"""
		return self._executed

	@readonly
	def Result(self) -> Nullable[bool]:
		"""
		Read-only property to access the outcome of the decision (:attr:`_result`).

		:returns: The outcome.
		"""
		return self._result


@export
class MCDCRecord(Base):
	"""
	An MC/DC record: a decision of conditions, and for each condition, whether a pair of test vectors showed its
	independent effect on the outcome.

	The record's array grew with the format version: ``[lineStart, columnStart, lineEnd, columnEnd, expandedFileID, kind,
	conditions]`` in 2.0.1; version 3.0.0 added the numbers of true and false decisions after the source range, version
	3.0.1 the ``fileID`` before ``expandedFileID``, and version 3.1.0 the test vectors at the end.
	"""

	_trueDecisions:  Nullable[int]     #: Number of executed test vectors with the outcome true, if stated.
	_falseDecisions: Nullable[int]     #: Number of executed test vectors with the outcome false, if stated.
	_conditions:     list[bool]        #: Whether a pair of test vectors showed the independent effect, by condition.
	_testVectors:    list[TestVector]  #: The test vectors; empty before format version 3.1.0.

	def __init__(
		self,
		lineStart: int,
		columnStart: int,
		lineEnd: int,
		columnEnd: int,
		fileID: Nullable[int],
		expandedFileID: int,
		kind: RegionKind,
		conditions: Iterable[bool],
		trueDecisions: Nullable[int] = None,
		falseDecisions: Nullable[int] = None,
		testVectors: Nullable[Iterable[TestVector]] = None
	) -> None:
		"""
		Initialize an MC/DC record.

		:param lineStart:      Line the decision starts at.
		:param columnStart:    Column the decision starts at.
		:param lineEnd:        Line the decision ends at.
		:param columnEnd:      Column the decision ends at.
		:param fileID:         Index of the decision's file in the file paths of its function or expansion; ``None``, if
		                       not stated.
		:param expandedFileID: Index of the file an expansion region expands to; ``0`` for an MC/DC record.
		:param kind:           The kind of the region: an MC/DC decision.
		:param conditions:     Whether a pair of test vectors showed the independent effect, by condition.
		:param trueDecisions:  Optional, number of executed test vectors with the outcome true. Default: ``None``.
		:param falseDecisions: Optional, number of executed test vectors with the outcome false. Default: ``None``.
		:param testVectors:    Optional, the test vectors. Default: none.
		:raises TypeError:     If parameter ``trueDecisions`` or ``falseDecisions`` isn't of type :class:`int`.
		:raises ValueError:    If parameter ``trueDecisions`` or ``falseDecisions`` is negative.
		:raises ValueError:    If parameter ``conditions`` is ``None``.
		:raises TypeError:     If parameter ``conditions`` isn't iterable.
		:raises TypeError:     If parameter ``conditions`` contains an element not of type :class:`bool`.
		:raises TypeError:     If parameter ``testVectors`` isn't iterable.
		:raises TypeError:     If parameter ``testVectors`` contains an element not of type :class:`TestVector`.
		"""
		super().__init__(lineStart, columnStart, lineEnd, columnEnd, fileID, expandedFileID, kind)

		for name, value in (("trueDecisions", trueDecisions), ("falseDecisions", falseDecisions)):
			if value is None:
				continue
			elif not isinstance(value, int):
				ex = TypeError(f"Parameter '{name}' is not of type 'int'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
				raise ex
			elif value < 0:
				ex = ValueError(f"Parameter '{name}' is negative.")
				ex.add_note(f"Got value '{value}'.")
				raise ex

		if conditions is None:
			raise ValueError(f"Parameter 'conditions' is None.")
		elif not isinstance(conditions, Iterable):
			ex = TypeError(f"Parameter 'conditions' is not iterable.")
			ex.add_note(f"Got type '{getFullyQualifiedName(conditions)}'.")
			raise ex

		self._trueDecisions =  trueDecisions
		self._falseDecisions = falseDecisions
		self._conditions =     []
		self._testVectors =    []

		for condition in conditions:
			if not isinstance(condition, bool):
				ex = TypeError(f"Parameter 'conditions' contains an element not of type 'bool'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(condition)}'.")
				raise ex

			self._conditions.append(condition)

		if testVectors is not None:
			if not isinstance(testVectors, Iterable):
				ex = TypeError(f"Parameter 'testVectors' is not iterable.")
				ex.add_note(f"Got type '{getFullyQualifiedName(testVectors)}'.")
				raise ex

			for testVector in testVectors:
				if not isinstance(testVector, TestVector):
					ex = TypeError(f"Parameter 'testVectors' contains an element not of type 'TestVector'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(testVector)}'.")
					raise ex

				self._testVectors.append(testVector)

	@classmethod
	def Parse(cls, record: list[Any]) -> Self:
		"""
		Parse an MC/DC record from its JSON array, in the shape of its format version.

		:param record: The JSON array of the MC/DC record.
		:returns:      The MC/DC record.
		"""
		if len(record) == 7:
			return cls(*record[:4], None, record[4], RegionKind(record[5]), record[6])
		elif len(record) == 9:
			return cls(*record[:4], None, record[6], RegionKind(record[7]), record[8], record[4], record[5])

		return cls(
			*record[:4], record[6], record[7], RegionKind(record[8]), record[9], record[4], record[5],
			[TestVector.Parse(testVector) for testVector in record[10]] if len(record) > 10 else None
		)

	@readonly
	def TrueDecisions(self) -> Nullable[int]:
		"""
		Read-only property to access the number of executed test vectors with the outcome true (:attr:`_trueDecisions`).

		:returns: The number; ``None`` before format version 3.0.0.
		"""
		return self._trueDecisions

	@readonly
	def FalseDecisions(self) -> Nullable[int]:
		"""
		Read-only property to access the number of executed test vectors with the outcome false (:attr:`_falseDecisions`).

		:returns: The number; ``None`` before format version 3.0.0.
		"""
		return self._falseDecisions

	@readonly
	def Conditions(self) -> list[bool]:
		"""
		Read-only property to access, by condition, whether a pair of test vectors showed its independent effect
		(:attr:`_conditions`).

		:returns: ``True`` for each condition shown to affect the outcome on its own.
		"""
		return self._conditions

	@readonly
	def TestVectors(self) -> list[TestVector]:
		"""
		Read-only property to access the test vectors (:attr:`_testVectors`).

		:returns: The test vectors; empty before format version 3.1.0.
		"""
		return self._testVectors
