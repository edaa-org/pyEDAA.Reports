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
"""Unit tests of GHDL's JSON coverage format: its model, its JSON Schema, merging and the conversion to the common model."""
from datetime                         import datetime, timezone
from json                             import dumps, loads
from pathlib                          import Path
from tempfile                         import TemporaryDirectory
from typing                           import Any

from pyEDAA.Reports.CodeCoverage      import CodeCoverageError, CoverageSummary, LineCoverageStatus
from pyEDAA.Reports.CodeCoverage.GHDL import CoverageMode, Document, File, MergedReport
from pyTooling.Testing                import Testcase
from pyTooling.Versioning             import SemanticVersion


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


DATA =  Path(__file__).parent.parent.parent / "data" / "CodeCoverage" / "VHDL"  #: Directory of the coverage files.
COUNT = DATA / "coverage-Count.json"                                            #: Coverage file of the run counting.
RESET = DATA / "coverage-Reset.json"                                            #: Coverage file of the run resetting.


def _write(directory: str, content: dict[str, Any]) -> Path:
	"""
	Write a coverage file into a directory.

	:param directory: The directory.
	:param content:   The coverage file's JSON object.
	:returns:         The coverage file.
	"""
	jsonFile = Path(directory) / "coverage.json"
	jsonFile.write_text(dumps(content), encoding="utf-8")
	return jsonFile


def _readLcov(lcovFile: Path) -> dict[str, dict[int, int]]:
	"""
	Read the lines of an lcov tracefile written by ``ghdl coverage --format=lcov``.

	:param lcovFile: The tracefile.
	:returns:        Per source file, the count per line.
	"""
	files: dict[str, dict[int, int]] = {}
	for line in lcovFile.read_text(encoding="utf-8").splitlines():
		if line.startswith("SF:"):
			lines = files.setdefault(line[3:], {})
		elif line.startswith("DA:"):
			number, count = line[3:].split(",")
			lines[int(number)] = int(count)

	return files


def _lines(summary: CoverageSummary) -> dict[str, dict[int, LineCoverageStatus]]:
	"""
	Collect the line states of a summary.

	:param summary: The report's root of the common model.
	:returns:       Per file path, the state per line.
	"""
	return {
		file.Path.as_posix(): {line.LineNumber: line.Status for line in file.IterateLines()}
		for file in summary.IterateFiles()
	}


class FormatModel(Testcase):
	"""The format's model keeps what the coverage file states: header, source files, checksums, lines."""

	def test_Report(self) -> None:
		report = Document(COUNT, analyzeAndConvert=True)

		self.assertEqual(("1.0.0", "unknown"), (report.Version, report.Testcase))
		self.assertIsInstance(report.Version, SemanticVersion)
		self.assertEqual(datetime(2026, 10, 8, 10, 48, 12, 89000, tzinfo=timezone.utc), report.Timestamp)
		self.assertEqual(
			["src/Counter.vhdl", "src/Utilities/Functions.vhdl", "tb/Counter_tb.vhdl"],
			sorted(path.as_posix() for path in report.Files)
		)

		counter = report.Files[Path("src/Counter.vhdl")]
		self.assertEqual(
			(Path("src/Counter.vhdl"), Path("."), "1a6afa99b014932646ce6591101aa1ac3695349a", CoverageMode.Statement, 35),
			(counter.Name, counter.Directory, counter.SHA1, counter.Mode, counter.LastLine)
		)
		self.assertEqual({25: True, 26: True, 27: False, 29: True, 34: True, 35: True}, counter.Result)

	def test_Mode(self) -> None:
		"""A file's ``mode`` is converted to a member of :class:`CoverageMode`."""
		counter = Document(COUNT, analyzeAndConvert=True).Files[Path("src/Counter.vhdl")]

		self.assertIs(CoverageMode.Statement, counter.Mode)
		self.assertEqual("stmt", counter.Mode)

	def test_Path(self) -> None:
		"""A file's path is its name, prefixed by the directory it was analyzed in, unless GHDL ran there."""
		for directory, name, path in (
			(".",                   "src/Counter.vhdl",            "src/Counter.vhdl"),
			("",                    "/home/user/src/Counter.vhdl", "/home/user/src/Counter.vhdl"),
			("/home/user/project/", "src/Counter.vhdl",            "/home/user/project/src/Counter.vhdl")
		):
			with self.subTest(directory=directory):
				file = File(Path(name), Path(directory), "0" * 40, CoverageMode.Statement, 1, {1: True})
				self.assertEqual(Path(path), file.Path)


