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
it is validated against the JSON Schema of the format version it states (:class:`FormatVersion`), reverse-engineered
from GCC: :file:`Gcov-1.schema.json` for format 1 (GCC 9 to 13), :file:`Gcov-2.schema.json` for format 2 (GCC 14 and
later). The format's model keeps what the report states: a :class:`Document` holds :class:`DataFile` records, a data
file :class:`File` records, and a file its :class:`~pyEDAA.Reports.CodeCoverage.Gcov.Records.Function` and
:class:`~pyEDAA.Reports.CodeCoverage.Gcov.Records.Line` records - a line in format 2 with the IDs of its basic blocks.
The records below a file are in :mod:`~pyEDAA.Reports.CodeCoverage.Gcov.Records`. Each record's constructor takes typed
values, so the model can be built by hand: a record below the report names its parent with the keyword parameter
``parent`` and is added to it. Its class method ``Parse`` reads the record's JSON object.

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
from __future__                               import annotations

from enum                                     import IntEnum
from gzip                                     import BadGzipFile, decompress
from json                                     import JSONDecodeError, JSONDecoder, loads
from pathlib                                  import Path
from re                                       import compile as re_compile
from typing                                   import Any, Optional as Nullable, Self
from zlib                                     import error as ZLibError

from jsonschema                               import Draft202012Validator
from pyTooling.Common                         import getFullyQualifiedName, readResourceFile
from pyTooling.Decorators                     import export, readonly
from pyTooling.Exceptions                     import ToolingException
from pyTooling.MetaClasses                    import ExtendedType
from pyTooling.Stopwatch                      import Stopwatch
from pyTooling.Versioning                     import SemanticVersion

from pyEDAA.Reports                           import Resources
from pyEDAA.Reports.CodeCoverage              import CodeCoverageError, CoverageSummary
from pyEDAA.Reports.CodeCoverage              import Document as cc_Document, File as cc_File, Function as cc_Function
from pyEDAA.Reports.CodeCoverage              import Line as cc_Line, LineCoverageStatus, SourceFile as cc_SourceFile


__all__ = ["SCHEMAS"]

# A class with a property named like a class - ``Path`` - can't name that class in the annotation of a field: the class
# body's namespace, where annotations are evaluated, binds the name to the property.
_Path = Path


