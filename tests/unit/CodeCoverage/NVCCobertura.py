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
"""Unit tests of NVC's Cobertura dialect: its model, its schema and the conversion to the common model."""
from pathlib                                            import Path
from tempfile                                           import TemporaryDirectory
from textwrap                                           import dedent

from lxml.etree                                         import XMLSchema, parse
from pyTooling.Common                                   import getResourceFile

from pyEDAA.Reports                                     import Resources
from pyEDAA.Reports.CodeCoverage                        import CodeCoverageError, LineCoverageStatus, Module, Package
from pyEDAA.Reports.CodeCoverage.Cobertura              import READ_SCHEMA as ANY_SCHEMA, Document as AnyDocument
from pyEDAA.Reports.CodeCoverage.Cobertura.NVCCobertura import READ_SCHEMA, Class, Document
from pyTooling.Testing                                  import Testcase


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


DATA =   Path(__file__).parent.parent.parent / "data" / "CodeCoverage"  #: Directory of the reports and their sources.
NVC =    DATA / "NVC"                                                   #: Directory of NVC's reports and their sources.
REPORT = NVC / "Count.xml"                                              #: Statement and branch coverage of one run.

#: A report of NVC 1.23.0, the root's attributes wrapped: an entity with a statement in line 5 and two architectures in
#: lines 8 to 15 of one file, each instantiated once.
ENTITY_REPORT = dedent("""\
	<?xml version='1.0' encoding='UTF-8'?>
	<!DOCTYPE coverage SYSTEM 'http://cobertura.sourceforge.net/xml/coverage-04.dtd'>
	<coverage version="nvc 1.23.0" line-rate="1.000000" branch-rate="1.000000" complexity="0.0" lines-valid="5"
	          lines-covered="5" branches-valid="2" branches-covered="2" timestamp="1791500000">
	<sources>
	<source>.</source>
	</sources>
	<packages>
	<package name="WORK" line-rate="1.000000" branch-rate="1.000000" complexity="0.0">
	<classes>
	<class name="UNIT(TWO)" filename="Unit.vhdl" line-rate="1.000000" branch-rate="1.000000" complexity="0.0" >
	<methods/>
	<lines>
	<line number="5" hits="4" branch="true" condition-coverage="100 %">
	<conditions>
	<condition number="0" type="jump" coverage="100 %"/>
	</conditions>
	</line>
	<line number="14" hits="3" branch="false"/>
	</lines>
	</class>
	<class name="UNIT(ONE)" filename="Unit.vhdl" line-rate="1.000000" branch-rate="1.000000" complexity="0.0" >
	<methods/>
	<lines>
	<line number="5" hits="4" branch="true" condition-coverage="100 %">
	<conditions>
	<condition number="0" type="jump" coverage="100 %"/>
	</conditions>
	</line>
	<line number="10" hits="3" branch="false"/>
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
	"""The format's model keeps what the report states, and a class' entity and architecture."""

	def test_Report(self) -> None:
		report = Document(REPORT, analyzeAndConvert=True)

		self.assertEqual(("nvc 1.23.0", "1791499953"), (report.Version, report.Timestamp))
		self.assertEqual(
			(32, 22, 11, 4), (report.LinesValid, report.LinesCovered, report.BranchesValid, report.BranchesCovered)
		)
		self.assertEqual((0.6875, 0.363636, 0.0), (report.LineRate, report.BranchRate, report.Complexity))
		self.assertEqual(["."], report.Sources)
		self.assertEqual(["WORK"], [package.Name for package in report.Packages])

		counter, testbench = report.Packages[0].Classes
		self.assertIsInstance(counter, Class)
		self.assertEqual(
			("COUNTER(RTL)", "COUNTER", "RTL", "src/Counter.vhdl", {}),
			(counter.Name, counter.Entity, counter.Architecture, counter.Filename, counter.Methods)
		)
		self.assertEqual(
			("COUNTER_TB(SIM)", "COUNTER_TB", "SIM", "tb/Counter_tb.vhdl"),
			(testbench.Name, testbench.Entity, testbench.Architecture, testbench.Filename)
		)
		self.assertEqual((0.526316, 0.25, 0.0), (counter.LineRate, counter.BranchRate, counter.Complexity))

	def test_Lines(self) -> None:
		"""A branching line has one condition: its taken and all branches are figured from the percentage."""
		lines = Document(REPORT, analyzeAndConvert=True).Packages[0].Classes[0].Lines

		for number, hits, branch, conditionCoverage, coverage in (
			(29, 86, True,  (2, 2), "100 %"),
			(30, 42, True,  (1, 2), "50 %"),
			(32,  0, True,  (1, 2), "50 %"),
			(35,  0, True,  (0, 2), "0 %"),
			(31,  0, False, None,   None),
			(36, 20, False, None,   None)
		):
			with self.subTest(line=number):
				line = lines[number]
				self.assertEqual((hits, branch, conditionCoverage), (line.Hits, line.Branch, line.ConditionCoverage))
				self.assertEqual(
					[] if coverage is None else [(0, "jump", coverage)],
					[(condition.Number, condition.Type, condition.Coverage) for condition in line.Conditions]
				)

	def test_Class(self) -> None:
		klass = Class("COUNTER", "RTL", "src/Counter.vhdl", 0.5, 0.25, 0.0)

		self.assertEqual(("COUNTER(RTL)", "COUNTER", "RTL"), (klass.Name, klass.Entity, klass.Architecture))
		self.assertEqual(("src/Counter.vhdl", 0.5, 0.25, 0.0), (
			klass.Filename, klass.LineRate, klass.BranchRate, klass.Complexity
		))
		self.assertEqual(({}, {}), (klass.Methods, klass.Lines))

	def test_Class_Invalid(self) -> None:
		for entity, architecture, exceptionType, message in (
			(None,      "RTL", ValueError, "Parameter 'entity' is None."),
			(1,         "RTL", TypeError,  "Parameter 'entity' is not of type 'str'."),
			("",        "RTL", ValueError, "Parameter 'entity' is empty."),
			("COUNTER", None,  ValueError, "Parameter 'architecture' is None."),
			("COUNTER", 1,     TypeError,  "Parameter 'architecture' is not of type 'str'."),
			("COUNTER", "",    ValueError, "Parameter 'architecture' is empty.")
		):
			with self.subTest(message=message):
				with self.assertRaises(exceptionType) as context:
					_ = Class(entity, architecture, "src/Counter.vhdl")

				self.assertEqual(message, str(context.exception))


class Conversion(Testcase):
	"""The conversion to the common model: counted lines, two branches per condition, and design units as units."""

	def test_Totals(self) -> None:
		"""Two branches per branching line; a line without a statement, which took a branch, is covered."""
		report = Document(REPORT, analyzeAndConvert=True)
		summary = report.ToCoverageSummary()

		self.assertEqual((32, 24, 22, 12, 4), (
			summary.TotalLines, summary.CoveredLines, summary.TotalBranches, summary.CoveredBranches, summary.PartialLines
		))
		self.assertEqual(report.LinesValid, summary.TotalLines)
		self.assertEqual(2 * report.BranchesValid, summary.TotalBranches)

	def test_Lines(self) -> None:
		summary = Document(REPORT, analyzeAndConvert=True).ToCoverageSummary()
		counter = summary.Directories["src"].Files["Counter.vhdl"]

		Covered, Partial, Uncovered = (
			LineCoverageStatus.Covered, LineCoverageStatus.PartiallyCovered, LineCoverageStatus.Uncovered
		)
		for number, status, count, branches in (
			(29, Covered,   86,   [Covered, Covered]),      # if rising_edge(Clock)
			(30, Partial,   42,   [Covered, Uncovered]),    # if Reset = '1': never true
			(32, Partial,   None, [Covered, Uncovered]),    # elsif: no statement
			(35, Uncovered, 0,    [Uncovered, Uncovered]),  # when "00": a choice is always '0 %'
			(36, Covered,   20,   []),
			(59, Uncovered, 0,    [])                       # report of the process never reached
		):
			with self.subTest(line=number):
				line = counter.Lines[number]
				self.assertEqual((status, count), (line.Status, line.CoverageCount))
				self.assertEqual(branches, [branch.Status for branch in line.Branches])
				self.assertEqual([None] * len(branches), [branch.CoverageCount for branch in line.Branches])

	def test_Merged(self) -> None:
		"""A report of two merged runs adds their hits."""
		count, reset, merged = (
			Document(NVC / f"{name}.xml", analyzeAndConvert=True).Packages[0].Classes for name in ("Count", "Reset", "Merged")
		)

		for first, second, both in zip(count, reset, merged):
			with self.subTest(design=both.Name):
				self.assertEqual((first.Name, second.Name), (both.Name, both.Name))
				self.assertEqual(
					{number: line.Hits + second.Lines[number].Hits for number, line in first.Lines.items()},
					{number: line.Hits for number, line in both.Lines.items()}
				)

		summary = Document(NVC / "Merged.xml", analyzeAndConvert=True).ToCoverageSummary()
		line = summary.Directories["src"].Files["Counter.vhdl"].Lines[30]
		self.assertEqual((LineCoverageStatus.Covered, 60, 2), (line.Status, line.CoverageCount, line.CoveredBranches))

	def test_Entity(self) -> None:
		"""An entity's statement is listed in the class of each architecture: one line, its hits added."""
		with TemporaryDirectory() as directory:
			summary = Document(_write(directory, ENTITY_REPORT), analyzeAndConvert=True).ToCoverageSummary()

		file = summary.Files["Unit.vhdl"]
		self.assertEqual((8, 2), (file.Lines[5].CoverageCount, len(file.Lines[5].Branches)))
		self.assertEqual((3, 2, 2), (summary.TotalLines, summary.TotalBranches, summary.CoveredBranches))

		units = {unit.QualifiedName: unit for unit in summary.IterateUnits()}
		self.assertEqual(["WORK", "WORK.UNIT", "WORK.UNIT.ONE", "WORK.UNIT.TWO"], list(units))
		self.assertEqual(
			(5, 14), (units["WORK.UNIT.TWO"].StartLine.LineNumber, units["WORK.UNIT.TWO"].EndLine.LineNumber)
		)

	def test_Units(self) -> None:
		"""The library becomes a package, an entity a module, its architecture a module spanning its listed lines."""
		summary = Document(REPORT, analyzeAndConvert=True).ToCoverageSummary()

		units = {unit.QualifiedName: unit for unit in summary.IterateUnits()}
		self.assertEqual(
			["WORK", "WORK.COUNTER", "WORK.COUNTER.RTL", "WORK.COUNTER_TB", "WORK.COUNTER_TB.SIM"], list(units)
		)
		for name, unitClass in (("WORK", Package), ("WORK.COUNTER", Module), ("WORK.COUNTER.RTL", Module)):
			with self.subTest(name=name):
				self.assertIsInstance(units[name], unitClass)

		rtl = units["WORK.COUNTER.RTL"]
		self.assertIs(summary.Directories["src"].Files["Counter.vhdl"], rtl.File)
		self.assertEqual((29, 59), (rtl.StartLine.LineNumber, rtl.EndLine.LineNumber))
		self.assertEqual((19, 12, 16, 7), (rtl.TotalLines, rtl.CoveredLines, rtl.TotalBranches, rtl.CoveredBranches))
		self.assertIsNone(units["WORK.COUNTER"].File)

	def test_BranchOnly(self) -> None:
		"""Measured with branch coverage alone, no line has hits: a line, which took a branch, has no count."""
		summary = Document(NVC / "Branch.xml", analyzeAndConvert=True).ToCoverageSummary()

		self.assertEqual((11, 8, 22, 12), (
			summary.TotalLines, summary.CoveredLines, summary.TotalBranches, summary.CoveredBranches
		))
		for file in summary.IterateFiles():
			for line in file.IterateLines():
				with self.subTest(file=file.Name, line=line.LineNumber):
					self.assertEqual(0 if line.Status is LineCoverageStatus.Uncovered else None, line.CoverageCount)

	def test_OtherKinds(self) -> None:
		"""Expression, toggle, FSM state and functional coverage add uncovered lines without branches."""
		for name, lineCount in (("Expression", 6), ("Toggle", 14), ("FSMState", 1), ("Functional", 1)):
			with self.subTest(kind=name):
				summary = Document(NVC / f"{name}.xml", analyzeAndConvert=True).ToCoverageSummary()

				self.assertEqual((lineCount, 0, 0), (summary.TotalLines, summary.CoveredLines, summary.TotalBranches))


class Schema(Testcase):
	"""The reverse-engineered schema accepts what NVC writes and rejects what it doesn't."""

	def test_Schemas(self) -> None:
		"""NVC's reports are valid for the dialect, coverage.py's and gcovr's aren't."""
		strict = XMLSchema(parse(getResourceFile(Resources, READ_SCHEMA)))

		for report, valid in (
			*((report, True) for report in sorted(NVC.glob("*.xml"))),
			(DATA / "Python" / "coverage.xml", False),
			(DATA / "VHDL" / "Cobertura.xml", False)
		):
			with self.subTest(report=report.name):
				self.assertEqual(valid, strict.validate(parse(report)))

	def test_GenericReader(self) -> None:
		"""The generic reader rejects a report of NVC with branch coverage: its 'condition-coverage' is a percentage."""
		lenient = XMLSchema(parse(getResourceFile(Resources, ANY_SCHEMA)))
		self.assertFalse(lenient.validate(parse(REPORT)))
		self.assertTrue(lenient.validate(parse(NVC / "Toggle.xml")))

		with self.assertRaises(CodeCoverageError) as context:
			_ = AnyDocument(REPORT, analyzeAndConvert=True)

		self.assertEqual(f"Validation error for '{REPORT}' using XSD schema 'Any-Cobertura.xsd'.", str(context.exception))

	def test_Invalid(self) -> None:
		"""Another percentage, rate, version, timestamp, complexity, source, method or condition isn't what NVC writes."""
		original = REPORT.read_text(encoding="utf-8")
		for name, old, new in (
			("Percentage", 'condition-coverage="50 %"', 'condition-coverage="50% (1/2)"'),
			("Coverage",   'coverage="50 %"/>', 'coverage="25 %"/>'),
			("Rate",       'line-rate="0.687500"', 'line-rate="0.6875"'),
			("Version",    'version="nvc 1.23.0"', 'version="7.16.1"'),
			("Timestamp",  'timestamp="1791499953"', 'timestamp="1791499953000"'),
			("Complexity", 'complexity="0.0" lines-valid', 'complexity="0" lines-valid'),
			("Source",     "<source>.</source>", "<source>src</source>"),
			("Method",     "<methods/>", '<methods><method name="f" signature=""><lines/></method></methods>'),
			("Condition",  '<condition number="0"', '<condition number="1"'),
			("Branch",     '<line number="31" hits="0" branch="false"/>', '<line number="31" hits="0"/>'),
			("Attribute",  '<line number="31" hits="0"', '<line number="31" hits="0" missing-branches="32"'),
			("Name",       'name="COUNTER(RTL)"', 'name="COUNTER"')
		):
			with self.subTest(name=name), TemporaryDirectory() as directory:
				self.assertIn(old, original)
				xmlFile = _write(directory, original.replace(old, new, 1))

				with self.assertRaises(CodeCoverageError) as context:
					_ = Document(xmlFile, analyzeAndConvert=True)

				self.assertEqual(
					f"Validation error for '{xmlFile}' using XSD schema 'NVC-Cobertura.xsd'.", str(context.exception)
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
			_ = Document(NVC / "missing.xml", analyzeAndConvert=True)

		self.assertEqual(f"Cobertura report file '{NVC / 'missing.xml'}' does not exist.", str(context.exception))

	def test_Unreadable(self) -> None:
		"""A directory can't be read as a file."""
		with self.assertRaises(CodeCoverageError) as context:
			_ = Document(NVC, analyzeAndConvert=True)

		self.assertEqual(f"Couldn't read Cobertura report file '{NVC}'.", str(context.exception))
		self.assertIsInstance(context.exception.__cause__, OSError)

	def test_NotAnalyzed(self) -> None:
		with self.assertRaises(CodeCoverageError):
			Document(REPORT).Convert()
