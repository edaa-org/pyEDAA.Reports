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
"""Testcase for the special cases of Catch2's JUnit reporter."""
from pathlib  import Path
from typing   import ClassVar
from unittest import TestCase as ut_TestCase

from pyEDAA.Reports.Unittesting                   import TestcaseStatus
from pyEDAA.Reports.Unittesting.JUnit.Catch2JUnit import Document, Testcase


class Catch2Quirks(ut_TestCase):
	"""
	Read a report written by Catch2 from :file:`tests/data/JUnit/Catch2/Quirks.test.cpp`.

	Catch2's console counts 8 test cases: 3 passed, 4 failed, 1 failed as expected.
	"""

	_junitFile: ClassVar[Path] = Path("tests/data/JUnit/Catch2/catch2-junit-quirks.xml")
	_document:  ClassVar[Document]

	@classmethod
	def setUpClass(cls) -> None:
		cls._document = Document(cls._junitFile, analyzeAndConvert=True)

	def _testcase(self, classname: str, name: str) -> Testcase:
		return self._document.Testsuites["quirks"].Testclasses[classname].Testcases[name]

	def test_Counts(self) -> None:
		self.assertEqual(8, self._document.TestcaseCount)
		self.assertEqual(4, self._document.Passed)
		self.assertEqual(3, self._document.Failed)
		self.assertEqual(0, self._document.Errored)
		self.assertEqual(1, self._document.Skipped)

	def test_NoAssertions(self) -> None:
		"""A test case without assertions and without output is missing."""
		self.assertNotIn("NoAssertions", self._document.Testsuites["quirks"].Testclasses["quirks.global"].Testcases)

	def test_Output(self) -> None:
		"""A test case without assertions, but with output, is reported."""
		testcase = self._testcase("quirks.global", "Output")

		self.assertIs(TestcaseStatus.Passed, testcase.Status)
		self.assertEqual("Hello Catch2", testcase.StandardOutput.strip())

	def test_MayFail(self) -> None:
		"""A failure expected by ``[!mayfail]`` is skipped."""
		testcase = self._testcase("quirks.global", "MayFail")

		self.assertIs(TestcaseStatus.Skipped, testcase.Status)
		self.assertEqual("TEST_CASE tagged with !mayfail", testcase.Message)
		self.assertIn("CHECK( 1 == 2 )", testcase.Details)

	def test_ShouldFail(self) -> None:
		"""A ``[!shouldfail]`` test case passing unexpectedly is failed for Catch2, but passed in the report."""
		testcase = self._testcase("quirks.global", "ShouldFail")

		self.assertIs(TestcaseStatus.Passed, testcase.Status)

	def test_Nested(self) -> None:
		"""A failure in a section fails the section's testcase only."""
		self.assertIs(TestcaseStatus.Passed, self._testcase("quirks.global", "Nested").Status)
		self.assertIs(TestcaseStatus.Failed, self._testcase("quirks.global", "Nested/Inner").Status)

	def test_ExplicitFailure(self) -> None:
		"""``FAIL()`` has no expression, so ``<failure>`` has no message."""
		testcase = self._testcase("quirks.global", "ExplicitFailure")

		self.assertIs(TestcaseStatus.Failed, testcase.Status)
		self.assertIsNone(testcase.Message)
		self.assertIn("Explicit failure.", testcase.Details)

	def test_TwoFailures(self) -> None:
		"""Only the first failed assertion is reported."""
		testcase = self._testcase("quirks.global", "TwoFailures")

		self.assertIs(TestcaseStatus.Failed, testcase.Status)
		self.assertEqual("1 == 2", testcase.Message)
		self.assertNotIn("3 == 4", testcase.Details)

	def test_NamespacedFixture(self) -> None:
		"""The namespace of a fixture class becomes a test suite in the unified data model."""
		summary = self._document.ToTestsuiteSummary()

		testsuite = summary.Testsuites["quirks"].Testsuites["quirks"].Testsuites["Namespace"].Testsuites["Fixture"]

		self.assertIn("NamespacedFixture", testsuite.Testcases)
