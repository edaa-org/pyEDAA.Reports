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

from pyEDAA.Reports.Unittesting       import TestcaseStatus, TestsuiteStatus
from pyEDAA.Reports.Unittesting       import Document as ut_Document, TestsuiteSummary as ut_TestsuiteSummary
from pyEDAA.Reports.Unittesting       import Testsuite as ut_Testsuite, Testcase as ut_Testcase
from pyEDAA.Reports.Unittesting.JUnit import Testcase, Testsuite, TestsuiteSummary, Document as JUnitDocument


class Instantiation(py_TestCase):
	def test_Testcase(self) -> None:
		tc = Testcase("tc", "cls")

		self.assertEqual("tc", tc.Name)
		self.assertEqual("cls", tc.Classname)
		self.assertEqual(TestcaseStatus.Unknown, tc.Status)
		self.assertIsNone(tc.Duration)
		self.assertIsNone(tc.AssertionCount)

	def test_Testsuite(self) -> None:
		ts = Testsuite("ts")

		self.assertEqual("ts", ts.Name)
		self.assertIsNone(ts.Hostname)
		self.assertEqual(TestsuiteStatus.Unknown, ts.Status)
		self.assertIsNone(ts.StartTime)
		self.assertIsNone(ts.Duration)
		self.assertEqual(0, ts.TestcaseCount)
		self.assertIsNone(ts.AssertionCount)

	def test_TestsuiteSummary(self) -> None:
		tss = TestsuiteSummary("tss")

		self.assertEqual("tss", tss.Name)
		# self.assertIsNone(tss.Hostname)
		self.assertIsNone(tss.StartTime)
		self.assertIsNone(tss.Duration)
		self.assertEqual(0, tss.TestsuiteCount)
		self.assertIsNone(tss.AssertionCount)


class TestcasesInTestsuite(py_TestCase):
	def test_TestcaseConstructor(self) -> None:
		ts = Testsuite("ts")
		self.assertEqual(0, ts.TestcaseCount)

		tc1 = Testcase("tc1", "cls", parent=ts)
		testcases1 = (tc1,)
		self.assertEqual(1, ts.TestcaseCount)
		self.assertTupleEqual(testcases1, tuple(ts.Testcases.values()))

		tc2 = Testcase("tc2", "cls", parent=ts)
		testcases2 = (tc1, tc2)
		self.assertEqual(2, ts.TestcaseCount)
		self.assertTupleEqual(testcases2, tuple(ts.Testcases.values()))

		for testcase in testcases2:
			self.assertEqual(ts, testcase.Parent)

	def test_TestsuiteConstructor(self) -> None:
		tc1 = Testcase("tc1", "cls")
		tc2 = Testcase("tc2", "cls")
		testcases2 = (tc1, tc2)

		ts = Testsuite("ts", testcases=testcases2)
		self.assertEqual(2, ts.TestcaseCount)
		self.assertTupleEqual(testcases2, tuple(ts.Testcases.values()))

		for testcase in testcases2:
			self.assertEqual(ts, testcase.Parent)

	def test_AddTestcase(self) -> None:
		tc1 = Testcase("tc1", "cls")
		tc2 = Testcase("tc2", "cls")

		testcases1 = (tc1,)
		testcases2 = (tc1, tc2)

		ts = Testsuite("ts")
		self.assertEqual(0, ts.TestcaseCount)

		ts.AddTestcase(tc1)
		self.assertEqual(1, ts.TestcaseCount)
		self.assertTupleEqual(testcases1, tuple(ts.Testcases.values()))

		ts.AddTestcase(tc2)
		self.assertEqual(2, ts.TestcaseCount)
		self.assertTupleEqual(testcases2, tuple(ts.Testcases.values()))

		for testcase in testcases2:
			self.assertEqual(ts, testcase.Parent)

	def test_AddTestcases(self) -> None:
		tc1 = Testcase("tc1", "cls")
		tc2 = Testcase("tc2", "cls")
		tc3 = Testcase("tc3", "cls")

		testcases1 = (tc1,)
		testcases23 = (tc2, tc3)
		testcases3 = (tc1, tc2, tc3)

		ts = Testsuite("ts")
		self.assertEqual(0, ts.TestcaseCount)

		ts.AddTestcases(testcases1)
		self.assertEqual(1, ts.TestcaseCount)
		self.assertTupleEqual(testcases1, tuple(ts.Testcases.values()))

		ts.AddTestcases(testcases23)
		self.assertEqual(3, ts.TestcaseCount)
		self.assertTupleEqual(testcases3, tuple(ts.Testcases.values()))

		for testcase in testcases3:
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
		tc1_1 = Testcase("tc1", "cls1", parent=ts)
		tss.Aggregate()

		self.assertIsNone(tc1_1.AssertionCount)
		self.assertIsNone(ts.AssertionCount)
		self.assertIsNone(tss.AssertionCount)
		self.assertEqual(1, ts.Tests)
		self.assertEqual(1, tss.Tests)

		tc2_1 = Testcase("tc2", "cls1", parent=ts)
		tss.Aggregate()

		self.assertEqual(2, ts.Tests)
		self.assertEqual(2, tss.Tests)

		tc3_2 = Testcase("tc3", "cls2", parent=ts)
		tc4_2 = Testcase("tc4", "cls2", parent=ts)
		tss.Aggregate()

		self.assertEqual(4, ts.Tests)
		self.assertEqual(4, tss.Tests)

	def test_Complex(self) -> None:
		tss = TestsuiteSummary("tss")
		ts1 = Testsuite("ts1", parent=tss)
		tc1_1 = Testcase("tc1", "cls1", parent=ts1)
		tc2_1 = Testcase("tc2", "cls1", parent=ts1)
		tc3_2 = Testcase("tc3", "cls2", parent=ts1)
		tc4_2 = Testcase("tc4", "cls2", parent=ts1)
		tss.Aggregate()

		self.assertEqual(4, ts1.Tests)
		self.assertEqual(4, tss.Tests)

		ts2 = Testsuite("ts2", parent=tss)
		tc5_3 = Testcase("tc5", "cls3", parent=ts2)
		tc6_3 = Testcase("tc6", "cls3", parent=ts2)
		tc7_4 = Testcase("tc7", "cls4", parent=ts2)
		tc8_4 = Testcase("tc8", "cls4", parent=ts2)
		tss.Aggregate()

		self.assertEqual(4, ts2.Tests)
		self.assertEqual(8, tss.Tests)


