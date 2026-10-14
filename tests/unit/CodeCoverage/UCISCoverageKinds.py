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
"""Unit tests of the UCIS XML interchange format's coverage kinds beside code coverage: toggles, conditions, FSMs,
assertions and covergroups - kept in the format's model."""
from pathlib                                       import Path
from tempfile                                      import TemporaryDirectory

from pyEDAA.Reports.CodeCoverage                   import CodeCoverageError
from pyEDAA.Reports.CodeCoverage.UCIS              import Document
from pyEDAA.Reports.CodeCoverage.UCIS.Assertions   import Assertion, AssertionBinKind, AssertionCoverage
from pyEDAA.Reports.CodeCoverage.UCIS.Bins         import Bin, BinContents
from pyEDAA.Reports.CodeCoverage.UCIS.Conditions   import ConditionCoverage, Expression
from pyEDAA.Reports.CodeCoverage.UCIS.CoverOptions import CovergroupOptions, CoverpointOptions, CrossOptions
from pyEDAA.Reports.CodeCoverage.UCIS.Covergroups  import CovergroupCoverage, CovergroupID, CovergroupInstance
from pyEDAA.Reports.CodeCoverage.UCIS.Coverpoints  import Coverpoint, CoverpointBin, ValueRange, ValueSequence
from pyEDAA.Reports.CodeCoverage.UCIS.Crosses      import Cross, CrossBin
from pyEDAA.Reports.CodeCoverage.UCIS.Elements     import StatementID
from pyEDAA.Reports.CodeCoverage.UCIS.FSMs         import FSM, FSMCoverage, FSMState, FSMTransition
from pyEDAA.Reports.CodeCoverage.UCIS.Instances    import InstanceCoverage
from pyEDAA.Reports.CodeCoverage.UCIS.PyUCIS       import Document as PyUCISDocument
from pyEDAA.Reports.CodeCoverage.UCIS.ToggleBits   import Toggle, ToggleBit
from pyEDAA.Reports.CodeCoverage.UCIS.Toggles      import Dimension, MetricMode, ToggleCoverage, ToggleObject
from pyTooling.Testing                             import Testcase


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


DATA =       Path(__file__).parent.parent.parent / "data" / "CodeCoverage" / "UCIS"  #: Directory of the UCIS XML files.
TOGGLES =    DATA / "PyUCIS" / "toggle_2state.xml"                                  #: pyucis' toggle coverage.
FSMS =       DATA / "PyUCIS" / "fsm_example.xml"                                    #: pyucis' FSM coverage.
ASSERTIONS = DATA / "PyUCIS" / "assertion_cover.xml"                                #: pyucis' assertion coverage.
PYVSC =      DATA / "PyVSC" / "apb_coverage.xml"                                    #: PyVSC's covergroups.


def _read(content: str) -> InstanceCoverage:
	"""
	Read the coverage of one instance, wrapped into a report in namespace ``UCIS``.

	:param content: The instance's coverage elements.
	:returns:       The instance.
	"""
	with TemporaryDirectory() as directory:
		xmlFile = Path(directory) / "ucis.xml"
		xmlFile.write_text(
			'<UCIS xmlns="UCIS" ucisVersion="1.0" writtenBy="unit test" writtenTime="2026-10-09T12:00:00">'
			'<sourceFiles fileName="src/dut.sv" id="1"/>'
			'<historyNodes historyNodeId="1" logicalName="t" testStatus="true" date="2026-10-09T12:00:00" '
			'toolCategory="simulator" ucisVersion="1.0" vendorId="v" vendorTool="t" vendorToolVersion="1"/>'
			'<instanceCoverages name="dut" key="0" moduleName="dut"><id file="1" line="1" inlineCount="1"/>'
			f'{content}</instanceCoverages></UCIS>',
			encoding="utf-8"
		)
		return Document(xmlFile, analyzeAndConvert=True).Instances[0]


