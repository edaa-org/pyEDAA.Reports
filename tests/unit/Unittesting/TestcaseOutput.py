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
"""The message, details and captured output of a test case: on the data model, through a merge, and from JUnit files."""
from pathlib  import Path
from textwrap import dedent

from pyEDAA.Reports.Unittesting                   import MergedTestcase, Testcase as ut_Testcase, TestcaseStatus
from pyEDAA.Reports.Unittesting.JUnit             import Document, Testcase as ju_Testcase
from pyEDAA.Reports.Unittesting.JUnit.PyTestJUnit import Document as PyTestDocument
from pyTooling.Testing                            import Testcase


REPORT = dedent("""\
	<?xml version="1.0" encoding="utf-8"?>
	<testsuites name="pytest tests">
	  <testsuite name="pytest" errors="1" failures="1" skipped="1" tests="4" time="0.5"
	             timestamp="2026-10-06T10:00:00.000000+02:00" hostname="runner">
	    <testcase classname="tests.unit.Module.Class" name="test_Passed" time="0.1" />
	    <testcase classname="tests.unit.Module.Class" name="test_Failed" time="0.1">
	      <failure message="AssertionError: assert 1 == 2">Traceback (most recent call last):
	AssertionError: assert 1 == 2</failure>
	      <system-out>Hello stdout</system-out>
	      <system-err>Hello stderr</system-err>
	    </testcase>
	    <testcase classname="tests.unit.Module.Class" name="test_Errored" time="0.1">
	      <error message="failed on setup with &quot;KeyError&quot;">KeyError: 'key'</error>
	    </testcase>
	    <testcase classname="tests.unit.Module.Class" name="test_Skipped" time="0.0">
	      <skipped type="pytest.skip" message="not on this platform" />
	    </testcase>
	  </testsuite>
	</testsuites>
	""")


class DataModel(Testcase):
	"""A test case keeps the message, details and captured output it was created with."""

	def test_Default(self) -> None:
		testcase = ut_Testcase("tc")

		self.assertIsNone(testcase.Message)
		self.assertIsNone(testcase.Details)
		self.assertIsNone(testcase.StandardOutput)
		self.assertIsNone(testcase.StandardError)

	def test_Values(self) -> None:
		testcase = ut_Testcase("tc", message="msg", details="trace", standardOutput="out", standardError="err")

		self.assertEqual("msg", testcase.Message)
		self.assertEqual("trace", testcase.Details)
		self.assertEqual("out", testcase.StandardOutput)
		self.assertEqual("err", testcase.StandardError)

	def test_Values_JUnit(self) -> None:
		testcase = ju_Testcase("tc", message="msg", details="trace", standardOutput="out", standardError="err")

		self.assertEqual("msg", testcase.Message)
		self.assertEqual("trace", testcase.Details)
		self.assertEqual("out", testcase.StandardOutput)
		self.assertEqual("err", testcase.StandardError)

	def test_WrongType(self) -> None:
		with self.assertRaises(TypeError) as context:
			_ = ut_Testcase("tc", standardOutput=1)

		self.assertEqual("Parameter 'standardOutput' is not of type 'str'.", str(context.exception))
		self.assertEqual(["Got type 'int'."], context.exception.__notes__)

	def test_Copy(self) -> None:
		testcase = ut_Testcase("tc", message="msg", details="trace", standardOutput="out", standardError="err")

		copy = testcase.Copy()

		self.assertEqual("msg", copy.Message)
		self.assertEqual("trace", copy.Details)
		self.assertEqual("out", copy.StandardOutput)
		self.assertEqual("err", copy.StandardError)

	def test_Conversion(self) -> None:
		"""The JUnit data model and the unified data model convert the fields into each other."""
		testcase = ju_Testcase("tc", message="msg", details="trace", standardOutput="out", standardError="err")

		converted = ju_Testcase.FromTestcase(testcase.ToTestcase())

		self.assertEqual("msg", converted.Message)
		self.assertEqual("trace", converted.Details)
		self.assertEqual("out", converted.StandardOutput)
		self.assertEqual("err", converted.StandardError)


