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
The records of LLVM's code coverage export below a file or a function: segments, regions, branch regions, MC/DC
records, expansions, and the summaries' counters.

A report states a segment or a region as a JSON array - a tuple of numbers and flags. A region names its source range by
line and column, and the file by an index into the file paths of its function or expansion.
"""
from __future__            import annotations

from enum                  import Enum
from pathlib               import Path
from typing                import Any, Optional as Nullable

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
class Segment(metaclass=ExtendedType, slots=True):
	"""
	A segment of a file: from a position on, the code has a count - until the next segment.

	A segment is ``[line, column, count, hasCount, isRegionEntry, isGapRegion]``. Format version 2.0.0 has no
	``isGapRegion``.
	"""

	_line:          int   #: Line the segment starts at.
	_column:        int   #: Column the segment starts at.
	_count:         int   #: The count of the code from here on.
	_hasCount:      bool  #: Whether the code from here on has a count; false e.g. after a function's end.
	_isRegionEntry: bool  #: Whether a region starts here; false, where a region continues after a nested one.
	_isGapRegion:   bool  #: Whether a gap region starts here.

	def __init__(self, segment: list[Any]) -> None:
		"""
		Initialize the segment from its JSON array.

		:param segment: The JSON array of the segment.
		"""
		self._line =          segment[0]
		self._column =        segment[1]
		self._count =         segment[2]
		self._hasCount =      segment[3]
		self._isRegionEntry = segment[4]
		self._isGapRegion =   segment[5] if len(segment) > 5 else False

	@readonly
	def Line(self) -> int:
		"""
		Read-only property to access the line the segment starts at (:attr:`_line`).

		:returns: The line number, counted from 1.
		"""
		return self._line

	@readonly
	def Column(self) -> int:
		"""
		Read-only property to access the column the segment starts at (:attr:`_column`).

		:returns: The column number, counted from 1.
		"""
		return self._column

	@readonly
	def Count(self) -> int:
		"""
		Read-only property to access the count of the code from the segment's start on (:attr:`_count`).

		:returns: How often the code ran; ``0`` without a count.
		"""
		return self._count

	@readonly
	def HasCount(self) -> bool:
		"""
		Read-only property to access whether the code from the segment's start on has a count (:attr:`_hasCount`).

		:returns: ``False`` e.g. after the end of a function, or in a skipped region.
		"""
		return self._hasCount

	@readonly
	def IsRegionEntry(self) -> bool:
		"""
		Read-only property to access whether a region starts at the segment's start (:attr:`_isRegionEntry`).

		:returns: ``False``, where a region continues after a region nested in it.
		"""
		return self._isRegionEntry

	@readonly
	def IsGapRegion(self) -> bool:
		"""
		Read-only property to access whether a gap region starts at the segment's start (:attr:`_isGapRegion`).

		:returns: ``True`` for a gap region; ``False`` in format version 2.0.0.
		"""
		return self._isGapRegion


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

	def __init__(self, record: list[Any], fileID: Nullable[int], expandedFileID: int, kind: int) -> None:
		"""
		Initialize the source range from the first four elements of a region's JSON array, and the region's files and kind.

		:param record:         The JSON array of the region.
		:param fileID:         Index of the region's file in the file paths of its function or expansion, if stated.
		:param expandedFileID: Index of the file an expansion region expands to.
		:param kind:           The number of the region's kind.
		"""
		self._lineStart =      record[0]
		self._columnStart =    record[1]
		self._lineEnd =        record[2]
		self._columnEnd =      record[3]
		self._fileID =         fileID
		self._expandedFileID = expandedFileID
		self._kind =           RegionKind(kind)

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

	def __init__(self, region: list[Any]) -> None:
		"""
		Initialize the region from its JSON array.

		:param region: The JSON array of the region.
		"""
		super().__init__(region, region[5], region[6], region[7])

		self._count = region[4]

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

	def __init__(self, branch: list[Any]) -> None:
		"""
		Initialize the branch region from its JSON array.

		:param branch: The JSON array of the branch region.
		"""
		super().__init__(branch, branch[6], branch[7], branch[8])

		self._trueCount =  branch[4]
		self._falseCount = branch[5]

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

	def __init__(self, testVector: dict[str, Any]) -> None:
		"""
		Initialize the test vector from its JSON object.

		:param testVector: The JSON object of the test vector.
		"""
		self._conditions = testVector["conditions"]
		self._executed =   testVector["executed"]
		self._result =     testVector["result"]

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

	def __init__(self, record: list[Any]) -> None:
		"""
		Initialize the MC/DC record from its JSON array, in the shape of its format version.

		:param record: The JSON array of the MC/DC record.
		"""
		if len(record) == 7:
			super().__init__(record, None, record[4], record[5])
		elif len(record) == 9:
			super().__init__(record, None, record[6], record[7])
		else:
			super().__init__(record, record[6], record[7], record[8])

		self._trueDecisions =  record[4] if len(record) > 7 else None
		self._falseDecisions = record[5] if len(record) > 7 else None
		self._conditions =     record[9] if len(record) > 9 else record[-1]
		self._testVectors =    [TestVector(testVector) for testVector in record[10]] if len(record) > 10 else []

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


@export
class Expansion(metaclass=ExtendedType, slots=True):
	"""
	A macro expansion in a file: the region it is expanded at, the regions of the function it is in, and its branches.
	"""

	_filePaths:     list[Path]          #: The paths of the files, which the file IDs of the regions index.
	_sourceRegion:  Region              #: The region the macro is expanded at.
	_targetRegions: list[Region]        #: The regions of the function the expansion is in.
	_branches:      list[BranchRegion]  #: The branch regions in the expansion, and in the expansions nested in it.

	def __init__(self, expansion: dict[str, Any]) -> None:
		"""
		Initialize the expansion from its JSON object.

		:param expansion: The JSON object of the expansion.
		"""
		self._filePaths =     [Path(filename.replace("\\", "/")) for filename in expansion["filenames"]]
		self._sourceRegion =  Region(expansion["source_region"])
		self._targetRegions = [Region(region) for region in expansion["target_regions"]]
		self._branches =      [BranchRegion(branch) for branch in expansion.get("branches", [])]

	@readonly
	def FilePaths(self) -> list[Path]:
		"""
		Read-only property to access the paths of the files, which the file IDs of the regions index (:attr:`_filePaths`).

		:returns: The paths, as the compiler named them.
		"""
		return self._filePaths

	@readonly
	def SourceRegion(self) -> Region:
		"""
		Read-only property to access the region the macro is expanded at (:attr:`_sourceRegion`).

		:returns: The region.
		"""
		return self._sourceRegion

	@readonly
	def TargetRegions(self) -> list[Region]:
		"""
		Read-only property to access the regions of the function the expansion is in (:attr:`_targetRegions`).

		:returns: The regions.
		"""
		return self._targetRegions

	@readonly
	def Branches(self) -> list[BranchRegion]:
		"""
		Read-only property to access the branch regions in the expansion, and in the expansions nested in it
		(:attr:`_branches`).

		:returns: The branch regions; empty before LLVM 12.
		"""
		return self._branches


@export
class Counters(metaclass=ExtendedType, slots=True):
	"""
	The counters of one kind of a summary: how many there are, and how many are covered.

	A summary counts lines, functions, regions, branches and MC/DC conditions.
	"""

	_count:      int            #: Number of lines, functions, regions, branches or MC/DC conditions.
	_covered:    int            #: Number of the covered ones.
	_notCovered: Nullable[int]  #: Number of the uncovered ones, if stated.
	_percent:    float          #: The coverage in percent.

	def __init__(self, counters: dict[str, Any]) -> None:
		"""
		Initialize the counters from their JSON object.

		:param counters: The JSON object of the counters.
		"""
		self._count =      counters["count"]
		self._covered =    counters["covered"]
		self._notCovered = counters.get("notcovered")
		self._percent =    counters["percent"]

	@readonly
	def Count(self) -> int:
		"""
		Read-only property to access the number of lines, functions, regions, branches or MC/DC conditions (:attr:`_count`).

		:returns: The number.
		"""
		return self._count

	@readonly
	def Covered(self) -> int:
		"""
		Read-only property to access the number of covered ones (:attr:`_covered`).

		:returns: The number.
		"""
		return self._covered

	@readonly
	def NotCovered(self) -> Nullable[int]:
		"""
		Read-only property to access the number of uncovered ones (:attr:`_notCovered`).

		:returns: The number, or ``None`` for lines, functions and instantiations, which don't state it.
		"""
		return self._notCovered

	@readonly
	def Percent(self) -> float:
		"""
		Read-only property to access the coverage (:attr:`_percent`).

		:returns: The coverage in percent.
		"""
		return self._percent


@export
class Summary(metaclass=ExtendedType, slots=True):
	"""
	A ``summary``: the counters llvm-cov computed for a file or the whole report.

	llvm-cov counts a file's lines, regions and branches per function, and merges a function's instantiations by taking
	the best one.
	"""

	_lines:          Counters            #: The counters of lines.
	_functions:      Counters            #: The counters of functions, a function's instantiations counted once.
	_instantiations: Counters            #: The counters of function instantiations.
	_regions:        Counters            #: The counters of code regions.
	_branches:       Nullable[Counters]  #: The counters of branch outcomes, if stated.
	_mcdc:           Nullable[Counters]  #: The counters of MC/DC conditions, if stated.

	def __init__(self, summary: dict[str, Any]) -> None:
		"""
		Initialize the summary from its JSON object.

		:param summary: The JSON object ``summary`` or ``totals``.
		"""
		self._lines =          Counters(summary["lines"])
		self._functions =      Counters(summary["functions"])
		self._instantiations = Counters(summary["instantiations"])
		self._regions =        Counters(summary["regions"])
		self._branches =       Counters(summary["branches"]) if "branches" in summary else None
		self._mcdc =           Counters(summary["mcdc"]) if "mcdc" in summary else None

	@readonly
	def Lines(self) -> Counters:
		"""
		Read-only property to access the counters of lines (:attr:`_lines`).

		:returns: The counters.
		"""
		return self._lines

	@readonly
	def Functions(self) -> Counters:
		"""
		Read-only property to access the counters of functions, a function's instantiations counted once
		(:attr:`_functions`).

		:returns: The counters.
		"""
		return self._functions

	@readonly
	def Instantiations(self) -> Counters:
		"""
		Read-only property to access the counters of function instantiations (:attr:`_instantiations`).

		:returns: The counters.
		"""
		return self._instantiations

	@readonly
	def Regions(self) -> Counters:
		"""
		Read-only property to access the counters of code regions (:attr:`_regions`).

		:returns: The counters.
		"""
		return self._regions

	@readonly
	def Branches(self) -> Nullable[Counters]:
		"""
		Read-only property to access the counters of branch outcomes - two per branch region - (:attr:`_branches`).

		:returns: The counters, or ``None`` before LLVM 12.
		"""
		return self._branches

	@readonly
	def MCDC(self) -> Nullable[Counters]:
		"""
		Read-only property to access the counters of MC/DC conditions (:attr:`_mcdc`).

		:returns: The counters, or ``None`` before LLVM 18.
		"""
		return self._mcdc
