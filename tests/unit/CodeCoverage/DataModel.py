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
from pyEDAA.Reports.CodeCoverage import Line, LineCoverageStatus, Method, Module, Package
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
		line = Line(12, PartiallyCovered, 7, (Branch(Covered, 7, 13), Branch(Uncovered, 0)))

		self.assertEqual(12, line.LineNumber)
		self.assertIs(PartiallyCovered, line.Status)
		self.assertEqual(7, line.Count)
		self.assertEqual(2, len(line.Branches))
		self.assertEqual(1, line.CoveredBranches)
		self.assertEqual(13, line.Branches[0].Target)
		self.assertEqual("<Line 12: PartiallyCovered (1/2 branches)>", repr(line))

	def test_WithoutCount(self) -> None:
		"""coverage.py states whether a line ran, but not how often."""
		line = Line(1, Covered)

		self.assertIsNone(line.Count)
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
		for status, count in ((Covered, 0), (PartiallyCovered, 0), (Uncovered, 3)):
			with self.subTest(status=status.name):
				with self.assertRaises(ValueError) as context:
					_ = Line(1, status, count)

				self.assertEqual("Parameter 'count' contradicts parameter 'status'.", str(context.exception))
				self.assertEqual([f"Got count '{count}' for status '{status.name}'."], context.exception.__notes__)

	def test_NegativeCount(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = Branch(Uncovered, -1)

		self.assertEqual("Parameter 'count' is negative.", str(context.exception))
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
			file.AddLine(Line(3, Uncovered))

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
		klass = Class("Shape", file=fileA, startLine=1, endLine=3, parent=module)
		method = Method("Area", file=fileA, startLine=2, endLine=3, status=Covered, count=4, parent=klass)
		function = Function("helper", file=fileA, status=Uncovered, count=0, parent=module)
		for number in (1, 2, 3):
			klass.AddLine(fileA.Lines[number])

		for number in (2, 3):
			method.AddLine(fileA.Lines[number])
		summary.Aggregate()

		self.assertEqual("src.a.Shape.Area", method.QualifiedName)
		self.assertEqual([package, module, klass, method, function], list(summary.IterateUnits()))
		self.assertEqual([module, klass, method, function], fileA.Units)
		self.assertEqual((2, 3, 4, Covered), (method.StartLine, method.EndLine, method.Count, method.Status))
		self.assertEqual((2, 1, 1), (method.TotalLines, method.CoveredLines, method.PartialLines))
		self.assertEqual((3, 2, 2), (klass.TotalLines, klass.CoveredLines, klass.TotalBranches))
		self.assertEqual((3, 2), (package.TotalLines, package.CoveredLines))
		self.assertEqual("<Method src.a.Shape.Area: 50.0%>", repr(method))

	def test_DuplicateUnit(self) -> None:
		summary = CoverageSummary("report")
		Package("src", parent=summary)

		with self.assertRaises(CodeCoverageError) as context:
			_ = Package("src", parent=summary)

		self.assertEqual("Unit 'src' is added twice to 'report'.", str(context.exception))


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
		fileA.AddLine(line)

	fileB = summary.GetOrAddFile("src/sub/b.py")
	for line in (
		Line(1, Covered, 1, (Branch(Covered), Branch(Covered))),
		Line(2, Uncovered, 0, (Branch(Uncovered), Branch(Uncovered)))
	):
		fileB.AddLine(line)

	summary.Aggregate()
	return summary
