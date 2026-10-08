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
# Copyright 2021-2026 Electronic Design Automation Abstraction (EDA²)                                                  #
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
coverage.py's JSON code coverage format: a model of the format, read from a report and converted to the common model.

coverage.py writes the format with ``coverage json``. A report is validated against the JSON Schema
:file:`CoveragePy-JSON.schema.json`, reverse-engineered from coverage.py, which accepts format versions 2 and 3. The
format's model keeps what the report states: a :class:`Document` holds :class:`File` records, a file - in format 3 -
:class:`Region` records of its functions and classes, and each its lines, branches and :class:`Summary`. Each
record's constructor takes typed values, so the model can be built by hand: a file or a region names its parent with
the keyword parameter ``parent`` and is added to it. Its class method ``Parse`` reads the record's JSON object.

:meth:`Document.ToCoverageSummary` converts the model to the common model of :mod:`pyEDAA.Reports.CodeCoverage`:

* A file's path is relative to the directory coverage.py ran in.
* Executed lines are covered - partially covered, if one of their branches wasn't taken -, missing lines uncovered,
  excluded lines excluded. The format has no counts.
* A branch is a pair of source and destination line; it becomes a branch of its source line, naming its target line -
  none for an exit of a function, which coverage.py states as a negative number.
* A file's directories become packages, the file a module spanning the whole file; its classes and functions - named by
  qualified names like ``Circle.Area`` - become classes, methods and functions, each spanning its ``class`` or ``def``
  line to its last line. coverage.py's own summary of a function counts the ``def`` line for the enclosing scope.

.. rubric:: Example

.. code-block:: Python

   from pathlib import Path
   from pyEDAA.Reports.CodeCoverage.CoveragePy import Document

   report = Document(Path("coverage.json"), analyzeAndConvert=True)
   summary = report.ToCoverageSummary()
   print(f"{summary.FileCount} files: {summary.Coverage:.1%}")
