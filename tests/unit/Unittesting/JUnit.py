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
from datetime import timedelta, datetime
from pathlib  import Path
from unittest import TestCase as py_TestCase

from pyEDAA.Reports.Unittesting       import TestcaseStatus, TestsuiteStatus, TestsuiteKind
from pyEDAA.Reports.Unittesting       import TestsuiteSummary as ut_TestsuiteSummary
from pyEDAA.Reports.Unittesting       import Testsuite as ut_Testsuite, Testcase as ut_Testcase
from pyEDAA.Reports.Unittesting.JUnit import UnittestException
from pyEDAA.Reports.Unittesting.JUnit import Testcase, Testclass, Testsuite, TestsuiteSummary, Document as JUnitDocument


class Instantiation(py_TestCase):
	def test_Testcase(self) -> None:
		tc = Testcase("tc")

		self.assertEqual("tc", tc.Name)
		with self.assertRaises(UnittestException):
			_ = tc.Classname
		self.assertEqual(TestcaseStatus.Unknown, tc.Status)
		self.assertIsNone(tc.Duration)
		self.assertEqual(0, tc.AssertionCount)

	def test_Class(self) -> None:
		cls = Testclass("cls")

		self.assertEqual("cls", cls.Name)
		self.assertEqual("cls", cls.Classname)
		# self.assertEqual(TestcaseStatus.Unknown, cls.Status)
		# self.assertIsNone(cls.Duration)
		self.assertEqual(0, cls.AssertionCount)

	def test_Testsuite(self) -> None:
		ts = Testsuite("ts")

		self.assertEqual("ts", ts.Name)
		self.assertIsNone(ts.Hostname)
		self.assertEqual(TestsuiteStatus.Unknown, ts.Status)
		self.assertIsNone(ts.StartTime)
		self.assertIsNone(ts.Duration)
		self.assertEqual(0, ts.TestcaseCount)
		self.assertEqual(0, ts.AssertionCount)

	def test_TestsuiteSummary(self) -> None:
		tss = TestsuiteSummary("tss")

		self.assertEqual("tss", tss.Name)
		# self.assertIsNone(tss.Hostname)
		self.assertIsNone(tss.StartTime)
		self.assertIsNone(tss.Duration)
		self.assertEqual(0, tss.TestsuiteCount)
		self.assertEqual(0, tss.AssertionCount)


class TestcasesInTestclass(py_TestCase):
	def test_TestcaseConstructor(self) -> None:
		cls = Testclass("cls")
		self.assertEqual(0, cls.TestcaseCount)

		tc1 = Testcase("tc1", parent=cls)
		testcases1 = (tc1,)
		self.assertEqual(1, cls.TestcaseCount)
		self.assertTupleEqual(testcases1, tuple(cls.Testcases.values()))

		tc2 = Testcase("tc2", parent=cls)
		testcases2 = (tc1, tc2)
		self.assertEqual(2, cls.TestcaseCount)
		self.assertTupleEqual(testcases2, tuple(cls.Testcases.values()))

		for testcase in testcases2:
			self.assertEqual(cls, testcase.Parent)

	def test_ClassConstructor(self) -> None:
		tc1 = Testcase("tc1")
		tc2 = Testcase("tc2")
		testcases2 = (tc1, tc2)

		cls = Testclass("cls", testcases=testcases2)
		self.assertEqual(2, cls.TestcaseCount)
		self.assertTupleEqual(testcases2, tuple(cls.Testcases.values()))

		for testcase in testcases2:
			self.assertEqual(cls, testcase.Parent)

	def test_AddTestcase(self) -> None:
		tc1 = Testcase("tc1")
		tc2 = Testcase("tc2")

		testcases1 = (tc1,)
		testcases2 = (tc1, tc2)

		cls = Testclass("cls")
		self.assertEqual(0, cls.TestcaseCount)

		cls.AddTestcase(tc1)
		self.assertEqual(1, cls.TestcaseCount)
		self.assertTupleEqual(testcases1, tuple(cls.Testcases.values()))

		cls.AddTestcase(tc2)
		self.assertEqual(2, cls.TestcaseCount)
		self.assertTupleEqual(testcases2, tuple(cls.Testcases.values()))

		for testcase in testcases2:
			self.assertEqual(cls, testcase.Parent)

	def test_AddTestcases(self) -> None:
		tc1 = Testcase("tc1")
		tc2 = Testcase("tc2")
		tc3 = Testcase("tc3")

		testcases1 = (tc1,)
		testcases23 = (tc2, tc3)
		testcases3 = (tc1, tc2, tc3)

		cls = Testclass("cls")
		self.assertEqual(0, cls.TestcaseCount)

		cls.AddTestcases(testcases1)
		self.assertEqual(1, cls.TestcaseCount)
		self.assertTupleEqual(testcases1, tuple(cls.Testcases.values()))

		cls.AddTestcases(testcases23)
		self.assertEqual(3, cls.TestcaseCount)
		self.assertTupleEqual(testcases3, tuple(cls.Testcases.values()))

		for testcase in testcases3:
			self.assertEqual(cls, testcase.Parent)


