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
# Copyright 2024-2024 Electronic Design Automation Abstraction (EDA²)                                                  #
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
from pathlib  import Path
from time     import perf_counter_ns
from typing   import List
from unittest import TestCase as ut_TestCase

from pyEDAA.Reports.Unittesting       import MergedTestsuiteSummary, IterationScheme, TestcaseStatus
from pyEDAA.Reports.Unittesting.JUnit import Document, JUnitReaderMode


class PyTooling(ut_TestCase):
	_outputDirectory = Path("tests/output/Merge_PyTooling")

	@classmethod
	def setUpClass(cls):
		print()
		if cls._outputDirectory.exists():
			print(f"Output directory '{cls._outputDirectory}' already exists.")
			print(f"Cleaning XML files from '{cls._outputDirectory}' ...")
			for file in cls._outputDirectory.glob("*.xml"):
				print(f"  unlinking file: {file}")
				file.unlink()
		else:
			print(f"Creating output directory '{cls._outputDirectory}' ...")
			cls._outputDirectory.mkdir(parents=True)

	def test_PlatformTesting(self) -> None:
		print()

		junitDocuments: List[Document] = []

		directory = Path("tests/data/JUnit/pyTooling")
		print(f"Reading platform testing summary files from '{directory}' ...")
		files = directory.glob("Platform-UnitTestReportSummary-XML-*.xml")
		startParsing = perf_counter_ns()
		for file in files:
			print(f"  Parsing {file}")
			junitDocument = Document(file, parse=True, readerMode=JUnitReaderMode.DecoupleTestsuiteHierarchyAndTestcaseClassName)
			junitDocuments.append(junitDocument)

		endParsing = perf_counter_ns()
		parsingDuration = (endParsing - startParsing) / 1e9

		print(f"Merging generic testsuites ...")
		startMerging = perf_counter_ns()
		merged = MergedTestsuiteSummary("PlatformTesting")
		for summary in junitDocuments:
			print(f"  merging {summary.Path}")
			merged.Merge(summary.ToTestsuiteSummary())

		endMerging = perf_counter_ns()
		mergingDuration = (endMerging - startMerging) / 1e9

		print("Structure of merged testcases:")
		print("-" * 40)
		print(merged.ToTree().Render(prefix="  "), end="")
		print("-" * 40)

		for summary in junitDocuments:
			self.assertGreaterEqual(merged.TestsuiteCount, summary.TestsuiteCount, f"{summary.Path}")
			self.assertGreaterEqual(merged.TestcaseCount, summary.TestcaseCount, f"{summary.Path}")

		mergedCount = len(junitDocuments)
		for item in merged.Iterate(IterationScheme.Default | IterationScheme.IncludeSelf):
			self.assertEqual(mergedCount, item.MergedCount, f"{item.Name}")

		for testcase in (tc for tc in merged.IterateTestcases() if tc.Name not in ("test_NativeMacOS", "test_MSYS", "test_MinGW32", "test_Clang32")):
			self.assertEqual(TestcaseStatus.Passed, testcase.Status, f"{testcase.Parent.Name}.{testcase.Name}")

		print(f"Aggregating datapoints in testsuite ...")
		startAggregate = perf_counter_ns()
		merged.Aggregate()
		endAggregate = perf_counter_ns()
		aggregateDuration = (endAggregate - startAggregate) / 1e9

		self.assertEqual(7, merged.TestsuiteCount)
		self.assertEqual(10, merged.TestcaseCount)
		self.assertEqual(0, merged.AssertionCount)
		self.assertEqual(10, merged.Tests)
		self.assertEqual(3, merged.Skipped)
		self.assertEqual(0, merged.Errored)
		self.assertEqual(0, merged.Failed)

		# Compress to a TestsuiteSummary
		result = merged.ToTestsuiteSummary()

		self.assertEqual(7, result.TestsuiteCount)
		self.assertEqual(10, result.TestcaseCount)
		self.assertEqual(0, result.AssertionCount)
		self.assertEqual(10, result.Tests)
		self.assertEqual(3, result.Skipped)
		self.assertEqual(0, result.Errored)
		self.assertEqual(0, result.Failed)

		print(f"Writing merged data as JUnit XML ...")
		startWrite = perf_counter_ns()
		junitDocument = Document.FromTestsuiteSummary(self._outputDirectory / "Platform.xml", result)
		junitDocument.Write(regenerate=True)
		endWrite = perf_counter_ns()
		writeDuration = (endWrite - startWrite) / 1e9

		print()
		print(f"Parsing:    {parsingDuration :.3f} ms")
		print(f"Merging:    {mergingDuration:.3f} ms")
		print(f"Aggregate:  {aggregateDuration:.3f} ms")
		print(f"Writing:    {writeDuration:.3f} ms")

	def test_Unittesting(self) -> None:
		print()

		junitDocuments: List[Document] = []

		directory = Path("tests/data/JUnit/pyTooling")
		print(f"Reading platform testing summary files from '{directory}' ...")
		files = directory.glob("pyTooling-UnitTestReportSummary-XML-*.xml")
		startParsing = perf_counter_ns()
		for file in files:
			print(f"  Parsing {file}")
			junitDocuments.append(Document(file, parse=True, readerMode=JUnitReaderMode.DecoupleTestsuiteHierarchyAndTestcaseClassName))
		endParsing = perf_counter_ns()
		parsingDuration = (endParsing - startParsing) / 1e9

		print(f"Merging generic testsuites ...")
		startMerging = perf_counter_ns()
		merged = MergedTestsuiteSummary("PlatformTesting")
		for summary in junitDocuments:
			print(f"  merging {summary.Path}")
			merged.Merge(summary.ToTestsuiteSummary())
		endMerging = perf_counter_ns()
		mergingDuration = (endMerging - startMerging) / 1e9

		print("Structure of merged testcases:")
		print("-" * 40)
		print(merged.ToTree().Render(prefix="  "), end="")
		print("-" * 40)

		for summary in junitDocuments:
			self.assertGreaterEqual(merged.TestsuiteCount, summary.TestsuiteCount, f"{summary.Path}")
			self.assertGreaterEqual(merged.TestcaseCount, summary.TestcaseCount, f"{summary.Path}")

		mergedCount = len(junitDocuments)
		for item in merged.Iterate(IterationScheme.Default | IterationScheme.IncludeSelf):
			self.assertEqual(mergedCount, item.MergedCount, f"{item.Name}")

		print(f"Aggregating datapoints in testsuite ...")
		startAggregate = perf_counter_ns()
		merged.Aggregate()
		endAggregate = perf_counter_ns()
		aggregateDuration = (endAggregate - startAggregate) / 1e9

		print(f"Writing merged data as JUnit XML ...")
		startWrite = perf_counter_ns()
		junitDocument = Document.FromTestsuiteSummary(self._outputDirectory / "Unittesting.xml", merged)
		junitDocument.Write(regenerate=True)
		endWrite = perf_counter_ns()
		writeDuration = (endWrite - startWrite) / 1e9

		print()
		print(f"Parsing:    {parsingDuration :.3f} ms")
		print(f"Merging:    {mergingDuration:.3f} ms")
		print(f"Aggregate:  {aggregateDuration:.3f} ms")
		print(f"Writing:    {writeDuration:.3f} ms")
