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
"""Unit tests of Aldec's UCDB XML format: its model, its XML schema and the conversion to the common model."""
from pathlib                                         import Path
from tempfile                                        import TemporaryDirectory

from lxml.etree                                      import fromstring
from pyEDAA.Reports.CodeCoverage                     import CodeCoverageError, LineCoverageStatus
from pyEDAA.Reports.CodeCoverage.AldecUCDB           import Document, Report, SCHEMA, Statement
from pyEDAA.Reports.CodeCoverage.AldecUCDB.Elements  import AttributesMixin, Command, CoverType, HistoryNode
from pyEDAA.Reports.CodeCoverage.AldecUCDB.Elements  import HistoryNodeKind, Language, NAMESPACE, ScopeType
from pyEDAA.Reports.CodeCoverage.AldecUCDB.Scopes    import Bin, BinFlags, Scope, SourceLocation
from pyEDAA.Reports.CodeCoverage.Cobertura           import Document as CoberturaDocument
from pyTooling.Testing                               import Testcase


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


DATA =      Path(__file__).parent.parent.parent / "data" / "CodeCoverage" / "Aldec"  #: Directory of the reports.
MERGED =    DATA / "ucdb.xml"                         #: Riviera-PRO 2021.10: one instance, four tests merged.
INSTANCES = DATA / "ucdb000_multiple_instances.xml"   #: Two instances of a module, and a class.
EXCLUDED =  DATA / "ucdb001_all_excluded.xml"         #: All statements excluded.
PARTIAL =   DATA / "ucdb002_partially_excluded.xml"   #: The statements of one of two instances excluded.
WORK =      Path("/project")                          #: Working directory of hand-built models.


def _write(directory: str, content: str) -> Path:
	"""
	Write a report file into a directory.

	:param directory: The directory.
	:param content:   The report's text.
	:returns:         The report file.
	"""
	xmlFile = Path(directory) / "ucdb.xml"
	xmlFile.write_text(content, encoding="utf-8")
	return xmlFile


def _instances(*counts: int, flags: BinFlags = BinFlags.Is32Bit) -> Document:
	"""
	Build a report by hand: per count an instance of module ``work.M``, whose statement in line 3 of ``m.sv`` ran so
	often.

	:param counts: The statement's count per instance.
	:param flags:  Optional, the flags of the statement bins. Default: ``BinFlags.Is32Bit``.
	:returns:      The report, not read from a file.
	"""
	document = Document(Path("hand.xml"))
	source =   SourceLocation(Path("top.sv"), WORK, 1, 1)
	top =      Scope("top", ScopeType.Instance, Language.Verilog, 1, 1, source, parent=document)
	for number, count in enumerate(counts, start=1):
		source =   SourceLocation(Path("top.sv"), WORK, 7 + number, 0)
		instance = Scope(f"m{number}", ScopeType.Instance, Language.Verilog, 1, 1, source, "work.M", parent=top)
		source =   SourceLocation(Path("m.sv"), WORK, 3, 1)
		Bin("", CoverType.StatementBin, flags, count, source, {"#SINDEX#": 1}, parent=instance)

	return document