class TestclassesInTestsuite(py_TestCase):
	def test_ClassConstructor(self) -> None:
		ts = Testsuite("ts")
		self.assertEqual(0, ts.TestcaseCount)

		cls1 = Testclass("cls1", parent=ts)
		classes1 = (cls1,)
		self.assertEqual(1, ts.TestclassCount)
		self.assertTupleEqual(classes1, tuple(ts.Testclasses.values()))

		cls2 = Testclass("cls2", parent=ts)
		classes2 = (cls1, cls2)
		self.assertEqual(2, ts.TestclassCount)
		self.assertTupleEqual(classes2, tuple(ts.Testclasses.values()))

		for testcase in classes2:
			self.assertEqual(ts, testcase.Parent)

	def test_TestsuiteConstructor(self) -> None:
		cls1 = Testclass("cls1")
		cls2 = Testclass("cls2")
		classes2 = (cls1, cls2)

		ts = Testsuite("ts", testclasses=classes2)
		self.assertEqual(2, ts.TestclassCount)
		self.assertTupleEqual(classes2, tuple(ts.Testclasses.values()))

		for testcase in classes2:
			self.assertEqual(ts, testcase.Parent)

	def test_AddTestcase(self) -> None:
		cls1 = Testclass("cls1")
		cls2 = Testclass("cls2")

		classes1 = (cls1,)
		classes2 = (cls1, cls2)

		ts = Testsuite("ts")
		self.assertEqual(0, ts.TestclassCount)

		ts.AddTestclass(cls1)
		self.assertEqual(1, ts.TestclassCount)
		self.assertTupleEqual(classes1, tuple(ts.Testclasses.values()))

		ts.AddTestclass(cls2)
		self.assertEqual(2, ts.TestclassCount)
		self.assertTupleEqual(classes2, tuple(ts.Testclasses.values()))

		for testcase in classes2:
			self.assertEqual(ts, testcase.Parent)

	def test_AddTestcases(self) -> None:
		cls1 = Testclass("cls1")
		cls2 = Testclass("cls2")
		cls3 = Testclass("cls3")

		classes1 = (cls1,)
		classes23 = (cls2, cls3)
		classes3 = (cls1, cls2, cls3)

		ts = Testsuite("ts")
		self.assertEqual(0, ts.TestclassCount)

		ts.AddTestclasses(classes1)
		self.assertEqual(1, ts.TestclassCount)
		self.assertTupleEqual(classes1, tuple(ts.Testclasses.values()))

		ts.AddTestclasses(classes23)
		self.assertEqual(3, ts.TestclassCount)
		self.assertTupleEqual(classes3, tuple(ts.Testclasses.values()))

		for testcase in classes3:
			self.assertEqual(ts, testcase.Parent)


