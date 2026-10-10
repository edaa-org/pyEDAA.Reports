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
"""Unit tests of QuestaSim's coverage report XML: its model, its XML schema and the conversion to the common model."""
from pathlib                                             import Path
from tempfile                                            import TemporaryDirectory
from textwrap                                            import dedent

from lxml.etree                                          import fromstring
from pyEDAA.Reports.CodeCoverage                         import CodeCoverageError, LineCoverageStatus
from pyEDAA.Reports.CodeCoverage.Cobertura               import Document as CoberturaDocument
from pyEDAA.Reports.CodeCoverage.QuestaSim               import Document, SCHEMA
from pyEDAA.Reports.CodeCoverage.QuestaSim.Details       import CaseBranch, CaseStatement, IfBranch, IfStatement
from pyEDAA.Reports.CodeCoverage.QuestaSim.Details       import Statement
from pyEDAA.Reports.CodeCoverage.QuestaSim.Elements      import CoverageKind, ReportMode, Statistics, Totals
from pyEDAA.Reports.CodeCoverage.QuestaSim.Scopes        import DesignUnitData, FileData, InstanceData
from pyEDAA.Reports.CodeCoverage.QuestaSim.StateMachines import FSMState, FSMTransition
from pyTooling.Testing                                   import Testcase


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


DATA =   Path(__file__).parent.parent.parent / "data" / "CodeCoverage" / "QuestaSim"  #: Directory of the reports.
REPORT = DATA / "coverage_report_details_bcesf.xml"                                   #: Report of Questa 2026.2.
OSVVM =  Path("../../../../OsvvmLibraries")                                           #: Sources, as Questa saw them.


def _write(directory: str, content: str) -> Path:
	"""
	Write a report file into a directory.

	:param directory: The directory.
	:param content:   The report's text.
	:returns:         The report file.
	"""
	xmlFile = Path(directory) / "coverage_report.xml"
	xmlFile.write_text(dedent(content), encoding="utf-8")
	return xmlFile


def _scope(document: Document, path: str) -> InstanceData:
	"""
	Return an instance of a report by its path.

	:param document: The report.
	:param path:     The instance's path.
	:returns:        The instance.
	"""
	return next(scope for scope in document.Scopes if scope.Path == path)