class FormatModel(Testcase):
	"""The format's model keeps what the report states: the tool, attributes, history nodes, scopes, bins, commands."""

	def test_Report(self) -> None:
		report = Document(INSTANCES, analyzeAndConvert=True)

		self.assertEqual(("Riviera-PRO", "2022.4"), (report.Tool, str(report.ToolVersion)))
		self.assertEqual({"path_separator": "/", "hier_mode": 1}, report.Attributes)
		self.assertEqual(
			["work.top", "work.DUT", "work.M", "work.UnitScopePackage_1", "work.$root($unit)", "top",
			 "\\package UnitScopePackage_1\\", "$unit.work"],
			[scope.Name for scope in report.Scopes]
		)
		self.assertEqual([], report.Commands)

	def test_HistoryNodes(self) -> None:
		"""A merge holds the tests and merges it merged."""
		merge, = Document(MERGED, analyzeAndConvert=True).HistoryNodes

		self.assertEqual(("merge", Path("cov/aggregate/aggregate.acdb"), HistoryNodeKind.Merge),
		                 (merge.Name, merge.PhysicalName, merge.Kind))
		self.assertEqual(["out4", "merge.55566235"], [node.Name for node in merge.HistoryNodes])
		test = merge.HistoryNodes[0]
		self.assertEqual((HistoryNodeKind.Test, []), (test.Kind, test.HistoryNodes))
		self.assertEqual(("Riviera-PRO", 0.0), (test.Attributes["UCIS:tool"], test.Attributes["UCIS:cost"]))
		self.assertEqual("", test.Attributes["UCIS:cmd"])

	def test_Scope(self) -> None:
		instance = Document(INSTANCES, analyzeAndConvert=True).Scopes[5].Scopes[0].Scopes[0]

		self.assertEqual(
			("m1", ScopeType.Instance, Language.Verilog, 1, 0x20000006, "work.M"),
			(instance.Name, instance.Type, instance.Language, instance.Weight, instance.Flags, instance.DesignUnit)
		)
		self.assertEqual((Path("dut.sv"), Path("/builds/gitlab/gliwice/ucdb2cobertura/tests/simple_test/project"), 40, 0), (
			instance.Source.File, instance.Source.WorkDirectory, instance.Source.LineNumber, instance.Source.Token
		))
		self.assertEqual({"#GOAL#": 100}, instance.Attributes)
		self.assertEqual([ScopeType.Branch, ScopeType.Process], [scope.Type for scope in instance.Scopes])
		self.assertEqual(6 + 4 + 6, len(list(instance.IterateBins())))

	def test_Bin(self) -> None:
		statement, *_ = Document(PARTIAL, analyzeAndConvert=True).Scopes[4].Scopes[0].Scopes[1].Bins

		self.assertEqual(("", CoverType.StatementBin, BinFlags.Is32Bit | BinFlags.ExcludeFile, 1),
		                 (statement.Name, statement.Type, statement.Flags, statement.Count))
		self.assertEqual({"#GOAL#": 1, "#SINDEX#": 1}, statement.Attributes)
		self.assertEqual((Path("dut006c.sv"), 8), (statement.Source.File, statement.Source.LineNumber))
		self.assertTrue(statement.IsExcluded)

	def test_BinTypes(self) -> None:
		"""A process states block bins by their value; a branching statement its branches by name."""
		instance = Document(PARTIAL, analyzeAndConvert=True).Scopes[4].Scopes[0].Scopes[0]
		branch, process = instance.Scopes

		self.assertEqual({CoverType.BranchBin}, {coverBin.Type for coverBin in branch.Bins})
		self.assertEqual({"true_branch"}, {coverBin.Name for coverBin in branch.Bins})
		self.assertEqual({CoverType.BlockBin}, {coverBin.Type for coverBin in process.Bins})

	def test_Flags(self) -> None:
		"""A flag not named by BinFlags is kept."""
		flags = BinFlags(0x20000041)

		self.assertEqual(0x20000041, flags)
		self.assertTrue(Bin("", CoverType.StatementBin, flags, 0, SourceLocation(Path("a.sv"), WORK, 1, 1)).IsExcluded)
		for flag in (BinFlags.ExcludePragma, BinFlags.ExcludeFile, BinFlags.ExcludeInstance, BinFlags.ExcludeAuto):
			self.assertIn(flag, BinFlags.Excluded)

	def test_Command(self) -> None:
		command, = Document(PARTIAL, analyzeAndConvert=True).Commands

		self.assertEqual((4, 44873, 1), (command.Type, command.Flags, command.Index))
		self.assertTrue(command.Data.startswith("3;1;10;dut006c.sv;63;"))


