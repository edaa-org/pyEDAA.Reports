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

The reader reads the test run and its summary; the results and test definitions are inspected as XML.

The reports in :file:`tests/data/TRX` are written by VSTest's TRX logger: :file:`CSharp-xUnit` by the example
:file:`examples/CSharp/xUnit`, :file:`CSharp-MSTest` and :file:`CSharp-NUnit` by small MSTest and NUnit test projects.
"""
from datetime                         import datetime, timedelta, timezone
from pathlib                          import Path
from uuid                             import UUID

from lxml.etree                       import parse

from pyEDAA.Reports.Unittesting       import UnittestError
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
NAMESPACES = {"trx": TRX.TRX_NAMESPACE}                      #: XML namespace of TRX.


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

class StatusQuo(Testcase):
	"""The reader doesn't read results and test definitions yet; the XML shows what a TRX file lists."""

	def test_Results(self) -> None:
		"""An exception fails a test like an assertion does; a skipped test isn't executed."""
		root = parse(XUNIT_FILE).getroot()

		self.assertEqual(
			{
				"MyLibrary.Tests.CalculatorTests.Absolute(value: -3, expected: 3)": "Passed",
				"MyLibrary.Tests.CalculatorTests.Absolute(value: -4, expected: 5)": "Failed",
				"MyLibrary.Tests.CalculatorTests.Absolute(value: 3, expected: 3)":  "Passed",
				"MyLibrary.Tests.CalculatorTests.Add":                              "Passed",
				"MyLibrary.Tests.CalculatorTests.DivideByZero":                     "Failed",
				"MyLibrary.Tests.CalculatorTests.IsEven":                           "Failed",
				"MyLibrary.Tests.CalculatorTests.Multiply":                         "NotExecuted",
				"MyLibrary.Tests.CalculatorTests.SumOfPositives":                   "Passed",
				"MyLibrary.Tests.CounterTests.Decrement":                           "Passed",
				"MyLibrary.Tests.CounterTests.Increment":                           "Passed",
				"MyLibrary.Tests.CounterTests.IncrementAsync":                      "Passed",
			},
			{
				result.get("testName"): result.get("outcome")
				for result in root.iterfind("trx:Results/trx:UnitTestResult", NAMESPACES)
			}
		)

	def test_Definitions(self) -> None:
		"""A test definition names the class and method; each data row of a theory is a test of its own."""
		root = parse(XUNIT_FILE).getroot()
		methods = root.findall("trx:TestDefinitions/trx:UnitTest/trx:TestMethod", NAMESPACES)

		self.assertEqual(3, len([method for method in methods if method.get("name") == "Absolute"]))
		self.assertEqual(
			{"MyLibrary.Tests.CalculatorTests", "MyLibrary.Tests.CounterTests"},
			{method.get("className") for method in methods}
		)


class DataModel(Testcase):
	"""Parameter checks of the TRX data model."""

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
