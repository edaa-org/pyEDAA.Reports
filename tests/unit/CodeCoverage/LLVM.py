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
"""Unit tests of LLVM's JSON code coverage export: its model, its JSON Schema and the conversion to the common model."""
from copy                                     import deepcopy
from json                                     import dumps, loads
from pathlib                                  import Path
from tempfile                                 import TemporaryDirectory
from typing                                   import Any

from pyEDAA.Reports.CodeCoverage              import CodeCoverageError, Function, LineCoverageStatus, SourceFile
from pyEDAA.Reports.CodeCoverage.LLVM         import Document
from pyEDAA.Reports.CodeCoverage.LLVM.Records import RegionKind
from pyTooling.Testing                        import Testcase


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


DATA = Path(__file__).parent.parent.parent / "data" / "CodeCoverage"  #: Directory of the reports and their sources.
REPORT = DATA / "LLVM" / "coverage-2.0.1.json"                        #: LLVM 19's export of the fixture.
REPORT_3_1_0 = DATA / "LLVM" / "coverage-3.1.0.json"                  #: LLVM 23's export of the same profile.


def _write(directory: str, content: dict[str, Any]) -> Path:
	"""
	Write a report file into a directory.

	:param directory: The directory.
	:param content:   The report's JSON object.
	:returns:         The report file.
	"""
	jsonFile = Path(directory) / "coverage.json"
	jsonFile.write_text(dumps(content), encoding="utf-8")
	return jsonFile


def _read(content: dict[str, Any]) -> Document:
	"""
	Write a report into a temporary directory, and read it.

	:param content: The report's JSON object.
	:returns:       The analyzed and converted report.
	"""
	with TemporaryDirectory() as directory:
		return Document(_write(directory, content), analyzeAndConvert=True)


class FormatModel(Testcase):
	"""The format's model keeps what the report states: files, functions, regions, summaries."""

	def test_Report(self) -> None:
		report = Document(REPORT, analyzeAndConvert=True)

		self.assertEqual("2.0.1", report.Version)
		self.assertEqual(
			["/project/include/Statistics.h", "/project/src/Shapes.cpp", "/project/src/Statistics.c"],
			[path.as_posix() for path in report.Files]
		)
		self.assertEqual(13, len(report.Functions))
		self.assertIn("_ZN8Geometry3MaxIiEET_S1_S1_", [function.Name for function in report.Functions])

		totals = report.Totals
		self.assertEqual((47, 41, 11, 10, 13, 11, 24, 15, 5, 0), (
			totals.Lines.Count, totals.Lines.Covered, totals.Functions.Count, totals.Functions.Covered,
			totals.Instantiations.Count, totals.Instantiations.Covered, totals.Branches.Count, totals.Branches.Covered,
			totals.MCDC.Count, totals.MCDC.Covered
		))
		self.assertIsNone(totals.Lines.NotCovered)
		self.assertEqual(9, totals.Branches.NotCovered)

	def test_File(self) -> None:
		statistics = Document(REPORT, analyzeAndConvert=True).Files[Path("/project/src/Statistics.c")]

		segment = statistics.Segments[0]
		self.assertEqual((3, 33, 2, True, True, False), (
			segment.Line, segment.Column, segment.Count, segment.HasCount, segment.IsRegionEntry, segment.IsGapRegion
		))

		branch = statistics.Branches[0]
		self.assertEqual((12, 18, 12, 27, 3, 1, 0, 0, RegionKind.Branch), (
			branch.LineStart, branch.ColumnStart, branch.LineEnd, branch.ColumnEnd, branch.TrueCount, branch.FalseCount,
			branch.FileID, branch.ExpandedFileID, branch.Kind
		))

		expansion = statistics.Expansions[0]
		source = expansion.SourceRegion
		self.assertEqual((20, 9, 2, 0, 1, RegionKind.Expansion), (
			source.LineStart, source.ColumnStart, source.Count, source.FileID, source.ExpandedFileID, source.Kind
		))
		self.assertEqual(9, len(expansion.TargetRegions))
		self.assertEqual([(3, 1), (3, 1)], [(branch.LineStart, branch.FileID) for branch in expansion.Branches])
		self.assertEqual(2, len(expansion.FilePaths))

		self.assertEqual((22, 18), (statistics.Summary.Lines.Count, statistics.Summary.Lines.Covered))

	def test_Function(self) -> None:
		functions = {function.Name: function for function in Document(REPORT, analyzeAndConvert=True).Functions}

		square = functions["Statistics.c:Square"]
		self.assertEqual((3, [Path("/project/src/Statistics.c")], 0), (square.Count, square.FilePaths, square.MainFileID))
		self.assertEqual([(6, 30, 8, 2, RegionKind.Code)], [
			(region.LineStart, region.ColumnStart, region.LineEnd, region.ColumnEnd, region.Kind) for region in square.Regions
		])

		clamp = functions["Clamp"]
		self.assertEqual((0, [1, 1]), (clamp.MainFileID, [branch.FileID for branch in clamp.Branches]))

	def test_MCDCRecord(self) -> None:
		"""An MC/DC record grows with the format: 3.0.0 adds the decisions, 3.0.1 the file ID, 3.1.0 the test vectors."""
		record = Document(REPORT, analyzeAndConvert=True).Files[Path("/project/src/Statistics.c")].MCDCRecords[0]

		self.assertEqual((24, 6, 24, 85, None, 0, RegionKind.MCDCDecision), (
			record.LineStart, record.ColumnStart, record.LineEnd, record.ColumnEnd, record.FileID, record.ExpandedFileID,
			record.Kind
		))
		self.assertEqual((None, None, [False] * 5, []), (
			record.TrueDecisions, record.FalseDecisions, record.Conditions, record.TestVectors
		))

		record = Document(REPORT_3_1_0, analyzeAndConvert=True).Files[Path("/project/src/Statistics.c")].MCDCRecords[0]
		self.assertEqual((24, 85, 0, 0, RegionKind.MCDCDecision, 2, 0, [False] * 5), (
			record.LineStart, record.ColumnEnd, record.FileID, record.ExpandedFileID, record.Kind, record.TrueDecisions,
			record.FalseDecisions, record.Conditions
		))
		self.assertEqual([([True, False, True, False, True], True, True), ([True, True, None, None, None], True, True)], [
			(testVector.Conditions, testVector.Executed, testVector.Result) for testVector in record.TestVectors
		])