class ParentRelation(Testcase):
	"""Each element below the report names its parent and is added to it."""

	def test_Report(self) -> None:
		document =    Document(Path("ucdb.xml"))
		historyNode = HistoryNode("test", Path("test.acdb"), HistoryNodeKind.Test, parent=document)
		scope =       Scope("top", ScopeType.Instance, Language.VHDL, 1, 0, SourceLocation(Path("a.vhdl"), WORK, 1, 1),
		                    parent=document)
		command =     Command(4, 0, "", 1, parent=document)

		self.assertEqual([document] * 3, [historyNode.Parent, scope.Parent, command.Parent])
		self.assertEqual(([historyNode], [scope], [command]), (document.HistoryNodes, document.Scopes, document.Commands))

	def test_Children(self) -> None:
		merge =  HistoryNode("merge", Path("all.acdb"), HistoryNodeKind.Merge)
		test =   HistoryNode("test", Path("test.acdb"), HistoryNodeKind.Test, {"UCIS:seed": "1"}, parent=merge)
		source = SourceLocation(Path("a.sv"), WORK, 1, 1)
		top =    Scope("top", ScopeType.Instance, Language.SystemVerilog, 1, 0, source)
		inner =  Scope("u", ScopeType.Instance, Language.SystemVerilog, 1, 0, source, "work.U", parent=top)
		inside = Bin("", CoverType.StatementBin, BinFlags.Is32Bit, 2, source, parent=inner)
		outer =  Bin("", CoverType.StatementBin, BinFlags.Is32Bit, 0, source, parent=top)

		self.assertEqual((merge, top, inner, top), (test.Parent, inner.Parent, inside.Parent, outer.Parent))
		self.assertEqual(([test], [inner], [outer], [inside]), (merge.HistoryNodes, top.Scopes, top.Bins, inner.Bins))
		self.assertEqual([outer, inside], list(top.IterateBins()))

	def test_Document(self) -> None:
		"""Reading a report builds each relation."""
		report = Document(INSTANCES, analyzeAndConvert=True)

		def check(scope: Scope) -> None:
			self.assertTrue(all(coverBin.Parent is scope for coverBin in scope.Bins))
			for child in scope.Scopes:
				self.assertIs(scope, child.Parent)
				check(child)

		self.assertTrue(all(node.Parent is report for node in report.HistoryNodes))
		for scope in report.Scopes:
			self.assertIs(report, scope.Parent)
			check(scope)

	def test_Parent(self) -> None:
		"""Each element checks the type of its parent."""
		module = "pyEDAA.Reports.CodeCoverage.AldecUCDB"
		source = SourceLocation(Path("a.sv"), WORK, 1, 1)
		test =   HistoryNode("test", Path("test.acdb"), HistoryNodeKind.Test)
		scope =  Scope("top", ScopeType.Instance, Language.Verilog, 1, 0, source)
		for create, types, got in (
			(lambda: HistoryNode("t", Path("t.acdb"), HistoryNodeKind.Test, parent=scope),
			 "'Report' or 'HistoryNode'", f"{module}.Scopes.Scope"),
			(lambda: Scope("s", ScopeType.Instance, Language.Verilog, 1, 0, source, parent=test),
			 "'Report' or 'Scope'", f"{module}.Elements.HistoryNode"),
			(lambda: Bin("", CoverType.StatementBin, BinFlags.Is32Bit, 0, source, parent=test),
			 "'Scope'", f"{module}.Elements.HistoryNode"),
			(lambda: Command(4, 0, "", 1, parent=scope), "'Report'", f"{module}.Scopes.Scope")
		):
			with self.subTest(types=types, got=got):
				with self.assertRaises(TypeError) as context:
					_ = create()
				self.assertEqual(f"Parameter 'parent' is not of type {types}.", str(context.exception))
				self.assertEqual([f"Got type '{got}'."], context.exception.__notes__)


