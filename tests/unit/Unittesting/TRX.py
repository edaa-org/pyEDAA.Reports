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
"""
Reading Visual Studio's test results format (TRX), as ``dotnet test --logger trx`` writes it.

The reports in :file:`tests/data/TRX` are written by VSTest's TRX logger: :file:`CSharp-xUnit` by the example
:file:`examples/CSharp/xUnit`, :file:`CSharp-MSTest` and :file:`CSharp-NUnit` by small MSTest and NUnit test projects.
"""
from datetime                         import datetime, timedelta, timezone
from pathlib                          import Path
from typing                           import Dict, Iterable, Optional as Nullable
from uuid                             import UUID

from pyEDAA.Reports.Unittesting       import UnittestError, DuplicateTestcaseError, TestcaseStatus, TestsuiteKind
from pyEDAA.Reports.Unittesting       import TestsuiteStatus, TestsuiteSummary as ut_TestsuiteSummary
from pyEDAA.Reports.Unittesting       import TRX
from pyEDAA.Reports.Unittesting.JUnit import Document as JUnitDocument
from pyTooling.Testing                import Testcase


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


DATA = Path(__file__).parent.parent.parent / "data/TRX"     #: Directory of the TRX files.
OUTPUT = Path(__file__).parent.parent.parent / "output/TRX"  #: Directory of modified TRX files.
XUNIT_FILE = DATA / "CSharp-xUnit/MyLibrary.Tests.trx"       #: TRX file of the xUnit.net example.
MSTEST_FILE = DATA / "CSharp-MSTest/MSTestSample.trx"        #: TRX file of the MSTest test project.
NUNIT_FILE = DATA / "CSharp-NUnit/NUnitSample.trx"           #: TRX file of the NUnit test project.


def statuses(summary: ut_TestsuiteSummary) -> Dict[str, TestcaseStatus]:
	"""
	Return the status of each test case in a test suite summary.

	:param summary: The test suite summary.
	:returns:       The test cases' statuses, by test suite and test case name, e.g. ``CounterTests.Increment``.
	"""
	return {
		f"{testcase.Parent.Name}.{testcase.Name}": testcase.Status for testcase in summary.IterateTestcases()
	}


class Schema(Testcase):
	"""Every TRX file is validated against the schema reverse engineered from VSTest's TRX logger."""

	@classmethod
	def setUpClass(cls) -> None:
		OUTPUT.mkdir(parents=True, exist_ok=True)

	def test_Fixtures(self) -> None:
		for path in (XUNIT_FILE, MSTEST_FILE, NUNIT_FILE):
			with self.subTest(path=path.parent.name):
				document = TRX.Document(path)
				document.Analyze()

				self.assertGreater(document.AnalysisDuration, timedelta())

	def test_UnknownTestId(self) -> None:
		"""A result referring to no test definition is invalid."""
		path = OUTPUT / "UnknownTestId.trx"
		path.write_text(
			XUNIT_FILE.read_text(encoding="utf-8-sig").replace(
				'testId="1de947dc-261b-bd9c-9a22-722b2250cb86" testName',
				'testId="00000000-0000-0000-0000-000000000000" testName'
			),
			encoding="utf-8"
		)

		with self.assertRaises(UnittestError) as context:
			_ = TRX.Document(path, analyzeAndConvert=True)

		self.assertEqual(f"Validation error for '{path}' using XSD schema 'VSTest-TRX.xsd'.", str(context.exception))
		self.assertIn(
			"No match found for key-sequence ['00000000-0000-0000-0000-000000000000']",
			context.exception.__notes__[0]
		)

	def test_JUnitFile(self) -> None:
		path = DATA.parent / "JUnit/pyEDAA.Reports/CSharp-xUnit/MyLibrary.Tests.junit.xml"

		with self.assertRaises(UnittestError) as context:
			_ = TRX.Document(path, analyzeAndConvert=True)

		self.assertEqual(
			f"Root element of '{path}' is not '<TestRun>' in namespace '{TRX.TRX_NAMESPACE}'.",
			str(context.exception)
		)
		self.assertEqual(["Got root element 'testsuites'."], context.exception.__notes__)

	def test_JUnitReader(self) -> None:
		"""The JUnit reader rejects a TRX file."""
		with self.assertRaises(UnittestError):
			_ = JUnitDocument(XUNIT_FILE, analyzeAndConvert=True)

	def test_NotAnalyzed(self) -> None:
		document = TRX.Document(XUNIT_FILE)

		with self.assertRaises(UnittestError) as context:
			document.Convert()

		self.assertEqual(f"TRX file '{XUNIT_FILE}' needs to be read and analyzed by an XML parser.", str(context.exception))

	def test_Missing(self) -> None:
		path = OUTPUT / "Missing.trx"

		with self.assertRaises(UnittestError) as context:
			_ = TRX.Document(path, analyzeAndConvert=True)

		self.assertEqual(f"TRX file '{path}' does not exist.", str(context.exception))