class TestsuiteInTestsuiteSummary(py_TestCase):
	def test_TestsuiteConstructor(self) -> None:
		tss = TestsuiteSummary("tss")
		self.assertEqual(0, tss.TestsuiteCount)

		ts1 = Testsuite("ts1", parent=tss)
		testsuites1 = (ts1,)
		self.assertEqual(1, tss.TestsuiteCount)
		self.assertTupleEqual(testsuites1, tuple(tss.Testsuites.values()))

		ts2 = Testsuite("ts2", parent=tss)
		testsuites2 = (ts1, ts2)
		self.assertEqual(2, tss.TestsuiteCount)
		self.assertTupleEqual(testsuites2, tuple(tss.Testsuites.values()))

		for testsuite in testsuites2:
			self.assertEqual(tss, testsuite.Parent)

	def test_TestsuitesConstructor(self) -> None:
		ts1 = Testsuite("ts1")
		ts2 = Testsuite("ts2")
		testsuites2 = (ts1, ts2)

		tss = TestsuiteSummary("tss", testsuites=testsuites2)
		self.assertEqual(2, tss.TestsuiteCount)
		self.assertTupleEqual(testsuites2, tuple(tss.Testsuites.values()))

		for testsuite in testsuites2:
			self.assertEqual(tss, testsuite.Parent)

	def test_AddTestsuite(self) -> None:
		ts1 = Testsuite("ts1")
		ts2 = Testsuite("ts2")

		testsuites1 = (ts1,)
		testsuites2 = (ts1, ts2)

		tss = TestsuiteSummary("tss")
		self.assertEqual(0, tss.TestsuiteCount)

		tss.AddTestsuite(ts1)
		self.assertEqual(1, tss.TestsuiteCount)
		self.assertTupleEqual(testsuites1, tuple(tss.Testsuites.values()))

		tss.AddTestsuite(ts2)
		self.assertEqual(2, tss.TestsuiteCount)
		self.assertTupleEqual(testsuites2, tuple(tss.Testsuites.values()))

		for testsuite in testsuites2:
			self.assertEqual(tss, testsuite.Parent)

	def test_AddTestsuites(self) -> None:
		ts1 = Testsuite("ts1")
		ts2 = Testsuite("ts2")
		ts3 = Testsuite("ts3")

		testsuites1 = (ts1,)
		testsuites23 = (ts2, ts3)
		testsuites3 = (ts1, ts2, ts3)

		tss = TestsuiteSummary("tss")
		self.assertEqual(0, tss.TestsuiteCount)

		tss.AddTestsuites(testsuites1)
		self.assertEqual(1, tss.TestsuiteCount)
		self.assertTupleEqual(testsuites1, tuple(tss.Testsuites.values()))

		tss.AddTestsuites(testsuites23)
		self.assertEqual(3, tss.TestsuiteCount)
		self.assertTupleEqual(testsuites3, tuple(tss.Testsuites.values()))

		for testsuite in testsuites3:
			self.assertEqual(tss, testsuite.Parent)