class Construction(Testcase):
	"""Each constructor checks its parameters: ``None``, then the type, then the value."""

	def test_Checks(self) -> None:
		source = SourceLocation(Path("a.sv"), WORK, 1, 1)
		test =   HistoryNodeKind.Test
		stmt =   CoverType.StatementBin
		flags =  BinFlags.Is32Bit
		vlog =   Language.Verilog
		inst =   ScopeType.Instance
		for create, exception, message in (
			(lambda: SourceLocation(None, WORK, 1, 1),               ValueError,
			 "Parameter 'file' is None."),
			(lambda: SourceLocation("a.sv", WORK, 1, 1),             TypeError,
			 "Parameter 'file' is not of type 'Path'."),
			(lambda: SourceLocation(Path("a"), "/w", 1, 1),          TypeError,
			 "Parameter 'workDirectory' is not of type 'Path'."),
			(lambda: SourceLocation(Path("a"), WORK, -1, 1),         ValueError,
			 "Parameter 'lineNumber' is negative."),
			(lambda: SourceLocation(Path("a"), WORK, 1, None),       ValueError,
			 "Parameter 'token' is None."),
			(lambda: HistoryNode(None, Path("t"), test),             ValueError,
			 "Parameter 'name' is None."),
			(lambda: HistoryNode("", Path("t"), test),               ValueError,
			 "Parameter 'name' is empty."),
			(lambda: HistoryNode("t", "t.acdb", test),               TypeError,
			 "Parameter 'physicalName' is not of type 'Path'."),
			(lambda: HistoryNode("t", Path("t"), 1),                 TypeError,
			 "Parameter 'kind' is not of type 'HistoryNodeKind'."),
			(lambda: HistoryNode("t", Path("t"), test, []),          TypeError,
			 "Parameter 'attributes' is not a mapping."),
			(lambda: HistoryNode("t", Path("t"), test, {1: 1}),      TypeError,
			 "Parameter 'attributes' contains a key not of type 'str'."),
			(lambda: HistoryNode("t", Path("t"), test, {"": 1}),     ValueError,
			 "Parameter 'attributes' contains an empty key."),
			(lambda: HistoryNode("t", Path("t"), test, {"k": None}), TypeError,
			 "Parameter 'attributes' contains a value not of type 'int', 'float' or 'str'."),
			(lambda: Scope("", inst, vlog, 1, 0, source),            ValueError,
			 "Parameter 'name' is empty."),
			(lambda: Scope("s", "INSTANCE", vlog, 1, 0, source),     TypeError,
			 "Parameter 'scopeType' is not of type 'ScopeType'."),
			(lambda: Scope("s", inst, None, 1, 0, source),           ValueError,
			 "Parameter 'language' is None."),
			(lambda: Scope("s", inst, vlog, -1, 0, source),          ValueError,
			 "Parameter 'weight' is negative."),
			(lambda: Scope("s", inst, vlog, 1, "0", source),         TypeError,
			 "Parameter 'flags' is not of type 'int'."),
			(lambda: Scope("s", inst, vlog, 1, 0, None),             ValueError,
			 "Parameter 'source' is None."),
			(lambda: Scope("s", inst, vlog, 1, 0, source, ""),       ValueError,
			 "Parameter 'designUnit' is empty."),
			(lambda: Bin(1, stmt, flags, 0, source),                 TypeError,
			 "Parameter 'name' is not of type 'str'."),
			(lambda: Bin("", "STMTBIN", flags, 0, source),           TypeError,
			 "Parameter 'coverType' is not of type 'CoverType'."),
			(lambda: Bin("", stmt, 1, 0, source),                    TypeError,
			 "Parameter 'flags' is not of type 'BinFlags'."),
			(lambda: Bin("", stmt, flags, -1, source),               ValueError,
			 "Parameter 'count' is negative."),
			(lambda: Bin("", stmt, flags, 0, Path("a.sv")),          TypeError,
			 "Parameter 'source' is not of type 'SourceLocation'."),
			(lambda: Command("4", 0, "", 1),                         TypeError,
			 "Parameter 'commandType' is not of type 'int'."),
			(lambda: Command(4, -1, "", 1),                          ValueError,
			 "Parameter 'flags' is negative."),
			(lambda: Command(4, 0, None, 1),                         ValueError,
			 "Parameter 'data' is None."),
			(lambda: Command(4, 0, "", -1),                          ValueError,
			 "Parameter 'index' is negative."),
			(lambda: Statement(Path("a"), 0, 1, []),                 ValueError,
			 "Parameter 'lineNumber' is less than 1."),
			(lambda: Statement(Path("a"), 1, 1, None),               ValueError,
			 "Parameter 'bins' is None."),
			(lambda: Statement(Path("a"), 1, 1, 3),                  TypeError,
			 "Parameter 'bins' is not iterable."),
			(lambda: Statement(Path("a"), 1, 1, [3]),                TypeError,
			 "Parameter 'bins' contains an element not of type 'Bin'."),
			(lambda: Statement(Path("a"), 1, 1, []),                 ValueError,
			 "Parameter 'bins' is empty.")
		):
			with self.subTest(message=message):
				with self.assertRaises(exception) as context:
					_ = create()
				self.assertEqual(message, str(context.exception))

	def test_Attributes(self) -> None:
		"""The attributes are copied, not referenced."""
		attributes = {"#GOAL#": 100, "UCIS:cpu_time": 0.5, "UCIS:tool": "Riviera-PRO"}
		source =     SourceLocation(Path("a.vhdl"), WORK, 1, 1)
		scope =      Scope("top", ScopeType.Instance, Language.VHDL, 1, 0, source, None, attributes)
		attributes["#GOAL#"] = 0

		self.assertEqual({"#GOAL#": 100, "UCIS:cpu_time": 0.5, "UCIS:tool": "Riviera-PRO"}, scope.Attributes)

	def test_Statement(self) -> None:
		"""A statement's count is the sum of its bins, which aren't excluded; it is excluded, if all are."""
		source =   SourceLocation(Path("a.sv"), WORK, 3, 1)
		ran =      Bin("", CoverType.StatementBin, BinFlags.Is32Bit, 2, source)
		excluded = Bin("", CoverType.StatementBin, BinFlags.Is32Bit | BinFlags.ExcludeInstance, 5, source)
		statement = Statement(Path("a.sv"), 3, 1, (ran, excluded, ran))

		self.assertEqual((Path("a.sv"), 3, 1, 4, False), (
			statement.File, statement.LineNumber, statement.Index, statement.Count, statement.IsExcluded
		))
		self.assertEqual([ran, excluded, ran], statement.Bins)
		self.assertTrue(Statement(Path("a.sv"), 3, 1, (excluded, )).IsExcluded)


