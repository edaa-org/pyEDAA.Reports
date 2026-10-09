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
"""
Unit tests for the JUnit dialect of the .NET test logger ``JunitXml.TestLogger``, as ``dotnet test --logger junit``
writes it.

The report in :file:`tests/data/JUnit/pyEDAA.Reports/CSharp-xUnit` is written by the example
:file:`examples/CSharp/xUnit`.
"""
from datetime                                         import datetime, timedelta, timezone
from pathlib                                          import Path
from textwrap                                         import dedent

from lxml.etree                                       import parse

from pyEDAA.Reports.Unittesting                       import TestcaseStatus, TestsuiteKind, UnittestError
from pyEDAA.Reports.Unittesting.JUnit                 import Document as AnyJUnitDocument
from pyEDAA.Reports.Unittesting.JUnit.TestLoggerJUnit import Document, Testsuite as ju_Testsuite
from pyEDAA.Reports.Unittesting.JUnit.TestLoggerJUnit import Testclass as ju_Testclass, Testcase as ju_Testcase
from pyTooling.Testing                                import Testcase


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


#: The JUnit XML file of the example.
JUNIT_FILE = Path("tests/data/JUnit/pyEDAA.Reports/CSharp-xUnit/MyLibrary.Tests.junit.xml")

#: A report of another dialect, with an errored test, a skip reason and a start time not in UTC.
REPORT = dedent("""\
	<?xml version="1.0" encoding="utf-8"?>
	<testsuites>
	  <testsuite name="pytest" errors="1" failures="1" skipped="1" tests="4" time="0.5"
	             timestamp="2026-10-06T10:00:00.000000+02:00" hostname="runner">
	    <testcase classname="tests.unit.Module.Class" name="test_Passed" time="0.0" />
	    <testcase classname="tests.unit.Module.Class" name="test_Failed" time="0.1">
	      <failure message="AssertionError: assert 1 == 2">Traceback (most recent call last):
	AssertionError: assert 1 == 2</failure>
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


class Reading(Testcase):
	"""The logger's report read with the tool's semantics: failed tests only, no skip reasons, a UTC start time."""

	def test_Testsuite(self) -> None:
		document = Document(JUNIT_FILE, analyzeAndConvert=True)

		self.assertEqual(1, document.TestsuiteCount)
		self.assertEqual(11, document.TestcaseCount)
		self.assertEqual(7, document.Passed)
		self.assertEqual(3, document.Failed)
		self.assertEqual(1, document.Skipped)
		self.assertEqual(0, document.Errored)

		testsuite = document.Testsuites["MyLibrary.Tests.dll"]
		self.assertEqual("dffa20ef8728", testsuite.Hostname)
		self.assertEqual(datetime(2026, 10, 8, 11, 9, 26, tzinfo=timezone.utc), testsuite.StartTime)
		self.assertEqual(timedelta(seconds=0.052), testsuite.Duration)
		self.assertEqual(testsuite.StartTime, document.StartTime)
		self.assertEqual(["MyLibrary.Tests.CalculatorTests", "MyLibrary.Tests.CounterTests"], sorted(testsuite.Testclasses))

	def test_Testcases(self) -> None:
		testclass = Document(JUNIT_FILE, analyzeAndConvert=True).Testsuites["MyLibrary.Tests.dll"].Testclasses
		testcases = testclass["MyLibrary.Tests.CalculatorTests"].Testcases

		failed = testcases["Absolute(value: -4, expected: 5)"]
		self.assertEqual(TestcaseStatus.Failed, failed.Status)
		self.assertEqual("Assert.Equal() Failure: Values differ\nExpected: 5\nActual:   4", failed.Message)
		self.assertEqual(
			"at MyLibrary.Tests.CalculatorTests.Absolute(Int32 value, Int32 expected)",
			failed.Details.partition(" in ")[0]
		)

		exception = testcases["DivideByZero"]
		self.assertEqual(TestcaseStatus.Failed, exception.Status)
		self.assertEqual("System.DivideByZeroException : Attempted to divide by zero.", exception.Message)

		skipped = testcases["Multiply"]
		self.assertEqual(TestcaseStatus.Skipped, skipped.Status)
		self.assertIsNone(skipped.Message)
		self.assertIsNone(skipped.Details)

		output = testclass["MyLibrary.Tests.CounterTests"].Testcases["Increment"]
		self.assertEqual(TestcaseStatus.Passed, output.Status)
		self.assertEqual("Counter value: 1\n\n", output.StandardOutput)
		self.assertEqual(timedelta(seconds=0.001), output.Duration)

	def test_UnifiedModel(self) -> None:
		"""Each part of a class' namespace becomes a test suite of kind ``Namespace``."""
		summary = Document(JUNIT_FILE, analyzeAndConvert=True).ToTestsuiteSummary()
		summary.Aggregate()

		testsuite = summary.Testsuites["MyLibrary.Tests.dll"]
		self.assertEqual(TestsuiteKind.Logical, testsuite.Kind)

		namespace = testsuite.Testsuites["MyLibrary"].Testsuites["Tests"]
		self.assertEqual(TestsuiteKind.Namespace, testsuite.Testsuites["MyLibrary"].Kind)
		self.assertEqual(TestsuiteKind.Namespace, namespace.Kind)
		self.assertEqual(TestsuiteKind.Class, namespace.Testsuites["CalculatorTests"].Kind)
		self.assertEqual(8, len(namespace.Testsuites["CalculatorTests"].Testcases))
		self.assertEqual(3, len(namespace.Testsuites["CounterTests"].Testcases))

		self.assertEqual(11, summary.TestcaseCount)
		self.assertEqual(7, summary.Passed)
		self.assertEqual(3, summary.Failed)
		self.assertEqual(1, summary.Skipped)

	def test_UnifiedModel_ClassNames(self) -> None:
		"""A nested class, a parameterized test class and a class in the global namespace keep their names."""
		testsuite = ju_Testsuite("Tests.dll", "localhost")
		for classname in ("NS.Sub.Outer+Inner", "NS.Fixture(\"a.b\",4.2)", ".Global"):
			testclass = ju_Testclass(classname, parent=testsuite)
			testclass.AddTestcase(ju_Testcase("Test", timedelta(seconds=0.1), TestcaseStatus.Passed))

		unified = testsuite.ToTestsuite()

		self.assertEqual(["Global", "NS"], sorted(unified.Testsuites))
		self.assertEqual(TestsuiteKind.Class, unified.Testsuites["Global"].Kind)
		self.assertEqual(TestsuiteKind.Namespace, unified.Testsuites["NS"].Kind)
		self.assertEqual(["Fixture(\"a.b\",4.2)", "Sub"], sorted(unified.Testsuites["NS"].Testsuites))
		self.assertEqual(TestsuiteKind.Class, unified.Testsuites["NS"].Testsuites["Fixture(\"a.b\",4.2)"].Kind)
		self.assertEqual(["Outer+Inner"], list(unified.Testsuites["NS"].Testsuites["Sub"].Testsuites))


class Writing(Testcase):
	"""A report of another dialect written as the logger would write it."""

	_outputDirectory = Path("tests/output/JunitXmlTestLogger")

	@classmethod
	def setUpClass(cls) -> None:
		cls._outputDirectory.mkdir(parents=True, exist_ok=True)
		cls._reportFile = cls._outputDirectory / "report.xml"
		cls._reportFile.write_text(REPORT, encoding="utf-8")

	def _write(self, fileName: str) -> Path:
		summary = AnyJUnitDocument(self._reportFile, analyzeAndConvert=True).ToTestsuiteSummary()
		summary.Aggregate()

		outputFile = self._outputDirectory / fileName
		Document.FromTestsuiteSummary(outputFile, summary).Write(regenerate=True, overwrite=True)

		return outputFile

	def test_Write(self) -> None:
		"""An error becomes a failure, a skip reason is dropped, the start time is written in UTC."""
		root = parse(self._write("written.xml")).getroot()

		self.assertEqual({}, dict(root.attrib))
		testsuite = root.find("testsuite")
		self.assertEqual("4", testsuite.get("tests"))
		self.assertEqual("2", testsuite.get("failures"))
		self.assertEqual("0", testsuite.get("errors"))
		self.assertEqual("2026-10-06T08:00:00", testsuite.get("timestamp"))
		self.assertEqual("0", testsuite.get("id"))
		self.assertEqual("pytest", testsuite.get("package"))

		testcases = {testcase.get("name"): testcase for testcase in testsuite.iterfind("testcase")}
		self.assertEqual("0.0000001", testcases["test_Passed"].get("time"))

		errored = testcases["test_Errored"].find("failure")
		self.assertEqual("failure", errored.get("type"))
		self.assertEqual("failed on setup with \"KeyError\"", errored.get("message"))
		self.assertEqual("KeyError: 'key'", errored.text)

		skipped = testcases["test_Skipped"].find("skipped")
		self.assertEqual({}, dict(skipped.attrib))
		self.assertIsNone(skipped.text)

	def test_Write_ReadBack(self) -> None:
		document = Document(self._write("readback.xml"), analyzeAndConvert=True)

		self.assertEqual(4, document.TestcaseCount)
		self.assertEqual(2, document.Failed)
		self.assertEqual(0, document.Errored)
		self.assertEqual(datetime(2026, 10, 6, 8, 0, 0, tzinfo=timezone.utc), document.StartTime)

	def test_Write_NoTimestamp(self) -> None:
		summary = AnyJUnitDocument(self._reportFile, analyzeAndConvert=True).ToTestsuiteSummary()
		summary.Testsuites["pytest"]._startTime = None

		document = Document.FromTestsuiteSummary(self._outputDirectory / "notimestamp.xml", summary)
		with self.assertRaises(UnittestError) as context:
			document.Generate()

		self.assertEqual(
			"The JunitXml.TestLogger JUnit format requires a timestamp on <testsuite>, but 'pytest' has none.",
			str(context.exception)
		)
