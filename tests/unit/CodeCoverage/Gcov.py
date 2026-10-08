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
"""Unit tests of GCC's gcov JSON format: its model, its JSON Schema and the conversion to the common model."""
from json                             import dumps, loads
from pathlib                          import Path
from tempfile                         import TemporaryDirectory
from typing                           import Any

from pyEDAA.Reports.CodeCoverage      import CodeCoverageError, Function, LineCoverageStatus, SourceFile
from pyEDAA.Reports.CodeCoverage.Gcov import Document
from pyTooling.Testing                import Testcase


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


DATA =   Path(__file__).parent.parent.parent / "data" / "CodeCoverage" / "GCC"  #: Directory of the reports and sources.
STREAM = DATA / "All.gcov.json"                                                 #: gcov's standard output of both.
GZIP =   DATA / "Main.gcov.json.gz"                                             #: gcov's report of 'Main.cpp'.


def _write(directory: str, content: str | bytes) -> Path:
	"""
	Write a report file into a directory.

	:param directory: The directory.
	:param content:   The report's text or bytes.
	:returns:         The report file.
	"""
	jsonFile = Path(directory) / "test.gcov.json"
	if isinstance(content, str):
		jsonFile.write_text(content, encoding="utf-8")
	else:
		jsonFile.write_bytes(content)
	return jsonFile


def _stream() -> list[dict[str, Any]]:
	"""
	Read the JSON objects of gcov's standard output.

	:returns: The JSON objects, one per data file.
	"""
	return [loads(line) for line in STREAM.read_text(encoding="utf-8").splitlines()]


class FormatModel(Testcase):
	"""The format's model keeps what the report states: data files, files, functions and lines."""

	def test_DataFiles(self) -> None:
		report = Document(STREAM, analyzeAndConvert=True)

		self.assertEqual(["Statistics.c", "Main.cpp"], [dataFile.Path.as_posix() for dataFile in report.DataFiles])
		main = report.DataFiles[1]
		self.assertEqual(("2", "14.2.0"), (main.FormatVersion, main.GCCVersion))
		self.assertTrue(main.CurrentWorkingDirectory.is_absolute())
		self.assertEqual([Path("Main.cpp"), Path("Containers/Stack.hpp")], list(main.Files))

	def test_Functions(self) -> None:
		stack = Document(STREAM, analyzeAndConvert=True).DataFiles[1].Files[Path("Containers/Stack.hpp")]

		pop = stack.Functions["_ZN10Containers5Stack3PopEv"]
		self.assertEqual("Containers::Stack::Pop()", pop.DemangledName)
		self.assertEqual((19, 8, 23, 4), (pop.StartLine, pop.StartColumn, pop.EndLine, pop.EndColumn))
		self.assertEqual((8, 7, 3), (pop.Blocks, pop.BlocksExecuted, pop.ExecutionCount))

	def test_Lines(self) -> None:
		stack = Document(STREAM, analyzeAndConvert=True).DataFiles[1].Files[Path("Containers/Stack.hpp")]

		line = next(line for line in stack.Lines if line.LineNumber == 21)
		self.assertEqual(("_ZN10Containers5Stack3PopEv", 1, False, [3, 4, 5, 8]),
		                 (line.FunctionName, line.Count, line.UnexecutedBlock, line.BlockIDs))

	def test_Template(self) -> None:
		"""A line of a template is listed once per instantiation."""
		main = Document(STREAM, analyzeAndConvert=True).DataFiles[1].Files[Path("Main.cpp")]

		self.assertEqual([("_Z7MaximumIdET_S0_S0_", 1), ("_Z7MaximumIiET_S0_S0_", 1)], [
			(line.FunctionName, line.Count) for line in main.Lines if line.LineNumber == 9
		])

	def test_Gzip(self) -> None:
		"""gcov's compressed report holds the same as its standard output."""
		dataFile, = Document(GZIP, analyzeAndConvert=True).DataFiles

		self.assertEqual(Path("Main.cpp"), dataFile.Path)
		self.assertEqual([Path("Main.cpp"), Path("Containers/Stack.hpp")], list(dataFile.Files))

	def test_Backslashes(self) -> None:
		"""The backslashes of a report written on Windows separate directories."""
		main = _stream()[1]
		main["current_working_directory"] = "C:\\build"
		main["data_file"] =                 "src\\Main.cpp"
		main["files"][1]["file"] =          "Containers\\Stack.hpp"
		with TemporaryDirectory() as directory:
			dataFile, = Document(_write(directory, dumps(main)), analyzeAndConvert=True).DataFiles

		self.assertEqual((Path("C:/build"), Path("src/Main.cpp")), (dataFile.CurrentWorkingDirectory, dataFile.Path))
		self.assertEqual(Path("Containers/Stack.hpp"), dataFile.Files[Path("Containers/Stack.hpp")].Path)