class Parsing(Testcase):
	"""Each element is read by its class method ``Parse``."""

	def test_Bin(self) -> None:
		coverBin = Bin.Parse(fromstring(
			f"<ux:bin xmlns:ux='{NAMESPACE}' name='' type='STMTBIN' flags='00000041'>"
			"<ux:attr key='#SINDEX#' type='int'>2</ux:attr><ux:count type='int'>7</ux:count>"
			"<ux:src file='a.sv' workdir='/w' line='12' token='1'/></ux:bin>"
		))

		self.assertEqual((CoverType.StatementBin, 7, {"#SINDEX#": 2}, True, 12), (
			coverBin.Type, coverBin.Count, coverBin.Attributes, coverBin.IsExcluded, coverBin.Source.LineNumber
		))

	def test_AttributeValue(self) -> None:
		"""An attribute's value must be of the type the attribute states."""
		element = fromstring(f"<ux:hnode xmlns:ux='{NAMESPACE}'><ux:attr key='UCIS:seed' type='int'>x</ux:attr></ux:hnode>")

		with self.assertRaises(CodeCoverageError) as context:
			_ = AttributesMixin._ParseAttributes(element)

		self.assertEqual("UCDB attribute 'UCIS:seed' states a value not of type 'int'.", str(context.exception))
		self.assertEqual(["Got value 'x'."], context.exception.__notes__)
		self.assertIsInstance(context.exception.__cause__, ValueError)