class FormatModel(Testcase):
	"""The report of Questa 2026.2 (``vcover report -xml -details -code bcesf``), read into the format's model."""

	@classmethod
	def setUpClass(cls) -> None:
		"""Read the report once."""
		cls.report = Document(REPORT, analyzeAndConvert=True)

	def test_Report(self) -> None:
		self.assertEqual("2026.2", self.report.ToolVersion)
		self.assertTrue(self.report.Command.startswith("vcover report -xml -details -code bcesf -output "))
		self.assertIs(ReportMode.ByInstance, self.report.Mode)
		self.assertTrue(self.report.HasLineDetails)
		self.assertEqual({}, self.report.Totals)
		self.assertEqual(62, len(self.report.Scopes))
		self.assertTrue(all(isinstance(scope, InstanceData) for scope in self.report.Scopes))

	def test_Instance(self) -> None:
		instance = _scope(self.report, "/tbaxi4memory/Axi4PassThru_1")

		self.assertEqual(("axi4passthru", "feedthru"), (instance.DesignUnit, instance.SecondaryUnit))
		self.assertIs(self.report, instance.Parent)
		self.assertEqual({0: OSVVM / "AXI4/Axi4/src/Axi4PassThru.vhd"}, instance.Files)
		statements = instance.Statistics[CoverageKind.Statements]
		self.assertEqual((45, 45, 100.0), (statements.Active, statements.Hits, statements.Percent))
		self.assertEqual(45, len(instance.Statements))
		self.assertEqual([], instance.IfStatements)

	def test_Package(self) -> None:
		"""A package has no secondary unit."""
		package = _scope(self.report, "/ifelsepkg")

		self.assertEqual("ifelsepkg", package.DesignUnit)
		self.assertIsNone(package.SecondaryUnit)

	def test_TwoFiles(self) -> None:
		"""An architecture and its entity in two files."""
		instance = _scope(self.report, "/tbaxi4memory/Memory_1")

		self.assertEqual(
			{0: OSVVM / "AXI4/Axi4/src/Axi4Memory_a.vhd", 1: OSVVM / "AXI4/Axi4/src/Axi4Memory_e.vhd"},
			instance.Files
		)

	def test_IfStatement(self) -> None:
		ifStatement = _scope(self.report, "/tbaxi4memory/Memory_1").IfStatements[0]

		self.assertTrue(ifStatement.HasElse)
		self.assertEqual(
			[(154, 1, 1, 0), (157, 1, 0, 0)],
			[(branch.LineNumber, branch.Index, branch.TrueCount, branch.FalseCount) for branch in ifStatement.Branches]
		)
		self.assertEqual((1, 1), (ifStatement.TakenBranches, ifStatement.EvaluationCount))
		self.assertEqual(OSVVM / "AXI4/Axi4/src/Axi4Memory_a.vhd", ifStatement.Branches[0].File)

	def test_IfStatement_AllFalse(self) -> None:
		"""An ``if`` without ``else``: its last branch is the implicit AllFalse branch, in the line of the ``if``."""
		instance = _scope(self.report, "/tbaxi4memory/Memory_1")
		ifStatement = next(statement for statement in instance.IfStatements if statement.Branches[0].LineNumber == 554)

		self.assertFalse(ifStatement.HasElse)
		self.assertEqual(
			[(554, 41, 0), (554, 0, 0)], [(b.LineNumber, b.TrueCount, b.FalseCount) for b in ifStatement.Branches]
		)

	def test_CaseStatement(self) -> None:
		caseStatement = _scope(self.report, "/tbaxi4memory/Memory_1").CaseStatements[0]

		self.assertEqual(9, len(caseStatement.Branches))
		branch = caseStatement.Branches[2]
		self.assertEqual((265, 2, 0), (branch.LineNumber, branch.Index, branch.Hits))
		self.assertEqual((1, 2), (caseStatement.TakenBranches, caseStatement.EvaluationCount))

	def test_StateMachine(self) -> None:
		"""UartRx's finite state machine: 6 of 6 states, 7 of 9 transitions; the file is the instance's only file."""
		instance = _scope(self.report, "/tbuart/UartRx_1")

		states, transitions = instance.Statistics[CoverageKind.States], instance.Statistics[CoverageKind.Transitions]
		self.assertEqual((6, 6, 9, 7), (states.Active, states.Hits, transitions.Active, transitions.Hits))
		self.assertEqual(
			["RX_IDLE", "RX_HUNT", "RX_DATA", "RX_PARITY", "RX_STOP", "RX_BREAK"], [state.Name for state in instance.States]
		)
		self.assertEqual(6, sum(1 for state in instance.States if state.Hits > 0))
		self.assertEqual(7, sum(1 for transition in instance.Transitions if transition.Hits > 0))
		transition = instance.Transitions[1]
		self.assertEqual(
			(1, "RX_HUNT", "RX_IDLE", 298, 0),
			(transition.Identifier, transition.FromState, transition.ToState, transition.LineNumber, transition.Hits)
		)
		self.assertEqual(OSVVM / "UART/src/UartRx.vhd", instance.States[0].File)
		self.assertIs(instance, transition.Parent)

	def test_StatisticsMatchItems(self) -> None:
		"""Each instance's statistics are the figures of its coverage items."""
		for instance in self.report.Scopes:
			with self.subTest(instance=instance.Path):
				statements = instance.Statistics[CoverageKind.Statements]
				self.assertEqual(statements.Active, len(instance.Statements))
				self.assertEqual(statements.Hits, sum(1 for statement in instance.Statements if statement.Hits > 0))
				if (branches := instance.Statistics.get(CoverageKind.Branches)) is not None:
					decisions = instance.IfStatements + instance.CaseStatements
					self.assertEqual(branches.Active, sum(len(decision.Branches) for decision in decisions))
					self.assertEqual(branches.Hits, sum(decision.TakenBranches for decision in decisions))

	def test_Totals(self) -> None:
		"""The coverage items of all instances together."""
		scopes = self.report.Scopes
		self.assertEqual(9089, sum(len(scope.Statements) for scope in scopes))
		self.assertEqual(2498, sum(scope.Statistics[CoverageKind.Statements].Hits for scope in scopes))
		self.assertEqual((912, 86), (sum(len(s.IfStatements) for s in scopes), sum(len(s.CaseStatements) for s in scopes)))
		self.assertEqual(9089, len(list(self.report.IterateStatements())))