class Toggles(Testcase):
	"""A toggle coverage holds signals - toggle objects -, their bits and each bit's transitions."""

	def test_PyUCIS(self) -> None:
		instance = PyUCISDocument(TOGGLES, analyzeAndConvert=True).Instances[0]

		toggleCoverage, = instance.ToggleCoverages
		toggleObject, = toggleCoverage.Objects
		self.assertEqual(("clk", "0", 5, None, []), (
			toggleObject.Name, toggleObject.Key, toggleObject.ID.LineNumber, toggleObject.Type, toggleObject.Dimensions
		))
		toggleBit, = toggleObject.Bits
		self.assertEqual([("0", "1", 100), ("1", "0", 99)],
		                 [(toggle.From, toggle.To, toggle.Bin.Contents.CoverageCount) for toggle in toggleBit.Toggles])
		self.assertEqual((instance, toggleCoverage, toggleObject, toggleBit),
		                 (toggleCoverage.Parent, toggleObject.Parent, toggleBit.Parent, toggleBit.Toggles[0].Parent))

	def test_Standard(self) -> None:
		"""A vector's dimensions, a bit's indices, the metric modes and the port direction."""
		instance = _read(
			'<toggleCoverage metricMode="2STOGGLE" weight="2"><toggleObject name="ff1" key="0" type="wire" '
			'portDirection="input" excluded="true" excludedReason="debug"><dimension left="3" right="0" downto="true"/>'
			'<id file="1" line="56" inlineCount="1"/><toggleBit name="ff1[2]" key="0"><index>2</index>'
			'<toggle from="0" to="1"><bin><contents coverageCount="3"/></bin></toggle></toggleBit></toggleObject>'
			'<metricMode metricMode="2STOGGLE"><userAttr key="designLevel" type="str">rtl1</userAttr></metricMode>'
			'</toggleCoverage>'
		)

		toggleCoverage, = instance.ToggleCoverages
		self.assertEqual(("2STOGGLE", 2), (toggleCoverage.MetricMode, toggleCoverage.Weight))
		toggleObject, = toggleCoverage.Objects
		self.assertEqual(("wire", "input", True, "debug"), (
			toggleObject.Type, toggleObject.PortDirection, toggleObject.IsExcluded, toggleObject.ExcludedReason
		))
		dimension, = toggleObject.Dimensions
		self.assertEqual((3, 0, True), (dimension.Left, dimension.Right, dimension.DownTo))
		self.assertEqual([2], toggleObject.Bits[0].Indices)
		mode, = toggleCoverage.MetricModes
		self.assertEqual(("2STOGGLE", "rtl1", toggleCoverage),
		                 (mode.MetricMode, mode.UserAttributes[0].Value, mode.Parent))

	def test_Construction(self) -> None:
		toggleCoverage = ToggleCoverage()
		toggleObject = ToggleObject("q", "0", StatementID(1, 3, 1), dimensions=[Dimension(3, 0, True)],
		                            parent=toggleCoverage)
		toggleBit = ToggleBit("q[0]", "0", [0], parent=toggleObject)
		toggle = Toggle("0", "1", Bin(BinContents(2)), parent=toggleBit)
		mode = MetricMode("3STOGGLE", parent=toggleCoverage)

		self.assertEqual(([toggleObject], [toggleBit], [toggle], [mode], toggle),
		                 (toggleCoverage.Objects, toggleObject.Bits, toggleBit.Toggles, toggleCoverage.MetricModes,
		                  toggle.Bin.Parent))

		with self.assertRaises(TypeError) as context:
			_ = Dimension(3, 0, "true")
		self.assertEqual("Parameter 'downTo' is not of type 'bool'.", str(context.exception))

		with self.assertRaises(ValueError) as context:
			_ = ToggleBit("q[0]", "0", [-1])
		self.assertEqual("Parameter 'indices' contains a negative index.", str(context.exception))
		self.assertEqual(["Got value '-1'."], context.exception.__notes__)

		with self.assertRaises(TypeError) as context:
			_ = Toggle("0", "1", Bin(BinContents(2)), parent=toggleObject)
		self.assertEqual("Parameter 'parent' is not of type 'ToggleBit'.", str(context.exception))


