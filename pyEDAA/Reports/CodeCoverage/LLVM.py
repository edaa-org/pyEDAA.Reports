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
LLVM's JSON code coverage export: a model of the format, read from a report and converted to the common model.

``llvm-cov export -format=text`` writes the format - type ``llvm.coverage.json.export`` - from the source-based code
coverage of Clang, and of other compilers based on LLVM, e.g. rustc or Swift. A report is validated against the JSON
Schema :file:`LLVM-Coverage-JSON.schema.json`, reverse-engineered from llvm-cov, which accepts the format versions
2.0.0 to 3.1.0. The format's model keeps what the report states: a :class:`Document` holds :class:`File` records - each
with its segments, branch regions, MC/DC records, expansions and summary -, and :class:`Function` records - each with
its regions, branch regions and MC/DC records.

* A report states a segment (:class:`Segment`) as a JSON array - a tuple of numbers and flags -, a file, a function or
  an expansion (:class:`Expansion`) as a JSON object.
* A report states a source region as a JSON array, a tuple of numbers: a :class:`Region`, a :class:`BranchRegion` or a
  :class:`MCDCRecord` with its :class:`TestVector` objects. A region names its source range by line and column, and
  the file by an index into the file paths of its function or expansion; :attr:`Base.FilePath` and :attr:`Base.File`
  look the index up.
* A summary (:class:`Summary`) holds the counters (:class:`Counters`) llvm-cov computed for a file or the whole report.

Each class of the format's model takes typed values in its constructor, so a model can be built by hand, too. A
classmethod ``Parse`` reads the class' JSON element and calls the constructor; :meth:`Document.Convert` parses a
report's files, functions and totals with it. Every element (:class:`Element`) knows the element containing it and the
report's root.

:meth:`Document.ToCoverageSummary` converts the model to the common model of :mod:`pyEDAA.Reports.CodeCoverage`:

* A file's path is relative to the directory common to all files, which becomes the report's source directory.
* A line's count is derived from the file's segments, as ``llvm-cov show`` derives it: the line is executable, if a
  region with a count starts on it, or a region with a count continues from a previous line - unless a skipped region
  starts the line. Its count is the largest count of the regions starting on it - gap regions excluded - and of the
  region continuing from a previous line.
* A branch region becomes two branches - its true and its false outcome - of the line it starts at, or of the line its
  macro is expanded at. The branch regions of a function's instantiations, e.g. of a template, are summed. A line with
  an outcome never taken is partially covered.
* A file becomes a source file unit, and each function a function of its file's unit, named as the report names it -
  without the file name of its translation unit, which prefixes a function local to it, e.g. ``Statistics.c:Square``.
  The format doesn't demangle C++ names.

.. rubric:: Example

.. code-block:: Python

   from pathlib import Path
   from pyEDAA.Reports.CodeCoverage.LLVM import Document

   report = Document(Path("coverage.json"), analyzeAndConvert=True)
   summary = report.ToCoverageSummary()
   print(f"{summary.FileCount} files: {summary.LineCoverage:.1%} of lines, {summary.BranchCoverage:.1%} of branches")
"""
from __future__                  import annotations

from enum                        import Enum
from json                        import JSONDecodeError, loads
from pathlib                     import Path
from re                          import match
from typing                      import Any, ClassVar, Generic, Iterable, Optional as Nullable, Self, TypeVar

from pyTooling.Common            import getFullyQualifiedName, readResourceFile
from pyTooling.Decorators        import export, readonly
from pyTooling.Exceptions        import ToolingException
from pyTooling.MetaClasses       import ExtendedType
from pyTooling.Stopwatch         import Stopwatch
from pyTooling.Versioning        import SemanticVersion

from pyEDAA.Reports              import Resources
from pyEDAA.Reports.CodeCoverage import AlreadyInCoverageReportError, Branch as cc_Branch, CodeCoverageError, \
                                        CoverageSummary, DuplicateFileError, Document as cc_Document, File as cc_File, \
                                        Function as cc_Function, Line as cc_Line, LineCoverageStatus, \
                                        SourceFile as cc_SourceFile


__all__ = ["SCHEMA"]

SCHEMA = "LLVM-Coverage-JSON.schema.json"  #: The JSON Schema a report is validated against.

# A class with a property named like a class - ``Path``, ``Summary`` - can't name that class in the annotation of a
# field: the class body's namespace, where annotations are evaluated, binds the name to the property.
_Path = Path

ParentType = TypeVar("ParentType")


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
class Element(Generic[ParentType], metaclass=ExtendedType, slots=True):
	"""
	Base-class of every element of the format's model: a reference to the element containing it, and to the report's
	root.

	A container connects the elements given to its constructor; an element created with a ``parent`` is added to the
	parent's collection. When a file or function joins a report, the report becomes the root of every element below it.
	"""

	_PARENT_TYPE: ClassVar[tuple[type, ...]]  #: The types a parent may have; assigned below the classes.

	_parent: Nullable[ParentType]  #: The element containing this one, or ``None``.
	_root:   Nullable[Report]      #: The report's root, or ``None`` while the element isn't part of a report.

	def __init__(self, *, parent: Nullable[ParentType] = None) -> None:
		"""
		Initialize an element with its parent and the parent's root.

		The parent doesn't list the element yet: the class adds it to the parent's collection, after setting its fields.

		:param parent:     Optional, the element containing this one. Default: ``None``.
		:raises TypeError: If parameter ``parent`` isn't of a type this class declares in :attr:`_PARENT_TYPE`.
		"""
		if parent is None:
			self._parent = None
			self._root =   None
		elif not isinstance(parent, self._PARENT_TYPE):
			typeNames = " or ".join(f"'{parentType.__name__}'" for parentType in self._PARENT_TYPE)
			ex = TypeError(f"Parameter 'parent' is not of type {typeNames}.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex
		else:
			self._parent = parent
			self._root =   parent._root

	@readonly
	def Parent(self) -> Nullable[ParentType]:
		"""
		Read-only property to access the element containing this one (:attr:`_parent`).

		:returns: The parent, or ``None`` if the element belongs to none.
		"""
		return self._parent

	@readonly
	def Root(self) -> Nullable[Report]:
		"""
		Read-only property to access the report's root (:attr:`_root`).

		:returns: The report, or ``None`` while the element isn't part of a report.
		"""
		return self._root

	def _SetRoot(self, root: Nullable[Report]) -> None:
		"""
		Set the report's root of the element.

		A class containing elements overrides it, to set the root of those too.

		:param root: The report's root, or ``None`` while the element isn't part of a report.
		"""
		self._root = root


@export
class Base(Element[ParentType]):
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
		kind: RegionKind,
		*,
		parent: Nullable[ParentType] = None
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
		:param parent:         Optional, the element containing the region. Default: ``None``.
		:raises ValueError:    If parameter ``lineStart`` is ``None``.
		:raises TypeError:     If parameter ``lineStart`` isn't of type :class:`int`.
		:raises ValueError:    If parameter ``lineStart`` is less than 1.
		:raises ValueError:    If parameter ``columnStart`` is ``None``.
		:raises TypeError:     If parameter ``columnStart`` isn't of type :class:`int`.
		:raises ValueError:    If parameter ``columnStart`` is less than 1.
		:raises ValueError:    If parameter ``lineEnd`` is ``None``.
		:raises TypeError:     If parameter ``lineEnd`` isn't of type :class:`int`.
		:raises ValueError:    If parameter ``lineEnd`` is less than 1.
		:raises ValueError:    If parameter ``columnEnd`` is ``None``.
		:raises TypeError:     If parameter ``columnEnd`` isn't of type :class:`int`.
		:raises ValueError:    If parameter ``columnEnd`` is less than 1.
		:raises TypeError:     If parameter ``fileID`` isn't of type :class:`int`.
		:raises ValueError:    If parameter ``fileID`` is negative.
		:raises ValueError:    If parameter ``fileID`` is no index into the file paths of parameter ``parent``.
		:raises ValueError:    If parameter ``expandedFileID`` is ``None``.
		:raises TypeError:     If parameter ``expandedFileID`` isn't of type :class:`int`.
		:raises ValueError:    If parameter ``expandedFileID`` is negative.
		:raises ValueError:    If parameter ``expandedFileID`` of an expansion region is no index into the file paths of
		                       parameter ``parent``.
		:raises ValueError:    If parameter ``kind`` is ``None``.
		:raises TypeError:     If parameter ``kind`` isn't of type :class:`RegionKind`.
		:raises TypeError:     If parameter ``parent`` isn't of a type this class declares in :attr:`_PARENT_TYPE`.
		"""
		super().__init__(parent=parent)

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
				ex = TypeError("Parameter 'fileID' is not of type 'int'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(fileID)}'.")
				raise ex
			elif fileID < 0:
				ex = ValueError("Parameter 'fileID' is negative.")
				ex.add_note(f"Got value '{fileID}'.")
				raise ex

		if expandedFileID is None:
			raise ValueError("Parameter 'expandedFileID' is None.")
		elif not isinstance(expandedFileID, int):
			ex = TypeError("Parameter 'expandedFileID' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(expandedFileID)}'.")
			raise ex
		elif expandedFileID < 0:
			ex = ValueError("Parameter 'expandedFileID' is negative.")
			ex.add_note(f"Got value '{expandedFileID}'.")
			raise ex

		if kind is None:
			raise ValueError("Parameter 'kind' is None.")
		elif not isinstance(kind, RegionKind):
			ex = TypeError("Parameter 'kind' is not of type 'RegionKind'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(kind)}'.")
			raise ex

		if isinstance(parent, (Function, Expansion)):
			for name, value in (
				("fileID", fileID), ("expandedFileID", expandedFileID if kind is RegionKind.Expansion else None)
			):
				if value is not None and value >= len(parent._filePaths):
					ex = ValueError(f"Parameter '{name}' is no index into the file paths of parameter 'parent'.")
					ex.add_note(f"Got value '{value}' for {len(parent._filePaths)} file paths.")
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

		For a region listed by a file, the index refers to the file paths of a function the report doesn't name;
		:attr:`FilePath` is the file's path then.

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

	@readonly
	def FilePath(self) -> Nullable[Path]:
		"""
		Read-only property to return the path of the region's file.

		A region of a function or expansion names its file by :attr:`FileID`, an index into the parent's file paths. A
		region listed by a file lies in that file.

		:returns: The path, as the compiler named it; ``None`` if the region belongs to no element, or for an MC/DC record
		          of a function before format version 3.0.1, which states no file.
		"""
		if self._parent is None:
			return None
		elif isinstance(self._parent, File):
			return self._parent._path
		elif self._fileID is None:
			return None

		return self._parent._filePaths[self._fileID]

	@readonly
	def File(self) -> Nullable[File]:
		"""
		Read-only property to return the region's file, as the report lists it.

		:returns: The file of :attr:`FilePath` in the report's files; ``None`` if the region isn't part of a report, or the
		          report doesn't list the file, e.g. one excluded by ``-ignore-filename-regex``.
		"""
		if self._root is None or (path := self.FilePath) is None:
			return None

		return self._root._files.get(path, None)

	@readonly
	def ExpandedFilePath(self) -> Nullable[Path]:
		"""
		Read-only property to return the path of the file an expansion region expands to (:attr:`ExpandedFileID`).

		:returns: The path, as the compiler named it; ``None`` for another kind of region, or a region belonging to no
		          function or expansion.
		"""
		if self._kind is not RegionKind.Expansion or not isinstance(self._parent, (Function, Expansion)):
			return None

		return self._parent._filePaths[self._expandedFileID]

	@readonly
	def ExpandedFile(self) -> Nullable[File]:
		"""
		Read-only property to return the file an expansion region expands to, as the report lists it.

		:returns: The file of :attr:`ExpandedFilePath` in the report's files; ``None`` if there is none, the region isn't
		          part of a report, or the report doesn't list the file.
		"""
		if self._root is None or (path := self.ExpandedFilePath) is None:
			return None

		return self._root._files.get(path, None)