class Construction(Testcase):
	"""Each class of the format's model checks its parameters: None, then the type, then the value."""

	def _assertRaises(self, create, cases) -> None:
		"""
		Check the exception and its message for each argument list.

		:param create: The class or function to call.
		:param cases:  Tuples of the arguments, the exception type and the message.
		"""
		for args, exceptionType, message in cases:
			with self.subTest(message=message):
				with self.assertRaises(exceptionType) as context:
					create(*args)

				self.assertEqual(message, str(context.exception))

	def test_Statistics(self) -> None:
		statistics = Statistics(CoverageKind.Statements, 4, 3, 75)

		self.assertEqual((4, 3, 75.0), (statistics.Active, statistics.Hits, statistics.Percent))
		self.assertIsInstance(statistics.Percent, float)
		self.assertIsNone(statistics.Parent)

	def test_Statistics_Checks(self) -> None:
		kind = CoverageKind.Statements
		self._assertRaises(Statistics, (
			((None, 4, 3, 75.0),        ValueError, "Parameter 'kind' is None."),
			(("statements", 4, 3, 75.0), TypeError, "Parameter 'kind' is not of type 'CoverageKind'."),
			((kind, None, 3, 75.0),     ValueError, "Parameter 'active' is None."),
			((kind, "4", 3, 75.0),      TypeError,  "Parameter 'active' is not of type 'int'."),
			((kind, -1, 0, 0.0),        ValueError, "Parameter 'active' is negative."),
			((kind, 4, None, 75.0),     ValueError, "Parameter 'hits' is None."),
			((kind, 4, "3", 75.0),      TypeError,  "Parameter 'hits' is not of type 'int'."),
			((kind, 4, 5, 75.0),        ValueError, "Parameter 'hits' is out of range 0..4."),
			((kind, 4, 3, None),        ValueError, "Parameter 'percent' is None."),
			((kind, 4, 3, "75"),        TypeError,  "Parameter 'percent' is not of type 'float' or 'int'."),
			((kind, 4, 3, 100.5),       ValueError, "Parameter 'percent' is out of range 0..100."),
		))

	def test_SourceItem_Checks(self) -> None:
		"""File, line and index - checked alike by statements and branches."""
		file = Path("a.vhdl")
		self._assertRaises(Statement, (
			((None, 1, 1, 0),     ValueError, "Parameter 'file' is None."),
			(("a.vhdl", 1, 1, 0), TypeError,  "Parameter 'file' is not of type 'Path'."),
			((file, None, 1, 0),  ValueError, "Parameter 'lineNumber' is None."),
			((file, "1", 1, 0),   TypeError,  "Parameter 'lineNumber' is not of type 'int'."),
			((file, 0, 1, 0),     ValueError, "Parameter 'lineNumber' is less than 1."),
			((file, 1, None, 0),  ValueError, "Parameter 'index' is None."),
			((file, 1, "1", 0),   TypeError,  "Parameter 'index' is not of type 'int'."),
			((file, 1, 0, 0),     ValueError, "Parameter 'index' is less than 1."),
			((file, 1, 1, None),  ValueError, "Parameter 'hits' is None."),
			((file, 1, 1, "0"),   TypeError,  "Parameter 'hits' is not of type 'int'."),
			((file, 1, 1, -1),    ValueError, "Parameter 'hits' is negative."),
		))

	def test_Branches_Checks(self) -> None:
		file = Path("a.vhdl")
		self._assertRaises(IfStatement, (
			((None, ), ValueError, "Parameter 'hasElse' is None."),
			((1, ),    TypeError,  "Parameter 'hasElse' is not of type 'bool'."),
		))
		self._assertRaises(IfBranch, (
			((file, 1, 1, None, 0), ValueError, "Parameter 'trueCount' is None."),
			((file, 1, 1, "1", 0),  TypeError,  "Parameter 'trueCount' is not of type 'int'."),
			((file, 1, 1, -1, 0),   ValueError, "Parameter 'trueCount' is negative."),
			((file, 1, 1, 0, None), ValueError, "Parameter 'falseCount' is None."),
			((file, 1, 1, 0, "1"),  TypeError,  "Parameter 'falseCount' is not of type 'int'."),
			((file, 1, 1, 0, -1),   ValueError, "Parameter 'falseCount' is negative."),
		))
		self._assertRaises(CaseBranch, (
			((file, 1, 1, None), ValueError, "Parameter 'hits' is None."),
			((file, 1, 1, "1"),  TypeError,  "Parameter 'hits' is not of type 'int'."),
			((file, 1, 1, -1),   ValueError, "Parameter 'hits' is negative."),
		))

	def test_StateMachine_Checks(self) -> None:
		file = Path("a.vhdl")
		self._assertRaises(FSMState, (
			((None, file, 1, 0),   ValueError, "Parameter 'name' is None."),
			((1, file, 1, 0),      TypeError,  "Parameter 'name' is not of type 'str'."),
			(("", file, 1, 0),     ValueError, "Parameter 'name' is empty."),
			(("S", "a.vhdl", 1, 0), TypeError, "Parameter 'file' is not of type 'Path'."),
			(("S", None, None, 0), ValueError, "Parameter 'lineNumber' is None."),
			(("S", None, "1", 0),  TypeError,  "Parameter 'lineNumber' is not of type 'int'."),
			(("S", None, 0, 0),    ValueError, "Parameter 'lineNumber' is less than 1."),
			(("S", None, 1, None), ValueError, "Parameter 'hits' is None."),
			(("S", None, 1, "0"),  TypeError,  "Parameter 'hits' is not of type 'int'."),
			(("S", None, 1, -1),   ValueError, "Parameter 'hits' is negative."),
		))
		self._assertRaises(FSMTransition, (
			((None, "A", "B", None, 1, 0), ValueError, "Parameter 'identifier' is None."),
			(("0", "A", "B", None, 1, 0),  TypeError,  "Parameter 'identifier' is not of type 'int'."),
			((-1, "A", "B", None, 1, 0),   ValueError, "Parameter 'identifier' is negative."),
			((0, None, "B", None, 1, 0),   ValueError, "Parameter 'fromState' is None."),
			((0, 1, "B", None, 1, 0),      TypeError,  "Parameter 'fromState' is not of type 'str'."),
			((0, "", "B", None, 1, 0),     ValueError, "Parameter 'fromState' is empty."),
			((0, "A", None, None, 1, 0),   ValueError, "Parameter 'toState' is None."),
			((0, "A", 1, None, 1, 0),      TypeError,  "Parameter 'toState' is not of type 'str'."),
			((0, "A", "", None, 1, 0),     ValueError, "Parameter 'toState' is empty."),
			((0, "A", "B", "a.v", 1, 0),   TypeError,  "Parameter 'file' is not of type 'Path'."),
			((0, "A", "B", None, 0, 0),    ValueError, "Parameter 'lineNumber' is less than 1."),
			((0, "A", "B", None, 1, -1),   ValueError, "Parameter 'hits' is negative."),
		))

	def test_InstanceData_Checks(self) -> None:
		self._assertRaises(InstanceData, (
			((None, "du"),                       ValueError, "Parameter 'path' is None."),
			((1, "du"),                          TypeError,  "Parameter 'path' is not of type 'str'."),
			(("", "du"),                         ValueError, "Parameter 'path' is empty."),
			(("/tb", None),                      ValueError, "Parameter 'designUnit' is None."),
			(("/tb", 1),                         TypeError,  "Parameter 'designUnit' is not of type 'str'."),
			(("/tb", ""),                        ValueError, "Parameter 'designUnit' is empty."),
			(("/tb", "du", 1),                   TypeError,  "Parameter 'secondaryUnit' is not of type 'str'."),
			(("/tb", "du", ""),                  ValueError, "Parameter 'secondaryUnit' is empty."),
			(("/tb", "du", None, [Path()]),      TypeError,  "Parameter 'files' is not a mapping."),
			(("/tb", "du", None, {"0": Path()}), TypeError,  "Parameter 'files' contains a key not of type 'int'."),
			(("/tb", "du", None, {-1: Path()}),  ValueError, "Parameter 'files' contains a negative key."),
			(("/tb", "du", None, {0: "a.v"}),    TypeError,  "Parameter 'files' contains a value not of type 'Path'."),
		))

	def test_DesignUnitData_Checks(self) -> None:
		self._assertRaises(DesignUnitData, (
			((None, ),   ValueError, "Parameter 'designUnit' is None."),
			((1, ),      TypeError,  "Parameter 'designUnit' is not of type 'str'."),
			(("", ),     ValueError, "Parameter 'designUnit' is empty."),
			(("du", 1),  TypeError,  "Parameter 'secondaryUnit' is not of type 'str'."),
			(("du", ""), ValueError, "Parameter 'secondaryUnit' is empty."),
		))

	def test_FileData_Checks(self) -> None:
		self._assertRaises(FileData, (
			((None, ),  ValueError, "Parameter 'path' is None."),
			(("a.v", ), TypeError,  "Parameter 'path' is not of type 'Path'."),
		))

	def test_Totals_Checks(self) -> None:
		self._assertRaises(Totals, (
			((None, 1),                    ValueError, "Parameter 'mode' is None."),
			(("byFile", 1),                TypeError,  "Parameter 'mode' is not of type 'ReportMode'."),
			((ReportMode.ByDesignUnit, 1), ValueError, "Parameter 'mode' is not 'ByFile' or 'ByInstance'."),
			((ReportMode.ByFile, None),    ValueError, "Parameter 'count' is None."),
			((ReportMode.ByFile, "1"),     TypeError,  "Parameter 'count' is not of type 'int'."),
			((ReportMode.ByFile, -1),      ValueError, "Parameter 'count' is negative."),
		))

	def test_Files_AreCopied(self) -> None:
		files = {0: Path("a.vhdl")}
		instance = InstanceData("/tb", "du", files=files)
		files[1] = Path("b.vhdl")

		self.assertEqual({0: Path("a.vhdl")}, instance.Files)


