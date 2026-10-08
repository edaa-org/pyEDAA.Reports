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
from json                                     import dumps, loads
from pathlib                                  import Path
from tempfile                                 import TemporaryDirectory
from typing                                   import Any

from pyEDAA.Reports.CodeCoverage              import CodeCoverageError, Function, LineCoverageStatus, SourceFile
from pyEDAA.Reports.CodeCoverage.Gcov         import DataFile, Document, File, FormatVersion, SCHEMAS
from pyEDAA.Reports.CodeCoverage.Gcov.Records import Function as gcov_Function, Line
from pyTooling.Testing                        import Testcase
from pyTooling.Versioning                     import SemanticVersion


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
	"""The format's model keeps what the report states: data files, files, functions, lines and their records."""

	def test_DataFiles(self) -> None:
		report = Document(STREAM, analyzeAndConvert=True)

		self.assertEqual(["Statistics.c", "Main.cpp"], [dataFile.Path.as_posix() for dataFile in report.DataFiles])
		main = report.DataFiles[1]
		self.assertEqual((FormatVersion.Version2, "14.2.0"), (main.FormatVersion, main.GCCVersion))
		self.assertIsInstance(main.GCCVersion, SemanticVersion)
		self.assertEqual(_stream()[1]["current_working_directory"], main.CurrentWorkingDirectory.as_posix())
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
		self.assertEqual([(1, False, True, 4, 5), (0, True, False, 4, 8)], [
			(branch.Count, branch.Throw, branch.Fallthrough, branch.SourceBlockID, branch.DestinationBlockID)
			for branch in line.Branches
		])
		self.assertEqual([(3, 1, 1), (4, 1, 1), (5, 1, 0), (8, 1, 0)], [
			(call.SourceBlockID, call.DestinationBlockID, call.Returned) for call in line.Calls
		])

	def test_Conditions(self) -> None:
		statistics = Document(STREAM, analyzeAndConvert=True).DataFiles[0].Files[Path("Statistics.c")]

		condition, = next(line for line in statistics.Lines if line.LineNumber == 20).Conditions
		self.assertEqual((4, 2, [], [0, 1]),
		                 (condition.Count, condition.Covered, condition.NotCoveredTrue, condition.NotCoveredFalse))

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

	def test_GCCVersion_Development(self) -> None:
		"""A development build of GCC states its date and phase behind the version."""
		main = _stream()[1]
		main["gcc_version"] = "15.0.1 20250418 (experimental)"
		with TemporaryDirectory() as directory:
			dataFile, = Document(_write(directory, dumps(main)), analyzeAndConvert=True).DataFiles

		self.assertEqual("15.0.1", dataFile.GCCVersion)

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


