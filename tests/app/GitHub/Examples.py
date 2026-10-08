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
# Copyright 2021-2026 Electronic Design Automation Abstraction (EDA²)                                                  #
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
"""Testcase for application testing report files generated on GitHub."""
from pathlib          import Path
from unittest         import TestCase

from pyTooling.Common import zipdicts

from pyEDAA.Reports.Unittesting                       import TestcaseStatus, UnittestError
from pyEDAA.Reports.Unittesting.JUnit                 import Document as AnyJUnitDocument
# FIXME: change to generic JUnit
from pyEDAA.Reports.Unittesting.JUnit.AntJUnit4       import Document as JUnit4Document
from pyEDAA.Reports.Unittesting.JUnit.CTestJUnit      import Document as CTestDocument
from pyEDAA.Reports.Unittesting.JUnit.GoogleTestJUnit import Document as GTestDocument
from pyEDAA.Reports.Unittesting.JUnit.PyTestJUnit     import Document as PyTestDocument
from pyTooling.Testing                                import Testcase


if __name__ == "__main__": # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unitest <testcase module>'")
	exit(1)


class CppGoogleTest(TestCase):
	def test_gtest(self) -> None:
		print()

		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Cpp-GoogleTest/gtest.xml")
		doc = GTestDocument(junitExampleFile, analyzeAndConvert=True)

		self.assertEqual(1, doc.TestsuiteCount)
		self.assertEqual(3, doc.TestcaseCount)

		print(f"JUnit file:")
		print(f"  Testsuites: {doc.TestsuiteCount}")
		print(f"  Testcases:  {doc.TestcaseCount}")

		print()
		print(f"Statistics:")
		print(f"  Times: parsing by lxml: {doc.AnalysisDuration.total_seconds():.3f}s   convert: {doc.ModelConversionDuration.total_seconds():.3f}s")

	def test_ReadWrite(self) -> None:
		print()

		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Cpp-GoogleTest/gtest.xml")
		doc = GTestDocument(junitExampleFile, analyzeAndConvert=True)

		junitOutputFile = Path("tests/output/JUnit/pyEDAA.Reports/Cpp-GoogleTest/gtest.xml")
		junitOutputFile.parent.mkdir(parents=True, exist_ok=True)
		doc.Write(junitOutputFile, regenerate=True, overwrite=True)

		sameDoc = GTestDocument(junitOutputFile, analyzeAndConvert=True)

		self.assertEqual(doc.TestsuiteCount, sameDoc.TestsuiteCount)
		self.assertEqual(doc.TestcaseCount, sameDoc.TestcaseCount)
		self.assertEqual(doc.Errored, sameDoc.Errored)
		self.assertEqual(doc.Skipped, sameDoc.Skipped)
		self.assertEqual(doc.Failed, sameDoc.Failed)
		self.assertEqual(doc.Passed, sameDoc.Passed)
		self.assertEqual(doc.Tests, sameDoc.Tests)

		for tsName, ts, sameTS in zipdicts(doc._testsuites, sameDoc._testsuites):
			self.assertEqual(ts.Name, sameTS.Name)
			self.assertEqual(ts.Duration, sameTS.Duration)
			self.assertEqual(ts.TestcaseCount, sameTS.TestcaseCount)
			self.assertEqual(ts.AssertionCount, sameTS.AssertionCount)
			self.assertEqual(ts.Errored, sameTS.Errored)
			self.assertEqual(ts.Skipped, sameTS.Skipped)
			self.assertEqual(ts.Failed, sameTS.Failed)
			self.assertEqual(ts.Passed, sameTS.Passed)
			self.assertEqual(ts.Tests, sameTS.Tests)

			for tclsName, tcls, sameTCls in zipdicts(ts._testclasses, sameTS._testclasses):
				self.assertEqual(tcls.Name, sameTCls.Name)
				self.assertEqual(tcls.Classname, sameTCls.Classname)
				self.assertEqual(tcls.TestcaseCount, sameTCls.TestcaseCount)
				self.assertEqual(tcls.AssertionCount, sameTCls.AssertionCount)

				for tcName, tc, sameTC in zipdicts(tcls._testcases, sameTCls._testcases):
					self.assertEqual(tc.Name, sameTC.Name)
					self.assertEqual(tc.Classname, sameTC.Classname)
					self.assertEqual(tc.Status, sameTC.Status)
					self.assertEqual(tc.Duration, sameTC.Duration)
					self.assertEqual(tc.AssertionCount, sameTC.AssertionCount)