class ParentRelation(Testcase):
	"""Each element names its parent and is added to it."""

	def test_ByHand(self) -> None:
		report = Document(Path("byHand.xml"))
		totals = Totals(ReportMode.ByInstance, 1, parent=report)
		instance = InstanceData("/tb/dut", "dut", "rtl", {0: Path("dut.vhdl")}, parent=report)
		statistics = Statistics(CoverageKind.Statements, 2, 1, 50.0, parent=instance)
		statement = Statement(Path("dut.vhdl"), 3, 1, 0, parent=instance)
		ifStatement = IfStatement(False, parent=instance)
		ifBranch = IfBranch(Path("dut.vhdl"), 5, 1, 2, 1, parent=ifStatement)
		caseStatement = CaseStatement(parent=instance)
		caseBranch = CaseBranch(Path("dut.vhdl"), 9, 1, 2, parent=caseStatement)
		state = FSMState("IDLE", Path("dut.vhdl"), 12, 1, parent=instance)
		transition = FSMTransition(0, "IDLE", "RUN", Path("dut.vhdl"), 13, 1, parent=instance)

		self.assertEqual({ReportMode.ByInstance: totals}, report.Totals)
		self.assertIs(report, totals.Parent)
		self.assertEqual([instance], report.Scopes)
		self.assertEqual({CoverageKind.Statements: statistics}, instance.Statistics)
		self.assertEqual([statement], instance.Statements)
		self.assertEqual(([ifStatement], [ifBranch]), (instance.IfStatements, ifStatement.Branches))
		self.assertEqual(([caseStatement], [caseBranch]), (instance.CaseStatements, caseStatement.Branches))
		self.assertEqual(([state], [transition]), (instance.States, instance.Transitions))
		self.assertEqual((ifStatement, caseStatement), (ifBranch.Parent, caseBranch.Parent))
		self.assertEqual([statement], list(report.IterateStatements()))

	def test_ParentTypes(self) -> None:
		report = Document(Path("byHand.xml"))
		file = Path("a.v")
		for create, typeName in (
			(lambda: Statistics(CoverageKind.Statements, 1, 1, 100.0, parent=report), "StatisticsMixin"),
			(lambda: Statement(file, 1, 1, 0, parent=report),                         "Scope"),
			(lambda: IfStatement(True, parent=report),                                "Scope"),
			(lambda: IfBranch(file, 1, 1, 0, 0, parent=CaseStatement()),              "IfStatement"),
			(lambda: CaseStatement(parent=report),                                    "Scope"),
			(lambda: CaseBranch(file, 1, 1, 0, parent=IfStatement(True)),             "CaseStatement"),
			(lambda: FSMState("S", None, 1, 0, parent=report),                        "Scope"),
			(lambda: FSMTransition(0, "A", "B", None, 1, 0, parent=report),           "Scope"),
			(lambda: InstanceData("/tb", "du", parent=Totals(ReportMode.ByFile, 0)),  "Report"),
			(lambda: Totals(ReportMode.ByFile, 0, parent=DesignUnitData("du")),       "Report"),
		):
			with self.subTest(typeName=typeName):
				with self.assertRaises(TypeError) as context:
					create()

				self.assertEqual(f"Parameter 'parent' is not of type '{typeName}'.", str(context.exception))

	def test_Duplicates(self) -> None:
		report = Document(Path("byHand.xml"))
		Totals(ReportMode.ByFile, 1, parent=report)
		designUnit = DesignUnitData("du", parent=report)
		Statistics(CoverageKind.Branches, 1, 1, 100.0, parent=designUnit)

		with self.assertRaises(CodeCoverageError) as context:
			Totals(ReportMode.ByFile, 2, parent=report)
		self.assertEqual("Summary record 'byFile' is stated twice.", str(context.exception))

		with self.assertRaises(CodeCoverageError) as context:
			Statistics(CoverageKind.Branches, 2, 1, 50.0, parent=designUnit)
		self.assertEqual("Coverage statistics 'branches' are stated twice.", str(context.exception))