class Conversion(Testcase):
	"""The conversion to the common model: files, lines, source files and functions."""

	def test_Counts(self) -> None:
		"""The computed counters agree with gcov's own summary, except for the lines of a template."""
		summary = Document(STREAM, analyzeAndConvert=True).ToCoverageSummary()

		self.assertEqual(["Main.cpp", "Statistics.c", "Containers/Stack.hpp"], [
			file.Path.as_posix() for file in summary.IterateFiles()
		])
		# gcov: 'Lines executed:100.00% of 20' - it counts the 2 lines of the template once per instantiation
		for path, counters in (
			("Statistics.c",         (21, 17)),
			("Containers/Stack.hpp", (11, 10)),
			("Main.cpp",             (16, 16))
		):
			with self.subTest(path=path):
				file = summary.GetOrAddFile(path)
				self.assertEqual(counters, (file.TotalLines, file.CoveredLines))

		self.assertEqual((48, 43, 0), (summary.TotalLines, summary.CoveredLines, summary.ExcludedLines))

	def test_Lines(self) -> None:
		summary = Document(STREAM, analyzeAndConvert=True).ToCoverageSummary()
		statistics = summary.Files["Statistics.c"]

		line = statistics.Lines[14]
		self.assertEqual((LineCoverageStatus.Covered, 4), (line.Status, line.CoverageCount))
		self.assertEqual((LineCoverageStatus.Uncovered, 0), (statistics.Lines[6].Status, statistics.Lines[6].CoverageCount))
		self.assertIsNone(statistics.Lines[10])

	def test_Template(self) -> None:
		"""A line of a template becomes one line, its counts added."""
		line = Document(STREAM, analyzeAndConvert=True).ToCoverageSummary().Files["Main.cpp"].Lines[9]

		self.assertEqual((LineCoverageStatus.Covered, 2), (line.Status, line.CoverageCount))

	def test_Units(self) -> None:
		summary = Document(STREAM, analyzeAndConvert=True).ToCoverageSummary()

		units = {unit.QualifiedName: unit for unit in summary.IterateUnits()}
		self.assertEqual(["Containers/Stack.hpp", "Main.cpp", "Statistics.c"], sorted(summary.Units))
		for name, unitClass in (
			("Statistics.c", SourceFile), ("Statistics.c.Clamp", Function), ("Main.cpp.int Maximum<int>(int, int)", Function),
			("Containers/Stack.hpp.Containers::Stack::Pop()", Function)
		):
			with self.subTest(name=name):
				self.assertIsInstance(units[name], unitClass)

		pop = units["Containers/Stack.hpp.Containers::Stack::Pop()"]
		self.assertEqual((19, 22, 3), (pop.StartLine.LineNumber, pop.EndLine.LineNumber, pop.CoverageCount))
		self.assertEqual((4, 4), (pop.TotalLines, pop.CoveredLines))

		twice = units["Statistics.c.Twice"]
		self.assertEqual((LineCoverageStatus.Uncovered, 0, 2, 0),
		                 (twice.Status, twice.CoverageCount, twice.TotalLines, twice.CoveredLines))

		source = units["Statistics.c"]
		self.assertEqual((LineCoverageStatus.Unknown, 4, 32), (
			source.Status, source.StartLine.LineNumber, source.EndLine.LineNumber
		))

	def test_SourceDirectories(self) -> None:
		report = Document(STREAM, analyzeAndConvert=True)

		self.assertEqual([report.DataFiles[0].CurrentWorkingDirectory], report.ToCoverageSummary().SourceDirectories)

	def test_Name(self) -> None:
		self.assertEqual("Main", Document(GZIP, analyzeAndConvert=True).ToCoverageSummary().Name)

	def test_Merge(self) -> None:
		"""A file several data files state - here the same data file twice - becomes one file, its counts added."""
		main = _stream()[1]
		with TemporaryDirectory() as directory:
			report = Document(_write(directory, f"{dumps(main)}\n{dumps(main)}\n"), analyzeAndConvert=True)

		summary = report.ToCoverageSummary()
		stack = summary.Directories["Containers"].Files["Stack.hpp"]
		self.assertEqual((2, 6), (stack.Lines[21].CoverageCount, stack.Lines[20].CoverageCount))
		self.assertEqual(11, stack.TotalLines)
		self.assertEqual(6, summary.Units["Containers/Stack.hpp"].Units["Containers::Stack::Pop()"].CoverageCount)

	def test_Format1(self) -> None:
		"""Format 1 has no basic blocks."""
		document = {
			"format_version": "1", "gcc_version": "13.2.0", "data_file": "main.c", "files": [{
				"file": "main.c",
				"functions": [{
					"name": "main", "demangled_name": "main", "start_line": 1, "start_column": 5, "end_line": 4,
					"end_column": 1, "blocks": 4, "blocks_executed": 3, "execution_count": 1
				}],
				"lines": [
					{"line_number": 1, "function_name": "main", "count": 1, "unexecuted_block": False, "branches": []},
					{"line_number": 2, "function_name": "main", "count": 1, "unexecuted_block": False, "branches": [
						{"count": 1, "throw": False, "fallthrough": True}, {"count": 0, "throw": False, "fallthrough": False}
					]},
					{"line_number": 3, "count": 0, "unexecuted_block": True, "branches": []}
				]
			}]
		}
		with TemporaryDirectory() as directory:
			report = Document(_write(directory, dumps(document)), analyzeAndConvert=True)

		line = report.DataFiles[0].Files[Path("main.c")].Lines[1]
		self.assertEqual([], line.BlockIDs)
		self.assertIsNone(report.DataFiles[0].CurrentWorkingDirectory)
		self.assertIsNone(report.DataFiles[0].Files[Path("main.c")].Lines[2].FunctionName)

		summary = report.ToCoverageSummary()
		self.assertEqual((3, 2), (summary.TotalLines, summary.CoveredLines))
		self.assertEqual([], summary.SourceDirectories)