class Conversion(py_TestCase):
	def test_ToTestcase(self) -> None:
		juTC = Testcase("tc", "cls1", duration=timedelta(seconds=0.023))
		tc = juTC.ToTestcase()

		self.assertEqual("tc", tc.Name)
		self.assertEqual(timedelta(seconds=0.023), tc.TestDuration)

	def test_ToTestsuite(self) -> None:
		juTS = Testsuite("ts", duration=timedelta(seconds=0.024))
		ts = juTS.ToTestsuite()

		self.assertEqual("ts", ts.Name)
		self.assertEqual(timedelta(seconds=0.024), ts.TotalDuration)

	def test_ToTestsuiteSummary(self) -> None:
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

		junitExampleFile = Path("tests/data/JUnit/pytest.pyAttributes.xml")
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

		junitExampleFile = Path("tests/data/JUnit/pytest.pyAttributes.xml")
		doc = JUnitDocument(junitExampleFile, parse=True)

		self.assertEqual(junitExampleFile, doc.Path)
		self.assertGreater(doc.AnalysisDuration, zeroTime)
		self.assertGreater(doc.ModelConversionDuration, zeroTime)

	def test_ReadWrite(self) -> None:
		junitExampleFile = Path("tests/data/JUnit/pytest.pyAttributes.xml")
		doc = JUnitDocument(junitExampleFile, parse=True)

		doc.Write(self._outputDirectory / "ReadWrite.xml")

	def test_Generate(self) -> None:
		print()
		doc = JUnitDocument(self._outputDirectory / "Generate.xml")
		doc._name = "root"
		doc._startTime = datetime.fromisoformat("2024-02-24T12:12:12+01:00")
		ts1 = Testsuite("ts1", startTime=datetime.fromisoformat("2024-02-24T12:12:12+01:00"))
		tc11 = Testcase("tc11", "cls1", assertionCount=10, duration=timedelta(seconds=0.005), parent=ts1)
		tc12 = Testcase("tc12", "cls2", assertionCount=24, duration=timedelta(seconds=0.859), parent=ts1)
		tc13 = Testcase("tc13", "cls2", assertionCount=24, duration=timedelta(seconds=0.859), parent=ts1)
		ts2 = Testsuite("ts2", startTime=datetime.fromisoformat("2024-02-24T12:12:13+01:00"))
		tc21 = Testcase("tc21", "cls3", assertionCount=13, duration=timedelta(seconds=3.637), parent=ts2)
		tc22 = Testcase("tc22", "cls3", assertionCount=48, duration=timedelta(seconds=2.473), parent=ts2)
		tc23 = Testcase("tc23", "cls4", assertionCount=48, duration=timedelta(seconds=2.473), parent=ts2)
		doc.AddTestsuite(ts1)
		doc.AddTestsuite(ts2)
		doc.Aggregate()

		# tree = doc.ToTree()
		# print(tree.Render())

		doc.Write(regenerate=True)


class ExampleFiles(py_TestCase):
	def test_pytest_pyAttributes(self) -> None:
		print()

		junitExampleFile = Path("tests/data/JUnit/pytest.pyAttributes.xml")
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

		junitExampleFile = Path("tests/data/JUnit/osvvm.Libraries.xml")
		doc = JUnitDocument(junitExampleFile, parse=True)

		self.assertGreater(doc.TestsuiteCount, 0)
		self.assertGreater(doc.TestcaseCount, 0)

		print(f"JUnit file:")
		print(f"  Testsuites: {len(doc.Testsuites)}")
		print(f"  Testcases:  ")

		print()
		print(f"Statistics:")
		print(f"  Times: MiniDOM: {doc.AnalysisDuration.total_seconds():.3f}s   convert: {doc.ModelConversionDuration.total_seconds():.3f}s")
