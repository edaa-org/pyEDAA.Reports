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
"""Unit tests of the classes of LLVM's format model: constructed from typed values, or parsed from JSON elements."""
from json                             import dumps
from pathlib                          import Path
from tempfile                         import TemporaryDirectory

from pyEDAA.Reports.CodeCoverage.LLVM import BranchRegion, Counters, Document, Expansion, File, Function, MCDCRecord
from pyEDAA.Reports.CodeCoverage.LLVM import Region, RegionKind, Segment, Summary, TestVector as MCDCTestVector
from pyTooling.Testing                import Testcase
from pyTooling.Versioning             import SemanticVersion


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


def _counters(count: int = 4, covered: int = 3) -> Counters:
	"""
	Create counters.

	:param count:   Optional, number of lines, functions or regions. Default: ``4``.
	:param covered: Optional, number of the covered ones. Default: ``3``.
	:returns:       The counters.
	"""
	return Counters(count, covered, covered * 100.0 / count)


def _summary() -> Summary:
	"""
	Create a summary without branches and MC/DC conditions.

	:returns: The summary.
	"""
	return Summary(_counters(), _counters(1, 1), _counters(1, 1), _counters())


class Construction(Testcase):
	"""Each class of the format's model is constructed from typed values."""

	def test_Segment(self) -> None:
		segment = Segment(3, 33, 2, True, True)

		self.assertEqual((3, 33, 2, True, True, False), (
			segment.Line, segment.Column, segment.Count, segment.HasCount, segment.IsRegionEntry, segment.IsGapRegion
		))
		self.assertTrue(Segment(3, 1, 0, False, False, True).IsGapRegion)

	def test_Region(self) -> None:
		region = Region(6, 30, 8, 2, 3, 0, 1, RegionKind.Expansion)

		self.assertEqual((6, 30, 8, 2, 3, 0, 1, RegionKind.Expansion), (
			region.LineStart, region.ColumnStart, region.LineEnd, region.ColumnEnd, region.Count, region.FileID,
			region.ExpandedFileID, region.Kind
		))

	def test_BranchRegion(self) -> None:
		branch = BranchRegion(12, 18, 12, 27, 3, 1, 0, 0, RegionKind.Branch)

		self.assertEqual((12, 18, 12, 27, 3, 1, 0, 0, RegionKind.Branch), (
			branch.LineStart, branch.ColumnStart, branch.LineEnd, branch.ColumnEnd, branch.TrueCount, branch.FalseCount,
			branch.FileID, branch.ExpandedFileID, branch.Kind
		))

	def test_MCDCRecord(self) -> None:
		record = MCDCRecord(24, 6, 24, 85, None, 0, RegionKind.MCDCDecision, (False, True))

		self.assertEqual((None, None, None, [False, True], []), (
			record.FileID, record.TrueDecisions, record.FalseDecisions, record.Conditions, record.TestVectors
		))

		testVector = MCDCTestVector([True, None], True, False)
		record = MCDCRecord(24, 6, 24, 85, 0, 0, RegionKind.MCDCDecision, [True], 2, 0, (testVector, ))

		self.assertEqual((0, 2, 0, [testVector]), (
			record.FileID, record.TrueDecisions, record.FalseDecisions, record.TestVectors
		))
		self.assertEqual(([True, None], True, False), (testVector.Conditions, testVector.Executed, testVector.Result))

	def test_Expansion(self) -> None:
		source = Region(20, 9, 20, 20, 2, 0, 1, RegionKind.Expansion)
		target = Region(3, 33, 3, 60, 2, 1, 0, RegionKind.Code)
		expansion = Expansion([Path("/project/src/Statistics.c")] * 2, source, [target])

		self.assertIs(source, expansion.SourceRegion)
		self.assertEqual(([target], []), (expansion.TargetRegions, expansion.Branches))
		self.assertEqual(2, len(expansion.FilePaths))

	def test_Summary(self) -> None:
		lines = _counters()
		summary = _summary()

		self.assertEqual((4, 3, None, 75.0), (lines.Count, lines.Covered, lines.NotCovered, lines.Percent))
		self.assertEqual((None, None), (summary.Branches, summary.MCDC))

		branches = Counters(2, 1, 50, 1)
		summary = Summary(lines, _counters(1, 1), _counters(1, 1), _counters(), branches, Counters(2, 1, 50, 1))

		self.assertIs(lines, summary.Lines)
		self.assertEqual((branches, 1), (summary.Branches, summary.MCDC.NotCovered))

	def test_File(self) -> None:
		summary = _summary()
		file = File(Path("/project/src/Statistics.c"), summary)

		self.assertEqual((Path("/project/src/Statistics.c"), summary), (file.Path, file.Summary))
		self.assertEqual(([], [], [], []), (file.Segments, file.Branches, file.MCDCRecords, file.Expansions))

		segment = Segment(3, 33, 2, True, True)
		file = File(Path("Statistics.c"), _summary(), segments=(segment, ))
		self.assertEqual([segment], file.Segments)

	def test_Function(self) -> None:
		regions = [Region(20, 9, 20, 20, 2, 0, 1, RegionKind.Expansion), Region(3, 33, 3, 60, 2, 1, 0, RegionKind.Code)]
		function = Function("Clamp", 2, regions, [Path("/project/src/Statistics.h"), Path("/project/src/Statistics.c")])

		self.assertEqual(("Clamp", 2, regions, [], []), (
			function.Name, function.Count, function.Regions, function.Branches, function.MCDCRecords
		))
		self.assertEqual(0, function.MainFileID)

	def test_Report(self) -> None:
		report = Document(Path("coverage.json"))

		self.assertEqual((None, {}, [], None), (report.Version, report.Files, report.Functions, report.Totals))

		file = File(Path("/project/src/Statistics.c"), _summary())
		function = Function("main", 1, [Region(1, 1, 3, 2, 1, 0, 0, RegionKind.Code)], [file.Path])
		totals = _summary()
		report = Document(
			Path("coverage.json"), version=SemanticVersion.Parse("2.0.1"), files=[file], functions=[function], totals=totals
		)

		self.assertEqual(("2.0.1", {file.Path: file}, [function], totals), (
			report.Version, report.Files, report.Functions, report.Totals
		))


