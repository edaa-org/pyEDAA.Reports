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
:class:`Region` records of its functions and classes, and each its lines, branches and :class:`Summary`.

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
from typing                      import Any, Optional as Nullable

from jsonschema                  import Draft202012Validator
from pyTooling.Common            import readResourceFile
from pyTooling.Decorators        import export, readonly
from pyTooling.Exceptions        import ToolingException
from pyTooling.MetaClasses       import ExtendedType
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
	"""

	_statementCount:     int            #: Number of statements, without the excluded ones.
	_coveredLines:       int            #: Number of executed statements.
	_missingLines:       int            #: Number of statements, which never ran.
	_excludedLines:      int            #: Number of excluded lines.
	_percentCovered:     float          #: Coverage of statements and branches, in percent.
	_branchCount:        Nullable[int]  #: Number of branches, if branch coverage was measured.
	_coveredBranches:    Nullable[int]  #: Number of taken branches, if branch coverage was measured.
	_partialBranchCount: Nullable[int]  #: Number of partially covered lines, if branch coverage was measured.

	def __init__(self, summary: dict[str, Any]) -> None:
		"""
		Initialize the summary from its JSON object.

		:param summary: The JSON object ``summary``.
		"""
		self._statementCount =     summary["num_statements"]
		self._coveredLines =       summary["covered_lines"]
		self._missingLines =       summary["missing_lines"]
		self._excludedLines =      summary["excluded_lines"]
		self._percentCovered =     summary["percent_covered"]
		self._branchCount =        summary.get("num_branches")
		self._coveredBranches =    summary.get("covered_branches")
		self._partialBranchCount = summary.get("num_partial_branches")

	@readonly
	def StatementCount(self) -> int:
		"""
		Read-only property to access the number of statements, without the excluded ones (:attr:`_statementCount`).

		:returns: The number of statements.
		"""
		return self._statementCount

	@readonly
	def CoveredLines(self) -> int:
		"""
		Read-only property to access the number of executed statements (:attr:`_coveredLines`).

		:returns: The number of executed statements.
		"""
		return self._coveredLines

	@readonly
	def MissingLines(self) -> int:
		"""
		Read-only property to access the number of statements, which never ran (:attr:`_missingLines`).

		:returns: The number of missing statements.
		"""
		return self._missingLines

	@readonly
	def ExcludedLines(self) -> int:
		"""
		Read-only property to access the number of excluded lines (:attr:`_excludedLines`).

		:returns: The number of excluded lines.
		"""
		return self._excludedLines

	@readonly
	def PercentCovered(self) -> float:
		"""
		Read-only property to access the coverage of statements and branches (:attr:`_percentCovered`).

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
	def CoveredBranches(self) -> Nullable[int]:
		"""
		Read-only property to access the number of taken branches (:attr:`_coveredBranches`).

		:returns: The number of taken branches, or ``None`` if branch coverage wasn't measured.
		"""
		return self._coveredBranches

	@readonly
	def PartialBranchCount(self) -> Nullable[int]:
		"""
		Read-only property to access the number of partially covered lines (:attr:`_partialBranchCount`).

		:returns: The number of lines, which ran without taking all branches, or ``None`` if branch coverage wasn't
		          measured.
		"""
		return self._partialBranchCount


_Summary = Summary


@export
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

	def __init__(self, record: dict[str, Any]) -> None:
		"""
		Initialize the lines from their JSON object.

		:param record: The JSON object of the file or region.
		"""
		self._executedLines =    record["executed_lines"]
		self._missingLines =     record["missing_lines"]
		self._excludedLines =    record["excluded_lines"]
		self._executedBranches = [(source, target) for source, target in record.get("executed_branches", [])]
		self._missingBranches =  [(source, target) for source, target in record.get("missing_branches", [])]
		self._summary =          Summary(record["summary"])

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
class Region(Base):
	"""
	A function or a class of a file - in format 3 -, named by its qualified name, e.g. ``Circle.Area``.
	"""

	_name:      str  #: Qualified name of the function or class.
	_startLine: int  #: The region's first line.

	def __init__(self, name: str, record: dict[str, Any]) -> None:
		"""
		Initialize the region from its JSON object.

		:param name:   Qualified name of the function or class.
		:param record: The JSON object of the region.
		"""
		super().__init__(record)

		self._name =      name
		self._startLine = record["start_line"]

	@readonly
	def Name(self) -> str:
		"""
		Read-only property to access the qualified name of the function or class (:attr:`_name`).

		:returns: The qualified name.
		"""
		return self._name

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

	The regions named ``""`` - the lines outside of every function or class - aren't kept.
	"""

	_path:      _Path              #: The file's path, relative to the directory coverage.py ran in.
	_functions: dict[str, Region]  #: The functions, by qualified name.
	_classes:   dict[str, Region]  #: The classes, by qualified name.

	def __init__(self, path: Path, record: dict[str, Any]) -> None:
		"""
		Initialize the file from its JSON object.

		:param path:   The file's path, relative to the directory coverage.py ran in.
		:param record: The JSON object of the file.
		"""
		super().__init__(record)

		self._path =      path
		self._functions = {name: Region(name, region) for name, region in record.get("functions", {}).items() if name != ""}
		self._classes =   {name: Region(name, region) for name, region in record.get("classes", {}).items() if name != ""}

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
class Report(metaclass=ExtendedType, slots=True):
	"""
	The report's root: how and when it was written, the measured files, and the totals.
	"""

	_format:         Nullable[int]              #: Version of the report format.
	_version:        Nullable[SemanticVersion]  #: Version of coverage.py.
	_timestamp:      Nullable[datetime]         #: Time the report was written, local time without time zone.
	_branchCoverage: bool                       #: Whether branch coverage was measured.
	_showContexts:   bool                       #: Whether the lines' contexts are listed.
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
		self._showContexts =   False
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
	def ShowContexts(self) -> bool:
		"""
		Read-only property to access whether the lines' contexts are listed (:attr:`_showContexts`).

		:returns: ``True``, if the contexts are listed.
		"""
		return self._showContexts

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
class Document(Report, cc_Document):
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
		super().__init__()

		self._jsonDocument = None

		cc_Document.__init__(self, jsonReportFile, analyzeAndConvert)

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
			self._showContexts =   meta["show_contexts"]
			self._files =          {}
			self._totals =         Summary(self._jsonDocument["totals"])

			for name, record in self._jsonDocument["files"].items():
				path =              Path(name.replace("\\", "/"))
				self._files[path] = File(path, record)

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
