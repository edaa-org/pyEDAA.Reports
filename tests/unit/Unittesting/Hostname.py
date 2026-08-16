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
"""The hostname of a test suite: on the data model, through a merge, and across a JUnit round trip."""
from pathlib  import Path
from unittest import TestCase as ut_TestCase

from pyEDAA.Reports.Unittesting                   import MergedTestsuiteSummary, Testsuite, TestsuiteSummary
from pyEDAA.Reports.Unittesting.JUnit             import Document, JUnitReaderMode
from pyEDAA.Reports.Unittesting.JUnit.CTestJUnit  import Document as CTestDocument
from pyEDAA.Reports.Unittesting.JUnit.PyTestJUnit import Document as PyTestDocument


class DataModel(ut_TestCase):
	"""A test suite records the host it was executed on."""

	def test_HostnameIsNoneByDefault(self) -> None:
		testsuite = Testsuite("suite")

		self.assertIsNone(testsuite.Hostname)

	def test_HostnameIsKept(self) -> None:
		testsuite = Testsuite("suite", hostname="runner")

		self.assertEqual("runner", testsuite.Hostname)

	def test_CopyKeepsTheHostname(self) -> None:
		testsuite = Testsuite("suite", hostname="runner")

		copy = testsuite.Copy()

		self.assertEqual("runner", copy.Hostname)
		self.assertEqual(testsuite._kind, copy._kind)


class Merging(ut_TestCase):
	"""Merging test suites of the same name combines their hostnames."""

	@staticmethod
	def _summary(name: str, hostname) -> TestsuiteSummary:
		return TestsuiteSummary("summary", testsuites=(Testsuite(name, hostname=hostname),))

	def _mergedHostname(self, *hostnames):
		merged = MergedTestsuiteSummary("summary")
		for hostname in hostnames:
			merged.Merge(self._summary("suite", hostname))

		return merged.ToTestsuiteSummary()._testsuites["suite"].Hostname

	def test_OneHost(self) -> None:
		self.assertEqual("alpha", self._mergedHostname("alpha"))

	def test_TheSameHostTwice(self) -> None:
		self.assertEqual("alpha", self._mergedHostname("alpha", "alpha"))

	def test_TwoHosts(self) -> None:
		self.assertEqual("various", self._mergedHostname("alpha", "beta"))

	def test_ThreeHostsWithARepetition(self) -> None:
		self.assertEqual("various", self._mergedHostname("alpha", "beta", "alpha"))

	def test_NoHostAtAll(self) -> None:
		self.assertIsNone(self._mergedHostname(None, None))

	def test_AnUnrecordedHostDoesNotMakeItVarious(self) -> None:
		"""A test suite without a hostname ran somewhere unrecorded, not somewhere else."""
		self.assertEqual("alpha", self._mergedHostname("alpha", None))
		self.assertEqual("alpha", self._mergedHostname(None, "alpha"))


class RoundTrip(ut_TestCase):
	"""A report written by pyEDAA.Reports can be read back with the dialect it was written in."""

	_referenceFile = Path("tests/data/JUnit/pyEDAA.Reports/Python-pytest/TestReportSummary.xml")
	_outputDirectory = Path("tests/output/Hostname")

	@classmethod
	def setUpClass(cls) -> None:
		cls._outputDirectory.mkdir(parents=True, exist_ok=True)

	def test_PyTestDialectRoundTrip(self) -> None:
		"""Reading, merging and writing a pytest report keeps it readable by the strict pyTest-JUnit reader."""
		document = Document(
			self._referenceFile,
			analyzeAndConvert=True,
			readerMode=JUnitReaderMode.DecoupleTestsuiteHierarchyAndTestcaseClassName
		)

		merged = MergedTestsuiteSummary("summary")
		merged.Merge(document.ToTestsuiteSummary())
		merged.Aggregate()

		outputFile = self._outputDirectory / "roundtrip.xml"
		PyTestDocument.FromTestsuiteSummary(outputFile, merged.ToTestsuiteSummary()).Write(regenerate=True, overwrite=True)

		# Without a hostname in the merged report, this read raises "Required parameter 'hostname' not found".
		rereadDocument = PyTestDocument(outputFile, analyzeAndConvert=True)

		self.assertGreater(len(rereadDocument._testsuites), 0)
		for testsuite in rereadDocument._testsuites.values():
			self.assertIsNotNone(testsuite._hostname, f"Testsuite '{testsuite._name}' lost its hostname.")

	def test_CTestDialectWritesAHostnameAndNotTheWordNone(self) -> None:
		"""CTest-JUnit.xsd requires the attribute, so it must never be the string representation of ``None``."""
		summary = TestsuiteSummary("summary", testsuites=(Testsuite("suite"),))

		outputFile = self._outputDirectory / "ctest.xml"
		CTestDocument.FromTestsuiteSummary(outputFile, summary).Write(regenerate=True, overwrite=True)

		content = outputFile.read_text()

		self.assertNotIn('hostname="None"', content)
		self.assertIn('hostname="localhost"', content)