class Parsing(Testcase):
	"""Each class of the format's model parses its XML element."""

	def test_Statistics(self) -> None:
		statistics = Statistics.Parse(fromstring("<toggleSummary active='8' hits='2' percent='25.00'/>"))

		self.assertIs(CoverageKind.Toggles, statistics.Kind)
		self.assertEqual((8, 2, 25.0), (statistics.Active, statistics.Hits, statistics.Percent))

	def test_Statistics_MoreHitsThanItems(self) -> None:
		with self.assertRaises(CodeCoverageError) as context:
			Statistics.Parse(fromstring("<branches active='1' hits='2' percent='100.00'/>"))

		self.assertEqual("Coverage statistics '<branches>' state more hit items than items.", str(context.exception))

	def test_Totals(self) -> None:
		totals = Totals.Parse(
			fromstring("<summaryByFile files='3'><statements active='4' hits='1' percent='25.00'/></summaryByFile>"),
			parent=Document(Path("byHand.xml"))
		)

		self.assertIs(ReportMode.ByFile, totals.Mode)
		self.assertEqual(3, totals.Count)
		self.assertEqual([CoverageKind.Statements], list(totals.Statistics))

	def test_DesignUnitData(self) -> None:
		"""By design unit, as Questa 2023.3 writes it."""
		designUnit = DesignUnitData.Parse(fromstring(
			"<DuData du='uart_core'><sourceTable files='1'><fileMap fn='0' path='/rtl/uart_core.v'/></sourceTable>"
			"<statements active='2' hits='1' percent='50.00'/><stmt fn='0' ln='113' st='1' hits='21'/>"
			"<stmt fn='0' ln='113' st='2' hits='0'/></DuData>"
		))

		self.assertEqual("uart_core", designUnit.DesignUnit)
		self.assertIsNone(designUnit.SecondaryUnit)
		self.assertEqual([(113, 1, 21), (113, 2, 0)], [(s.LineNumber, s.Index, s.Hits) for s in designUnit.Statements])

	def test_FileData(self) -> None:
		"""A coverage item without file number is in the file of its ``<fileData>``."""
		fileData = FileData.Parse(fromstring("<fileData path='src/a.vhdl'><stmt ln='4' st='1' hits='2'/></fileData>"))

		self.assertEqual(Path("src/a.vhdl"), fileData.Path)
		self.assertEqual(Path("src/a.vhdl"), fileData.Statements[0].File)

	def test_SingleFile(self) -> None:
		"""A coverage item without file number is in the only file of its scope's source table."""
		instance = InstanceData.Parse(fromstring(
			"<instanceData path='/tb' du='tb'><sourceTable files='1'><fileMap fn='4' path='tb.vhdl'/></sourceTable>"
			"<stmt ln='9' st='1' hits='1'/></instanceData>"
		))

		self.assertEqual(Path("tb.vhdl"), instance.Statements[0].File)

	def test_UnknownFile(self) -> None:
		for xml, message in (
			("<instanceData path='/tb' du='tb'><stmt fn='1' ln='9' st='1' hits='1'/></instanceData>",
			 "'<stmt>' in line 1 names file number '1', which is unknown."),
			("<instanceData path='/tb' du='tb'><sourceTable files='2'><fileMap fn='0' path='a.v'/>"
			 "<fileMap fn='1' path='b.v'/></sourceTable><stmt ln='9' st='1' hits='1'/></instanceData>",
			 "'<stmt>' in line 1 names no file number."),
		):
			with self.subTest(message=message):
				with self.assertRaises(CodeCoverageError) as context:
					InstanceData.Parse(fromstring(xml))

				self.assertEqual(message, str(context.exception))

	def test_Branches(self) -> None:
		instance = InstanceData.Parse(fromstring(
			"<instanceData path='/tb' du='tb'><sourceTable files='1'><fileMap fn='0' path='tb.vhdl'/></sourceTable>"
			"<if active='2' hits='1' percent='50.00' hasElse='0'><ielem fn='0' ln='5' st='1' true='3' false='0'/>"
			"<ielem fn='0' ln='5' st='1' true='0' false='0'/></if>"
			"<case active='2' hits='2' percent='100.00'><celem fn='0' ln='8' st='1' hits='1'/>"
			"<celem fn='0' ln='9' st='1' hits='4'/></case></instanceData>"
		))

		ifStatement, caseStatement = instance.IfStatements[0], instance.CaseStatements[0]
		self.assertFalse(ifStatement.HasElse)
		self.assertEqual([(5, 3), (5, 0)], [(branch.LineNumber, branch.TrueCount) for branch in ifStatement.Branches])
		self.assertEqual(Path("tb.vhdl"), ifStatement.Branches[0].File)
		self.assertEqual([(8, 1), (9, 4)], [(branch.LineNumber, branch.Hits) for branch in caseStatement.Branches])
		self.assertEqual(5, caseStatement.EvaluationCount)

	def test_Branches_Figures(self) -> None:
		"""An ``if`` or ``case`` statement's figures must be its branches'."""
		for xml, message in (
			("<if active='2' hits='2' percent='100.00' hasElse='1'><ielem fn='0' ln='5' st='1' true='3' false='0'/>"
			 "<ielem fn='0' ln='6' st='1' true='0' false='0'/></if>",
			 "'<if>' in line 1 states other figures than its branches have."),
			("<case active='3' hits='1' percent='33.33'><celem fn='0' ln='8' st='1' hits='1'/></case>",
			 "'<case>' in line 1 states other figures than its branches have."),
		):
			with self.subTest(message=message):
				instance = InstanceData("/tb", "tb", files={0: Path("tb.vhdl")})
				parse = IfStatement.Parse if xml.startswith("<if") else CaseStatement.Parse
				with self.assertRaises(CodeCoverageError) as context:
					parse(fromstring(xml), parent=instance)

				self.assertEqual(message, str(context.exception))

	def test_StateMachine(self) -> None:
		"""A state and a transition name no file number: the scope's file, if it has one, else unknown."""
		for files, file in (({0: Path("fsm.vhdl")}, Path("fsm.vhdl")), ({0: Path("a.v"), 1: Path("b.v")}, None)):
			with self.subTest(files=len(files)):
				instance = InstanceData("/tb", "tb", files=files)
				state = FSMState.Parse(fromstring("<state ln='3' hits='2' state='IDLE'/>"), parent=instance)
				transition = FSMTransition.Parse(
					fromstring("<trans ln='4' tid='0' hits='1' state='IDLE -> RUN'/>"), parent=instance
				)

				self.assertEqual(("IDLE", 3, 2, file), (state.Name, state.LineNumber, state.Hits, state.File))
				self.assertEqual(("IDLE", "RUN", file), (transition.FromState, transition.ToState, transition.File))

	def test_Transition_States(self) -> None:
		instance = InstanceData("/tb", "tb")
		with self.assertRaises(CodeCoverageError) as context:
			FSMTransition.Parse(fromstring("<trans ln='4' tid='0' hits='1' state='IDLE'/>"), parent=instance)

		self.assertEqual("'<trans>' in line 1 doesn't name the states it connects.", str(context.exception))