class Conditions(Testcase):
	"""A condition coverage holds expressions, nested by their sub-expressions, and a bin per combination of values."""

	def test_Standard(self) -> None:
		instance = _read(
			'<conditionCoverage metricMode="UCIS:BITWISE_FLAT"><expr name="#cond#1#" key="3" exprString="(a&amp;&amp;b)'
			' || c" index="0" width="1" statementType="if"><id file="1" line="35" inlineCount="1"/>'
			'<subExpr>(a&amp;&amp;b)</subExpr><subExpr>c</subExpr>'
			'<bin><contents nameComponent="0-" coverageCount="2"/></bin><bin><contents nameComponent="-1" coverageCount="0"/>'
			'</bin><hierarchicalExpr name="#cond#1#1#" key="4" exprString="(a&amp;&amp;b)" index="1" width="1">'
			'<id file="1" line="35" inlineCount="1"/><subExpr>a</subExpr><subExpr>b</subExpr>'
			'<bin><contents coverageCount="1"/></bin></hierarchicalExpr></expr></conditionCoverage>'
		)

		conditionCoverage, = instance.ConditionCoverages
		expression, = conditionCoverage.Expressions
		self.assertEqual(("#cond#1#", "(a&&b) || c", 0, 1, "if", ["(a&&b)", "c"]), (
			expression.Name, expression.Text, expression.Index, expression.Width, expression.StatementType,
			expression.SubExpressions
		))
		self.assertEqual([("0-", 2), ("-1", 0)], [
			(coverBin.Contents.NameComponent, coverBin.Contents.CoverageCount) for coverBin in expression.Bins
		])
		nested, = expression.Expressions
		self.assertEqual(("(a&&b)", 1, None, expression, expression),
		                 (nested.Text, nested.Index, nested.StatementType, nested.Parent, expression.Bins[0].Parent))

	def test_Construction(self) -> None:
		conditionCoverage = ConditionCoverage()
		expression = Expression("e", "0", "a|b", 0, 1, StatementID(1, 4, 1), ["a", "b"], [Bin(BinContents(1))],
		                        parent=conditionCoverage)
		self.assertEqual([expression], conditionCoverage.Expressions)

		with self.assertRaises(ValueError) as context:
			_ = Expression("e", "0", "a|b", -1, 1, StatementID(1, 4, 1), ["a"], [Bin(BinContents(1))])
		self.assertEqual("Parameter 'index' is negative.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = Expression("e", "0", "a|b", 0, 1, StatementID(1, 4, 1), ["a"], [BinContents(1)])
		self.assertEqual("Parameter 'bins' contains an element not of type 'Bin'.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = Expression("e", "0", "a|b", 0, 1, StatementID(1, 4, 1), ["a"], [], parent=InstanceCoverage(
				"dut", "0", StatementID(1, 1, 1)
			))
		self.assertEqual("Parameter 'parent' is not of type 'ConditionCoverage' or 'Expression'.", str(context.exception))


class FSMs(Testcase):
	"""An FSM coverage holds finite state machines, their states and transitions."""

	def test_PyUCIS(self) -> None:
		fsmCoverage, = PyUCISDocument(FSMS, analyzeAndConvert=True).Instances[0].FSMCoverages
		fsm, = fsmCoverage.FSMs

		self.assertEqual(("state_reg", "reg", 1), (fsm.Name, fsm.Type, fsm.Width))
		self.assertEqual([("IDLE", "0", 5), ("ACTIVE", "1", 3), ("DONE", "2", 0)],
		                 [(state.Name, state.Value, state.Bin.Contents.CoverageCount) for state in fsm.States])
		self.assertEqual([(["IDLE", "ACTIVE"], 3), (["ACTIVE", "DONE"], 0)],
		                 [(transition.States, transition.Bin.Contents.CoverageCount) for transition in fsm.Transitions])
		self.assertEqual((fsmCoverage, fsm, fsm), (fsm.Parent, fsm.States[0].Parent, fsm.Transitions[0].Parent))

	def test_Construction(self) -> None:
		fsm = FSM("ctrl", "reg", 4, parent=FSMCoverage())
		state = FSMState(Bin(BinContents(3)), "st1", "4", parent=fsm)
		transition = FSMTransition(["4", "6"], Bin(BinContents(4)), parent=fsm)
		self.assertEqual(([state], [transition], state), (fsm.States, fsm.Transitions, state.Bin.Parent))

		with self.assertRaises(ValueError) as context:
			_ = FSMTransition(["4"], Bin(BinContents(4)))
		self.assertEqual("Parameter 'states' has less than two states.", str(context.exception))
		self.assertEqual(["Got 1 state(s)."], context.exception.__notes__)

		with self.assertRaises(ValueError) as context:
			_ = FSM(width=0)
		self.assertEqual("Parameter 'width' is less than 1.", str(context.exception))