@export
class Region(Base["Function | Expansion"]):
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
		kind: RegionKind,
		*,
		parent: Nullable[Function | Expansion] = None
	) -> None:
		"""
		Initialize a region, and add it to the regions of its function or to the target regions of its expansion.

		:param lineStart:      Line the region starts at.
		:param columnStart:    Column the region starts at.
		:param lineEnd:        Line the region ends at.
		:param columnEnd:      Column the region ends at.
		:param count:          How often the region's code ran.
		:param fileID:         Index of the region's file in the file paths of its function or expansion.
		:param expandedFileID: Index of the file an expansion region expands to.
		:param kind:           The kind of the region.
		:param parent:         Optional, the function or expansion the region belongs to. Default: ``None``.
		:raises ValueError:    If parameter ``count`` is ``None``.
		:raises TypeError:     If parameter ``count`` isn't of type :class:`int`.
		:raises ValueError:    If parameter ``count`` is negative.
		:raises ValueError:    If parameter ``fileID`` is ``None``.
		:raises TypeError:     If parameter ``parent`` isn't of type :class:`Function` or :class:`Expansion`.
		"""
		super().__init__(lineStart, columnStart, lineEnd, columnEnd, fileID, expandedFileID, kind, parent=parent)

		if fileID is None:
			raise ValueError("Parameter 'fileID' is None.")

		if count is None:
			raise ValueError("Parameter 'count' is None.")
		elif not isinstance(count, int):
			ex = TypeError("Parameter 'count' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(count)}'.")
			raise ex
		elif count < 0:
			ex = ValueError("Parameter 'count' is negative.")
			ex.add_note(f"Got value '{count}'.")
			raise ex

		self._count = count

		if parent is not None:
			(parent._regions if isinstance(parent, Function) else parent._targetRegions).append(self)

	@classmethod
	def Parse(cls, region: list[Any], *, parent: Nullable[Function | Expansion] = None) -> Self:
		"""
		Parse a region from its JSON array.

		:param region: The JSON array of the region.
		:param parent: Optional, the function or expansion the region belongs to. Default: ``None``.
		:returns:      The region.
		"""
		return cls(*region[:7], RegionKind(region[7]), parent=parent)

	@readonly
	def Count(self) -> int:
		"""
		Read-only property to access how often the region's code ran (:attr:`_count`).

		:returns: The count.
		"""
		return self._count