class CppGoogleTestCTest(TestCase):
	def test_ctest(self) -> None:
		print()

		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Cpp-GoogleTest/ctest.xml")
		doc = CTestDocument(junitExampleFile, analyzeAndConvert=True)

		# self.assertEqual(1, doc.TestsuiteCount)
		# self.assertEqual(3, doc.TestcaseCount)

		print(f"JUnit file:")
		print(f"  Testsuites: {doc.TestsuiteCount}")
		print(f"  Testcases:  {doc.TestcaseCount}")

		print()
		print(f"Statistics:")
		print(f"  Times: parsing by lxml: {doc.AnalysisDuration.total_seconds():.3f}s   convert: {doc.ModelConversionDuration.total_seconds():.3f}s")

	def test_ReadWrite(self) -> None:
		print()

		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Cpp-GoogleTest/ctest.xml")
		doc = CTestDocument(junitExampleFile, analyzeAndConvert=True)

		junitOutputFile = Path("tests/output/JUnit/pyEDAA.Reports/Cpp-GoogleTest/ctest.xml")
		junitOutputFile.parent.mkdir(parents=True, exist_ok=True)
		doc.Write(junitOutputFile, regenerate=True, overwrite=True)

		sameDoc = CTestDocument(junitOutputFile, analyzeAndConvert=True)

		self.assertEqual(doc.TestsuiteCount, sameDoc.TestsuiteCount)
		self.assertEqual(doc.TestcaseCount, sameDoc.TestcaseCount)
		self.assertEqual(doc.Errored, sameDoc.Errored)
		self.assertEqual(doc.Skipped, sameDoc.Skipped)
		self.assertEqual(doc.Failed, sameDoc.Failed)
		self.assertEqual(doc.Passed, sameDoc.Passed)
		self.assertEqual(doc.Tests, sameDoc.Tests)

		for tsName, ts, sameTS in zipdicts(doc._testsuites, sameDoc._testsuites):
			self.assertEqual(ts.Name, sameTS.Name)
			self.assertEqual(ts.Duration, sameTS.Duration)
			self.assertEqual(ts.TestcaseCount, sameTS.TestcaseCount)
			self.assertEqual(ts.AssertionCount, sameTS.AssertionCount)
			self.assertEqual(ts.Errored, sameTS.Errored)
			self.assertEqual(ts.Skipped, sameTS.Skipped)
			self.assertEqual(ts.Failed, sameTS.Failed)
			self.assertEqual(ts.Passed, sameTS.Passed)
			self.assertEqual(ts.Tests, sameTS.Tests)

			for tclsName, tcls, sameTCls in zipdicts(ts._testclasses, sameTS._testclasses):
				self.assertEqual(tcls.Name, sameTCls.Name)
				self.assertEqual(tcls.Classname, sameTCls.Classname)
				self.assertEqual(tcls.TestcaseCount, sameTCls.TestcaseCount)
				self.assertEqual(tcls.AssertionCount, sameTCls.AssertionCount)

				for tcName, tc, sameTC in zipdicts(tcls._testcases, sameTCls._testcases):
					self.assertEqual(tc.Name, sameTC.Name)
					self.assertEqual(tc.Classname, sameTC.Classname)
					self.assertEqual(tc.Status, sameTC.Status)
					self.assertEqual(tc.Duration, sameTC.Duration)
					self.assertEqual(tc.AssertionCount, sameTC.AssertionCount)


class CppCatch2(TestCase):
	def test_JUnit(self) -> None:
		"""Known gap: no dialect reads Catch2's JUnit report yet."""
		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Cpp-Catch2/catch2-junit.xml")

		for documentClass in (AnyJUnitDocument, JUnit4Document, CTestDocument, GTestDocument, PyTestDocument):
			with self.subTest(dialect=documentClass.__module__):
				with self.assertRaises(UnittestError):
					documentClass(junitExampleFile, analyzeAndConvert=True)