class ParameterChecks(Testcase):
	"""The constructors check their parameters: ``None``, then the type, then the value."""

	def test_Segment(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = Segment(None, 1, 0, True, True)

		self.assertEqual("Parameter 'line' is None.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = Segment(1, "1", 0, True, True)

		self.assertEqual("Parameter 'column' is not of type 'int'.", str(context.exception))
		self.assertEqual(["Got type 'str'."], context.exception.__notes__)

		with self.assertRaises(ValueError) as context:
			_ = Segment(0, 1, 0, True, True)

		self.assertEqual("Parameter 'line' is less than 1.", str(context.exception))
		self.assertEqual(["Got value '0'."], context.exception.__notes__)

		with self.assertRaises(TypeError) as context:
			_ = Segment(1, 1, 0, 1, True)

		self.assertEqual("Parameter 'hasCount' is not of type 'bool'.", str(context.exception))
		self.assertEqual(["Got type 'int'."], context.exception.__notes__)

	def test_Region(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = Region(1, 1, 1, 2, 0, None, 0, RegionKind.Code)

		self.assertEqual("Parameter 'fileID' is None.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = Region(1, 1, 1, 2, 0, 0, 0, 0)

		self.assertEqual("Parameter 'kind' is not of type 'RegionKind'.", str(context.exception))
		self.assertEqual(["Got type 'int'."], context.exception.__notes__)

		with self.assertRaises(ValueError) as context:
			_ = BranchRegion(1, 1, 1, 2, 1, -1, 0, 0, RegionKind.Branch)

		self.assertEqual("Parameter 'falseCount' is negative.", str(context.exception))
		self.assertEqual(["Got value '-1'."], context.exception.__notes__)

	def test_MCDCRecord(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = MCDCRecord(1, 1, 1, 2, None, 0, RegionKind.MCDCDecision, None)

		self.assertEqual("Parameter 'conditions' is None.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = MCDCRecord(1, 1, 1, 2, None, 0, RegionKind.MCDCDecision, [1])

		self.assertEqual("Parameter 'conditions' contains an element not of type 'bool'.", str(context.exception))
		self.assertEqual(["Got type 'int'."], context.exception.__notes__)

		with self.assertRaises(TypeError) as context:
			_ = MCDCTestVector([True], True, 1)

		self.assertEqual("Parameter 'result' is not of type 'bool'.", str(context.exception))

	def test_Expansion(self) -> None:
		source = Region(20, 9, 20, 20, 2, 0, 1, RegionKind.Expansion)
		with self.assertRaises(TypeError) as context:
			_ = Expansion([Path("Statistics.c")], source, 5)

		self.assertEqual("Parameter 'targetRegions' is not iterable.", str(context.exception))
		self.assertEqual(["Got type 'int'."], context.exception.__notes__)

		with self.assertRaises(TypeError) as context:
			_ = Expansion(["Statistics.c"], source, [])

		self.assertEqual("Parameter 'filePaths' contains an element not of type 'Path'.", str(context.exception))
		self.assertEqual(["Got type 'str'."], context.exception.__notes__)

	def test_Summary(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = Counters(2, 1, 100.5)

		self.assertEqual("Parameter 'percent' is out of range 0..100.", str(context.exception))
		self.assertEqual(["Got value '100.5'."], context.exception.__notes__)

		with self.assertRaises(ValueError) as context:
			_ = Summary(None, _counters(), _counters(), _counters())

		self.assertEqual("Parameter 'lines' is None.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = Summary(_counters(), _counters(), _counters(), _counters(), mcdc={})

		self.assertEqual("Parameter 'mcdc' is not of type 'Counters'.", str(context.exception))
		self.assertEqual(["Got type 'dict'."], context.exception.__notes__)

	def test_File(self) -> None:
		with self.assertRaises(TypeError) as context:
			_ = File("Statistics.c", _summary())

		self.assertEqual("Parameter 'path' is not of type 'Path'.", str(context.exception))
		self.assertEqual(["Got type 'str'."], context.exception.__notes__)

	def test_Function(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = Function("", 0, [], [])

		self.assertEqual("Parameter 'name' is empty.", str(context.exception))

	def test_Report(self) -> None:
		with self.assertRaises(TypeError) as context:
			_ = Document(Path("coverage.json"), version="2.0.1")

		self.assertEqual("Parameter 'version' is not of type 'SemanticVersion'.", str(context.exception))
		self.assertEqual(["Got type 'str'."], context.exception.__notes__)

		with self.assertRaises(TypeError) as context:
			_ = Document(Path("coverage.json"), files=[Function("main", 0, [], [])])

		self.assertEqual("Parameter 'files' contains an element not of type 'File'.", str(context.exception))
		self.assertEqual(["Got type 'pyEDAA.Reports.CodeCoverage.LLVM.Function'."], context.exception.__notes__)


class Parse(Testcase):
	"""``Parse`` reads a JSON element - an array or an object - and calls the constructor."""

	def test_Segment(self) -> None:
		"""Format 2.0.0 has no gap flag in a segment."""
		self.assertFalse(Segment.Parse([3, 33, 2, True, True]).IsGapRegion)
		self.assertTrue(Segment.Parse([3, 33, 2, True, True, True]).IsGapRegion)

	def test_Region(self) -> None:
		region = Region.Parse([6, 30, 8, 2, 3, 0, 0, 0])
		self.assertEqual((6, 2, 3, RegionKind.Code), (region.LineStart, region.ColumnEnd, region.Count, region.Kind))

		branch = BranchRegion.Parse([12, 18, 12, 27, 3, 1, 1, 0, 6])
		self.assertEqual((3, 1, 1, RegionKind.MCDCBranch), (
			branch.TrueCount, branch.FalseCount, branch.FileID, branch.Kind
		))

	def test_MCDCRecord(self) -> None:
		"""An MC/DC record grows with the format: 3.0.0 adds the decisions, 3.0.1 the file ID, 3.1.0 the test vectors."""
		testVector = {"conditions": [True, None], "executed": False, "result": None}
		for record, expected in (
			([24, 6, 24, 85, 0, 5, [False]],                         (None, 0, None, None, [False], 0)),
			([24, 6, 24, 85, 2, 1, 0, 5, [True]],                    (None, 0, 2, 1, [True], 0)),
			([24, 6, 24, 85, 2, 1, 1, 0, 5, [True]],                 (1, 0, 2, 1, [True], 0)),
			([24, 6, 24, 85, 2, 1, 1, 0, 5, [True], [testVector]],   (1, 0, 2, 1, [True], 1))
		):
			with self.subTest(length=len(record)):
				mcdc = MCDCRecord.Parse(record)

				self.assertEqual(expected, (
					mcdc.FileID, mcdc.ExpandedFileID, mcdc.TrueDecisions, mcdc.FalseDecisions, mcdc.Conditions,
					len(mcdc.TestVectors)
				))
				self.assertIs(RegionKind.MCDCDecision, mcdc.Kind)

		vector = MCDCRecord.Parse([24, 6, 24, 85, 2, 1, 1, 0, 5, [True], [testVector]]).TestVectors[0]
		self.assertEqual(([True, None], False, None), (vector.Conditions, vector.Executed, vector.Result))

	def test_Summary(self) -> None:
		counters = {"count": 2, "covered": 1, "percent": 50}
		summary = Summary.Parse({"lines": counters, "functions": counters, "instantiations": counters, "regions": counters})

		self.assertEqual((2, 1, None, 50), (
			summary.Lines.Count, summary.Lines.Covered, summary.Lines.NotCovered, summary.Lines.Percent
		))
		self.assertEqual((None, None), (summary.Branches, summary.MCDC))
		self.assertEqual(1, Counters.Parse({**counters, "notcovered": 1}).NotCovered)

	def test_File(self) -> None:
		"""A summary-only report has only a file's name and summary; a Windows path uses backslashes."""
		counters = {"count": 0, "covered": 0, "percent": 0}
		summary = {"lines": counters, "functions": counters, "instantiations": counters, "regions": counters}
		file = File.Parse({"filename": "C:\\project\\src\\Statistics.c", "summary": summary})

		self.assertEqual(Path("C:/project/src/Statistics.c"), file.Path)
		self.assertEqual(([], [], [], []), (file.Segments, file.Branches, file.MCDCRecords, file.Expansions))

		expansion = Expansion.Parse({
			"filenames": ["src\\Statistics.c", "src\\Statistics.c"],
			"source_region": [20, 9, 20, 20, 2, 0, 1, 1],
			"target_regions": [[3, 33, 3, 60, 2, 1, 0, 0]]
		})
		self.assertEqual(([Path("src/Statistics.c")] * 2, RegionKind.Expansion, 1, []), (
			expansion.FilePaths, expansion.SourceRegion.Kind, len(expansion.TargetRegions), expansion.Branches
		))

	def test_Function(self) -> None:
		function = Function.Parse({
			"name": "Statistics.c:Square", "count": 3, "regions": [[6, 30, 8, 2, 3, 0, 0, 0]],
			"filenames": ["/project/src/Statistics.c"]
		})

		self.assertEqual(("Statistics.c:Square", 3, [Path("/project/src/Statistics.c")], [], [], 1), (
			function.Name, function.Count, function.FilePaths, function.Branches, function.MCDCRecords,
			len(function.Regions)
		))

	def test_Report(self) -> None:
		"""A report written with ``-skip-functions`` has no functions."""
		counters = {"count": 0, "covered": 0, "percent": 0}
		summary = {"lines": counters, "functions": counters, "instantiations": counters, "regions": counters}
		with TemporaryDirectory() as directory:
			jsonFile = Path(directory) / "coverage.json"
			jsonFile.write_text(dumps({"version": "2.0.1", "type": "llvm.coverage.json.export", "data": [{
				"files": [{"filename": "/project/src/Statistics.c", "summary": summary}], "totals": summary
			}]}), encoding="utf-8")
			report = Document(jsonFile, analyzeAndConvert=True)

		self.assertEqual(("2.0.1", [Path("/project/src/Statistics.c")], [], 0), (
			report.Version, list(report.Files), report.Functions, report.Totals.Lines.Count
		))


class Tree(Testcase):
	"""Every element knows the element containing it, and the report's root."""

	def test_Parsed(self) -> None:
		"""Each collection of a parsed report holds its own element type, with its owner as parent, the report as root."""
		document = Document(Path("tests/data/CodeCoverage/LLVM/coverage-3.1.0.json"), analyzeAndConvert=True)

		self.assertGreater(len(document.Files), 0)
		for file in document.Files.values():
			self.assertIsInstance(file, File)
			self.assertIs(document, file.Parent)
			self.assertIs(document, file.Root)

			self.assertGreater(len(file.Segments), 0)
			for segment in file.Segments:
				self.assertIsInstance(segment, Segment)
				self.assertIs(file, segment.Parent)
				self.assertIs(document, segment.Root)

			for branch in file.Branches:
				self.assertIsInstance(branch, BranchRegion)
				self.assertIs(file, branch.Parent)
				self.assertIs(document, branch.Root)

			for record in file.MCDCRecords:
				self.assertIsInstance(record, MCDCRecord)
				self.assertIs(file, record.Parent)
				self.assertIs(document, record.Root)

			for expansion in file.Expansions:
				self.assertIsInstance(expansion, Expansion)
				self.assertIs(file, expansion.Parent)
				self.assertIs(document, expansion.Root)

				self.assertIsInstance(expansion.SourceRegion, Region)
				self.assertIs(expansion, expansion.SourceRegion.Parent)
				self.assertIs(document, expansion.SourceRegion.Root)

				for region in expansion.TargetRegions:
					self.assertIsInstance(region, Region)
					self.assertIs(expansion, region.Parent)
					self.assertIs(document, region.Root)

				for branch in expansion.Branches:
					self.assertIsInstance(branch, BranchRegion)
					self.assertIs(expansion, branch.Parent)
					self.assertIs(document, branch.Root)

			summary = file.Summary
			self.assertIsInstance(summary, Summary)
			self.assertIs(file, summary.Parent)
			self.assertIs(document, summary.Root)

			for counters in (summary.Lines, summary.Functions, summary.Instantiations, summary.Regions, summary.Branches):
				self.assertIsInstance(counters, Counters)
				self.assertIs(summary, counters.Parent)
				self.assertIs(document, counters.Root)

		self.assertGreater(len(document.Functions), 0)
		for function in document.Functions:
			self.assertIsInstance(function, Function)
			self.assertIs(document, function.Parent)
			self.assertIs(document, function.Root)

			self.assertGreater(len(function.Regions), 0)
			for region in function.Regions:
				self.assertIsInstance(region, Region)
				self.assertIs(function, region.Parent)
				self.assertIs(document, region.Root)

			for branch in function.Branches:
				self.assertIsInstance(branch, BranchRegion)
				self.assertIs(function, branch.Parent)
				self.assertIs(document, branch.Root)

			for record in function.MCDCRecords:
				self.assertIsInstance(record, MCDCRecord)
				self.assertIs(function, record.Parent)
				self.assertIs(document, record.Root)

				self.assertGreater(len(record.TestVectors), 0)
				for testVector in record.TestVectors:
					self.assertIsInstance(testVector, MCDCTestVector)
					self.assertIs(record, testVector.Parent)
					self.assertIs(document, testVector.Root)

		totals = document.Totals
		self.assertIsInstance(totals, Summary)
		self.assertIs(document, totals.Parent)
		self.assertIs(document, totals.Root)

		for counters in (totals.Lines, totals.Functions, totals.Instantiations, totals.Regions, totals.Branches):
			self.assertIsInstance(counters, Counters)
			self.assertIs(totals, counters.Parent)
			self.assertIs(document, counters.Root)

		# The loops, which may run zero times per file or function, run at least once for this report.
		self.assertGreater(sum(len(file.Expansions) for file in document.Files.values()), 0)
		self.assertGreater(sum(len(file.Branches) for file in document.Files.values()), 0)
		self.assertGreater(sum(len(function.Branches) for function in document.Functions), 0)
		self.assertGreater(sum(len(function.MCDCRecords) for function in document.Functions), 0)

	def test_BottomUp(self) -> None:
		"""A container connects the elements given to it; joining the report sets the root of every element below."""
		region = Region(3, 33, 3, 60, 2, 0, 0, RegionKind.Code)
		function = Function("Square", 2, [region], [Path("/project/src/Statistics.c")])
		self.assertIs(function, region.Parent)
		self.assertIsNone(region.Root)

		segment = Segment(3, 33, 2, True, True)
		file = File(Path("/project/src/Statistics.c"), _summary(), segments=[segment])
		document = Document(Path("coverage.json"), files=[file], functions=[function], totals=_summary())

		self.assertEqual((function, document, file, document), (region.Parent, region.Root, segment.Parent, segment.Root))
		self.assertIs(document, document.Totals.Functions.Root)

	def test_BottomUp_Nested(self) -> None:
		"""Joining the report sets the root of the elements two levels below a file or function, too."""
		filePaths =  [Path("/project/src/Statistics.c"), Path("/project/include/Statistics.h")]
		testVector = MCDCTestVector([True], True, True)
		record =     MCDCRecord(9, 7, 9, 22, 0, 0, RegionKind.MCDCDecision, [True], testVectors=[testVector])
		function =   Function("Square", 2, [], filePaths[:1], mcdcRecords=[record])
		target =     Region(6, 30, 8, 2, 3, 1, 0, RegionKind.Code)
		expansion =  Expansion(filePaths, Region(20, 9, 20, 20, 2, 0, 1, RegionKind.Expansion), [target])
		file =       File(filePaths[0], _summary(), expansions=[expansion])
		self.assertTrue(all(element.Root is None for element in (testVector, target, file.Summary.Lines)))

		document = Document(Path("coverage.json"), files=[file], functions=[function])
		self.assertTrue(all(element.Root is document for element in (
			record, testVector, expansion, expansion.SourceRegion, target, file.Summary, file.Summary.Lines
		)))

	def test_TopDown(self) -> None:
		"""An element created with a parent is added to the parent's collection, and takes the parent's root."""
		document = Document(Path("coverage.json"))
		file = File(Path("/project/src/Statistics.c"), _summary(), parent=document)
		segment = Segment(3, 33, 2, True, True, parent=file)
		branch = BranchRegion(9, 7, 9, 12, 1, 2, 0, 0, RegionKind.Branch, parent=file)
		function = Function("Square", 2, [], [Path("/project/src/Statistics.c")], parent=document)
		region = Region(3, 33, 3, 60, 2, 0, 0, RegionKind.Code, parent=function)
		record = MCDCRecord(9, 7, 9, 22, 0, 0, RegionKind.MCDCDecision, [True], parent=function)
		testVector = MCDCTestVector([True], True, True, parent=record)

		self.assertEqual({Path("/project/src/Statistics.c"): file}, document.Files)
		self.assertEqual(([segment], [branch], [function], [region], [record], [testVector]), (
			file.Segments, file.Branches, document.Functions, function.Regions, function.MCDCRecords, record.TestVectors
		))
		self.assertTrue(all(element.Root is document for element in (file, segment, branch, region, testVector)))

		filePaths = [Path("/project/src/Statistics.c"), Path("/project/include/Statistics.h")]
		expansion = Expansion(filePaths, Region(20, 9, 20, 20, 2, 0, 1, RegionKind.Expansion), [], parent=file)
		target = Region(6, 30, 8, 2, 3, 1, 0, RegionKind.Code, parent=expansion)
		self.assertEqual(([expansion], [target], document), (file.Expansions, expansion.TargetRegions, target.Root))

	def test_ParentChecks(self) -> None:
		document = Document(Path("coverage.json"))
		file = File(Path("/project/src/Statistics.c"), _summary(), parent=document)

		for create, message in (
			(lambda: Segment(3, 33, 2, True, True, parent=document), "Parameter 'parent' is not of type 'File'."),
			(lambda: Region(3, 33, 3, 60, 2, 0, 0, RegionKind.Code, parent=file),
			 "Parameter 'parent' is not of type 'Function' or 'Expansion'."),
		):
			with self.subTest(message=message):
				with self.assertRaises(TypeError) as context:
					_ = create()

				self.assertEqual(message, str(context.exception))

		region = Region(3, 33, 3, 60, 2, 0, 0, RegionKind.Code)
		summary = _summary()
		_ = Function("Square", 2, [region], [Path("/project/src/Statistics.c")])
		_ = File(Path("/project/src/Shapes.cpp"), summary)
		for create, message in (
			(lambda: Function("Average", 1, [region], []), "Parameter 'regions' contains a region of another element."),
			(lambda: File(Path("/project/src/Statistics.c"), _summary(), parent=document),
			 "Parameter 'parent' has a file of the same path."),
			(lambda: File(Path("/project/src/Statistics.h"), summary),
			 "Parameter 'summary' is the summary of another element."),
			(lambda: Document(Path("coverage.json"), files=[file]), "Parameter 'files' contains a file of another report."),
			(lambda: Document(Path("coverage.json"), files=[File(Path("a.c"), _summary()), File(Path("a.c"), _summary())]),
			 "Parameter 'files' contains two files of the same path."),
		):
			with self.subTest(message=message):
				with self.assertRaises(ValueError) as context:
					_ = create()

				self.assertEqual(message, str(context.exception))


class FileReferences(Testcase):
	"""A region's file ID and a function's main file are looked up by properties; nobody looks up an ID by hand."""

	def test_Parsed(self) -> None:
		document = Document(Path("tests/data/CodeCoverage/LLVM/coverage-3.1.0.json"), analyzeAndConvert=True)
		statistics = document.Files[Path("/project/src/Statistics.c")]
		header =     document.Files[Path("/project/include/Statistics.h")]
		functions =  {function.Name: function for function in document.Functions}

		clamp = functions["Clamp"]
		self.assertEqual((statistics, statistics), (clamp.MainFile, clamp.Regions[0].File))
		self.assertTrue(all(region.FilePath == clamp.FilePaths[region.FileID] for region in clamp.Regions))
		expansionRegion = next(region for region in clamp.Regions if region.Kind is RegionKind.Expansion)
		self.assertEqual((Path("/project/src/Statistics.c"), statistics), (
			expansionRegion.ExpandedFilePath, expansionRegion.ExpandedFile
		))
		codeRegion = next(region for region in clamp.Regions if region.Kind is RegionKind.Code)
		self.assertEqual((None, None), (codeRegion.ExpandedFilePath, codeRegion.ExpandedFile))

		average = functions["Statistics.c:Average"]
		self.assertEqual((Path("/project/include/Statistics.h"), header), (average.MainFilePath, average.MainFile))
		self.assertIs(statistics, functions["InRange"].MCDCRecords[0].File)

		self.assertTrue(all(branch.File is statistics for branch in statistics.Branches), "A file lists its own regions.")
		expansion = statistics.Expansions[0]
		self.assertIs(statistics, expansion.SourceRegion.File)

	def test_Unresolved(self) -> None:
		"""A region of no element, a file the report doesn't list, and an MC/DC record of format 2.0.1 have no file."""
		region = Region(3, 33, 3, 60, 2, 0, 0, RegionKind.Code)
		self.assertEqual((None, None, None), (region.FilePath, region.File, region.ExpandedFilePath))

		function = Function("Square", 2, [region], [Path("/project/src/Statistics.c")])
		self.assertEqual((Path("/project/src/Statistics.c"), None), (region.FilePath, region.File))

		_ = Document(Path("coverage.json"), functions=[function])
		self.assertEqual((Path("/project/src/Statistics.c"), None, None), (region.FilePath, region.File, function.MainFile))

		record = MCDCRecord(9, 7, 9, 22, None, 0, RegionKind.MCDCDecision, [True], parent=function)
		self.assertEqual((None, None), (record.FilePath, record.File))

	def test_OutOfRange(self) -> None:
		"""A file ID is checked against the file paths, when the region joins a function or expansion."""
		function = Function("Square", 2, [], [Path("/project/src/Statistics.c")])

		with self.assertRaises(ValueError) as context:
			_ = Region(3, 33, 3, 60, 2, 1, 0, RegionKind.Code, parent=function)
		self.assertEqual(
			"Parameter 'fileID' is no index into the file paths of parameter 'parent'.", str(context.exception)
		)
		self.assertEqual(["Got value '1' for 1 file paths."], context.exception.__notes__)

		with self.assertRaises(ValueError) as context:
			_ = Region(20, 9, 20, 20, 2, 0, 1, RegionKind.Expansion, parent=function)
		self.assertEqual(
			"Parameter 'expandedFileID' is no index into the file paths of parameter 'parent'.", str(context.exception)
		)

		for create, message in (
			(lambda: Function("f", 1, [Region(3, 33, 3, 60, 2, 1, 0, RegionKind.Code)], [Path("a.c")]),
			 "Parameter 'regions' contains a region of a file ID out of range."),
			(lambda: Function("f", 1, [Region(20, 9, 20, 20, 2, 0, 1, RegionKind.Expansion)], [Path("a.c")]),
			 "Parameter 'regions' contains an expansion region of an expanded file ID out of range."),
			(lambda: Expansion([Path("a.c")], Region(20, 9, 20, 20, 2, 0, 1, RegionKind.Expansion), []),
			 "Parameter 'sourceRegion' is an expansion region of an expanded file ID out of range."),
			(lambda: Expansion([Path("a.c")], Region(20, 9, 20, 20, 2, 0, 0, RegionKind.Code), [], [
				BranchRegion(9, 7, 9, 12, 1, 2, 1, 0, RegionKind.Branch)
			]), "Parameter 'branches' contains a region of a file ID out of range."),
		):
			with self.subTest(message=message):
				with self.assertRaises(ValueError) as context:
					_ = create()

				self.assertEqual(message, str(context.exception))