class Conversion(Testcase):
	"""The conversion to the common model: lines derived from segments, branches, and source files with functions."""

	def test_Paths(self) -> None:
		"""The paths are relative to the directory common to all files."""
		summary = Document(REPORT, analyzeAndConvert=True).ToCoverageSummary()

		self.assertEqual([Path("/project")], summary.SourceDirectories)
		self.assertEqual(["include/Statistics.h", "src/Shapes.cpp", "src/Statistics.c"], [
			file.Path.as_posix() for file in summary.IterateFiles()
		])

	def test_Lines(self) -> None:
		statistics = Document(REPORT, analyzeAndConvert=True).ToCoverageSummary().Directories["src"].Files["Statistics.c"]

		lines = statistics.Lines
		self.assertEqual((LineCoverageStatus.Covered, 4), (lines[12].Status, lines[12].CoverageCount))
		self.assertIs(LineCoverageStatus.PartiallyCovered, lines[24].Status)
		self.assertEqual((LineCoverageStatus.Uncovered, 0), (lines[31].Status, lines[31].CoverageCount))
		# a line inside a function continues the count of the region before it; empty lines and skipped code are no lines
		self.assertEqual((LineCoverageStatus.Covered, 2), (lines[26].Status, lines[26].CoverageCount))
		self.assertEqual([None] * 4, lines[27:31])
		# a macro defined in the file counts at its definition, as 'llvm-cov show' shows it
		self.assertEqual(2, lines[3].CoverageCount)

	def test_Branches(self) -> None:
		summary = Document(REPORT, analyzeAndConvert=True).ToCoverageSummary()
		statistics = summary.Directories["src"].Files["Statistics.c"]

		self.assertEqual([3, 1], [branch.CoverageCount for branch in statistics.Lines[12].Branches])
		# the branch regions of a macro expansion count at the line the macro is expanded at
		self.assertEqual([1, 1, 1, 0], [branch.CoverageCount for branch in statistics.Lines[20].Branches])
		self.assertEqual([2, 0, 1, 1, 1, 0, 0, 1, 1, 0], [branch.CoverageCount for branch in statistics.Lines[24].Branches])
		self.assertIs(LineCoverageStatus.Uncovered, statistics.Lines[24].Branches[1].Status)
		# the branch regions of a template's instantiations are summed
		self.assertEqual([1, 1], [
			branch.CoverageCount for branch in summary.Directories["src"].Files["Shapes.cpp"].Lines[6].Branches
		])

	def test_Totals(self) -> None:
		"""The counters agree with llvm-cov's summaries, but for a macro's definition line and a template's branches."""
		report = Document(REPORT, analyzeAndConvert=True)
		summary = report.ToCoverageSummary()

		# llvm-cov counts per function: without the definition line of a macro, and a template's best instantiation only
		differences = {"include/Statistics.h": (0, 0, 0), "src/Shapes.cpp": (0, 0, 1), "src/Statistics.c": (1, 1, 0)}
		for file in summary.IterateFiles():
			path = file.Path.as_posix()
			stated = report.Files[Path("/project") / file.Path].Summary
			lines, coveredLines, coveredBranches = differences[path]
			with self.subTest(file=path):
				self.assertEqual((
					stated.Lines.Count + lines, stated.Lines.Covered + coveredLines, stated.Branches.Count,
					stated.Branches.Covered + coveredBranches
				), (file.TotalLines, file.CoveredLines, file.TotalBranches, file.CoveredBranches))

		self.assertEqual((48, 42, 5, 24, 16), (
			summary.TotalLines, summary.CoveredLines, summary.PartialLines, summary.TotalBranches, summary.CoveredBranches
		))

	def test_Units(self) -> None:
		summary = Document(REPORT, analyzeAndConvert=True).ToCoverageSummary()

		units = {unit.QualifiedName: unit for unit in summary.IterateUnits()}
		self.assertIsInstance(units["src/Statistics.c"], SourceFile)
		square = units["src/Statistics.c.Square"]
		self.assertIsInstance(square, Function)
		self.assertEqual((LineCoverageStatus.Covered, 3, 6, 8), (
			square.Status, square.CoverageCount, square.StartLine.LineNumber, square.EndLine.LineNumber
		))
		negate = units["src/Statistics.c.Negate"]
		self.assertEqual((LineCoverageStatus.Uncovered, 0, 3, 0), (
			negate.Status, negate.CoverageCount, negate.TotalLines, negate.CoveredLines
		))
		self.assertIn("src/Shapes.cpp._ZN8Geometry3MaxIdEET_S1_S1_", units)
		self.assertEqual(["Average", "_ZL7Averageii"], sorted(units["include/Statistics.h"].Units))

	def test_Versions(self) -> None:
		"""LLVM 19 and LLVM 23 export the same profile to the same common model."""
		def lines(report: Path) -> list[tuple[str, int, LineCoverageStatus, Any, list[Any]]]:
			"""Nested function listing the lines of a report with their branches."""
			summary = Document(report, analyzeAndConvert=True).ToCoverageSummary()
			return [
				(file.Path.as_posix(), line.LineNumber, line.Status, line.CoverageCount, [
					(branch.Status, branch.CoverageCount) for branch in line.Branches
				]) for file in summary.IterateFiles() for line in file.IterateLines()
			]

		self.assertEqual(lines(REPORT), lines(REPORT_3_1_0))

	def test_Format2_0_0(self) -> None:
		"""Format 2.0.0 has no gap flag in a segment and no branch regions; a summary-only report has no lines."""
		content = loads(REPORT.read_text(encoding="utf-8"))
		content["version"] = "2.0.0"
		export = content["data"][0]
		for file in export["files"]:
			file["segments"] = [segment[:5] for segment in file["segments"]]
			del file["branches"], file["mcdc_records"], file["summary"]["branches"], file["summary"]["mcdc"]

		for function in export["functions"]:
			del function["branches"], function["mcdc_records"]

		del export["totals"]["branches"], export["totals"]["mcdc"]

		report = _read(content)
		self.assertIsNone(report.Totals.Branches)
		self.assertFalse(report.Files[Path("/project/src/Statistics.c")].Segments[0].IsGapRegion)
		summary = report.ToCoverageSummary()
		self.assertEqual((0, 16), (summary.TotalBranches, len(list(summary.IterateUnits()))))

		summaryOnly = {"version": "2.0.1", "type": "llvm.coverage.json.export", "data": [{
			"files": [{"filename": file["filename"], "summary": file["summary"]} for file in export["files"]],
			"totals": export["totals"]
		}]}
		summary = _read(summaryOnly).ToCoverageSummary()
		self.assertEqual((3, 0), (summary.FileCount, summary.TotalLines))

	def test_UnexpandedFile(self) -> None:
		"""A branch region in a file, which no region expands to, is an error."""
		content = loads(REPORT.read_text(encoding="utf-8"))
		clamp = next(function for function in content["data"][0]["functions"] if function["name"] == "Clamp")
		clamp["regions"] = [region for region in clamp["regions"] if region[7] != 1]

		with self.assertRaises(CodeCoverageError) as context:
			_read(content).ToCoverageSummary()

		self.assertEqual(
			"Function 'Clamp' has a branch region in a file no region expands to.", str(context.exception)
		)


