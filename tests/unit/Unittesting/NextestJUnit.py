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
"""The cargo-nextest JUnit dialect: its test case, and the reports nextest wrote for the Rust examples."""
from datetime                                      import datetime, timedelta, timezone
from pathlib                                       import Path
from uuid                                          import UUID

from pyEDAA.Reports.Unittesting                    import Testcase as ut_Testcase, TestcaseStatus, TestsuiteKind
from pyEDAA.Reports.Unittesting                    import UnittestError
from pyEDAA.Reports.Unittesting.JUnit.NextestJUnit import Document, Testcase as ne_Testcase
from pyTooling.Testing                             import Testcase


EXAMPLE_FILE = Path("tests/data/JUnit/pyEDAA.Reports/Rust-Cargo/nextest-junit.xml")
RETRIES_FILE = Path("tests/data/JUnit/pyEDAA.Reports/Rust-Cargo-Retries/nextest-junit-retries.xml")
OUTPUT_DIRECTORY = Path("tests/output/NextestJUnit")


class DataModel(Testcase):
	"""A test case of the dialect carries a start time and a rerun count."""

	def test_Default(self) -> None:
		testcase = ne_Testcase("tc")

		self.assertIsNone(testcase.StartTime)
		self.assertEqual(0, testcase.RerunCount)

	def test_Values(self) -> None:
		startTime = datetime(2026, 10, 8, 11, 5, 35, 662000, tzinfo=timezone.utc)
		testcase = ne_Testcase("tc", timedelta(seconds=0.004), TestcaseStatus.Passed, startTime=startTime, rerunCount=2)

		self.assertEqual(startTime, testcase.StartTime)
		self.assertEqual(2, testcase.RerunCount)

	def test_StartTime_Type(self) -> None:
		with self.assertRaises(TypeError) as context:
			ne_Testcase("tc", startTime="2026-10-08T11:05:35.662+00:00")

		self.assertEqual("Parameter 'startTime' is not of type 'datetime'.", str(context.exception))
		self.assertEqual(["Got type 'str'."], context.exception.__notes__)

	def test_RerunCount_None(self) -> None:
		with self.assertRaises(ValueError) as context:
			ne_Testcase("tc", rerunCount=None)

		self.assertEqual("Parameter 'rerunCount' is None.", str(context.exception))

	def test_RerunCount_Type(self) -> None:
		with self.assertRaises(TypeError) as context:
			ne_Testcase("tc", rerunCount="1")

		self.assertEqual("Parameter 'rerunCount' is not of type 'int'.", str(context.exception))
		self.assertEqual(["Got type 'str'."], context.exception.__notes__)

	def test_RerunCount_Negative(self) -> None:
		with self.assertRaises(ValueError) as context:
			ne_Testcase("tc", rerunCount=-1)

		self.assertEqual("Parameter 'rerunCount' is negative.", str(context.exception))
		self.assertEqual(["Got value '-1'."], context.exception.__notes__)

	def test_Copy(self) -> None:
		startTime = datetime(2026, 10, 8, 11, 5, 35, 662000, tzinfo=timezone.utc)
		testcase = ne_Testcase("tc", startTime=startTime, rerunCount=1).Copy()

		self.assertEqual(startTime, testcase.StartTime)
		self.assertEqual(1, testcase.RerunCount)

	def test_ToTestcase(self) -> None:
		"""The start time is kept in the unified data model, the rerun count is lost."""
		startTime = datetime(2026, 10, 8, 11, 5, 35, 662000, tzinfo=timezone.utc)
		testcase = ne_Testcase("tc", timedelta(seconds=0.004), TestcaseStatus.Passed, startTime=startTime, rerunCount=1)

		self.assertEqual(startTime, testcase.ToTestcase().StartTime)

	def test_FromTestcase(self) -> None:
		startTime = datetime(2026, 10, 8, 11, 5, 35, 662000, tzinfo=timezone.utc)
		testcase = ne_Testcase.FromTestcase(ut_Testcase("tc", startTime=startTime, status=TestcaseStatus.Passed))

		self.assertEqual(startTime, testcase.StartTime)
		self.assertEqual(0, testcase.RerunCount)