class Hierarchy(py_TestCase):
	def test_Simple(self) -> None:
		tss = TestsuiteSummary("tss")
		ts = Testsuite("ts", parent=tss)
		cls1 = Testclass("cls1", parent=ts)
		tc1_1 = Testcase("tc1", parent=cls1)
		tss.Aggregate()

		self.assertEqual(0, tc1_1.AssertionCount)
		self.assertEqual(0, ts.AssertionCount)
		self.assertEqual(0, tss.AssertionCount)
		self.assertEqual(1, ts.Tests)
		self.assertEqual(1, tss.Tests)

		tc2_1 = Testcase("tc2", parent=cls1)
		tss.Aggregate()

		self.assertEqual(2, ts.Tests)
		self.assertEqual(2, tss.Tests)

		cls2 = Testclass("cls2", parent=ts)
		tc3_2 = Testcase("tc3", parent=cls2)
		tc4_2 = Testcase("tc4", parent=cls2)
		tss.Aggregate()

		self.assertEqual(4, ts.Tests)
		self.assertEqual(4, tss.Tests)

	def test_Complex(self) -> None:
		tss = TestsuiteSummary("tss")
		ts1 = Testsuite("ts1", parent=tss)
		cls1 = Testclass("cls1", parent=ts1)
		tc1_1 = Testcase("tc1", parent=cls1)
		tc2_1 = Testcase("tc2", parent=cls1)
		cls2 = Testclass("cls2", parent=ts1)
		tc3_2 = Testcase("tc3", parent=cls2)
		tc4_2 = Testcase("tc4", parent=cls2)
		tss.Aggregate()

		self.assertEqual(4, ts1.Tests)
		self.assertEqual(4, tss.Tests)

		ts2 = Testsuite("ts2", parent=tss)
		cls3 = Testclass("cls1", parent=ts2)
		tc5_3 = Testcase("tc5", parent=cls3)
		tc6_3 = Testcase("tc6", parent=cls3)
		cls4 = Testclass("cls4", parent=ts2)
		tc7_4 = Testcase("tc7", parent=cls4)
		tc8_4 = Testcase("tc8", parent=cls4)
		tss.Aggregate()

		self.assertEqual(4, ts2.Tests)
		self.assertEqual(8, tss.Tests)


class Conversion(py_TestCase):
	def test_TestcaseToTestcase(self) -> None:
		juTC = Testcase("tc", duration=timedelta(seconds=0.023))
		tc = juTC.ToTestcase()

		self.assertEqual("tc", tc.Name)
		self.assertEqual(timedelta(seconds=0.023), tc.TestDuration)

	def test_ClassToTestsuite(self) -> None:
		juC = Testclass("cls")
		ts = juC.ToTestsuite()

		self.assertEqual("cls", ts.Name)
		self.assertEqual(TestsuiteKind.Class, ts.Kind)

	def test_TestsuiteToTestsuite(self) -> None:
		juTS = Testsuite("ts", duration=timedelta(seconds=0.024))
		ts = juTS.ToTestsuite()

		self.assertEqual("ts", ts.Name)
		self.assertEqual(TestsuiteKind.Logical, ts.Kind)
		self.assertEqual(timedelta(seconds=0.024), ts.TotalDuration)

	def test_TestsuiteSummaryToTestsuiteSummary(self) -> None:
		juTSS = TestsuiteSummary("tss", duration=timedelta(seconds=0.025))
		tss = juTSS.ToTestsuiteSummary()

		self.assertEqual("tss", tss.Name)
		self.assertEqual(timedelta(seconds=0.025), tss.TotalDuration)

	def test_FromTestcase(self) -> None:
		tc = ut_Testcase("tc")
		juTC = Testcase.FromTestcase(tc)

		self.assertEqual("tc", juTC.Name)

	def test_FromTestsuite(self) -> None:
		ts = ut_Testsuite("ts")
		juTS = Testsuite.FromTestsuite(ts)

		self.assertEqual("ts", juTS.Name)

	def test_FromTestsuiteSummary(self) -> None:
		tss = ut_TestsuiteSummary("tss")
		juTSS = TestsuiteSummary.FromTestsuiteSummary(tss)

		self.assertEqual("tss", juTSS.Name)


