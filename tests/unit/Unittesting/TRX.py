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
Unit tests documenting Visual Studio's test results format (TRX), as ``dotnet test --logger trx`` writes it.

No reader exists yet. The report in :file:`tests/data/JUnit/pyEDAA.Reports/CSharp-xUnit` is written by the example
:file:`examples/CSharp/xUnit`.
"""
from pathlib                          import Path

from lxml.etree                       import parse

from pyEDAA.Reports.Unittesting       import UnittestError
from pyEDAA.Reports.Unittesting.JUnit import Document
from pyTooling.Testing                import Testcase


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


#: The TRX file of the example.
TRX_FILE = Path(__file__).parent.parent.parent / "data/JUnit/pyEDAA.Reports/CSharp-xUnit/MyLibrary.Tests.trx"
NAMESPACES = {"trx": "http://microsoft.com/schemas/VisualStudio/TeamTest/2010"}  #: XML namespace of TRX.


class StatusQuo(Testcase):
	"""A TRX file lists results, test definitions and a summary of a test run; no reader exists yet."""

	def test_Results(self) -> None:
		"""An exception fails a test like an assertion does; a skipped test isn't executed."""
		root = parse(TRX_FILE).getroot()

		self.assertEqual(f"{{{NAMESPACES['trx']}}}TestRun", root.tag)
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

		def message(testName: str) -> str:
			"""Nested function returning the message of a test's result."""
			return root.findtext(
				f"trx:Results/trx:UnitTestResult[@testName='{testName}']/trx:Output/trx:ErrorInfo/trx:Message",
				namespaces=NAMESPACES
			)

		self.assertEqual(
			"System.DivideByZeroException : Attempted to divide by zero.",
			message("MyLibrary.Tests.CalculatorTests.DivideByZero")
		)
		self.assertEqual("Multiplication isn't implemented yet.", message("MyLibrary.Tests.CalculatorTests.Multiply"))

	def test_Definitions(self) -> None:
		"""A test definition names the class and method; each data row of a theory is a test of its own."""
		root = parse(TRX_FILE).getroot()
		methods = root.findall("trx:TestDefinitions/trx:UnitTest/trx:TestMethod", NAMESPACES)

		self.assertEqual(3, len([method for method in methods if method.get("name") == "Absolute"]))
		self.assertEqual(
			{"MyLibrary.Tests.CalculatorTests", "MyLibrary.Tests.CounterTests"},
			{method.get("className") for method in methods}
		)

	def test_Counters(self) -> None:
		"""The skipped test is counted in ``total`` only: ``executed`` excludes it, ``notExecuted`` doesn't count it."""
		counters = parse(TRX_FILE).getroot().find("trx:ResultSummary/trx:Counters", NAMESPACES)

		self.assertEqual(
			{"total": "11", "executed": "10", "passed": "7", "failed": "3", "error": "0", "notExecuted": "0"},
			{name: counters.get(name) for name in ("total", "executed", "passed", "failed", "error", "notExecuted")}
		)

	def test_JUnit(self) -> None:
		"""The JUnit reader rejects a TRX file."""
		with self.assertRaises(UnittestError):
			_ = Document(TRX_FILE, analyzeAndConvert=True)