class XUnit(Testcase):
	"""The TRX file of the xUnit.net example."""

	def test_TestRun(self) -> None:
		document = TRX.Document(XUNIT_FILE, analyzeAndConvert=True)

		self.assertEqual(UUID("0da8d99b-7a14-4e6a-bb1d-2e7625ca5720"), document.Id)
		self.assertEqual("@dffa20ef8728 2026-10-08 11:09:27", document.Name)
		self.assertEqual(datetime(2026, 10, 8, 11, 9, 26, 184828, tzinfo=timezone.utc), document.StartTime)
		self.assertEqual(datetime(2026, 10, 8, 11, 9, 27, 732372, tzinfo=timezone.utc), document.FinishTime)
		self.assertIs(TRX.TestOutcome.Failed, document.Outcome)
		self.assertEqual(
			{
				UUID("8c84fa94-04c1-424b-9868-57a2d4851a1d"): "Results Not in a List",
				UUID("19431567-8539-422a-85d7-44ee4e166bda"): "All Loaded Results"
			},
			document.TestLists
		)
		self.assertTrue(document.StandardOutput.startswith("[xUnit.net 00:00:00.00] xUnit.net VSTest Adapter v4.0.0"))
		self.assertTrue(
			document.StandardOutput.endswith("Test 'MyLibrary.Tests.CalculatorTests.Multiply' was skipped in the test run.\n")
		)
		self.assertGreater(document.ModelConversionDuration, timedelta())

	def test_Counters(self) -> None:
		"""The skipped test is counted in ``total`` only: ``executed`` excludes it, ``notExecuted`` doesn't count it."""
		document = TRX.Document(XUNIT_FILE, analyzeAndConvert=True)

		self.assertEqual(
			{"total": 11, "executed": 10, "passed": 7, "failed": 3, "error": 0, "notExecuted": 0},
			{name: document.Counters[name] for name in ("total", "executed", "passed", "failed", "error", "notExecuted")}
		)
		self.assertEqual(1, len([result for result in document.Results if result.Outcome is TRX.TestOutcome.NotExecuted]))

	def test_Definitions(self) -> None:
		"""A test definition names the class and method; each data row of a theory is a test of its own."""
		document = TRX.Document(XUNIT_FILE, analyzeAndConvert=True)
		unitTest = document.UnitTests[UUID("c227cb92-a240-849d-5ffd-de973891e007")]

		self.assertEqual(11, len(document.UnitTests))
		self.assertEqual("MyLibrary.Tests.CalculatorTests.Absolute(value: 3, expected: 3)", unitTest.Name)
		self.assertEqual("MyLibrary.Tests.CalculatorTests", unitTest.ClassName)
		self.assertEqual("Absolute", unitTest.MethodName)
		self.assertEqual("MyLibrary.Tests.dll", unitTest.CodeBase.name)
		self.assertEqual("executor://xunit/VsTestRunner3/netcore/", unitTest.AdapterTypeName)
		self.assertEqual(3, len([test for test in document.UnitTests.values() if test.MethodName == "Absolute"]))

	def test_Results(self) -> None:
		"""An exception fails a test like an assertion does; a skipped test isn't executed and keeps its reason."""
		document = TRX.Document(XUNIT_FILE, analyzeAndConvert=True)
		results = {result.TestName: result for result in document.Results}

		self.assertEqual(11, len(results))
		self.assertIs(TRX.TestOutcome.Failed, results["MyLibrary.Tests.CalculatorTests.DivideByZero"].Outcome)
		self.assertEqual(
			"System.DivideByZeroException : Attempted to divide by zero.",
			results["MyLibrary.Tests.CalculatorTests.DivideByZero"].Message
		)
		self.assertTrue(
			results["MyLibrary.Tests.CalculatorTests.DivideByZero"].Details.startswith("   at MyLibrary.Calculator.Divide(")
		)

		skipped = results["MyLibrary.Tests.CalculatorTests.Multiply"]
		self.assertIs(TRX.TestOutcome.NotExecuted, skipped.Outcome)
		self.assertEqual("Multiplication isn't implemented yet.", skipped.Message)
		self.assertIsNone(skipped.Details)

		passed = results["MyLibrary.Tests.CounterTests.Increment"]
		self.assertIs(TRX.TestOutcome.Passed, passed.Outcome)
		self.assertEqual("Counter value: 1", passed.StandardOutput)
		self.assertIsNone(passed.Message)
		self.assertEqual("dffa20ef8728", passed.ComputerName)
		self.assertEqual(timedelta(milliseconds=1), passed.Duration)
		self.assertEqual(datetime(2026, 10, 8, 11, 9, 27, 549278, tzinfo=timezone.utc), passed.StartTime)
		self.assertEqual(datetime(2026, 10, 8, 11, 9, 27, 550659, tzinfo=timezone.utc), passed.EndTime)
		self.assertEqual([], passed.InnerResults)

	def test_TestsuiteSummary(self) -> None:
		"""Counts and statuses as ``dotnet test`` states them: 11 tests, 7 passed, 3 failed, 1 skipped."""
		summary = TRX.Document(XUNIT_FILE, analyzeAndConvert=True).ToTestsuiteSummary()

		self.assertEqual("@dffa20ef8728 2026-10-08 11:09:27", summary.Name)
		self.assertEqual(TestsuiteStatus.Failed, summary.Status)
		self.assertEqual(timedelta(seconds=1, microseconds=547544), summary.TotalDuration)
		self.assertEqual(11, summary.Tests)
		self.assertEqual(7, summary.Passed)
		self.assertEqual(3, summary.Failed)
		self.assertEqual(1, summary.Skipped)
		self.assertEqual(0, summary.Errored)

		assembly = summary.Testsuites["MyLibrary.Tests.dll"]
		self.assertEqual("dffa20ef8728", assembly.Hostname)
		self.assertEqual(TestsuiteKind.Namespace, assembly.Testsuites["MyLibrary"].Kind)
		self.assertEqual(TestsuiteKind.Namespace, assembly.Testsuites["MyLibrary"].Testsuites["Tests"].Kind)
		self.assertEqual(
			{"CalculatorTests", "CounterTests"},
			set(assembly.Testsuites["MyLibrary"].Testsuites["Tests"].Testsuites)
		)
		self.assertEqual(
			{
				"CalculatorTests.Absolute(value: -3, expected: 3)": TestcaseStatus.Passed,
				"CalculatorTests.Absolute(value: -4, expected: 5)": TestcaseStatus.Failed,
				"CalculatorTests.Absolute(value: 3, expected: 3)":  TestcaseStatus.Passed,
				"CalculatorTests.Add":                              TestcaseStatus.Passed,
				"CalculatorTests.DivideByZero":                     TestcaseStatus.Failed,
				"CalculatorTests.IsEven":                           TestcaseStatus.Failed,
				"CalculatorTests.Multiply":                         TestcaseStatus.Skipped,
				"CalculatorTests.SumOfPositives":                   TestcaseStatus.Passed,
				"CounterTests.Decrement":                           TestcaseStatus.Passed,
				"CounterTests.Increment":                           TestcaseStatus.Passed,
				"CounterTests.IncrementAsync":                      TestcaseStatus.Passed,
			},
			statuses(summary)
		)

		classTestsuite = assembly.Testsuites["MyLibrary"].Testsuites["Tests"].Testsuites["CalculatorTests"]
		self.assertEqual(TestsuiteKind.Class, classTestsuite.Kind)
		multiply = classTestsuite.Testcases["Multiply"]
		self.assertEqual("Multiplication isn't implemented yet.", multiply.Message)
		self.assertEqual(timedelta(milliseconds=1), multiply.TestDuration)
		self.assertEqual(datetime(2026, 10, 8, 11, 9, 27, 557016, tzinfo=timezone.utc), multiply.StartTime)