@export
class BranchRegion(Base["File | Function | Expansion"]):
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
		kind: RegionKind,
		*,
		parent: Nullable[File | Function | Expansion] = None
	) -> None:
		"""
		Initialize a branch region, and add it to the branch regions of its file, function or expansion.

		:param lineStart:      Line the branch region starts at.
		:param columnStart:    Column the branch region starts at.
		:param lineEnd:        Line the branch region ends at.
		:param columnEnd:      Column the branch region ends at.
		:param trueCount:      How often the condition was true.
		:param falseCount:     How often the condition was false.
		:param fileID:         Index of the branch region's file in the file paths of its function or expansion.
		:param expandedFileID: Index of the file an expansion region expands to; ``0`` for a branch region.
		:param kind:           The kind of the region: a branch, or a condition measured for MC/DC.
		:param parent:         Optional, the file, function or expansion the branch region belongs to. Default: ``None``.
		:raises ValueError:    If parameter ``trueCount`` is ``None``.
		:raises TypeError:     If parameter ``trueCount`` isn't of type :class:`int`.
		:raises ValueError:    If parameter ``trueCount`` is negative.
		:raises ValueError:    If parameter ``falseCount`` is ``None``.
		:raises TypeError:     If parameter ``falseCount`` isn't of type :class:`int`.
		:raises ValueError:    If parameter ``falseCount`` is negative.
		:raises ValueError:    If parameter ``fileID`` is ``None``.
		:raises TypeError:     If parameter ``parent`` isn't of type :class:`File`, :class:`Function` or
		                       :class:`Expansion`.
		"""
		super().__init__(lineStart, columnStart, lineEnd, columnEnd, fileID, expandedFileID, kind, parent=parent)

		if fileID is None:
			raise ValueError("Parameter 'fileID' is None.")

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

		if parent is not None:
			parent._branches.append(self)

	@classmethod
	def Parse(cls, branch: list[Any], *, parent: Nullable[File | Function | Expansion] = None) -> Self:
		"""
		Parse a branch region from its JSON array.

		:param branch: The JSON array of the branch region.
		:param parent: Optional, the file, function or expansion the branch region belongs to. Default: ``None``.
		:returns:      The branch region.
		"""
		return cls(*branch[:8], RegionKind(branch[8]), parent=parent)

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
class TestVector(Element["MCDCRecord"]):
	"""
	A test vector of an MC/DC decision - in format version 3.1.0 -: the values of its conditions, and the outcome.
	"""

	_conditions: list[Nullable[bool]]  #: The values of the conditions; ``None`` for a condition not evaluated.
	_executed:   bool                  #: Whether the test vector was executed.
	_result:     Nullable[bool]        #: The outcome of the decision.

	def __init__(
		self,
		conditions: Iterable[Nullable[bool]],
		executed: bool,
		result: Nullable[bool],
		*,
		parent: Nullable[MCDCRecord] = None
	) -> None:
		"""
		Initialize a test vector, and add it to the test vectors of its MC/DC record.

		:param conditions:  The values of the conditions; ``None`` for a condition not evaluated.
		:param executed:    Whether the test vector was executed.
		:param result:      The outcome of the decision.
		:param parent:      Optional, the MC/DC record the test vector belongs to. Default: ``None``.
		:raises ValueError: If parameter ``conditions`` is ``None``.
		:raises TypeError:  If parameter ``conditions`` isn't iterable.
		:raises TypeError:  If parameter ``conditions`` contains an element not of type :class:`bool`, other than ``None``.
		:raises ValueError: If parameter ``executed`` is ``None``.
		:raises TypeError:  If parameter ``executed`` isn't of type :class:`bool`.
		:raises TypeError:  If parameter ``result`` isn't of type :class:`bool`.
		:raises TypeError:  If parameter ``parent`` isn't of type :class:`MCDCRecord`.
		"""
		super().__init__(parent=parent)

		if conditions is None:
			raise ValueError("Parameter 'conditions' is None.")
		elif not isinstance(conditions, Iterable):
			ex = TypeError("Parameter 'conditions' is not iterable.")
			ex.add_note(f"Got type '{getFullyQualifiedName(conditions)}'.")
			raise ex

		if executed is None:
			raise ValueError("Parameter 'executed' is None.")
		elif not isinstance(executed, bool):
			ex = TypeError("Parameter 'executed' is not of type 'bool'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(executed)}'.")
			raise ex

		if result is not None and not isinstance(result, bool):
			ex = TypeError("Parameter 'result' is not of type 'bool'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(result)}'.")
			raise ex

		self._conditions = conditionList = []
		self._executed =   executed
		self._result =     result

		for condition in conditions:
			if condition is not None and not isinstance(condition, bool):
				ex = TypeError("Parameter 'conditions' contains an element not of type 'bool'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(condition)}'.")
				raise ex

			conditionList.append(condition)

		if parent is not None:
			parent._testVectors.append(self)

	@classmethod
	def Parse(cls, testVector: dict[str, Any], *, parent: Nullable[MCDCRecord] = None) -> Self:
		"""
		Parse a test vector from its JSON object.

		:param testVector: The JSON object of the test vector.
		:param parent:     Optional, the MC/DC record the test vector belongs to. Default: ``None``.
		:returns:          The test vector.
		"""
		return cls(testVector["conditions"], testVector["executed"], testVector["result"], parent=parent)

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
class MCDCRecord(Base["File | Function"]):
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
		testVectors: Nullable[Iterable[TestVector]] = None,
		*,
		parent: Nullable[File | Function] = None
	) -> None:
		"""
		Initialize an MC/DC record, and add it to the MC/DC records of its file or function.

		:param lineStart:                     Line the decision starts at.
		:param columnStart:                   Column the decision starts at.
		:param lineEnd:                       Line the decision ends at.
		:param columnEnd:                     Column the decision ends at.
		:param fileID:                        Index of the decision's file in the file paths of its function or
		                                      expansion; ``None``, if not stated.
		:param expandedFileID:                Index of the file an expansion region expands to; ``0`` for an MC/DC
		                                      record.
		:param kind:                          The kind of the region: an MC/DC decision.
		:param conditions:                    Whether a pair of test vectors showed the independent effect, by
		                                      condition.
		:param trueDecisions:                 Optional, number of executed test vectors with the outcome true.
		                                      Default: ``None``.
		:param falseDecisions:                Optional, number of executed test vectors with the outcome false.
		                                      Default: ``None``.
		:param testVectors:                   Optional, the test vectors. Default: none.
		:param parent:                        Optional, the file or function the MC/DC record belongs to. Default:
		                                      ``None``.
		:raises ValueError:                   If parameter ``conditions`` is ``None``.
		:raises TypeError:                    If parameter ``conditions`` isn't iterable.
		:raises TypeError:                    If parameter ``conditions`` contains an element not of type
		                                      :class:`bool`.
		:raises TypeError:                    If parameter ``trueDecisions`` isn't of type :class:`int`.
		:raises ValueError:                   If parameter ``trueDecisions`` is negative.
		:raises TypeError:                    If parameter ``falseDecisions`` isn't of type :class:`int`.
		:raises ValueError:                   If parameter ``falseDecisions`` is negative.
		:raises TypeError:                    If parameter ``testVectors`` isn't iterable.
		:raises TypeError:                    If parameter ``testVectors`` contains an element not of type
		                                      :class:`TestVector`.
		:raises AlreadyInCoverageReportError: If parameter ``testVectors`` contains a test vector of another MC/DC
		                                      record.
		:raises TypeError:                    If parameter ``parent`` isn't of type :class:`File` or
		                                      :class:`Function`.
		"""
		super().__init__(lineStart, columnStart, lineEnd, columnEnd, fileID, expandedFileID, kind, parent=parent)

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
			raise ValueError("Parameter 'conditions' is None.")
		elif not isinstance(conditions, Iterable):
			ex = TypeError("Parameter 'conditions' is not iterable.")
			ex.add_note(f"Got type '{getFullyQualifiedName(conditions)}'.")
			raise ex

		self._trueDecisions =  trueDecisions
		self._falseDecisions = falseDecisions
		self._conditions =     conditionList = []
		self._testVectors =    testVectorList = []

		for condition in conditions:
			if not isinstance(condition, bool):
				ex = TypeError("Parameter 'conditions' contains an element not of type 'bool'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(condition)}'.")
				raise ex

			conditionList.append(condition)

		if testVectors is not None:
			if not isinstance(testVectors, Iterable):
				ex = TypeError("Parameter 'testVectors' is not iterable.")
				ex.add_note(f"Got type '{getFullyQualifiedName(testVectors)}'.")
				raise ex

			for testVector in testVectors:
				if not isinstance(testVector, TestVector):
					ex = TypeError("Parameter 'testVectors' contains an element not of type 'TestVector'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(testVector)}'.")
					raise ex
				elif testVector._parent is not None:
					raise AlreadyInCoverageReportError("Parameter 'testVectors' contains a test vector of another MC/DC record.")

				testVector._parent = self
				testVector._root =   self._root
				testVectorList.append(testVector)

		if parent is not None:
			parent._mcdcRecords.append(self)

	@classmethod
	def Parse(cls, record: list[Any], *, parent: Nullable[File | Function] = None) -> Self:
		"""
		Parse an MC/DC record from its JSON array, in the shape of its format version.

		:param record: The JSON array of the MC/DC record.
		:param parent: Optional, the file or function the MC/DC record belongs to. Default: ``None``.
		:returns:      The MC/DC record.
		"""
		if len(record) == 7:
			return cls(*record[:4], None, record[4], RegionKind(record[5]), record[6], parent=parent)
		elif len(record) == 9:
			return cls(*record[:4], None, record[6], RegionKind(record[7]), record[8], record[4], record[5], parent=parent)

		return cls(
			*record[:4], record[6], record[7], RegionKind(record[8]), record[9], record[4], record[5],
			[TestVector.Parse(testVector) for testVector in record[10]] if len(record) > 10 else None, parent=parent
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

	def _SetRoot(self, root: Nullable[Report]) -> None:
		"""
		Set the report's root of the MC/DC record, and of its test vectors.

		:param root: The report's root, or ``None`` while the element isn't part of a report.
		"""
		self._root = root
		for testVector in self._testVectors:
			testVector._SetRoot(root)


@export
class Counters(Element["Summary"]):
	"""
	The counters of one kind of a summary: how many there are, and how many are covered.

	A summary counts lines, functions, regions, branches and MC/DC conditions. The summary given the counters becomes
	their parent.
	"""

	_count:      int            #: Number of lines, functions, regions, branches or MC/DC conditions.
	_covered:    int            #: Number of the covered ones.
	_notCovered: Nullable[int]  #: Number of the uncovered ones, if stated.
	_percent:    float          #: The coverage in percent.

	def __init__(self, count: int, covered: int, percent: float, notCovered: Nullable[int] = None) -> None:
		"""
		Initialize counters.

		:param count:       Number of lines, functions, regions, branches or MC/DC conditions.
		:param covered:     Number of the covered ones.
		:param percent:     The coverage in percent.
		:param notCovered:  Optional, number of the uncovered ones. Default: ``None``.
		:raises ValueError: If parameter ``count`` is ``None``.
		:raises TypeError:  If parameter ``count`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``count`` is negative.
		:raises ValueError: If parameter ``covered`` is ``None``.
		:raises TypeError:  If parameter ``covered`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``covered`` is negative.
		:raises ValueError: If parameter ``percent`` is ``None``.
		:raises TypeError:  If parameter ``percent`` isn't of type :class:`float` or :class:`int`.
		:raises ValueError: If parameter ``percent`` is out of range 0..100.
		:raises TypeError:  If parameter ``notCovered`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``notCovered`` is negative.
		"""
		super().__init__()

		for name, value in (("count", count), ("covered", covered)):
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

		if notCovered is not None:
			if not isinstance(notCovered, int):
				ex = TypeError("Parameter 'notCovered' is not of type 'int'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(notCovered)}'.")
				raise ex
			elif notCovered < 0:
				ex = ValueError("Parameter 'notCovered' is negative.")
				ex.add_note(f"Got value '{notCovered}'.")
				raise ex

		if percent is None:
			raise ValueError("Parameter 'percent' is None.")
		elif not isinstance(percent, (float, int)):
			ex = TypeError("Parameter 'percent' is not of type 'float'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(percent)}'.")
			raise ex
		elif not 0 <= percent <= 100:
			ex = ValueError("Parameter 'percent' is out of range 0..100.")
			ex.add_note(f"Got value '{percent}'.")
			raise ex

		self._count =      count
		self._covered =    covered
		self._notCovered = notCovered
		self._percent =    percent

	@classmethod
	def Parse(cls, counters: dict[str, Any]) -> Self:
		"""
		Parse counters from their JSON object.

		:param counters: The JSON object of the counters.
		:returns:        The counters.
		"""
		return cls(counters["count"], counters["covered"], counters["percent"], counters.get("notcovered"))

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
class Summary(Element["File | Report"]):
	"""
	A ``summary``: the counters llvm-cov computed for a file or the whole report.

	llvm-cov counts a file's lines, regions and branches per function, and merges a function's instantiations by taking
	the best one. The file or report given the summary becomes its parent.
	"""

	_lines:          Counters            #: The counters of lines.
	_functions:      Counters            #: The counters of functions, a function's instantiations counted once.
	_instantiations: Counters            #: The counters of function instantiations.
	_regions:        Counters            #: The counters of code regions.
	_branches:       Nullable[Counters]  #: The counters of branch outcomes, if stated.
	_mcdc:           Nullable[Counters]  #: The counters of MC/DC conditions, if stated.

	def __init__(
		self,
		lines: Counters,
		functions: Counters,
		instantiations: Counters,
		regions: Counters,
		branches: Nullable[Counters] = None,
		mcdc: Nullable[Counters] = None
	) -> None:
		"""
		Initialize a summary.

		:param lines:                         The counters of lines.
		:param functions:                     The counters of functions, a function's instantiations counted once.
		:param instantiations:                The counters of function instantiations.
		:param regions:                       The counters of code regions.
		:param branches:                      Optional, the counters of branch outcomes. Default: ``None``.
		:param mcdc:                          Optional, the counters of MC/DC conditions. Default: ``None``.
		:raises ValueError:                   If parameter ``lines`` is ``None``.
		:raises TypeError:                    If parameter ``lines`` isn't of type :class:`Counters`.
		:raises AlreadyInCoverageReportError: If parameter ``lines`` are the counters of another summary.
		:raises ValueError:                   If parameter ``functions`` is ``None``.
		:raises TypeError:                    If parameter ``functions`` isn't of type :class:`Counters`.
		:raises AlreadyInCoverageReportError: If parameter ``functions`` are the counters of another summary.
		:raises ValueError:                   If parameter ``instantiations`` is ``None``.
		:raises TypeError:                    If parameter ``instantiations`` isn't of type :class:`Counters`.
		:raises AlreadyInCoverageReportError: If parameter ``instantiations`` are the counters of another summary.
		:raises ValueError:                   If parameter ``regions`` is ``None``.
		:raises TypeError:                    If parameter ``regions`` isn't of type :class:`Counters`.
		:raises AlreadyInCoverageReportError: If parameter ``regions`` are the counters of another summary.
		:raises TypeError:                    If parameter ``branches`` isn't of type :class:`Counters`.
		:raises AlreadyInCoverageReportError: If parameter ``branches`` are the counters of another summary.
		:raises TypeError:                    If parameter ``mcdc`` isn't of type :class:`Counters`.
		:raises AlreadyInCoverageReportError: If parameter ``mcdc`` are the counters of another summary.
		"""
		super().__init__()

		for name, counters in (
			("lines", lines), ("functions", functions), ("instantiations", instantiations), ("regions", regions)
		):
			if counters is None:
				raise ValueError(f"Parameter '{name}' is None.")
			elif not isinstance(counters, Counters):
				ex = TypeError(f"Parameter '{name}' is not of type 'Counters'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(counters)}'.")
				raise ex

		for name, counters in (("branches", branches), ("mcdc", mcdc)):
			if counters is not None and not isinstance(counters, Counters):
				ex = TypeError(f"Parameter '{name}' is not of type 'Counters'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(counters)}'.")
				raise ex

		for name, counters in (
			("lines", lines), ("functions", functions), ("instantiations", instantiations), ("regions", regions),
			("branches", branches), ("mcdc", mcdc)
		):
			if counters is None:
				continue
			elif counters._parent is not None:
				raise AlreadyInCoverageReportError(f"Parameter '{name}' are the counters of another summary.")

			counters._parent = self

		self._lines =          lines
		self._functions =      functions
		self._instantiations = instantiations
		self._regions =        regions
		self._branches =       branches
		self._mcdc =           mcdc

	@classmethod
	def Parse(cls, summary: dict[str, Any]) -> Self:
		"""
		Parse a summary from its JSON object.

		:param summary: The JSON object ``summary`` or ``totals``.
		:returns:       The summary.
		"""
		return cls(
			Counters.Parse(summary["lines"]),
			Counters.Parse(summary["functions"]),
			Counters.Parse(summary["instantiations"]),
			Counters.Parse(summary["regions"]),
			Counters.Parse(summary["branches"]) if "branches" in summary else None,
			Counters.Parse(summary["mcdc"]) if "mcdc" in summary else None
		)

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

	def _SetRoot(self, root: Nullable[Report]) -> None:
		"""
		Set the report's root of the summary, and of its counters.

		:param root: The report's root, or ``None`` while the element isn't part of a report.
		"""
		self._root = root
		for counters in (self._lines, self._functions, self._instantiations, self._regions, self._branches, self._mcdc):
			if counters is not None:
				counters._SetRoot(root)


_Summary = Summary


@export
class Segment(Element["File"]):
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
		isGapRegion: bool = False,
		*,
		parent: Nullable[File] = None
	) -> None:
		"""
		Initialize a segment, and add it to the segments of its file.

		:param line:          Line the segment starts at.
		:param column:        Column the segment starts at.
		:param count:         The count of the code from here on.
		:param hasCount:      Whether the code from here on has a count.
		:param isRegionEntry: Whether a region starts here.
		:param isGapRegion:   Optional, whether a gap region starts here. Default: ``False``.
		:param parent:        Optional, the file the segment belongs to. Default: ``None``.
		:raises ValueError:   If parameter ``line`` is ``None``.
		:raises TypeError:    If parameter ``line`` isn't of type :class:`int`.
		:raises ValueError:   If parameter ``line`` is less than 1.
		:raises ValueError:   If parameter ``column`` is ``None``.
		:raises TypeError:    If parameter ``column`` isn't of type :class:`int`.
		:raises ValueError:   If parameter ``column`` is less than 1.
		:raises ValueError:   If parameter ``count`` is ``None``.
		:raises TypeError:    If parameter ``count`` isn't of type :class:`int`.
		:raises ValueError:   If parameter ``count`` is negative.
		:raises ValueError:   If parameter ``hasCount`` is ``None``.
		:raises TypeError:    If parameter ``hasCount`` isn't of type :class:`bool`.
		:raises ValueError:   If parameter ``isRegionEntry`` is ``None``.
		:raises TypeError:    If parameter ``isRegionEntry`` isn't of type :class:`bool`.
		:raises ValueError:   If parameter ``isGapRegion`` is ``None``.
		:raises TypeError:    If parameter ``isGapRegion`` isn't of type :class:`bool`.
		:raises TypeError:    If parameter ``parent`` isn't of type :class:`File`.
		"""
		super().__init__(parent=parent)

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
			raise ValueError("Parameter 'count' is None.")
		elif not isinstance(count, int):
			ex = TypeError("Parameter 'count' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(count)}'.")
			raise ex
		elif count < 0:
			ex = ValueError("Parameter 'count' is negative.")
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

		if parent is not None:
			parent._segments.append(self)

	@classmethod
	def Parse(cls, segment: list[Any], *, parent: Nullable[File] = None) -> Self:
		"""
		Parse a segment from its JSON array.

		:param segment: The JSON array of the segment.
		:param parent:  Optional, the file the segment belongs to. Default: ``None``.
		:returns:       The segment.
		"""
		return cls(*segment[:5], segment[5] if len(segment) > 5 else False, parent=parent)

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
class Expansion(Element["File"]):
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
		branches: Nullable[Iterable[BranchRegion]] = None,
		*,
		parent: Nullable[File] = None
	) -> None:
		"""
		Initialize an expansion, and add it to the expansions of its file.

		:param filePaths:                     The paths of the files, which the file IDs of the regions index.
		:param sourceRegion:                  The region the macro is expanded at.
		:param targetRegions:                 The regions of the function the expansion is in.
		:param branches:                      Optional, the branch regions in the expansion, and in the expansions
		                                      nested in it. Default: none.
		:param parent:                        Optional, the file the expansion belongs to. Default: ``None``.
		:raises ValueError:                   If parameter ``filePaths`` is ``None``.
		:raises TypeError:                    If parameter ``filePaths`` isn't iterable.
		:raises TypeError:                    If parameter ``filePaths`` contains an element not of type
		                                      :class:`~pathlib.Path`.
		:raises ValueError:                   If parameter ``sourceRegion`` is ``None``.
		:raises TypeError:                    If parameter ``sourceRegion`` isn't of type :class:`Region`.
		:raises AlreadyInCoverageReportError: If parameter ``sourceRegion`` is a region of another element.
		:raises ValueError:                   If parameter ``sourceRegion`` is a region of a file ID or an expanded file ID
		                                      out of range of parameter ``filePaths``.
		:raises ValueError:                   If parameter ``targetRegions`` is ``None``.
		:raises TypeError:                    If parameter ``targetRegions`` isn't iterable.
		:raises TypeError:                    If parameter ``targetRegions`` contains an element not of type
		                                      :class:`Region`.
		:raises AlreadyInCoverageReportError: If parameter ``targetRegions`` contains a region of another element.
		:raises ValueError:                   If parameter ``targetRegions`` contains a region of a file ID or an expanded
		                                      file ID out of range of parameter ``filePaths``.
		:raises TypeError:                    If parameter ``branches`` isn't iterable.
		:raises TypeError:                    If parameter ``branches`` contains an element not of type
		                                      :class:`BranchRegion`.
		:raises AlreadyInCoverageReportError: If parameter ``branches`` contains a region of another element.
		:raises ValueError:                   If parameter ``branches`` contains a region of a file ID or an expanded file
		                                      ID out of range of parameter ``filePaths``.
		:raises TypeError:                    If parameter ``parent`` isn't of type :class:`File`.
		"""
		super().__init__(parent=parent)

		if filePaths is None:
			raise ValueError("Parameter 'filePaths' is None.")
		elif not isinstance(filePaths, Iterable):
			ex = TypeError("Parameter 'filePaths' is not iterable.")
			ex.add_note(f"Got type '{getFullyQualifiedName(filePaths)}'.")
			raise ex

		if sourceRegion is None:
			raise ValueError("Parameter 'sourceRegion' is None.")
		elif not isinstance(sourceRegion, Region):
			ex = TypeError("Parameter 'sourceRegion' is not of type 'Region'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(sourceRegion)}'.")
			raise ex
		elif sourceRegion._parent is not None:
			raise AlreadyInCoverageReportError("Parameter 'sourceRegion' is a region of another element.")

		if targetRegions is None:
			raise ValueError("Parameter 'targetRegions' is None.")

		self._filePaths =     filePathList = []
		self._sourceRegion =  sourceRegion
		self._targetRegions = []
		self._branches =      []

		for filePath in filePaths:
			if not isinstance(filePath, Path):
				ex = TypeError("Parameter 'filePaths' contains an element not of type 'Path'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(filePath)}'.")
				raise ex

			filePathList.append(filePath)

		for name, elements, elementType, target in (
			("targetRegions", targetRegions, Region, self._targetRegions),
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
				elif element._parent is not None:
					raise AlreadyInCoverageReportError(f"Parameter '{name}' contains a region of another element.")
				elif element._fileID is not None and element._fileID >= len(self._filePaths):
					ex = ValueError(f"Parameter '{name}' contains a region of a file ID out of range.")
					ex.add_note(f"Got value '{element._fileID}' for {len(self._filePaths)} file paths.")
					raise ex
				elif element._kind is RegionKind.Expansion and element._expandedFileID >= len(self._filePaths):
					ex = ValueError(f"Parameter '{name}' contains an expansion region of an expanded file ID out of range.")
					ex.add_note(f"Got value '{element._expandedFileID}' for {len(self._filePaths)} file paths.")
					raise ex

				element._parent = self
				element._root =   self._root
				target.append(element)

		if sourceRegion._fileID >= len(self._filePaths):
			ex = ValueError("Parameter 'sourceRegion' is a region of a file ID out of range.")
			ex.add_note(f"Got value '{sourceRegion._fileID}' for {len(self._filePaths)} file paths.")
			raise ex
		elif sourceRegion._kind is RegionKind.Expansion and sourceRegion._expandedFileID >= len(self._filePaths):
			ex = ValueError("Parameter 'sourceRegion' is an expansion region of an expanded file ID out of range.")
			ex.add_note(f"Got value '{sourceRegion._expandedFileID}' for {len(self._filePaths)} file paths.")
			raise ex

		sourceRegion._parent = self
		sourceRegion._root =   self._root

		if parent is not None:
			parent._expansions.append(self)

	@classmethod
	def Parse(cls, expansion: dict[str, Any], *, parent: Nullable[File] = None) -> Self:
		"""
		Parse an expansion from its JSON object.

		:param expansion: The JSON object of the expansion.
		:param parent:    Optional, the file the expansion belongs to. Default: ``None``.
		:returns:         The expansion.
		"""
		return cls(
			[Path(filename.replace("\\", "/")) for filename in expansion["filenames"]],
			Region.Parse(expansion["source_region"]),
			[Region.Parse(region) for region in expansion["target_regions"]],
			[BranchRegion.Parse(branch) for branch in expansion.get("branches", [])],
			parent=parent
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

	def _SetRoot(self, root: Nullable[Report]) -> None:
		"""
		Set the report's root of the expansion, and of its source region, target regions and branch regions.

		:param root: The report's root, or ``None`` while the element isn't part of a report.
		"""
		self._root = root
		for region in (self._sourceRegion, *self._targetRegions, *self._branches):
			region._SetRoot(root)


@export
class File(Element["Report"]):
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
		expansions: Nullable[Iterable[Expansion]] = None,
		*,
		parent: Nullable[Report] = None
	) -> None:
		"""
		Initialize a file, and add it to the files of its report.

		:param path:                          The file's path, as the compiler named it.
		:param summary:                       The counters llvm-cov computed.
		:param segments:                      Optional, the segments, by position. Default: none.
		:param branches:                      Optional, the branch regions of the file's functions. Default: none.
		:param mcdcRecords:                   Optional, the MC/DC records of the file's functions. Default: none.
		:param expansions:                    Optional, the macro expansions in the file. Default: none.
		:param parent:                        Optional, the report the file belongs to. Default: ``None``.
		:raises ValueError:                   If parameter ``path`` is ``None``.
		:raises TypeError:                    If parameter ``path`` isn't of type :class:`~pathlib.Path`.
		:raises ValueError:                   If parameter ``summary`` is ``None``.
		:raises TypeError:                    If parameter ``summary`` isn't of type :class:`Summary`.
		:raises AlreadyInCoverageReportError: If parameter ``summary`` is the summary of another element.
		:raises TypeError:                    If parameter ``segments`` isn't iterable.
		:raises TypeError:                    If parameter ``segments`` contains an element not of type
		                                      :class:`Segment`.
		:raises AlreadyInCoverageReportError: If parameter ``segments`` contains an element of another element.
		:raises TypeError:                    If parameter ``branches`` isn't iterable.
		:raises TypeError:                    If parameter ``branches`` contains an element not of type
		                                      :class:`BranchRegion`.
		:raises AlreadyInCoverageReportError: If parameter ``branches`` contains an element of another element.
		:raises TypeError:                    If parameter ``mcdcRecords`` isn't iterable.
		:raises TypeError:                    If parameter ``mcdcRecords`` contains an element not of type
		                                      :class:`MCDCRecord`.
		:raises AlreadyInCoverageReportError: If parameter ``mcdcRecords`` contains an element of another element.
		:raises TypeError:                    If parameter ``expansions`` isn't iterable.
		:raises TypeError:                    If parameter ``expansions`` contains an element not of type
		                                      :class:`Expansion`.
		:raises AlreadyInCoverageReportError: If parameter ``expansions`` contains an element of another element.
		:raises TypeError:                    If parameter ``parent`` isn't of type :class:`Report`.
		:raises DuplicateFileError:           If parameter ``parent`` has a file of the same path.
		"""
		super().__init__(parent=parent)

		if path is None:
			raise ValueError("Parameter 'path' is None.")
		elif not isinstance(path, Path):
			ex = TypeError("Parameter 'path' is not of type 'Path'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(path)}'.")
			raise ex
		elif parent is not None and path in parent._files:
			ex = DuplicateFileError("Parameter 'parent' has a file of the same path.")
			ex.add_note(f"Got value '{path.as_posix()}'.")
			raise ex

		if summary is None:
			raise ValueError("Parameter 'summary' is None.")
		elif not isinstance(summary, Summary):
			ex = TypeError("Parameter 'summary' is not of type 'Summary'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(summary)}'.")
			raise ex
		elif summary._parent is not None:
			raise AlreadyInCoverageReportError("Parameter 'summary' is the summary of another element.")

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
				elif element._parent is not None:
					raise AlreadyInCoverageReportError(f"Parameter '{name}' contains an element of another element.")

				element._parent = self
				element._SetRoot(self._root)

				target.append(element)

		summary._parent = self
		summary._SetRoot(self._root)

		if parent is not None:
			parent._files[path] = self

	@classmethod
	def Parse(cls, file: dict[str, Any], *, parent: Nullable[Report] = None) -> Self:
		"""
		Parse a file from its JSON object.

		:param file:   The JSON object of the file.
		:param parent: Optional, the report the file belongs to. Default: ``None``.
		:returns:      The file.
		"""
		return cls(
			Path(file["filename"].replace("\\", "/")),
			Summary.Parse(file["summary"]),
			[Segment.Parse(segment) for segment in file.get("segments", [])],
			[BranchRegion.Parse(branch) for branch in file.get("branches", [])],
			[MCDCRecord.Parse(record) for record in file.get("mcdc_records", [])],
			[Expansion.Parse(expansion) for expansion in file.get("expansions", [])],
			parent=parent
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

	def _SetRoot(self, root: Nullable[Report]) -> None:
		"""
		Set the report's root of the file, and of its segments, branch regions, MC/DC records, expansions and summary.

		:param root: The report's root, or ``None`` while the element isn't part of a report.
		"""
		self._root = root
		for element in (*self._segments, *self._branches, *self._mcdcRecords, *self._expansions, self._summary):
			element._SetRoot(root)


@export
class Function(Element["Report"]):
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
		mcdcRecords: Nullable[Iterable[MCDCRecord]] = None,
		*,
		parent: Nullable[Report] = None
	) -> None:
		"""
		Initialize a function, and add it to the functions of its report.

		:param name:                          The function's name, as the profile names it - e.g. mangled.
		:param count:                         How often the function was called.
		:param regions:                       The regions.
		:param filePaths:                     The paths of the files, which the file IDs of the regions index.
		:param branches:                      Optional, the branch regions. Default: none.
		:param mcdcRecords:                   Optional, the MC/DC records. Default: none.
		:param parent:                        Optional, the report the function belongs to. Default: ``None``.
		:raises ValueError:                   If parameter ``name`` is ``None``.
		:raises TypeError:                    If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError:                   If parameter ``name`` is empty.
		:raises ValueError:                   If parameter ``count`` is ``None``.
		:raises TypeError:                    If parameter ``count`` isn't of type :class:`int`.
		:raises ValueError:                   If parameter ``count`` is negative.
		:raises ValueError:                   If parameter ``regions`` is ``None``.
		:raises TypeError:                    If parameter ``regions`` isn't iterable.
		:raises TypeError:                    If parameter ``regions`` contains an element not of type
		                                      :class:`Region`.
		:raises AlreadyInCoverageReportError: If parameter ``regions`` contains a region of another element.
		:raises ValueError:                   If parameter ``regions`` contains a region of a file ID or an expanded file ID
		                                      out of range of parameter ``filePaths``.
		:raises ValueError:                   If parameter ``filePaths`` is ``None``.
		:raises TypeError:                    If parameter ``filePaths`` isn't iterable.
		:raises TypeError:                    If parameter ``filePaths`` contains an element not of type
		                                      :class:`~pathlib.Path`.
		:raises TypeError:                    If parameter ``branches`` isn't iterable.
		:raises TypeError:                    If parameter ``branches`` contains an element not of type
		                                      :class:`BranchRegion`.
		:raises AlreadyInCoverageReportError: If parameter ``branches`` contains a region of another element.
		:raises ValueError:                   If parameter ``branches`` contains a region of a file ID or an expanded file
		                                      ID out of range of parameter ``filePaths``.
		:raises TypeError:                    If parameter ``mcdcRecords`` isn't iterable.
		:raises TypeError:                    If parameter ``mcdcRecords`` contains an element not of type
		                                      :class:`MCDCRecord`.
		:raises AlreadyInCoverageReportError: If parameter ``mcdcRecords`` contains a region of another element.
		:raises ValueError:                   If parameter ``mcdcRecords`` contains a region of a file ID or an expanded
		                                      file ID out of range of parameter ``filePaths``.
		:raises TypeError:                    If parameter ``parent`` isn't of type :class:`Report`.
		"""
		super().__init__(parent=parent)

		if name is None:
			raise ValueError("Parameter 'name' is None.")
		elif not isinstance(name, str):
			ex = TypeError("Parameter 'name' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(name)}'.")
			raise ex
		elif name == "":
			raise ValueError("Parameter 'name' is empty.")

		if count is None:
			raise ValueError("Parameter 'count' is None.")
		elif not isinstance(count, int):
			ex = TypeError("Parameter 'count' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(count)}'.")
			raise ex
		elif count < 0:
			ex = ValueError("Parameter 'count' is negative.")
			ex.add_note(f"Got value '{count}'.")
			raise ex

		if regions is None:
			raise ValueError("Parameter 'regions' is None.")

		if filePaths is None:
			raise ValueError("Parameter 'filePaths' is None.")
		elif not isinstance(filePaths, Iterable):
			ex = TypeError("Parameter 'filePaths' is not iterable.")
			ex.add_note(f"Got type '{getFullyQualifiedName(filePaths)}'.")
			raise ex

		self._name =        name
		self._count =       count
		self._regions =     []
		self._branches =    []
		self._mcdcRecords = []
		self._filePaths =   filePathList = []

		for filePath in filePaths:
			if not isinstance(filePath, Path):
				ex = TypeError("Parameter 'filePaths' contains an element not of type 'Path'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(filePath)}'.")
				raise ex

			filePathList.append(filePath)

		for parameterName, elements, elementType, target in (
			("regions", regions, Region, self._regions), ("branches", branches, BranchRegion, self._branches),
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
				elif element._parent is not None:
					raise AlreadyInCoverageReportError(f"Parameter '{parameterName}' contains a region of another element.")
				elif element._fileID is not None and element._fileID >= len(self._filePaths):
					ex = ValueError(f"Parameter '{parameterName}' contains a region of a file ID out of range.")
					ex.add_note(f"Got value '{element._fileID}' for {len(self._filePaths)} file paths.")
					raise ex
				elif element._kind is RegionKind.Expansion and element._expandedFileID >= len(self._filePaths):
					ex = ValueError(
						f"Parameter '{parameterName}' contains an expansion region of an expanded file ID out of range."
					)
					ex.add_note(f"Got value '{element._expandedFileID}' for {len(self._filePaths)} file paths.")
					raise ex

				element._parent = self
				element._SetRoot(self._root)

				target.append(element)

		if parent is not None:
			parent._functions.append(self)

	@classmethod
	def Parse(cls, function: dict[str, Any], *, parent: Nullable[Report] = None) -> Self:
		"""
		Parse a function from its JSON object.

		:param function: The JSON object of the function.
		:param parent:   Optional, the report the function belongs to. Default: ``None``.
		:returns:        The function.
		"""
		return cls(
			function["name"],
			function["count"],
			[Region.Parse(region) for region in function["regions"]],
			[Path(filename.replace("\\", "/")) for filename in function["filenames"]],
			[BranchRegion.Parse(branch) for branch in function.get("branches", [])],
			[MCDCRecord.Parse(record) for record in function.get("mcdc_records", [])],
			parent=parent
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

	@readonly
	def MainFilePath(self) -> Nullable[Path]:
		"""
		Read-only property to return the path of the file the function is in (:attr:`MainFileID`).

		:returns: The path, as the compiler named it; ``None`` if every file is expanded to.
		"""
		return None if (mainFileID := self.MainFileID) is None else self._filePaths[mainFileID]

	@readonly
	def MainFile(self) -> Nullable[File]:
		"""
		Read-only property to return the file the function is in, as the report lists it.

		:returns: The file of :attr:`MainFilePath` in the report's files; ``None`` if the function isn't part of a report,
		          every file is expanded to, or the report doesn't list the file.
		"""
		if self._root is None or (path := self.MainFilePath) is None:
			return None

		return self._root._files.get(path, None)

	def _SetRoot(self, root: Nullable[Report]) -> None:
		"""
		Set the report's root of the function, and of its regions, branch regions and MC/DC records.

		:param root: The report's root, or ``None`` while the element isn't part of a report.
		"""
		self._root = root
		for element in (*self._regions, *self._branches, *self._mcdcRecords):
			element._SetRoot(root)


@export
class Report(metaclass=ExtendedType, mixin=True):
	"""
	The report's root: the format version, the files, the functions, and the totals.

	It is the root of every element below it.
	"""

	_root:      Report                     #: The report's root: the report itself.
	_version:   Nullable[SemanticVersion]  #: Version of the report format.
	_files:     dict[Path, File]           #: The files, by path.
	_functions: list[Function]             #: The functions.
	_totals:    Nullable[Summary]          #: The counters of the whole report.

	def __init__(
		self,
		version: Nullable[SemanticVersion] = None,
		files: Nullable[Iterable[File]] = None,
		functions: Nullable[Iterable[Function]] = None,
		totals: Nullable[Summary] = None
	) -> None:
		"""
		Initialize a report; empty, without parameters.

		:param version:                       Optional, version of the report format. Default: ``None``.
		:param files:                         Optional, the files. Default: none.
		:param functions:                     Optional, the functions. Default: none.
		:param totals:                        Optional, the counters of the whole report. Default: ``None``.
		:raises TypeError:                    If parameter ``version`` isn't of type
		                                      :class:`~pyTooling.Versioning.SemanticVersion`.
		:raises TypeError:                    If parameter ``files`` isn't iterable.
		:raises TypeError:                    If parameter ``files`` contains an element not of type :class:`File`.
		:raises DuplicateFileError:           If parameter ``files`` contains two files of the same path.
		:raises AlreadyInCoverageReportError: If parameter ``files`` contains an element of another report.
		:raises TypeError:                    If parameter ``functions`` isn't iterable.
		:raises TypeError:                    If parameter ``functions`` contains an element not of type
		                                      :class:`Function`.
		:raises AlreadyInCoverageReportError: If parameter ``functions`` contains an element of another report.
		:raises TypeError:                    If parameter ``totals`` isn't of type :class:`Summary`.
		:raises AlreadyInCoverageReportError: If parameter ``totals`` is the summary of another element.
		"""
		if version is not None and not isinstance(version, SemanticVersion):
			ex = TypeError("Parameter 'version' is not of type 'SemanticVersion'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(version)}'.")
			raise ex

		if totals is not None and not isinstance(totals, Summary):
			ex = TypeError("Parameter 'totals' is not of type 'Summary'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(totals)}'.")
			raise ex
		elif totals is not None and totals._parent is not None:
			raise AlreadyInCoverageReportError("Parameter 'totals' is the summary of another element.")

		self._root =      self
		self._version =   version
		self._files =     {}
		self._functions = functionList = []
		self._totals =    totals

		if files is not None:
			if not isinstance(files, Iterable):
				ex = TypeError("Parameter 'files' is not iterable.")
				ex.add_note(f"Got type '{getFullyQualifiedName(files)}'.")
				raise ex

			for file in files:
				if not isinstance(file, File):
					ex = TypeError("Parameter 'files' contains an element not of type 'File'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(file)}'.")
					raise ex
				elif file._parent is not None:
					raise AlreadyInCoverageReportError("Parameter 'files' contains a file of another report.")
				elif file._path in self._files:
					ex = DuplicateFileError("Parameter 'files' contains two files of the same path.")
					ex.add_note(f"Got value '{file._path.as_posix()}'.")
					raise ex

				file._parent = self
				file._SetRoot(self)

				self._files[file._path] = file

		if functions is not None:
			if not isinstance(functions, Iterable):
				ex = TypeError("Parameter 'functions' is not iterable.")
				ex.add_note(f"Got type '{getFullyQualifiedName(functions)}'.")
				raise ex

			for function in functions:
				if not isinstance(function, Function):
					ex = TypeError("Parameter 'functions' contains an element not of type 'Function'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(function)}'.")
					raise ex
				elif function._parent is not None:
					raise AlreadyInCoverageReportError("Parameter 'functions' contains a function of another report.")

				function._parent = self
				function._SetRoot(self)

				functionList.append(function)

		if totals is not None:
			totals._parent = self
			totals._SetRoot(self)

	@readonly
	def Version(self) -> Nullable[SemanticVersion]:
		"""
		Read-only property to access the version of the report format (:attr:`_version`).

		:returns: The version, e.g. ``2.0.1``; ``None`` before the report was converted.
		"""
		return self._version

	@readonly
	def Files(self) -> dict[Path, File]:
		"""
		Read-only property to access the files (:attr:`_files`).

		:returns: The files, by path.
		"""
		return self._files

	@readonly
	def Functions(self) -> list[Function]:
		"""
		Read-only property to access the functions (:attr:`_functions`).

		:returns: The functions; empty in a report written with ``-skip-functions`` or ``-summary-only``.
		"""
		return self._functions

	@readonly
	def Totals(self) -> Nullable[Summary]:
		"""
		Read-only property to access the counters of the whole report (:attr:`_totals`).

		:returns: The totals; ``None`` before the report was converted.
		"""
		return self._totals


TestVector._PARENT_TYPE =   (MCDCRecord, )
Region._PARENT_TYPE =       (Function, Expansion)
BranchRegion._PARENT_TYPE = (File, Function, Expansion)
MCDCRecord._PARENT_TYPE =   (File, Function)
Counters._PARENT_TYPE =     (Summary, )
Summary._PARENT_TYPE =      (File, Report)
Segment._PARENT_TYPE =      (File, )
Expansion._PARENT_TYPE =    (File, )
File._PARENT_TYPE =         (Report, )
Function._PARENT_TYPE =     (Report, )


@export
class Document(cc_Document, Report):
	"""
	An LLVM JSON code coverage export: read into the format's model, and converted to the common model.
	"""

	_jsonDocument: Nullable[dict[str, Any]]  #: The parsed and validated JSON document, after :meth:`Analyze`.

	def __init__(
		self,
		jsonReportFile: Path,
		analyzeAndConvert: bool = False,
		*,
		version: Nullable[SemanticVersion] = None,
		files: Nullable[Iterable[File]] = None,
		functions: Nullable[Iterable[Function]] = None,
		totals: Nullable[Summary] = None
	) -> None:
		"""
		Initialize the report, and optionally read it; or build it from typed values.

		:param jsonReportFile:    Path to the JSON file.
		:param analyzeAndConvert: Optional, if true, analyze the file and convert its content. Default: ``False``.
		:param version:           Optional, version of the report format. Default: ``None``.
		:param files:             Optional, the files. Default: none.
		:param functions:         Optional, the functions. Default: none.
		:param totals:            Optional, the counters of the whole report. Default: ``None``.
		:raises TypeError:        If parameter ``version`` isn't of type :class:`~pyTooling.Versioning.SemanticVersion`.
		:raises TypeError:        If parameter ``files`` isn't iterable.
		:raises TypeError:        If parameter ``files`` contains an element not of type
		                          :class:`File`.
		:raises TypeError:        If parameter ``functions`` isn't iterable.
		:raises TypeError:        If parameter ``functions`` contains an element not of type
		                          :class:`Function`.
		:raises TypeError:        If parameter ``totals`` isn't of type
		                          :class:`Summary`.
		"""
		super().__init__(jsonReportFile)
		Report.__init__(self, version, files, functions, totals)

		self._jsonDocument = None

		if analyzeAndConvert:
			self.Analyze()
			self.Convert()

	def Analyze(self) -> None:
		"""
		Parse the JSON file and validate it against the JSON Schema :data:`SCHEMA`.

		:raises CodeCoverageError: If the file doesn't exist.
		:raises CodeCoverageError: If the file isn't valid JSON.
		:raises CodeCoverageError: If the JSON Schema can't be read.
		:raises CodeCoverageError: If the file isn't valid according to the JSON Schema.
		"""
		if not self._path.exists():
			raise CodeCoverageError(f"LLVM coverage export file '{self._path}' does not exist.") \
				from FileNotFoundError(f"File '{self._path}' not found.")

		from jsonschema import Draft202012Validator

		with Stopwatch() as sw:
			try:
				jsonDocument = loads(self._path.read_text(encoding="utf-8"))
			except JSONDecodeError as ex:
				raise CodeCoverageError(f"JSON syntax error in LLVM coverage export file '{self._path}'.") from ex

			try:
				schema = loads(readResourceFile(Resources, SCHEMA))
			except (ToolingException, JSONDecodeError) as ex:
				raise CodeCoverageError(f"Couldn't read JSON Schema '{SCHEMA}' from package resources.") from ex

			errors = sorted(Draft202012Validator(schema).iter_errors(jsonDocument), key=lambda error: list(error.path))
			if len(errors) > 0:
				ex = CodeCoverageError(f"Validation error for '{self._path}' using JSON Schema '{SCHEMA}'.")
				for error in errors:
					ex.add_note(f"/{'/'.join(str(part) for part in error.path)}: {error.message}")
				raise ex

			self._jsonDocument = jsonDocument

		self._analysisDuration = sw.Duration

	def Convert(self) -> None:
		"""
		Convert the parsed and validated JSON document to the format's model.

		:raises CodeCoverageError: If the JSON file was not analyzed before. |br|
		                           Call 'Document.Analyze()' or create the document using
		                           'Document(path, analyzeAndConvert=True)'.
		"""
		if self._jsonDocument is None:
			ex = CodeCoverageError(
				f"LLVM coverage export file '{self._path}' needs to be read and analyzed by a JSON parser."
			)
			ex.add_note("Call 'Document.Analyze()' or create the document using 'Document(path, analyzeAndConvert=True)'.")
			raise ex

		with Stopwatch() as sw:
			data =            self._jsonDocument["data"][0]
			self._version =   SemanticVersion.Parse(self._jsonDocument["version"])
			self._files =     {}
			self._functions = []
			self._totals =    Summary.Parse(data["totals"])

			self._totals._parent = self
			self._totals._SetRoot(self)

			for record in data["files"]:
				File.Parse(record, parent=self)

			for function in data.get("functions", []):
				Function.Parse(function, parent=self)

		self._conversionDuration = sw.Duration

	def ToCoverageSummary(self) -> CoverageSummary:
		"""
		Convert the format's model to the common model, and aggregate it.

		:returns:                  The report's root of the common model, named after the report file.
		:raises CodeCoverageError: If a file's path runs through another file.
		:raises CodeCoverageError: If a function has a branch region in a file, which none of its regions expands to.
		"""
		parents = [path.parent.parts for path in self._files]
		first =   min(parents, default=())
		last =    max(parents, default=())
		common =  first
		for index, part in enumerate(first):
			if part != last[index]:
				common = first[:index]
				break

		summary = CoverageSummary(self._path.stem, sourceDirectories=[Path(*common)] if len(common) > 0 else [])
		commonFiles = {path: summary.GetOrAddFile("/".join(path.parts[len(common):])) for path in self._files}

		branches = self._CollectBranches()
		for path, file in self._files.items():
			self._ConvertLines(file, commonFiles[path], branches[path])

		self._ConvertUnits(commonFiles, summary)

		summary.Aggregate()
		return summary

	def _CollectBranches(self) -> dict[Path, dict[tuple[Any, ...], list[int]]]:
		"""
		Collect the branch regions of the functions by file; a branch region found in several functions is summed.

		A branch region is collected at the line it starts at, or at the line its macro is expanded at. It is found in
		several functions e.g. in the instantiations of a template.

		:returns:                  By path, the summed true and false counts of each branch region, keyed by the line
		                           number first.
		:raises CodeCoverageError: If a function has a branch region in a file, which none of its regions expands to.
		"""
		branches: dict[Path, dict[tuple[Any, ...], list[int]]] = {path: {} for path in self._files}
		for function in self._functions:
			mainFileID = function.MainFileID
			if mainFileID is None or (fileBranches := branches.get(function._filePaths[mainFileID])) is None:
				continue

			expansions = {
				region._expandedFileID: region for region in function._regions if region._kind is RegionKind.Expansion
			}
			for branch in function._branches:
				lineNumber = branch._lineStart
				fileID =     branch._fileID
				while fileID != mainFileID:
					if (expansion := expansions.get(fileID)) is None:
						ex = CodeCoverageError(f"Function '{function._name}' has a branch region in a file no region expands to.")
						ex.add_note(f"Got file ID {fileID} of file '{function._filePaths[fileID]}'.")
						raise ex

					lineNumber = expansion._lineStart
					fileID =     expansion._fileID

				key = (
					lineNumber, function._filePaths[branch._fileID],
					branch._lineStart, branch._columnStart, branch._lineEnd, branch._columnEnd
				)
				if (counts := fileBranches.get(key)) is None:
					fileBranches[key] = [branch._trueCount, branch._falseCount]
				else:
					counts[0] += branch._trueCount
					counts[1] += branch._falseCount

		return branches

	@staticmethod
	def _ConvertLines(file: File, commonFile: cc_File, branches: dict[tuple[Any, ...], list[int]]) -> None:
		"""
		Convert a file's segments to lines of the common model, and add the branches of the file's branch regions.

		A line's count is derived as ``llvm-cov show`` derives it: of the segments starting on the line, and of the last
		segment of a previous line, which continues on it. A branch region of a line, which isn't executable, is left out.

		:param file:       The file of the format's model.
		:param commonFile: The file of the common model.
		:param branches:   The true and false counts of each branch region of the file, keyed by the line number first.
		"""
		counts: dict[int, int] =    {}
		wrapped: Nullable[Segment] = None
		segments =                   file._segments
		index =                      0
		while index < len(segments):
			lineNumber =   segments[index]._line
			lineSegments = []
			while index < len(segments) and segments[index]._line == lineNumber:
				lineSegments.append(segments[index])
				index += 1

			starts =  [s._count for s in lineSegments if s._hasCount and s._isRegionEntry and not s._isGapRegion]
			skipped = not lineSegments[0]._hasCount and lineSegments[0]._isRegionEntry
			if (
				(not skipped and ((wrapped is not None and wrapped._hasCount) or len(starts) > 0)) or
				any(segment._hasCount and segment._isRegionEntry for segment in lineSegments)
			):
				counts[lineNumber] = max((wrapped._count if wrapped is not None else 0, *starts))

			# the lines up to the next segment continue the last segment of this line
			wrapped = lineSegments[-1]
			if wrapped._hasCount:
				nextLineNumber = segments[index]._line if index < len(segments) else lineNumber + 1
				for number in range(lineNumber + 1, nextLineNumber):
					counts[number] = wrapped._count

		partialLines = {key[0] for key, outcomes in branches.items() if 0 in outcomes}
		for number in sorted(counts):
			count = counts[number]
			if count == 0:
				status = LineCoverageStatus.Uncovered
			elif number in partialLines:
				status = LineCoverageStatus.PartiallyCovered
			else:
				status = LineCoverageStatus.Covered

			cc_Line(number, status, count, parent=commonFile)

		lines = commonFile._lines
		for key in sorted(branches):
			if key[0] < len(lines) and (line := lines[key[0]]) is not None:
				for count in branches[key]:
					cc_Branch(LineCoverageStatus.Covered if count > 0 else LineCoverageStatus.Uncovered, count, parent=line)

	def _ConvertUnits(self, commonFiles: dict[Path, cc_File], summary: CoverageSummary) -> None:
		"""
		Convert the files to source file units, and the functions to function units of their files.

		A function local to a translation unit is named without the file name prefixing it. Functions of the same name in a
		file - e.g. a header's inline function compiled in several translation units - become one unit, their counts
		summed.

		:param commonFiles: The files of the common model, by path.
		:param summary:     The report's root of the common model.
		"""
		functions: dict[tuple[Path, str], list[int]] = {}
		for function in self._functions:
			mainFileID = function.MainFileID
			if mainFileID is None or (path := function._filePaths[mainFileID]) not in commonFiles:
				continue

			name = function._name
			if (local := match(r"(.+?\.[^.:;/\\]+)[:;](.+)", name)) is not None:
				name = local[2]

			regions =         [region for region in function._regions if region._fileID == mainFileID]
			firstLineNumber = min((region._lineStart for region in regions), default=0)
			lastLineNumber =  max((region._lineEnd for region in regions), default=0)
			if (span := functions.get((path, name))) is None:
				functions[(path, name)] = [function._count, firstLineNumber, lastLineNumber]
			else:
				span[0] += function._count
				span[1] =  min(span[1], firstLineNumber)
				span[2] =  max(span[2], lastLineNumber)

		sourceFiles: dict[Path, cc_SourceFile] = {}
		for path, commonFile in commonFiles.items():
			lastLineNumber = commonFile._lastLineNumber
			sourceFiles[path] = cc_SourceFile(
				commonFile.Path.as_posix(),
				file=commonFile,
				startLine=next(commonFile.IterateLines(), None),
				endLine=commonFile._lines[lastLineNumber] if lastLineNumber > 0 else None,
				parent=summary
			)

		for (path, name), (count, firstLineNumber, lastLineNumber) in functions.items():
			commonFile = commonFiles[path]
			lines =      [line for line in commonFile._lines[firstLineNumber:lastLineNumber + 1] if line is not None]
			cc_Function(
				name,
				file=commonFile,
				startLine=lines[0] if len(lines) > 0 else None,
				endLine=lines[-1] if len(lines) > 0 else None,
				status=LineCoverageStatus.Covered if count > 0 else LineCoverageStatus.Uncovered,
				coverageCount=count,
				parent=sourceFiles[path]
			)
