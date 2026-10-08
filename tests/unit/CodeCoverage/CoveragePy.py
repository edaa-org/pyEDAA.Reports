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
"""Unit tests of coverage.py's JSON format: its model, its JSON Schema and the conversion to the common model."""
from datetime                               import datetime
from json                                   import dumps, loads
from pathlib                                import Path
from tempfile                               import TemporaryDirectory
from typing                                 import Any

from pyEDAA.Reports.CodeCoverage            import Class, CodeCoverageError, Function, LineCoverageStatus, Method
from pyEDAA.Reports.CodeCoverage            import Module, Package
from pyEDAA.Reports.CodeCoverage.CoveragePy import Base, Document, File, Region, Summary
from pyTooling.MetaClasses                  import AbstractClassError
from pyTooling.Testing                      import Testcase
from pyTooling.Versioning                   import SemanticVersion


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


DATA = Path(__file__).parent.parent.parent / "data" / "CodeCoverage"  #: Directory of the reports and their sources.
REPORT = DATA / "Python" / "coverage.json"                            #: coverage.py's JSON report of the fixture.


def _write(directory: str, content: dict[str, Any]) -> Path:
	"""
	Write a report file into a directory.

	:param directory: The directory.
	:param content:   The report's JSON object.
	:returns:         The report file.
	"""
	jsonFile = Path(directory) / "coverage.json"
	jsonFile.write_text(dumps(content), encoding="utf-8")
	return jsonFile


SUMMARY = {
	"covered_lines": 3, "num_statements": 4, "percent_covered": 66.66666666666667, "percent_covered_display": "67",
	"missing_lines": 1, "excluded_lines": 0, "num_branches": 2, "num_partial_branches": 1, "covered_branches": 1,
	"missing_branches": 1
}  #: A summary as coverage.py writes it, with branch coverage.


