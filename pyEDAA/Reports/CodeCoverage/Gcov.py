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
GCC's gcov JSON code coverage format: a model of the format, read from a report and converted to the common model.

gcov writes the format with ``gcov --json-format``: gzip-compressed to a :file:`*.gcov.json.gz` file per data file, or
- with ``--stdout`` - as plain JSON, one line per data file. A report is read in either form, and each JSON object in
it is validated against the JSON Schema :file:`Gcov-JSON.schema.json`, reverse-engineered from GCC, which accepts
format versions 1 (GCC 9 to 13) and 2 (GCC 14 and later). The format's model keeps what the report states: a
:class:`Document` holds :class:`DataFile` records, a data file :class:`File` records, and a file its
:class:`Function` and :class:`Line` records - a line in format 2 with the IDs of its basic blocks.

:meth:`Document.ToCoverageSummary` converts the model to the common model of :mod:`pyEDAA.Reports.CodeCoverage`:

* A file's path is relative to the directory the compiler ran in - a data file's ``current_working_directory`` -,
  unless it is absolute.
* A line's ``count`` is its count. A line several functions share - e.g. the instantiations of a template - or
  several data files state - e.g. a header - becomes one line, its counts added.
* A file becomes a source file unit, its functions - by demangled name, e.g. ``Containers::Stack::Pop()`` - become
  functions, each spanning its first to its last line, with its execution count.
* Basic blocks have no counterpart in the common model. The format has no excluded lines.

.. rubric:: Example

.. code-block:: Python

   from pathlib import Path
   from pyEDAA.Reports.CodeCoverage.Gcov import Document

   report = Document(Path("main.gcov.json.gz"), analyzeAndConvert=True)
   summary = report.ToCoverageSummary()
   print(f"{summary.FileCount} files: {summary.LineCoverage:.1%}")
