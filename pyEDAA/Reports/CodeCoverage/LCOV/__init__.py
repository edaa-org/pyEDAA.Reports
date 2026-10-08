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
lcov's tracefile format: a model of the format, read from a tracefile and converted to the common model.

lcov writes the format with ``lcov --capture``; other tools write it too - e.g. ``llvm-cov export -format=lcov``,
coverage.py (``coverage lcov``) or GHDL (``ghdl coverage --format=lcov``). The format is specified by lcov's manual
page :manpage:`geninfo(1)`, section *TRACEFILE FORMAT*: a text file of records, one per line, e.g.
``DA:<line number>,<execution count>``. The format's model keeps what the tracefile states: a :class:`Document` holds
:class:`~pyEDAA.Reports.CodeCoverage.LCOV.Records.Section` records - a source file, as a test measured it -, a section
:class:`~pyEDAA.Reports.CodeCoverage.LCOV.Records.Function`, :class:`~pyEDAA.Reports.CodeCoverage.LCOV.Records.Line`,
:class:`~pyEDAA.Reports.CodeCoverage.LCOV.Records.Branch` and
:class:`~pyEDAA.Reports.CodeCoverage.LCOV.Records.Condition` records, and the summaries it states.

A tracefile is read by a strict line parser: an unknown, malformed or misplaced record raises an exception, which notes
the record's line number.

:meth:`Document.ToCoverageSummary` converts the model to the common model of :mod:`pyEDAA.Reports.CodeCoverage`:

* A section's source file is a file; sections of the same file - one per test - are merged, their counts added.
* A line's execution count is its count; a branching line is partially covered, if one of its branches wasn't taken. A
  branch never evaluated - ``-`` - is uncovered without count.
* A file becomes a source file unit, its functions function units, each spanning its start to its end line.
* The format has no excluded lines, no branch targets and no units but functions; the conditions of MC/DC coverage
  have no counterpart in the common model.

.. rubric:: Example

.. code-block:: Python

   from pathlib import Path
   from pyEDAA.Reports.CodeCoverage.LCOV import Document

   tracefile = Document(Path("coverage.info"), analyzeAndConvert=True)
   summary = tracefile.ToCoverageSummary()
   for file in summary.IterateFiles():
     print(f"{file.Path}: {file.LineCoverage:.1%}")