class MSTest(Testcase):
	"""The TRX file of an MSTest test project."""

	def test_Results(self) -> None:
		"""MSTest names a test without its class; both rows of a folded data-driven test share one definition."""
		document = TRX.Document(MSTEST_FILE, analyzeAndConvert=True)
		results = {result.TestName: result for result in document.Results}

		self.assertEqual(10, len(document.Results))
		self.assertEqual(9, len(document.UnitTests))
		self.assertEqual(results["Folded (1,1)"].TestId, results["Folded (2,3)"].TestId)
		self.assertEqual("Folded", document.UnitTests[results["Folded (1,1)"].TestId].Name)
		self.assertEqual("Adding", results["Add"].StandardOutput)
		self.assertEqual("on stderr", results["Add"].StandardError)
		self.assertIsNone(results["Ignored"].Duration)
		self.assertEqual("Test 'Slow' timed out after 100ms", results["Slow"].Message)

	def test_TestsuiteSummary(self) -> None:
		"""Counts as ``dotnet test`` states them: 10 tests, 3 passed, 5 failed, 2 skipped."""
		document = TRX.Document(MSTEST_FILE, analyzeAndConvert=True)
		summary = document.ToTestsuiteSummary()

		self.assertEqual(
			{"total": 10, "executed": 8, "passed": 3, "failed": 5, "notExecuted": 0},
			{name: document.Counters[name] for name in ("total", "executed", "passed", "failed", "notExecuted")}
		)
		self.assertEqual((10, 3, 5, 2), (summary.Tests, summary.Passed, summary.Failed, summary.Skipped))
		self.assertEqual(
			{
				"CalculatorTests.Add":          TestcaseStatus.Passed,
				"CalculatorTests.Fails":        TestcaseStatus.Failed,
				"CalculatorTests.Ignored":      TestcaseStatus.Skipped,
				"CalculatorTests.Inconclusive": TestcaseStatus.Skipped,
				"CalculatorTests.Rows (1,1)":   TestcaseStatus.Passed,
				"CalculatorTests.Rows (2,3)":   TestcaseStatus.Failed,
				"CalculatorTests.Slow":         TestcaseStatus.Failed,
				"CalculatorTests.Throws":       TestcaseStatus.Failed,
				"FoldedTests.Folded (1,1)":     TestcaseStatus.Passed,
				"FoldedTests.Folded (2,3)":     TestcaseStatus.Failed,
			},
			statuses(summary)
		)


