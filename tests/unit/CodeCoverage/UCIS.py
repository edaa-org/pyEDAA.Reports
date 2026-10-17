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
"""Unit tests of the UCIS XML interchange format: its model, its XML schema and the conversion to the common model."""
from datetime                                      import datetime
from decimal                                       import Decimal
from pathlib                                       import Path
from tempfile                                      import TemporaryDirectory

from lxml.etree                                    import fromstring
from pyEDAA.Reports.CodeCoverage                   import CodeCoverageError, LineCoverageStatus
from pyEDAA.Reports.CodeCoverage.Cobertura         import Document as CoberturaDocument
from pyEDAA.Reports.CodeCoverage.UCIS              import Document, FormatVersion, SCHEMAS
from pyEDAA.Reports.CodeCoverage.UCIS.Bins         import Bin, BinContents
from pyEDAA.Reports.CodeCoverage.UCIS.Blocks       import Block, BlockCoverage, Process, Statement
from pyEDAA.Reports.CodeCoverage.UCIS.Branches     import Branch, BranchCoverage, BranchStatement
from pyEDAA.Reports.CodeCoverage.UCIS.Elements     import StatementID, UserAttribute, UserAttributeType
from pyEDAA.Reports.CodeCoverage.UCIS.HistoryNodes import HistoryNode
from pyEDAA.Reports.CodeCoverage.UCIS.Instances    import InstanceCoverage, SourceFile
from pyTooling.Testing                             import Testcase


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


DATA =      Path(__file__).parent.parent.parent / "data" / "CodeCoverage" / "UCIS"  #: Directory of the UCIS XML files.
SYNTHETIC = DATA / "synthetic-1.0.xml"                                             #: The hand-written UCIS 1.0 file.


def _write(directory: str, content: str) -> Path:
	"""
	Write a report file into a directory.

	:param directory: The directory.
	:param content:   The report's text.
	:returns:         The report file.
	"""
	xmlFile = Path(directory) / "ucis.xml"
	xmlFile.write_text(content, encoding="utf-8")
	return xmlFile


def _instance(content: str) -> str:
	"""
	Wrap the coverage of one instance into a report with one source file and one history node.

	:param content: The instance's coverage elements.
	:returns:       The report's text.
	"""
	return (
		'<UCIS xmlns="UCIS" ucisVersion="1.0" writtenBy="unit test" writtenTime="2026-10-09T12:00:00">'
		'<sourceFiles fileName="src/dut.sv" id="1"/>'
		'<historyNodes historyNodeId="1" logicalName="t" testStatus="true" date="2026-10-09T12:00:00" '
		'toolCategory="simulator" ucisVersion="1.0" vendorId="v" vendorTool="t" vendorToolVersion="1"/>'
		'<instanceCoverages name="dut" key="0" moduleName="dut"><id file="1" line="1" inlineCount="1"/>'
		f'{content}</instanceCoverages></UCIS>'
	)


