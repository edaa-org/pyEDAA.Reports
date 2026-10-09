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
"""Unit tests of pyucis' dialect of the UCIS XML interchange format: the elements in no namespace."""
from datetime                                import datetime
from pathlib                                 import Path
from tempfile                                import TemporaryDirectory

from pyEDAA.Reports.CodeCoverage             import CodeCoverageError, LineCoverageStatus
from pyEDAA.Reports.CodeCoverage.UCIS        import Document, FormatVersion
from pyEDAA.Reports.CodeCoverage.UCIS.PyUCIS import Document as PyUCISDocument, SCHEMAS
from pyTooling.Testing                       import Testcase


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


DATA =      Path(__file__).parent.parent.parent / "data" / "CodeCoverage" / "UCIS"  #: Directory of the UCIS XML files.
SYNTHETIC = DATA / "synthetic-1.0.xml"                                             #: The hand-written UCIS 1.0 file.
BLOCKS =    DATA / "PyUCIS" / "block_statement.xml"                                #: pyucis' statement coverage.
BRANCHES =  DATA / "PyUCIS" / "branch_nested.xml"                                  #: pyucis' branch coverage.


class PyUCIS(Testcase):
	"""pyucis writes the elements in no namespace: its dialect is read with the standard's schema without namespace."""

	def test_Report(self) -> None:
		report = PyUCISDocument(BLOCKS, analyzeAndConvert=True)

		self.assertEqual((FormatVersion.Version1_0, "mballance", datetime(1771, 7, 9, 2, 3, 5)),
		                 (report.FormatVersion, report.WrittenBy, report.WrittenTime))
		self.assertEqual({1: Path("__null__file__"), 2: Path("alu.sv")},
		                 {fileID: sourceFile.Path for fileID, sourceFile in report.SourceFiles.items()})
		historyNode = report.HistoryNodes[0]
		self.assertEqual(("test_basic", "1", "42", "unknown"),
		                 (historyNode.LogicalName, historyNode.Kind, historyNode.Seed, historyNode.VendorTool))
		statement, = report.IterateStatements()
		self.assertEqual(("stmt_10", 10, 7),
		                 (statement.Alias, statement.ID.LineNumber, statement.Bin.Contents.CoverageCount))

	def test_Statements(self) -> None:
		"""A source file without coverage - pyucis' ``__null__file__`` - becomes no file."""
		summary = PyUCISDocument(BLOCKS, analyzeAndConvert=True).ToCoverageSummary()

		self.assertEqual([Path("alu.sv")], [file.Path for file in summary.IterateFiles()])
		self.assertEqual((1, 1), (summary.TotalLines, summary.CoveredLines))
		self.assertEqual({"work.alu": (10, 10)}, {
			unit.Name: (unit.StartLine.LineNumber, unit.EndLine.LineNumber) for unit in summary.IterateUnits()
		})

	def test_Branches(self) -> None:
		"""A branch goes to a line, only if the report lists that line."""
		summary = PyUCISDocument(BRANCHES, analyzeAndConvert=True).ToCoverageSummary()

		line = summary.GetOrAddFile("ctrl.sv").GetLine(20)
		self.assertEqual((LineCoverageStatus.Covered, 8), (line.Status, line.CoverageCount))
		self.assertEqual([(5, line), (3, None)], [(branch.CoverageCount, branch.Target) for branch in line.Branches])

	def test_Namespace(self) -> None:
		"""The standard's reader rejects pyucis' elements without namespace, and pyucis' reader the standard's."""
		with self.assertRaises(CodeCoverageError) as context:
			_ = Document(BLOCKS, analyzeAndConvert=True)
		self.assertEqual(f"Root element of '{BLOCKS}' is not '<{{UCIS}}UCIS>'.", str(context.exception))
		self.assertEqual(["Got root element '<UCIS>'."], context.exception.__notes__)

		with self.assertRaises(CodeCoverageError) as context:
			_ = PyUCISDocument(SYNTHETIC, analyzeAndConvert=True)
		self.assertEqual(f"Root element of '{SYNTHETIC}' is not '<UCIS>'.", str(context.exception))
		self.assertEqual(["Got root element '<{UCIS}UCIS>'."], context.exception.__notes__)

	def test_Schemas(self) -> None:
		self.assertEqual({FormatVersion.Version1_0: "PyUCIS-1.0.xsd"}, SCHEMAS)

	def test_Validation(self) -> None:
		"""The dialect's schema is the standard's: a block coverage holds statements or blocks, not both."""
		content = BLOCKS.read_text(encoding="utf-8").replace(
			"    </blockCoverage>",
			'<block><blockBin><contents coverageCount="1"/></blockBin><blockId file="2" line="11" inlineCount="1"/></block>'
			"</blockCoverage>"
		)
		with TemporaryDirectory() as directory:
			xmlFile = Path(directory) / "ucis.xml"
			xmlFile.write_text(content, encoding="utf-8")

			with self.assertRaises(CodeCoverageError) as context:
				_ = PyUCISDocument(xmlFile, analyzeAndConvert=True)

		self.assertEqual(f"Validation error for '{xmlFile}' using XSD schema 'PyUCIS-1.0.xsd'.", str(context.exception))