class Conversion(Testcase):
	"""The conversion to the common model agrees with GHDL's own conversion to lcov."""

	def test_Lcov(self) -> None:
		"""Each run's lines and states agree with the lcov tracefile 'ghdl coverage --format=lcov' wrote."""
		for coverageFile in (COUNT, RESET):
			with self.subTest(run=coverageFile.stem):
				summary = Document(coverageFile, analyzeAndConvert=True).ToCoverageSummary()
				lcov = _readLcov(coverageFile.with_suffix(".info"))

				self.assertEqual(
					{path: {number: LineCoverageStatus.Covered if count > 0 else LineCoverageStatus.Uncovered
					        for number, count in lines.items()} for path, lines in lcov.items()},
					_lines(summary)
				)

	def test_Counters(self) -> None:
		summary = Document(COUNT, analyzeAndConvert=True).ToCoverageSummary()

		self.assertEqual("coverage-Count", summary.Name)
		self.assertEqual((27, 23, 4, 0, 0, 0), (
			summary.TotalLines, summary.CoveredLines, summary.MissingLines, summary.ExcludedLines, summary.PartialLines,
			summary.TotalBranches
		))
		self.assertEqual(
			[("src/Counter.vhdl", 6, 5), ("src/Utilities/Functions.vhdl", 6, 5), ("tb/Counter_tb.vhdl", 15, 13)],
			[(file.Path.as_posix(), file.TotalLines, file.CoveredLines) for file in summary.IterateFiles()]
		)

	def test_Lines(self) -> None:
		counter = Document(COUNT, analyzeAndConvert=True).ToCoverageSummary().Directories["src"].Files["Counter.vhdl"]

		self.assertEqual(35, counter.LastLineNumber)
		self.assertIsNone(counter.Lines[28])
		line = counter.Lines[27]
		self.assertIs(LineCoverageStatus.Uncovered, line.Status)
		self.assertIsNone(line.CoverageCount)
		self.assertEqual([], line.Branches)
		self.assertIs(LineCoverageStatus.Covered, counter.Lines[29].Status)

	def test_NoUnits(self) -> None:
		"""The format names no units."""
		self.assertEqual([], list(Document(COUNT, analyzeAndConvert=True).ToCoverageSummary().IterateUnits()))


