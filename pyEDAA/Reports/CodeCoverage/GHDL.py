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
GHDL's JSON code coverage format: a model of the format, read from coverage files, merged, and converted to the common
model.

GHDL writes the format when simulating with ``ghdl -r --coverage``, by default to :file:`coverage-<timestamp>.json`. A
coverage file is validated against the JSON Schema :file:`GHDL-Coverage.schema.json`, reverse-engineered from
GHDL, which accepts format version 1.0.0. The format's model keeps what the file states: a :class:`Document` holds
:class:`File` records, each with its checksum and, per line with a coverage point, whether the line ran.

:class:`MergedReport` merges the coverage files of several simulation runs, as ``ghdl coverage`` reads several files.
:meth:`Document.ToCoverageSummary` and :meth:`MergedReport.ToCoverageSummary` convert to the common model of
:mod:`pyEDAA.Reports.CodeCoverage`:

* A file's path is the name it was analyzed by - relative to the directory GHDL ran in -, or, if analyzed in another
  directory, prefixed by that directory.
* A line that ran is covered, a line that didn't uncovered. The format states statement coverage as a flag per line:
  it has no counts, no branches and no excluded lines.
* The format names no units: no design units, processes or subprograms.

.. rubric:: Example

.. code-block:: Python

   from pathlib import Path
   from pyEDAA.Reports.CodeCoverage.GHDL import Document, MergedReport

   documents = []
   for path in sorted(Path(".").glob("coverage-*.json")):
     documents.append(Document(path, analyzeAndConvert=True))

   summary = MergedReport("Counter", documents).ToCoverageSummary()
   print(f"{summary.FileCount} files: {summary.LineCoverage:.1%}")