class Statements(Testcase):
	"""The statements are the statement bins of the instances, one per bin or merged over all instances."""

	def _counts(self, xmlFile: Path, mergeInstances: bool) -> tuple[int, int]:
		statements = [s for s in Document(xmlFile, analyzeAndConvert=True).IterateStatements(mergeInstances)]
		included =   [s for s in statements if not s.IsExcluded]
		return len(included), sum(1 for statement in included if statement.Count > 0)

	def test_MultipleInstances(self) -> None:
		self.assertEqual((15, 14), self._counts(INSTANCES, False))
		self.assertEqual((9, 8), self._counts(INSTANCES, True))

	def test_AllExcluded(self) -> None:
		self.assertEqual((0, 0), self._counts(EXCLUDED, False))
		self.assertEqual((0, 0), self._counts(EXCLUDED, True))

	def test_PartiallyExcluded(self) -> None:
		self.assertEqual((5, 4), self._counts(PARTIAL, False))
		self.assertEqual((5, 4), self._counts(PARTIAL, True))

	def test_Merged(self) -> None:
		self.assertEqual((112, 112), self._counts(MERGED, False))

	def test_DesignUnits(self) -> None:
		"""A design unit's statement bins - module ``work.M`` states six - aren't statements."""
		report = Document(INSTANCES, analyzeAndConvert=True)

		self.assertEqual(6, sum(1 for b in report.Scopes[2].IterateBins() if b.Type is CoverType.StatementBin))
		self.assertEqual(15, len(list(report.IterateStatements())))

	def test_Merge(self) -> None:
		"""Merged, a statement ran as often as in all instances together."""
		statement, = _instances(0, 3).IterateStatements(mergeInstances=True)

		self.assertEqual((Path("m.sv"), 3, 1, 3, 2), (
			statement.File, statement.LineNumber, statement.Index, statement.Count, len(statement.Bins)
		))
		self.assertEqual([0, 3], [s.Count for s in _instances(0, 3).IterateStatements()])

	def test_NoStatementIndex(self) -> None:
		document = _instances(1)
		document.Scopes[0].Scopes[0].Bins[0]._attributes.clear()

		with self.assertRaises(CodeCoverageError) as context:
			_ = list(document.IterateStatements())

		self.assertEqual("UCDB statement bin at 'm.sv:3' states no statement index.", str(context.exception))

	def test_MergeInstances(self) -> None:
		for value, exception, message in (
			(None, ValueError, "Parameter 'mergeInstances' is None."),
			(1,    TypeError,  "Parameter 'mergeInstances' is not of type 'bool'.")
		):
			with self.subTest(value=value):
				with self.assertRaises(exception) as context:
					_ = list(Report.IterateStatements(_instances(1), value))
				self.assertEqual(message, str(context.exception))