class Merge(Testcase):
	"""Merging the coverage files of several runs: a line ran, if it ran in one of the runs."""

	def test_Merge(self) -> None:
		count = Document(COUNT, analyzeAndConvert=True)
		reset = Document(RESET, analyzeAndConvert=True)
		merged = MergedReport("Counter", (count, reset))

		self.assertEqual("Counter", merged.Name)
		self.assertEqual([count, reset], merged.Reports)
		self.assertEqual(66, merged.Files[Path("tb/Counter_tb.vhdl")].LastLine)

		summary = merged.ToCoverageSummary()
		self.assertEqual("Counter", summary.Name)
		self.assertEqual((27, 25), (summary.TotalLines, summary.CoveredLines))

		testbench = _lines(summary)["tb/Counter_tb.vhdl"]
		self.assertIs(LineCoverageStatus.Covered, testbench[46])    # ran in run 'Count' only
		self.assertIs(LineCoverageStatus.Covered, testbench[52])    # ran in run 'Reset' only
		self.assertIs(LineCoverageStatus.Uncovered, testbench[66])  # ran in no run

		# the merged reports are left unchanged
		self.assertFalse(count.Files[Path("src/Counter.vhdl")].Result[27])

	def test_Merge_Order(self) -> None:
		"""The order of the coverage files doesn't matter."""
		count = Document(COUNT, analyzeAndConvert=True)
		reset = Document(RESET, analyzeAndConvert=True)

		self.assertEqual(
			_lines(MergedReport("Counter", (count, reset)).ToCoverageSummary()),
			_lines(MergedReport("Counter", (reset, count)).ToCoverageSummary())
		)

	def test_Merge_Incremental(self) -> None:
		merged = MergedReport("Counter")
		self.assertEqual({}, merged.Files)

		merged.Merge(Document(COUNT, analyzeAndConvert=True))
		merged.Merge(Document(RESET, analyzeAndConvert=True))
		self.assertEqual(25, merged.ToCoverageSummary().CoveredLines)

	def test_Merge_LastLine(self) -> None:
		"""A merged file's last line with a coverage point is the largest of the merged files."""
		content = loads(COUNT.read_text(encoding="utf-8"))
		del content["outputs"][0]["result"]["66"]
		content["outputs"][0]["max-line"] = 65
		with TemporaryDirectory() as directory:
			shorter = Document(_write(directory, content), analyzeAndConvert=True)

		merged = MergedReport("Counter", (shorter, Document(COUNT, analyzeAndConvert=True)))
		self.assertEqual(66, merged.Files[Path("tb/Counter_tb.vhdl")].LastLine)

	def test_Merge_Checksum(self) -> None:
		"""A source file changed between two runs can't be merged."""
		content = loads(RESET.read_text(encoding="utf-8"))
		content["outputs"][2]["sha1"] = "0" * 40
		with TemporaryDirectory() as directory:
			changed = Document(_write(directory, content), analyzeAndConvert=True)

		with self.assertRaises(CodeCoverageError) as context:
			_ = MergedReport("Counter", (Document(COUNT, analyzeAndConvert=True), changed))

		self.assertEqual(
			"Content of source file 'src/Counter.vhdl' differs from the reports merged before.", str(context.exception)
		)
		self.assertEqual(
			[f"Got SHA-1 checksum '{'0' * 40}' instead of '1a6afa99b014932646ce6591101aa1ac3695349a'."],
			context.exception.__notes__
		)

	def test_Parameters(self) -> None:
		for arguments, exceptionClass, message in (
			((None, ),         ValueError, "Parameter 'name' is None."),
			((1, ),            TypeError,  "Parameter 'name' is not of type 'str'."),
			(("", ),           ValueError, "Parameter 'name' is empty."),
			(("Counter", 1),   TypeError,  "Parameter 'reports' is not iterable."),
			(("Counter", [1]), TypeError,  "Parameter 'reports' contains an element not of type 'Report'.")
		):
			with self.subTest(message=message):
				with self.assertRaises(exceptionClass) as context:
					_ = MergedReport(*arguments)

				self.assertEqual(message, str(context.exception))

		merged = MergedReport("Counter")
		with self.assertRaises(ValueError) as context:
			merged.Merge(None)
		self.assertEqual("Parameter 'report' is None.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			merged.Merge(1)
		self.assertEqual("Parameter 'report' is not of type 'Report'.", str(context.exception))
		self.assertEqual(["Got type 'int'."], context.exception.__notes__)


class Schema(Testcase):
	"""The reverse-engineered JSON Schema accepts GHDL's coverage files and rejects what GHDL doesn't write."""

	def _assertRejected(self, content: dict[str, Any], notes: list[str]) -> None:
		"""
		Assert a coverage file is rejected by the JSON Schema.

		:param content: The coverage file's JSON object.
		:param notes:   The expected notes of the exception.
		"""
		with TemporaryDirectory() as directory:
			jsonFile = _write(directory, content)

			with self.assertRaises(CodeCoverageError) as context:
				_ = Document(jsonFile, analyzeAndConvert=True)

		self.assertEqual(
			f"Validation error for '{jsonFile}' using JSON Schema 'GHDL-Coverage.schema.json'.", str(context.exception)
		)
		self.assertEqual(notes, context.exception.__notes__)

	def test_Version(self) -> None:
		content = loads(COUNT.read_text(encoding="utf-8"))
		content["version"] = "2.0.0"
		self._assertRejected(content, ["/version: '2.0.0' is not one of ['1.0.0']"])

	def test_Mode(self) -> None:
		content = loads(COUNT.read_text(encoding="utf-8"))
		content["outputs"][0]["mode"] = "decision"
		self._assertRejected(content, ["/outputs/0/mode: 'decision' is not one of ['stmt']"])

	def test_Result(self) -> None:
		"""A result is a flag, not a count."""
		content = loads(COUNT.read_text(encoding="utf-8"))
		content["outputs"][0]["result"]["26"] = 2
		self._assertRejected(content, ["/outputs/0/result/26: 2 is not one of [0, 1]"])

	def test_UnknownField(self) -> None:
		content = loads(COUNT.read_text(encoding="utf-8"))
		content["outputs"][0]["count"] = {}
		self._assertRejected(content, ["/outputs/0: Additional properties are not allowed ('count' was unexpected)"])

	def test_Syntax(self) -> None:
		with TemporaryDirectory() as directory:
			jsonFile = Path(directory) / "coverage.json"
			jsonFile.write_text("{", encoding="utf-8")

			with self.assertRaises(CodeCoverageError) as context:
				_ = Document(jsonFile, analyzeAndConvert=True)

		self.assertEqual(f"JSON syntax error in GHDL coverage file '{jsonFile}'.", str(context.exception))

	def test_Missing(self) -> None:
		with self.assertRaises(CodeCoverageError) as context:
			_ = Document(DATA / "missing.json", analyzeAndConvert=True)

		self.assertEqual(f"GHDL coverage file '{DATA / 'missing.json'}' does not exist.", str(context.exception))

	def test_NotAnalyzed(self) -> None:
		with self.assertRaises(CodeCoverageError):
			Document(COUNT).Convert()


class Consistency(Testcase):
	"""Rules of the format the JSON Schema can't express."""

	def test_DuplicateFile(self) -> None:
		content = loads(COUNT.read_text(encoding="utf-8"))
		content["outputs"].append(content["outputs"][0])
		with TemporaryDirectory() as directory:
			jsonFile = _write(directory, content)

			with self.assertRaises(CodeCoverageError) as context:
				_ = Document(jsonFile, analyzeAndConvert=True)

		self.assertEqual(
			f"GHDL coverage file '{jsonFile}' names source file 'tb/Counter_tb.vhdl' twice.", str(context.exception)
		)

	def test_BeyondLastLine(self) -> None:
		content = loads(COUNT.read_text(encoding="utf-8"))
		content["outputs"][0]["max-line"] = 60
		with TemporaryDirectory() as directory:
			jsonFile = _write(directory, content)

			with self.assertRaises(CodeCoverageError) as context:
				_ = Document(jsonFile, analyzeAndConvert=True)

		self.assertEqual(
			f"GHDL coverage file '{jsonFile}' names a line of 'tb/Counter_tb.vhdl' beyond 'max-line'.", str(context.exception)
		)
		self.assertEqual(["Got line 66 for 'max-line' 60."], context.exception.__notes__)