class Schema(Testcase):
	"""The reverse-engineered JSON Schema accepts llvm-cov's export and rejects what it doesn't write."""

	def test_MCDCRecord_3_0_0(self) -> None:
		"""Format 3.0.0 added the numbers of true and false decisions, but not yet the file ID."""
		content = loads(REPORT.read_text(encoding="utf-8"))
		content["version"] = "3.0.0"
		record = content["data"][0]["files"][2]["mcdc_records"][0]
		record[4:4] = [2, 0]

		record = _read(deepcopy(content)).Files[Path("/project/src/Statistics.c")].MCDCRecords[0]
		self.assertEqual((2, 0, None, 0, [False] * 5), (
			record.TrueDecisions, record.FalseDecisions, record.FileID, record.ExpandedFileID, record.Conditions
		))

		del content["data"][0]["files"][2]["mcdc_records"][0][4]
		with TemporaryDirectory() as directory:
			with self.assertRaises(CodeCoverageError) as context:
				_ = Document(_write(directory, content), analyzeAndConvert=True)

		self.assertEqual(1, len(context.exception.__notes__))
		self.assertTrue(context.exception.__notes__[0].startswith("/data/0/files/2/mcdc_records/0: "))

	def test_Version(self) -> None:
		content = loads(REPORT.read_text(encoding="utf-8"))
		content["version"] = "1.0.0"
		with TemporaryDirectory() as directory:
			jsonFile = _write(directory, content)

			with self.assertRaises(CodeCoverageError) as context:
				_ = Document(jsonFile, analyzeAndConvert=True)

		self.assertEqual(
			f"Validation error for '{jsonFile}' using JSON Schema 'LLVM-Coverage-JSON.schema.json'.", str(context.exception)
		)
		self.assertEqual(
			["/version: '1.0.0' is not one of ['2.0.0', '2.0.1', '3.0.0', '3.0.1', '3.1.0']"], context.exception.__notes__
		)

	def test_UnknownField(self) -> None:
		content = loads(REPORT.read_text(encoding="utf-8"))
		content["data"][0]["files"][0]["lines"] = []
		with TemporaryDirectory() as directory:
			with self.assertRaises(CodeCoverageError) as context:
				_ = Document(_write(directory, content), analyzeAndConvert=True)

		self.assertEqual(
			["/data/0/files/0: Additional properties are not allowed ('lines' was unexpected)"], context.exception.__notes__
		)

	def test_Syntax(self) -> None:
		with TemporaryDirectory() as directory:
			jsonFile = Path(directory) / "coverage.json"
			jsonFile.write_text("{", encoding="utf-8")

			with self.assertRaises(CodeCoverageError) as context:
				_ = Document(jsonFile, analyzeAndConvert=True)

		self.assertEqual(f"JSON syntax error in LLVM coverage export file '{jsonFile}'.", str(context.exception))

	def test_Missing(self) -> None:
		with self.assertRaises(CodeCoverageError) as context:
			_ = Document(DATA / "missing.json", analyzeAndConvert=True)

		self.assertEqual(f"LLVM coverage export file '{DATA / 'missing.json'}' does not exist.", str(context.exception))

	def test_NotAnalyzed(self) -> None:
		with self.assertRaises(CodeCoverageError):
			Document(REPORT).Convert()