class Assertions(Testcase):
	"""An assertion coverage holds assertions, each with a bin per outcome the report counts."""

	def test_PyUCIS(self) -> None:
		assertionCoverage, = PyUCISDocument(ASSERTIONS, analyzeAndConvert=True).Instances[0].AssertionCoverages
		assertion, = assertionCoverage.Assertions

		self.assertEqual(("prop_valid", "cover"), (assertion.Name, assertion.AssertionKind))
		self.assertEqual(
			{AssertionBinKind.Cover: 8, AssertionBinKind.Fail: 0, AssertionBinKind.Attempt: 8},
			{binKind: coverBin.Contents.CoverageCount for binKind, coverBin in assertion.Bins.items()}
		)
		self.assertIs(assertion, assertion.Bins[AssertionBinKind.Cover].Parent)

	def test_Construction(self) -> None:
		assertionCoverage = AssertionCoverage()
		assertion = Assertion("a1", "assert", {AssertionBinKind.Pass: Bin(BinContents(30))}, parent=assertionCoverage)
		self.assertEqual([assertion], assertionCoverage.Assertions)

		with self.assertRaises(TypeError) as context:
			_ = Assertion("a1", "assert", {"passBin": Bin(BinContents(30))})
		self.assertEqual("Parameter 'bins' contains a key not of type 'AssertionBinKind'.", str(context.exception))
		self.assertEqual(["Got type 'str'."], context.exception.__notes__)


