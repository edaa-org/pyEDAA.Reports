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
its regions, branch regions and MC/DC records. The records below a file or a function are in
:mod:`~pyEDAA.Reports.CodeCoverage.LLVM.Records`.

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
from __future__                               import annotations

from json                                     import JSONDecodeError, loads
from os.path                                  import commonprefix
from pathlib                                  import Path
from re                                       import match
from typing                                   import Any, Optional as Nullable

from jsonschema                               import Draft202012Validator
from pyTooling.Common                         import readResourceFile
from pyTooling.Decorators                     import export, readonly
from pyTooling.Exceptions                     import ToolingException
from pyTooling.MetaClasses                    import ExtendedType
from pyTooling.Stopwatch                      import Stopwatch
from pyTooling.Versioning                     import SemanticVersion

from pyEDAA.Reports                           import Resources
from pyEDAA.Reports.CodeCoverage              import Branch as cc_Branch, CodeCoverageError, CoverageSummary
from pyEDAA.Reports.CodeCoverage              import Document as cc_Document, File as cc_File, Function as cc_Function
from pyEDAA.Reports.CodeCoverage              import Line as cc_Line, LineCoverageStatus, SourceFile as cc_SourceFile
from pyEDAA.Reports.CodeCoverage.LLVM.Records import BranchRegion, Expansion, MCDCRecord, Region, RegionKind
from pyEDAA.Reports.CodeCoverage.LLVM.Records import Segment, Summary


__all__ = ["SCHEMA"]

SCHEMA = "LLVM-Coverage-JSON.schema.json"  #: The JSON Schema a report is validated against.

# A class with a property named like a class - ``Path``, ``Summary`` - can't name that class in the annotation of a
# field: the class body's namespace, where annotations are evaluated, binds the name to the property.
_Path =    Path
_Summary = Summary


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

	def __init__(self, file: dict[str, Any]) -> None:
		"""
		Initialize the file from its JSON object.

		:param file: The JSON object of the file.
		"""
		self._path =        Path(file["filename"].replace("\\", "/"))
		self._segments =    [Segment(segment) for segment in file.get("segments", [])]
		self._branches =    [BranchRegion(branch) for branch in file.get("branches", [])]
		self._mcdcRecords = [MCDCRecord(record) for record in file.get("mcdc_records", [])]
		self._expansions =  [Expansion(expansion) for expansion in file.get("expansions", [])]
		self._summary =     Summary(file["summary"])

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

	def __init__(self, function: dict[str, Any]) -> None:
		"""
		Initialize the function from its JSON object.

		:param function: The JSON object of the function.
		"""
		self._name =        function["name"]
		self._count =       function["count"]
		self._regions =     [Region(region) for region in function["regions"]]
		self._branches =    [BranchRegion(branch) for branch in function.get("branches", [])]
		self._mcdcRecords = [MCDCRecord(record) for record in function.get("mcdc_records", [])]
		self._filePaths =   [Path(filename.replace("\\", "/")) for filename in function["filenames"]]

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


@export
class Report(metaclass=ExtendedType, slots=True):
	"""
	The report's root: the format version, the files, the functions, and the totals.
	"""

	_version:   Nullable[SemanticVersion]  #: Version of the report format.
	_files:     dict[Path, File]           #: The files, by path.
	_functions: list[Function]             #: The functions.
	_totals:    Nullable[Summary]          #: The counters of the whole report.

	def __init__(self) -> None:
		"""
		Initialize an empty report.
		"""
		self._version =   None
		self._files =     {}
		self._functions = []
		self._totals =    None

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
class Document(Report, cc_Document):
	"""
	An LLVM JSON code coverage export: read into the format's model, and converted to the common model.
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
			export = self._jsonDocument["data"][0]
			self._version =   SemanticVersion.Parse(self._jsonDocument["version"])
			self._files =     {}
			self._functions = [Function(function) for function in export.get("functions", [])]
			self._totals =    Summary(export["totals"])

			for record in export["files"]:
				file =                    File(record)
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
		Collect the branch regions of the functions by file, each at the line it starts at, or at the line its macro is
		expanded at; the counts of a branch region found in several functions - e.g. the instantiations of a template - are
		summed.

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
