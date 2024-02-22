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

from pyEDAA.Reports.Unittesting.JUnit import Document, Testcase, TestcaseState, Testsuite, TestsuiteSummary


class Instantiation(ut_TestCase):
	def test_Summary(self) -> None:
		tss = TestsuiteSummary("tss", timedelta(milliseconds=9831))

		self.assertEqual("tss", tss.Name)
		self.assertEqual(TestcaseState.Unknown, tss.State)
		self.assertEqual(0, len(tss.Testsuites))
		self.assertEqual(9.831, tss.Time.total_seconds())

	def test_Testsuite(self) -> None:
		ts = Testsuite("ts", timedelta(milliseconds=4206))

		self.assertEqual("ts", ts.Name)
		self.assertEqual(TestcaseState.Unknown, ts.State)
		self.assertEqual(0, len(ts.Testsuites))
		self.assertEqual(0, len(ts.Testcases))
		self.assertEqual(4.206, ts.Time.total_seconds())

	def test_Testcase(self) -> None:
		tc = Testcase("tc", timedelta(milliseconds=1505))

		self.assertEqual("tc", tc.Name)
		self.assertEqual(TestcaseState.Unknown, tc.State)
		self.assertEqual(0, tc.Assertions)
		self.assertEqual(1.505, tc.Time.total_seconds())


class Transformation(ut_TestCase):
	def test_JUnit2Unittesting(self) -> None:
		tss = TestsuiteSummary("tss", timedelta(milliseconds=9831))
		ts1 = Testsuite("ts1", timedelta(milliseconds=4206), parent=tss)
		ts2 = Testsuite("ts2", timedelta(milliseconds=4206), parent=tss)
		tc11 = Testcase("tc11", timedelta(milliseconds=1505), parent=ts1)
		tc12 = Testcase("tc12", timedelta(milliseconds=1505), parent=ts1)
		tc21 = Testcase("tc21", timedelta(milliseconds=1505), parent=ts2)
		tc22 = Testcase("tc22", timedelta(milliseconds=1505), parent=ts2)

		tts = tss.ConvertToGeneric()

		self.assertEqual("tss", tts.Name)
		self.assertEqual("ts1", tts.Testsuites[ts1.Name].Name)
		self.assertEqual("ts2", tts.Testsuites[ts2.Name].Name)
		self.assertEqual("tc11", tts.Testsuites[ts1.Name].Testcases[tc11.Name].Name)
		self.assertEqual("tc12", tts.Testsuites[ts1.Name].Testcases[tc12.Name].Name)
		self.assertEqual("tc21", tts.Testsuites[ts2.Name].Testcases[tc21.Name].Name)
		self.assertEqual("tc22", tts.Testsuites[ts2.Name].Testcases[tc22.Name].Name)


class ExampleFiles(ut_TestCase):
	def test_pytest_pyAttributes(self) -> None:
		print()

		junitExampleFile = Path("tests/data/JUnit/pytest.pyAttributes.xml")
		doc = Document(junitExampleFile)

		print(f"JUnit file:")
		print(f"  Testsuites: {len(doc.Testsuites)}")
		print(f"  Testcases:  ")

		print()
		print(f"Statistics:")
		print(f"  Times: MiniDOM: {doc._readingByMiniDom:.3f}s   convert: {doc._modelConversion:.3f}s")

	def test_OSVVM_Libraries(self) -> None:
		print()

		junitExampleFile = Path("tests/data/JUnit/osvvm.Libraries.xml")
		doc = Document(junitExampleFile)

		print(f"JUnit file:")
		print(f"  Testsuites: {len(doc.Testsuites)}")
		print(f"  Testcases:  ")

		print()
		print(f"Statistics:")
		print(f"  Times: MiniDOM: {doc._readingByMiniDom:.3f}s   convert: {doc._modelConversion:.3f}s")