class Covergroups(Testcase):
	"""A covergroup coverage holds covergroup instances, their coverpoints with bins and crosses with bins."""

	def test_Standard(self) -> None:
		"""The example of the standard (section 9.8.12), as its schema has it."""
		instance = _read(
			'<covergroupCoverage><cgInstance name="top.cv" key="12" alias="my_name"><options at_least="2"/>'
			'<cgId cgName="cg" moduleName="top"><cginstSourceId file="1" line="4" inlineCount="1"/>'
			'<cgSourceId file="1" line="42" inlineCount="1"/></cgId><cgParms><name>N</name><value>4</value></cgParms>'
			'<coverpoint name="cvpt_a" key="14" exprString="a"><options at_least="2"/>'
			'<coverpointBin type="default"><range from="0" to="7"><contents coverageCount="5"/></range>'
			'<range from="9" to="10"><contents coverageCount="1"/></range></coverpointBin>'
			'<coverpointBin type="default"><sequence><contents coverageCount="12"/><seqValue>3</seqValue>'
			'<seqValue>5</seqValue></sequence></coverpointBin></coverpoint>'
			'<cross name="xab" key="15"><options weight="1" goal="100" comment="a comment"/>'
			'<crossExpr>cvpt_a</crossExpr><crossExpr>cvpt_b</crossExpr>'
			'<crossBin><index>0</index><index>1</index><contents coverageCount="3"/></crossBin></cross>'
			'</cgInstance></covergroupCoverage>'
		)

		covergroupCoverage, = instance.CovergroupCoverages
		cgInstance, = covergroupCoverage.Instances
		self.assertEqual(("top.cv", "12", "my_name", {"N": "4"}, 2, 100, False), (
			cgInstance.Name, cgInstance.Key, cgInstance.Alias, cgInstance.Parameters, cgInstance.Options.AtLeast,
			cgInstance.Options.Goal, cgInstance.IsExcluded
		))
		self.assertEqual(("cg", "top", 4, 42), (
			cgInstance.CovergroupID.Name, cgInstance.CovergroupID.ModuleName,
			cgInstance.CovergroupID.InstanceSourceID.LineNumber, cgInstance.CovergroupID.SourceID.LineNumber
		))
		coverpoint, = cgInstance.Coverpoints
		ranges, sequences = coverpoint.Bins
		self.assertEqual(("a", 2, 64), (coverpoint.Expression, coverpoint.Options.AtLeast, coverpoint.Options.AutoBinMax))
		self.assertEqual([(0, 7, 5), (9, 10, 1)], [
			(valueRange.From, valueRange.To, valueRange.Contents.CoverageCount) for valueRange in ranges.Ranges
		])
		self.assertEqual(([3, 5], 12, None, sequences),
		                 (sequences.Sequences[0].Values, sequences.Sequences[0].Contents.CoverageCount, sequences.Name,
		                  sequences.Sequences[0].Parent))
		cross, = cgInstance.Crosses
		self.assertEqual((["cvpt_a", "cvpt_b"], "a comment", 0), (cross.Expressions, cross.Options.Comment,
		                                                          cross.Options.CrossNumPrintMissing))
		crossBin, = cross.Bins
		self.assertEqual(([0, 1], 3, "default", cross),
		                 (crossBin.Indices, crossBin.Contents.CoverageCount, crossBin.BinType, crossBin.Parent))

	def test_PyVSC(self) -> None:
		"""pyucis names a coverpoint's and a cross' bins, PyVSC states no values - a range of ``-1``."""
		cgInstance, = PyUCISDocument(PYVSC, analyzeAndConvert=True).Instances[0].CovergroupCoverages[0].Instances

		self.assertEqual(["type_cp", "addr_cp", "data_cp"], [coverpoint.Name for coverpoint in cgInstance.Coverpoints])
		read, write = cgInstance.Coverpoints[0].Bins
		self.assertEqual(("read", "0", "bins", -1, 154), (
			read.Name, read.Key, read.BinType, read.Ranges[0].From, read.Ranges[0].Contents.CoverageCount
		))
		self.assertEqual([("cross_rw_addr", 32), ("cross_rw_wdata", 4)],
		                 [(cross.Name, len(cross.Bins)) for cross in cgInstance.Crosses])

	def test_PyVSC_Standard(self) -> None:
		"""The standard's schema has no name of a coverpoint's bin."""
		content = PYVSC.read_text(encoding="utf-8").replace(
			'<UCIS xmlns:ucis="http://www.w3.org/2001/XMLSchema-instance"', '<UCIS xmlns="UCIS"'
		)
		with TemporaryDirectory() as directory:
			xmlFile = Path(directory) / "ucis.xml"
			xmlFile.write_text(content, encoding="utf-8")

			with self.assertRaises(CodeCoverageError) as context:
				_ = Document(xmlFile, analyzeAndConvert=True)

		self.assertIn("The attribute 'name' is not allowed.", context.exception.__notes__[0])

	def test_Construction(self) -> None:
		covergroupID = CovergroupID("cg", "top", StatementID(1, 4, 1), StatementID(1, 42, 1))
		cgInstance = CovergroupInstance("top.cv", "0", CovergroupOptions(), covergroupID, parent=CovergroupCoverage())
		coverpoint = Coverpoint("cp", "0", CoverpointOptions(), parent=cgInstance)
		coverpointBin = CoverpointBin("default", [ValueRange(0, 7, BinContents(5))], parent=coverpoint)
		cross = Cross("x", "0", CrossOptions(), ["cp", "cp"], parent=cgInstance)
		crossBin = CrossBin([0, 0], BinContents(1), parent=cross)

		self.assertEqual(([coverpoint], [coverpointBin], [cross], [crossBin], coverpointBin),
		                 (cgInstance.Coverpoints, coverpoint.Bins, cgInstance.Crosses, cross.Bins,
		                  coverpointBin.Ranges[0].Parent))

		with self.assertRaises(ValueError) as context:
			_ = CoverpointOptions(goal=-1)
		self.assertEqual("Parameter 'goal' is negative.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = CovergroupInstance("top.cv", "0", CoverpointOptions(), covergroupID)
		self.assertEqual("Parameter 'options' is not of type 'CovergroupOptions'.", str(context.exception))

		with self.assertRaises(ValueError) as context:
			_ = ValueSequence([], BinContents(1))
		self.assertEqual("Parameter 'values' is empty.", str(context.exception))

		with self.assertRaises(ValueError) as context:
			_ = CrossBin([], BinContents(1))
		self.assertEqual("Parameter 'indices' is empty.", str(context.exception))


class Conversion(Testcase):
	"""The coverage kinds beside code coverage aren't converted to the common model."""

	def test_NoLines(self) -> None:
		for xmlFile in (TOGGLES, FSMS, ASSERTIONS, PYVSC):
			with self.subTest(file=xmlFile.name):
				summary = PyUCISDocument(xmlFile, analyzeAndConvert=True).ToCoverageSummary()

				self.assertEqual(([], 0), (list(summary.IterateFiles()), summary.TotalLines))