class Conversion(Testcase):
	"""The statement coverage is converted to lines of the common model."""

	def test_Lines(self) -> None:
		"""A line is covered, if all its statements ran; it ran as often as its least often run statement."""
		for mergeInstances in (False, True):
			with self.subTest(mergeInstances=mergeInstances):
				summary = Document(INSTANCES, analyzeAndConvert=True).ToCoverageSummary(mergeInstances)
				file, = summary.IterateFiles()

				self.assertEqual(Path("dut.sv"), file.Path)
				self.assertEqual((7, 6, 0), (summary.TotalLines, summary.CoveredLines, summary.ExcludedLines))
				self.assertEqual(
					{6: 1, 7: 0, 9: 1, 25: 1, 26: 1, 27: 1, 28: 1},
					{line.LineNumber: int(line.Status is LineCoverageStatus.Covered) for line in file.IterateLines()}
				)

		self.assertEqual(LineCoverageStatus.Uncovered, file.GetLine(7).Status)
		self.assertEqual(0, file.GetLine(7).CoverageCount)

	def test_Counts(self) -> None:
		file, = Document(MERGED, analyzeAndConvert=True).ToCoverageSummary().IterateFiles()

		self.assertEqual((Path("Verilog/board.v"), 112, 112), (file.Path, file.TotalLines, file.CoveredLines))
		self.assertEqual((194, 88, None), (file.LastLineNumber, file.GetLine(37).CoverageCount, file.GetLine(36)))

	def test_Excluded(self) -> None:
		"""A line, whose statements are all excluded, is excluded; the file is listed."""
		for xmlFile, files, figures in (
			(EXCLUDED, [Path("dut.sv")],                         (0, 0, 7)),
			(PARTIAL,  [Path("dut006b.sv"), Path("dut006c.sv")], (5, 4, 5))
		):
			with self.subTest(file=xmlFile.name):
				summary = Document(xmlFile, analyzeAndConvert=True).ToCoverageSummary()

				self.assertEqual(files, [file.Path for file in summary.IterateFiles()])
				self.assertEqual(figures, (summary.TotalLines, summary.CoveredLines, summary.ExcludedLines))

		excluded = summary.Files["dut006c.sv"]
		self.assertEqual({LineCoverageStatus.Excluded}, {line.Status for line in excluded.IterateLines()})

	def test_MergeInstances(self) -> None:
		"""A line ran by one of two instances is covered only, if the instances are merged."""
		summary = _instances(4, 0).ToCoverageSummary()
		self.assertEqual((1, 0), (summary.TotalLines, summary.CoveredLines))

		line, = _instances(4, 0).ToCoverageSummary(mergeInstances=True).Files["m.sv"].IterateLines()
		self.assertEqual((LineCoverageStatus.Covered, 4), (line.Status, line.CoverageCount))

	def test_ExcludedInstance(self) -> None:
		"""An instance's excluded statement doesn't count for the line."""
		document = _instances(0, 2)
		document.Scopes[0].Scopes[0].Bins[0]._flags = BinFlags.Is32Bit | BinFlags.ExcludeInstance

		line, = document.ToCoverageSummary().Files["m.sv"].IterateLines()
		self.assertEqual((LineCoverageStatus.Covered, 2), (line.Status, line.CoverageCount))

	def test_Summary(self) -> None:
		"""The summary is named after the report file; its source directories are the directories the tool ran in."""
		summary = Document(PARTIAL, analyzeAndConvert=True).ToCoverageSummary()

		self.assertEqual("ucdb002_partially_excluded", summary.Name)
		self.assertEqual(
			[Path("/builds/gitlab/gliwice/ucdb2cobertura/tests/simple_test/project")], summary.SourceDirectories
		)
		self.assertEqual({}, summary.Units)

	def test_Cobertura(self) -> None:
		"""Written as Cobertura XML, the same figures are read back."""
		with TemporaryDirectory() as directory:
			xmlFile = Path(directory) / "cobertura.xml"
			summary = Document(INSTANCES, analyzeAndConvert=True).ToCoverageSummary()
			CoberturaDocument.FromCoverageSummary(xmlFile, summary).Write(overwrite=True, regenerate=True)

			readBack = CoberturaDocument(xmlFile, analyzeAndConvert=True).ToCoverageSummary()

		self.assertEqual((7, 6), (readBack.TotalLines, readBack.CoveredLines))