class NUnit(Testcase):
	"""The TRX file of an NUnit test project."""

	def test_TestsuiteSummary(self) -> None:
		"""
		An inconclusive test, an explicit test and a test raising a warning aren't executed, like an ignored test.

		``dotnet test`` states 7 tests (2 passed, 3 failed, 2 skipped): it doesn't count the inconclusive and the explicit
		test, the TRX file lists them.
		"""
		document = TRX.Document(NUNIT_FILE, analyzeAndConvert=True)
		summary = document.ToTestsuiteSummary()
		namespace = summary.Testsuites["NUnitSample.dll"].Testsuites["Sample"].Testsuites["Tests"]
		testcases = namespace.Testsuites["CalculatorTests"].Testcases

		self.assertEqual(
			{"total": 9, "executed": 5, "passed": 2, "failed": 3, "notExecuted": 0},
			{name: document.Counters[name] for name in ("total", "executed", "passed", "failed", "notExecuted")}
		)
		self.assertEqual((9, 2, 3, 4), (summary.Tests, summary.Passed, summary.Failed, summary.Skipped))
		self.assertEqual(
			{
				"CalculatorTests.Add":          TestcaseStatus.Passed,
				"CalculatorTests.Fails":        TestcaseStatus.Failed,
				"CalculatorTests.Ignored":      TestcaseStatus.Skipped,
				"CalculatorTests.Inconclusive": TestcaseStatus.Skipped,
				"CalculatorTests.OnRequest":    TestcaseStatus.Skipped,
				"CalculatorTests.Rows(1,1)":    TestcaseStatus.Passed,
				"CalculatorTests.Rows(2,3)":    TestcaseStatus.Failed,
				"CalculatorTests.Throws":       TestcaseStatus.Failed,
				"CalculatorTests.Warns":        TestcaseStatus.Skipped,
			},
			statuses(summary)
		)
		self.assertEqual("Careful.", testcases["Warns"].Message)
		self.assertEqual("Careful.", testcases["Warns"].StandardOutput)


