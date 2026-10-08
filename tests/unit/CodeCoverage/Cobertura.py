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
# Copyright 2021-2026 Electronic Design Automation Abstraction (EDA²)                                                  #
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
"""Unit tests of the Cobertura XML format: its model, its schemas and the conversion to the common model."""
from pathlib                               import Path
from tempfile                              import TemporaryDirectory

from lxml.etree                            import XMLSchema, parse
from pyTooling.Common                      import getResourceFile

from pyEDAA.Reports                        import Resources
from pyEDAA.Reports.CodeCoverage           import Class, CodeCoverageError, LineCoverageStatus, Method, Package
from pyEDAA.Reports.CodeCoverage.Cobertura import READ_SCHEMA, STRICT_SCHEMA, Document
from pyTooling.Testing                     import Testcase


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


DATA = Path(__file__).parent.parent.parent / "data" / "CodeCoverage"  #: Directory of the reports and their sources.


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
	"""The format's model keeps what the report states: figures, packages, classes, methods, lines, conditions."""

	def test_VHDL(self) -> None:
		report = Document(DATA / "VHDL" / "Cobertura.xml", analyzeAndConvert=True)

		self.assertEqual("gcovr 8.4", report.Version)
		self.assertEqual("1791360000", report.Timestamp)
		self.assertEqual(
			(16, 12, 12, 8), (report.LinesValid, report.LinesCovered, report.BranchesValid, report.BranchesCovered)
		)
		self.assertEqual((0.75, 0.6667, 0.0), (report.LineRate, report.BranchRate, report.Complexity))
		self.assertEqual(["."], report.Sources)
		self.assertEqual(["src", "src.Utilities"], [package.Name for package in report.Packages])

		counter = report.Packages[0].Classes[0]
		self.assertEqual(
			("Counter_vhdl", "src/Counter.vhdl", 0.875, 0.75),
			(counter.Name, counter.Filename, counter.LineRate, counter.BranchRate)
		)
		line = counter.Lines[26]
		self.assertEqual((1024, True, (1, 2)), (line.Hits, line.Branch, line.ConditionCoverage))
		self.assertEqual(
			[(0, "jump", "50%")], [(condition.Number, condition.Type, condition.Coverage) for condition in line.Conditions]
		)
		self.assertGreaterEqual(report.AnalysisDuration.total_seconds(), 0.0)

	def test_Methods(self) -> None:
		with TemporaryDirectory() as directory:
			report = Document(_write(directory,
				'<coverage><packages><package name="p"><classes><class name="A" filename="A.java"><methods>'
				'<method name="run" signature="()V"><lines><line number="3" hits="1"/></lines></method>'
				'<method name="run" signature="(I)V"><lines><line number="5" hits="0"/></lines></method>'
				'</methods><lines><line number="3" hits="1"/><line number="5" hits="0"/></lines></class>'
				'</classes></package></packages></coverage>'
			), analyzeAndConvert=True)

		methods = report.Packages[0].Classes[0].Methods
		self.assertEqual(["run", "run(I)V"], list(methods))
		self.assertEqual("()V", methods["run"].Signature)
		self.assertEqual([5], list(methods["run(I)V"].Lines))


