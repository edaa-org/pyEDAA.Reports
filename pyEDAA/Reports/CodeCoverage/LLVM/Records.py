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
The records of LLVM's code coverage export: files and functions, and below them segments and macro expansions.

A report states a segment as a JSON array - a tuple of numbers and flags -, a file, a function or an expansion as a
JSON object. A record's constructor takes typed values; its classmethod ``Parse`` reads the record's JSON array or
object. The source regions are in :mod:`~pyEDAA.Reports.CodeCoverage.LLVM.Regions`, the summaries in
:mod:`~pyEDAA.Reports.CodeCoverage.LLVM.Summaries`.
"""
from __future__                                 import annotations

from pathlib                                    import Path
from typing                                     import Any, Iterable, Optional as Nullable, Self

from pyTooling.Common                           import getFullyQualifiedName
from pyTooling.Decorators                       import export, readonly
from pyTooling.MetaClasses                      import ExtendedType

from pyEDAA.Reports.CodeCoverage.LLVM.Regions   import BranchRegion, MCDCRecord, Region, RegionKind
from pyEDAA.Reports.CodeCoverage.LLVM.Summaries import Summary


# A class with a property named like a class - ``Path``, ``Summary`` - can't name that class in the annotation of a
# field: the class body's namespace, where annotations are evaluated, binds the name to the property.
_Path =    Path
_Summary = Summary


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

	def __init__(
		self,
		line: int,
		column: int,
		count: int,
		hasCount: bool,
		isRegionEntry: bool,
		isGapRegion: bool = False
	) -> None:
		"""
		Initialize a segment.

		:param line:          Line the segment starts at.
		:param column:        Column the segment starts at.
		:param count:         The count of the code from here on.
		:param hasCount:      Whether the code from here on has a count.
		:param isRegionEntry: Whether a region starts here.
		:param isGapRegion:   Optional, whether a gap region starts here. Default: ``False``.
		:raises ValueError:   If parameter ``line`` or ``column`` is ``None``.
		:raises TypeError:    If parameter ``line`` or ``column`` isn't of type :class:`int`.
		:raises ValueError:   If parameter ``line`` or ``column`` is less than 1.
		:raises ValueError:   If parameter ``count`` is ``None``.
		:raises TypeError:    If parameter ``count`` isn't of type :class:`int`.
		:raises ValueError:   If parameter ``count`` is negative.
		:raises ValueError:   If parameter ``hasCount``, ``isRegionEntry`` or ``isGapRegion`` is ``None``.
		:raises TypeError:    If parameter ``hasCount``, ``isRegionEntry`` or ``isGapRegion`` isn't of type :class:`bool`.
		"""
		for name, position in (("line", line), ("column", column)):
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

		for name, flag in (("hasCount", hasCount), ("isRegionEntry", isRegionEntry), ("isGapRegion", isGapRegion)):
			if flag is None:
				raise ValueError(f"Parameter '{name}' is None.")
			elif not isinstance(flag, bool):
				ex = TypeError(f"Parameter '{name}' is not of type 'bool'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(flag)}'.")
				raise ex

		self._line =          line
		self._column =        column
		self._count =         count
		self._hasCount =      hasCount
		self._isRegionEntry = isRegionEntry
		self._isGapRegion =   isGapRegion

	@classmethod
	def Parse(cls, segment: list[Any]) -> Self:
		"""
		Parse a segment from its JSON array.

		:param segment: The JSON array of the segment.
		:returns:       The segment.
		"""
		return cls(*segment[:5], segment[5] if len(segment) > 5 else False)

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
class Expansion(metaclass=ExtendedType, slots=True):
	"""
	A macro expansion in a file: the region it is expanded at, the regions of the function it is in, and its branches.
	"""

	_filePaths:     list[Path]          #: The paths of the files, which the file IDs of the regions index.
	_sourceRegion:  Region              #: The region the macro is expanded at.
	_targetRegions: list[Region]        #: The regions of the function the expansion is in.
	_branches:      list[BranchRegion]  #: The branch regions in the expansion, and in the expansions nested in it.

	def __init__(
		self,
		filePaths: Iterable[Path],
		sourceRegion: Region,
		targetRegions: Iterable[Region],
		branches: Nullable[Iterable[BranchRegion]] = None
	) -> None:
		"""
		Initialize an expansion.

		:param filePaths:     The paths of the files, which the file IDs of the regions index.
		:param sourceRegion:  The region the macro is expanded at.
		:param targetRegions: The regions of the function the expansion is in.
		:param branches:      Optional, the branch regions in the expansion, and in the expansions nested in it. Default:
		                      none.
		:raises ValueError:   If parameter ``filePaths`` or ``targetRegions`` is ``None``.
		:raises TypeError:    If parameter ``filePaths``, ``targetRegions`` or ``branches`` isn't iterable.
		:raises TypeError:    If parameter ``filePaths`` contains an element not of type :class:`~pathlib.Path`.
		:raises ValueError:   If parameter ``sourceRegion`` is ``None``.
		:raises TypeError:    If parameter ``sourceRegion`` isn't of type
		                      :class:`~pyEDAA.Reports.CodeCoverage.LLVM.Regions.Region`.
		:raises TypeError:    If parameter ``targetRegions`` contains an element not of type
		                      :class:`~pyEDAA.Reports.CodeCoverage.LLVM.Regions.Region`.
		:raises TypeError:    If parameter ``branches`` contains an element not of type :class:`BranchRegion`.
		"""
		if filePaths is None:
			raise ValueError(f"Parameter 'filePaths' is None.")

		if sourceRegion is None:
			raise ValueError(f"Parameter 'sourceRegion' is None.")
		elif not isinstance(sourceRegion, Region):
			ex = TypeError(f"Parameter 'sourceRegion' is not of type 'Region'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(sourceRegion)}'.")
			raise ex

		if targetRegions is None:
			raise ValueError(f"Parameter 'targetRegions' is None.")

		self._filePaths =     []
		self._sourceRegion =  sourceRegion
		self._targetRegions = []
		self._branches =      []

		for name, elements, elementType, target in (
			("filePaths", filePaths, Path, self._filePaths), ("targetRegions", targetRegions, Region, self._targetRegions),
			("branches", branches, BranchRegion, self._branches)
		):
			if elements is None:
				continue
			elif not isinstance(elements, Iterable):
				ex = TypeError(f"Parameter '{name}' is not iterable.")
				ex.add_note(f"Got type '{getFullyQualifiedName(elements)}'.")
				raise ex

			for element in elements:
				if not isinstance(element, elementType):
					ex = TypeError(f"Parameter '{name}' contains an element not of type '{elementType.__name__}'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(element)}'.")
					raise ex

				target.append(element)

	@classmethod
	def Parse(cls, expansion: dict[str, Any]) -> Self:
		"""
		Parse an expansion from its JSON object.

		:param expansion: The JSON object of the expansion.
		:returns:         The expansion.
		"""
		return cls(
			[Path(filename.replace("\\", "/")) for filename in expansion["filenames"]],
			Region.Parse(expansion["source_region"]),
			[Region.Parse(region) for region in expansion["target_regions"]],
			[BranchRegion.Parse(branch) for branch in expansion.get("branches", [])]
		)

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
class File(metaclass=ExtendedType, slots=True):
	"""
	A file: its segments, branch regions, MC/DC records and expansions, and its summary.

	A report written with ``-summary-only`` has only the summary, one written with ``-skip-expansions`` no expansions.
	"""

	_path:        _Path               #: The file's path, as the compiler named it.
	_segments:    list[Segment]       #: The segments, by position.
	_branches:    list[BranchRegion]  #: The branch regions of the file's functions.
	_mcdcRecords: list[MCDCRecord]    #: The MC/DC records of the file's functions.
	_expansions:  list[Expansion]     #: The macro expansions in the file.
	_summary:     _Summary            #: The counters llvm-cov computed.

	def __init__(
		self,
		path: Path,
		summary: Summary,
		segments: Nullable[Iterable[Segment]] = None,
		branches: Nullable[Iterable[BranchRegion]] = None,
		mcdcRecords: Nullable[Iterable[MCDCRecord]] = None,
		expansions: Nullable[Iterable[Expansion]] = None
	) -> None:
		"""
		Initialize a file.

		:param path:        The file's path, as the compiler named it.
		:param summary:     The counters llvm-cov computed.
		:param segments:    Optional, the segments, by position. Default: none.
		:param branches:    Optional, the branch regions of the file's functions. Default: none.
		:param mcdcRecords: Optional, the MC/DC records of the file's functions. Default: none.
		:param expansions:  Optional, the macro expansions in the file. Default: none.
		:raises ValueError: If parameter ``path`` is ``None``.
		:raises TypeError:  If parameter ``path`` isn't of type :class:`~pathlib.Path`.
		:raises ValueError: If parameter ``summary`` is ``None``.
		:raises TypeError:  If parameter ``summary`` isn't of type
		                    :class:`~pyEDAA.Reports.CodeCoverage.LLVM.Summaries.Summary`.
		:raises TypeError:  If parameter ``segments``, ``branches``, ``mcdcRecords`` or ``expansions`` isn't iterable.
		:raises TypeError:  If parameter ``segments`` contains an element not of type :class:`Segment`.
		:raises TypeError:  If parameter ``branches`` contains an element not of type :class:`BranchRegion`.
		:raises TypeError:  If parameter ``mcdcRecords`` contains an element not of type :class:`MCDCRecord`.
		:raises TypeError:  If parameter ``expansions`` contains an element not of type :class:`Expansion`.
		"""
		if path is None:
			raise ValueError(f"Parameter 'path' is None.")
		elif not isinstance(path, Path):
			ex = TypeError(f"Parameter 'path' is not of type 'Path'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(path)}'.")
			raise ex

		if summary is None:
			raise ValueError(f"Parameter 'summary' is None.")
		elif not isinstance(summary, Summary):
			ex = TypeError(f"Parameter 'summary' is not of type 'Summary'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(summary)}'.")
			raise ex

		self._path =        path
		self._segments =    []
		self._branches =    []
		self._mcdcRecords = []
		self._expansions =  []
		self._summary =     summary

		for name, elements, elementType, target in (
			("segments", segments, Segment, self._segments), ("branches", branches, BranchRegion, self._branches),
			("mcdcRecords", mcdcRecords, MCDCRecord, self._mcdcRecords),
			("expansions", expansions, Expansion, self._expansions)
		):
			if elements is None:
				continue
			elif not isinstance(elements, Iterable):
				ex = TypeError(f"Parameter '{name}' is not iterable.")
				ex.add_note(f"Got type '{getFullyQualifiedName(elements)}'.")
				raise ex

			for element in elements:
				if not isinstance(element, elementType):
					ex = TypeError(f"Parameter '{name}' contains an element not of type '{elementType.__name__}'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(element)}'.")
					raise ex

				target.append(element)

	@classmethod
	def Parse(cls, file: dict[str, Any]) -> Self:
		"""
		Parse a file from its JSON object.

		:param file: The JSON object of the file.
		:returns:    The file.
		"""
		return cls(
			Path(file["filename"].replace("\\", "/")),
			Summary.Parse(file["summary"]),
			[Segment.Parse(segment) for segment in file.get("segments", [])],
			[BranchRegion.Parse(branch) for branch in file.get("branches", [])],
			[MCDCRecord.Parse(record) for record in file.get("mcdc_records", [])],
			[Expansion.Parse(expansion) for expansion in file.get("expansions", [])]
		)

	@readonly
	def Path(self) -> Path:
		"""
		Read-only property to access the file's path (:attr:`_path`).

		:returns: The path, as the compiler named it - usually absolute.
		"""
		return self._path

	@readonly
	def Segments(self) -> list[Segment]:
		"""
		Read-only property to access the segments (:attr:`_segments`).

		:returns: The segments, by position; empty in a summary-only report.
		"""
		return self._segments

	@readonly
	def Branches(self) -> list[BranchRegion]:
		"""
		Read-only property to access the branch regions of the file's functions (:attr:`_branches`).

		Which branch regions of a macro expansion are listed here, depends on the LLVM version.

		:returns: The branch regions.
		"""
		return self._branches

	@readonly
	def MCDCRecords(self) -> list[MCDCRecord]:
		"""
		Read-only property to access the MC/DC records of the file's functions (:attr:`_mcdcRecords`).

		:returns: The MC/DC records.
		"""
		return self._mcdcRecords

	@readonly
	def Expansions(self) -> list[Expansion]:
		"""
		Read-only property to access the macro expansions in the file (:attr:`_expansions`).

		:returns: The expansions.
		"""
		return self._expansions

	@readonly
	def Summary(self) -> Summary:
		"""
		Read-only property to access the counters llvm-cov computed (:attr:`_summary`).

		:returns: The summary.
		"""
		return self._summary


@export
class Function(metaclass=ExtendedType, slots=True):
	"""
	A function - an instantiation of a template is a function of its own -: how often it was called, its regions, branch
	regions and MC/DC records, and the files they are in.
	"""

	_name:        str                 #: The function's name, as the profile names it - e.g. mangled.
	_count:       int                 #: How often the function was called.
	_regions:     list[Region]        #: The regions.
	_branches:    list[BranchRegion]  #: The branch regions.
	_mcdcRecords: list[MCDCRecord]    #: The MC/DC records.
	_filePaths:   list[Path]          #: The paths of the files, which the file IDs of the regions index.

	def __init__(
		self,
		name: str,
		count: int,
		regions: Iterable[Region],
		filePaths: Iterable[Path],
		branches: Nullable[Iterable[BranchRegion]] = None,
		mcdcRecords: Nullable[Iterable[MCDCRecord]] = None
	) -> None:
		"""
		Initialize a function.

		:param name:        The function's name, as the profile names it - e.g. mangled.
		:param count:       How often the function was called.
		:param regions:     The regions.
		:param filePaths:   The paths of the files, which the file IDs of the regions index.
		:param branches:    Optional, the branch regions. Default: none.
		:param mcdcRecords: Optional, the MC/DC records. Default: none.
		:raises ValueError: If parameter ``name`` is ``None``.
		:raises TypeError:  If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError: If parameter ``name`` is empty.
		:raises ValueError: If parameter ``count`` is ``None``.
		:raises TypeError:  If parameter ``count`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``count`` is negative.
		:raises ValueError: If parameter ``regions`` or ``filePaths`` is ``None``.
		:raises TypeError:  If parameter ``regions``, ``filePaths``, ``branches`` or ``mcdcRecords`` isn't iterable.
		:raises TypeError:  If parameter ``regions`` contains an element not of type
		                    :class:`~pyEDAA.Reports.CodeCoverage.LLVM.Regions.Region`.
		:raises TypeError:  If parameter ``filePaths`` contains an element not of type :class:`~pathlib.Path`.
		:raises TypeError:  If parameter ``branches`` contains an element not of type :class:`BranchRegion`.
		:raises TypeError:  If parameter ``mcdcRecords`` contains an element not of type :class:`MCDCRecord`.
		"""
		if name is None:
			raise ValueError(f"Parameter 'name' is None.")
		elif not isinstance(name, str):
			ex = TypeError(f"Parameter 'name' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(name)}'.")
			raise ex
		elif name == "":
			raise ValueError(f"Parameter 'name' is empty.")

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

		if regions is None:
			raise ValueError(f"Parameter 'regions' is None.")

		if filePaths is None:
			raise ValueError(f"Parameter 'filePaths' is None.")

		self._name =        name
		self._count =       count
		self._regions =     []
		self._branches =    []
		self._mcdcRecords = []
		self._filePaths =   []

		for parameterName, elements, elementType, target in (
			("regions", regions, Region, self._regions), ("filePaths", filePaths, Path, self._filePaths),
			("branches", branches, BranchRegion, self._branches),
			("mcdcRecords", mcdcRecords, MCDCRecord, self._mcdcRecords)
		):
			if elements is None:
				continue
			elif not isinstance(elements, Iterable):
				ex = TypeError(f"Parameter '{parameterName}' is not iterable.")
				ex.add_note(f"Got type '{getFullyQualifiedName(elements)}'.")
				raise ex

			for element in elements:
				if not isinstance(element, elementType):
					ex = TypeError(f"Parameter '{parameterName}' contains an element not of type '{elementType.__name__}'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(element)}'.")
					raise ex

				target.append(element)

	@classmethod
	def Parse(cls, function: dict[str, Any]) -> Self:
		"""
		Parse a function from its JSON object.

		:param function: The JSON object of the function.
		:returns:        The function.
		"""
		return cls(
			function["name"],
			function["count"],
			[Region.Parse(region) for region in function["regions"]],
			[Path(filename.replace("\\", "/")) for filename in function["filenames"]],
			[BranchRegion.Parse(branch) for branch in function.get("branches", [])],
			[MCDCRecord.Parse(record) for record in function.get("mcdc_records", [])]
		)

	@readonly
	def Name(self) -> str:
		"""
		Read-only property to access the function's name (:attr:`_name`).

		:returns: The name, as the profile names it: mangled, and prefixed by the file name of its translation unit, if
		          local to it - e.g. ``Statistics.c:Square``.
		"""
		return self._name

	@readonly
	def Count(self) -> int:
		"""
		Read-only property to access how often the function was called (:attr:`_count`).

		:returns: The count.
		"""
		return self._count

	@readonly
	def Regions(self) -> list[Region]:
		"""
		Read-only property to access the regions (:attr:`_regions`).

		:returns: The regions.
		"""
		return self._regions

	@readonly
	def Branches(self) -> list[BranchRegion]:
		"""
		Read-only property to access the branch regions (:attr:`_branches`).

		:returns: The branch regions, also those in macro expansions.
		"""
		return self._branches

	@readonly
	def MCDCRecords(self) -> list[MCDCRecord]:
		"""
		Read-only property to access the MC/DC records (:attr:`_mcdcRecords`).

		:returns: The MC/DC records.
		"""
		return self._mcdcRecords

	@readonly
	def FilePaths(self) -> list[Path]:
		"""
		Read-only property to access the paths of the files, which the file IDs of the regions index (:attr:`_filePaths`).

		:returns: The paths, as the compiler named them.
		"""
		return self._filePaths

	@readonly
	def MainFileID(self) -> Nullable[int]:
		"""
		Read-only property to return the file ID of the file the function is in: the first file no expansion region
		expands to.

		:returns: The index into :attr:`FilePaths`, or ``None`` if every file is expanded to.
		"""
		expanded = {region._expandedFileID for region in self._regions if region._kind is RegionKind.Expansion}
		return next((fileID for fileID in range(len(self._filePaths)) if fileID not in expanded), None)
