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
"""Unit tests of lcov's tracefile format: its model, its line parser and the conversion to the common model."""
from pathlib                                  import Path
from tempfile                                 import TemporaryDirectory

from pyEDAA.Reports.CodeCoverage              import CodeCoverageError, Function, LineCoverageStatus, SourceFile
from pyEDAA.Reports.CodeCoverage.LCOV         import RECORD_SYNTAX, Document, Tracefile
from pyEDAA.Reports.CodeCoverage.LCOV.Records import Function as lcov_Function, Line, Section
from pyTooling.Testing                        import Testcase


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


DATA = Path(__file__).parent.parent.parent / "data" / "CodeCoverage"  #: Directory of the reports and their sources.
GHDL = DATA / "lcov" / "VHDL" / "GHDL.info"                           #: GHDL's tracefile of the VHDL fixture.


def _write(directory: str, content: str) -> Path:
	"""
	Write a tracefile into a directory.

	:param directory: The directory.
	:param content:   The tracefile's content.
	:returns:         The tracefile.
	"""
	tracefile = Path(directory) / "coverage.info"
	tracefile.write_text(content, encoding="utf-8")
	return tracefile


class FormatModel(Testcase):
	"""The format's model keeps what the tracefile states: sections, functions, lines, summaries."""

	def test_GHDL(self) -> None:
		"""GHDL states a file as a function 'file' at line 1, and no summaries."""
		tracefile = Document(GHDL, analyzeAndConvert=True)

		self.assertEqual(
			[Path("Testbench.vhdl"), Path("Classify.vhdl")], [section.SourceFile for section in tracefile.Sections]
		)
		section = tracefile.Sections[1]
		self.assertEqual(("", None, None), (section.TestName, section.LinesFound, section.FunctionsFound))
		self.assertEqual([("file", 1, None, 1)], [
			(function.Name, function.StartLine, function.EndLine, function.Count) for function in section.Functions
		])
		self.assertEqual({11: 1, 12: 0, 14: 1, 16: 0, 21: 1}, {
			number: line.Count for number, line in section.Lines.items()
		})

	def test_Records(self) -> None:
		"""Comments, versions, aliases, a line listed twice, and a path written on Windows."""
		with TemporaryDirectory() as directory:
			tracefile = Document(_write(directory,
				"#written by hand\nTN:\nSF:src\\a.cpp\nVER:1.2\n"
				"FNL:0,3,9\nFNA:0,2,Box<int>::Size\nFNA:0,1,Box<float>::Size\nFNL:1,11\nFNA:1,0,Box<int>::Box\n"
				"FNF:2\nFNH:1\nDA:4,2\nDA:4,3\nLF:1\nLH:1\n\nend_of_record\n"
			), analyzeAndConvert=True)

		self.assertEqual(["written by hand"], tracefile.Comments)
		section = tracefile.Sections[0]
		self.assertEqual((Path("src/a.cpp"), "1.2", 2, 1, 1, 1), (
			section.SourceFile, section.Version, section.FunctionsFound, section.FunctionsHit, section.LinesFound,
			section.LinesHit
		))
		size, box = section.Functions
		self.assertEqual(("Box<int>::Size", {"Box<int>::Size": 2, "Box<float>::Size": 1}, 3), (
			size.Name, size.Aliases, size.Count
		))
		self.assertEqual((1, 11, None, {"Box<int>::Box": 0}), (box.Index, box.StartLine, box.EndLine, box.Aliases))
		self.assertEqual((5, None), (section.Lines[4].Count, section.Lines[4].Checksum))


class Parents(Testcase):
	"""Every record below the tracefile has a parent, and is registered in its parent's collection."""

	def test_Line(self) -> None:
		section = Section("", Path("a.c"))
		line = Line(4, 2, parent=section)

		self.assertIs(section, line.Parent)
		self.assertEqual({4: line}, section.Lines)
		self.assertIsNone(Line(5, 0).Parent)

	def test_Function(self) -> None:
		section = Section("", Path("a.c"))
		first = lcov_Function(1, 3, parent=section)
		second = lcov_Function(5, None, 0, parent=section)

		self.assertEqual([section, section], [first.Parent, second.Parent])
		self.assertEqual([first, second], section.Functions)
		self.assertIsNone(lcov_Function(1, None).Parent)

	def test_Section(self) -> None:
		tracefile = Tracefile()
		first = Section("", Path("a.c"), parent=tracefile)
		second = Section("t", Path("b.c"), parent=tracefile)

		self.assertEqual([tracefile, tracefile], [first.Parent, second.Parent])
		self.assertEqual([first, second], tracefile.Sections)
		self.assertIsNone(Section("", Path("a.c")).Parent)

	def test_WrongParent(self) -> None:
		section = Section("", Path("a.c"))
		for create, expected in (
			(lambda: Line(1, 0, parent=Tracefile()), "Section"),
			(lambda: lcov_Function(1, None, parent=Tracefile()), "Section"),
			(lambda: Section("", Path("a.c"), parent=section), "Tracefile")
		):
			with self.subTest(expected=expected):
				with self.assertRaises(TypeError) as context:
					create()

				self.assertEqual(f"Parameter 'parent' is not of type '{expected}'.", str(context.exception))
				self.assertEqual(1, len(context.exception.__notes__))

	def test_Document(self) -> None:
		"""A read tracefile is the parent of its sections, a section of its functions and lines."""
		with TemporaryDirectory() as directory:
			tracefile = Document(_write(directory,
				"SF:a.c\nFN:1,3,f\nFNDA:1,f\nDA:2,1\nend_of_record\nSF:b.c\nFNL:0,1\nFNA:0,0,g\nDA:1,0\nend_of_record\n"
			), analyzeAndConvert=True)

		self.assertEqual([tracefile, tracefile], [section.Parent for section in tracefile.Sections])
		for section in tracefile.Sections:
			with self.subTest(section=section.SourceFile):
				self.assertEqual([section], [function.Parent for function in section.Functions])
				self.assertEqual([section], [line.Parent for line in section.Lines.values()])