class Conversion(Testcase):
	"""Conversion of a test run to the unified data model."""

	@classmethod
	def setUpClass(cls) -> None:
		OUTPUT.mkdir(parents=True, exist_ok=True)

	def _testRun(self, *results: TRX.UnitTestResult) -> TRX.TestRun:
		"""
		Create a test run with one test definition.

		:param results: The test run's results.
		:returns:       The test run.
		"""
		unitTest = TRX.UnitTest(
			UUID(int=1), "Rows", "Sample.Tests.CalculatorTests", "Rows", Path("/bin/Sample.Tests.dll"), "executor://mstest"
		)
		return TRX.TestRun("run", unitTests=(unitTest, ), results=results)

	def _result(
		self,
		number: int,
		name: str,
		outcome: TRX.TestOutcome,
		testId: int = 1,
		innerResults: Nullable[Iterable[TRX.UnitTestResult]] = None
	) -> TRX.UnitTestResult:
		"""
		Create a test result.

		:param number:       Number of the execution.
		:param name:         Name of the test.
		:param outcome:      Outcome of the test.
		:param testId:       Optional, number of the test definition.
		:param innerResults: Optional, inner results.
		:returns:            The test result.
		"""
		return TRX.UnitTestResult(
			UUID(int=100 + number), UUID(int=testId), name, "host", outcome, UUID(int=2), innerResults=innerResults
		)

	def test_InnerResults(self) -> None:
		"""The rows of a data-driven test become test cases, the container doesn't."""
		container = self._result(0, "Rows", TRX.TestOutcome.Failed, innerResults=(
			self._result(1, "Rows (1,1)", TRX.TestOutcome.Passed),
			self._result(2, "Rows (2,3)", TRX.TestOutcome.Failed)
		))
		summary = self._testRun(container).ToTestsuiteSummary()

		self.assertEqual(
			{"CalculatorTests.Rows (1,1)": TestcaseStatus.Passed, "CalculatorTests.Rows (2,3)": TestcaseStatus.Failed},
			statuses(summary)
		)

	def test_Outcomes(self) -> None:
		"""Each outcome maps to a status a test suite counts."""
		testRun = self._testRun(*(
			self._result(number, outcome.name, outcome) for number, outcome in enumerate(TRX.TestOutcome)
		))
		summary = testRun.ToTestsuiteSummary()

		self.assertEqual(len(TRX.TestOutcome), summary.Tests)
		self.assertEqual(
			{f"CalculatorTests.{outcome.name}": TRX.STATUS_MAP[outcome] for outcome in TRX.TestOutcome},
			statuses(summary)
		)

	def test_UnknownTestId(self) -> None:
		with self.assertRaises(UnittestError) as context:
			_ = self._testRun(self._result(1, "Other", TRX.TestOutcome.Passed, testId=3)).ToTestsuiteSummary()

		self.assertEqual("Test result 'Other' refers to no test definition.", str(context.exception))
		self.assertEqual([f"Got test ID '{UUID(int=3)}'."], context.exception.__notes__)

	def test_DuplicateName(self) -> None:
		with self.assertRaises(DuplicateTestcaseError):
			_ = self._testRun(
				self._result(1, "Rows (1,1)", TRX.TestOutcome.Passed),
				self._result(2, "Rows (1,1)", TRX.TestOutcome.Passed)
			).ToTestsuiteSummary()

	def test_WindowsPaths(self) -> None:
		"""A TRX file written on Windows names the assembly with backslashes; a duration can exceed a day."""
		path = OUTPUT / "Windows.trx"
		codeBase = "/home/runner/work/pyEDAA.Reports/pyEDAA.Reports/examples/CSharp/xUnit/test/MyLibrary.Tests/bin"
		path.write_text(
			XUNIT_FILE.read_text(encoding="utf-8-sig")
				.replace(f'codeBase="{codeBase}/Debug/net10.0/', 'codeBase="D:\\a\\pyEDAA.Reports\\bin\\Debug\\net10.0\\')
				.replace('duration="00:00:00.0180000"', 'duration="1.02:03:04.5000000"'),
			encoding="utf-8"
		)
		document = TRX.Document(path, analyzeAndConvert=True)
		summary = document.ToTestsuiteSummary()

		self.assertEqual(["MyLibrary.Tests.dll"], list(summary.Testsuites))
		self.assertEqual(
			timedelta(days=1, hours=2, minutes=3, seconds=4, milliseconds=500),
			{result.TestName: result for result in document.Results}["MyLibrary.Tests.CalculatorTests.Add"].Duration
		)