class JavaAntJUnit4(TestCase):
	def test_JUnit4(self) -> None:
		print()

		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Java-Ant-JUnit4/TEST-my.AllTests.xml")
		doc = JUnit4Document(junitExampleFile, analyzeAndConvert=True)

		self.assertEqual(1, doc.TestsuiteCount)
		self.assertEqual(2, doc.TestcaseCount)

		print(f"JUnit file:")
		print(f"  Testsuites: {doc.TestsuiteCount}")
		print(f"  Testcases:  {doc.TestcaseCount}")

		print()
		print(f"Statistics:")
		print(f"  Times: parsing by lxml: {doc.AnalysisDuration.total_seconds():.3f}s   convert: {doc.ModelConversionDuration.total_seconds():.3f}s")

	def test_ReadWrite(self) -> None:
		print()

		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Java-Ant-JUnit4/TEST-my.AllTests.xml")
		doc = JUnit4Document(junitExampleFile, analyzeAndConvert=True)

		junitOutputFile = Path("tests/output/JUnit/pyEDAA.Reports/Java-Ant-JUnit4/TEST-my.AllTests.xml")
		junitOutputFile.parent.mkdir(parents=True, exist_ok=True)
		doc.Write(junitOutputFile, regenerate=True, overwrite=True)

		sameDoc = JUnit4Document(junitOutputFile, analyzeAndConvert=True)

		self.assertEqual(doc.TestsuiteCount, sameDoc.TestsuiteCount)
		self.assertEqual(doc.TestcaseCount, sameDoc.TestcaseCount)
		self.assertEqual(doc.Errored, sameDoc.Errored)
		self.assertEqual(doc.Skipped, sameDoc.Skipped)
		self.assertEqual(doc.Failed, sameDoc.Failed)
		self.assertEqual(doc.Passed, sameDoc.Passed)
		self.assertEqual(doc.Tests, sameDoc.Tests)

		for tsName, ts, sameTS in zipdicts(doc._testsuites, sameDoc._testsuites):
			self.assertEqual(ts.Name, sameTS.Name)
			self.assertEqual(ts.Duration, sameTS.Duration)
			self.assertEqual(ts.TestcaseCount, sameTS.TestcaseCount)
			self.assertEqual(ts.AssertionCount, sameTS.AssertionCount)
			self.assertEqual(ts.Errored, sameTS.Errored)
			self.assertEqual(ts.Skipped, sameTS.Skipped)
			self.assertEqual(ts.Failed, sameTS.Failed)
			self.assertEqual(ts.Passed, sameTS.Passed)
			self.assertEqual(ts.Tests, sameTS.Tests)

			for tclsName, tcls, sameTCls in zipdicts(ts._testclasses, sameTS._testclasses):
				self.assertEqual(tcls.Name, sameTCls.Name)
				self.assertEqual(tcls.Classname, sameTCls.Classname)
				self.assertEqual(tcls.TestcaseCount, sameTCls.TestcaseCount)
				self.assertEqual(tcls.AssertionCount, sameTCls.AssertionCount)

				for tcName, tc, sameTC in zipdicts(tcls._testcases, sameTCls._testcases):
					self.assertEqual(tc.Name, sameTC.Name)
					self.assertEqual(tc.Classname, sameTC.Classname)
					self.assertEqual(tc.Status, sameTC.Status)
					self.assertEqual(tc.Duration, sameTC.Duration)
					self.assertEqual(tc.AssertionCount, sameTC.AssertionCount)