"""
from __future__                  import annotations

from gzip                        import BadGzipFile, decompress
from json                        import JSONDecodeError, JSONDecoder, loads
from pathlib                     import Path
from re                          import compile as re_compile
from typing                      import Any, Optional as Nullable
from zlib                        import error as ZLibError

from jsonschema                  import Draft202012Validator
from pyTooling.Common            import readResourceFile
from pyTooling.Decorators        import export, readonly
from pyTooling.Exceptions        import ToolingException
from pyTooling.MetaClasses       import ExtendedType
from pyTooling.Stopwatch         import Stopwatch
from pyTooling.Versioning        import SemanticVersion

from pyEDAA.Reports              import Resources
from pyEDAA.Reports.CodeCoverage import CodeCoverageError, CoverageSummary
from pyEDAA.Reports.CodeCoverage import Document as cc_Document, File as cc_File, Function as cc_Function
from pyEDAA.Reports.CodeCoverage import Line as cc_Line, LineCoverageStatus, SourceFile as cc_SourceFile


__all__ = ["SCHEMA"]

SCHEMA = "Gcov-JSON.schema.json"  #: The JSON Schema each JSON object of a report is validated against.

# A class with a property named like a class - ``Path`` - can't name that class in the annotation of a field: the class
# body's namespace, where annotations are evaluated, binds the name to the property.
_Path = Path


@export
class Line(metaclass=ExtendedType, slots=True):
	"""
	A ``line`` of a file: how often it ran, and its basic blocks.
	"""

	_lineNumber:      int            #: Line number, counted from 1.
	_functionName:    Nullable[str]  #: Mangled name of the function the line belongs to, if the report says.
	_count:           int            #: Number of times the line ran.
	_unexecutedBlock: bool           #: Whether a basic block of the line, not only reached by exceptions, never ran.
	_blockIDs:        list[int]      #: IDs of the basic blocks ending on this line, in format 2.

	def __init__(self, record: dict[str, Any]) -> None:
		"""
		Initialize the line from its JSON object.

		:param record: The JSON object of the line.
		"""
		self._lineNumber =      record["line_number"]
		self._functionName =    record.get("function_name")
		self._count =           record["count"]
		self._unexecutedBlock = record["unexecuted_block"]
		self._blockIDs =        record.get("block_ids", [])

	@readonly
	def LineNumber(self) -> int:
		"""
		Read-only property to access the line number (:attr:`_lineNumber`).

		:returns: The line number, counted from 1.
		"""
		return self._lineNumber

	@readonly
	def FunctionName(self) -> Nullable[str]:
		"""
		Read-only property to access the mangled name of the function the line belongs to (:attr:`_functionName`).

		:returns: The function's name, or ``None`` for a line of inlined statements.
		"""
		return self._functionName

	@readonly
	def Count(self) -> int:
		"""
		Read-only property to access the number of times the line ran (:attr:`_count`).

		:returns: The count.
		"""
		return self._count

	@readonly
	def UnexecutedBlock(self) -> bool:
		"""
		Read-only property to access whether a basic block of the line never ran (:attr:`_unexecutedBlock`).

		A block only reached by exceptions doesn't count.

		:returns: ``True``, if not every statement of the line ran.
		"""
		return self._unexecutedBlock

	@readonly
	def BlockIDs(self) -> list[int]:
		"""
		Read-only property to access the IDs of the basic blocks ending on this line (:attr:`_blockIDs`).

		:returns: The blocks' IDs, unique within the function; empty in format 1.
		"""
		return self._blockIDs


@export
class Function(metaclass=ExtendedType, slots=True):
	"""
	A ``function`` of a file: its names, its position, its basic blocks and how often it ran.
	"""

	_name:           str  #: Name of the function, mangled.
	_demangledName:  str  #: Name of the function, demangled.
	_startLine:      int  #: The function's first line.
	_startColumn:    int  #: The function's first column.
	_endLine:        int  #: The function's last line.
	_endColumn:      int  #: The function's last column.
	_blocks:         int  #: Number of basic blocks.
	_blocksExecuted: int  #: Number of executed basic blocks.
	_executionCount: int  #: Number of times the function ran.

	def __init__(self, record: dict[str, Any]) -> None:
		"""
		Initialize the function from its JSON object.

		:param record: The JSON object of the function.
		"""
		self._name =           record["name"]
		self._demangledName =  record["demangled_name"]
		self._startLine =      record["start_line"]
		self._startColumn =    record["start_column"]
		self._endLine =        record["end_line"]
		self._endColumn =      record["end_column"]
		self._blocks =         record["blocks"]
		self._blocksExecuted = record["blocks_executed"]
		self._executionCount = record["execution_count"]

	@readonly
	def Name(self) -> str:
		"""
		Read-only property to access the mangled name of the function (:attr:`_name`).

		:returns: The name, e.g. ``_ZN10Containers5Stack3PopEv``.
		"""
		return self._name

	@readonly
	def DemangledName(self) -> str:
		"""
		Read-only property to access the demangled name of the function (:attr:`_demangledName`).

		:returns: The name, e.g. ``Containers::Stack::Pop()``.
		"""
		return self._demangledName

	@readonly
	def StartLine(self) -> int:
		"""
		Read-only property to access the function's first line (:attr:`_startLine`).

		:returns: The line number.
		"""
		return self._startLine

	@readonly
	def StartColumn(self) -> int:
		"""
		Read-only property to access the function's first column (:attr:`_startColumn`).

		:returns: The column number, counted from 1.
		"""
		return self._startColumn

	@readonly
	def EndLine(self) -> int:
		"""
		Read-only property to access the function's last line (:attr:`_endLine`).

		:returns: The line number.
		"""
		return self._endLine

	@readonly
	def EndColumn(self) -> int:
		"""
		Read-only property to access the function's last column (:attr:`_endColumn`).

		:returns: The column number, counted from 1.
		"""
		return self._endColumn

	@readonly
	def Blocks(self) -> int:
		"""
		Read-only property to access the number of basic blocks (:attr:`_blocks`).

		:returns: The number of blocks.
		"""
		return self._blocks

	@readonly
	def BlocksExecuted(self) -> int:
		"""
		Read-only property to access the number of executed basic blocks (:attr:`_blocksExecuted`).

		:returns: The number of executed blocks.
		"""
		return self._blocksExecuted

	@readonly
	def ExecutionCount(self) -> int:
		"""
		Read-only property to access the number of times the function ran (:attr:`_executionCount`).

		:returns: The count.
		"""
		return self._executionCount


@export
class File(metaclass=ExtendedType, slots=True):
	"""
	A source ``file`` of a data file: its functions and lines.

	A line several functions share - e.g. the instantiations of a template - is listed once per function.
	"""

	_path:      _Path                #: The file's path, as the compiler named it.
	_functions: dict[str, Function]  #: The functions, by mangled name.
	_lines:     list[Line]           #: The executable lines, in order; a line of several functions once per function.

	def __init__(self, record: dict[str, Any]) -> None:
		"""
		Initialize the file from its JSON object.

		:param record: The JSON object of the file.
		"""
		self._path =      Path(record["file"].replace("\\", "/"))
		self._functions = {function["name"]: Function(function) for function in record["functions"]}
		self._lines =     [Line(line) for line in record["lines"]]

	@readonly
	def Path(self) -> Path:
		"""
		Read-only property to access the file's path (:attr:`_path`).

		:returns: The path, relative to the directory the compiler ran in, unless absolute.
		"""
		return self._path

	@readonly
	def Functions(self) -> dict[str, Function]:
		"""
		Read-only property to access the functions (:attr:`_functions`).

		:returns: The functions, by mangled name.
		"""
		return self._functions

	@readonly
	def Lines(self) -> list[Line]:
		"""
		Read-only property to access the executable lines (:attr:`_lines`).

		:returns: The lines; a line several functions share is listed once per function.
		"""
		return self._lines


@export
class DataFile(metaclass=ExtendedType, slots=True):
	"""
	The coverage measured in a data file (GCDA): the versions of the format and of GCC, and the source files.
	"""

	_path:                    _Path              #: Path of the data file, as gcov was called with it.
	_formatVersion:           int                #: Version of the report format.
	_gccVersion:              SemanticVersion    #: Version of GCC.
	_currentWorkingDirectory: Nullable[_Path]    #: The directory the compiler ran in, if the report says.
	_files:                   dict[_Path, File]  #: The source files, by path.

	def __init__(self, record: dict[str, Any]) -> None:
		"""
		Initialize the data file from its JSON object.

		:param record: The JSON object of the data file: a report's root object.
		"""
		self._path =                    Path(record["data_file"].replace("\\", "/"))
		self._formatVersion =           int(record["format_version"])
		self._gccVersion =              SemanticVersion.Parse(record["gcc_version"].split(" ", 1)[0])
		self._currentWorkingDirectory = None
		self._files =                   {}

		if (directory := record.get("current_working_directory")) is not None:
			self._currentWorkingDirectory = Path(directory.replace("\\", "/"))

		for fileRecord in record["files"]:
			file =                    File(fileRecord)
			self._files[file._path] = file

	@readonly
	def Path(self) -> Path:
		"""
		Read-only property to access the path of the data file (:attr:`_path`).

		:returns: The path, as gcov was called with it, e.g. ``main.c``.
		"""
		return self._path

	@readonly
	def FormatVersion(self) -> int:
		"""
		Read-only property to access the version of the report format (:attr:`_formatVersion`).

		gcov states it as a string, e.g. ``"2"``.

		:returns: The version, ``1`` or ``2``.
		"""
		return self._formatVersion

	@readonly
	def GCCVersion(self) -> SemanticVersion:
		"""
		Read-only property to access the version of GCC (:attr:`_gccVersion`).

		A development build of GCC states its date and phase behind the version, e.g. ``15.0.1 20250418 (experimental)``;
		they aren't kept.

		:returns: The version, e.g. ``14.2.0``.
		"""
		return self._gccVersion

	@readonly
	def CurrentWorkingDirectory(self) -> Nullable[Path]:
		"""
		Read-only property to access the directory the compiler ran in (:attr:`_currentWorkingDirectory`).

		:returns: The directory, on the machine the code was compiled on, or ``None`` if the report doesn't say.
		"""
		return self._currentWorkingDirectory

	@readonly
	def Files(self) -> dict[Path, File]:
		"""
		Read-only property to access the source files (:attr:`_files`).

		:returns: The files, by path.
		"""
		return self._files


@export
class Coverage(metaclass=ExtendedType, slots=True):
	"""
	The content of a report file: the data files.
	"""

	_dataFiles: list[DataFile]  #: The data files, in the order the report lists them.

	def __init__(self) -> None:
		"""
		Initialize an empty report.
		"""
		self._dataFiles = []

	@readonly
	def DataFiles(self) -> list[DataFile]:
		"""
		Read-only property to access the data files (:attr:`_dataFiles`).

		:returns: The data files: one of a :file:`*.gcov.json.gz` file; one per line of gcov's standard output.
		"""
		return self._dataFiles


@export
class Document(Coverage, cc_Document):
	"""
	A gcov JSON code coverage report: read into the format's model, and converted to the common model.
	"""

	_jsonDocuments: Nullable[list[dict[str, Any]]]  #: The parsed and validated JSON objects, after :meth:`Analyze`.

	def __init__(self, jsonReportFile: Path, analyzeAndConvert: bool = False) -> None:
		"""
		Initialize the report, and optionally read it.

		:param jsonReportFile:    Path to the JSON file, gzip-compressed or plain.
		:param analyzeAndConvert: Optional, if true, analyze the file and convert its content. Default: ``False``.
		"""
		super().__init__()

		self._jsonDocuments = None

		cc_Document.__init__(self, jsonReportFile, analyzeAndConvert)

	def Analyze(self) -> None:
		"""
		Read the file - decompressing it, if gzip-compressed -, parse its JSON objects and validate each against the JSON
		Schema :data:`SCHEMA`.

		:raises CodeCoverageError: If the file doesn't exist.
		:raises CodeCoverageError: If the file is gzip-compressed, but corrupt.
		:raises CodeCoverageError: If the file isn't valid JSON.
		:raises CodeCoverageError: If the file holds no JSON object.
		:raises CodeCoverageError: If the JSON Schema can't be read.
		:raises CodeCoverageError: If a JSON object isn't valid according to the JSON Schema.
		"""
		if not self._path.exists():
			raise CodeCoverageError(f"gcov report file '{self._path}' does not exist.") \
				from FileNotFoundError(f"File '{self._path}' not found.")

		with Stopwatch() as sw:
			content = self._path.read_bytes()
			if content[:2] == b"\x1f\x8b":
				try:
					content = decompress(content)
				except (BadGzipFile, EOFError, ZLibError) as ex:
					raise CodeCoverageError(f"gzip error in gcov report file '{self._path}'.") from ex

			# gcov's standard output holds one JSON object per data file
			jsonDocuments = []
			try:
				text = content.decode("utf-8")
				decoder = JSONDecoder()
				nonWhitespace = re_compile(r"\S")
				position = 0
				while (match := nonWhitespace.search(text, position)) is not None:
					jsonDocument, position = decoder.raw_decode(text, match.start())
					jsonDocuments.append(jsonDocument)
			except (UnicodeDecodeError, JSONDecodeError) as ex:
				raise CodeCoverageError(f"JSON syntax error in gcov report file '{self._path}'.") from ex

			if len(jsonDocuments) == 0:
				raise CodeCoverageError(f"gcov report file '{self._path}' holds no JSON object.")

			try:
				schema = loads(readResourceFile(Resources, SCHEMA))
			except (ToolingException, JSONDecodeError) as ex:
				raise CodeCoverageError(f"Couldn't read JSON Schema '{SCHEMA}' from package resources.") from ex

			# a note per error; prefixed by the object's index, if the file holds several
			validator = Draft202012Validator(schema)
			notes = []
			for index, jsonDocument in enumerate(jsonDocuments):
				prefix = f"[{index}]" if len(jsonDocuments) > 1 else ""
				for error in sorted(validator.iter_errors(jsonDocument), key=lambda error: list(error.path)):
					notes.append(f"{prefix}/{'/'.join(str(part) for part in error.path)}: {error.message}")

			if len(notes) > 0:
				ex = CodeCoverageError(f"Validation error for '{self._path}' using JSON Schema '{SCHEMA}'.")
				for note in notes:
					ex.add_note(note)
				raise ex

			self._jsonDocuments = jsonDocuments

		self._analysisDuration = sw.Duration

	def Convert(self) -> None:
		"""
		Convert the parsed and validated JSON objects to the format's model.

		:raises CodeCoverageError: If the JSON file was not analyzed before. |br|
		                           Call 'Document.Analyze()' or create the document using
		                           'Document(path, analyzeAndConvert=True)'.
		"""
		if self._jsonDocuments is None:
			ex = CodeCoverageError(f"gcov report file '{self._path}' needs to be read and analyzed by a JSON parser.")
			ex.add_note(f"Call 'Document.Analyze()' or create the document using 'Document(path, analyzeAndConvert=True)'.")
			raise ex

		with Stopwatch() as sw:
			self._dataFiles = [DataFile(jsonDocument) for jsonDocument in self._jsonDocuments]

		self._conversionDuration = sw.Duration

	def ToCoverageSummary(self) -> CoverageSummary:
		"""
		Convert the format's model to the common model, and aggregate it.

		A source file several data files state - e.g. a header - becomes one file: the counts of its lines and of its
		functions are added. The directories the compiler ran in become the source directories.

		:returns:                  The report's root of the common model, named after the report file without the
		                           extensions ``.gcov``, ``.json`` and ``.gz``.
		:raises CodeCoverageError: If a file's path runs through another file.
		"""
		name = self._path.name.removesuffix(".gz").removesuffix(".json").removesuffix(".gcov")
		directories = {
			dataFile._currentWorkingDirectory for dataFile in self._dataFiles if dataFile._currentWorkingDirectory is not None
		}
		summary = CoverageSummary(name if name != "" else self._path.name, sourceDirectories=sorted(directories))

		# per file of the common model: the counts of its lines, and of its functions
		lineCounts:     dict[cc_File, dict[int, int]] = {}
		functionCounts: dict[cc_File, dict[str, tuple[int, int, int]]] = {}
		for dataFile in self._dataFiles:
			for file in dataFile._files.values():
				commonFile = summary.GetOrAddFile(file._path)
				counts =     lineCounts.setdefault(commonFile, {})
				functions =  functionCounts.setdefault(commonFile, {})

				for line in file._lines:
					counts[line._lineNumber] = counts.get(line._lineNumber, 0) + line._count

				for function in file._functions.values():
					startLine, endLine, count = functions.get(
						function._demangledName, (function._startLine, function._endLine, 0)
					)
					functions[function._demangledName] = (startLine, endLine, count + function._executionCount)

		for commonFile, counts in lineCounts.items():
			for number in sorted(counts):
				status = LineCoverageStatus.Covered if counts[number] > 0 else LineCoverageStatus.Uncovered
				cc_Line(number, status, counts[number], parent=commonFile)

			lines =          commonFile._lines
			lastLineNumber = commonFile._lastLineNumber
			sourceFile = cc_SourceFile(
				commonFile.Path.as_posix(),
				file=commonFile,
				startLine=next(commonFile.IterateLines(), None),
				endLine=lines[lastLineNumber] if lastLineNumber > 0 else None,
				parent=summary
			)

			for functionName, (startLine, endLine, count) in functionCounts[commonFile].items():
				numbers = [number for number in range(startLine, min(endLine, lastLineNumber) + 1) if lines[number] is not None]
				cc_Function(
					functionName,
					file=commonFile,
					startLine=lines[numbers[0]] if len(numbers) > 0 else None,
					endLine=lines[numbers[-1]] if len(numbers) > 0 else None,
					status=LineCoverageStatus.Covered if count > 0 else LineCoverageStatus.Uncovered,
					coverageCount=count,
					parent=sourceFile
				)

		summary.Aggregate()
		return summary
