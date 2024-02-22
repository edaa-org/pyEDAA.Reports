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
from unittest import TestCase as ut_TestCase

from pyEDAA.Reports.Unittesting import Testcase, Status, Testsuite, DuplicateTestsuiteException, DuplicateTestcaseException


class TestcaseInstantiation(ut_TestCase):
	def test_Testcase_NoName(self) -> None:
		with self.assertRaises(TypeError):
			_ = Testcase(None)

	def test_Testcase_OnlyName(self) -> None:
		tc = Testcase("test")

		self.assertEqual("test", tc.Name)
		self.assertEqual(Status.Unknown, tc.Status)

	def test_Testcase_WithAssertionCounts(self) -> None:
		tc = Testcase("test", assertionCount=5, failedAssertionCount=1, passedAssertionCount=4)

		self.assertEqual("test", tc.Name)
		self.assertEqual(Status.Unknown, tc.Status)
		self.assertEqual(5, tc.AssertionCount)
		self.assertEqual(1, tc.FailedAssertionCount)
		self.assertEqual(4, tc.PassedAssertionCount)

	def test_Testcase_WithErrorCounts(self) -> None:
		tc = Testcase("test", warningCount=1, errorCount=2, fatalCount=3)

		self.assertEqual("test", tc.Name)
		self.assertEqual(Status.Unknown, tc.Status)
		self.assertEqual(1, tc.WarningCount)
		self.assertEqual(2, tc.ErrorCount)
		self.assertEqual(3, tc.FatalCount)

	def test_Testcase_WithWrongCounts(self) -> None:
		with self.assertRaises(ValueError):
			_ = Testcase("test", assertionCount=5, failedAssertionCount=2, passedAssertionCount=4)

	def test_Testcase_OnlyAssertionCount(self) -> None:
		with self.assertRaises(ValueError):
			_ = Testcase("test", assertionCount=5)

	def test_Testcase_OnlyFailedAssertionCount(self) -> None:
		with self.assertRaises(ValueError):
			_ = Testcase("test", failedAssertionCount=1)

	def test_Testcase_OnlyPassedAssertionCount(self) -> None:
		with self.assertRaises(ValueError):
			_ = Testcase("test", passedAssertionCount=4)

	def test_Testcase_NoFailedAssertionCount(self) -> None:
		tc = Testcase("test", assertionCount=5, passedAssertionCount=4)

		self.assertEqual("test", tc.Name)
		self.assertEqual(Status.Unknown, tc.Status)
		self.assertEqual(5, tc.AssertionCount)
		self.assertEqual(1, tc.FailedAssertionCount)
		self.assertEqual(4, tc.PassedAssertionCount)

	def test_Testcase_NoPassedAssertionCount(self) -> None:
		tc = Testcase("test", assertionCount=5, failedAssertionCount=1)

		self.assertEqual("test", tc.Name)
		self.assertEqual(Status.Unknown, tc.Status)
		self.assertEqual(5, tc.AssertionCount)
		self.assertEqual(1, tc.FailedAssertionCount)
		self.assertEqual(4, tc.PassedAssertionCount)

	def test_Testcase_NoAssertionCount(self) -> None:
		tc = Testcase("test", failedAssertionCount=1, passedAssertionCount=4)

		self.assertEqual("test", tc.Name)
		self.assertEqual(Status.Unknown, tc.Status)
		self.assertEqual(5, tc.AssertionCount)
		self.assertEqual(1, tc.FailedAssertionCount)
		self.assertEqual(4, tc.PassedAssertionCount)


class TestsuiteInstantiation(ut_TestCase):
	def test_Testsuite_NoName(self) -> None:
		with self.assertRaises(TypeError):
			_ = Testsuite(None)

	def test_Testsuite_OnlyName(self) -> None:
		ts = Testsuite("test")

		self.assertEqual("test", ts.Name)
		self.assertEqual(Status.Unknown, ts.Status)