class JavaGradleJUnit4(Testcase):
	def test_JUnit4(self) -> None:
		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Java-Gradle-JUnit4/TEST-my.pack.MyClassTest.xml")
		doc = JUnit4Document(junitExampleFile, analyzeAndConvert=True)

		self.assertEqual(1, doc.TestsuiteCount)
		self.assertEqual(6, doc.TestcaseCount)
		self.assertEqual(6, doc.Tests)
		self.assertEqual(2, doc.Passed)
		self.assertEqual(2, doc.Failed)
		self.assertEqual(0, doc.Errored)
		self.assertEqual(2, doc.Skipped)

	def test_Status(self) -> None:
		"""Gradle writes an exception as ``<failure>``, an ignored test and a failed assumption as ``<skipped>``."""
		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Java-Gradle-JUnit4/TEST-my.pack.MyClassTest.xml")
		doc = JUnit4Document(junitExampleFile, analyzeAndConvert=True)

		testclass = doc._testsuites["my.pack.MyClassTest"]._testclasses["my.pack.MyClassTest"]
		self.assertEqual(
			{
				"testAbsolute":     TestcaseStatus.Passed,
				"testAssumption":   TestcaseStatus.Skipped,
				"testDivideByZero": TestcaseStatus.Failed,
				"testIgnored":      TestcaseStatus.Skipped,
				"testReturnFalse":  TestcaseStatus.Passed,
				"testReturnTrue":   TestcaseStatus.Failed,
			},
			{name: testcase.Status for name, testcase in testclass._testcases.items()}
		)

	def test_ReadWrite(self) -> None:
		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Java-Gradle-JUnit4/TEST-my.pack.MyClassTest.xml")
		doc = JUnit4Document(junitExampleFile, analyzeAndConvert=True)

		junitOutputFile = Path("tests/output/JUnit/pyEDAA.Reports/Java-Gradle-JUnit4/TEST-my.pack.MyClassTest.xml")
		junitOutputFile.parent.mkdir(parents=True, exist_ok=True)
		doc.Write(junitOutputFile, regenerate=True, overwrite=True)

		sameDoc = JUnit4Document(junitOutputFile, analyzeAndConvert=True)

		self.assertEqual(doc.TestsuiteCount, sameDoc.TestsuiteCount)
		self.assertEqual(doc.TestcaseCount, sameDoc.TestcaseCount)
		self.assertEqual(doc.Errored, sameDoc.Errored)
		self.assertEqual(doc.Skipped, sameDoc.Skipped)
		self.assertEqual(doc.Failed, sameDoc.Failed)
		self.assertEqual(doc.Passed, sameDoc.Passed)
		self.assertEqual(doc.Tests, sameDoc.Tests)

		for tsName, ts, sameTS in zipdicts(doc._testsuites, sameDoc._testsuites):
			self.assertEqual(ts.Name, sameTS.Name)
			self.assertEqual(ts.StartTime, sameTS.StartTime)
			self.assertEqual(ts.Duration, sameTS.Duration)
			self.assertEqual(ts.TestcaseCount, sameTS.TestcaseCount)
			self.assertEqual(ts.Errored, sameTS.Errored)
			self.assertEqual(ts.Skipped, sameTS.Skipped)
			self.assertEqual(ts.Failed, sameTS.Failed)
			self.assertEqual(ts.Passed, sameTS.Passed)
			self.assertEqual(ts.Tests, sameTS.Tests)

			for tclsName, tcls, sameTCls in zipdicts(ts._testclasses, sameTS._testclasses):
				self.assertEqual(tcls.Name, sameTCls.Name)
				self.assertEqual(tcls.Classname, sameTCls.Classname)
				self.assertEqual(tcls.TestcaseCount, sameTCls.TestcaseCount)

				for tcName, tc, sameTC in zipdicts(tcls._testcases, sameTCls._testcases):
					self.assertEqual(tc.Name, sameTC.Name)
					self.assertEqual(tc.Classname, sameTC.Classname)
					self.assertEqual(tc.Status, sameTC.Status)
					self.assertEqual(tc.Duration, sameTC.Duration)


