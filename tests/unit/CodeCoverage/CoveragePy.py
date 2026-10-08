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
from pyEDAA.Reports.CodeCoverage.CoveragePy import Document
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


class FormatModel(Testcase):
	"""The format's model keeps what the report states: meta data, files, regions, summaries."""

	def test_Report(self) -> None:
		report = Document(REPORT, analyzeAndConvert=True)

		self.assertEqual(
			(3, "7.16.1", True, False), (report.Format, report.Version, report.BranchCoverage, report.ShowContexts)
		)
		self.assertIsInstance(report.Version, SemanticVersion)
		self.assertEqual(datetime(2026, 10, 7, 9, 14, 51, 108137), report.Timestamp)
		self.assertEqual(
			["myPackage/Shapes.py", "myPackage/Units/Length.py", "myPackage/Units/__init__.py", "myPackage/__init__.py"],
			sorted(path.as_posix() for path in report.Files)
		)
		totals = report.Totals
		self.assertEqual((27, 22, 5, 2, 10, 5, 3), (
			totals.StatementCount, totals.CoveredLines, totals.MissingLines, totals.ExcludedLines, totals.BranchCount,
			totals.CoveredBranches, totals.PartialBranchCount
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
			with self.subTest(entity=entity.Path.as_posix()):
				self.assertEqual(
					(stated.StatementCount, stated.CoveredLines, stated.ExcludedLines, stated.BranchCount,
					 stated.CoveredBranches, stated.PartialBranchCount),
					(entity.TotalLines, entity.CoveredLines, entity.ExcludedLines, entity.TotalBranches,
					 entity.CoveredBranches, entity.PartialLines)
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