class FormatModel(Testcase):
	"""The format's model keeps what the report states: source files, history nodes, instances and their coverage."""

	def test_Report(self) -> None:
		report = Document(SYNTHETIC, analyzeAndConvert=True)

		self.assertEqual(
			(FormatVersion.Version1_0, "hand-written", datetime(2026, 10, 9, 12, 0, 0)),
			(report.FormatVersion, report.WrittenBy, report.WrittenTime)
		)
		self.assertEqual(
			{1: Path("rtl/counter.sv"), 2: Path("tb/top.sv")},
			{fileID: sourceFile.Path for fileID, sourceFile in report.SourceFiles.items()}
		)
		self.assertIs(report, report.SourceFiles[1].Parent)
		self.assertEqual(["top", "top.c1", "top.c2"], [instance.Name for instance in report.Instances])

	def test_HistoryNode(self) -> None:
		historyNode = Document(SYNTHETIC, analyzeAndConvert=True).HistoryNodes[1]

		self.assertEqual(
			("test_counter", True, datetime(2026, 10, 9, 11, 59, 0), "UCIS:Simulator", "1.0", "synthetic", "hand-written"),
			(historyNode.LogicalName, historyNode.TestStatus, historyNode.Date, historyNode.ToolCategory,
			 historyNode.UCISVersion, historyNode.VendorID, historyNode.VendorTool)
		)
		self.assertEqual(
			(Path("test_counter.ucdb"), "UCIS_HISTORYNODE_TEST", 112.0, "ns", Path("/home/user/project"), 0.25),
			(historyNode.PhysicalName, historyNode.Kind, historyNode.SimulationTime, historyNode.TimeUnit,
			 historyNode.RunDirectory, historyNode.CPUTime)
		)
		self.assertEqual(("0", "vsim", "-c top", "user", None, None, None, None), (
			historyNode.Seed, historyNode.Command, historyNode.Arguments, historyNode.UserName, historyNode.ParentID,
			historyNode.Cost, historyNode.SameTests, historyNode.Comment
		))
		attribute, = historyNode.UserAttributes
		self.assertEqual(("optimization_level", UserAttributeType.Integer, 3, None),
		                 (attribute.Key, attribute.Type, attribute.Value, attribute.Length))

	def test_Instances(self) -> None:
		top, c1, c2 = Document(SYNTHETIC, analyzeAndConvert=True).Instances

		self.assertEqual(("top", "0", 1, "top", None), (top.Name, top.Key, top.InstanceID, top.ModuleName,
		                                                top.ParentInstanceID))
		self.assertEqual(("counter", 1, {}), (c1.ModuleName, c1.ParentInstanceID, c1.DesignParameters))
		self.assertEqual({"WIDTH": "4"}, c2.DesignParameters)
		self.assertEqual((2, 5, 1), (c2.ID.FileID, c2.ID.LineNumber, c2.ID.InlineCount))
		self.assertEqual((1, 1), (len(c2.BlockCoverages), len(c2.BranchCoverages)))
		self.assertEqual(("UCIS:STATEMENT", 1), (c2.BlockCoverages[0].MetricMode, c2.BlockCoverages[0].Weight))

	def test_Statements(self) -> None:
		report = Document(SYNTHETIC, analyzeAndConvert=True)
		statements = list(report.IterateStatements())

		self.assertEqual(9, len(statements))
		excluded = statements[2]
		self.assertEqual((9, 0, True, "end of simulation"), (
			excluded.ID.LineNumber, excluded.Bin.Contents.CoverageCount, excluded.IsExcluded, excluded.ExcludedReason
		))
		first = statements[3]
		self.assertEqual(("#stmt#3#1#", ":5:", [], None), (
			first.Bin.Contents.NameComponent, first.Bin.Contents.TypeComponent, first.Bin.Contents.HistoryNodeIDs,
			first.Bin.CoverageCountGoal
		))
		self.assertEqual([1], statements[0].Bin.Contents.HistoryNodeIDs)
		self.assertIs(statements[0], statements[0].Bin.Parent)

	def test_BranchStatements(self) -> None:
		statement, _ = Document(SYNTHETIC, analyzeAndConvert=True).IterateBranchStatements()

		self.assertEqual(("if", "(rst)", 3), (statement.StatementType, statement.BranchExpression, statement.ID.LineNumber))
		self.assertEqual([(4, "true", 2), (6, "all_false_bin", 10)], [
			(branch.ID.LineNumber, branch.Bin.Contents.NameComponent, branch.Bin.Contents.CoverageCount)
			for branch in statement.Branches
		])