class Schema(Testcase):
	"""The reverse-engineered JSON Schema accepts gcov's report and rejects what it doesn't write."""

	def test_FormatVersion(self) -> None:
		main = _stream()[1]
		main["format_version"] = "3"
		with TemporaryDirectory() as directory:
			jsonFile = _write(directory, dumps(main))

			with self.assertRaises(CodeCoverageError) as context:
				_ = Document(jsonFile, analyzeAndConvert=True)

		self.assertEqual(
			f"Validation error for '{jsonFile}' using JSON Schema 'Gcov-JSON.schema.json'.", str(context.exception)
		)
		self.assertEqual(["/format_version: '3' is not one of ['1', '2']"], context.exception.__notes__)

	def test_UnknownField(self) -> None:
		"""An error in the second JSON object of a file is prefixed by its index."""
		statistics, main = _stream()
		main["files"][1]["lines"][0]["hits"] = 1
		with TemporaryDirectory() as directory:
			with self.assertRaises(CodeCoverageError) as context:
				_ = Document(_write(directory, f"{dumps(statistics)}\n{dumps(main)}\n"), analyzeAndConvert=True)

		self.assertEqual(
			["[1]/files/1/lines/0: Additional properties are not allowed ('hits' was unexpected)"],
			context.exception.__notes__
		)

	def test_Syntax(self) -> None:
		with TemporaryDirectory() as directory:
			jsonFile = _write(directory, "{}\n{")

			with self.assertRaises(CodeCoverageError) as context:
				_ = Document(jsonFile, analyzeAndConvert=True)

		self.assertEqual(f"JSON syntax error in gcov report file '{jsonFile}'.", str(context.exception))

	def test_Empty(self) -> None:
		with TemporaryDirectory() as directory:
			jsonFile = _write(directory, "\n")

			with self.assertRaises(CodeCoverageError) as context:
				_ = Document(jsonFile, analyzeAndConvert=True)

		self.assertEqual(f"gcov report file '{jsonFile}' holds no JSON object.", str(context.exception))

	def test_CorruptGzip(self) -> None:
		with TemporaryDirectory() as directory:
			jsonFile = _write(directory, GZIP.read_bytes()[:100])

			with self.assertRaises(CodeCoverageError) as context:
				_ = Document(jsonFile, analyzeAndConvert=True)

		self.assertEqual(f"gzip error in gcov report file '{jsonFile}'.", str(context.exception))

	def test_Missing(self) -> None:
		with self.assertRaises(CodeCoverageError) as context:
			_ = Document(DATA / "missing.gcov.json.gz", analyzeAndConvert=True)

		self.assertEqual(f"gcov report file '{DATA / 'missing.gcov.json.gz'}' does not exist.", str(context.exception))

	def test_NotAnalyzed(self) -> None:
		with self.assertRaises(CodeCoverageError):
			Document(GZIP).Convert()