class JavaGradleJUnit5(Testcase):
	def test_JUnit5(self) -> None:
		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Java-Gradle-JUnit5/TEST-my.pack.MyClassTest.xml")
		doc = JUnit4Document(junitExampleFile, analyzeAndConvert=True)

		self.assertEqual(1, doc.TestsuiteCount)
		self.assertEqual(8, doc.TestcaseCount)
		self.assertEqual(8, doc.Tests)
		self.assertEqual(3, doc.Passed)
		self.assertEqual(3, doc.Failed)
		self.assertEqual(0, doc.Errored)
		self.assertEqual(2, doc.Skipped)

	def test_Names(self) -> None:
		"""Test suite and test cases are named by their display names; ``classname`` is the class' name."""
		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Java-Gradle-JUnit5/TEST-my.pack.MyClassTest.xml")
		doc = JUnit4Document(junitExampleFile, analyzeAndConvert=True)

		self.assertEqual(["Tests of MyClass"], list(doc._testsuites))
		testsuite = doc._testsuites["Tests of MyClass"]
		self.assertEqual(["my.pack.MyClassTest"], list(testsuite._testclasses))
		self.assertEqual(
			{
				"[1] 5, 5":                    TestcaseStatus.Passed,
				"[2] -5, 5":                   TestcaseStatus.Passed,
				"[3] 0, 1":                    TestcaseStatus.Failed,
				"testAssumption()":            TestcaseStatus.Skipped,
				"testDivideByZero()":          TestcaseStatus.Failed,
				"testReturnTrue()":            TestcaseStatus.Failed,
				"testDisabled()":              TestcaseStatus.Skipped,
				"returnFalse() returns false": TestcaseStatus.Passed,
			},
			{name: testcase.Status for name, testcase in testsuite._testclasses["my.pack.MyClassTest"]._testcases.items()}
		)

	def test_NestedClass(self) -> None:
		"""A nested test class is a test suite and a file of its own."""
		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Java-Gradle-JUnit5/TEST-my.pack.MyClassTest$Divide.xml")
		doc = JUnit4Document(junitExampleFile, analyzeAndConvert=True)

		self.assertEqual(["my.pack.MyClassTest$Divide"], list(doc._testsuites))
		self.assertEqual(1, doc.Passed)

	def test_ReadWrite(self) -> None:
		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Java-Gradle-JUnit5/TEST-my.pack.MyClassTest.xml")
		doc = JUnit4Document(junitExampleFile, analyzeAndConvert=True)

		junitOutputFile = Path("tests/output/JUnit/pyEDAA.Reports/Java-Gradle-JUnit5/TEST-my.pack.MyClassTest.xml")
		junitOutputFile.parent.mkdir(parents=True, exist_ok=True)
		doc.Write(junitOutputFile, regenerate=True, overwrite=True)

		sameDoc = JUnit4Document(junitOutputFile, analyzeAndConvert=True)

		self.assertEqual(doc.TestsuiteCount, sameDoc.TestsuiteCount)
		self.assertEqual(doc.TestcaseCount, sameDoc.TestcaseCount)
		self.assertEqual(doc.Errored, sameDoc.Errored)
		self.assertEqual(doc.Skipped, sameDoc.Skipped)
		self.assertEqual(doc.Failed, sameDoc.Failed)
		self.assertEqual(doc.Passed, sameDoc.Passed)
		self.assertEqual(doc.Tests, sameDoc.Tests)

		for tsName, ts, sameTS in zipdicts(doc._testsuites, sameDoc._testsuites):
			self.assertEqual(ts.Name, sameTS.Name)
			self.assertEqual(ts.StartTime, sameTS.StartTime)
			self.assertEqual(ts.Duration, sameTS.Duration)
			self.assertEqual(ts.TestcaseCount, sameTS.TestcaseCount)
			self.assertEqual(ts.Errored, sameTS.Errored)
			self.assertEqual(ts.Skipped, sameTS.Skipped)
			self.assertEqual(ts.Failed, sameTS.Failed)
			self.assertEqual(ts.Passed, sameTS.Passed)
			self.assertEqual(ts.Tests, sameTS.Tests)

			for tclsName, tcls, sameTCls in zipdicts(ts._testclasses, sameTS._testclasses):
				self.assertEqual(tcls.Name, sameTCls.Name)
				self.assertEqual(tcls.Classname, sameTCls.Classname)
				self.assertEqual(tcls.TestcaseCount, sameTCls.TestcaseCount)

				for tcName, tc, sameTC in zipdicts(tcls._testcases, sameTCls._testcases):
					self.assertEqual(tc.Name, sameTC.Name)
					self.assertEqual(tc.Classname, sameTC.Classname)
					self.assertEqual(tc.Status, sameTC.Status)
					self.assertEqual(tc.Duration, sameTC.Duration)


