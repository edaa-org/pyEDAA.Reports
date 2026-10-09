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
2.0.0 to 3.1.0. The format's model keeps what the report states: a :class:`Document` holds
:class:`~pyEDAA.Reports.CodeCoverage.LLVM.Records.File` records - each with its segments, branch regions, MC/DC records,
expansions and summary -, and :class:`~pyEDAA.Reports.CodeCoverage.LLVM.Records.Function` records - each with its
regions, branch regions and MC/DC records. The records are in :mod:`~pyEDAA.Reports.CodeCoverage.LLVM.Records`, the
source regions in :mod:`~pyEDAA.Reports.CodeCoverage.LLVM.Regions`, the summaries in
:mod:`~pyEDAA.Reports.CodeCoverage.LLVM.Summaries`.

Each class of the format's model takes typed values in its constructor, so a model can be built by hand, too. A
classmethod ``Parse`` reads the class' JSON element and calls the constructor; :meth:`Document.Convert` parses a
report's files, functions and totals with it.

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
from __future__                                 import annotations

from collections.abc                            import Iterable
from json                                       import JSONDecodeError, loads
from os.path                                    import commonprefix
from pathlib                                    import Path
from re                                         import match
from typing                                     import Any, Optional as Nullable

from jsonschema                                 import Draft202012Validator
from pyTooling.Common                           import getFullyQualifiedName, readResourceFile
from pyTooling.Decorators                       import export, readonly
from pyTooling.Exceptions                       import ToolingException
from pyTooling.MetaClasses                      import ExtendedType
from pyTooling.Stopwatch                        import Stopwatch
from pyTooling.Versioning                       import SemanticVersion

from pyEDAA.Reports                             import Resources
from pyEDAA.Reports.CodeCoverage                import Branch as cc_Branch, CodeCoverageError, CoverageSummary
from pyEDAA.Reports.CodeCoverage                import Document as cc_Document, File as cc_File, Function as cc_Function
from pyEDAA.Reports.CodeCoverage                import Line as cc_Line, LineCoverageStatus, SourceFile as cc_SourceFile
from pyEDAA.Reports.CodeCoverage.LLVM.Regions   import RegionKind
from pyEDAA.Reports.CodeCoverage.LLVM.Records   import File, Function, Segment
from pyEDAA.Reports.CodeCoverage.LLVM.Summaries import Summary


__all__ = ["SCHEMA"]

SCHEMA = "LLVM-Coverage-JSON.schema.json"  #: The JSON Schema a report is validated against.

@export
class Report(metaclass=ExtendedType, mixin=True):
	"""
	The report's root: the format version, the files, the functions, and the totals.
	"""

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

		:param version:     Optional, version of the report format. Default: ``None``.
		:param files:       Optional, the files. Default: none.
		:param functions:   Optional, the functions. Default: none.
		:param totals:      Optional, the counters of the whole report. Default: ``None``.
		:raises TypeError:  If parameter ``version`` isn't of type :class:`~pyTooling.Versioning.SemanticVersion`.
		:raises TypeError:  If parameter ``files`` or ``functions`` isn't iterable.
		:raises TypeError:  If parameter ``files`` contains an element not of type
		                    :class:`~pyEDAA.Reports.CodeCoverage.LLVM.Records.File`.
		:raises TypeError:  If parameter ``functions`` contains an element not of type
		                    :class:`~pyEDAA.Reports.CodeCoverage.LLVM.Records.Function`.
		:raises TypeError:  If parameter ``totals`` isn't of type
		                    :class:`~pyEDAA.Reports.CodeCoverage.LLVM.Summaries.Summary`.
		"""
		if version is not None and not isinstance(version, SemanticVersion):
			ex = TypeError(f"Parameter 'version' is not of type 'SemanticVersion'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(version)}'.")
			raise ex

		if totals is not None and not isinstance(totals, Summary):
			ex = TypeError(f"Parameter 'totals' is not of type 'Summary'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(totals)}'.")
			raise ex

		self._version =   version
		self._files =     {}
		self._functions = []
		self._totals =    totals

		if files is not None:
			if not isinstance(files, Iterable):
				ex = TypeError(f"Parameter 'files' is not iterable.")
				ex.add_note(f"Got type '{getFullyQualifiedName(files)}'.")
				raise ex

			for file in files:
				if not isinstance(file, File):
					ex = TypeError(f"Parameter 'files' contains an element not of type 'File'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(file)}'.")
					raise ex

				self._files[file._path] = file

		if functions is not None:
			if not isinstance(functions, Iterable):
				ex = TypeError(f"Parameter 'functions' is not iterable.")
				ex.add_note(f"Got type '{getFullyQualifiedName(functions)}'.")
				raise ex

			for function in functions:
				if not isinstance(function, Function):
					ex = TypeError(f"Parameter 'functions' contains an element not of type 'Function'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(function)}'.")
					raise ex

				self._functions.append(function)

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
		:raises TypeError:        If parameter ``files`` or ``functions`` isn't iterable.
		:raises TypeError:        If parameter ``files`` contains an element not of type
		                          :class:`~pyEDAA.Reports.CodeCoverage.LLVM.Records.File`.
		:raises TypeError:        If parameter ``functions`` contains an element not of type
		                          :class:`~pyEDAA.Reports.CodeCoverage.LLVM.Records.Function`.
		:raises TypeError:        If parameter ``totals`` isn't of type
		                          :class:`~pyEDAA.Reports.CodeCoverage.LLVM.Summaries.Summary`.
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
			ex.add_note(f"Call 'Document.Analyze()' or create the document using 'Document(path, analyzeAndConvert=True)'.")
			raise ex

		with Stopwatch() as sw:
			data =            self._jsonDocument["data"][0]
			self._version =   SemanticVersion.Parse(self._jsonDocument["version"])
			self._files =     {}
			self._functions = [Function.Parse(function) for function in data.get("functions", [])]
			self._totals =    Summary.Parse(data["totals"])

			for record in data["files"]:
				file =                    File.Parse(record)
				self._files[file._path] = file

		self._conversionDuration = sw.Duration

	def ToCoverageSummary(self) -> CoverageSummary:
		"""
		Convert the format's model to the common model, and aggregate it.

		:returns:                  The report's root of the common model, named after the report file.
		:raises CodeCoverageError: If a file's path runs through another file.
		:raises CodeCoverageError: If a function has a branch region in a file, which none of its regions expands to.
		"""
		common = commonprefix([path.parent.parts for path in self._files])

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