class DataModel(Testcase):
	"""Parameter checks of the TRX data model."""

	def test_UnitTest(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = TRX.UnitTest(UUID(int=1), "", "Class", "Method", Path("a.dll"), "executor://a")
		self.assertEqual("Parameter 'name' is empty.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = TRX.UnitTest("1", "Name", "Class", "Method", Path("a.dll"), "executor://a")
		self.assertEqual("Parameter 'id' is not of type 'UUID'.", str(context.exception))
		self.assertEqual(["Got type 'str'."], context.exception.__notes__)

		with self.assertRaises(ValueError) as context:
			_ = TRX.UnitTest(UUID(int=1), "Name", "Class", "Method", None, "executor://a")
		self.assertEqual("Parameter 'codeBase' is None.", str(context.exception))

	def test_UnitTestResult(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = TRX.UnitTestResult(UUID(int=1), None, "Name", "host", TRX.TestOutcome.Passed, UUID(int=2))
		self.assertEqual("Parameter 'testId' is None.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = TRX.UnitTestResult(UUID(int=1), UUID(int=1), "Name", "host", "Passed", UUID(int=2))
		self.assertEqual("Parameter 'outcome' is not of type 'TestOutcome'.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = TRX.UnitTestResult(
				UUID(int=1), UUID(int=1), "Name", "host", TRX.TestOutcome.Passed, UUID(int=2), innerResults=(1, )
			)
		self.assertEqual("Element of parameter 'innerResults' is not of type 'UnitTestResult'.", str(context.exception))

	def test_TestRun(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = TRX.TestRun(None)
		self.assertEqual("Parameter 'name' is None.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = TRX.TestRun("run", counters={"total": "11"})
		self.assertEqual("Value of parameter 'counters' is not of type 'int'.", str(context.exception))
		self.assertEqual(["Got type 'str'."], context.exception.__notes__)

		with self.assertRaises(TypeError) as context:
			_ = TRX.TestRun("run", outcome="Failed")
		self.assertEqual("Parameter 'outcome' is not of type 'TestOutcome'.", str(context.exception))
