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
from datetime import timedelta
from pathlib  import Path
from unittest import TestCase as ut_TestCase

from pyEDAA.Reports.Unittesting.JUnit import JUnitDocument, Testcase, TestcaseState, Testsuite, TestsuiteSummary


class Instantiation(ut_TestCase):
	def test_Summary(self) -> None:
		tss = TestsuiteSummary("tss", totalDuration=timedelta(milliseconds=9831))

		self.assertEqual("tss", tss.Name)
		self.assertEqual(TestcaseState.Unknown, tss.State)
		self.assertEqual(0, len(tss.Testsuites))
		self.assertEqual(9.831, tss.TotalDuration.total_seconds())

	def test_Testsuite(self) -> None:
		ts = Testsuite("ts", totalDuration=timedelta(milliseconds=4206))

		self.assertEqual("ts", ts.Name)
		self.assertEqual(TestcaseState.Unknown, ts.State)
		self.assertEqual(0, len(ts.Testsuites))
		self.assertEqual(0, len(ts.Testcases))
		self.assertEqual(4.206, ts.TotalDuration.total_seconds())

	def test_Testcase(self) -> None:
		tc = Testcase("tc", totalDuration=timedelta(milliseconds=1505))

		self.assertEqual("tc", tc.Name)
		self.assertEqual(TestcaseState.Unknown, tc.State)
		self.assertIsNone(tc.AssertionCount)
		self.assertIsNone(tc.PassedAssertionCount)
		self.assertIsNone(tc.FailedAssertionCount)
		self.assertEqual(0, tc.WarningCount)
		self.assertEqual(0, tc.ErrorCount)
		self.assertEqual(0, tc.FatalCount)
		self.assertEqual(1.505, tc.TotalDuration.total_seconds())


class ExampleFiles(ut_TestCase):
	def test_pytest_pyAttributes(self) -> None:
		print()

		junitExampleFile = Path("tests/data/JUnit/pytest.pyAttributes.xml")
		doc = JUnitDocument(junitExampleFile)

		print(f"JUnit file:")
		print(f"  Testsuites: {len(doc.Testsuites)}")
		print(f"  Testcases:  ")

		print()
		print(f"Statistics:")
		print(f"  Times: MiniDOM: {doc._readingByMiniDom:.3f}s   convert: {doc._modelConversion:.3f}s")

	def test_OSVVM_Libraries(self) -> None:
		print()

		junitExampleFile = Path("tests/data/JUnit/osvvm.Libraries.xml")
		doc = JUnitDocument(junitExampleFile)

		print(f"JUnit file:")
		print(f"  Testsuites: {len(doc.Testsuites)}")
		print(f"  Testcases:  ")

		print()
		print(f"Statistics:")
		print(f"  Times: MiniDOM: {doc._readingByMiniDom:.3f}s   convert: {doc._modelConversion:.3f}s")