class Merging(Testcase):
	"""A merged test case keeps the message, details and captured output of the first merged test case having them."""

	def test_FirstNonNone(self) -> None:
		merged = MergedTestcase(ut_Testcase("tc", standardOutput="out1"))
		merged.Merge(ut_Testcase("tc", message="msg2", standardOutput="out2"))
		merged.Merge(ut_Testcase("tc", message="msg3", standardError="err3"))

		testcase = merged.ToTestcase()

		self.assertEqual("msg2", testcase.Message)
		self.assertIsNone(testcase.Details)
		self.assertEqual("out1", testcase.StandardOutput)
		self.assertEqual("err3", testcase.StandardError)


class JUnitReader(Testcase):
	"""The JUnit reader keeps the content of ``<failure>``, ``<error>``, ``<skipped>`` and the captured output."""

	_outputDirectory = Path("tests/output/TestcaseOutput")

	@classmethod
	def setUpClass(cls) -> None:
		cls._outputDirectory.mkdir(parents=True, exist_ok=True)
		cls._reportFile = cls._outputDirectory / "report.xml"
		cls._reportFile.write_text(REPORT, encoding="utf-8")

	def _testcases(self, document: Document):
		testclass = document.Testsuites["pytest"].Testclasses["tests.unit.Module.Class"]
		return testclass.Testcases

	def test_Read(self) -> None:
		testcases = self._testcases(Document(self._reportFile, analyzeAndConvert=True))

		passed = testcases["test_Passed"]
		self.assertEqual(TestcaseStatus.Passed, passed.Status)
		self.assertIsNone(passed.Message)
		self.assertIsNone(passed.Details)
		self.assertIsNone(passed.StandardOutput)
		self.assertIsNone(passed.StandardError)

		failed = testcases["test_Failed"]
		self.assertEqual(TestcaseStatus.Failed, failed.Status)
		self.assertEqual("AssertionError: assert 1 == 2", failed.Message)
		self.assertEqual("Traceback (most recent call last):\nAssertionError: assert 1 == 2", failed.Details)
		self.assertEqual("Hello stdout", failed.StandardOutput)
		self.assertEqual("Hello stderr", failed.StandardError)

		errored = testcases["test_Errored"]
		self.assertEqual(TestcaseStatus.Errored, errored.Status)
		self.assertEqual("failed on setup with \"KeyError\"", errored.Message)
		self.assertEqual("KeyError: 'key'", errored.Details)

		skipped = testcases["test_Skipped"]
		self.assertEqual(TestcaseStatus.Skipped, skipped.Status)
		self.assertEqual("not on this platform", skipped.Message)
		self.assertIsNone(skipped.Details)

	def test_Read_UnifiedModel(self) -> None:
		"""The fields reach the unified data model, so every consumer of a converted summary sees them."""
		summary = Document(self._reportFile, analyzeAndConvert=True).ToTestsuiteSummary()

		testsuite = summary.Testsuites["pytest"]
		for name in ("tests", "unit", "Module", "Class"):
			testsuite = testsuite.Testsuites[name]

		failed = testsuite.Testcases["test_Failed"]
		self.assertEqual("AssertionError: assert 1 == 2", failed.Message)
		self.assertEqual("Traceback (most recent call last):\nAssertionError: assert 1 == 2", failed.Details)
		self.assertEqual("Hello stdout", failed.StandardOutput)
		self.assertEqual("Hello stderr", failed.StandardError)

	def test_RoundTrip(self) -> None:
		"""A written report carries the fields, so reading it back restores them."""
		summary = Document(self._reportFile, analyzeAndConvert=True).ToTestsuiteSummary()

		outputFile = self._outputDirectory / "roundtrip.xml"
		PyTestDocument.FromTestsuiteSummary(outputFile, summary).Write(regenerate=True, overwrite=True)

		testcases = self._testcases(PyTestDocument(outputFile, analyzeAndConvert=True))

		failed = testcases["test_Failed"]
		self.assertEqual(TestcaseStatus.Failed, failed.Status)
		self.assertEqual("AssertionError: assert 1 == 2", failed.Message)
		self.assertEqual("Traceback (most recent call last):\nAssertionError: assert 1 == 2", failed.Details)
		self.assertEqual("Hello stdout", failed.StandardOutput)
		self.assertEqual("Hello stderr", failed.StandardError)

		skipped = testcases["test_Skipped"]
		self.assertEqual(TestcaseStatus.Skipped, skipped.Status)
		self.assertEqual("not on this platform", skipped.Message)
		self.assertIsNone(skipped.Details)
