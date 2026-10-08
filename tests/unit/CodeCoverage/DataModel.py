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
"""Unit tests of the code coverage data model: lines, branches, files, directories, units and their counters."""
from pathlib                     import Path

from pyEDAA.Reports.CodeCoverage import Branch, Class, CodeCoverageError, CoverageSummary, Directory, File, Function
from pyEDAA.Reports.CodeCoverage import Line, LineCoverageStatus, Method, Module, Package, SourceFile
from pyTooling.Testing           import Testcase


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


Covered =          LineCoverageStatus.Covered           #: Shortcut of a coverage state.
PartiallyCovered = LineCoverageStatus.PartiallyCovered  #: Shortcut of a coverage state.
Uncovered =        LineCoverageStatus.Uncovered         #: Shortcut of a coverage state.
Excluded =         LineCoverageStatus.Excluded          #: Shortcut of a coverage state.


class Lines(Testcase):
	"""A line and a branch carry a coverage state and, if the report says, a count."""

	def test_Properties(self) -> None:
		target = Line(13, Covered, 7)
		line = Line(12, PartiallyCovered, 7, (Branch(Covered, 7, target), Branch(Uncovered, 0)))
		self.assertEqual(0, line.CoveredBranches)

		line.Aggregate()

		self.assertEqual(12, line.LineNumber)
		self.assertIs(PartiallyCovered, line.Status)
		self.assertEqual(7, line.CoverageCount)
		self.assertEqual(2, len(line.Branches))
		self.assertEqual(1, line.CoveredBranches)
		self.assertIs(target, line.Branches[0].Target)
		self.assertIsNone(line.Branches[1].Target)
		self.assertEqual("<Line 12: PartiallyCovered (1/2 branches)>", repr(line))

	def test_WithoutCount(self) -> None:
		"""coverage.py states whether a line ran, but not how often."""
		line = Line(1, Covered)

		self.assertIsNone(line.CoverageCount)
		self.assertEqual([], line.Branches)

	def test_NumberType(self) -> None:
		with self.assertRaises(TypeError) as context:
			_ = Line("1", Covered)

		self.assertEqual("Parameter 'lineNumber' is not of type 'int'.", str(context.exception))
		self.assertEqual(["Got type 'str'."], context.exception.__notes__)

	def test_NumberRange(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = Line(0, Covered)

		self.assertEqual("Parameter 'lineNumber' is less than 1.", str(context.exception))
		self.assertEqual(["Got value '0'."], context.exception.__notes__)

	def test_StatusType(self) -> None:
		with self.assertRaises(TypeError) as context:
			_ = Line(1, 1)

		self.assertEqual("Parameter 'status' is not of type 'LineCoverageStatus'.", str(context.exception))
		self.assertEqual(["Got type 'int'."], context.exception.__notes__)

	def test_CountContradiction(self) -> None:
		for status, coverageCount in ((Covered, 0), (PartiallyCovered, 0), (Uncovered, 3)):
			with self.subTest(status=status.name):
				with self.assertRaises(ValueError) as context:
					_ = Line(1, status, coverageCount)

				self.assertEqual("Parameter 'coverageCount' contradicts parameter 'status'.", str(context.exception))
				self.assertEqual([f"Got count '{coverageCount}' for status '{status.name}'."], context.exception.__notes__)

	def test_NegativeCount(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = Branch(Uncovered, -1)

		self.assertEqual("Parameter 'coverageCount' is negative.", str(context.exception))
		self.assertEqual(["Got value '-1'."], context.exception.__notes__)


class Hierarchy(Testcase):
	"""Files and directories are built from paths; the counters are summed up to the root."""

	def test_GetOrAddFile(self) -> None:
		summary = CoverageSummary("report")
		file = summary.GetOrAddFile("src/Utilities/Functions.vhdl")

		self.assertIs(file, summary.GetOrAddFile(Path("src/Utilities/Functions.vhdl")))
		self.assertIs(file, summary.GetOrAddFile("src\\Utilities\\Functions.vhdl"))
		self.assertEqual(Path("src/Utilities/Functions.vhdl"), file.Path)
		self.assertEqual("Functions.vhdl", file.Name)
		self.assertIsInstance(file.Parent, Directory)
		self.assertEqual(["src"], list(summary.Directories))
		self.assertEqual(Path("."), summary.Path)

	def test_GetOrAddFile_Absolute(self) -> None:
		"""An absolute path's root - ``/`` on POSIX, ``\\`` or a drive on Windows - becomes no directory."""
		summary = CoverageSummary("report")
		file = summary.GetOrAddFile(Path("/home/runner/src/Counter.vhdl"))

		self.assertEqual(Path("home/runner/src/Counter.vhdl"), file.Path)
		self.assertEqual(["home"], list(summary.Directories))

	def test_GetOrAddFile_Empty(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = CoverageSummary("report").GetOrAddFile("./")

		self.assertEqual("Parameter 'path' names no file.", str(context.exception))

	def test_FileAsDirectory(self) -> None:
		summary = CoverageSummary("report")
		summary.GetOrAddFile("src/Counter.vhdl")

		with self.assertRaises(CodeCoverageError) as context:
			_ = summary.GetOrAddFile("src/Counter.vhdl/Other.vhdl")

		self.assertEqual("'src/Counter.vhdl' is a file, not a directory.", str(context.exception))

	def test_DuplicateName(self) -> None:
		directory = Directory("src")
		_ = File("Counter.vhdl", parent=directory)

		with self.assertRaises(CodeCoverageError) as context:
			_ = Directory("Counter.vhdl", parent=directory)

		self.assertEqual("Directory 'src' already contains 'Counter.vhdl'.", str(context.exception))

	def test_DuplicateLine(self) -> None:
		file = File("Counter.vhdl", lines=(Line(3, Covered), ))

		with self.assertRaises(CodeCoverageError) as context:
			_ = Line(3, Uncovered, parent=file)

		self.assertEqual("Line 3 of file 'Counter.vhdl' is added twice.", str(context.exception))

	def test_LineList(self) -> None:
		"""A file's lines are a list indexed by line number; unlisted lines are None, also when added out of order."""
		file = File("a.c", lines=(Line(5, Covered), ))
		Line(2, Uncovered, parent=file)
		Line(7, Excluded, parent=file)

		lineNumbers = [None if line is None else line.LineNumber for line in file.Lines]
		self.assertEqual([None, None, 2, None, None, 5, None, 7], lineNumbers)
		self.assertEqual(7, file.LastLineNumber)
		self.assertIs(file.Lines[5], file.GetLine(5))
		self.assertIsNone(file.GetLine(3))

		with self.assertRaises(ValueError) as context:
			_ = file.GetLine(8)

		self.assertEqual("Parameter 'lineNumber' is beyond the last line of file 'a.c'.", str(context.exception))
		self.assertEqual(["Got value '8' for 7 lines."], context.exception.__notes__)
		self.assertIsInstance(context.exception.__cause__, IndexError)

	def test_LineList_Constructor(self) -> None:
		"""Lines given to the constructor - also by a generator, out of order - fill a list ending at the last line."""
		file = File("a.c", lines=(line for line in (Line(4, Covered), Line(2, Uncovered))))

		self.assertEqual(4, file.LastLineNumber)
		self.assertEqual(5, len(file.Lines))
		self.assertEqual([2, 4], [line.LineNumber for line in file.IterateLines()])

	def test_GetLine(self) -> None:
		for lineNumber, exceptionType, message in (
			(None, ValueError, "Parameter 'lineNumber' is None."),
			("1",  TypeError,  "Parameter 'lineNumber' is not of type 'int'."),
			(0,    ValueError, "Parameter 'lineNumber' is less than 1.")
		):
			with self.subTest(lineNumber=lineNumber):
				with self.assertRaises(exceptionType) as context:
					_ = File("a.c").GetLine(lineNumber)

				self.assertEqual(message, str(context.exception))

	def test_DuplicateLine_Parameter(self) -> None:
		with self.assertRaises(CodeCoverageError) as context:
			_ = File("Counter.vhdl", lines=(Line(3, Covered), Line(3, Uncovered)))

		self.assertEqual("Line 3 of file 'Counter.vhdl' is added twice.", str(context.exception))

	def test_IterateFiles(self) -> None:
		summary = CoverageSummary("report")
		for path in ("src/b/x.c", "src/a.c", "z.c", "src/c.c"):
			summary.GetOrAddFile(path)

		self.assertEqual(
			["z.c", "src/a.c", "src/c.c", "src/b/x.c"], [file.Path.as_posix() for file in summary.IterateFiles()]
		)
		self.assertEqual(4, summary.FileCount)

	def test_Aggregate(self) -> None:
		summary = _Example()

		for entity, expected in (
			(summary,                                       (5, 3, 2, 1, 1, 6, 3, 3)),
			(summary.Directories["src"].Files["a.py"],      (3, 2, 1, 1, 1, 2, 1, 1)),
			(summary.Directories["src"].Directories["sub"], (2, 1, 1, 0, 0, 4, 2, 2)),
		):
			with self.subTest(entity=str(entity.Path)):
				self.assertEqual(expected, (
					entity.TotalLines, entity.CoveredLines, entity.MissingLines, entity.ExcludedLines, entity.PartialLines,
					entity.TotalBranches, entity.CoveredBranches, entity.MissingBranches
				))

		self.assertAlmostEqual(3 / 5, summary.LineCoverage)
		self.assertAlmostEqual(3 / 6, summary.BranchCoverage)
		self.assertAlmostEqual(6 / 11, summary.Coverage)

	def test_Empty(self) -> None:
		"""Without executable lines or branches, nothing is uncovered, as coverage.py counts it."""
		summary = CoverageSummary("report")
		summary.GetOrAddFile("empty.py")
		summary.Aggregate()

		self.assertEqual(1.0, summary.LineCoverage)
		self.assertEqual(1.0, summary.BranchCoverage)
		self.assertEqual(1.0, summary.Coverage)


class Units(Testcase):
	"""The logical hierarchy: units naming the lines of their files, each line counted once."""

	def test_Hierarchy(self) -> None:
		summary = _Example()
		fileA = summary.Directories["src"].Files["a.py"]

		package = Package("src", parent=summary)
		module = Module("a", file=fileA, parent=package)
		lines = fileA.Lines
		klass = Class("Shape", file=fileA, startLine=lines[1], endLine=lines[3], parent=module)
		method = Method(
			"Area", file=fileA, startLine=lines[2], endLine=lines[3], status=Covered, coverageCount=4, parent=klass
		)
		function = Function("helper", file=fileA, status=Uncovered, coverageCount=0, parent=module)
		summary.Aggregate()

		self.assertEqual("src.a.Shape.Area", method.QualifiedName)
		self.assertEqual([package, module, klass, method, function], list(summary.IterateUnits()))
		self.assertEqual([module, klass, method, function], fileA.Units)
		self.assertEqual(
			(lines[2], lines[3], 4, Covered), (method.StartLine, method.EndLine, method.CoverageCount, method.Status)
		)
		self.assertIs(summary, method.Root)
		self.assertEqual((2, 1, 1), (method.TotalLines, method.CoveredLines, method.PartialLines))
		self.assertEqual((3, 2, 2), (klass.TotalLines, klass.CoveredLines, klass.TotalBranches))
		self.assertEqual((3, 2), (package.TotalLines, package.CoveredLines))
		self.assertEqual("<Method src.a.Shape.Area: 50.0%>", repr(method))
		self.assertEqual([lines[2], lines[3]], list(method.IterateLines()))
		self.assertEqual([], list(function.IterateLines()))

	def test_SourceFile(self) -> None:
		"""In C, the file is the unit containing the functions."""
		summary = CoverageSummary("report")
		file = summary.GetOrAddFile("src/main.c")
		for line in (Line(3, Covered, 1), Line(4, Covered, 1), Line(8, Uncovered, 0)):
			line.Parent = file

		sourceFile = SourceFile("main.c", file=file, startLine=file.Lines[3], endLine=file.Lines[8], parent=summary)
		function = Function("main", file=file, startLine=file.Lines[3], endLine=file.Lines[4], parent=sourceFile)
		summary.Aggregate()

		self.assertEqual("main.c.main", function.QualifiedName)
		self.assertEqual([sourceFile, function], file.Units)
		self.assertEqual((3, 2), (sourceFile.TotalLines, sourceFile.CoveredLines))
		self.assertEqual((2, 2), (function.TotalLines, function.CoveredLines))

	def test_IterateLines(self) -> None:
		"""A file's lines are walked from a first to a last line by line number; lines it doesn't list are skipped."""
		file = File("a.c", lines=(Line(8, Covered), Line(3, Covered), Line(5, Uncovered), Line(4, Excluded)))

		self.assertEqual([3, 4, 5, 8], [line.LineNumber for line in file.IterateLines()])
		self.assertEqual([4, 5], [line.LineNumber for line in file.IterateLines(file.Lines[4], file.Lines[5])])
		self.assertEqual([5, 8], [line.LineNumber for line in file.IterateLines(startLine=file.Lines[5])])
		self.assertEqual([], list(File("empty.c").IterateLines()))

	def test_DuplicateUnit(self) -> None:
		summary = CoverageSummary("report")
		Package("src", parent=summary)

		with self.assertRaises(CodeCoverageError) as context:
			_ = Package("src", parent=summary)

		self.assertEqual("Unit 'src' is added twice to 'report'.", str(context.exception))


class Tree(Testcase):
	"""Every element has a parent and the report's root; attaching a subtree passes the root on."""

	def test_Parents(self) -> None:
		summary = _Example()
		fileA = summary.Directories["src"].Files["a.py"]
		line = fileA.Lines[2]

		self.assertIs(fileA, line.Parent)
		self.assertIs(line, line.Branches[0].Parent)
		self.assertIs(summary, fileA.Parent.Parent)
		self.assertIsNone(summary.Parent)
		for element in (summary, fileA, line, line.Branches[0]):
			with self.subTest(element=repr(element)):
				self.assertIs(summary, element.Root)

	def test_ConstructorChildren(self) -> None:
		"""Lines and branches given to a constructor get the parent and the root of the element they are given to."""
		summary = CoverageSummary("report")
		branch = Branch(Covered)
		line = Line(1, Covered, 1, (branch, ))
		file = File("a.py", lines=(line, ), parent=summary)

		self.assertEqual((file, line), (line.Parent, branch.Parent))
		self.assertEqual((summary, summary), (line.Root, branch.Root))

	def test_AttachSubtree(self) -> None:
		directory = Directory("src")
		line = Line(1, PartiallyCovered, 1, (Branch(Covered), Branch(Uncovered)))
		file = File("a.py", lines=(line, ), parent=directory)
		unit = Package("src")
		Module("a", file=file, parent=unit)
		self.assertIsNone(file.Lines[1].Root)

		summary = CoverageSummary("report")
		directory.Parent = summary
		unit.Parent = summary

		self.assertIs(directory, summary.Directories["src"])
		self.assertIs(unit, summary.Units["src"])
		for element in (directory, file, file.Lines[1], file.Lines[1].Branches[1], unit, unit.Units["a"]):
			with self.subTest(element=repr(element)):
				self.assertIs(summary, element.Root)

	def test_ParentType(self) -> None:
		for create, expected in (
			(lambda: Branch(Covered, parent=File("a.py")),      "Line"),
			(lambda: Line(1, Covered, parent=Directory("src")), "File"),
			(lambda: File("a.py", parent=Line(1, Covered)),     "Directory"),
			(lambda: Directory("src", parent=File("a.py")),     "Directory"),
			(lambda: Package("src", parent=Directory("src")),   "Unit' or 'CoverageSummary")
		):
			with self.subTest(expected=expected):
				with self.assertRaises(TypeError) as context:
					_ = create()

				self.assertEqual(f"Parameter 'parent' is not of type '{expected}'.", str(context.exception))

	def test_ParentType_Setter(self) -> None:
		with self.assertRaises(TypeError) as context:
			File("a.py").Parent = Line(1, Covered)

		self.assertEqual("Parameter 'parent' is not of type 'Directory'.", str(context.exception))
		self.assertEqual(["Got type 'pyEDAA.Reports.CodeCoverage.Line'."], context.exception.__notes__)

	def test_ParentOfRoot(self) -> None:
		with self.assertRaises(TypeError) as context:
			CoverageSummary("report").Parent = Directory("src")

		self.assertEqual("A 'pyEDAA.Reports.CodeCoverage.CoverageSummary' has no parent.", str(context.exception))
		self.assertEqual(["Got type 'pyEDAA.Reports.CodeCoverage.Directory'."], context.exception.__notes__)

	def test_ParentNone(self) -> None:
		with self.assertRaises(ValueError) as context:
			File("a.py").Parent = None

		self.assertEqual("Parameter 'parent' is None.", str(context.exception))


class Checks(Testcase):
	"""Parameters are checked for None, then their type, then their value."""

	def test_Name(self) -> None:
		for create in (lambda name: File(name), lambda name: Directory(name), lambda name: Package(name)):
			for name, exceptionType, message in (
				(None, ValueError, "Parameter 'name' is None."),
				(1,    TypeError,  "Parameter 'name' is not of type 'str'."),
				("",   ValueError, "Parameter 'name' is empty.")
			):
				with self.subTest(name=name):
					with self.assertRaises(exceptionType) as context:
						_ = create(name)

					self.assertEqual(message, str(context.exception))

	def test_LineNumberNone(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = Line(None, Covered)

		self.assertEqual("Parameter 'lineNumber' is None.", str(context.exception))

	def test_StatusNone(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = Branch(None)

		self.assertEqual("Parameter 'status' is None.", str(context.exception))

	def test_CountType(self) -> None:
		with self.assertRaises(TypeError) as context:
			_ = Line(1, Covered, "1")

		self.assertEqual("Parameter 'coverageCount' is not of type 'int'.", str(context.exception))
		self.assertEqual(["Got type 'str'."], context.exception.__notes__)

	def test_Elements(self) -> None:
		for create, parameter, typeName in (
			(lambda: File("a.py", lines=(1, )),                        "lines",             "Line"),
			(lambda: Line(1, Covered, branches=(Covered, )),           "branches",          "Branch"),
			(lambda: CoverageSummary("report", sourceDirectories="/"), "sourceDirectories", "Path")
		):
			with self.subTest(parameter=parameter):
				with self.assertRaises(TypeError) as context:
					_ = create()

				self.assertEqual(
					f"Parameter '{parameter}' contains an element not of type '{typeName}'.", str(context.exception)
				)

	def test_NotIterable(self) -> None:
		with self.assertRaises(TypeError) as context:
			_ = File("a.py", lines=1)

		self.assertEqual("Parameter 'lines' is not iterable.", str(context.exception))
		self.assertEqual(["Got type 'int'."], context.exception.__notes__)

	def test_TargetType(self) -> None:
		with self.assertRaises(TypeError) as context:
			_ = Branch(Covered, target=13)

		self.assertEqual("Parameter 'target' is not of type 'Line'.", str(context.exception))
		self.assertEqual(["Got type 'int'."], context.exception.__notes__)

	def test_UnitLines(self) -> None:
		with self.assertRaises(TypeError) as context:
			_ = Class("Shape", startLine=1)

		self.assertEqual("Parameter 'startLine' is not of type 'Line'.", str(context.exception))

		file = File("a.py", lines=(Line(1, Covered), Line(2, Covered)))
		with self.assertRaises(ValueError) as context:
			_ = Class("Shape", file=File("b.py"), startLine=file.Lines[1])

		self.assertEqual("Parameter 'startLine' is not a line of parameter 'file'.", str(context.exception))

		with self.assertRaises(ValueError) as context:
			_ = Class("Shape", file=file, startLine=file.Lines[2], endLine=file.Lines[1])

		self.assertEqual("Parameter 'endLine' is before parameter 'startLine'.", str(context.exception))
		self.assertEqual(["Got lines 2 to 1."], context.exception.__notes__)

		with self.assertRaises(ValueError) as context:
			_ = list(File("b.py").IterateLines(file.Lines[1]))

		self.assertEqual("Parameter 'startLine' is not a line of file 'b.py'.", str(context.exception))

	def test_PathType(self) -> None:
		with self.assertRaises(TypeError) as context:
			_ = CoverageSummary("report").GetOrAddFile(1)

		self.assertEqual("Parameter 'path' is not of type 'Path' or 'str'.", str(context.exception))


def _Example() -> CoverageSummary:
	"""
	Build a report of two files: ``src/a.py`` with a covered, a partially covered, an uncovered and an excluded line,
	and ``src/sub/b.py`` with a covered and an uncovered line, both branching.

	:returns: The report's root, aggregated.
	"""
	summary = CoverageSummary("report")
	fileA = summary.GetOrAddFile("src/a.py")
	for line in (
		Line(1, Covered, 2), Line(2, PartiallyCovered, 1, (Branch(Covered), Branch(Uncovered))), Line(3, Uncovered, 0),
		Line(4, Excluded)
	):
		line.Parent = fileA

	fileB = summary.GetOrAddFile("src/sub/b.py")
	for line in (
		Line(1, Covered, 1, (Branch(Covered), Branch(Covered))),
		Line(2, Uncovered, 0, (Branch(Uncovered), Branch(Uncovered)))
	):
		line.Parent = fileB

	summary.Aggregate()
	return summary