"""
from __future__                  import annotations

from datetime                    import datetime
from json                        import JSONDecodeError, loads
from pathlib                     import Path
from typing                      import Any, Iterable, Optional as Nullable, Self

from jsonschema                  import Draft202012Validator
from pyTooling.Common            import getFullyQualifiedName, readResourceFile, StringEnum
from pyTooling.Decorators        import export, readonly
from pyTooling.Exceptions        import ToolingException
from pyTooling.MetaClasses       import ExtendedType, abstractclass
from pyTooling.Stopwatch         import Stopwatch
from pyTooling.Versioning        import SemanticVersion

from pyEDAA.Reports              import Resources
from pyEDAA.Reports.CodeCoverage import Branch as cc_Branch, Class as cc_Class, CodeCoverageError, CoverageSummary
from pyEDAA.Reports.CodeCoverage import Document as cc_Document, File as cc_File, Function as cc_Function
from pyEDAA.Reports.CodeCoverage import Line as cc_Line, LineCoverageStatus, Method as cc_Method, Module as cc_Module
from pyEDAA.Reports.CodeCoverage import Package as cc_Package, Unit as cc_Unit


__all__ = ["SCHEMA"]

SCHEMA = "CoveragePy-JSON.schema.json"  #: The JSON Schema a report is validated against.

# A class with a property named like a class - ``Path``, ``Summary`` - can't name that class in the annotation of a
# field: the class body's namespace, where annotations are evaluated, binds the name to the property.
_Path = Path


@export
class Summary(metaclass=ExtendedType, slots=True):
	"""
	A ``summary``: the counters coverage.py computed for the whole report, a file or a region.

	coverage.py measures lines. What it calls a statement (``num_statements``) is a line number: a statement spanning
	several lines counts by its first line, several statements on one line count once.
	"""

	_lineCount:          int            #: Number of executable lines, without the excluded ones.
	_coveredLineCount:   int            #: Number of executed lines.
	_missingLineCount:   int            #: Number of executable lines, which never ran.
	_excludedLineCount:  int            #: Number of excluded lines.
	_percentCovered:     float          #: Coverage of lines and branches, in percent.
	_branchCount:        Nullable[int]  #: Number of branches, if branch coverage was measured.
	_coveredBranchCount: Nullable[int]  #: Number of taken branches, if branch coverage was measured.
	_partialBranchCount: Nullable[int]  #: Number of branches never taken from executed lines, if branches were measured.

	def __init__(
		self,
		lineCount:          int,
		coveredLineCount:   int,
		missingLineCount:   int,
		excludedLineCount:  int,
		percentCovered:     float,
		branchCount:        Nullable[int] = None,
		coveredBranchCount: Nullable[int] = None,
		partialBranchCount: Nullable[int] = None
	) -> None:
		"""
		Initialize the summary from its counters.

		:param lineCount:          Number of executable lines, without the excluded ones.
		:param coveredLineCount:   Number of executed lines.
		:param missingLineCount:   Number of executable lines, which never ran.
		:param excludedLineCount:  Number of excluded lines.
		:param percentCovered:     Coverage of lines and branches, in percent.
		:param branchCount:        Optional, number of branches. Default: ``None`` (branch coverage wasn't measured).
		:param coveredBranchCount: Optional, number of taken branches. Default: ``None`` (branch coverage wasn't measured).
		:param partialBranchCount: Optional, number of branches never taken from executed lines. |br|
		                           Default: ``None`` (branch coverage wasn't measured).
		:raises ValueError:        If parameter ``lineCount``, ``coveredLineCount``, ``missingLineCount`` or
		                           ``excludedLineCount`` is ``None``.
		:raises TypeError:         If parameter ``lineCount``, ``coveredLineCount``, ``missingLineCount`` or
		                           ``excludedLineCount`` is not of type :class:`int`.
		:raises ValueError:        If parameter ``lineCount``, ``coveredLineCount``, ``missingLineCount`` or
		                           ``excludedLineCount`` is negative.
		:raises ValueError:        If parameter ``percentCovered`` is ``None``.
		:raises TypeError:         If parameter ``percentCovered`` is not of type :class:`float`.
		:raises ValueError:        If parameter ``percentCovered`` is out of range 0..100.
		:raises TypeError:         If parameter ``branchCount``, ``coveredBranchCount`` or ``partialBranchCount`` is not of
		                           type :class:`int`.
		:raises ValueError:        If parameter ``branchCount``, ``coveredBranchCount`` or ``partialBranchCount`` is
		                           negative.
		"""
		for name, count in (
			("lineCount",         lineCount),
			("coveredLineCount",  coveredLineCount),
			("missingLineCount",  missingLineCount),
			("excludedLineCount", excludedLineCount)
		):
			if count is None:
				raise ValueError(f"Parameter '{name}' is None.")
			elif not isinstance(count, int):
				ex = TypeError(f"Parameter '{name}' is not of type 'int'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(count)}'.")
				raise ex
			elif count < 0:
				ex = ValueError(f"Parameter '{name}' is negative.")
				ex.add_note(f"Got value '{count}'.")
				raise ex

		if percentCovered is None:
			raise ValueError(f"Parameter 'percentCovered' is None.")
		elif not isinstance(percentCovered, (int, float)):
			ex = TypeError(f"Parameter 'percentCovered' is not of type 'float'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(percentCovered)}'.")
			raise ex
		elif not 0 <= percentCovered <= 100:
			ex = ValueError(f"Parameter 'percentCovered' is out of range 0..100.")
			ex.add_note(f"Got value '{percentCovered}'.")
			raise ex

		for name, count in (
			("branchCount",        branchCount),
			("coveredBranchCount", coveredBranchCount),
			("partialBranchCount", partialBranchCount)
		):
			if count is None:
				continue
			elif not isinstance(count, int):
				ex = TypeError(f"Parameter '{name}' is not of type 'int'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(count)}'.")
				raise ex
			elif count < 0:
				ex = ValueError(f"Parameter '{name}' is negative.")
				ex.add_note(f"Got value '{count}'.")
				raise ex

		self._lineCount =          lineCount
		self._coveredLineCount =   coveredLineCount
		self._missingLineCount =   missingLineCount
		self._excludedLineCount =  excludedLineCount
		self._percentCovered =     percentCovered
		self._branchCount =        branchCount
		self._coveredBranchCount = coveredBranchCount
		self._partialBranchCount = partialBranchCount

	@classmethod
	def Parse(cls, summary: dict[str, Any]) -> Self:
		"""
		Read a summary from its JSON object.

		:param summary:     The JSON object ``summary`` or ``totals``.
		:returns:           The summary.
		:raises ValueError: If parameter ``summary`` is ``None``.
		:raises TypeError:  If parameter ``summary`` is not of type :class:`dict`.
		"""
		if summary is None:
			raise ValueError(f"Parameter 'summary' is None.")
		elif not isinstance(summary, dict):
			ex = TypeError(f"Parameter 'summary' is not of type 'dict'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(summary)}'.")
			raise ex

		return cls(
			summary["num_statements"],
			summary["covered_lines"],
			summary["missing_lines"],
			summary["excluded_lines"],
			summary["percent_covered"],
			summary.get("num_branches"),
			summary.get("covered_branches"),
			summary.get("num_partial_branches")
		)

	@readonly
	def LineCount(self) -> int:
		"""
		Read-only property to access the number of executable lines, without the excluded ones (:attr:`_lineCount`).

		coverage.py states it as ``num_statements``.

		:returns: The number of executable lines.
		"""
		return self._lineCount

	@readonly
	def CoveredLineCount(self) -> int:
		"""
		Read-only property to access the number of executed lines (:attr:`_coveredLineCount`).

		:returns: The number of executed lines.
		"""
		return self._coveredLineCount

	@readonly
	def MissingLineCount(self) -> int:
		"""
		Read-only property to access the number of executable lines, which never ran (:attr:`_missingLineCount`).

		:returns: The number of missing lines.
		"""
		return self._missingLineCount

	@readonly
	def ExcludedLineCount(self) -> int:
		"""
		Read-only property to access the number of excluded lines (:attr:`_excludedLineCount`).

		:returns: The number of excluded lines.
		"""
		return self._excludedLineCount

	@readonly
	def PercentCovered(self) -> float:
		"""
		Read-only property to access the coverage of lines and branches (:attr:`_percentCovered`).

		:returns: The coverage in percent.
		"""
		return self._percentCovered

	@readonly
	def BranchCount(self) -> Nullable[int]:
		"""
		Read-only property to access the number of branches (:attr:`_branchCount`).

		:returns: The number of branches, or ``None`` if branch coverage wasn't measured.
		"""
		return self._branchCount

	@readonly
	def CoveredBranchCount(self) -> Nullable[int]:
		"""
		Read-only property to access the number of taken branches (:attr:`_coveredBranchCount`).

		:returns: The number of taken branches, or ``None`` if branch coverage wasn't measured.
		"""
		return self._coveredBranchCount

	@readonly
	def PartialBranchCount(self) -> Nullable[int]:
		"""
		Read-only property to access the number of branches never taken from executed lines (:attr:`_partialBranchCount`).

		:returns: The number of branches, which were never taken although their line ran, or ``None`` if branch coverage
		          wasn't measured.
		"""
		return self._partialBranchCount


_Summary = Summary


@export
@abstractclass
class Base(metaclass=ExtendedType, slots=True):
	"""
	Base-class of a file and a region: its executed, missing and excluded lines, its branches, and its summary.
	"""

	_executedLines:    list[int]              #: The executed lines.
	_missingLines:     list[int]              #: The lines, which never ran.
	_excludedLines:    list[int]              #: The excluded lines.
	_executedBranches: list[tuple[int, int]]  #: The taken branches, as pairs of source and destination line.
	_missingBranches:  list[tuple[int, int]]  #: The branches never taken, as pairs of source and destination line.
	_summary:          _Summary               #: The counters coverage.py computed.

	def __init__(
		self,
		summary:          Summary,
		executedLines:    Nullable[Iterable[int]] = None,
		missingLines:     Nullable[Iterable[int]] = None,
		excludedLines:    Nullable[Iterable[int]] = None,
		executedBranches: Nullable[Iterable[tuple[int, int]]] = None,
		missingBranches:  Nullable[Iterable[tuple[int, int]]] = None
	) -> None:
		"""
		Initialize the summary, the lines and the branches.

		:param summary:          The counters coverage.py computed.
		:param executedLines:    Optional, the executed lines. Default: ``None`` (none).
		:param missingLines:     Optional, the lines, which never ran. Default: ``None`` (none).
		:param excludedLines:    Optional, the excluded lines. Default: ``None`` (none).
		:param executedBranches: Optional, the taken branches, as pairs of source and destination line. |br|
		                         Default: ``None`` (none, or branch coverage wasn't measured).
		:param missingBranches:  Optional, the branches never taken, as pairs of source and destination line. |br|
		                         Default: ``None`` (none, or branch coverage wasn't measured).
		:raises ValueError:      If parameter ``summary`` is ``None``.
		:raises TypeError:       If parameter ``summary`` is not of type :class:`Summary`.
		:raises TypeError:       If parameter ``executedLines``, ``missingLines`` or ``excludedLines`` is not iterable.
		:raises TypeError:       If an element of parameter ``executedLines``, ``missingLines`` or ``excludedLines`` is
		                         not of type :class:`int`.
		:raises TypeError:       If parameter ``executedBranches`` or ``missingBranches`` is not iterable.
		:raises TypeError:       If an element of parameter ``executedBranches`` or ``missingBranches`` is not a pair of
		                         :class:`int`.
		"""
		if summary is None:
			raise ValueError(f"Parameter 'summary' is None.")
		elif not isinstance(summary, Summary):
			ex = TypeError(f"Parameter 'summary' is not of type 'Summary'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(summary)}'.")
			raise ex

		lineLists: list[list[int]] = []
		for name, numbers in (
			("executedLines", executedLines),
			("missingLines",  missingLines),
			("excludedLines", excludedLines)
		):
			lineList: list[int] = []
			if numbers is not None:
				if not isinstance(numbers, Iterable):
					ex = TypeError(f"Parameter '{name}' is not iterable.")
					ex.add_note(f"Got type '{getFullyQualifiedName(numbers)}'.")
					raise ex

				for number in numbers:
					if not isinstance(number, int):
						ex = TypeError(f"An element of parameter '{name}' is not of type 'int'.")
						ex.add_note(f"Got type '{getFullyQualifiedName(number)}'.")
						raise ex

					lineList.append(number)
			lineLists.append(lineList)

		branchLists: list[list[tuple[int, int]]] = []
		for name, branches in (
			("executedBranches", executedBranches),
			("missingBranches",  missingBranches)
		):
			branchList: list[tuple[int, int]] = []
			if branches is not None:
				if not isinstance(branches, Iterable):
					ex = TypeError(f"Parameter '{name}' is not iterable.")
					ex.add_note(f"Got type '{getFullyQualifiedName(branches)}'.")
					raise ex

				for branch in branches:
					if not (isinstance(branch, tuple) and len(branch) == 2 and all(isinstance(line, int) for line in branch)):
						ex = TypeError(f"An element of parameter '{name}' is not a pair of 'int'.")
						ex.add_note(f"Got '{branch!r}' of type '{getFullyQualifiedName(branch)}'.")
						raise ex

					branchList.append(branch)
			branchLists.append(branchList)

		self._executedLines, self._missingLines, self._excludedLines = lineLists
		self._executedBranches, self._missingBranches =                branchLists
		self._summary =                                                summary

	@readonly
	def ExecutedLines(self) -> list[int]:
		"""
		Read-only property to access the executed lines (:attr:`_executedLines`).

		:returns: The line numbers.
		"""
		return self._executedLines

	@readonly
	def MissingLines(self) -> list[int]:
		"""
		Read-only property to access the lines, which never ran (:attr:`_missingLines`).

		:returns: The line numbers.
		"""
		return self._missingLines

	@readonly
	def ExcludedLines(self) -> list[int]:
		"""
		Read-only property to access the excluded lines (:attr:`_excludedLines`).

		:returns: The line numbers.
		"""
		return self._excludedLines

	@readonly
	def ExecutedBranches(self) -> list[tuple[int, int]]:
		"""
		Read-only property to access the taken branches (:attr:`_executedBranches`).

		:returns: The branches as pairs of source and destination line; empty, if branch coverage wasn't measured.
		"""
		return self._executedBranches

	@readonly
	def MissingBranches(self) -> list[tuple[int, int]]:
		"""
		Read-only property to access the branches never taken (:attr:`_missingBranches`).

		:returns: The branches as pairs of source and destination line; empty, if branch coverage wasn't measured.
		"""
		return self._missingBranches

	@readonly
	def Summary(self) -> Summary:
		"""
		Read-only property to access the counters coverage.py computed (:attr:`_summary`).

		:returns: The summary.
		"""
		return self._summary

	@readonly
	def AllLines(self) -> list[int]:
		"""
		Read-only property to return the executed, missing and excluded lines.

		:returns: The line numbers, sorted.
		"""
		return sorted({*self._executedLines, *self._missingLines, *self._excludedLines})


@export
class RegionKind(StringEnum):
	"""
	Kind of a region of a file, as coverage.py names it: a function or a class.

	A file states its regions of each kind in their own JSON object: ``functions`` and ``classes``.
	"""

	Function = "function"  #: A function or a method, listed in ``functions``.
	Class =    "class"     #: A class, listed in ``classes``.


@export
class Region(Base):
	"""
	A function or a class of a file - in format 3 -, named by its qualified name, e.g. ``Circle.Area``.
	"""

	_parent:    Nullable[File]  #: The file the region belongs to.
	_name:      str             #: Qualified name of the function or class.
	_kind:      RegionKind      #: Kind of the region: a function or a class.
	_startLine: int             #: The region's first line.

	def __init__(
		self,
		name:             str,
		kind:             RegionKind,
		startLine:        int,
		summary:          Summary,
		executedLines:    Nullable[Iterable[int]] = None,
		missingLines:     Nullable[Iterable[int]] = None,
		excludedLines:    Nullable[Iterable[int]] = None,
		executedBranches: Nullable[Iterable[tuple[int, int]]] = None,
		missingBranches:  Nullable[Iterable[tuple[int, int]]] = None,
		*,
		parent:           Nullable[File] = None
	) -> None:
		"""
		Initialize the region from its name, its kind, its first line, its summary, its lines and its branches, and add it
		to the functions or classes of its file.

		:param name:             Qualified name of the function or class, e.g. ``Circle.Area``.
		:param kind:             Kind of the region: a function or a class.
		:param startLine:        The region's first line.
		:param summary:          The counters coverage.py computed.
		:param executedLines:    Optional, the executed lines. Default: ``None`` (none).
		:param missingLines:     Optional, the lines, which never ran. Default: ``None`` (none).
		:param excludedLines:    Optional, the excluded lines. Default: ``None`` (none).
		:param executedBranches: Optional, the taken branches, as pairs of source and destination line. |br|
		                         Default: ``None`` (none, or branch coverage wasn't measured).
		:param missingBranches:  Optional, the branches never taken, as pairs of source and destination line. |br|
		                         Default: ``None`` (none, or branch coverage wasn't measured).
		:param parent:           Optional, the file the region belongs to; the region is added to its functions or classes
		                         by :attr:`Name`, as its :attr:`Kind` says. Default: ``None``.
		:raises ValueError:      If parameter ``name`` is ``None``.
		:raises TypeError:       If parameter ``name`` is not of type :class:`str`.
		:raises ValueError:      If parameter ``name`` is empty.
		:raises ValueError:      If parameter ``kind`` is ``None``.
		:raises TypeError:       If parameter ``kind`` is not of type :class:`RegionKind`.
		:raises ValueError:      If parameter ``startLine`` is ``None``.
		:raises TypeError:       If parameter ``startLine`` is not of type :class:`int`.
		:raises ValueError:      If parameter ``startLine`` is less than 1.
		:raises TypeError:       If parameter ``parent`` is not of type :class:`File`.
		:raises ValueError:      If parameter ``parent`` contains a region of the same kind and name already.
		"""
		super().__init__(summary, executedLines, missingLines, excludedLines, executedBranches, missingBranches)

		if name is None:
			raise ValueError(f"Parameter 'name' is None.")
		elif not isinstance(name, str):
			ex = TypeError(f"Parameter 'name' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(name)}'.")
			raise ex
		elif name == "":
			raise ValueError(f"Parameter 'name' is empty.")

		if kind is None:
			raise ValueError(f"Parameter 'kind' is None.")
		elif not isinstance(kind, RegionKind):
			ex = TypeError(f"Parameter 'kind' is not of type 'RegionKind'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(kind)}'.")
			raise ex

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

		if parent is not None:
			if not isinstance(parent, File):
				ex = TypeError(f"Parameter 'parent' is not of type 'File'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
				raise ex

			regions = parent._functions if kind is RegionKind.Function else parent._classes
			if name in regions:
				raise ValueError(f"Parameter 'parent' contains {kind} '{name}' already.")

		self._parent =    parent
		self._name =      name
		self._kind =      kind
		self._startLine = startLine

		if parent is not None:
			regions[name] = self

	@classmethod
	def Parse(cls, name: str, kind: RegionKind, region: dict[str, Any], *, parent: Nullable[File] = None) -> Self:
		"""
		Read a region from its JSON object.

		:param name:        Qualified name of the function or class: the region's key in ``functions`` or ``classes``.
		:param kind:        Kind of the region: :attr:`RegionKind.Function` in ``functions``, :attr:`RegionKind.Class` in
		                    ``classes``.
		:param region:      The JSON object of the region.
		:param parent:      Optional, the file the region belongs to. Default: ``None``.
		:returns:           The region.
		:raises ValueError: If parameter ``region`` is ``None``.
		:raises TypeError:  If parameter ``region`` is not of type :class:`dict`.
		"""
		if region is None:
			raise ValueError(f"Parameter 'region' is None.")
		elif not isinstance(region, dict):
			ex = TypeError(f"Parameter 'region' is not of type 'dict'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(region)}'.")
			raise ex

		return cls(
			name,
			kind,
			region["start_line"],
			Summary.Parse(region["summary"]),
			region["executed_lines"],
			region["missing_lines"],
			region["excluded_lines"],
			(tuple(branch) for branch in region.get("executed_branches", [])),
			(tuple(branch) for branch in region.get("missing_branches", [])),
			parent=parent
		)

	@readonly
	def Parent(self) -> Nullable[File]:
		"""
		Read-only property to access the file the region belongs to (:attr:`_parent`).

		:returns: The file; ``None`` if the region belongs to no file.
		"""
		return self._parent

	@readonly
	def Name(self) -> str:
		"""
		Read-only property to access the qualified name of the function or class (:attr:`_name`).

		:returns: The qualified name.
		"""
		return self._name

	@readonly
	def Kind(self) -> RegionKind:
		"""
		Read-only property to access the kind of the region (:attr:`_kind`).

		:returns: The kind: a function or a class.
		"""
		return self._kind

	@readonly
	def StartLine(self) -> int:
		"""
		Read-only property to access the region's first line (:attr:`_startLine`).

		:returns: The line number.
		"""
		return self._startLine


@export
class File(Base):
	"""
	A measured file: its lines, branches and summary, and - in format 3 - its functions and classes.

	The regions named ``""`` - the lines outside of every function or class - aren't kept: :meth:`Parse` skips them.
	"""

	_parent:    Nullable[Report]   #: The report the file belongs to.
	_path:      _Path              #: The file's path, relative to the directory coverage.py ran in.
	_functions: dict[str, Region]  #: The functions, by qualified name.
	_classes:   dict[str, Region]  #: The classes, by qualified name.

	def __init__(
		self,
		path:             Path,
		summary:          Summary,
		executedLines:    Nullable[Iterable[int]] = None,
		missingLines:     Nullable[Iterable[int]] = None,
		excludedLines:    Nullable[Iterable[int]] = None,
		executedBranches: Nullable[Iterable[tuple[int, int]]] = None,
		missingBranches:  Nullable[Iterable[tuple[int, int]]] = None,
		*,
		parent:           Nullable[Report] = None
	) -> None:
		"""
		Initialize the file from its path, its summary, its lines and its branches, and add it to the files of its report.

		Its functions and classes are added by creating them with this file as their parent.

		:param path:             The file's path, relative to the directory coverage.py ran in.
		:param summary:          The counters coverage.py computed.
		:param executedLines:    Optional, the executed lines. Default: ``None`` (none).
		:param missingLines:     Optional, the lines, which never ran. Default: ``None`` (none).
		:param excludedLines:    Optional, the excluded lines. Default: ``None`` (none).
		:param executedBranches: Optional, the taken branches, as pairs of source and destination line. |br|
		                         Default: ``None`` (none, or branch coverage wasn't measured).
		:param missingBranches:  Optional, the branches never taken, as pairs of source and destination line. |br|
		                         Default: ``None`` (none, or branch coverage wasn't measured).
		:param parent:           Optional, the report the file belongs to; the file is added to its files by :attr:`Path`.
		                         Default: ``None``.
		:raises ValueError:      If parameter ``path`` is ``None``.
		:raises TypeError:       If parameter ``path`` is not of type :class:`~pathlib.Path`.
		:raises TypeError:       If parameter ``parent`` is not of type :class:`Report`.
		:raises ValueError:      If parameter ``parent`` contains a file of the same path already.
		"""
		super().__init__(summary, executedLines, missingLines, excludedLines, executedBranches, missingBranches)

		if path is None:
			raise ValueError(f"Parameter 'path' is None.")
		elif not isinstance(path, Path):
			ex = TypeError(f"Parameter 'path' is not of type 'Path'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(path)}'.")
			raise ex

		if parent is not None:
			if not isinstance(parent, Report):
				ex = TypeError(f"Parameter 'parent' is not of type 'Report'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
				raise ex
			elif path in parent._files:
				raise ValueError(f"Parameter 'parent' contains file '{path.as_posix()}' already.")

		self._parent =    parent
		self._path =      path
		self._functions = {}
		self._classes =   {}

		if parent is not None:
			parent._files[path] = self

	@classmethod
	def Parse(cls, name: str, file: dict[str, Any], *, parent: Nullable[Report] = None) -> Self:
		"""
		Read a file, its functions and classes from its JSON object.

		The regions named ``""`` - the lines outside of every function or class - are skipped.

		:param name:               The file's path as the report states it - its key in ``files`` -, relative to the
		                           directory coverage.py ran in; ``\\`` separators become ``/``.
		:param file:               The JSON object of the file.
		:param parent:             Optional, the report the file belongs to. Default: ``None``.
		:returns:                  The file.
		:raises ValueError:        If parameter ``name`` is ``None``.
		:raises TypeError:         If parameter ``name`` is not of type :class:`str`.
		:raises ValueError:        If parameter ``file`` is ``None``.
		:raises TypeError:         If parameter ``file`` is not of type :class:`dict`.
		:raises CodeCoverageError: If the report names the file's path twice.
		"""
		if name is None:
			raise ValueError(f"Parameter 'name' is None.")
		elif not isinstance(name, str):
			ex = TypeError(f"Parameter 'name' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(name)}'.")
			raise ex

		if file is None:
			raise ValueError(f"Parameter 'file' is None.")
		elif not isinstance(file, dict):
			ex = TypeError(f"Parameter 'file' is not of type 'dict'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(file)}'.")
			raise ex

		path = Path(name.replace("\\", "/"))
		if parent is not None and path in parent._files:
			raise CodeCoverageError(f"coverage.py report names file '{path.as_posix()}' twice.")

		measuredFile = cls(
			path,
			Summary.Parse(file["summary"]),
			file["executed_lines"],
			file["missing_lines"],
			file["excluded_lines"],
			(tuple(branch) for branch in file.get("executed_branches", [])),
			(tuple(branch) for branch in file.get("missing_branches", [])),
			parent=parent
		)

		for kind, regions in ((RegionKind.Function, "functions"), (RegionKind.Class, "classes")):
			for regionName, region in file.get(regions, {}).items():
				if regionName != "":
					Region.Parse(regionName, kind, region, parent=measuredFile)

		return measuredFile

	@readonly
	def Parent(self) -> Nullable[Report]:
		"""
		Read-only property to access the report the file belongs to (:attr:`_parent`).

		:returns: The report; ``None`` if the file belongs to no report.
		"""
		return self._parent

	@readonly
	def Path(self) -> Path:
		"""
		Read-only property to access the file's path (:attr:`_path`).

		:returns: The path, relative to the directory coverage.py ran in.
		"""
		return self._path

	@readonly
	def Functions(self) -> dict[str, Region]:
		"""
		Read-only property to access the functions (:attr:`_functions`).

		:returns: The functions, by qualified name; empty in format 2.
		"""
		return self._functions

	@readonly
	def Classes(self) -> dict[str, Region]:
		"""
		Read-only property to access the classes (:attr:`_classes`).

		:returns: The classes, by qualified name; empty in format 2.
		"""
		return self._classes


@export
class Report(metaclass=ExtendedType, mixin=True):
	"""
	The report's root: how and when it was written, the measured files, and the totals.
	"""

	_format:         Nullable[int]              #: Version of the report format.
	_version:        Nullable[SemanticVersion]  #: Version of coverage.py.
	_timestamp:      Nullable[datetime]         #: Time the report was written, local time without time zone.
	_branchCoverage: bool                       #: Whether branch coverage was measured.
	_hasContexts:    bool                       #: Whether the report lists the contexts of the lines.
	_files:          dict[Path, File]           #: The measured files, by path.
	_totals:         Nullable[Summary]          #: The counters of the whole report.

	def __init__(self) -> None:
		"""
		Initialize an empty report.
		"""
		self._format =         None
		self._version =        None
		self._timestamp =      None
		self._branchCoverage = False
		self._hasContexts =    False
		self._files =          {}
		self._totals =         None

	@readonly
	def Format(self) -> Nullable[int]:
		"""
		Read-only property to access the version of the report format (:attr:`_format`).

		:returns: The version, ``2`` or ``3``; ``None`` before the report was converted.
		"""
		return self._format

	@readonly
	def Version(self) -> Nullable[SemanticVersion]:
		"""
		Read-only property to access the version of coverage.py, which wrote the report (:attr:`_version`).

		:returns: The version, e.g. ``7.16.1``; ``None`` before the report was converted.
		"""
		return self._version

	@readonly
	def Timestamp(self) -> Nullable[datetime]:
		"""
		Read-only property to access the time the report was written (:attr:`_timestamp`).

		:returns: The time in the writer's local time, without a time zone; ``None`` before the report was converted.
		"""
		return self._timestamp

	@readonly
	def BranchCoverage(self) -> bool:
		"""
		Read-only property to access whether branch coverage was measured (:attr:`_branchCoverage`).

		:returns: ``True``, if branch coverage was measured.
		"""
		return self._branchCoverage

	@readonly
	def HasContexts(self) -> bool:
		"""
		Read-only property to access whether the report lists the contexts of the lines (:attr:`_hasContexts`).

		coverage.py includes them, when configured with ``[json] show_contexts = True``; the report states it as
		``show_contexts``.

		:returns: ``True``, if the files list the contexts of their lines.
		"""
		return self._hasContexts

	@readonly
	def Files(self) -> dict[Path, File]:
		"""
		Read-only property to access the measured files (:attr:`_files`).

		:returns: The files, by path.
		"""
		return self._files

	@readonly
	def Totals(self) -> Nullable[Summary]:
		"""
		Read-only property to access the counters of the whole report (:attr:`_totals`).

		:returns: The totals; ``None`` before the report was converted.
		"""
		return self._totals


@export
class Document(cc_Document, Report):
	"""
	A coverage.py JSON code coverage report: read into the format's model, and converted to the common model.
	"""

	_jsonDocument: Nullable[dict[str, Any]]  #: The parsed and validated JSON document, after :meth:`Analyze`.

	def __init__(self, jsonReportFile: Path, analyzeAndConvert: bool = False) -> None:
		"""
		Initialize the report, and optionally read it.

		:param jsonReportFile:    Path to the JSON file.
		:param analyzeAndConvert: Optional, if true, analyze the file and convert its content. Default: ``False``.
		"""
		super().__init__(jsonReportFile)
		Report.__init__(self)

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
			raise CodeCoverageError(f"coverage.py report file '{self._path}' does not exist.") \
				from FileNotFoundError(f"File '{self._path}' not found.")

		with Stopwatch() as sw:
			try:
				jsonDocument = loads(self._path.read_text(encoding="utf-8"))
			except JSONDecodeError as ex:
				raise CodeCoverageError(f"JSON syntax error in coverage.py report file '{self._path}'.") from ex

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
		:raises CodeCoverageError: If the report names a file's path twice.
		"""
		if self._jsonDocument is None:
			ex = CodeCoverageError(f"coverage.py report file '{self._path}' needs to be read and analyzed by a JSON parser.")
			ex.add_note(f"Call 'Document.Analyze()' or create the document using 'Document(path, analyzeAndConvert=True)'.")
			raise ex

		with Stopwatch() as sw:
			meta = self._jsonDocument["meta"]
			self._format =         meta["format"]
			self._version =        SemanticVersion.Parse(meta["version"])
			self._timestamp =      datetime.fromisoformat(meta["timestamp"])
			self._branchCoverage = meta["branch_coverage"]
			self._hasContexts =    meta["show_contexts"]
			self._totals =         Summary.Parse(self._jsonDocument["totals"])

			for name, record in self._jsonDocument["files"].items():
				File.Parse(name, record, parent=self)

		self._conversionDuration = sw.Duration

	def ToCoverageSummary(self) -> CoverageSummary:
		"""
		Convert the format's model to the common model, and aggregate it.

		:returns:                  The report's root of the common model, named after the report file.
		:raises CodeCoverageError: If a file's path runs through another file.
		"""
		summary = CoverageSummary(self._path.stem)

		for file in self._files.values():
			commonFile = summary.GetOrAddFile(file._path)
			self._ConvertLines(file, commonFile)
			self._ConvertUnits(file, commonFile, summary)

		summary.Aggregate()
		return summary

	@staticmethod
	def _ConvertLines(file: File, commonFile: cc_File) -> None:
		"""
		Convert a file's lines and branches to lines of the common model.

		:param file:       The file of the format's model.
		:param commonFile: The file of the common model.
		"""
		missingSources = {source for source, _ in file._missingBranches}

		statuses: dict[int, LineCoverageStatus] = {}
		for number in file._executedLines:
			partial = number in missingSources
			statuses[number] = LineCoverageStatus.PartiallyCovered if partial else LineCoverageStatus.Covered

		for number in file._missingLines:
			statuses[number] = LineCoverageStatus.Uncovered

		for number in file._excludedLines:
			statuses[number] = LineCoverageStatus.Excluded

		for number in sorted(statuses):
			cc_Line(number, statuses[number], parent=commonFile)

		lines =          commonFile._lines
		lastLineNumber = commonFile._lastLineNumber
		for status, arcs in (
			(LineCoverageStatus.Covered,   file._executedBranches),
			(LineCoverageStatus.Uncovered, file._missingBranches)
		):
			for source, target in arcs:
				cc_Branch(status, target=lines[target] if 0 < target <= lastLineNumber else None, parent=lines[source])

	@staticmethod
	def _ConvertUnits(file: File, commonFile: cc_File, summary: CoverageSummary) -> None:
		"""
		Convert a file to units: its directories to packages, the file to a module, its classes and functions to classes,
		methods and functions.

		:param file:       The file of the format's model.
		:param commonFile: The file of the common model.
		:param summary:    The report's root of the common model.
		"""
		path = file._path
		parent: cc_Unit | CoverageSummary = summary
		for part in path.parent.parts:
			parent = parent._units[part] if part in parent._units else cc_Package(part, parent=parent)

		lines =          commonFile._lines
		lastLineNumber = commonFile._lastLineNumber
		module = cc_Module(
			path.stem,
			file=commonFile,
			startLine=next(commonFile.IterateLines(), None),
			endLine=lines[lastLineNumber] if lastLineNumber > 0 else None,
			parent=parent
		)

		for kind, regions in (("class", file._classes), ("function", file._functions)):
			for name in sorted(regions):
				region = regions[name]
				*outerNames, ownName = name.split(".")

				# the enclosing class or function, found by the outer names; a region outside of a known one is left out
				container: Nullable[cc_Unit] = module
				for outerName in outerNames:
					if (container := container._units.get(outerName)) is None:
						break

				if container is None or ownName in container._units:
					continue

				if kind == "class":
					unitClass: type[cc_Unit] = cc_Class
				elif isinstance(container, cc_Class):
					unitClass = cc_Method
				else:
					unitClass = cc_Function

				numbers = [
					number for number in (region._startLine, *region.AllLines)
					if number <= lastLineNumber and lines[number] is not None
				]

				unitClass(
					ownName,
					file=commonFile,
					startLine=lines[min(numbers)] if len(numbers) > 0 else None,
					endLine=lines[max(numbers)] if len(numbers) > 0 else None,
					parent=container
				)