class Schema(Testcase):
	"""The report's root element and the XML schema reject what QuestaSim doesn't write."""

	def _assertRejected(self, content: str, message: str) -> CodeCoverageError:
		"""
		Read a report and check the error's message.

		:param content: The report's text.
		:param message: The expected message, with ``{file}`` for the report's path.
		:returns:       The error.
		"""
		with TemporaryDirectory() as directory:
			xmlFile = _write(directory, content)
			with self.assertRaises(CodeCoverageError) as context:
				Document(xmlFile, analyzeAndConvert=True)

			self.assertEqual(message.format(file=xmlFile), str(context.exception))
			return context.exception

	def test_RootElement(self) -> None:
		self._assertRejected("<?xml version='1.0'?><ucdb/>", "Root element of '{file}' is not '<coverage_report>'.")

	def test_FunctionalCoverage(self) -> None:
		self._assertRejected(
			"<coverage_report><functional_coverage_report/></coverage_report>",
			"'{file}' is a functional coverage report, not a code coverage report."
		)

	def test_Invalid(self) -> None:
		stats = "<states active='1' hits='1' percent='100.00'/><transitions active='1' hits='0' percent='0.00'/>"
		table = "<sourceTable files='1'><fileMap fn='0' path='a.v'/></sourceTable>"
		for name, content in (
			("unknown element",     "<lines active='1' hits='1' percent='100'/>"),
			("percent > 100",       "<branches active='1' hits='1' percent='100.01'/>"),
			("negative hits",       "<stmt ln='1' st='1' hits='-1'/>"),
			("line 0",              "<stmt ln='0' st='1' hits='1'/>"),
			("file number",         table + "<stmt fn='1' ln='1' st='1' hits='1'/>"),
			("source table later",  "<branches active='1' hits='1' percent='100'/>" + table),
			("state before states", "<state ln='3' hits='1' state='IDLE'/>" + stats),
			("negative tid",        stats + "<trans ln='3' tid='-1' hits='0' state='A -> B'/>"),
			("trans before state",  stats + "<trans ln='3' tid='0' hits='0' state='A -> B'/><state ln='2' hits='1'/>"),
			("ielem without true",  "<if active='1' hits='0' percent='0.00' hasElse='1'><ielem ln='2' st='1'/></if>"),
		):
			with self.subTest(name=name):
				exception = self._assertRejected(
					f"<coverage_report><code_coverage_report byInstance='1'><instanceData path='/tb' du='tb'>{content}"
					f"</instanceData></code_coverage_report></coverage_report>",
					f"Validation error for '{{file}}' using XSD schema '{SCHEMA}'."
				)
				self.assertNotEqual([], exception.__notes__)

	def test_UnknownAttribute(self) -> None:
		self._assertRejected(
			"<coverage_report><code_coverage_report byInstance='1'><instanceData path='/tb' du='tb' lib='work'/>"
			"</code_coverage_report></coverage_report>",
			f"Validation error for '{{file}}' using XSD schema '{SCHEMA}'."
		)

	def test_Mode(self) -> None:
		for attributes, note in (("", "Got modes: none."), (" byDU='1' byInstance='1'", "Got modes: byInstance, byDU.")):
			with self.subTest(attributes=attributes):
				exception = self._assertRejected(
					f"<coverage_report><code_coverage_report{attributes}/></coverage_report>",
					"QuestaSim coverage report '{file}' doesn't state exactly one mode."
				)
				self.assertEqual(note, exception.__notes__[0])

	def test_MissingFile(self) -> None:
		with self.assertRaises(CodeCoverageError) as context:
			Document(DATA / "missing.xml", analyzeAndConvert=True)

		self.assertEqual(f"QuestaSim coverage report '{DATA / 'missing.xml'}' does not exist.", str(context.exception))

	def test_SyntaxError(self) -> None:
		self._assertRejected("<coverage_report>", "XML syntax error in QuestaSim coverage report '{file}'.")

	def test_ConvertBeforeAnalyze(self) -> None:
		with self.assertRaises(CodeCoverageError) as context:
			Document(REPORT).Convert()

		self.assertEqual(
			f"QuestaSim coverage report '{REPORT}' needs to be read and analyzed by an XML parser.", str(context.exception)
		)