class RustCargo(Testcase):
	"""
	The report of the Rust example.

	Console: ``12 tests run: 8 passed, 4 failed, 1 skipped``. The ``#[ignore]``d test ``tests::reset`` is not in the
	report.
	"""

	def test_Summary(self) -> None:
		doc = Document(EXAMPLE_FILE, analyzeAndConvert=True)

		self.assertEqual("nextest-run", doc.Name)
		self.assertEqual(UUID("8c42a7f8-ce32-4ba2-aaf1-ce7c6cd97e8d"), doc.RunID)
		self.assertEqual(datetime(2026, 10, 8, 11, 5, 35, 662000, tzinfo=timezone.utc), doc.StartTime)
		self.assertEqual(timedelta(seconds=0.036), doc.Duration)
		self.assertEqual(12, doc.Tests)
		self.assertEqual(8, doc.Passed)
		self.assertEqual(4, doc.Failed)
		self.assertEqual(0, doc.Skipped)
		self.assertEqual(0, doc.Errored)

	def test_Testsuites(self) -> None:
		"""A test suite per test binary, without hostname, start time and duration; the class name is the binary too."""
		doc = Document(EXAMPLE_FILE, analyzeAndConvert=True)

		self.assertEqual(["counter::sequence", "counter"], list(doc.Testsuites))
		for testsuite in doc.Testsuites.values():
			with self.subTest(testsuite=testsuite.Name):
				self.assertIsNone(testsuite.Hostname)
				self.assertIsNone(testsuite.StartTime)
				self.assertIsNone(testsuite.Duration)
				self.assertEqual([testsuite.Name], list(testsuite.Testclasses))

	def test_Statuses(self) -> None:
		doc = Document(EXAMPLE_FILE, analyzeAndConvert=True)

		statuses = {
			testcase.Name: testcase.Status
			for testsuite in doc.Testsuites.values()
			for testclass in testsuite.Testclasses.values()
			for testcase in testclass.Testcases.values()
		}

		self.assertEqual({
			"printing_test":                  TestcaseStatus.Passed,
			"count_up_and_down":              TestcaseStatus.Passed,
			"underflow":                      TestcaseStatus.Passed,
			"tests::decrement_underflow":     TestcaseStatus.Passed,
			"tests::increment":               TestcaseStatus.Passed,
			"tests::init":                    TestcaseStatus.Passed,
			"tests::not_panicking":           TestcaseStatus.Failed,
			"tests::failing_result":          TestcaseStatus.Failed,
			"tests::failing":                 TestcaseStatus.Failed,
			"tests::decrement":               TestcaseStatus.Passed,
			"tests::panicking":               TestcaseStatus.Failed,
			"tests::try_decrement_underflow": TestcaseStatus.Passed,
		}, statuses)

	def test_Failures(self) -> None:
		"""Every failure has the same type, its message is the first line of the test's error output."""
		doc = Document(EXAMPLE_FILE, analyzeAndConvert=True)
		testcases = doc.Testsuites["counter"].Testclasses["counter"].Testcases

		self.assertEqual("Error: Underflow", testcases["tests::failing_result"].Message)
		self.assertEqual("note: test did not panic as expected at src/lib.rs:119:5", testcases["tests::not_panicking"].Message)
		self.assertEqual(
			"thread 'tests::panicking' (554411) panicked at src/lib.rs:37:31", testcases["tests::panicking"].Message
		)
		self.assertTrue(testcases["tests::failing"].Details.startswith(
			"thread 'tests::failing' (554412) panicked at src/lib.rs:100:9:\nassertion `left == right` failed"
		))

	def test_Output(self) -> None:
		doc = Document(EXAMPLE_FILE, analyzeAndConvert=True)
		testcase = doc.Testsuites["counter::sequence"].Testclasses["counter::sequence"].Testcases["printing_test"]

		self.assertIn("Output written to stdout by a passing test.\n", testcase.StandardOutput)
		self.assertEqual("Output written to stderr by a passing test.\n", testcase.StandardError)

	def test_StartTimes(self) -> None:
		doc = Document(EXAMPLE_FILE, analyzeAndConvert=True)
		testcase = doc.Testsuites["counter"].Testclasses["counter"].Testcases["tests::failing"]

		self.assertEqual(datetime(2026, 10, 8, 11, 5, 35, 662000, tzinfo=timezone.utc), testcase.StartTime)
		self.assertEqual(timedelta(seconds=0.004), testcase.Duration)

	def test_UnifiedDataModel(self) -> None:
		"""The class name repeats the test suite's name, so the test cases are one level below a suite of the same name."""
		summary = Document(EXAMPLE_FILE, analyzeAndConvert=True).ToTestsuiteSummary()
		summary.Aggregate()

		testsuite = summary.Testsuites["counter"]
		testclass = testsuite.Testsuites["counter"]
		testcase = testclass.Testcases["tests::failing"]

		self.assertEqual(TestsuiteKind.Logical, testsuite.Kind)
		self.assertEqual(TestsuiteKind.Class, testclass.Kind)
		self.assertEqual(TestcaseStatus.Failed, testcase.Status)
		self.assertEqual(datetime(2026, 10, 8, 11, 5, 35, 662000, tzinfo=timezone.utc), testcase.StartTime)
		self.assertEqual(12, summary.TestcaseCount)

	def test_Write(self) -> None:
		"""The run ID is written back; read through the unified data model, it is lost."""
		outputFile = OUTPUT_DIRECTORY / "nextest-junit.xml"
		outputFile.parent.mkdir(parents=True, exist_ok=True)

		doc = Document(EXAMPLE_FILE, analyzeAndConvert=True)
		doc.Write(outputFile, regenerate=True, overwrite=True)
		self.assertEqual(doc.RunID, Document(outputFile, analyzeAndConvert=True).RunID)

		Document.FromTestsuiteSummary(outputFile, doc.ToTestsuiteSummary()).Write(regenerate=True, overwrite=True)
		self.assertIsNone(Document(outputFile, analyzeAndConvert=True).RunID)

	def test_Write_WithoutStartTime(self) -> None:
		doc = Document(EXAMPLE_FILE, analyzeAndConvert=True)
		summary = doc.ToTestsuiteSummary()
		summary._startTime = None

		with self.assertRaises(UnittestError) as context:
			Document.FromTestsuiteSummary(OUTPUT_DIRECTORY / "no-timestamp.xml", summary).Generate()

		self.assertEqual(
			"The cargo-nextest + JUnit format requires a timestamp on <testsuites>, but the report has none.",
			str(context.exception)
		)


