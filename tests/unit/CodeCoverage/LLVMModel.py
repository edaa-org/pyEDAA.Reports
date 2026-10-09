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
from json                                       import dumps
from pathlib                                    import Path
from tempfile                                   import TemporaryDirectory

from pyEDAA.Reports.CodeCoverage.LLVM           import Document
from pyEDAA.Reports.CodeCoverage.LLVM.Records   import Expansion, File, Function, Segment
from pyEDAA.Reports.CodeCoverage.LLVM.Regions   import BranchRegion, MCDCRecord, Region, RegionKind
from pyEDAA.Reports.CodeCoverage.LLVM.Regions   import TestVector as MCDCTestVector
from pyEDAA.Reports.CodeCoverage.LLVM.Summaries import Counters, Summary
from pyTooling.Testing                          import Testcase
from pyTooling.Versioning                       import SemanticVersion


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
		summary = Summary(lines, lines, lines, lines, branches, branches)

		self.assertIs(lines, summary.Lines)
		self.assertEqual((branches, branches, 1), (summary.Branches, summary.MCDC, summary.MCDC.NotCovered))

	def test_File(self) -> None:
		summary = _summary()
		file = File(Path("/project/src/Statistics.c"), summary)

		self.assertEqual((Path("/project/src/Statistics.c"), summary), (file.Path, file.Summary))
		self.assertEqual(([], [], [], []), (file.Segments, file.Branches, file.MCDCRecords, file.Expansions))

		segment = Segment(3, 33, 2, True, True)
		file = File(Path("Statistics.c"), summary, segments=(segment, ))
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
		self.assertEqual(["Got type 'pyEDAA.Reports.CodeCoverage.LLVM.Records.Function'."], context.exception.__notes__)


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