@export
class FormatVersion(IntEnum):
	"""
	Version of the gcov JSON format, as a report's ``format_version`` states it.

	GCC 9 to 13 write format 1. GCC 14 and later write format 2, which adds the IDs of the basic blocks of a line and of
	a branch, and the calls and conditions of a line; GCC 15 adds the prime paths of a function to format 2.
	"""

	Version1 = 1  #: Format 1, written by GCC 9 to 13.
	Version2 = 2  #: Format 2, written by GCC 14 and later.

	@classmethod
	def Parse(cls, value: str) -> Self:
		"""
		Convert the version, as gcov states it - a string, e.g. ``"2"`` -, to the member of that version.

		:param value:       The version, as a report's ``format_version`` states it.
		:returns:           The member of that version.
		:raises ValueError: If parameter ``value`` is ``None``.
		:raises TypeError:  If parameter ``value`` isn't of type :class:`str`.
		:raises ValueError: If parameter ``value`` isn't a supported format version.
		"""
		if value is None:
			raise ValueError(f"Parameter 'value' is None.")
		elif not isinstance(value, str):
			ex = TypeError(f"Parameter 'value' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
			raise ex
		elif value not in [str(member.value) for member in cls]:
			ex = ValueError(f"Parameter 'value' is not a supported gcov JSON format version.")
			ex.add_note(f"Got value '{value}'.")
			ex.add_note(f"Supported format versions: {', '.join(str(member.value) for member in cls)}.")
			raise ex

		return cls(int(value))


# Like '_Path': DataFile has a property named 'FormatVersion'.
_FormatVersion = FormatVersion

SCHEMAS: dict[FormatVersion, str] = {
	FormatVersion.Version1: "Gcov-1.schema.json",
	FormatVersion.Version2: "Gcov-2.schema.json"
}  #: Per format version, the JSON Schema a JSON object of that version is validated against.


@export
class File(metaclass=ExtendedType, slots=True):
	"""
	A source ``file`` of a data file: its functions and lines.

	A line several functions share - e.g. the instantiations of a template - is listed once per function.
	"""

	_parent:    Nullable[DataFile]   #: The data file the file belongs to.
	_path:      _Path                #: The file's path, as the compiler named it.
	_functions: dict[str, Function]  #: The functions, by mangled name.
	_lines:     list[Line]           #: The executable lines, in order; a line of several functions once per function.

	def __init__(self, path: Path, *, parent: Nullable[DataFile] = None) -> None:
		"""
		Initialize the file, and add it to the files of its data file.

		Its functions and lines are added by creating them with this file as their parent.

		:param path:        The file's path, as the compiler named it.
		:param parent:      Optional, the data file the file belongs to; the file is added to its files by :attr:`Path`.
		                    Default: ``None``.
		:raises ValueError: If parameter ``path`` is ``None``.
		:raises TypeError:  If parameter ``path`` isn't of type :class:`~pathlib.Path`.
		:raises TypeError:  If parameter ``parent`` isn't of type :class:`DataFile`.
		"""
		if path is None:
			raise ValueError(f"Parameter 'path' is None.")
		elif not isinstance(path, Path):
			ex = TypeError(f"Parameter 'path' is not of type 'Path'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(path)}'.")
			raise ex

		if parent is not None and not isinstance(parent, DataFile):
			ex = TypeError(f"Parameter 'parent' is not of type 'DataFile'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =    parent
		self._path =      path
		self._functions = {}
		self._lines =     []

		if parent is not None:
			parent._files[self._path] = self

	@classmethod
	def Parse(cls, record: dict[str, Any], *, parent: Nullable[DataFile] = None) -> Self:
		"""
		Parse a file, its functions and lines from its JSON object.

		A backslash in the path - as a report written on Windows has them - separates directories.

		:param record:             The JSON object of the file.
		:param parent:             Optional, the data file the file belongs to. Default: ``None``.
		:returns:                  The file.
		:raises CodeCoverageError: If the file names a function twice.
		"""
		file = cls(Path(record["file"].replace("\\", "/")), parent=parent)

		for function in record["functions"]:
			if (name := function["name"]) in file._functions:
				raise CodeCoverageError(f"gcov source file '{file._path.as_posix()}' names function '{name}' twice.")

			Function.Parse(function, parent=file)

		for line in record["lines"]:
			Line.Parse(line, parent=file)

		return file

	@readonly
	def Parent(self) -> Nullable[DataFile]:
		"""
		Read-only property to access the data file the file belongs to (:attr:`_parent`).

		:returns: The data file; ``None`` if the file belongs to no data file.
		"""
		return self._parent

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


# 'Records' imports 'File', the parent of its records, so it's imported after 'File' is defined.
from pyEDAA.Reports.CodeCoverage.Gcov.Records import Function, Line


@export
class DataFile(metaclass=ExtendedType, slots=True):
	"""
	The coverage measured in a data file (GCDA): the versions of the format and of GCC, and the source files.
	"""

	_parent:                  Nullable[Coverage]  #: The report the data file belongs to.
	_path:                    _Path               #: Path of the data file, as gcov was called with it.
	_formatVersion:           _FormatVersion      #: Version of the report format.
	_gccVersion:              SemanticVersion     #: Version of GCC.
	_currentWorkingDirectory: Nullable[_Path]     #: The directory the compiler ran in, if the report says.
	_files:                   dict[_Path, File]   #: The source files, by path.

	def __init__(
		self,
		path:                    Path,
		formatVersion:           FormatVersion,
		gccVersion:              SemanticVersion,
		currentWorkingDirectory: Nullable[Path] = None,
		*,
		parent:                  Nullable[Coverage] = None
	) -> None:
		"""
		Initialize the data file, and add it to the data files of its report.

		Its source files are added by creating them with this data file as their parent.

		:param path:                    Path of the data file, as gcov was called with it.
		:param formatVersion:           Version of the report format.
		:param gccVersion:              Version of GCC.
		:param currentWorkingDirectory: Optional, the directory the compiler ran in. Default: ``None``.
		:param parent:                  Optional, the report the data file belongs to; the data file is appended to its
		                                data files. Default: ``None``.
		:raises ValueError:             If parameter ``path`` is ``None``.
		:raises TypeError:              If parameter ``path`` isn't of type :class:`~pathlib.Path`.
		:raises ValueError:             If parameter ``formatVersion`` is ``None``.
		:raises TypeError:              If parameter ``formatVersion`` isn't of type :class:`FormatVersion`.
		:raises ValueError:             If parameter ``gccVersion`` is ``None``.
		:raises TypeError:              If parameter ``gccVersion`` isn't of type
		                                :class:`~pyTooling.Versioning.SemanticVersion`.
		:raises TypeError:              If parameter ``currentWorkingDirectory`` isn't of type :class:`~pathlib.Path`.
		:raises TypeError:              If parameter ``parent`` isn't of type :class:`Coverage`.
		"""
		if path is None:
			raise ValueError(f"Parameter 'path' is None.")
		elif not isinstance(path, Path):
			ex = TypeError(f"Parameter 'path' is not of type 'Path'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(path)}'.")
			raise ex

		if formatVersion is None:
			raise ValueError(f"Parameter 'formatVersion' is None.")
		elif not isinstance(formatVersion, FormatVersion):
			ex = TypeError(f"Parameter 'formatVersion' is not of type 'FormatVersion'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(formatVersion)}'.")
			raise ex

		if gccVersion is None:
			raise ValueError(f"Parameter 'gccVersion' is None.")
		elif not isinstance(gccVersion, SemanticVersion):
			ex = TypeError(f"Parameter 'gccVersion' is not of type 'SemanticVersion'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(gccVersion)}'.")
			raise ex

		if currentWorkingDirectory is not None and not isinstance(currentWorkingDirectory, Path):
			ex = TypeError(f"Parameter 'currentWorkingDirectory' is not of type 'Path'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(currentWorkingDirectory)}'.")
			raise ex

		if parent is not None and not isinstance(parent, Coverage):
			ex = TypeError(f"Parameter 'parent' is not of type 'Coverage'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =                  parent
		self._path =                    path
		self._formatVersion =           formatVersion
		self._gccVersion =              gccVersion
		self._currentWorkingDirectory = currentWorkingDirectory
		self._files =                   {}

		if parent is not None:
			parent._dataFiles.append(self)

	@classmethod
	def Parse(cls, record: dict[str, Any], *, parent: Nullable[Coverage] = None) -> Self:
		"""
		Parse a data file and its source files from its JSON object.

		The format version is converted by :meth:`FormatVersion.Parse`; a development build of GCC states its date and
		phase behind its version, e.g. ``15.0.1 20250418 (experimental)``. A backslash in a path - as a report written on
		Windows has them - separates directories.

		:param record:             The JSON object of the data file: a report's root object.
		:param parent:             Optional, the report the data file belongs to. Default: ``None``.
		:returns:                  The data file.
		:raises CodeCoverageError: If the data file names a source file twice.
		"""
		directory = record.get("current_working_directory")
		dataFile = cls(
			Path(record["data_file"].replace("\\", "/")),
			FormatVersion.Parse(record["format_version"]),
			SemanticVersion.Parse(record["gcc_version"].split(" ", 1)[0]),
			Path(directory.replace("\\", "/")) if directory is not None else None,
			parent=parent
		)

		for file in record["files"]:
			if (path := Path(file["file"].replace("\\", "/"))) in dataFile._files:
				raise CodeCoverageError(
					f"gcov data file '{dataFile._path.as_posix()}' names source file '{path.as_posix()}' twice."
				)

			File.Parse(file, parent=dataFile)

		return dataFile

	@readonly
	def Parent(self) -> Nullable[Coverage]:
		"""
		Read-only property to access the report the data file belongs to (:attr:`_parent`).

		:returns: The report; ``None`` if the data file belongs to no report.
		"""
		return self._parent

	@readonly
	def Path(self) -> Path:
		"""
		Read-only property to access the path of the data file (:attr:`_path`).

		It is the path gcov was called with, e.g. ``main.c`` for ``gcov --json-format main.c``.

		:returns: The path, as gcov was called with it.
		"""
		return self._path

	@readonly
	def FormatVersion(self) -> FormatVersion:
		"""
		Read-only property to access the version of the report format (:attr:`_formatVersion`).

		:returns: The format version.
		"""
		return self._formatVersion

	@readonly
	def GCCVersion(self) -> SemanticVersion:
		"""
		Read-only property to access the version of GCC (:attr:`_gccVersion`).

		A development build of GCC states its date and phase behind the version, e.g. ``15.0.1 20250418 (experimental)``;
		they aren't kept.

		:returns: The version.
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

	The root of the format's model: a data file names it as its parent.
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
		Schema of the format version it states (:data:`SCHEMAS`).

		:raises CodeCoverageError: If the file doesn't exist.
		:raises CodeCoverageError: If the file is gzip-compressed, but corrupt.
		:raises CodeCoverageError: If the file isn't valid JSON.
		:raises CodeCoverageError: If the file holds no JSON object.
		:raises CodeCoverageError: If a JSON object states no supported format version.
		:raises CodeCoverageError: If a JSON Schema can't be read.
		:raises CodeCoverageError: If a JSON object isn't valid according to the JSON Schema of its format version.
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

			# a note's path is prefixed by the object's index, if the file holds several
			validators: dict[FormatVersion, Draft202012Validator] = {}
			for index, jsonDocument in enumerate(jsonDocuments):
				prefix = f"[{index}]" if len(jsonDocuments) > 1 else ""

				version = jsonDocument.get("format_version") if isinstance(jsonDocument, dict) else None
				try:
					formatVersion = FormatVersion.Parse(version)
				except (ValueError, TypeError) as ex:
					error = CodeCoverageError(f"gcov report file '{self._path}' states an unsupported format version.")
					got = f"value '{version}'" if version is not None else "no value"
					error.add_note(f"Got {got} at '{prefix}/format_version'.")
					error.add_note(f"Supported format versions: {', '.join(str(member.value) for member in FormatVersion)}.")
					raise error from ex

				schemaFile = SCHEMAS[formatVersion]
				if (validator := validators.get(formatVersion)) is None:
					try:
						schema = loads(readResourceFile(Resources, schemaFile))
					except (ToolingException, JSONDecodeError) as ex:
						raise CodeCoverageError(f"Couldn't read JSON Schema '{schemaFile}' from package resources.") from ex

					validator = validators[formatVersion] = Draft202012Validator(schema)

				errors = sorted(validator.iter_errors(jsonDocument), key=lambda error: list(error.path))
				if len(errors) > 0:
					ex = CodeCoverageError(f"Validation error for '{self._path}' using JSON Schema '{schemaFile}'.")
					for error in errors:
						ex.add_note(f"{prefix}/{'/'.join(str(part) for part in error.path)}: {error.message}")
					raise ex

			self._jsonDocuments = jsonDocuments

		self._analysisDuration = sw.Duration

	def Convert(self) -> None:
		"""
		Convert the parsed and validated JSON objects to the format's model.

		:raises CodeCoverageError: If the JSON file was not analyzed before. |br|
		                           Call 'Document.Analyze()' or create the document using
		                           'Document(path, analyzeAndConvert=True)'.
		:raises CodeCoverageError: If a data file names a source file twice.
		:raises CodeCoverageError: If a source file names a function twice.
		"""
		if self._jsonDocuments is None:
			ex = CodeCoverageError(f"gcov report file '{self._path}' needs to be read and analyzed by a JSON parser.")
			ex.add_note(f"Call 'Document.Analyze()' or create the document using 'Document(path, analyzeAndConvert=True)'.")
			raise ex

		with Stopwatch() as sw:
			for jsonDocument in self._jsonDocuments:
				DataFile.Parse(jsonDocument, parent=self)

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