class Conversion(Testcase):
	"""The conversion to the common model: files and lines, and source files and functions as units."""

	def test_GHDL(self) -> None:
		"""GHDL's function 'file' at line 1 spans no listed line."""
		summary = Document(GHDL, analyzeAndConvert=True).ToCoverageSummary()

		self.assertEqual((11, 9, 2), (summary.TotalLines, summary.CoveredLines, summary.FileCount))
		self.assertEqual(
			["Classify.vhdl", "Classify.vhdl.file", "Testbench.vhdl", "Testbench.vhdl.file"],
			[unit.QualifiedName for unit in summary.IterateUnits()]
		)
		classify = summary.Units["Classify.vhdl"]
		self.assertIsInstance(classify, SourceFile)
		self.assertEqual((11, 21, 5, 3), (
			classify.StartLine.LineNumber, classify.EndLine.LineNumber, classify.TotalLines, classify.CoveredLines
		))
		file = classify.Units["file"]
		self.assertIsInstance(file, Function)
		self.assertEqual(
			(None, None, LineCoverageStatus.Covered, 1), (file.StartLine, file.EndLine, file.Status, file.CoverageCount)
		)
		self.assertIs(LineCoverageStatus.Uncovered, summary.Files["Classify.vhdl"].Lines[12].Status)

	def test_Functions(self) -> None:
		"""A function spans the listed lines from its start to its end line; without end line its start line only."""
		with TemporaryDirectory() as directory:
			summary = Document(_write(directory,
				"SF:a.c\nFN:1,6,f\nFN:8,g\nFN:12,h\nFNDA:0,f\nFNDA:3,g\n"
				"DA:2,0\nDA:3,0\nDA:5,0\nDA:8,3\nDA:9,3\nDA:12,0\nend_of_record\n"
			), analyzeAndConvert=True).ToCoverageSummary()

		units = summary.Units["a.c"].Units
		self.assertEqual([
			("f", LineCoverageStatus.Uncovered, 0, 2, 5, 3),
			("g", LineCoverageStatus.Covered, 3, 8, None, 0),
			("h", LineCoverageStatus.Unknown, None, 12, None, 0)
		], [
			(name, unit.Status, unit.CoverageCount, unit.StartLine.LineNumber,
			 None if unit.EndLine is None else unit.EndLine.LineNumber, unit.TotalLines)
			for name, unit in units.items()
		])

	def test_MergedTests(self) -> None:
		"""Two tests' sections of one file are one file: the counts of lines and functions are added."""
		with TemporaryDirectory() as directory:
			summary = Document(_write(directory,
				"TN:first\nSF:src/a.c\nFN:1,3,f\nFNDA:0,f\nDA:1,0\nDA:2,0\nend_of_record\n"
				"TN:second\nSF:./src/a.c\nFN:1,3,f\nFNDA:2,f\nDA:1,2\nDA:2,0\nDA:3,1\nend_of_record\n"
			), analyzeAndConvert=True).ToCoverageSummary()

		file = summary.Directories["src"].Files["a.c"]
		self.assertEqual([(1, 2), (2, 0), (3, 1)], [(line.LineNumber, line.CoverageCount) for line in file.IterateLines()])
		function = summary.Units["src/a.c"].Units["f"]
		self.assertEqual((LineCoverageStatus.Covered, 2, 3, 2), (
			function.Status, function.CoverageCount, function.TotalLines, function.CoveredLines
		))


