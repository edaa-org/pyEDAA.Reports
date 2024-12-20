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
# Copyright 2021-2024 Electronic Design Automation Abstraction (EDA²)                                                  #
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

# FIXME: change to generic JUnit
from pyEDAA.Reports.Unittesting.JUnit.AntJUnit4       import Document as JUnit4Document
from pyEDAA.Reports.Unittesting.JUnit.CTestJUnit      import Document as CTestDocument
from pyEDAA.Reports.Unittesting.JUnit.GoogleTestJUnit import Document as GTestDocument
from pyEDAA.Reports.Unittesting.JUnit.PyTestJUnit     import Document as PyTestDocument


if __name__ == "__main__": # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unitest <testcase module>'")
	exit(1)


class CppGoogleTest(TestCase):
	def test_gtest(self):
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

	def test_ReadWrite(self):
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
	def test_ctest(self):
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

	def test_ReadWrite(self):
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


class JavaAntJUnit4(TestCase):
	def test_JUnit4(self):
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

	def test_ReadWrite(self):
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


class PythonPyTest(TestCase):
	def test_Read(self):
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

	def test_ReadWrite(self):
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