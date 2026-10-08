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
#
"""Unit tests of coverage.py's Cobertura dialect: its model, its schema and the conversion to the common model."""
from pathlib                                                   import Path
from tempfile                                                  import TemporaryDirectory
from textwrap                                                  import dedent

from lxml.etree                                                import XMLSchema, parse
from pyTooling.Common                                          import getResourceFile

from pyEDAA.Reports                                            import Resources
from pyEDAA.Reports.CodeCoverage                               import CodeCoverageError, LineCoverageStatus, Module
from pyEDAA.Reports.CodeCoverage                               import Package
from pyEDAA.Reports.CodeCoverage.Cobertura                     import READ_SCHEMA as ANY_SCHEMA
from pyEDAA.Reports.CodeCoverage.Cobertura.CoveragePyCobertura import READ_SCHEMA, Document, Line
from pyTooling.Testing                                         import Testcase


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


DATA =   Path(__file__).parent.parent.parent / "data" / "CodeCoverage"  #: Directory of the reports and their sources.
REPORT = DATA / "Python" / "coverage.xml"                              #: coverage.py's Cobertura report of the fixture.

#: A report of coverage.py 7.16.1, measuring branches, the root's attributes wrapped: line 2 never takes its branch to
#: the function's exit.
EXIT_REPORT = dedent("""\
	<?xml version="1.0" ?>
	<coverage version="7.16.1" timestamp="1791456017279" lines-valid="8" lines-covered="7" line-rate="0.875"
	          branches-valid="4" branches-covered="2" branch-rate="0.5" complexity="0">
		<!-- Generated by coverage.py: https://coverage.readthedocs.io/en/7.16.1 -->
		<!-- Based on https://raw.githubusercontent.com/cobertura/web/master/htdocs/xml/coverage-04.dtd -->
		<sources>
			<source>/home/user/project</source>
		</sources>
		<packages>
			<package name="pkg" line-rate="0.875" branch-rate="0.5" complexity="0">
				<classes>
					<class name="Exit.py" filename="pkg/Exit.py" complexity="0" line-rate="0.875" branch-rate="0.5">
						<methods/>
						<lines>
							<line number="1" hits="1"/>
							<line number="2" hits="1" branch="true" condition-coverage="50% (1/2)" missing-branches="exit"/>
							<line number="3" hits="1"/>
							<line number="6" hits="1"/>
							<line number="7" hits="1"/>
							<line number="8" hits="1" branch="true" condition-coverage="50% (1/2)" missing-branches="9"/>
							<line number="9" hits="0"/>
							<line number="10" hits="1"/>
						</lines>
					</class>
				</classes>
			</package>
		</packages>
	</coverage>
""")

#: The same measurement without branches.
LINE_REPORT = dedent("""\
	<?xml version="1.0" ?>
	<coverage version="7.16.1" timestamp="1791456017981" lines-valid="8" lines-covered="7" line-rate="0.875"
	          branches-covered="0" branches-valid="0" branch-rate="0" complexity="0">
		<sources>
			<source>/home/user/project</source>
		</sources>
		<packages>
			<package name="pkg" line-rate="0.875" branch-rate="0" complexity="0">
				<classes>
					<class name="Exit.py" filename="pkg/Exit.py" complexity="0" line-rate="0.875" branch-rate="0">
						<methods/>
						<lines>
							<line number="1" hits="1"/>
							<line number="2" hits="1"/>
							<line number="3" hits="1"/>
							<line number="6" hits="1"/>
							<line number="7" hits="1"/>
							<line number="8" hits="1"/>
							<line number="9" hits="0"/>
							<line number="10" hits="1"/>
						</lines>
					</class>
				</classes>
			</package>
		</packages>
	</coverage>
""")


def _write(directory: str, content: str) -> Path:
	"""
	Write a report file into a directory.

	:param directory: The directory.
	:param content:   The report's content.
	:returns:         The report file.
	"""
	xmlFile = Path(directory) / "coverage.xml"
	xmlFile.write_text(content, encoding="utf-8")
	return xmlFile