class Conversion(Testcase):
	"""The statements and branches, converted to lines of the common model."""

	@classmethod
	def setUpClass(cls) -> None:
		"""Read and convert the report once."""
		cls.summary = Document(REPORT, analyzeAndConvert=True).ToCoverageSummary()

	def _file(self, name: str):
		"""
		Return a file of the converted report by its name.

		:param name: The file's name.
		:returns:    The file.
		"""
		return next(file for file in self.summary.IterateFiles() if file.Path.name == name)

	def test_Totals(self) -> None:
		self.assertEqual("coverage_report_details_bcesf", self.summary.Name)
		self.assertEqual(62, len(list(self.summary.IterateFiles())))
		self.assertEqual((9698, 2782), (self.summary.TotalLines, self.summary.CoveredLines))
		self.assertEqual((2744, 587), (self.summary.TotalBranches, self.summary.CoveredBranches))

	def test_RelativePaths(self) -> None:
		"""File paths stay as Questa saw them, relative to where it ran."""
		self.assertEqual(OSVVM / "UART/src/UartRx.vhd", self._file("UartRx.vhd").Path)

	def test_File(self) -> None:
		passThru, uartRx = self._file("Axi4PassThru.vhd"), self._file("UartRx.vhd")

		self.assertEqual((45, 45, 0), (passThru.TotalLines, passThru.CoveredLines, passThru.TotalBranches))
		self.assertEqual((95, 82), (uartRx.TotalLines, uartRx.CoveredLines))
		self.assertEqual((62, 46), (uartRx.TotalBranches, uartRx.CoveredBranches))

	def test_IfLine(self) -> None:
		"""An ``if`` with ``else``: both branches on the line of the ``if``; the line ran as often as it was evaluated."""
		line = next(line for line in self._file("Axi4Memory_a.vhd").IterateLines() if line.LineNumber == 154)

		self.assertEqual((LineCoverageStatus.PartiallyCovered, 1), (line.Status, line.CoverageCount))
		self.assertEqual([(LineCoverageStatus.Covered, 1), (LineCoverageStatus.Uncovered, 0)],
		                 [(branch.Status, branch.CoverageCount) for branch in line.Branches])

	def test_AllFalseBranch(self) -> None:
		"""An ``if`` without ``else``: the AllFalse branch, never taken, is the line's second branch."""
		line = next(line for line in self._file("Axi4Memory_a.vhd").IterateLines() if line.LineNumber == 554)

		self.assertEqual((LineCoverageStatus.PartiallyCovered, 41), (line.Status, line.CoverageCount))
		self.assertEqual([41, 0], [branch.CoverageCount for branch in line.Branches])

	def test_Merged(self) -> None:
		"""Two instances of one design unit: their statements and branches are summed."""
		instance = (
			"<instanceData path='/tb/c{0}' du='counter' sec='rtl'><sourceTable files='1'><fileMap fn='0' path='c.vhdl'/>"
			"</sourceTable><branches active='2' hits='1' percent='50.00'/><if active='2' hits='1' percent='50.00' "
			"hasElse='1'><ielem fn='0' ln='5' st='1' true='{1}' false='0'/><ielem fn='0' ln='7' st='1' true='0' "
			"false='0'/></if><statements active='1' hits='1' percent='100.00'/><stmt fn='0' ln='6' st='1' hits='{1}'/>"
			"</instanceData>"
		)
		with TemporaryDirectory() as directory:
			xmlFile = _write(
				directory,
				f"<coverage_report><code_coverage_report lines='1' byInstance='1'>{instance.format(1, 3)}"
				f"{instance.format(2, 4)}</code_coverage_report></coverage_report>"
			)
			summary = Document(xmlFile, analyzeAndConvert=True).ToCoverageSummary()

		lines = {line.LineNumber: line for line in next(summary.IterateFiles()).IterateLines()}
		self.assertEqual(7, lines[6].CoverageCount)
		self.assertEqual([7, 0], [branch.CoverageCount for branch in lines[5].Branches])

	def test_NoDetails(self) -> None:
		"""A report without details has no statements to convert; the note says how to write one."""
		with TemporaryDirectory() as directory:
			xmlFile = _write(
				directory,
				"<coverage_report><code_coverage_report byInstance='1'><instanceData path='/tb' du='tb'>"
				"<statements active='4' hits='4' percent='100.00'/></instanceData></code_coverage_report></coverage_report>"
			)
			with self.assertRaises(CodeCoverageError) as context:
				Document(xmlFile, analyzeAndConvert=True).ToCoverageSummary()

		self.assertEqual(f"QuestaSim coverage report '{xmlFile}' has no statements to convert.", str(context.exception))
		self.assertEqual(["Write the report with details: 'vcover report -xml -details ...'."], context.exception.__notes__)

	def test_Cobertura(self) -> None:
		"""The converted report, written as Cobertura XML and read back, has the same figures."""
		with TemporaryDirectory() as directory:
			coberturaFile = Path(directory) / "coverage.xml"
			CoberturaDocument.FromCoverageSummary(coberturaFile, self.summary).Write(regenerate=True)
			reread = CoberturaDocument(coberturaFile, analyzeAndConvert=True).ToCoverageSummary()

		self.assertEqual(
			(self.summary.TotalLines, self.summary.CoveredLines, self.summary.TotalBranches, self.summary.CoveredBranches),
			(reread.TotalLines, reread.CoveredLines, reread.TotalBranches, reread.CoveredBranches)
		)
