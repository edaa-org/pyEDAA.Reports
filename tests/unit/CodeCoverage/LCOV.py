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
from typing                                   import Callable

from pyEDAA.Reports.CodeCoverage              import CodeCoverageError, Function, LineCoverageStatus, SourceFile
from pyEDAA.Reports.CodeCoverage.LCOV         import RECORD_SYNTAX, Document
from pyEDAA.Reports.CodeCoverage.LCOV.Records import Branch, Condition, Function as lcov_Function, Line, Section
from pyTooling.Testing                        import Testcase


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


DATA = Path(__file__).parent.parent.parent / "data" / "CodeCoverage"  #: Directory of the reports and their sources.
GCC =  DATA / "lcov" / "C" / "GCC.info"                               #: lcov's tracefile of the C fixture, from GCC.
LLVM = DATA / "lcov" / "C" / "LLVM.info"                              #: llvm-cov's tracefile of the C fixture.
GHDL = DATA / "lcov" / "VHDL" / "GHDL.info"                           #: GHDL's tracefile of the VHDL fixture.
PY =   DATA / "Python" / "coverage.info"                              #: coverage.py's tracefile of the Python fixture.


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
	"""The format's model keeps what the tracefile states: sections, functions, lines, branches, conditions, summaries."""

	def test_GCC(self) -> None:
		"""lcov 2.3 writes functions as leader and aliases, MC/DC conditions, and checksums."""
		tracefile = Document(GCC, analyzeAndConvert=True)

		self.assertEqual([("Classify", Path("Clamp.h")), ("Classify", Path("Classify.c"))], [
			(section.TestName, section.SourceFile) for section in tracefile.Sections
		])
		section = tracefile.Sections[1]
		self.assertEqual((20, 14, 14, 9, 4, 3, 14, 9), (
			section.LinesFound, section.LinesHit, section.BranchesFound, section.BranchesHit, section.FunctionsFound,
			section.FunctionsHit, section.ConditionsFound, section.ConditionsHit
		))

		twice = section.Functions[1]
		self.assertEqual((1, "Twice", 17, 21, {"Twice": 0}, 0), (
			twice.Index, twice.Name, twice.StartLine, twice.EndLine, twice.Aliases, twice.Count
		))
		self.assertEqual((5, 3, "i6lS0TI+70N3scXJXzSuRg"), (
			section.Lines[5].Number, section.Lines[5].Count, section.Lines[5].Checksum
		))
		self.assertEqual([(18, 0, "0", None, False), (18, 0, "1", None, False)], [
			(branch.LineNumber, branch.Block, branch.Expression, branch.Taken, branch.IsException)
			for branch in section.Branches if branch.LineNumber == 18
		])
		self.assertEqual([(2, True, 1, "1"), (2, False, 0, "1")], [
			(condition.GroupSize, condition.Sense, condition.Taken, condition.Expression)
			for condition in section.Conditions if condition.LineNumber == 14 and condition.Index == 1
		])
		self.assertGreaterEqual(tracefile.AnalysisDuration.total_seconds(), 0.0)

	def test_LLVM(self) -> None:
		"""llvm-cov writes no test name, functions without end line, and a header's static function prefixed by its unit."""
		tracefile = Document(LLVM, analyzeAndConvert=True)

		clamp = tracefile.Sections[0].Functions[0]
		self.assertEqual(("", Path("Clamp.h")), (tracefile.Sections[0].TestName, tracefile.Sections[0].SourceFile))
		self.assertEqual((None, "Classify.c:Clamp", 2, None, 2), (
			clamp.Index, clamp.Name, clamp.StartLine, clamp.EndLine, clamp.Count
		))
		section = tracefile.Sections[1]
		self.assertEqual(["main", "Sign", "InRange", "Twice"], [function.Name for function in section.Functions])
		self.assertEqual([(1, "2", 2), (1, "3", 0)], [
			(branch.Block, branch.Expression, branch.Taken) for branch in section.Branches if branch.Block == 1
		])
		self.assertEqual([], section.Conditions)

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

	def test_CoveragePy(self) -> None:
		"""coverage.py writes branches as human-readable expressions, and '-' for a branch of a line, which never ran."""
		sections = Document(PY, analyzeAndConvert=True).Sections

		length = sections[1]
		self.assertEqual([("jump to line 15", None), ("jump to line 17", None)], [
			(branch.Expression, branch.Taken) for branch in length.Branches if branch.LineNumber == 14
		])
		self.assertEqual(("ToMeters", 4, 17, 1), (
			length.Functions[0].Name, length.Functions[0].StartLine, length.Functions[0].EndLine, length.Functions[0].Count
		))
		self.assertEqual((Path("myPackage/Units/__init__.py"), {}, None), (
			sections[2].SourceFile, sections[2].Lines, sections[2].LinesFound
		))

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

	def test_Branches(self) -> None:
		"""An exception branch, a branch never evaluated, and an expression with commas."""
		with TemporaryDirectory() as directory:
			section = Document(_write(directory,
				"SF:a.cpp\nBRDA:4,e0,1,5\nBRDA:4,0,2,-\nBRDA:7,1,f(a, b),0\nDA:4,5\nDA:7,1\nend_of_record\n"
			), analyzeAndConvert=True).Sections[0]

		self.assertEqual([(4, 0, "1", 5, True), (4, 0, "2", None, False), (7, 1, "f(a, b)", 0, False)], [
			(branch.LineNumber, branch.Block, branch.Expression, branch.Taken, branch.IsException)
			for branch in section.Branches
		])


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
		first = lcov_Function(1, 3, {"f": 1}, parent=section)
		second = lcov_Function(5, None, {"g": None}, 0, parent=section)

		self.assertEqual([section, section], [first.Parent, second.Parent])
		self.assertEqual([first, second], section.Functions)
		self.assertIsNone(lcov_Function(1, None, {"f": 1}).Parent)

	def test_Section(self) -> None:
		tracefile = Document(Path("coverage.info"))
		first = Section("", Path("a.c"), parent=tracefile)
		second = Section("t", Path("b.c"), parent=tracefile)

		self.assertEqual([tracefile, tracefile], [first.Parent, second.Parent])
		self.assertEqual([first, second], tracefile.Sections)
		self.assertIsNone(Section("", Path("a.c")).Parent)

	def test_Branch(self) -> None:
		section = Section("", Path("a.c"))
		first = Branch(4, 0, "0", 1, False, parent=section)
		second = Branch(4, 0, "1", None, False, parent=section)

		self.assertEqual([section, section], [first.Parent, second.Parent])
		self.assertEqual([first, second], section.Branches)
		self.assertIsNone(Branch(4, 0, "0", 0, True).Parent)

	def test_Condition(self) -> None:
		section = Section("", Path("a.c"))
		first = Condition(7, 2, True, 1, 0, "x", parent=section)
		second = Condition(7, 2, False, 0, 0, "x", parent=section)

		self.assertEqual([section, section], [first.Parent, second.Parent])
		self.assertEqual([first, second], section.Conditions)
		self.assertIsNone(Condition(7, 2, True, 0, 1, "y").Parent)

	def test_WrongParent(self) -> None:
		section = Section("", Path("a.c"))
		for create, expected in (
			(lambda: Line(1, 0, parent=Document(Path("coverage.info"))), "Section"),
			(lambda: lcov_Function(1, None, {"f": 1}, parent=Document(Path("coverage.info"))), "Section"),
			(lambda: Branch(1, 0, "0", 0, False, parent=Document(Path("coverage.info"))), "Section"),
			(lambda: Condition(1, 1, True, 0, 0, "x", parent=Document(Path("coverage.info"))), "Section"),
			(lambda: Section("", Path("a.c"), parent=section), "Tracefile")
		):
			with self.subTest(expected=expected):
				with self.assertRaises(TypeError) as context:
					create()

				self.assertEqual(f"Parameter 'parent' is not of type '{expected}'.", str(context.exception))
				self.assertEqual(1, len(context.exception.__notes__))

	def test_Document(self) -> None:
		"""A read tracefile is the parent of its sections, a section of its functions, lines, branches and conditions."""
		with TemporaryDirectory() as directory:
			tracefile = Document(_write(directory,
				"SF:a.c\nFN:1,3,f\nFNDA:1,f\nDA:2,1\nBRDA:2,0,0,1\nMCDC:2,1,t,1,0,x\nend_of_record\n"
				"SF:b.c\nFNL:0,1\nFNA:0,0,g\nDA:1,0\nBRDA:1,0,0,-\nMCDC:1,1,f,0,0,y\nend_of_record\n"
			), analyzeAndConvert=True)

		self.assertEqual([tracefile, tracefile], [section.Parent for section in tracefile.Sections])
		for section in tracefile.Sections:
			with self.subTest(section=section.SourceFile):
				self.assertEqual([section], [function.Parent for function in section.Functions])
				self.assertEqual([section], [line.Parent for line in section.Lines.values()])
				self.assertEqual([section], [branch.Parent for branch in section.Branches])
				self.assertEqual([section], [condition.Parent for condition in section.Conditions])

	def test_Line_Duplicate(self) -> None:
		"""A section has one line per number: the first stays, the second is rejected."""
		section = Section("", Path("src/a.c"))
		first = Line(3, 1, parent=section)

		with self.assertRaises(CodeCoverageError) as context:
			_ = Line(3, 7, parent=section)

		self.assertEqual("Line 3 of the section of 'src/a.c' is added twice.", str(context.exception))
		self.assertEqual({3: first}, section.Lines)
		self.assertEqual(1, section.Lines[3].Count)