class Hierarchy(ut_TestCase):
	def test_Testsuites(self) -> None:
		ts1 = Testsuite("ts1")
		ts2 = Testsuite("ts2")

		ts = Testsuite("root", testsuites=(ts1, ts2))

		self.assertIsNone(ts.Parent)
		self.assertEqual(2, len(ts.Testsuites))
		self.assertEqual(0, len(ts.Testcases))

		self.assertEqual(ts1, ts.Testsuites["ts1"])
		self.assertEqual(ts2, ts.Testsuites["ts2"])
		self.assertEqual(ts, ts1.Parent)
		self.assertEqual(ts, ts2.Parent)

	def test_Testcases(self) -> None:
		tc1 = Testcase("tc1")
		tc2 = Testcase("tc2")

		ts = Testsuite("root", testcases=(tc1, tc2))

		self.assertIsNone(ts.Parent)
		self.assertEqual(0, len(ts.Testsuites))
		self.assertEqual(2, len(ts.Testcases))

		self.assertEqual(tc1, ts.Testcases["tc1"])
		self.assertEqual(tc2, ts.Testcases["tc2"])
		self.assertEqual(ts, tc1.Parent)
		self.assertEqual(ts, tc2.Parent)

	def test_AddTestsuite(self) -> None:
		ts = Testsuite("root")
		ts1 = Testsuite("ts1")

		self.assertIsNone(ts.Parent)
		self.assertEqual(0, len(ts.Testsuites))
		self.assertEqual(0, len(ts.Testcases))

		ts.AddTestsuite(ts1)

		self.assertEqual(1, len(ts.Testsuites))
		self.assertEqual(0, len(ts.Testcases))
		self.assertEqual(ts1, ts.Testsuites["ts1"])
		self.assertEqual(ts, ts1.Parent)

	def test_AddTestsuites(self) -> None:
		ts = Testsuite("root")
		ts1 = Testsuite("ts1")
		ts2 = Testsuite("ts2")
		tss = (ts1, ts2)

		self.assertIsNone(ts.Parent)
		self.assertEqual(0, len(ts.Testsuites))
		self.assertEqual(0, len(ts.Testcases))

		ts.AddTestsuites(tss)

		self.assertEqual(2, len(ts.Testsuites))
		self.assertEqual(0, len(ts.Testcases))
		self.assertEqual(ts1, ts.Testsuites["ts1"])
		self.assertEqual(ts2, ts.Testsuites["ts2"])
		self.assertEqual(ts, ts1.Parent)
		self.assertEqual(ts, ts2.Parent)

	def test_AddTestcase(self) -> None:
		ts = Testsuite("root")
		tc1 = Testcase("tc1")

		self.assertIsNone(ts.Parent)
		self.assertEqual(0, len(ts.Testsuites))
		self.assertEqual(0, len(ts.Testcases))

		ts.AddTestcase(tc1)

		self.assertEqual(0, len(ts.Testsuites))
		self.assertEqual(1, len(ts.Testcases))
		self.assertEqual(tc1, ts.Testcases["tc1"])
		self.assertEqual(ts, tc1.Parent)

	def test_AddTestcases(self) -> None:
		ts = Testsuite("root")
		tc1 = Testcase("tc1")
		tc2 = Testcase("tc2")
		tcs = (tc1, tc2)

		self.assertIsNone(ts.Parent)
		self.assertEqual(0, len(ts.Testsuites))
		self.assertEqual(0, len(ts.Testcases))

		ts.AddTestcases(tcs)

		self.assertEqual(0, len(ts.Testsuites))
		self.assertEqual(2, len(ts.Testcases))

		self.assertEqual(tc1, ts.Testcases["tc1"])
		self.assertEqual(tc2, ts.Testcases["tc2"])
		self.assertEqual(ts, tc1.Parent)
		self.assertEqual(ts, tc2.Parent)


class Duplicates(ut_TestCase):
	def test_DuplicateTestsuite(self) -> None:
		ts = Testsuite("root")

		ts1 = Testsuite("ts1")
		ts2 = Testsuite("ts1")

		ts.AddTestsuite(ts1)
		with self.assertRaises(DuplicateTestsuiteException):
			ts.AddTestsuite(ts2)

	def test_DuplicateTestsuites(self) -> None:
		ts1 = Testsuite("ts1")
		ts2 = Testsuite("ts1")

		with self.assertRaises(DuplicateTestsuiteException):
			_ = Testsuite("root", testsuites=(ts1, ts2))

	def test_DuplicateTestcase(self) -> None:
		ts = Testsuite("root")

		tc1 = Testcase("tc1")
		tc2 = Testcase("tc1")

		ts.AddTestcase(tc1)
		with self.assertRaises(DuplicateTestcaseException):
			ts.AddTestcase(tc2)

	def test_DuplicateTestcases(self) -> None:
		tc1 = Testcase("tc1")
		tc2 = Testcase("tc1")

		with self.assertRaises(DuplicateTestcaseException):
			_ = Testsuite("root", testcases=(tc1, tc2))


class Aggregate(ut_TestCase):
	def test_AggregateAssertions(self) -> None:
		tc1 = Testcase("tc1", 5, 1, 4)
		tc2 = Testcase("tc2", 10, 0, 10)
		ts = Testsuite("root", testcases=(tc1, tc2))

		ts.Aggregate()