class Conversion(Testcase):
	"""The conversion to the common model: files and lines, and packages, classes and methods as units."""

	def test_Python(self) -> None:
		"""coverage.py's report: the computed figures agree with the stated ones."""
		report = Document(DATA / "Python" / "coverage.xml", analyzeAndConvert=True)
		summary = report.ToCoverageSummary()

		self.assertEqual("coverage", summary.Name)
		self.assertEqual(["myPackage"], [str(directory) for directory in summary.SourceDirectories])
		self.assertEqual(
			["Shapes.py", "__init__.py", "Units/Length.py", "Units/__init__.py"],
			[file.Path.as_posix() for file in summary.IterateFiles()]
		)
		self.assertEqual(
			(report.LinesValid, report.LinesCovered, report.BranchesValid, report.BranchesCovered),
			(summary.TotalLines, summary.CoveredLines, summary.TotalBranches, summary.CoveredBranches)
		)

		shapes = summary.Files["Shapes.py"]
		self.assertIs(LineCoverageStatus.PartiallyCovered, shapes.Lines[7].Status)
		self.assertEqual(1, shapes.Lines[7].CoverageCount)
		self.assertEqual(
			[LineCoverageStatus.Covered, LineCoverageStatus.Uncovered], [branch.Status for branch in shapes.Lines[7].Branches]
		)
		self.assertIs(LineCoverageStatus.Uncovered, shapes.Lines[8].Status)

	def test_VHDL(self) -> None:
		"""gcovr's packages - directories joined by '.' - become nested packages holding the classes."""
		summary = Document(DATA / "VHDL" / "Cobertura.xml", analyzeAndConvert=True).ToCoverageSummary()

		self.assertEqual((16, 12, 12, 8, 2), (
			summary.TotalLines, summary.CoveredLines, summary.TotalBranches, summary.CoveredBranches, summary.PartialLines
		))
		self.assertEqual(
			["src", "src.Counter_vhdl", "src.Utilities", "src.Utilities.Functions_vhdl"],
			[unit.QualifiedName for unit in summary.IterateUnits()]
		)
		counter = summary.Units["src"].Units["Counter_vhdl"]
		self.assertIsInstance(summary.Units["src"], Package)
		self.assertIsInstance(counter, Class)
		self.assertIs(summary.Directories["src"].Files["Counter.vhdl"], counter.File)
		self.assertEqual((8, 7), (counter.TotalLines, counter.CoveredLines))
		self.assertEqual(2048, counter.File.Lines[25].CoverageCount)

	def test_MergedClasses(self) -> None:
		"""Two classes of one source file, as Java's nested classes, become one file; their lines are merged."""
		with TemporaryDirectory() as directory:
			summary = Document(_write(directory,
				'<coverage><packages><package name="p"><classes>'
				'<class name="A" filename="A.java"><methods><method name="run"><lines><line number="4" hits="0"/></lines>'
				'</method></methods><lines>'
				'<line number="3" hits="1" branch="true" condition-coverage="50% (1/2)"/><line number="4" hits="0"/>'
				'</lines></class>'
				'<class name="A$Inner" filename="A.java"><lines><line number="4" hits="2"/></lines></class>'
				'</classes></package></packages></coverage>'
			), analyzeAndConvert=True).ToCoverageSummary()

		file = summary.Files["A.java"]
		self.assertEqual([3, 4], [line.LineNumber for line in file.IterateLines()])
		self.assertEqual(2, file.Lines[4].CoverageCount)
		self.assertIs(LineCoverageStatus.Covered, file.Lines[4].Status)
		self.assertIs(LineCoverageStatus.PartiallyCovered, file.Lines[3].Status)

		method = summary.Units["p"].Units["A"].Units["run"]
		self.assertIsInstance(method, Method)
		self.assertEqual((file.Lines[4], file.Lines[4]), (method.StartLine, method.EndLine))
		klass = summary.Units["p"].Units["A"]
		self.assertEqual((file.Lines[3], file.Lines[4]), (klass.StartLine, klass.EndLine))
		self.assertEqual(["A", "A$Inner"], list(summary.Units["p"].Units))


class Schemas(Testcase):
	"""The lenient schema reads what tools write; the strict one is the official DTD's translation."""

	def test_Strict(self) -> None:
		"""coverage.py's extra attribute 'missing-branches' violates the DTD; gcovr's report follows it."""
		strict = XMLSchema(parse(getResourceFile(Resources, STRICT_SCHEMA)))
		lenient = XMLSchema(parse(getResourceFile(Resources, READ_SCHEMA)))

		for report, valid in ((DATA / "Python" / "coverage.xml", False), (DATA / "VHDL" / "Cobertura.xml", True)):
			with self.subTest(report=report.parent.name):
				self.assertEqual(valid, strict.validate(parse(report)))
				self.assertTrue(lenient.validate(parse(report)))

	def test_RootElement(self) -> None:
		with TemporaryDirectory() as directory:
			xmlFile = _write(directory, "<testsuites/>")

			with self.assertRaises(CodeCoverageError) as context:
				_ = Document(xmlFile, analyzeAndConvert=True)

		self.assertEqual(f"Root element of '{xmlFile}' is not '<coverage>'.", str(context.exception))
		self.assertEqual(["Got root element '<testsuites>'."], context.exception.__notes__)

	def test_Invalid(self) -> None:
		"""A line without hits violates the lenient schema too."""
		with TemporaryDirectory() as directory:
			xmlFile = _write(directory,
				'<coverage><packages><package name="p"><classes><class filename="a.c"><lines>'
				'<line number="1"/></lines></class></classes></package></packages></coverage>'
			)

			with self.assertRaises(CodeCoverageError) as context:
				_ = Document(xmlFile, analyzeAndConvert=True)

		self.assertEqual(f"Validation error for '{xmlFile}' using XSD schema 'Any-Cobertura.xsd'.", str(context.exception))
		self.assertEqual(1, len(context.exception.__notes__))

	def test_Missing(self) -> None:
		with self.assertRaises(CodeCoverageError) as context:
			_ = Document(DATA / "missing.xml", analyzeAndConvert=True)

		self.assertEqual(f"Cobertura report file '{DATA / 'missing.xml'}' does not exist.", str(context.exception))

	def test_NotAnalyzed(self) -> None:
		with self.assertRaises(CodeCoverageError):
			Document(DATA / "VHDL" / "Cobertura.xml").Convert()
