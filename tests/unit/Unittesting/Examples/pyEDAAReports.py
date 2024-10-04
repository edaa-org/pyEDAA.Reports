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
"""Testcase for unit testing report files generated by OSVVM."""
from pathlib      import Path
from unittest     import TestCase

# FIXME: change to generic JUnit
from pyEDAA.Reports.Unittesting.JUnit.AntJUnit        import Document as JUnit4Document
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


class JavaAntJUnit4(TestCase):
	def test_JUnit4(self):
		print()

		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Java-Ant-JUnit4/TEST-my.AllTests.xml")
		doc = JUnit4Document(junitExampleFile, analyzeAndConvert=True)

		# self.assertEqual(1, doc.TestsuiteCount)
		# self.assertEqual(3, doc.TestcaseCount)

		print(f"JUnit file:")
		print(f"  Testsuites: {doc.TestsuiteCount}")
		print(f"  Testcases:  {doc.TestcaseCount}")

		print()
		print(f"Statistics:")
		print(f"  Times: parsing by lxml: {doc.AnalysisDuration.total_seconds():.3f}s   convert: {doc.ModelConversionDuration.total_seconds():.3f}s")


class PythonPyTest(TestCase):
	def test_PyTest(self):
		print()

		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Python-pytest/TestReportSummary.xml")
		doc = PyTestDocument(junitExampleFile, analyzeAndConvert=True)

		self.assertEqual(1, doc.TestsuiteCount)
		self.assertEqual(8, doc.TestcaseCount)

		print(f"JUnit file:")
		print(f"  Testsuites: {doc.TestsuiteCount}")
		print(f"  Testcases:  {doc.TestcaseCount}")

		print()
		print(f"Statistics:")
		print(f"  Times: parsing by lxml: {doc.AnalysisDuration.total_seconds():.3f}s   convert: {doc.ModelConversionDuration.total_seconds():.3f}s")