class FormatModel(Testcase):
	"""The format's model keeps what the report states, and the targets of the branches never taken."""

	def test_Report(self) -> None:
		report = Document(REPORT, analyzeAndConvert=True)

		self.assertEqual(("7.16.1", "1791364491202"), (report.Version, report.Timestamp))
		self.assertEqual(
			(27, 22, 10, 5), (report.LinesValid, report.LinesCovered, report.BranchesValid, report.BranchesCovered)
		)
		self.assertEqual((0.8148, 0.5, 0.0), (report.LineRate, report.BranchRate, report.Complexity))
		self.assertEqual(["myPackage"], report.Sources)
		self.assertEqual([".", "Units"], [package.Name for package in report.Packages])

		length = report.Packages[1].Classes[0]
		self.assertEqual(("Length.py", "Units/Length.py", {}), (length.Name, length.Filename, length.Methods))

		line = length.Lines[14]
		self.assertIsInstance(line, Line)
		self.assertEqual(
			(0, True, (0, 2), [15, 17]), (line.Hits, line.Branch, line.ConditionCoverage, line.MissingBranches)
		)
		self.assertEqual([], line.Conditions)

		line = length.Lines[11]
		self.assertEqual((1, False, None, []), (line.Hits, line.Branch, line.ConditionCoverage, line.MissingBranches))

	def test_Exit(self) -> None:
		"""coverage.py names an exit of the function 'exit'."""
		with TemporaryDirectory() as directory:
			report = Document(_write(directory, EXIT_REPORT), analyzeAndConvert=True)

		lines = report.Packages[0].Classes[0].Lines
		self.assertEqual([None], lines[2].MissingBranches)
		self.assertEqual([9], lines[8].MissingBranches)

	def test_Line(self) -> None:
		line = Line(3, 1, True, (2, 3), iter([None]))

		self.assertEqual((3, 1, True, (2, 3), [None]), (
			line.Number, line.Hits, line.Branch, line.ConditionCoverage, line.MissingBranches
		))
		self.assertEqual([], Line(4, 0).MissingBranches)


class Conversion(Testcase):
	"""The conversion to the common model: lines without counts, branches with targets, and modules as units."""

	def test_Totals(self) -> None:
		"""The computed counters agree with the figures coverage.py states, in total and per file."""
		report = Document(REPORT, analyzeAndConvert=True)
		summary = report.ToCoverageSummary()

		self.assertEqual(
			(report.LinesValid, report.LinesCovered, report.BranchesValid, report.BranchesCovered),
			(summary.TotalLines, summary.CoveredLines, summary.TotalBranches, summary.CoveredBranches)
		)
		self.assertEqual(3, summary.PartialLines)

		for package in report.Packages:
			for klass in package.Classes:
				with self.subTest(file=klass.Filename):
					file = summary.GetOrAddFile(klass.Filename)
					self.assertAlmostEqual(klass.LineRate, file.LineCoverage, places=4)
					self.assertAlmostEqual(klass.BranchRate, file.BranchCoverage, places=4)

	def test_Lines(self) -> None:
		summary = Document(REPORT, analyzeAndConvert=True).ToCoverageSummary()

		shapes = summary.Files["Shapes.py"]
		line = shapes.Lines[7]
		self.assertIs(LineCoverageStatus.PartiallyCovered, line.Status)
		self.assertIsNone(line.CoverageCount)
		self.assertEqual([(LineCoverageStatus.Covered, None), (LineCoverageStatus.Uncovered, shapes.Lines[8])], [
			(branch.Status, branch.Target) for branch in line.Branches
		])
		self.assertEqual((LineCoverageStatus.Uncovered, None), (shapes.Lines[8].Status, shapes.Lines[8].CoverageCount))
		self.assertEqual((LineCoverageStatus.Covered, None), (shapes.Lines[9].Status, shapes.Lines[9].CoverageCount))

		length = summary.Directories["Units"].Files["Length.py"]
		line = length.Lines[14]
		self.assertIs(LineCoverageStatus.Uncovered, line.Status)
		self.assertEqual([(LineCoverageStatus.Uncovered, 15), (LineCoverageStatus.Uncovered, 17)], [
			(branch.Status, branch.Target.LineNumber) for branch in line.Branches
		])
		self.assertEqual([LineCoverageStatus.Covered] * 2, [branch.Status for branch in length.Lines[10].Branches])

	def test_Exit(self) -> None:
		"""A branch to the function's exit has no target line."""
		with TemporaryDirectory() as directory:
			summary = Document(_write(directory, EXIT_REPORT), analyzeAndConvert=True).ToCoverageSummary()

		exit = summary.Directories["pkg"].Files["Exit.py"]
		self.assertEqual([(LineCoverageStatus.Covered, None), (LineCoverageStatus.Uncovered, None)], [
			(branch.Status, branch.Target) for branch in exit.Lines[2].Branches
		])
		self.assertIs(exit.Lines[9], exit.Lines[8].Branches[1].Target)
		self.assertEqual((8, 7, 4, 2, 2), (
			summary.TotalLines, summary.CoveredLines, summary.TotalBranches, summary.CoveredBranches, summary.PartialLines
		))

	def test_WithoutBranches(self) -> None:
		"""Measured without branches, no line branches."""
		with TemporaryDirectory() as directory:
			summary = Document(_write(directory, LINE_REPORT), analyzeAndConvert=True).ToCoverageSummary()

		self.assertEqual(
			(8, 7, 0, 0), (summary.TotalLines, summary.CoveredLines, summary.TotalBranches, summary.PartialLines)
		)
		self.assertEqual(1.0, summary.BranchCoverage)

	def test_Units(self) -> None:
		"""A file's directories become packages, the file a module spanning its listed lines."""
		summary = Document(REPORT, analyzeAndConvert=True).ToCoverageSummary()

		units = {unit.QualifiedName: unit for unit in summary.IterateUnits()}
		self.assertEqual(["Shapes", "Units", "Units.Length", "Units.__init__", "__init__"], list(units))
		for name, unitClass in (("Shapes", Module), ("Units", Package), ("Units.Length", Module)):
			with self.subTest(name=name):
				self.assertIsInstance(units[name], unitClass)

		length = units["Units.Length"]
		self.assertIs(summary.Directories["Units"].Files["Length.py"], length.File)
		self.assertEqual((4, 17), (length.StartLine.LineNumber, length.EndLine.LineNumber))
		self.assertEqual(
			(8, 5, 6, 3), (length.TotalLines, length.CoveredLines, length.TotalBranches, length.CoveredBranches)
		)
		self.assertEqual((None, None), (units["Units.__init__"].StartLine, units["Units.__init__"].EndLine))

	def test_SameFileTwice(self) -> None:
		content = REPORT.read_text(encoding="utf-8").replace('filename="__init__.py"', 'filename="Shapes.py"')
		with TemporaryDirectory() as directory:
			report = Document(_write(directory, content), analyzeAndConvert=True)

		with self.assertRaises(CodeCoverageError) as context:
			_ = report.ToCoverageSummary()

		self.assertEqual("Line 2 of file 'Shapes.py' is added twice.", str(context.exception))