class JavaGradleJUnit6(Testcase):
	def test_JUnit6(self) -> None:
		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Java-Gradle-JUnit6/TEST-my.pack.MyClassTest.xml")
		doc = JUnit4Document(junitExampleFile, analyzeAndConvert=True)

		self.assertEqual(1, doc.TestsuiteCount)
		self.assertEqual(8, doc.TestcaseCount)
		self.assertEqual(8, doc.Tests)
		self.assertEqual(3, doc.Passed)
		self.assertEqual(3, doc.Failed)
		self.assertEqual(0, doc.Errored)
		self.assertEqual(2, doc.Skipped)

	def test_Names(self) -> None:
		"""Test suite and test cases are named by their display names; ``classname`` is the class' name."""
		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Java-Gradle-JUnit6/TEST-my.pack.MyClassTest.xml")
		doc = JUnit4Document(junitExampleFile, analyzeAndConvert=True)

		self.assertEqual(["Tests of MyClass"], list(doc._testsuites))
		testsuite = doc._testsuites["Tests of MyClass"]
		self.assertEqual(["my.pack.MyClassTest"], list(testsuite._testclasses))
		self.assertEqual(
			{
				'[1] "5", "5"':                TestcaseStatus.Passed,
				'[2] "-5", "5"':               TestcaseStatus.Passed,
				'[3] "0", "1"':                TestcaseStatus.Failed,
				"testAssumption()":            TestcaseStatus.Skipped,
				"testDivideByZero()":          TestcaseStatus.Failed,
				"testReturnTrue()":            TestcaseStatus.Failed,
				"testDisabled()":              TestcaseStatus.Skipped,
				"returnFalse() returns false": TestcaseStatus.Passed,
			},
			{name: testcase.Status for name, testcase in testsuite._testclasses["my.pack.MyClassTest"]._testcases.items()}
		)

	def test_NestedClass(self) -> None:
		"""A nested test class is a test suite and a file of its own."""
		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Java-Gradle-JUnit6/TEST-my.pack.MyClassTest$Divide.xml")
		doc = JUnit4Document(junitExampleFile, analyzeAndConvert=True)

		self.assertEqual(["my.pack.MyClassTest$Divide"], list(doc._testsuites))
		self.assertEqual(1, doc.Passed)

	def test_ReadWrite(self) -> None:
		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Java-Gradle-JUnit6/TEST-my.pack.MyClassTest.xml")
		doc = JUnit4Document(junitExampleFile, analyzeAndConvert=True)

		junitOutputFile = Path("tests/output/JUnit/pyEDAA.Reports/Java-Gradle-JUnit6/TEST-my.pack.MyClassTest.xml")
		junitOutputFile.parent.mkdir(parents=True, exist_ok=True)
		doc.Write(junitOutputFile, regenerate=True, overwrite=True)

		sameDoc = JUnit4Document(junitOutputFile, analyzeAndConvert=True)

		self.assertEqual(doc.TestsuiteCount, sameDoc.TestsuiteCount)
		self.assertEqual(doc.TestcaseCount, sameDoc.TestcaseCount)
		self.assertEqual(doc.Errored, sameDoc.Errored)
		self.assertEqual(doc.Skipped, sameDoc.Skipped)
		self.assertEqual(doc.Failed, sameDoc.Failed)
		self.assertEqual(doc.Passed, sameDoc.Passed)
		self.assertEqual(doc.Tests, sameDoc.Tests)

		for tsName, ts, sameTS in zipdicts(doc._testsuites, sameDoc._testsuites):
			self.assertEqual(ts.Name, sameTS.Name)
			self.assertEqual(ts.StartTime, sameTS.StartTime)
			self.assertEqual(ts.Duration, sameTS.Duration)
			self.assertEqual(ts.TestcaseCount, sameTS.TestcaseCount)
			self.assertEqual(ts.Errored, sameTS.Errored)
			self.assertEqual(ts.Skipped, sameTS.Skipped)
			self.assertEqual(ts.Failed, sameTS.Failed)
			self.assertEqual(ts.Passed, sameTS.Passed)
			self.assertEqual(ts.Tests, sameTS.Tests)

			for tclsName, tcls, sameTCls in zipdicts(ts._testclasses, sameTS._testclasses):
				self.assertEqual(tcls.Name, sameTCls.Name)
				self.assertEqual(tcls.Classname, sameTCls.Classname)
				self.assertEqual(tcls.TestcaseCount, sameTCls.TestcaseCount)

				for tcName, tc, sameTC in zipdicts(tcls._testcases, sameTCls._testcases):
					self.assertEqual(tc.Name, sameTC.Name)
					self.assertEqual(tc.Classname, sameTC.Classname)
					self.assertEqual(tc.Status, sameTC.Status)
					self.assertEqual(tc.Duration, sameTC.Duration)