class Construction(Testcase):
	"""The format's model is built by hand: each constructor takes typed values and checks them."""

	def _AssertChecks(self, cases: tuple[tuple[Callable[[], object], type[Exception], str, list[str]], ...]) -> None:
		"""
		Assert that each constructor call raises the exception of its case.

		:param cases: The cases: a constructor call, the exception's type, its message and its notes.
		"""
		for create, exceptionType, message, notes in cases:
			with self.subTest(message=message):
				with self.assertRaises(exceptionType) as context:
					_ = create()

				self.assertEqual(message, str(context.exception))
				self.assertEqual(notes, getattr(context.exception, "__notes__", []))

	def test_Line(self) -> None:
		line = Line(13, 3, "i6lS0TI+70N3scXJXzSuRg")

		self.assertEqual((13, 3, "i6lS0TI+70N3scXJXzSuRg", None), (line.Number, line.Count, line.Checksum, line.Parent))
		self.assertIsNone(Line(1, 0).Checksum)

	def test_Branch(self) -> None:
		branch = Branch(4, 0, "jump to line 8", None, True)

		self.assertEqual((4, 0, "jump to line 8", None, True, None), (
			branch.LineNumber, branch.Block, branch.Expression, branch.Taken, branch.IsException, branch.Parent
		))

	def test_Condition(self) -> None:
		condition = Condition(14, 2, False, 0, 1, "1")

		self.assertEqual((14, 2, False, 0, 1, "1", None), (
			condition.LineNumber, condition.GroupSize, condition.Sense, condition.Taken, condition.Index,
			condition.Expression, condition.Parent
		))

	def test_Function(self) -> None:
		"""The first alias names the function; the function keeps its own copy of the aliases."""
		aliases = {"Box<int>::Size": 2, "Box<float>::Size": None}
		function = lcov_Function(3, 9, aliases, 0)
		aliases["Box<char>::Size"] = 1

		self.assertEqual((3, 9, 0, "Box<int>::Size", {"Box<int>::Size": 2, "Box<float>::Size": None}, 2, None), (
			function.StartLine, function.EndLine, function.Index, function.Name, function.Aliases, function.Count,
			function.Parent
		))
		self.assertEqual((None, None, None), (
			lcov_Function(1, None, {"f": None}).EndLine, lcov_Function(1, None, {"f": None}).Index,
			lcov_Function(1, None, {"f": None}).Count
		))

	def test_Section(self) -> None:
		section = Section("", Path("a.c"))

		self.assertEqual(("", Path("a.c"), None, [], {}, [], [], None), (
			section.TestName, section.SourceFile, section.Version, section.Functions, section.Lines, section.Branches,
			section.Conditions, section.Parent
		))

	def test_Line_Checks(self) -> None:
		self._AssertChecks((
			(lambda: Line(None, 1), ValueError, "Parameter 'number' is None.", []),
			(lambda: Line("3", 1), TypeError, "Parameter 'number' is not of type 'int'.", ["Got type 'str'."]),
			(lambda: Line(0, 1), ValueError, "Parameter 'number' is less than 1.", ["Got value '0'."]),
			(lambda: Line(3, None), ValueError, "Parameter 'count' is None.", []),
			(lambda: Line(3, 1.0), TypeError, "Parameter 'count' is not of type 'int'.", ["Got type 'float'."]),
			(lambda: Line(3, -1), ValueError, "Parameter 'count' is negative.", ["Got value '-1'."]),
			(lambda: Line(3, 1, 5), TypeError, "Parameter 'checksum' is not of type 'str'.", ["Got type 'int'."]),
			(lambda: Line(3, 1, ""), ValueError, "Parameter 'checksum' is empty.", [])
		))

	def test_Branch_Checks(self) -> None:
		self._AssertChecks((
			(lambda: Branch(None, 0, "0", 1, False), ValueError, "Parameter 'lineNumber' is None.", []),
			(lambda: Branch("4", 0, "0", 1, False), TypeError, "Parameter 'lineNumber' is not of type 'int'.",
			 ["Got type 'str'."]),
			(lambda: Branch(0, 0, "0", 1, False), ValueError, "Parameter 'lineNumber' is less than 1.", ["Got value '0'."]),
			(lambda: Branch(4, None, "0", 1, False), ValueError, "Parameter 'block' is None.", []),
			(lambda: Branch(4, "e0", "0", 1, False), TypeError, "Parameter 'block' is not of type 'int'.",
			 ["Got type 'str'."]),
			(lambda: Branch(4, -1, "0", 1, False), ValueError, "Parameter 'block' is negative.", ["Got value '-1'."]),
			(lambda: Branch(4, 0, None, 1, False), ValueError, "Parameter 'expression' is None.", []),
			(lambda: Branch(4, 0, 0, 1, False), TypeError, "Parameter 'expression' is not of type 'str'.",
			 ["Got type 'int'."]),
			(lambda: Branch(4, 0, "", 1, False), ValueError, "Parameter 'expression' is empty.", []),
			(lambda: Branch(4, 0, "0", "-", False), TypeError, "Parameter 'taken' is not of type 'int'.",
			 ["Got type 'str'."]),
			(lambda: Branch(4, 0, "0", -1, False), ValueError, "Parameter 'taken' is negative.", ["Got value '-1'."]),
			(lambda: Branch(4, 0, "0", 1, None), ValueError, "Parameter 'isException' is None.", []),
			(lambda: Branch(4, 0, "0", 1, "e"), TypeError, "Parameter 'isException' is not of type 'bool'.",
			 ["Got type 'str'."])
		))

	def test_Condition_Checks(self) -> None:
		self._AssertChecks((
			(lambda: Condition(None, 2, True, 1, 0, "x"), ValueError, "Parameter 'lineNumber' is None.", []),
			(lambda: Condition("7", 2, True, 1, 0, "x"), TypeError, "Parameter 'lineNumber' is not of type 'int'.",
			 ["Got type 'str'."]),
			(lambda: Condition(0, 2, True, 1, 0, "x"), ValueError, "Parameter 'lineNumber' is less than 1.",
			 ["Got value '0'."]),
			(lambda: Condition(7, None, True, 1, 0, "x"), ValueError, "Parameter 'groupSize' is None.", []),
			(lambda: Condition(7, "2", True, 1, 0, "x"), TypeError, "Parameter 'groupSize' is not of type 'int'.",
			 ["Got type 'str'."]),
			(lambda: Condition(7, -2, True, 1, 0, "x"), ValueError, "Parameter 'groupSize' is negative.",
			 ["Got value '-2'."]),
			(lambda: Condition(7, 2, None, 1, 0, "x"), ValueError, "Parameter 'sense' is None.", []),
			(lambda: Condition(7, 2, "t", 1, 0, "x"), TypeError, "Parameter 'sense' is not of type 'bool'.",
			 ["Got type 'str'."]),
			(lambda: Condition(7, 2, True, None, 0, "x"), ValueError, "Parameter 'taken' is None.", []),
			(lambda: Condition(7, 2, True, "1", 0, "x"), TypeError, "Parameter 'taken' is not of type 'int'.",
			 ["Got type 'str'."]),
			(lambda: Condition(7, 2, True, -1, 0, "x"), ValueError, "Parameter 'taken' is negative.", ["Got value '-1'."]),
			(lambda: Condition(7, 2, True, 1, None, "x"), ValueError, "Parameter 'index' is None.", []),
			(lambda: Condition(7, 2, True, 1, "0", "x"), TypeError, "Parameter 'index' is not of type 'int'.",
			 ["Got type 'str'."]),
			(lambda: Condition(7, 2, True, 1, -1, "x"), ValueError, "Parameter 'index' is negative.", ["Got value '-1'."]),
			(lambda: Condition(7, 2, True, 1, 0, None), ValueError, "Parameter 'expression' is None.", []),
			(lambda: Condition(7, 2, True, 1, 0, 0), TypeError, "Parameter 'expression' is not of type 'str'.",
			 ["Got type 'int'."]),
			(lambda: Condition(7, 2, True, 1, 0, ""), ValueError, "Parameter 'expression' is empty.", [])
		))

	def test_Function_Checks(self) -> None:
		self._AssertChecks((
			(lambda: lcov_Function(None, 3, {"f": 1}), ValueError, "Parameter 'startLine' is None.", []),
			(lambda: lcov_Function("1", 3, {"f": 1}), TypeError, "Parameter 'startLine' is not of type 'int'.",
			 ["Got type 'str'."]),
			(lambda: lcov_Function(0, 3, {"f": 1}), ValueError, "Parameter 'startLine' is less than 1.", ["Got value '0'."]),
			(lambda: lcov_Function(1, "3", {"f": 1}), TypeError, "Parameter 'endLine' is not of type 'int'.",
			 ["Got type 'str'."]),
			(lambda: lcov_Function(1, 0, {"f": 1}), ValueError, "Parameter 'endLine' is less than 1.", ["Got value '0'."]),
			(lambda: lcov_Function(1, 3, {"f": 1}, "0"), TypeError, "Parameter 'index' is not of type 'int'.",
			 ["Got type 'str'."]),
			(lambda: lcov_Function(1, 3, {"f": 1}, -1), ValueError, "Parameter 'index' is negative.", ["Got value '-1'."])
		))

	def test_Function_Aliases(self) -> None:
		"""A function has a name: the aliases are required and not empty."""
		self._AssertChecks((
			(lambda: lcov_Function(1, 3, None), ValueError, "Parameter 'aliases' is None.", []),
			(lambda: lcov_Function(1, 3, ["f"]), TypeError, "Parameter 'aliases' is not a mapping.", ["Got type 'list'."]),
			(lambda: lcov_Function(1, 3, {}), ValueError, "Parameter 'aliases' is empty.", []),
			(lambda: lcov_Function(1, 3, {1: 1}), TypeError, "Parameter 'aliases' contains a name not of type 'str'.",
			 ["Got type 'int'."]),
			(lambda: lcov_Function(1, 3, {"": 1}), ValueError, "Parameter 'aliases' contains an empty name.", []),
			(lambda: lcov_Function(1, 3, {"f": "1"}), TypeError, "Parameter 'aliases' contains a count not of type 'int'.",
			 ["Got type 'str'."]),
			(lambda: lcov_Function(1, 3, {"f": -1}), ValueError, "Parameter 'aliases' contains a negative count.",
			 ["Got value '-1'."])
		))

	def test_Section_Checks(self) -> None:
		self._AssertChecks((
			(lambda: Section(None, Path("a.c")), ValueError, "Parameter 'testName' is None.", []),
			(lambda: Section(1, Path("a.c")), TypeError, "Parameter 'testName' is not of type 'str'.", ["Got type 'int'."]),
			(lambda: Section("", None), ValueError, "Parameter 'sourceFile' is None.", []),
			(lambda: Section("", "a.c"), TypeError, "Parameter 'sourceFile' is not of type 'Path'.", ["Got type 'str'."])
		))