class Construction(Testcase):
	"""The format's model is built by hand from typed values, and checks them."""

	def test_Summary(self) -> None:
		summary = Summary(4, 3, 1, 0, 75.0)

		self.assertEqual((4, 3, 1, 0, 75.0), (
			summary.LineCount, summary.CoveredLineCount, summary.MissingLineCount, summary.ExcludedLineCount,
			summary.PercentCovered
		))
		self.assertEqual((None, None, None), (summary.BranchCount, summary.CoveredBranchCount, summary.PartialBranchCount))

	def test_Summary_Branches(self) -> None:
		summary = Summary(4, 3, 1, 0, 66.7, branchCount=2, coveredBranchCount=1, partialBranchCount=1)

		self.assertEqual((2, 1, 1), (summary.BranchCount, summary.CoveredBranchCount, summary.PartialBranchCount))

	def test_Summary_None(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = Summary(None, 3, 1, 0, 75.0)

		self.assertEqual("Parameter 'lineCount' is None.", str(context.exception))

	def test_Summary_Type(self) -> None:
		with self.assertRaises(TypeError) as context:
			_ = Summary(4, "3", 1, 0, 75.0)

		self.assertEqual("Parameter 'coveredLineCount' is not of type 'int'.", str(context.exception))
		self.assertEqual(["Got type 'str'."], context.exception.__notes__)

	def test_Summary_Negative(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = Summary(4, 3, 1, 0, 75.0, partialBranchCount=-1)

		self.assertEqual("Parameter 'partialBranchCount' is negative.", str(context.exception))
		self.assertEqual(["Got value '-1'."], context.exception.__notes__)

	def test_Summary_PercentCovered(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = Summary(4, 3, 1, 0, 100.5)

		self.assertEqual("Parameter 'percentCovered' is out of range 0..100.", str(context.exception))

	def test_Base(self) -> None:
		with self.assertRaises(AbstractClassError):
			_ = Base(Summary(0, 0, 0, 0, 100.0))

	def test_Region(self) -> None:
		summary = Summary(4, 3, 1, 0, 66.7, branchCount=2, coveredBranchCount=1, partialBranchCount=1)
		region = Region(
			"Circle", 5, summary, executedLines=[7, 9, 12], missingLines=(8, ), executedBranches=[(7, 9)],
			missingBranches=[(7, 8)]
		)

		self.assertEqual(("Circle", 5), (region.Name, region.StartLine))
		self.assertIs(summary, region.Summary)
		self.assertEqual(([7, 9, 12], [8], []), (region.ExecutedLines, region.MissingLines, region.ExcludedLines))
		self.assertEqual(([(7, 9)], [(7, 8)]), (region.ExecutedBranches, region.MissingBranches))
		self.assertEqual([7, 8, 9, 12], region.AllLines)

	def test_Region_EmptyName(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = Region("", 1, Summary(0, 0, 0, 0, 100.0))

		self.assertEqual("Parameter 'name' is empty.", str(context.exception))

	def test_Region_StartLine(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = Region("Circle", 0, Summary(0, 0, 0, 0, 100.0))

		self.assertEqual("Parameter 'startLine' is less than 1.", str(context.exception))
		self.assertEqual(["Got value '0'."], context.exception.__notes__)

	def test_Region_Summary(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = Region("Circle", 5, None)

		self.assertEqual("Parameter 'summary' is None.", str(context.exception))

	def test_Region_Lines(self) -> None:
		with self.assertRaises(TypeError) as context:
			_ = Region("Circle", 5, Summary(1, 1, 0, 0, 100.0), excludedLines=[7, "8"])

		self.assertEqual("An element of parameter 'excludedLines' is not of type 'int'.", str(context.exception))
		self.assertEqual(["Got type 'str'."], context.exception.__notes__)

	def test_Region_Branches(self) -> None:
		with self.assertRaises(TypeError) as context:
			_ = Region("Circle", 5, Summary(1, 1, 0, 0, 100.0), missingBranches=[[7, 8]])

		self.assertEqual("An element of parameter 'missingBranches' is not a pair of 'int'.", str(context.exception))
		self.assertEqual(["Got '[7, 8]' of type 'list'."], context.exception.__notes__)

	def test_File(self) -> None:
		area = Region("Circle.Area", 11, Summary(1, 1, 0, 0, 100.0), executedLines=[12])
		circle = Region("Circle", 5, Summary(2, 2, 0, 0, 100.0), executedLines=[7, 12])
		file = File(
			Path("myPackage/Shapes.py"), Summary(3, 3, 0, 0, 100.0), executedLines=[5, 7, 12], functions=[area],
			classes=(circle, )
		)

		self.assertEqual(Path("myPackage/Shapes.py"), file.Path)
		self.assertEqual({"Circle.Area": area}, file.Functions)
		self.assertEqual({"Circle": circle}, file.Classes)
		self.assertEqual(([5, 7, 12], [], []), (file.ExecutedLines, file.MissingLines, file.ExcludedLines))
		self.assertEqual(([], []), (file.ExecutedBranches, file.MissingBranches))

	def test_File_Path(self) -> None:
		with self.assertRaises(TypeError) as context:
			_ = File("myPackage/Shapes.py", Summary(0, 0, 0, 0, 100.0))

		self.assertEqual("Parameter 'path' is not of type 'Path'.", str(context.exception))
		self.assertEqual(["Got type 'str'."], context.exception.__notes__)

	def test_File_Regions(self) -> None:
		with self.assertRaises(TypeError) as context:
			_ = File(Path("Shapes.py"), Summary(0, 0, 0, 0, 100.0), functions={"Circle.Area": 11})

		self.assertEqual("An element of parameter 'functions' is not of type 'Region'.", str(context.exception))
		self.assertEqual(["Got type 'str'."], context.exception.__notes__)

	def test_File_DuplicateRegion(self) -> None:
		circle = Region("Circle", 5, Summary(0, 0, 0, 0, 100.0))
		with self.assertRaises(ValueError) as context:
			_ = File(Path("Shapes.py"), Summary(0, 0, 0, 0, 100.0), classes=[circle, circle])

		self.assertEqual("Parameter 'classes' contains region 'Circle' twice.", str(context.exception))


class Parsing(Testcase):
	"""Parse reads a JSON object of the report and builds the format's model from it."""

	def test_Summary(self) -> None:
		summary = Summary.Parse(SUMMARY)

		self.assertEqual((4, 3, 1, 0, 66.66666666666667, 2, 1, 1), (
			summary.LineCount, summary.CoveredLineCount, summary.MissingLineCount, summary.ExcludedLineCount,
			summary.PercentCovered, summary.BranchCount, summary.CoveredBranchCount, summary.PartialBranchCount
		))

	def test_Summary_NoBranches(self) -> None:
		summary = Summary.Parse({
			"covered_lines": 1, "num_statements": 2, "percent_covered": 50.0, "missing_lines": 1, "excluded_lines": 0
		})

		self.assertEqual((None, None, None), (summary.BranchCount, summary.CoveredBranchCount, summary.PartialBranchCount))

	def test_Summary_None(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = Summary.Parse(None)

		self.assertEqual("Parameter 'summary' is None.", str(context.exception))

	def test_Region(self) -> None:
		region = Region.Parse("Circle", {
			"executed_lines": [7, 9, 12], "summary": SUMMARY, "missing_lines": [8], "excluded_lines": [], "start_line": 5,
			"executed_branches": [[7, 9]], "missing_branches": [[7, 8]]
		})

		self.assertEqual(("Circle", 5, 4), (region.Name, region.StartLine, region.Summary.LineCount))
		self.assertEqual(([(7, 9)], [(7, 8)]), (region.ExecutedBranches, region.MissingBranches))

	def test_Region_Type(self) -> None:
		with self.assertRaises(TypeError) as context:
			_ = Region.Parse("Circle", [])

		self.assertEqual("Parameter 'region' is not of type 'dict'.", str(context.exception))
		self.assertEqual(["Got type 'list'."], context.exception.__notes__)

	def test_File(self) -> None:
		"""The path's separators become '/'; the region named '' - the lines outside of every region - is skipped."""
		region = {"executed_lines": [], "summary": SUMMARY, "missing_lines": [], "excluded_lines": [], "start_line": 1}
		file = File.Parse("myPackage\\Shapes.py", {
			"executed_lines": [7, 9, 12], "summary": SUMMARY, "missing_lines": [8], "excluded_lines": [],
			"functions": {"": region, "Circle.Area": region}, "classes": {"": region, "Circle": region}
		})

		self.assertEqual("myPackage/Shapes.py", file.Path.as_posix())
		self.assertEqual((["Circle.Area"], ["Circle"]), (list(file.Functions), list(file.Classes)))
		self.assertEqual(([], []), (file.ExecutedBranches, file.MissingBranches))

	def test_File_Name(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = File.Parse(None, {})

		self.assertEqual("Parameter 'name' is None.", str(context.exception))


class FormatModel(Testcase):
	"""The format's model keeps what the report states: meta data, files, regions, summaries."""

	def test_Report(self) -> None:
		report = Document(REPORT, analyzeAndConvert=True)

		self.assertEqual(
			(3, "7.16.1", True, False), (report.Format, report.Version, report.BranchCoverage, report.HasContexts)
		)
		self.assertIsInstance(report.Version, SemanticVersion)
		self.assertEqual(datetime(2026, 10, 7, 9, 14, 51, 108137), report.Timestamp)
		self.assertEqual(
			["myPackage/Shapes.py", "myPackage/Units/Length.py", "myPackage/Units/__init__.py", "myPackage/__init__.py"],
			sorted(path.as_posix() for path in report.Files)
		)
		totals = report.Totals
		self.assertEqual((27, 22, 5, 2, 10, 5, 3), (
			totals.LineCount, totals.CoveredLineCount, totals.MissingLineCount, totals.ExcludedLineCount,
			totals.BranchCount, totals.CoveredBranchCount, totals.PartialBranchCount
		))

		shapes = report.Files[Path("myPackage/Shapes.py")]
		self.assertEqual([8, 25], shapes.MissingLines)
		self.assertEqual([28, 29], shapes.ExcludedLines)
		self.assertIn((7, 8), shapes.MissingBranches)
		self.assertEqual(["Circle.Area", "Circle.__init__", "Rectangle.Area", "Rectangle.IsSquare", "Rectangle.__init__",
		                  "Rectangle.__repr__"], sorted(shapes.Functions))
		self.assertEqual((5, [7, 8, 9, 12]), (shapes.Classes["Circle"].StartLine, shapes.Classes["Circle"].AllLines))


class Conversion(Testcase):
	"""The conversion to the common model: lines with branches and their targets, and modules, classes and functions."""

	def test_Totals(self) -> None:
		"""The computed counters agree with the summaries coverage.py computed, in total and per file."""
		report = Document(REPORT, analyzeAndConvert=True)
		summary = report.ToCoverageSummary()

		pairs = [(summary, report.Totals)]
		pairs.extend((file, report.Files[file.Path].Summary) for file in summary.IterateFiles())
		for entity, stated in pairs:
			files = list(summary.IterateFiles()) if entity is summary else [entity]
			partialBranches = sum(
				1 for file in files for line in file.IterateLines() if line.Status is not LineCoverageStatus.Uncovered
				for branch in line.Branches if branch.Status is LineCoverageStatus.Uncovered
			)
			with self.subTest(entity=entity.Path.as_posix()):
				self.assertEqual(
					(stated.LineCount, stated.CoveredLineCount, stated.ExcludedLineCount, stated.BranchCount,
					 stated.CoveredBranchCount, stated.PartialBranchCount),
					(entity.TotalLines, entity.CoveredLines, entity.ExcludedLines, entity.TotalBranches,
					 entity.CoveredBranches, partialBranches)
				)
				self.assertAlmostEqual(stated.PercentCovered, entity.Coverage * 100)

	def test_Lines(self) -> None:
		shapes = Document(REPORT, analyzeAndConvert=True).ToCoverageSummary().Directories["myPackage"].Files["Shapes.py"]

		line = shapes.Lines[7]
		self.assertIs(LineCoverageStatus.PartiallyCovered, line.Status)
		self.assertIsNone(line.CoverageCount)
		self.assertEqual([(LineCoverageStatus.Covered, 9), (LineCoverageStatus.Uncovered, 8)], [
			(branch.Status, branch.Target.LineNumber) for branch in line.Branches
		])
		self.assertIs(LineCoverageStatus.Uncovered, shapes.Lines[8].Status)
		self.assertIs(LineCoverageStatus.Excluded, shapes.Lines[28].Status)

	def test_Units(self) -> None:
		summary = Document(REPORT, analyzeAndConvert=True).ToCoverageSummary()

		units = {unit.QualifiedName: unit for unit in summary.IterateUnits()}
		for name, unitClass in (
			("myPackage", Package), ("myPackage.Shapes", Module), ("myPackage.Shapes.Circle", Class),
			("myPackage.Shapes.Circle.Area", Method), ("myPackage.Units.Length.ToMeters", Function),
			("myPackage.__init__", Module)
		):
			with self.subTest(name=name):
				self.assertIsInstance(units[name], unitClass)

		isSquare = units["myPackage.Shapes.Rectangle.IsSquare"]
		self.assertEqual((23, 26), (isSquare.StartLine.LineNumber, isSquare.EndLine.LineNumber))
		# the unit spans its 'def' line too, which coverage.py's function summary counts for the enclosing scope
		self.assertEqual((4, 3, 1), (isSquare.TotalLines, isSquare.CoveredLines, isSquare.PartialLines))
		self.assertIn(summary.Directories["myPackage"].Files["Shapes.py"].Lines[24], list(isSquare.IterateLines()))

	def test_Format2(self) -> None:
		"""Format 2 has no regions: a file becomes a module only."""
		summary = {
			"covered_lines": 1, "num_statements": 2, "percent_covered": 50.0, "missing_lines": 1, "excluded_lines": 0
		}
		with TemporaryDirectory() as directory:
			report = Document(_write(directory, {
				"meta": {"format": 2, "version": "6.5.0", "timestamp": "2022-10-01T12:00:00", "branch_coverage": False,
				         "show_contexts": False},
				"files": {
					"pkg\\mod.py": {"executed_lines": [1], "missing_lines": [2], "excluded_lines": [], "summary": summary}
				},
				"totals": summary
			}), analyzeAndConvert=True)

		common = report.ToCoverageSummary()
		self.assertEqual(["pkg.mod"], [unit.QualifiedName for unit in common.IterateUnits()][1:])
		self.assertEqual((2, 1, 0), (common.TotalLines, common.CoveredLines, common.TotalBranches))
		self.assertEqual("pkg/mod.py", next(common.IterateFiles()).Path.as_posix())


class Schema(Testcase):
	"""The reverse-engineered JSON Schema accepts coverage.py's report and rejects what it doesn't write."""

	def test_Format1(self) -> None:
		"""Format 1 had no 'meta.format'."""
		content = loads(REPORT.read_text(encoding="utf-8"))
		del content["meta"]["format"]
		with TemporaryDirectory() as directory:
			jsonFile = _write(directory, content)

			with self.assertRaises(CodeCoverageError) as context:
				_ = Document(jsonFile, analyzeAndConvert=True)

		self.assertEqual(
			f"Validation error for '{jsonFile}' using JSON Schema 'CoveragePy-JSON.schema.json'.", str(context.exception)
		)
		self.assertEqual(["/meta: 'format' is a required property"], context.exception.__notes__)

	def test_UnknownField(self) -> None:
		content = loads(REPORT.read_text(encoding="utf-8"))
		content["files"]["myPackage/Shapes.py"]["hits"] = []
		with TemporaryDirectory() as directory:
			with self.assertRaises(CodeCoverageError) as context:
				_ = Document(_write(directory, content), analyzeAndConvert=True)

		self.assertEqual(
			["/files/myPackage/Shapes.py: Additional properties are not allowed ('hits' was unexpected)"],
			context.exception.__notes__
		)

	def test_Syntax(self) -> None:
		with TemporaryDirectory() as directory:
			jsonFile = Path(directory) / "coverage.json"
			jsonFile.write_text("{", encoding="utf-8")

			with self.assertRaises(CodeCoverageError) as context:
				_ = Document(jsonFile, analyzeAndConvert=True)

		self.assertEqual(f"JSON syntax error in coverage.py report file '{jsonFile}'.", str(context.exception))

	def test_Missing(self) -> None:
		with self.assertRaises(CodeCoverageError) as context:
			_ = Document(DATA / "missing.json", analyzeAndConvert=True)

		self.assertEqual(f"coverage.py report file '{DATA / 'missing.json'}' does not exist.", str(context.exception))

	def test_NotAnalyzed(self) -> None:
		with self.assertRaises(CodeCoverageError):
			Document(REPORT).Convert()