class PythonPyTest(TestCase):
	def test_Read(self) -> None:
		print()

		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Python-pytest/TestReportSummary.xml")
		doc = PyTestDocument(junitExampleFile, analyzeAndConvert=True)

		self.assertEqual(1, doc.TestsuiteCount)
		self.assertEqual(8, doc.TestcaseCount)
		self.assertEqual(0, doc.Errored)
		self.assertEqual(0, doc.Skipped)
		self.assertEqual(0, doc.Failed)
		# self.assertEqual(8, doc.Passed)
		self.assertEqual(8, doc.Tests)

		print(f"JUnit file:")
		print(f"  Testsuites: {doc.TestsuiteCount}")
		print(f"  Testcases:  {doc.TestcaseCount}")

		print()
		print(f"Statistics:")
		print(f"  Times: parsing by lxml: {doc.AnalysisDuration.total_seconds():.3f}s   convert: {doc.ModelConversionDuration.total_seconds():.3f}s")

	def test_ReadWrite(self) -> None:
		print()

		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Python-pytest/TestReportSummary.xml")
		doc = PyTestDocument(junitExampleFile, analyzeAndConvert=True)

		junitOutputFile = Path("tests/output/JUnit/pyEDAA.Reports/Python-pytest/TestReportSummary.xml")
		junitOutputFile.parent.mkdir(parents=True, exist_ok=True)
		doc.Write(junitOutputFile, regenerate=True, overwrite=True)

		sameDoc = PyTestDocument(junitOutputFile, analyzeAndConvert=True)

		self.assertEqual(doc.TestsuiteCount, sameDoc.TestsuiteCount)
		self.assertEqual(doc.TestcaseCount, sameDoc.TestcaseCount)
		self.assertEqual(doc.Errored, sameDoc.Errored)
		self.assertEqual(doc.Skipped, sameDoc.Skipped)
		self.assertEqual(doc.Failed, sameDoc.Failed)
		self.assertEqual(doc.Passed, sameDoc.Passed)
		self.assertEqual(doc.Tests, sameDoc.Tests)

		for tsName, ts, sameTS in zipdicts(doc._testsuites, sameDoc._testsuites):
			self.assertEqual(ts.Name, sameTS.Name)
			self.assertEqual(ts.Duration, sameTS.Duration)
			self.assertEqual(ts.TestcaseCount, sameTS.TestcaseCount)
			self.assertEqual(ts.AssertionCount, sameTS.AssertionCount)
			self.assertEqual(ts.Errored, sameTS.Errored)
			self.assertEqual(ts.Skipped, sameTS.Skipped)
			self.assertEqual(ts.Failed, sameTS.Failed)
			self.assertEqual(ts.Passed, sameTS.Passed)
			self.assertEqual(ts.Tests, sameTS.Tests)

			for tclsName, tcls, sameTCls in zipdicts(ts._testclasses, sameTS._testclasses):
				self.assertEqual(tcls.Name, sameTCls.Name)
				self.assertEqual(tcls.Classname, sameTCls.Classname)
				self.assertEqual(tcls.TestcaseCount, sameTCls.TestcaseCount)
				self.assertEqual(tcls.AssertionCount, sameTCls.AssertionCount)

				for tcName, tc, sameTC in zipdicts(tcls._testcases, sameTCls._testcases):
					self.assertEqual(tc.Name, sameTC.Name)
					self.assertEqual(tc.Classname, sameTC.Classname)
					self.assertEqual(tc.Status, sameTC.Status)
					self.assertEqual(tc.Duration, sameTC.Duration)
					self.assertEqual(tc.AssertionCount, sameTC.AssertionCount)


class RustCargo(TestCase):
	def test_JUnit(self) -> None:
		"""Known gap: no dialect reads cargo-nextest's JUnit report yet."""
		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Rust-Cargo/nextest-junit.xml")

		for documentClass in (AnyJUnitDocument, JUnit4Document, CTestDocument, GTestDocument, PyTestDocument):
			with self.subTest(dialect=documentClass.__module__):
				with self.assertRaises(UnittestError):
					documentClass(junitExampleFile, analyzeAndConvert=True)