class Schema(Testcase):
	"""A report is validated against the XML schema; its root element must be ``<ux:ucdb>``."""

	def _reject(self, content: str) -> CodeCoverageError:
		with TemporaryDirectory() as directory:
			xmlFile = _write(directory, content)
			with self.assertRaises(CodeCoverageError) as context:
				_ = Document(xmlFile, analyzeAndConvert=True)

		self.assertEqual(f"Validation error for '{xmlFile}' using XSD schema '{SCHEMA}'.", str(context.exception))
		return context.exception

	def test_Schema(self) -> None:
		self.assertEqual("Aldec-UCDB.xsd", SCHEMA)

	def test_UnknownAttribute(self) -> None:
		content = PARTIAL.read_text(encoding="utf-8").replace('lang="VLOG"', 'hits="4" lang="VLOG"', 1)
		ex =      self._reject(content)
		self.assertIn("The attribute 'hits' is not allowed.", ex.__notes__[0])

	def test_ScopeType(self) -> None:
		ex = self._reject(PARTIAL.read_text(encoding="utf-8").replace('type="DU_MODULE"', 'type="DU_ENTITY"', 1))
		self.assertIn("'DU_ENTITY' is not an element of the set", ex.__notes__[0])

	def test_DuplicateAttribute(self) -> None:
		"""An element states an attribute key once."""
		content = PARTIAL.read_text(encoding="utf-8").replace(
			'<ux:attr key="hier_mode" type="int">1</ux:attr>',
			'<ux:attr key="hier_mode" type="int">1</ux:attr>\n<ux:attr key="hier_mode" type="int">2</ux:attr>'
		)
		self.assertIn("Duplicate key-sequence ['hier_mode']", self._reject(content).__notes__[0])

	def test_Version(self) -> None:
		ex = self._reject(PARTIAL.read_text(encoding="utf-8").replace('version="Riviera-PRO 2022.04"', 'version="2022.04"'))
		self.assertIn("'2022.04' is not accepted by the pattern", ex.__notes__[0])

	def test_Root(self) -> None:
		"""The reader rejects a Cobertura report by its root element."""
		xmlFile = DATA.parent / "Python" / "coverage.xml"

		with self.assertRaises(CodeCoverageError) as context:
			_ = Document(xmlFile, analyzeAndConvert=True)

		self.assertEqual(
			f"Root element of '{xmlFile}' is not '<ux:ucdb>' of namespace 'www.aldec.com'.", str(context.exception)
		)
		self.assertEqual(["Got root element '<coverage>'."], context.exception.__notes__)

	def test_Cobertura(self) -> None:
		"""The Cobertura reader rejects a UCDB report by its root element."""
		with self.assertRaises(CodeCoverageError) as context:
			_ = CoberturaDocument(PARTIAL, analyzeAndConvert=True)

		self.assertEqual([f"Got root element '<{{{NAMESPACE}}}ucdb>'."], context.exception.__notes__)

	def test_FileNotFound(self) -> None:
		with self.assertRaises(CodeCoverageError) as context:
			_ = Document(DATA / "missing.xml", analyzeAndConvert=True)

		self.assertEqual(f"Aldec UCDB file '{DATA / 'missing.xml'}' does not exist.", str(context.exception))

	def test_Unreadable(self) -> None:
		"""A directory can't be read as a file."""
		with self.assertRaises(CodeCoverageError) as context:
			_ = Document(DATA, analyzeAndConvert=True)

		self.assertEqual(f"Couldn't read Aldec UCDB file '{DATA}'.", str(context.exception))
		self.assertIsInstance(context.exception.__cause__, OSError)

	def test_NotAnalyzed(self) -> None:
		with self.assertRaises(CodeCoverageError) as context:
			Document(PARTIAL).Convert()

		self.assertEqual(
			f"Aldec UCDB file '{PARTIAL}' needs to be read and analyzed by an XML parser.", str(context.exception)
		)