class Construction(Testcase):
	"""The format's model is built by hand: each constructor takes typed values and checks them."""

	def test_UserAttribute(self) -> None:
		attribute = UserAttribute("run_mask", UserAttributeType.Bits, "01101100", 8)

		self.assertEqual(("run_mask", UserAttributeType.Bits, "01101100", 8),
		                 (attribute.Key, attribute.Type, attribute.Value, attribute.Length))
		self.assertIsNone(UserAttribute("x1", UserAttributeType.Double).Value)

	def test_UserAttribute_Value(self) -> None:
		"""The value's type follows the attribute's type."""
		with self.assertRaises(TypeError) as context:
			_ = UserAttribute("level", UserAttributeType.Integer, "3")
		self.assertEqual("Parameter 'value' is not of type 'int'.", str(context.exception))
		self.assertEqual(["Got type 'str' for attribute type 'int'."], context.exception.__notes__)

		with self.assertRaises(TypeError) as context:
			_ = UserAttribute("ratio", UserAttributeType.Double, 1)
		self.assertEqual("Parameter 'value' is not of type 'float'.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = UserAttribute("level", "int", 3)
		self.assertEqual("Parameter 'attributeType' is not of type 'UserAttributeType'.", str(context.exception))

	def test_Bin(self) -> None:
		coverBin = Bin(BinContents(4, [2, 5], "block", ":22:"), 1, "b1", True, "unreachable", 2)

		self.assertEqual((4, [2, 5], "block", ":22:"), (
			coverBin.Contents.CoverageCount, coverBin.Contents.HistoryNodeIDs, coverBin.Contents.NameComponent,
			coverBin.Contents.TypeComponent
		))
		self.assertEqual((1, "b1", True, "unreachable", 2, None), (
			coverBin.CoverageCountGoal, coverBin.Alias, coverBin.IsExcluded, coverBin.ExcludedReason, coverBin.Weight,
			coverBin.Parent
		))

	def test_Bin_Checks(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = Bin(None)
		self.assertEqual("Parameter 'contents' is None.", str(context.exception))

		with self.assertRaises(ValueError) as context:
			_ = Bin(BinContents(0), -1)
		self.assertEqual("Parameter 'coverageCountGoal' is negative.", str(context.exception))
		self.assertEqual(["Got value '-1'."], context.exception.__notes__)

		with self.assertRaises(TypeError) as context:
			_ = Bin(BinContents(0), excluded="false")
		self.assertEqual("Parameter 'excluded' is not of type 'bool'.", str(context.exception))

		with self.assertRaises(ValueError) as context:
			_ = Bin(BinContents(0), weight=-2)
		self.assertEqual("Parameter 'weight' is negative.", str(context.exception))

	def test_BinContents_Checks(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = BinContents(-1)
		self.assertEqual("Parameter 'coverageCount' is negative.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = BinContents(1, ["2"])
		self.assertEqual("Parameter 'historyNodeIDs' contains an element not of type 'int'.", str(context.exception))
		self.assertEqual(["Got type 'str'."], context.exception.__notes__)

	def test_StatementID(self) -> None:
		statementID = StatementID(3, 5, 1)

		self.assertEqual((3, 5, 1, "<StatementID 3:5:1>"),
		                 (statementID.FileID, statementID.LineNumber, statementID.InlineCount, repr(statementID)))

		for arguments, message in (
			((None, 1, 1), "Parameter 'fileID' is None."),
			((1, "5", 1),  "Parameter 'lineNumber' is not of type 'int'."),
			((1, 1, 0),    "Parameter 'inlineCount' is less than 1.")
		):
			with self.subTest(arguments=arguments):
				with self.assertRaises((ValueError, TypeError)) as context:
					_ = StatementID(*arguments)
				self.assertEqual(message, str(context.exception))

	def test_SourceFile(self) -> None:
		sourceFile = SourceFile(Path("src/dut.sv"), 1)
		self.assertEqual((Path("src/dut.sv"), 1, None), (sourceFile.Path, sourceFile.SourceFileID, sourceFile.Parent))

		with self.assertRaises(TypeError) as context:
			_ = SourceFile("src/dut.sv", 1)
		self.assertEqual("Parameter 'path' is not of type 'Path'.", str(context.exception))

		with self.assertRaises(ValueError) as context:
			_ = SourceFile(Path("src/dut.sv"), 0)
		self.assertEqual("Parameter 'sourceFileID' is less than 1.", str(context.exception))

	def test_HistoryNode(self) -> None:
		date = datetime(2026, 10, 9, 12, 0, 0)
		historyNode = HistoryNode(0, "merged", True, date, "merge", "1.0", "v", "t", "1", cost=Decimal("3.2"))
		self.assertEqual(("merged", Decimal("3.2"), None), (historyNode.LogicalName, historyNode.Cost, historyNode.Parent))

		with self.assertRaises(TypeError) as context:
			_ = HistoryNode(0, "merged", True, "2026-10-09", "merge", "1.0", "v", "t", "1")
		self.assertEqual("Parameter 'date' is not of type 'datetime'.", str(context.exception))

		with self.assertRaises(ValueError) as context:
			_ = HistoryNode(0, "merged", True, date, "merge", "1.0", None, "t", "1")
		self.assertEqual("Parameter 'vendorID' is None.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = HistoryNode(0, "merged", True, date, "merge", "1.0", "v", "t", "1", simulationTime=112)
		self.assertEqual("Parameter 'simulationTime' is not of type 'float'.", str(context.exception))

		with self.assertRaises(ValueError) as context:
			_ = HistoryNode(0, "merged", True, date, "merge", "1.0", "v", "t", "1", parentID=-1)
		self.assertEqual("Parameter 'parentID' is negative.", str(context.exception))

	def test_InstanceCoverage(self) -> None:
		instance = InstanceCoverage("top.dut", "3", StatementID(1, 4, 1), designParameters={"WIDTH": "8"})
		self.assertEqual(("top.dut", "3", {"WIDTH": "8"}, [], [], None), (
			instance.Name, instance.Key, instance.DesignParameters, instance.BlockCoverages, instance.BranchCoverages,
			instance.Parent
		))

		with self.assertRaises(TypeError) as context:
			_ = InstanceCoverage("top.dut", "3", StatementID(1, 4, 1), designParameters={"WIDTH": 8})
		self.assertEqual("Parameter 'designParameters' contains a name or value not of type 'str'.", str(context.exception))
		self.assertEqual(["Got types 'str' and 'int'."], context.exception.__notes__)

		with self.assertRaises(TypeError) as context:
			_ = InstanceCoverage("top.dut", "3", StatementID(1, 4, 1), instanceID="1")
		self.assertEqual("Parameter 'instanceID' is not of type 'int'.", str(context.exception))

	def test_UserAttributes(self) -> None:
		with self.assertRaises(TypeError) as context:
			_ = Bin(BinContents(0), userAttributes=[("key", "value")])
		self.assertEqual("Parameter 'userAttributes' contains an element not of type 'UserAttribute'.",
		                 str(context.exception))
		self.assertEqual(["Got type 'tuple'."], context.exception.__notes__)


class ParentRelation(Testcase):
	"""Each element below the report names its parent and is added to it; an element owning a bin is the bin's parent."""

	def test_Report(self) -> None:
		document = Document(Path("ucis.xml"))
		sourceFile = SourceFile(Path("src/dut.sv"), 1, parent=document)
		historyNode = HistoryNode(
			1, "test", True, datetime(2026, 10, 9), "simulator", "1.0", "v", "t", "1", parent=document
		)
		instance = InstanceCoverage("dut", "0", StatementID(1, 1, 1), parent=document)

		self.assertEqual(({1: sourceFile}, {1: historyNode}, [instance]),
		                 (document.SourceFiles, document.HistoryNodes, document.Instances))
		self.assertEqual((document, document, document), (sourceFile.Parent, historyNode.Parent, instance.Parent))

	def test_Blocks(self) -> None:
		instance = InstanceCoverage("dut", "0", StatementID(1, 1, 1))
		blockCoverage = BlockCoverage("UCIS:BLOCK", parent=instance)
		process = Process("always", parent=blockCoverage)
		block = Block(StatementID(1, 3, 1), Bin(BinContents(2)), [StatementID(1, 4, 1)], "always", parent=process)
		nested = Block(StatementID(1, 5, 1), Bin(BinContents(1)), parent=block)
		statement = Statement(StatementID(1, 8, 1), Bin(BinContents(0)), parent=blockCoverage)

		self.assertEqual(([blockCoverage], [process], [block], [nested], [statement]), (
			instance.BlockCoverages, blockCoverage.Processes, process.Blocks, block.Blocks, blockCoverage.Statements
		))
		self.assertEqual((instance, blockCoverage, process, block, block),
		                 (blockCoverage.Parent, process.Parent, block.Parent, nested.Parent, block.Bin.Parent))
		self.assertEqual([block, nested], list(blockCoverage.IterateBlocks()))
		self.assertEqual(("always", "always", [4]), (process.ProcessType, block.ParentProcess,
		                                             [statementID.LineNumber for statementID in block.StatementIDs]))

	def test_Branches(self) -> None:
		instance = InstanceCoverage("dut", "0", StatementID(1, 1, 1))
		branchCoverage = BranchCoverage(parent=instance)
		statement = BranchStatement(StatementID(1, 5, 1), "case", "(x)", parent=branchCoverage)
		branch = Branch(StatementID(1, 6, 1), Bin(BinContents(3)), parent=statement)
		nested = BranchStatement(StatementID(1, 6, 2), "if", parent=branch)

		self.assertEqual(([branchCoverage], [statement], [branch], [nested]), (
			instance.BranchCoverages, branchCoverage.Statements, statement.Branches, branch.Statements
		))
		self.assertEqual((instance, branchCoverage, statement, branch),
		                 (branchCoverage.Parent, statement.Parent, branch.Parent, nested.Parent))
		self.assertEqual([statement, nested], list(branchCoverage.IterateStatements()))

	def test_WrongParent(self) -> None:
		instance = InstanceCoverage("dut", "0", StatementID(1, 1, 1))
		document = Document(Path("ucis.xml"))
		for create, message, got in (
			(lambda: Statement(StatementID(1, 1, 1), Bin(BinContents(0)), parent=instance),
			 "Parameter 'parent' is not of type 'BlockCoverage'.",
			 "pyEDAA.Reports.CodeCoverage.UCIS.Instances.InstanceCoverage"),
			(lambda: Block(StatementID(1, 1, 1), Bin(BinContents(0)), parent=instance),
			 "Parameter 'parent' is not of type 'BlockCoverage', 'Process' or 'Block'.",
			 "pyEDAA.Reports.CodeCoverage.UCIS.Instances.InstanceCoverage"),
			(lambda: BranchStatement(StatementID(1, 1, 1), "if", parent=instance),
			 "Parameter 'parent' is not of type 'BranchCoverage' or 'Branch'.",
			 "pyEDAA.Reports.CodeCoverage.UCIS.Instances.InstanceCoverage"),
			(lambda: BlockCoverage(parent=document),
			 "Parameter 'parent' is not of type 'InstanceCoverage'.", "pyEDAA.Reports.CodeCoverage.UCIS.Document"),
			(lambda: SourceFile(Path("a.sv"), 1, parent=instance),
			 "Parameter 'parent' is not of type 'Report'.", "pyEDAA.Reports.CodeCoverage.UCIS.Instances.InstanceCoverage")
		):
			with self.subTest(message=message):
				with self.assertRaises(TypeError) as context:
					_ = create()
				self.assertEqual(message, str(context.exception))
				self.assertEqual([f"Got type '{got}'."], context.exception.__notes__)


class Parsing(Testcase):
	"""Each element's class method ``Parse`` reads its XML element."""

	def test_UserAttribute(self) -> None:
		for xml, expected in (
			('<userAttr xmlns="UCIS" key="k" type="int"> 3 </userAttr>',          (UserAttributeType.Integer, 3, None)),
			('<userAttr xmlns="UCIS" key="k" type="double">0.5</userAttr>',       (UserAttributeType.Double, 0.5, None)),
			('<userAttr xmlns="UCIS" key="k" type="bits" len="4">0110</userAttr>', (UserAttributeType.Bits, "0110", 4)),
			('<userAttr xmlns="UCIS" key="k" type="str" len="3264"/>',            (UserAttributeType.String, None, 3264))
		):
			with self.subTest(xml=xml):
				attribute = UserAttribute.Parse(fromstring(xml))
				self.assertEqual(expected, (attribute.Type, attribute.Value, attribute.Length))

	def test_UserAttribute_Value(self) -> None:
		with self.assertRaises(CodeCoverageError) as context:
			_ = UserAttribute.Parse(fromstring('<userAttr xmlns="UCIS" key="level" type="int">high</userAttr>'))

		self.assertEqual("UCIS user attribute 'level' states a value not of type 'int'.", str(context.exception))
		self.assertEqual(["Got value 'high'."], context.exception.__notes__)

	def test_Bin(self) -> None:
		coverBin = Bin.Parse(fromstring(
			'<bin xmlns="UCIS" coverageCountGoal="1" excluded="1" weight="0"><contents coverageCount="4">'
			'<historyNodeId>2</historyNodeId><historyNodeId>5</historyNodeId></contents>'
			'<userAttr key="label" type="str">st1</userAttr></bin>'
		))

		self.assertEqual((4, [2, 5], 1, True, 0, ["st1"]), (
			coverBin.Contents.CoverageCount, coverBin.Contents.HistoryNodeIDs, coverBin.CoverageCountGoal,
			coverBin.IsExcluded, coverBin.Weight, [attribute.Value for attribute in coverBin.UserAttributes]
		))

	def test_Blocks(self) -> None:
		"""A block coverage of processes: a process' blocks, nested blocks, the statements a block contains."""
		with TemporaryDirectory() as directory:
			report = Document(_write(directory, _instance(
				'<blockCoverage metricMode="BLOCK_MODE3"><process processType="always"><block parentProcess="always">'
				'<statementId file="1" line="3" inlineCount="1"/><statementId file="1" line="4" inlineCount="1"/>'
				'<hierarchicalBlock><blockBin><contents coverageCount="0"/></blockBin>'
				'<blockId file="1" line="6" inlineCount="1"/></hierarchicalBlock>'
				'<blockBin><contents coverageCount="5"/></blockBin><blockId file="1" line="3" inlineCount="1"/>'
				'</block></process></blockCoverage>'
			)), analyzeAndConvert=True)

		blockCoverage, = report.Instances[0].BlockCoverages
		process, = blockCoverage.Processes
		block, = process.Blocks
		nested, = block.Blocks
		self.assertEqual(("always", 3, [3, 4], 5), (
			block.ParentProcess, block.ID.LineNumber, [statementID.LineNumber for statementID in block.StatementIDs],
			block.Bin.Contents.CoverageCount
		))
		self.assertEqual((6, 0, None), (nested.ID.LineNumber, nested.Bin.Contents.CoverageCount, nested.ParentProcess))


class Conversion(Testcase):
	"""The statement and branch coverage converts to the common model's lines, branches and modules."""

	def test_Lines(self) -> None:
		"""Each instance counts on its own: a line ran as often as its least often run statement."""
		summary = Document(SYNTHETIC, analyzeAndConvert=True).ToCoverageSummary()

		self.assertEqual(("synthetic-1.0", [Path("/home/user/project")]), (summary.Name, summary.SourceDirectories))
		counter = summary.GetOrAddFile("rtl/counter.sv")
		self.assertEqual(
			[(3, LineCoverageStatus.PartiallyCovered, 12), (4, LineCoverageStatus.Covered, 2),
			 (6, LineCoverageStatus.Uncovered, 0)],
			[(line.LineNumber, line.Status, line.CoverageCount) for line in counter.Lines if line is not None]
		)
		top = summary.GetOrAddFile("tb/top.sv")
		self.assertEqual(
			[(6, LineCoverageStatus.Covered, 23), (8, LineCoverageStatus.Covered, 1), (9, LineCoverageStatus.Excluded, None)],
			[(line.LineNumber, line.Status, line.CoverageCount) for line in top.Lines if line is not None]
		)
		self.assertEqual((5, 4, 1, 4, 3), (summary.TotalLines, summary.CoveredLines, summary.ExcludedLines,
		                                   summary.TotalBranches, summary.CoveredBranches))

	def test_Lines_MergeInstances(self) -> None:
		"""Merged, a statement ran as often as in all instances together; the branches are summed per branch."""
		summary = Document(SYNTHETIC, analyzeAndConvert=True).ToCoverageSummary(mergeInstances=True)

		counter = summary.GetOrAddFile("rtl/counter.sv")
		self.assertEqual(
			[(3, LineCoverageStatus.Covered, 24), (4, LineCoverageStatus.Covered, 14), (6, LineCoverageStatus.Covered, 10)],
			[(line.LineNumber, line.Status, line.CoverageCount) for line in counter.Lines if line is not None]
		)
		self.assertEqual((5, 5, 2, 2), (summary.TotalLines, summary.CoveredLines, summary.TotalBranches,
		                                summary.CoveredBranches))

	def test_Branches(self) -> None:
		"""A branch goes to the line of its first statement."""
		counter = Document(SYNTHETIC, analyzeAndConvert=True).ToCoverageSummary().GetOrAddFile("rtl/counter.sv")

		self.assertEqual(
			[(LineCoverageStatus.Covered, 2, 4), (LineCoverageStatus.Covered, 10, 6),
			 (LineCoverageStatus.Covered, 12, 4), (LineCoverageStatus.Uncovered, 0, 6)],
			[(branch.Status, branch.CoverageCount, branch.Target.LineNumber) for branch in counter.GetLine(3).Branches]
		)

	def test_Modules(self) -> None:
		"""A design unit spans the lines of its statements."""
		summary = Document(SYNTHETIC, analyzeAndConvert=True).ToCoverageSummary()

		self.assertEqual(
			{"counter": ("rtl/counter.sv", 3, 6, 3), "top": ("tb/top.sv", 6, 9, 2)},
			{unit.Name: (unit.File.Path.as_posix(), unit.StartLine.LineNumber, unit.EndLine.LineNumber, unit.TotalLines)
			 for unit in summary.IterateUnits()}
		)

	def test_Blocks(self) -> None:
		"""A block's statements ran as often as their block; a block without statements counts for its own line."""
		with TemporaryDirectory() as directory:
			summary = Document(_write(directory, _instance(
				'<blockCoverage><block><statementId file="1" line="3" inlineCount="1"/>'
				'<statementId file="1" line="4" inlineCount="1"/>'
				'<hierarchicalBlock><blockBin><contents coverageCount="0"/></blockBin>'
				'<blockId file="1" line="6" inlineCount="1"/></hierarchicalBlock>'
				'<blockBin><contents coverageCount="5"/></blockBin><blockId file="1" line="3" inlineCount="1"/>'
				'</block></blockCoverage>'
			)), analyzeAndConvert=True).ToCoverageSummary()

		self.assertEqual(
			[(3, 5), (4, 5), (6, 0)],
			[(line.LineNumber, line.CoverageCount) for line in summary.GetOrAddFile("src/dut.sv").Lines if line is not None]
		)

	def test_Excluded(self) -> None:
		"""An excluded bin excludes its statement; an excluded branch or branching statement isn't converted."""
		with TemporaryDirectory() as directory:
			summary = Document(_write(directory, _instance(
				'<blockCoverage><statement><id file="1" line="3" inlineCount="1"/>'
				'<bin excluded="true"><contents coverageCount="0"/></bin></statement>'
				'<statement><id file="1" line="5" inlineCount="1"/><bin><contents coverageCount="2"/></bin></statement>'
				'</blockCoverage><branchCoverage>'
				'<statement statementType="if" excluded="true"><id file="1" line="3" inlineCount="1"/>'
				'<branch><id file="1" line="3" inlineCount="1"/><branchBin><contents coverageCount="0"/></branchBin></branch>'
				'</statement><statement statementType="if"><id file="1" line="5" inlineCount="1"/>'
				'<branch><id file="1" line="6" inlineCount="1"/><branchBin><contents coverageCount="2"/></branchBin></branch>'
				'<branch><id file="1" line="8" inlineCount="1"/>'
				'<branchBin excluded="true"><contents coverageCount="0"/></branchBin></branch>'
				'</statement></branchCoverage>'
			)), analyzeAndConvert=True).ToCoverageSummary()

		file = summary.GetOrAddFile("src/dut.sv")
		self.assertEqual((LineCoverageStatus.Excluded, []), (file.GetLine(3).Status, file.GetLine(3).Branches))
		self.assertEqual((LineCoverageStatus.Covered, 1, None),
		                 (file.GetLine(5).Status, len(file.GetLine(5).Branches), file.GetLine(5).Branches[0].Target))

	def test_BranchWithoutStatement(self) -> None:
		"""A branching statement's line without statement coverage ran as often as its branches were taken."""
		with TemporaryDirectory() as directory:
			summary = Document(_write(directory, _instance(
				'<branchCoverage><statement statementType="if"><id file="1" line="5" inlineCount="1"/>'
				'<branch><id file="1" line="5" inlineCount="1"/><branchBin><contents coverageCount="2"/></branchBin></branch>'
				'<branch><id file="1" line="5" inlineCount="1"/><branchBin><contents coverageCount="0"/></branchBin></branch>'
				'</statement></branchCoverage>'
			)), analyzeAndConvert=True).ToCoverageSummary()

		line = summary.GetOrAddFile("src/dut.sv").GetLine(5)
		self.assertEqual((LineCoverageStatus.PartiallyCovered, 2, line),
		                 (line.Status, line.CoverageCount, line.Branches[0].Target))

	def test_UnknownSourceFile(self) -> None:
		with TemporaryDirectory() as directory:
			report = Document(_write(directory, _instance(
				'<blockCoverage><statement><id file="7" line="3" inlineCount="1"/>'
				'<bin><contents coverageCount="1"/></bin></statement></blockCoverage>'
			)), analyzeAndConvert=True)

		with self.assertRaises(CodeCoverageError) as context:
			_ = report.ToCoverageSummary()

		self.assertEqual("UCIS statement identifier names source file ID '7'.", str(context.exception))
		self.assertEqual(["The report states source file IDs: 1."], context.exception.__notes__)

	def test_MergeInstances(self) -> None:
		report = Document(SYNTHETIC, analyzeAndConvert=True)

		with self.assertRaises(ValueError) as context:
			_ = report.ToCoverageSummary(None)
		self.assertEqual("Parameter 'mergeInstances' is None.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = report.ToCoverageSummary(1)
		self.assertEqual("Parameter 'mergeInstances' is not of type 'bool'.", str(context.exception))
		self.assertEqual(["Got type 'int'."], context.exception.__notes__)


class Schema(Testcase):
	"""A report is validated against the XML schema of the UCIS version its root states."""

	def test_Schemas(self) -> None:
		self.assertEqual({FormatVersion.Version1_0: "UCIS-1.0.xsd"}, SCHEMAS)

	def test_FormatVersion(self) -> None:
		content = SYNTHETIC.read_text(encoding="utf-8").replace('"1.0" writtenBy', '"1.1" writtenBy')
		with TemporaryDirectory() as directory:
			xmlFile = _write(directory, content)

			with self.assertRaises(CodeCoverageError) as context:
				_ = Document(xmlFile, analyzeAndConvert=True)

		self.assertEqual(f"UCIS XML file '{xmlFile}' states an unsupported UCIS version.", str(context.exception))
		self.assertEqual(["Got version '1.1'.", "Supported UCIS versions: 1.0."], context.exception.__notes__)

	def test_Namespace(self) -> None:
		"""The root element must be in namespace ``UCIS``."""
		content = SYNTHETIC.read_text(encoding="utf-8").replace('<UCIS xmlns="UCIS"', '<UCIS xmlns="urn:ucis"')
		with TemporaryDirectory() as directory:
			xmlFile = _write(directory, content)

			with self.assertRaises(CodeCoverageError) as context:
				_ = Document(xmlFile, analyzeAndConvert=True)

		self.assertEqual(f"Root element of '{xmlFile}' is not '<{{UCIS}}UCIS>'.", str(context.exception))
		self.assertEqual(["Got root element '<{urn:ucis}UCIS>'."], context.exception.__notes__)

	def test_Validation(self) -> None:
		"""The schema requires a history node's date."""
		content = SYNTHETIC.read_text(encoding="utf-8").replace(' date="2026-10-09T11:59:00"', "")
		with TemporaryDirectory() as directory:
			xmlFile = _write(directory, content)

			with self.assertRaises(CodeCoverageError) as context:
				_ = Document(xmlFile, analyzeAndConvert=True)

		self.assertEqual(f"Validation error for '{xmlFile}' using XSD schema 'UCIS-1.0.xsd'.", str(context.exception))
		self.assertIn("The attribute 'date' is required but missing.", context.exception.__notes__[0])

	def test_DuplicateSourceFile(self) -> None:
		content = SYNTHETIC.read_text(encoding="utf-8").replace('"tb/top.sv" id="2"', '"tb/top.sv" id="1"')
		with TemporaryDirectory() as directory:
			xmlFile = _write(directory, content)

			with self.assertRaises(CodeCoverageError) as context:
				_ = Document(xmlFile, analyzeAndConvert=True)

		self.assertEqual(f"UCIS XML file '{xmlFile}' states source file ID '1' twice.", str(context.exception))

	def test_Cobertura(self) -> None:
		"""The UCIS reader rejects a Cobertura report by its root element."""
		xmlFile = DATA.parent / "Python" / "coverage.xml"

		with self.assertRaises(CodeCoverageError) as context:
			_ = Document(xmlFile, analyzeAndConvert=True)

		self.assertEqual(f"Root element of '{xmlFile}' is not '<{{UCIS}}UCIS>'.", str(context.exception))
		self.assertEqual(["Got root element '<coverage>'."], context.exception.__notes__)

		with self.assertRaises(CodeCoverageError) as context:
			_ = CoberturaDocument(SYNTHETIC, analyzeAndConvert=True)
		self.assertEqual(["Got root element '<{UCIS}UCIS>'."], context.exception.__notes__)

	def test_FileNotFound(self) -> None:
		with self.assertRaises(CodeCoverageError) as context:
			_ = Document(DATA / "missing.xml", analyzeAndConvert=True)

		self.assertEqual(f"UCIS XML file '{DATA / 'missing.xml'}' does not exist.", str(context.exception))

	def test_NotAnalyzed(self) -> None:
		with self.assertRaises(CodeCoverageError) as context:
			Document(SYNTHETIC).Convert()

		self.assertEqual(f"UCIS XML file '{SYNTHETIC}' needs to be read and analyzed by an XML parser.",
		                 str(context.exception))