"""
from __future__                               import annotations

from pathlib                                  import Path
from re                                       import Pattern, compile as re_compile
from typing                                   import Optional as Nullable

from pyTooling.Decorators                     import export, readonly
from pyTooling.MetaClasses                    import ExtendedType
from pyTooling.Stopwatch                      import Stopwatch

from pyEDAA.Reports.CodeCoverage              import Branch as cc_Branch, CodeCoverageError, CoverageSummary
from pyEDAA.Reports.CodeCoverage              import Document as cc_Document, File as cc_File, Function as cc_Function
from pyEDAA.Reports.CodeCoverage              import Line as cc_Line, LineCoverageStatus, SourceFile as cc_SourceFile
from pyEDAA.Reports.CodeCoverage.LCOV.Records import Branch, Condition, Function, Line, Section


__all__ = ["RECORD_PATTERNS", "RECORD_SYNTAX"]

#: The pattern of each record's value - the text after ``<key>:`` -, by key.
RECORD_PATTERNS: dict[str, Pattern[str]] = {
	"TN":   re_compile(r"(.*)"),
	"SF":   re_compile(r"(.+)"),
	"VER":  re_compile(r"(.+)"),
	"FN":   re_compile(r"([1-9]\d*),(?:([1-9]\d*),)?(.+)"),
	"FNDA": re_compile(r"(\d+),(.+)"),
	"FNL":  re_compile(r"(\d+),([1-9]\d*)(?:,([1-9]\d*))?"),
	"FNA":  re_compile(r"(\d+),(\d+),(.+)"),
	"FNF":  re_compile(r"(\d+)"),
	"FNH":  re_compile(r"(\d+)"),
	"BRDA": re_compile(r"([1-9]\d*),(e?)(\d+),(.+),(\d+|-)"),
	"BRF":  re_compile(r"(\d+)"),
	"BRH":  re_compile(r"(\d+)"),
	"MCDC": re_compile(r"([1-9]\d*),(\d+),([tf]),(\d+),(\d+),(.+)"),
	"MCF":  re_compile(r"(\d+)"),
	"MCH":  re_compile(r"(\d+)"),
	"DA":   re_compile(r"([1-9]\d*),(\d+)(?:,([^,\s]+))?"),
	"LF":   re_compile(r"(\d+)"),
	"LH":   re_compile(r"(\d+)"),
}

#: The syntax of each record, as :manpage:`geninfo(1)` states it, by key.
RECORD_SYNTAX: dict[str, str] = {
	"TN":            "TN:<test name>",
	"SF":            "SF:<path to the source file>",
	"VER":           "VER:<version ID>",
	"FN":            "FN:<line number of function start>,[<line number of function end>,]<function name>",
	"FNDA":          "FNDA:<execution count>,<function name>",
	"FNL":           "FNL:<index>,<line number of function start>[,<line number of function end>]",
	"FNA":           "FNA:<index>,<execution count>,<name>",
	"FNF":           "FNF:<number of functions found>",
	"FNH":           "FNH:<number of functions hit>",
	"BRDA":          "BRDA:<line number>,[<exception>]<block>,<branch>,<taken>",
	"BRF":           "BRF:<number of branches found>",
	"BRH":           "BRH:<number of branches hit>",
	"MCDC":          "MCDC:<line number>,<group size>,<sense>,<taken>,<index>,<expression>",
	"MCF":           "MCF:<number of conditions found>",
	"MCH":           "MCH:<number of conditions hit>",
	"DA":            "DA:<line number>,<execution count>[,<checksum>]",
	"LF":            "LF:<number of instrumented lines>",
	"LH":            "LH:<number of lines with a non-zero execution count>",
	"end_of_record": "end_of_record",
}


@export
class Tracefile(metaclass=ExtendedType, mixin=True):
	"""
	A tracefile: its comments and sections.
	"""

	_comments: list[str]      #: The comments, without the leading ``#``.
	_sections: list[Section]  #: The sections, in the tracefile's order.

	def __init__(self) -> None:
		"""
		Initialize an empty tracefile.
		"""
		self._comments = []
		self._sections = []

	@readonly
	def Comments(self) -> list[str]:
		"""
		Read-only property to access the comments (:attr:`_comments`).

		A tool writes them on request, e.g. ``lcov --comment``.

		:returns: The comments, without the leading ``#``.
		"""
		return self._comments

	@readonly
	def Sections(self) -> list[Section]:
		"""
		Read-only property to access the sections (:attr:`_sections`).

		:returns: The sections, in the tracefile's order; a source file has a section per test.
		"""
		return self._sections


@export
class Document(cc_Document, Tracefile):
	"""
	An lcov tracefile: read into the format's model, and converted to the common model.
	"""

	_records: Nullable[list[tuple[int, str, str, tuple[Nullable[str], ...]]]]  #: The records, after :meth:`Analyze`.

	def __init__(self, tracefile: Path, analyzeAndConvert: bool = False) -> None:
		"""
		Initialize the tracefile, and optionally read it.

		:param tracefile:         Path to the tracefile.
		:param analyzeAndConvert: Optional, if true, analyze the file and convert its content. Default: ``False``.
		"""
		super().__init__(tracefile)
		Tracefile.__init__(self)

		self._records = None

		if analyzeAndConvert:
			self.Analyze()
			self.Convert()

	def Analyze(self) -> None:
		"""
		Read the tracefile and parse each line into a record: a comment, or a key and its values.

		Empty lines are skipped.

		:raises CodeCoverageError: If the file doesn't exist.
		:raises CodeCoverageError: If the file isn't UTF-8 encoded.
		:raises CodeCoverageError: If a line is no record lcov knows. |br|
		                           The exception notes the line and the known records.
		:raises CodeCoverageError: If a record's values don't match its syntax. |br|
		                           The exception notes the line and the record's syntax.
		"""
		if not self._path.exists():
			raise CodeCoverageError(f"lcov tracefile '{self._path}' does not exist.") \
				from FileNotFoundError(f"File '{self._path}' not found.")

		with Stopwatch() as sw:
			try:
				content = self._path.read_text(encoding="utf-8")
			except UnicodeDecodeError as ex:
				raise CodeCoverageError(f"lcov tracefile '{self._path}' is not UTF-8 encoded.") from ex

			records: list[tuple[int, str, str, tuple[Nullable[str], ...]]] = []
			for lineNumber, text in enumerate(content.splitlines(), start=1):
				text = text.rstrip()
				if text == "":
					continue
				elif text.startswith("#"):
					records.append((lineNumber, text, "#", (text[1:], )))
					continue
				elif text == "end_of_record":
					records.append((lineNumber, text, text, ()))
					continue

				key, colon, value = text.partition(":")
				if colon == "" or (pattern := RECORD_PATTERNS.get(key)) is None:
					ex = CodeCoverageError(f"Unknown record '{key}' in lcov tracefile '{self._path}'.")
					ex.add_note(f"Line {lineNumber}: '{text}'")
					ex.add_note(f"Known records: {', '.join(RECORD_SYNTAX)}")
					raise ex
				elif (match := pattern.fullmatch(value)) is None:
					ex = CodeCoverageError(f"Malformed record '{key}' in lcov tracefile '{self._path}'.")
					ex.add_note(f"Line {lineNumber}: '{text}'")
					ex.add_note(f"Expected '{RECORD_SYNTAX[key]}'.")
					raise ex

				records.append((lineNumber, text, key, match.groups()))

			self._records = records

		self._analysisDuration = sw.Duration

	def Convert(self) -> None:
		"""
		Convert the parsed records to the format's model: comments, and sections from ``SF`` to ``end_of_record``.

		A ``TN`` record names the test of the sections after it. A line listed twice in a section - as geninfo may write
		it - counts the sum.

		:raises CodeCoverageError: If the tracefile was not analyzed before. |br|
		                           Call 'Document.Analyze()' or create the document using
		                           'Document(path, analyzeAndConvert=True)'.
		:raises CodeCoverageError: If a section starts before the previous one ended. |br|
		                           The exception notes the line.
		:raises CodeCoverageError: If a record other than a comment, ``TN`` or ``SF`` is outside of a section. |br|
		                           The exception notes the line.
		:raises CodeCoverageError: If a ``TN`` record is inside of a section. |br|
		                           The exception notes the line.
		:raises CodeCoverageError: If a section states a function name or ``FNL`` index twice. |br|
		                           The exception notes the line.
		:raises CodeCoverageError: If an ``FNDA`` or ``FNA`` record refers to an unknown function. |br|
		                           The exception notes the line.
		:raises CodeCoverageError: If an ``FNL`` record has no ``FNA`` record. |br|
		                           The exception notes the section's last line.
		:raises CodeCoverageError: If the last section doesn't end with ``end_of_record``. |br|
		                           The exception notes the section's first line.
		"""
		if self._records is None:
			ex = CodeCoverageError(f"lcov tracefile '{self._path}' needs to be read and analyzed by a line parser.")
			ex.add_note(f"Call 'Document.Analyze()' or create the document using 'Document(path, analyzeAndConvert=True)'.")
			raise ex

		with Stopwatch() as sw:
			testName = ""
			section: Nullable[Section] = None
			sectionLineNumber = 0
			functionsByName: dict[str, Function] = {}
			functionsByIndex: dict[int, Function] = {}
			for lineNumber, text, key, values in self._records:
				if key == "#":
					self._comments.append(values[0])
				elif key == "SF":
					if section is not None:
						ex = CodeCoverageError(f"Record 'SF' inside the section of '{section._sourceFile}' in '{self._path}'.")
						ex.add_note(f"Line {lineNumber}: '{text}'")
						ex.add_note(f"End the section of line {sectionLineNumber} with 'end_of_record'.")
						raise ex

					section = Section(testName, Path(values[0].replace("\\", "/")), parent=self)
					sectionLineNumber = lineNumber
					functionsByName = {}
					functionsByIndex = {}
				elif key == "TN":
					if section is not None:
						ex = CodeCoverageError(f"Record 'TN' inside the section of '{section._sourceFile}' in '{self._path}'.")
						ex.add_note(f"Line {lineNumber}: '{text}'")
						raise ex

					testName = values[0]
				elif section is None:
					ex = CodeCoverageError(f"Record '{key}' outside of a section in lcov tracefile '{self._path}'.")
					ex.add_note(f"Line {lineNumber}: '{text}'")
					ex.add_note(f"A section starts with '{RECORD_SYNTAX['SF']}'.")
					raise ex
				elif key == "end_of_record":
					for index, function in functionsByIndex.items():
						if len(function._aliases) == 0:
							ex = CodeCoverageError(f"Function index {index} has no alias in the section of '{section._sourceFile}'.")
							ex.add_note(f"The section ends in line {lineNumber}.")
							ex.add_note(f"Name the function by '{RECORD_SYNTAX['FNA']}'.")
							raise ex

					section = None
				elif key == "DA":
					number, count = int(values[0]), int(values[1])
					if (line := section._lines.get(number)) is None:
						Line(number, count, values[2], parent=section)
					else:
						line._count += count
				elif key == "BRDA":
					taken = None if values[4] == "-" else int(values[4])
					section._branches.append(Branch(int(values[0]), int(values[2]), values[3], taken, values[1] == "e"))
				elif key == "MCDC":
					section._conditions.append(Condition(
						int(values[0]), int(values[1]), values[2] == "t", int(values[3]), int(values[4]), values[5]
					))
				elif key == "FN":
					if (name := values[2]) in functionsByName:
						ex = CodeCoverageError(f"Function '{name}' is stated twice in the section of '{section._sourceFile}'.")
						ex.add_note(f"Line {lineNumber}: '{text}'")
						raise ex

					function = Function(int(values[0]), None if values[1] is None else int(values[1]), parent=section)
					function._aliases[name] = None
					functionsByName[name] = function
				elif key == "FNL":
					if (index := int(values[0])) in functionsByIndex:
						ex = CodeCoverageError(f"Function index {index} is stated twice in the section of '{section._sourceFile}'.")
						ex.add_note(f"Line {lineNumber}: '{text}'")
						raise ex

					function = Function(int(values[1]), None if values[2] is None else int(values[2]), index, parent=section)
					functionsByIndex[index] = function
				elif key == "FNDA" or key == "FNA":
					if key == "FNDA":
						count, name = int(values[0]), values[1]
						function = functionsByName.get(name)
					else:
						count, name = int(values[1]), values[2]
						function = functionsByIndex.get(int(values[0]))

					if function is None:
						ex = CodeCoverageError(f"Record '{key}' refers to an unknown function in '{self._path}'.")
						ex.add_note(f"Line {lineNumber}: '{text}'")
						raise ex

					previous = function._aliases.get(name)
					function._aliases[name] = count if previous is None else previous + count
				elif key == "VER":
					section._version = values[0]
				elif key == "FNF":
					section._functionsFound = int(values[0])
				elif key == "FNH":
					section._functionsHit = int(values[0])
				elif key == "BRF":
					section._branchesFound = int(values[0])
				elif key == "BRH":
					section._branchesHit = int(values[0])
				elif key == "MCF":
					section._conditionsFound = int(values[0])
				elif key == "MCH":
					section._conditionsHit = int(values[0])
				elif key == "LF":
					section._linesFound = int(values[0])
				else:
					section._linesHit = int(values[0])

			if section is not None:
				ex = CodeCoverageError(f"Missing 'end_of_record' at the end of lcov tracefile '{self._path}'.")
				ex.add_note(f"The section of '{section._sourceFile}' starts in line {sectionLineNumber}.")
				raise ex

		self._conversionDuration = sw.Duration

	def ToCoverageSummary(self) -> CoverageSummary:
		"""
		Convert the format's model to the common model, and aggregate it.

		The sections of one source file - one per test - are one file: the counts of a line, of a branch and of a function
		are added. A line is partially covered, if one of its branches wasn't taken; a line with branches, but without
		``DA`` record, has an unknown state. A file becomes a source file unit, spanning its first to its last line, its
		functions become function units, each spanning its start to its end line; a function without end line - e.g. from
		llvm-cov - names its start line only.

		:returns:                  The report's root of the common model, named after the tracefile.
		:raises CodeCoverageError: If a file's path runs through another file.
		"""
		summary = CoverageSummary(self._path.stem)

		files: dict[int, cc_File] = {}
		lineCounts: dict[int, dict[int, int]] = {}
		branchCounts: dict[int, dict[tuple[int, int, str, bool], Nullable[int]]] = {}
		functionCounts: dict[int, dict[str, tuple[int, Nullable[int], Nullable[int]]]] = {}
		for section in self._sections:
			file = summary.GetOrAddFile(section._sourceFile)
			files[id(file)] = file

			lines = lineCounts.setdefault(id(file), {})
			for number, line in section._lines.items():
				lines[number] = lines.get(number, 0) + line._count

			branches = branchCounts.setdefault(id(file), {})
			for branch in section._branches:
				key = (branch._lineNumber, branch._block, branch._expression, branch._isException)
				taken = branches.get(key)
				if branch._taken is not None:
					branches[key] = branch._taken if taken is None else taken + branch._taken
				elif key not in branches:
					branches[key] = None

			functions = functionCounts.setdefault(id(file), {})
			for function in section._functions:
				count = function.Count
				if (merged := functions.get(function.Name)) is not None and merged[2] is not None:
					count = merged[2] if count is None else merged[2] + count
				functions[function.Name] = (function._startLine, function._endLine, count)

		for fileID, file in files.items():
			self._ConvertLines(file, lineCounts[fileID], branchCounts[fileID])
			self._ConvertUnits(file, functionCounts[fileID], summary)

		summary.Aggregate()
		return summary

	@staticmethod
	def _ConvertLines(
		file: cc_File,
		lineCounts: dict[int, int],
		branchCounts: dict[tuple[int, int, str, bool], Nullable[int]]
	) -> None:
		"""
		Convert a file's merged line and branch counts to lines of the common model.

		:param file:         The file of the common model.
		:param lineCounts:   The execution counts, by line number.
		:param branchCounts: How often each branch was taken - ``None``, if never evaluated -, by line number, block,
		                     expression and exception flag.
		"""
		branchesByLine: dict[int, list[Nullable[int]]] = {}
		for (lineNumber, *_), taken in branchCounts.items():
			branchesByLine.setdefault(lineNumber, []).append(taken)

		for lineNumber in sorted({*lineCounts, *branchesByLine}):
			takenCounts = branchesByLine.get(lineNumber, [])
			statuses = [
				LineCoverageStatus.Covered if taken is not None and taken > 0 else LineCoverageStatus.Uncovered
				for taken in takenCounts
			]
			branches = [cc_Branch(status, taken) for status, taken in zip(statuses, takenCounts)]

			if (count := lineCounts.get(lineNumber)) is None:
				status = LineCoverageStatus.Unknown
			elif count == 0:
				status = LineCoverageStatus.Uncovered
			elif LineCoverageStatus.Uncovered in statuses:
				status = LineCoverageStatus.PartiallyCovered
			else:
				status = LineCoverageStatus.Covered

			cc_Line(lineNumber, status, count, branches, parent=file)

	@staticmethod
	def _ConvertUnits(
		file: cc_File,
		functionCounts: dict[str, tuple[int, Nullable[int], Nullable[int]]],
		summary: CoverageSummary
	) -> None:
		"""
		Convert a file to a source file unit, and its functions to function units.

		:param file:           The file of the common model.
		:param functionCounts: The start line, end line and count of each function, by name.
		:param summary:        The report's root of the common model.
		"""
		lines =          file._lines
		lastLineNumber = file._lastLineNumber
		sourceFile = cc_SourceFile(
			file.Path.as_posix(),
			file=file,
			startLine=next(file.IterateLines(), None),
			endLine=lines[lastLineNumber] if lastLineNumber > 0 else None,
			parent=summary
		)

		for name, (start, end, count) in functionCounts.items():
			if end is None:
				startLine = lines[start] if start <= lastLineNumber else None
				endLine = None
			else:
				numbers = [number for number in range(start, min(end, lastLineNumber) + 1) if lines[number] is not None]
				startLine = lines[numbers[0]] if len(numbers) > 0 else None
				endLine = lines[numbers[-1]] if len(numbers) > 0 else None

			if count is None:
				status = LineCoverageStatus.Unknown
			else:
				status = LineCoverageStatus.Covered if count > 0 else LineCoverageStatus.Uncovered

			cc_Function(
				name, file=file, startLine=startLine, endLine=endLine, status=status, coverageCount=count, parent=sourceFile
			)