class Schema(Testcase):
	"""The reverse-engineered schema accepts what coverage.py writes and rejects what it doesn't."""

	def test_Schemas(self) -> None:
		"""coverage.py's report is valid for the dialect and the generic reader, gcovr's for the generic one only."""
		strict = XMLSchema(parse(getResourceFile(Resources, READ_SCHEMA)))
		lenient = XMLSchema(parse(getResourceFile(Resources, ANY_SCHEMA)))

		for report, valid in ((REPORT, True), (DATA / "VHDL" / "Cobertura.xml", False)):
			with self.subTest(report=report.parent.name):
				self.assertEqual(valid, strict.validate(parse(report)))
				self.assertTrue(lenient.validate(parse(report)))

	def test_Invalid(self) -> None:
		"""A count, a method, a condition or an unknown attribute isn't what coverage.py writes."""
		original = REPORT.read_text(encoding="utf-8")
		for name, old, new in (
			("Count",     '<line number="2" hits="1"/>', '<line number="2" hits="2"/>'),
			("Method",    "<methods/>", '<methods><method name="f" signature=""><lines/></method></methods>'),
			("Condition", '<line number="2" hits="1"/>', '<line number="2" hits="1"><conditions/></line>'),
			("Attribute", '<line number="2" hits="1"/>', '<line number="2" hits="1" branch="false"/>'),
			("Target",    'missing-branches="8"', 'missing-branches="-1"'),
			("Version",   'version="7.16.1"', 'version="gcovr 8.4"'),
		):
			with self.subTest(name=name), TemporaryDirectory() as directory:
				xmlFile = _write(directory, original.replace(old, new, 1))

				with self.assertRaises(CodeCoverageError) as context:
					_ = Document(xmlFile, analyzeAndConvert=True)

				self.assertEqual(
					f"Validation error for '{xmlFile}' using XSD schema 'CoveragePy-Cobertura.xsd'.", str(context.exception)
				)
				self.assertEqual(1, len(context.exception.__notes__))

	def test_RootElement(self) -> None:
		with TemporaryDirectory() as directory:
			xmlFile = _write(directory, "<testsuites/>")

			with self.assertRaises(CodeCoverageError) as context:
				_ = Document(xmlFile, analyzeAndConvert=True)

		self.assertEqual(f"Root element of '{xmlFile}' is not '<coverage>'.", str(context.exception))

	def test_Missing(self) -> None:
		with self.assertRaises(CodeCoverageError) as context:
			_ = Document(DATA / "missing.xml", analyzeAndConvert=True)

		self.assertEqual(f"Cobertura report file '{DATA / 'missing.xml'}' does not exist.", str(context.exception))

	def test_NotAnalyzed(self) -> None:
		with self.assertRaises(CodeCoverageError):
			Document(REPORT).Convert()