class Parser(Testcase):
	"""The strict line parser rejects unknown, malformed and misplaced records, and notes the line."""

	def _Read(self, content: str) -> CodeCoverageError:
		"""
		Read a tracefile, which is expected to fail.

		:param content: The tracefile's content.
		:returns:       The exception.
		"""
		with TemporaryDirectory() as directory:
			with self.assertRaises(CodeCoverageError) as context:
				_ = Document(_write(directory, content), analyzeAndConvert=True)

		return context.exception

	def test_UnknownRecord(self) -> None:
		ex = self._Read("SF:a.c\nXY:1\nend_of_record\n")

		self.assertTrue(str(ex).startswith("Unknown record 'XY' in lcov tracefile '"))
		self.assertEqual(["Line 2: 'XY:1'", f"Known records: {', '.join(RECORD_SYNTAX)}"], ex.__notes__)

	def test_MalformedRecord(self) -> None:
		"""Line number 0 is malformed."""
		ex = self._Read("SF:a.c\nDA:0,1\nend_of_record\n")

		self.assertTrue(str(ex).startswith("Malformed record 'DA' in lcov tracefile '"))
		self.assertEqual(["Line 2: 'DA:0,1'", "Expected 'DA:<line number>,<execution count>[,<checksum>]'."], ex.__notes__)

	def test_OutsideOfSection(self) -> None:
		ex = self._Read("TN:t\nDA:1,1\n")

		self.assertTrue(str(ex).startswith("Record 'DA' outside of a section in lcov tracefile '"))
		self.assertEqual(["Line 2: 'DA:1,1'", "A section starts with 'SF:<path to the source file>'."], ex.__notes__)

	def test_SectionNotEnded(self) -> None:
		ex = self._Read("SF:a.c\nDA:1,1\nSF:b.c\nend_of_record\n")

		self.assertTrue(str(ex).startswith("Record 'SF' inside the section of 'a.c' in '"))
		self.assertEqual(["Line 3: 'SF:b.c'", "End the section of line 1 with 'end_of_record'."], ex.__notes__)

	def test_TestNameInsideSection(self) -> None:
		ex = self._Read("SF:a.c\nTN:t\nend_of_record\n")

		self.assertTrue(str(ex).startswith("Record 'TN' inside the section of 'a.c' in '"))
		self.assertEqual(["Line 2: 'TN:t'"], ex.__notes__)

	def test_MissingEndOfRecord(self) -> None:
		ex = self._Read("TN:\nSF:a.c\nDA:1,1\n")

		self.assertTrue(str(ex).startswith("Missing 'end_of_record' at the end of lcov tracefile '"))
		self.assertEqual(["The section of 'a.c' starts in line 2."], ex.__notes__)

	def test_UnknownFunction(self) -> None:
		for content, record in (
			("SF:a.c\nFN:1,f\nFNDA:1,g\nend_of_record\n", "FNDA:1,g"),
			("SF:a.c\nFNL:0,1\nFNA:1,1,g\nend_of_record\n", "FNA:1,1,g")
		):
			with self.subTest(record=record):
				ex = self._Read(content)

				self.assertTrue(str(ex).startswith(f"Record '{record.split(':')[0]}' refers to an unknown function in '"))
				self.assertEqual([f"Line 3: '{record}'"], ex.__notes__)

	def test_DuplicateFunction(self) -> None:
		for content, message in (
			("SF:a.c\nFN:1,f\nFN:5,f\nend_of_record\n", "Function 'f' is stated twice in the section of 'a.c'."),
			("SF:a.c\nFNL:0,1\nFNL:0,5\nend_of_record\n", "Function index 0 is stated twice in the section of 'a.c'.")
		):
			with self.subTest(message=message):
				ex = self._Read(content)

				self.assertEqual(message, str(ex))
				self.assertEqual(1, len(ex.__notes__))

	def test_FunctionWithoutAlias(self) -> None:
		ex = self._Read("SF:a.c\nFNL:0,1\nFNL:1,5\nFNA:1,0,g\nend_of_record\n")

		self.assertEqual("Function index 0 has no alias in the section of 'a.c'.", str(ex))
		self.assertEqual(
			["The section ends in line 5.", "Name the function by 'FNA:<index>,<execution count>,<name>'."], ex.__notes__
		)

	def test_Encoding(self) -> None:
		with TemporaryDirectory() as directory:
			tracefile = Path(directory) / "coverage.info"
			tracefile.write_bytes(b"SF:\xff.c\nend_of_record\n")

			with self.assertRaises(CodeCoverageError) as context:
				_ = Document(tracefile, analyzeAndConvert=True)

		self.assertEqual(f"lcov tracefile '{tracefile}' is not UTF-8 encoded.", str(context.exception))

	def test_Missing(self) -> None:
		with self.assertRaises(CodeCoverageError) as context:
			_ = Document(DATA / "missing.info", analyzeAndConvert=True)

		self.assertEqual(f"lcov tracefile '{DATA / 'missing.info'}' does not exist.", str(context.exception))

	def test_NotAnalyzed(self) -> None:
		with self.assertRaises(CodeCoverageError):
			Document(GHDL).Convert()