class Construction(Testcase):
	"""The format's model is built by hand: each constructor takes typed values and checks them."""

	def test_Line(self) -> None:
		line = Line(21, 1, False, "_ZN10Containers5Stack3PopEv", (3, 4, 5, 8))

		self.assertEqual((21, 1, False, "_ZN10Containers5Stack3PopEv", [3, 4, 5, 8]),
		                 (line.LineNumber, line.Count, line.UnexecutedBlock, line.FunctionName, line.BlockIDs))

	def test_Line_Defaults(self) -> None:
		line = Line(3, 0, True)

		self.assertEqual((None, [], [], [], []),
		                 (line.FunctionName, line.BlockIDs, line.Branches, line.Calls, line.Conditions))

	def test_Function(self) -> None:
		pop = gcov_Function("_ZN10Containers5Stack3PopEv", "Containers::Stack::Pop()", 19, 8, 23, 4, 8, 7, 3)

		self.assertEqual(("_ZN10Containers5Stack3PopEv", "Containers::Stack::Pop()"), (pop.Name, pop.DemangledName))
		self.assertEqual((19, 8, 23, 4), (pop.StartLine, pop.StartColumn, pop.EndLine, pop.EndColumn))
		self.assertEqual((8, 7, 3), (pop.Blocks, pop.BlocksExecuted, pop.ExecutionCount))

	def test_File(self) -> None:
		file = File(Path("main.c"))

		self.assertEqual((Path("main.c"), None, {}, []), (file.Path, file.Parent, file.Functions, file.Lines))

	def test_DataFile(self) -> None:
		dataFile = DataFile(Path("main.c"), FormatVersion.Version2, SemanticVersion.Parse("14.2.0"), Path("/build"))

		self.assertEqual((Path("main.c"), FormatVersion.Version2, "14.2.0", Path("/build")),
		                 (dataFile.Path, dataFile.FormatVersion, dataFile.GCCVersion, dataFile.CurrentWorkingDirectory))

	def test_DataFile_Defaults(self) -> None:
		dataFile = DataFile(Path("main.c"), FormatVersion.Version1, SemanticVersion.Parse("13.2.0"))

		self.assertEqual((None, None, {}), (dataFile.CurrentWorkingDirectory, dataFile.Parent, dataFile.Files))

	def test_Line_LineNumber(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = Line(None, 0, False)
		self.assertEqual("Parameter 'lineNumber' is None.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = Line("1", 0, False)
		self.assertEqual("Parameter 'lineNumber' is not of type 'int'.", str(context.exception))
		self.assertEqual(["Got type 'str'."], context.exception.__notes__)

		with self.assertRaises(ValueError) as context:
			_ = Line(0, 0, False)
		self.assertEqual("Parameter 'lineNumber' is less than 1.", str(context.exception))
		self.assertEqual(["Got value '0'."], context.exception.__notes__)

	def test_Line_BlockIDs(self) -> None:
		with self.assertRaises(TypeError) as context:
			_ = Line(1, 0, False, blockIDs=[3, "4"])
		self.assertEqual("Parameter 'blockIDs' contains an element not of type 'int'.", str(context.exception))

	def test_Function_Name(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = gcov_Function("", "main", 1, 5, 3, 1, 4, 4, 1)
		self.assertEqual("Parameter 'name' is empty.", str(context.exception))

	def test_Function_ExecutionCount(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = gcov_Function("main", "main", 1, 5, 3, 1, 4, 4, -1)
		self.assertEqual("Parameter 'executionCount' is negative.", str(context.exception))
		self.assertEqual(["Got value '-1'."], context.exception.__notes__)

	def test_File_Path(self) -> None:
		with self.assertRaises(TypeError) as context:
			_ = File("main.c")
		self.assertEqual("Parameter 'path' is not of type 'Path'.", str(context.exception))
		self.assertEqual(["Got type 'str'."], context.exception.__notes__)

	def test_DataFile_FormatVersion(self) -> None:
		"""The format version is a member of FormatVersion, not its number."""
		with self.assertRaises(ValueError) as context:
			_ = DataFile(Path("main.c"), None, SemanticVersion.Parse("14.2.0"))
		self.assertEqual("Parameter 'formatVersion' is None.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = DataFile(Path("main.c"), 2, SemanticVersion.Parse("14.2.0"))
		self.assertEqual("Parameter 'formatVersion' is not of type 'FormatVersion'.", str(context.exception))
		self.assertEqual(["Got type 'int'."], context.exception.__notes__)

	def test_DataFile_GCCVersion(self) -> None:
		with self.assertRaises(TypeError) as context:
			_ = DataFile(Path("main.c"), FormatVersion.Version2, "14.2.0")
		self.assertEqual("Parameter 'gccVersion' is not of type 'SemanticVersion'.", str(context.exception))
		self.assertEqual(["Got type 'str'."], context.exception.__notes__)


class ParentRelation(Testcase):
	"""Each record below the report names its parent and is added to it."""

	def test_DataFile(self) -> None:
		document = Document(Path("coverage.json"))
		dataFile = DataFile(Path("main.c"), FormatVersion.Version2, SemanticVersion.Parse("14.2.0"), parent=document)

		self.assertIs(document, dataFile.Parent)
		self.assertEqual([dataFile], document.DataFiles)

	def test_File(self) -> None:
		dataFile = DataFile(Path("main.c"), FormatVersion.Version2, SemanticVersion.Parse("14.2.0"))
		file = File(Path("main.c"), parent=dataFile)

		self.assertIs(dataFile, file.Parent)
		self.assertEqual({Path("main.c"): file}, dataFile.Files)

	def test_Function(self) -> None:
		file = File(Path("main.c"))
		main = gcov_Function("main", "main", 1, 5, 3, 1, 4, 4, 1, parent=file)

		self.assertIs(file, main.Parent)
		self.assertEqual({"main": main}, file.Functions)

	def test_Line(self) -> None:
		"""A line several functions share is added once per function."""
		file = File(Path("main.c"))
		lines = [Line(1, 1, False, "main", parent=file), Line(1, 1, False, "other", parent=file)]

		self.assertEqual([file, file], [line.Parent for line in lines])
		self.assertEqual(lines, file.Lines)

	def test_Defaults(self) -> None:
		self.assertIsNone(gcov_Function("main", "main", 1, 5, 3, 1, 4, 4, 1).Parent)
		self.assertIsNone(Line(1, 1, False).Parent)

	def test_Document(self) -> None:
		"""Reading a report builds each relation."""
		report = Document(STREAM, analyzeAndConvert=True)

		for dataFile in report.DataFiles:
			self.assertIs(report, dataFile.Parent)
			for file in dataFile.Files.values():
				self.assertIs(dataFile, file.Parent)
				self.assertTrue(all(function.Parent is file for function in file.Functions.values()))
				self.assertTrue(all(line.Parent is file for line in file.Lines))

	def test_DataFile_Parent(self) -> None:
		with self.assertRaises(TypeError) as context:
			_ = DataFile(Path("main.c"), FormatVersion.Version2, SemanticVersion.Parse("14.2.0"), parent=[])
		self.assertEqual("Parameter 'parent' is not of type 'Coverage'.", str(context.exception))
		self.assertEqual(["Got type 'list'."], context.exception.__notes__)

	def test_File_Parent(self) -> None:
		with self.assertRaises(TypeError) as context:
			_ = File(Path("main.c"), parent=Document(Path("coverage.json")))
		self.assertEqual("Parameter 'parent' is not of type 'DataFile'.", str(context.exception))
		self.assertEqual(["Got type 'pyEDAA.Reports.CodeCoverage.Gcov.Document'."], context.exception.__notes__)

	def test_Function_Parent(self) -> None:
		dataFile = DataFile(Path("main.c"), FormatVersion.Version2, SemanticVersion.Parse("14.2.0"))
		with self.assertRaises(TypeError) as context:
			_ = gcov_Function("main", "main", 1, 5, 3, 1, 4, 4, 1, parent=dataFile)
		self.assertEqual("Parameter 'parent' is not of type 'File'.", str(context.exception))
		self.assertEqual(["Got type 'pyEDAA.Reports.CodeCoverage.Gcov.DataFile'."], context.exception.__notes__)

	def test_Line_Parent(self) -> None:
		with self.assertRaises(TypeError) as context:
			_ = Line(1, 1, False, parent="main.c")
		self.assertEqual("Parameter 'parent' is not of type 'File'.", str(context.exception))
		self.assertEqual(["Got type 'str'."], context.exception.__notes__)

	def test_File_Duplicate(self) -> None:
		"""A data file naming a source file twice is rejected before the second file is created."""
		main = _stream()[1]
		main["files"].append(main["files"][1])

		with self.assertRaises(CodeCoverageError) as context:
			_ = DataFile.Parse(main)
		self.assertEqual(
			"gcov data file 'Main.cpp' names source file 'Containers/Stack.hpp' twice.", str(context.exception)
		)

	def test_Function_Duplicate(self) -> None:
		record = _stream()[1]["files"][0]
		record["functions"].append(record["functions"][0])

		with self.assertRaises(CodeCoverageError) as context:
			_ = File.Parse(record)
		self.assertEqual(
			f"gcov source file 'Main.cpp' names function '{record['functions'][0]['name']}' twice.", str(context.exception)
		)


class Parsing(Testcase):
	"""Each class of the format's model parses its JSON object."""

	def test_FormatVersion(self) -> None:
		"""gcov states the format version as a string."""
		self.assertIs(FormatVersion.Version1, FormatVersion.Parse("1"))
		self.assertIs(FormatVersion.Version2, FormatVersion.Parse("2"))

	def test_FormatVersion_Unsupported(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = FormatVersion.Parse("3")
		self.assertEqual("Parameter 'value' is not a supported gcov JSON format version.", str(context.exception))
		self.assertEqual(["Got value '3'.", "Supported format versions: 1, 2."], context.exception.__notes__)

	def test_FormatVersion_Type(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = FormatVersion.Parse(None)
		self.assertEqual("Parameter 'value' is None.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = FormatVersion.Parse(2)
		self.assertEqual("Parameter 'value' is not of type 'str'.", str(context.exception))
		self.assertEqual(["Got type 'int'."], context.exception.__notes__)

	def test_Line(self) -> None:
		line = Line.Parse({
			"line_number": 21, "function_name": "_ZN10Containers5Stack3PopEv", "count": 1, "unexecuted_block": False,
			"block_ids": [3, 4, 5, 8], "branches": []
		})

		self.assertEqual((21, 1, False, "_ZN10Containers5Stack3PopEv", [3, 4, 5, 8]),
		                 (line.LineNumber, line.Count, line.UnexecutedBlock, line.FunctionName, line.BlockIDs))

	def test_Line_Format1(self) -> None:
		"""A line of format 1 has no basic blocks, calls and conditions; a line of inlined statements has no function."""
		line = Line.Parse({
			"line_number": 3, "count": 0, "unexecuted_block": True, "branches": [
				{"count": 0, "throw": False, "fallthrough": True}
			]
		})

		self.assertEqual((None, [], [], []), (line.FunctionName, line.BlockIDs, line.Calls, line.Conditions))
		self.assertEqual([(0, None, None)], [
			(branch.Count, branch.SourceBlockID, branch.DestinationBlockID) for branch in line.Branches
		])

	def test_Function(self) -> None:
		pop = gcov_Function.Parse({
			"name": "_ZN10Containers5Stack3PopEv", "demangled_name": "Containers::Stack::Pop()", "start_line": 19,
			"start_column": 8, "end_line": 23, "end_column": 4, "blocks": 8, "blocks_executed": 7, "execution_count": 3
		})

		self.assertEqual(("_ZN10Containers5Stack3PopEv", "Containers::Stack::Pop()"), (pop.Name, pop.DemangledName))
		self.assertEqual((19, 8, 23, 4, 8, 7, 3), (
			pop.StartLine, pop.StartColumn, pop.EndLine, pop.EndColumn, pop.Blocks, pop.BlocksExecuted, pop.ExecutionCount
		))

	def test_File(self) -> None:
		"""The backslashes of a path written on Windows separate directories."""
		file = File.Parse(_stream()[1]["files"][1] | {"file": "Containers\\Stack.hpp"})

		self.assertEqual(Path("Containers/Stack.hpp"), file.Path)
		self.assertEqual("Containers::Stack::Pop()", file.Functions["_ZN10Containers5Stack3PopEv"].DemangledName)
		self.assertEqual([19, 20, 21, 22], [line.LineNumber for line in file.Lines if line.LineNumber in range(19, 24)])

	def test_DataFile(self) -> None:
		"""The format version is a string; a development build of GCC states its date and phase behind the version."""
		dataFile = DataFile.Parse(_stream()[1] | {"gcc_version": "15.0.1 20250418 (experimental)"})

		self.assertEqual((Path("Main.cpp"), FormatVersion.Version2, "15.0.1"),
		                 (dataFile.Path, dataFile.FormatVersion, dataFile.GCCVersion))
		self.assertIsInstance(dataFile.GCCVersion, SemanticVersion)
		self.assertEqual([Path("Main.cpp"), Path("Containers/Stack.hpp")], list(dataFile.Files))


class Conversion(Testcase):
	"""The conversion to the common model: files, lines with branches, source files and functions."""

	def test_Counts(self) -> None:
		"""The computed counters agree with gcov's own summary, except for the lines of a template."""
		summary = Document(STREAM, analyzeAndConvert=True).ToCoverageSummary()

		self.assertEqual(["Main.cpp", "Statistics.c", "Containers/Stack.hpp"], [
			file.Path.as_posix() for file in summary.IterateFiles()
		])
		# gcov: 'Lines executed:100.00% of 20' - it counts the 2 lines of the template once per instantiation
		for path, counters in (
			("Statistics.c",         (21, 17, 10, 6)),
			("Containers/Stack.hpp", (11, 10,  8, 4)),
			("Main.cpp",             (16, 16, 32, 17))
		):
			with self.subTest(path=path):
				file = summary.GetOrAddFile(path)
				self.assertEqual(counters, (file.TotalLines, file.CoveredLines, file.TotalBranches, file.CoveredBranches))

		self.assertEqual((48, 43, 0), (summary.TotalLines, summary.CoveredLines, summary.ExcludedLines))

	def test_Lines(self) -> None:
		summary = Document(STREAM, analyzeAndConvert=True).ToCoverageSummary()
		statistics = summary.Files["Statistics.c"]

		line = statistics.Lines[5]
		self.assertEqual((LineCoverageStatus.PartiallyCovered, 1), (line.Status, line.CoverageCount))
		self.assertEqual([(LineCoverageStatus.Uncovered, 0, None), (LineCoverageStatus.Covered, 1, None)], [
			(branch.Status, branch.CoverageCount, branch.Target) for branch in line.Branches
		])
		self.assertEqual((LineCoverageStatus.Uncovered, 0), (statistics.Lines[6].Status, statistics.Lines[6].CoverageCount))
		self.assertIsNone(statistics.Lines[10])

		# the exceptional branch of the 'throw' line was never taken
		throwLine = summary.Directories["Containers"].Files["Stack.hpp"].Lines[21]
		self.assertEqual((LineCoverageStatus.PartiallyCovered, 1, 2),
		                 (throwLine.Status, throwLine.CoverageCount, len(throwLine.Branches)))

	def test_Template(self) -> None:
		"""A line of a template becomes one line: its counts added, the branches of every instantiation kept."""
		line = Document(STREAM, analyzeAndConvert=True).ToCoverageSummary().Files["Main.cpp"].Lines[9]

		self.assertEqual((LineCoverageStatus.PartiallyCovered, 2), (line.Status, line.CoverageCount))
		self.assertEqual([1, 0, 0, 1], [branch.CoverageCount for branch in line.Branches])

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
		self.assertEqual((4, 4, 4, 3), (pop.TotalLines, pop.CoveredLines, pop.TotalBranches, pop.CoveredBranches))

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
		self.assertEqual((2, 6, [2, 0]), (
			stack.Lines[21].CoverageCount, stack.Lines[20].CoverageCount,
			[branch.CoverageCount for branch in stack.Lines[21].Branches]
		))
		self.assertEqual((11, 8), (stack.TotalLines, stack.TotalBranches))
		self.assertEqual(6, summary.Units["Containers/Stack.hpp"].Units["Containers::Stack::Pop()"].CoverageCount)

	def test_Format1(self) -> None:
		"""Format 1 has no basic blocks, calls and conditions."""
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

		self.assertIs(FormatVersion.Version1, report.DataFiles[0].FormatVersion)
		line = report.DataFiles[0].Files[Path("main.c")].Lines[1]
		self.assertEqual(([], [], [], None), (line.BlockIDs, line.Calls, line.Conditions, line.Branches[0].SourceBlockID))
		self.assertIsNone(report.DataFiles[0].CurrentWorkingDirectory)
		self.assertIsNone(report.DataFiles[0].Files[Path("main.c")].Lines[2].FunctionName)

		summary = report.ToCoverageSummary()
		self.assertEqual((3, 2, 2, 1, 1), (
			summary.TotalLines, summary.CoveredLines, summary.TotalBranches, summary.CoveredBranches, summary.PartialLines
		))
		self.assertEqual([], summary.SourceDirectories)


class Schema(Testcase):
	"""Each JSON object is validated against the JSON Schema of its format version: it rejects what gcov doesn't write."""

	def test_Schemas(self) -> None:
		self.assertEqual({FormatVersion.Version1: "Gcov-1.schema.json", FormatVersion.Version2: "Gcov-2.schema.json"},
		                 SCHEMAS)

	def test_FormatVersion(self) -> None:
		main = _stream()[1]
		main["format_version"] = "3"
		with TemporaryDirectory() as directory:
			jsonFile = _write(directory, dumps(main))

			with self.assertRaises(CodeCoverageError) as context:
				_ = Document(jsonFile, analyzeAndConvert=True)

		self.assertEqual(f"gcov report file '{jsonFile}' states an unsupported format version.", str(context.exception))
		self.assertEqual(
			["Got value '3' at '/format_version'.", "Supported format versions: 1, 2."], context.exception.__notes__
		)

	def test_FormatVersion_Missing(self) -> None:
		"""The format version is read before validating; the second object states none."""
		statistics, main = _stream()
		del main["format_version"]
		with TemporaryDirectory() as directory:
			with self.assertRaises(CodeCoverageError) as context:
				_ = Document(_write(directory, f"{dumps(statistics)}\n{dumps(main)}\n"), analyzeAndConvert=True)

		self.assertEqual(
			["Got no value at '[1]/format_version'.", "Supported format versions: 1, 2."], context.exception.__notes__
		)

	def test_Format1_Strict(self) -> None:
		"""Format 1 has no basic blocks: the schema of format 1 rejects them."""
		main = _stream()[1]
		main["format_version"] = "1"
		with TemporaryDirectory() as directory:
			jsonFile = _write(directory, dumps(main))

			with self.assertRaises(CodeCoverageError) as context:
				_ = Document(jsonFile, analyzeAndConvert=True)

		self.assertEqual(
			f"Validation error for '{jsonFile}' using JSON Schema 'Gcov-1.schema.json'.", str(context.exception)
		)
		self.assertIn(
			"/files/1/lines/0: Additional properties are not allowed ('block_ids', 'calls', 'conditions' were unexpected)",
			context.exception.__notes__
		)

	def test_Format2_Strict(self) -> None:
		"""gcov of GCC 14 and later writes a line's basic blocks, calls and conditions, if empty."""
		main = _stream()[1]
		del main["files"][1]["lines"][0]["block_ids"]
		with TemporaryDirectory() as directory:
			jsonFile = _write(directory, dumps(main))

			with self.assertRaises(CodeCoverageError) as context:
				_ = Document(jsonFile, analyzeAndConvert=True)

		self.assertEqual(
			f"Validation error for '{jsonFile}' using JSON Schema 'Gcov-2.schema.json'.", str(context.exception)
		)
		self.assertEqual(["/files/1/lines/0: 'block_ids' is a required property"], context.exception.__notes__)

	def test_Formats(self) -> None:
		"""A file may hold objects of both format versions, each validated against its schema."""
		document = {
			"format_version": "1", "gcc_version": "13.2.0", "data_file": "empty.c", "files": [
				{"file": "empty.c", "functions": [], "lines": []}
			]
		}
		with TemporaryDirectory() as directory:
			report = Document(_write(directory, f"{dumps(document)}\n{dumps(_stream()[1])}\n"), analyzeAndConvert=True)

		self.assertEqual([FormatVersion.Version1, FormatVersion.Version2], [
			dataFile.FormatVersion for dataFile in report.DataFiles
		])

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