class Document(py_TestCase):
	_outputDirectory = Path("tests/output/JUnit_Document")

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

	def test_Create_WithoutParse(self) -> None:
		zeroTime = timedelta()

		junitExampleFile = Path("tests/data/JUnit/pyAttributes/pytest.pyAttributes.xml")
		doc = JUnitDocument(junitExampleFile)

		self.assertEqual(junitExampleFile, doc.Path)
		self.assertLess(doc.AnalysisDuration, zeroTime)
		self.assertLess(doc.ModelConversionDuration, zeroTime)

		doc.Read()
		self.assertGreater(doc.AnalysisDuration, zeroTime)

		doc.Parse()
		self.assertGreater(doc.ModelConversionDuration, zeroTime)

	def test_Create_WithParse(self) -> None:
		zeroTime = timedelta()

		junitExampleFile = Path("tests/data/JUnit/pyAttributes/pytest.pyAttributes.xml")
		doc = JUnitDocument(junitExampleFile, parse=True)

		self.assertEqual(junitExampleFile, doc.Path)
		self.assertGreater(doc.AnalysisDuration, zeroTime)
		self.assertGreater(doc.ModelConversionDuration, zeroTime)

	def test_ReadWrite(self) -> None:
		junitExampleFile = Path("tests/data/JUnit/pyAttributes/pytest.pyAttributes.xml")
		doc = JUnitDocument(junitExampleFile, parse=True)

		doc.Write(self._outputDirectory / "ReadWrite.xml")

	def test_Generate(self) -> None:
		print()
		doc = JUnitDocument(self._outputDirectory / "Generate.xml")
		doc._name = "root"
		doc._startTime = datetime.fromisoformat("2024-02-24T12:12:12+01:00")
		ts1 = Testsuite("ts1", startTime=datetime.fromisoformat("2024-02-24T12:12:12+01:00"))
		cls1 = Testclass("cls1", parent=ts1)
		tc11 = Testcase("tc11", assertionCount=10, duration=timedelta(seconds=0.005), parent=cls1)
		cls2 = Testclass("cls2", parent=ts1)
		tc12 = Testcase("tc12", assertionCount=24, duration=timedelta(seconds=0.859), parent=cls2)
		tc13 = Testcase("tc13", assertionCount=24, duration=timedelta(seconds=0.859), parent=cls2)
		ts2 = Testsuite("ts2", startTime=datetime.fromisoformat("2024-02-24T12:12:13+01:00"))
		cls3 = Testclass("cls3", parent=ts2)
		tc21 = Testcase("tc21", assertionCount=13, duration=timedelta(seconds=3.637), parent=cls3)
		tc22 = Testcase("tc22", assertionCount=48, duration=timedelta(seconds=2.473), parent=cls3)
		cls4 = Testclass("cls4", parent=ts2)
		tc23 = Testcase("tc23", assertionCount=48, duration=timedelta(seconds=2.473), parent=cls4)
		doc.AddTestsuite(ts1)
		doc.AddTestsuite(ts2)
		doc.Aggregate()

		# tree = doc.ToTree()
		# print(tree.Render())

		doc.Write(regenerate=True)


class ExampleFiles(py_TestCase):
	def test_pytest_pyAttributes(self) -> None:
		print()

		junitExampleFile = Path("tests/data/JUnit/pyAttributes/pytest.pyAttributes.xml")
		doc = JUnitDocument(junitExampleFile, parse=True)

		self.assertGreater(doc.TestsuiteCount, 0)
		self.assertGreater(doc.TestcaseCount, 0)

		print(f"JUnit file:")
		print(f"  Testsuites: {len(doc.Testsuites)}")
		print(f"  Testcases:  ")

		print()
		print(f"Statistics:")
		print(f"  Times: MiniDOM: {doc.AnalysisDuration.total_seconds():.3f}s   convert: {doc.ModelConversionDuration.total_seconds():.3f}s")

	def test_OSVVM_Libraries(self) -> None:
		print()

		junitExampleFile = Path("tests/data/JUnit/OsvvmLibraries/OSVVMLibraries_RunAllTests.xml")
		doc = JUnitDocument(junitExampleFile, parse=True)

		self.assertGreater(doc.TestsuiteCount, 0)
		self.assertGreater(doc.TestcaseCount, 0)

		print(f"JUnit file:")
		print(f"  Testsuites: {len(doc.Testsuites)}")
		print(f"  Testcases:  ")

		print()
		print(f"Statistics:")
		print(f"  Times: MiniDOM: {doc.AnalysisDuration.total_seconds():.3f}s   convert: {doc.ModelConversionDuration.total_seconds():.3f}s")