"""
from __future__                  import annotations

from collections.abc             import Iterable
from datetime                    import datetime, timezone
from json                        import JSONDecodeError, loads
from pathlib                     import Path
from typing                      import Any, Optional as Nullable

from jsonschema                  import Draft202012Validator
from pyTooling.Common            import getFullyQualifiedName, readResourceFile, StringEnum
from pyTooling.Decorators        import export, readonly
from pyTooling.Exceptions        import ToolingException
from pyTooling.MetaClasses       import ExtendedType
from pyTooling.Stopwatch         import Stopwatch
from pyTooling.Versioning        import SemanticVersion

from pyEDAA.Reports              import Resources
from pyEDAA.Reports.CodeCoverage import CodeCoverageError, CoverageSummary, Document as cc_Document, Line as cc_Line
from pyEDAA.Reports.CodeCoverage import LineCoverageStatus


__all__ = ["SCHEMA"]

SCHEMA = "GHDL-Coverage.schema.json"  #: The JSON Schema a coverage file is validated against.

# A class with a property named like a class - ``Path`` - can't name that class in the annotation of a field: the class
# body's namespace, where annotations are evaluated, binds the name to the property.
_Path = Path


@export
class CoverageMode(StringEnum):
	"""
	Kind of coverage of a source file, as stated by an entry's ``mode``.

	GHDL writes only ``stmt``: its writer :file:`src/ghdldrv/ghdlcovout.adb` knows no other kind of coverage, and its
	reader :file:`src/ghdldrv/ghdlcov.adb` skips the field.
	"""

	Statement = "stmt"  #: Statement coverage: per line with a statement, whether a statement of the line ran.


@export
class File(metaclass=ExtendedType, slots=True):
	"""
	An entry of ``outputs``: a source file, where it was analyzed, its checksum, and its lines with coverage points.
	"""

	_name:      _Path            #: The file's name, as given to the analysis.
	_directory: _Path            #: The directory the file was analyzed in; ``.`` for the directory GHDL ran in.
	_sha1:      str              #: SHA-1 checksum of the file's content.
	_mode:      CoverageMode     #: Kind of coverage, e.g. statement coverage.
	_lastLine:  int              #: The last line with a coverage point.
	_result:    dict[int, bool]  #: Per line with a coverage point, whether the line ran.

	def __init__(
		self,
		name: Path,
		directory: Path,
		sha1: str,
		mode: CoverageMode,
		lastLine: int,
		result: dict[int, bool]
	) -> None:
		"""
		Initialize the file from the fields of its JSON object.

		:param name:      The file's name, as given to the analysis.
		:param directory: The directory the file was analyzed in; ``.`` for the directory GHDL ran in.
		:param sha1:      SHA-1 checksum of the file's content.
		:param mode:      Kind of coverage, e.g. statement coverage.
		:param lastLine:  The last line with a coverage point.
		:param result:    Per line with a coverage point, whether the line ran.
		"""
		self._name =      name
		self._directory = directory
		self._sha1 =      sha1
		self._mode =      mode
		self._lastLine =  lastLine
		self._result =    result

	@readonly
	def Name(self) -> Path:
		"""
		Read-only property to access the file's name, as given to the analysis (:attr:`_name`).

		:returns: The name, e.g. ``src/Counter.vhdl``.
		"""
		return self._name

	@readonly
	def Directory(self) -> Path:
		"""
		Read-only property to access the directory the file was analyzed in (:attr:`_directory`).

		:returns: The directory; ``.`` for the directory GHDL ran in and for an absolute name.
		"""
		return self._directory

	@readonly
	def Path(self) -> Path:
		"""
		Read-only property to return the file's path: its :attr:`Name`, prefixed by its :attr:`Directory` unless ``.``.

		:returns: The path, as ``ghdl coverage`` names the file.
		"""
		return self._directory / self._name

	@readonly
	def SHA1(self) -> str:
		"""
		Read-only property to access the SHA-1 checksum of the file's content (:attr:`_sha1`).

		:returns: The checksum, 40 hexadecimal digits.
		"""
		return self._sha1

	@readonly
	def Mode(self) -> CoverageMode:
		"""
		Read-only property to access the kind of coverage (:attr:`_mode`).

		:returns: The kind of coverage, e.g. :attr:`CoverageMode.Statement`.
		"""
		return self._mode

	@readonly
	def LastLine(self) -> int:
		"""
		Read-only property to access the last line with a coverage point (:attr:`_lastLine`).

		:returns: The line number.
		"""
		return self._lastLine

	@readonly
	def Result(self) -> dict[int, bool]:
		"""
		Read-only property to access whether each line with a coverage point ran (:attr:`_result`).

		:returns: Per line number, ``True`` if a statement of the line ran.
		"""
		return self._result


@export
class Report(metaclass=ExtendedType, slots=True):
	"""
	The coverage file's root: the format's version, when it was written, and the source files.
	"""

	_version:   Nullable[SemanticVersion]  #: Version of the format.
	_testcase:  Nullable[str]              #: Name of the testcase.
	_timestamp: Nullable[datetime]         #: Time the file was written, UTC.
	_files:     dict[Path, File]           #: The source files, by path.

	def __init__(self) -> None:
		"""
		Initialize an empty report.
		"""
		self._version =   None
		self._testcase =  None
		self._timestamp = None
		self._files =     {}

	@readonly
	def Version(self) -> Nullable[SemanticVersion]:
		"""
		Read-only property to access the version of the format (:attr:`_version`).

		:returns: The version, ``1.0.0``; ``None`` before the coverage file was converted.
		"""
		return self._version

	@readonly
	def Testcase(self) -> Nullable[str]:
		"""
		Read-only property to access the name of the testcase (:attr:`_testcase`).

		:returns: The name; GHDL writes ``unknown``.
		"""
		return self._testcase

	@readonly
	def Timestamp(self) -> Nullable[datetime]:
		"""
		Read-only property to access the time the coverage file was written (:attr:`_timestamp`).

		GHDL states it in UTC, to the millisecond, as ``YYYYMMDDhhmmss.mmm``.

		:returns: The time, with time zone UTC; ``None`` before the coverage file was converted.
		"""
		return self._timestamp

	@readonly
	def Files(self) -> dict[Path, File]:
		"""
		Read-only property to access the source files (:attr:`_files`).

		:returns: The files, by :attr:`File.Path`.
		"""
		return self._files


@export
class Document(Report, cc_Document):
	"""
	A GHDL coverage file: read into the format's model, and converted to the common model.
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
			raise CodeCoverageError(f"GHDL coverage file '{self._path}' does not exist.") \
				from FileNotFoundError(f"File '{self._path}' not found.")

		with Stopwatch() as sw:
			try:
				jsonDocument = loads(self._path.read_text(encoding="utf-8"))
			except JSONDecodeError as ex:
				raise CodeCoverageError(f"JSON syntax error in GHDL coverage file '{self._path}'.") from ex

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
		:raises CodeCoverageError: If the JSON file names a source file twice.
		:raises CodeCoverageError: If a source file's result names a line beyond its ``max-line``.
		"""
		if self._jsonDocument is None:
			ex = CodeCoverageError(f"GHDL coverage file '{self._path}' needs to be read and analyzed by a JSON parser.")
			ex.add_note(f"Call 'Document.Analyze()' or create the document using 'Document(path, analyzeAndConvert=True)'.")
			raise ex

		with Stopwatch() as sw:
			timestamp = datetime.strptime(self._jsonDocument["timestamp"], "%Y%m%d%H%M%S.%f")

			self._version =   SemanticVersion.Parse(self._jsonDocument["version"])
			self._testcase =  self._jsonDocument["testcase"]
			self._timestamp = timestamp.replace(tzinfo=timezone.utc)

			files: dict[Path, File] = {}
			for output in self._jsonDocument["outputs"]:
				file = File(
					Path(output["file"].replace("\\", "/")),
					Path(output["dir"].replace("\\", "/")),
					output["sha1"],
					CoverageMode.Parse(output["mode"]),
					output["max-line"],
					{int(number): ran == 1 for number, ran in output["result"].items()}
				)

				if (path := file.Path) in files:
					raise CodeCoverageError(f"GHDL coverage file '{self._path}' names source file '{path}' twice.")
				elif (line := max(file._result)) > file._lastLine:
					ex = CodeCoverageError(f"GHDL coverage file '{self._path}' names a line of '{path}' beyond 'max-line'.")
					ex.add_note(f"Got line {line} for 'max-line' {file._lastLine}.")
					raise ex

				files[path] = file

			self._files = files

		self._conversionDuration = sw.Duration

	def ToCoverageSummary(self) -> CoverageSummary:
		"""
		Convert the format's model to the common model, and aggregate it.

		:returns:                  The report's root of the common model, named after the coverage file.
		:raises CodeCoverageError: If a file's path runs through another file.
		"""
		return MergedReport(self._path.stem, (self, )).ToCoverageSummary()


@export
class MergedReport(metaclass=ExtendedType, slots=True):
	"""
	The coverage files of several simulation runs, merged: a line ran, if it ran in one of the runs.

	``ghdl coverage`` reads several coverage files too, but a line's result there is the result of the last file naming
	the line.
	"""

	_name:    str               #: Name of the merged report.
	_reports: list[Report]      #: The merged reports, in the order they were merged.
	_files:   dict[Path, File]  #: The merged source files, by path.

	def __init__(self, name: str, reports: Nullable[Iterable[Report]] = None) -> None:
		"""
		Initialize a merged report, and merge the given reports.

		:param name:               Name of the merged report, e.g. of the design simulated.
		:param reports:            Optional, the reports to merge. Default: ``None``.
		:raises ValueError:        If parameter ``name`` is ``None``.
		:raises TypeError:         If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError:        If parameter ``name`` is empty.
		:raises TypeError:         If parameter ``reports`` isn't iterable.
		:raises TypeError:         If parameter ``reports`` contains an element not of type :class:`Report`.
		:raises CodeCoverageError: If a source file's checksum differs between two reports.
		"""
		if name is None:
			raise ValueError(f"Parameter 'name' is None.")
		elif not isinstance(name, str):
			ex = TypeError(f"Parameter 'name' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(name)}'.")
			raise ex
		elif name == "":
			raise ValueError(f"Parameter 'name' is empty.")

		self._name =    name
		self._reports = []
		self._files =   {}

		if reports is not None:
			if not isinstance(reports, Iterable):
				ex = TypeError(f"Parameter 'reports' is not iterable.")
				ex.add_note(f"Got type '{getFullyQualifiedName(reports)}'.")
				raise ex

			for report in reports:
				if not isinstance(report, Report):
					ex = TypeError(f"Parameter 'reports' contains an element not of type 'Report'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(report)}'.")
					raise ex

				self.Merge(report)

	def Merge(self, report: Report) -> None:
		"""
		Merge a report: add its source files, or merge them into the files of the same path.

		A merged line ran, if it ran in one of the reports; a merged file's :attr:`File.LastLine` is the largest.

		:param report:             The report to merge.
		:raises ValueError:        If parameter ``report`` is ``None``.
		:raises TypeError:         If parameter ``report`` isn't of type :class:`Report`.
		:raises CodeCoverageError: If a source file's checksum differs from the checksum in a report merged before.
		"""
		if report is None:
			raise ValueError(f"Parameter 'report' is None.")
		elif not isinstance(report, Report):
			ex = TypeError(f"Parameter 'report' is not of type 'Report'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(report)}'.")
			raise ex

		for path, file in report._files.items():
			if (merged := self._files.get(path)) is None:
				self._files[path] = File(
					file._name, file._directory, file._sha1, file._mode, file._lastLine, dict(file._result)
				)
			elif merged._sha1 != file._sha1:
				ex = CodeCoverageError(f"Content of source file '{path}' differs from the reports merged before.")
				ex.add_note(f"Got SHA-1 checksum '{file._sha1}' instead of '{merged._sha1}'.")
				raise ex
			else:
				merged._lastLine = max(merged._lastLine, file._lastLine)
				result = merged._result
				for number, ran in file._result.items():
					result[number] = ran or result.get(number, False)

		self._reports.append(report)

	@readonly
	def Name(self) -> str:
		"""
		Read-only property to access the name of the merged report (:attr:`_name`).

		:returns: The name.
		"""
		return self._name

	@readonly
	def Reports(self) -> list[Report]:
		"""
		Read-only property to access the merged reports (:attr:`_reports`).

		:returns: The reports, in the order they were merged.
		"""
		return self._reports

	@readonly
	def Files(self) -> dict[Path, File]:
		"""
		Read-only property to access the merged source files (:attr:`_files`).

		:returns: The files, by :attr:`File.Path`.
		"""
		return self._files

	def ToCoverageSummary(self) -> CoverageSummary:
		"""
		Convert the merged source files to the common model, and aggregate it.

		:returns:                  The report's root of the common model, named after the merged report.
		:raises CodeCoverageError: If a file's path runs through another file.
		"""
		summary = CoverageSummary(self._name)

		for path, file in self._files.items():
			commonFile = summary.GetOrAddFile(path)
			result =     file._result
			for number in sorted(result):
				cc_Line(
					number,
					LineCoverageStatus.Covered if result[number] else LineCoverageStatus.Uncovered,
					parent=commonFile
				)

		summary.Aggregate()
		return summary