class Conversion(Testcase):
	"""The conversion to the common model: files, lines and branches, and source files and functions as units."""

	def test_HandBuilt(self) -> None:
		"""A model built by hand converts like a read one: a function is named by its first alias."""
		tracefile = Document(Path("coverage.info"))
		section = Section("", Path("a.c"), parent=tracefile)
		lcov_Function(1, 3, {"f": 2, "g": 1}, parent=section)
		Line(2, 3, parent=section)

		summary = tracefile.ToCoverageSummary()

		function = summary.Units["a.c"].Units["f"]
		self.assertEqual((LineCoverageStatus.Covered, 3), (function.Status, function.CoverageCount))
		self.assertEqual((1, 1), (summary.TotalLines, summary.CoveredLines))

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

	def test_Summaries(self) -> None:
		"""The computed counters agree with the summaries each section states."""
		for path in (GCC, LLVM, PY):
			tracefile = Document(path, analyzeAndConvert=True)
			summary = tracefile.ToCoverageSummary()
			for section in tracefile.Sections:
				with self.subTest(tracefile=path.name, section=section.SourceFile.as_posix()):
					file = summary.GetOrAddFile(section.SourceFile)
					functions = [unit for unit in file.Units if isinstance(unit, Function)]
					self.assertEqual(
						(section.LinesFound or 0, section.LinesHit or 0, section.BranchesFound or 0,
						 section.BranchesHit or 0, section.FunctionsFound or 0, section.FunctionsHit or 0),
						(file.TotalLines, file.CoveredLines, file.TotalBranches, file.CoveredBranches, len(functions),
						 sum(1 for function in functions if function.Status is LineCoverageStatus.Covered))
					)

	def test_Lines(self) -> None:
		classify = Document(GCC, analyzeAndConvert=True).ToCoverageSummary().Files["Classify.c"]

		line = classify.Lines[6]
		self.assertEqual((LineCoverageStatus.PartiallyCovered, 3), (line.Status, line.CoverageCount))
		self.assertEqual([(LineCoverageStatus.Uncovered, 0), (LineCoverageStatus.Covered, 3)], [
			(branch.Status, branch.CoverageCount) for branch in line.Branches
		])
		self.assertEqual([None, None], [branch.Target for branch in line.Branches])

		line = classify.Lines[18]
		self.assertEqual((LineCoverageStatus.Uncovered, 0), (line.Status, line.CoverageCount))
		self.assertEqual([(LineCoverageStatus.Uncovered, None)] * 2, [
			(branch.Status, branch.CoverageCount) for branch in line.Branches
		])
		self.assertIs(LineCoverageStatus.Covered, classify.Lines[5].Status)
		self.assertIsNone(classify.Lines[4])

	def test_Units(self) -> None:
		summary = Document(GCC, analyzeAndConvert=True).ToCoverageSummary()

		self.assertEqual(
			["Clamp.h", "Clamp.h.Clamp", "Classify.c", "Classify.c.InRange", "Classify.c.Sign", "Classify.c.Twice",
			 "Classify.c.main"],
			[unit.QualifiedName for unit in summary.IterateUnits()]
		)
		classify = summary.Units["Classify.c"]
		self.assertIsInstance(classify, SourceFile)
		self.assertEqual((5, 32, 20, 14), (
			classify.StartLine.LineNumber, classify.EndLine.LineNumber, classify.TotalLines, classify.CoveredLines
		))

		twice = classify.Units["Twice"]
		self.assertIsInstance(twice, Function)
		self.assertEqual((LineCoverageStatus.Uncovered, 0, 17, 20, 4, 0), (
			twice.Status, twice.CoverageCount, twice.StartLine.LineNumber, twice.EndLine.LineNumber, twice.TotalLines,
			twice.CoveredLines
		))

	def test_Units_WithoutEndLine(self) -> None:
		"""llvm-cov's functions have no end line: they name their start line only."""
		sign = Document(LLVM, analyzeAndConvert=True).ToCoverageSummary().Units["Classify.c"].Units["Sign"]

		self.assertEqual((5, None, 0, 3), (sign.StartLine.LineNumber, sign.EndLine, sign.TotalLines, sign.CoverageCount))

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

	def test_MergedTests_Branches(self) -> None:
		"""Two tests' counts of a branch are added; a branch never evaluated in one test takes the other's count."""
		with TemporaryDirectory() as directory:
			summary = Document(_write(directory,
				"TN:first\nSF:a.c\nBRDA:2,0,0,-\nBRDA:2,0,1,-\nDA:2,0\nend_of_record\n"
				"TN:second\nSF:a.c\nBRDA:2,0,0,2\nBRDA:2,0,1,-\nDA:2,2\nend_of_record\n"
			), analyzeAndConvert=True).ToCoverageSummary()

		line = summary.Files["a.c"].Lines[2]
		self.assertEqual((LineCoverageStatus.PartiallyCovered, 2), (line.Status, line.CoverageCount))
		self.assertEqual([(LineCoverageStatus.Covered, 2), (LineCoverageStatus.Uncovered, None)], [
			(branch.Status, branch.CoverageCount) for branch in line.Branches
		])

	def test_BranchWithoutLine(self) -> None:
		"""A line with branches, but without 'DA' record, has an unknown state."""
		with TemporaryDirectory() as directory:
			tracefile = Document(_write(directory, "SF:a.c\nBRDA:3,0,0,1\nBRDA:3,0,1,0\nend_of_record\n"))
			tracefile.Analyze()
			tracefile.Convert()

		line = tracefile.ToCoverageSummary().Files["a.c"].Lines[3]
		self.assertEqual((LineCoverageStatus.Unknown, None, 2), (line.Status, line.CoverageCount, len(line.Branches)))


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

	def test_Unreadable(self) -> None:
		"""A directory can't be read as a file."""
		with self.assertRaises(CodeCoverageError) as context:
			_ = Document(DATA, analyzeAndConvert=True)

		self.assertEqual(f"Couldn't read lcov tracefile '{DATA}'.", str(context.exception))
		self.assertIsInstance(context.exception.__cause__, OSError)

	def test_NotAnalyzed(self) -> None:
		with self.assertRaises(CodeCoverageError):
			Document(GHDL).Convert()