class RustCargoRetries(Testcase):
	"""
	A report with retries, a reported skip and a setup script.

	Console: ``4 tests run: 2 passed (1 flaky), 2 failed, 1 skipped``. The report counts the setup script as a test.
	"""

	def test_Summary(self) -> None:
		doc = Document(RETRIES_FILE, analyzeAndConvert=True)

		self.assertEqual(6, doc.Tests)
		self.assertEqual(3, doc.Passed)
		self.assertEqual(2, doc.Failed)
		self.assertEqual(1, doc.Skipped)
		self.assertEqual(0, doc.Errored)

	def test_SetupScript(self) -> None:
		doc = Document(RETRIES_FILE, analyzeAndConvert=True)
		testcase = doc.Testsuites["@setup-script:prepare"].Testclasses["@setup-script:prepare"].Testcases["prepare"]

		self.assertEqual(TestcaseStatus.Passed, testcase.Status)
		self.assertEqual("(stdout not captured)", testcase.StandardOutput)

	def test_Statuses(self) -> None:
		"""A flaky test passes, unless it is configured to fail; the reruns are counted."""
		doc = Document(RETRIES_FILE, analyzeAndConvert=True)
		testcases = doc.Testsuites["retries"].Testclasses["retries"].Testcases

		self.assertEqual({
			"tests::ignored":       (TestcaseStatus.Skipped, 0),
			"tests::passing":       (TestcaseStatus.Passed,  0),
			"tests::flaky_failing": (TestcaseStatus.Failed,  1),
			"tests::flaky":         (TestcaseStatus.Passed,  1),
			"tests::failing":       (TestcaseStatus.Failed,  1),
		}, {name: (testcase.Status, testcase.RerunCount) for name, testcase in testcases.items()})

	def test_Skipped(self) -> None:
		"""A skipped test has no start time."""
		doc = Document(RETRIES_FILE, analyzeAndConvert=True)
		testcase = doc.Testsuites["retries"].Testclasses["retries"].Testcases["tests::ignored"]

		self.assertEqual("Skipped: test does not match the run-ignored option", testcase.Message)
		self.assertIsNone(testcase.StartTime)
		self.assertEqual(timedelta(0), testcase.Duration)

	def test_FlakyFailing(self) -> None:
		doc = Document(RETRIES_FILE, analyzeAndConvert=True)
		testcase = doc.Testsuites["retries"].Testclasses["retries"].Testcases["tests::flaky_failing"]

		self.assertEqual("test passed on attempt 2/2 but is configured to fail when flaky", testcase.Message)
		self.assertIsNone(testcase.Details)

	def test_Write(self) -> None:
		"""Reruns are not written."""
		outputFile = OUTPUT_DIRECTORY / "nextest-junit-retries.xml"
		outputFile.parent.mkdir(parents=True, exist_ok=True)

		Document(RETRIES_FILE, analyzeAndConvert=True).Write(outputFile, regenerate=True, overwrite=True)
		doc = Document(outputFile, analyzeAndConvert=True)
		testcase = doc.Testsuites["retries"].Testclasses["retries"].Testcases["tests::failing"]

		self.assertEqual(TestcaseStatus.Failed, testcase.Status)
		self.assertEqual(0, testcase.RerunCount)
