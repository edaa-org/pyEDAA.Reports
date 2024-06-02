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

from pyEDAA.Reports.Unittesting import DuplicateTestsuiteException, DuplicateTestcaseException, TestsuiteStatus
from pyEDAA.Reports.Unittesting import TestcaseStatus, Testcase, Testsuite, TestsuiteSummary, IterationScheme


class TestcaseInstantiation(ut_TestCase):
	def test_Testcase_NoName(self) -> None:
		with self.assertRaises(ValueError):
			_ = Testcase(None)

	def test_Testcase_OnlyName(self) -> None:
		tc = Testcase("test")

		self.assertEqual("test", tc.Name)
		self.assertEqual(TestcaseStatus.Unknown, tc.Status)

	def test_Testcase_WithAssertionCounts(self) -> None:
		tc = Testcase("test", assertionCount=5, failedAssertionCount=1, passedAssertionCount=4)

		self.assertEqual("test", tc.Name)
		self.assertEqual(TestcaseStatus.Unknown, tc.Status)
		self.assertEqual(5, tc.AssertionCount)
		self.assertEqual(1, tc.FailedAssertionCount)
		self.assertEqual(4, tc.PassedAssertionCount)

	def test_Testcase_WithErrorCounts(self) -> None:
		tc = Testcase("test", warningCount=1, errorCount=2, fatalCount=3)

		self.assertEqual("test", tc.Name)
		self.assertEqual(TestcaseStatus.Unknown, tc.Status)
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
		self.assertEqual(TestcaseStatus.Unknown, tc.Status)
		self.assertEqual(5, tc.AssertionCount)
		self.assertEqual(1, tc.FailedAssertionCount)
		self.assertEqual(4, tc.PassedAssertionCount)

	def test_Testcase_NoPassedAssertionCount(self) -> None:
		tc = Testcase("test", assertionCount=5, failedAssertionCount=1)

		self.assertEqual("test", tc.Name)
		self.assertEqual(TestcaseStatus.Unknown, tc.Status)
		self.assertEqual(5, tc.AssertionCount)
		self.assertEqual(1, tc.FailedAssertionCount)
		self.assertEqual(4, tc.PassedAssertionCount)

	def test_Testcase_NoAssertionCount(self) -> None:
		tc = Testcase("test", failedAssertionCount=1, passedAssertionCount=4)

		self.assertEqual("test", tc.Name)
		self.assertEqual(TestcaseStatus.Unknown, tc.Status)
		self.assertEqual(5, tc.AssertionCount)
		self.assertEqual(1, tc.FailedAssertionCount)
		self.assertEqual(4, tc.PassedAssertionCount)


class TestsuiteInstantiation(ut_TestCase):
	def test_Testsuite_NoName(self) -> None:
		with self.assertRaises(ValueError):
			_ = Testsuite(None)

	def test_Testsuite_OnlyName(self) -> None:
		ts = Testsuite("test")

		self.assertEqual("test", ts.Name)
		self.assertEqual(TestsuiteStatus.Unknown, ts.Status)


class Hierarchy(ut_TestCase):
	def test_TestsuiteParentIsTestsuite(self) -> None:
		ts1 = Testsuite("ts1")
		ts2 = Testcase("ts2", parent=ts1)

		self.assertEqual(ts1, ts2.Parent)
		self.assertEqual(ts2, ts1.Testcases["ts2"])

	def test_TestsuitesInTestsuite(self) -> None:
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

	def test_TestcaseParentIsTestcase(self) -> None:
		tc1 = Testcase("tc1")

		with self.assertRaises(TypeError):
			_ = Testcase("tc2", parent=tc1)

	def test_TestcaseParentIsTestsuite(self) -> None:
		ts = Testsuite("ts")
		tc1 = Testcase("tc1", parent=ts)

		self.assertEqual(ts, tc1.Parent)
		self.assertEqual(tc1, ts.Testcases["tc1"])

	def test_TestcasesInTestsuite(self) -> None:
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


class TestsuiteSummaryInstantiation(ut_TestCase):
	def test_TestsuiteSummary_NoName(self) -> None:
		with self.assertRaises(ValueError):
			_ = TestsuiteSummary(None)


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
		tc1 = Testcase("tc1", assertionCount=5, failedAssertionCount=1, passedAssertionCount=4)
		tc2 = Testcase("tc2", assertionCount=10, failedAssertionCount=0, passedAssertionCount=10)
		ts = Testsuite("root", testcases=(tc1, tc2))

		ts.Aggregate()


def CreateTestsuiteStructure(rootIsSummary: bool = True, empty: bool = False) -> Testsuite:
	if rootIsSummary:
		root = TestsuiteSummary("summary")
	else:
		root = Testsuite("root")

	ts1 = Testsuite("ts1", parent=root)
	ts11 = Testsuite("ts11", parent=ts1)
	ts12 = Testsuite("ts12", parent=ts1)
	ts2 = Testsuite("ts2", parent=root)
	ts21 = Testsuite("ts21", parent=ts2)
	ts211 = Testsuite("ts211", parent=ts21)
	ts212 = Testsuite("ts212", parent=ts21)
	ts213 = Testsuite("ts213", parent=ts21)
	ts3 = Testsuite("ts3", parent=root)

	if not rootIsSummary:
		tc1 = Testcase("tc1", parent=root)
		tc2 = Testcase("tc2", parent=root)
	tc11 = Testcase("tc11", parent=ts1)
	tc12 = Testcase("tc12", parent=ts1)
	tc111 = Testcase("tc111", parent=ts11)
	tc112 = Testcase("tc112", parent=ts11)
	tc121 = Testcase("tc121", parent=ts12)
	tc122 = Testcase("tc122", parent=ts12)
	tc123 = Testcase("tc123", parent=ts12)
	if not empty:
		tc211 = Testcase("tc211", parent=ts21)
	tc2111 = Testcase("tc2111", parent=ts211)
	tc2112 = Testcase("tc2112", parent=ts211)
	tc2113 = Testcase("tc2113", parent=ts211)
	tc2114 = Testcase("tc2114", parent=ts211)
	if not empty:
		tc2121 = Testcase("tc2121", parent=ts212)
		tc2122 = Testcase("tc2122", parent=ts212)
	tc2131 = Testcase("tc2131", parent=ts213)
	tc2132 = Testcase("tc2132", parent=ts213)
	if not empty:
		tc31 = Testcase("tc31", parent=ts3)
		tc32 = Testcase("tc32", parent=ts3)

	return root


class Iterator(ut_TestCase):
	def test_Testsuite_Iterate(self) -> None:
		root = CreateTestsuiteStructure(rootIsSummary=False)

		expectedPreOrder =  ["tc1", "tc2", "ts1", "tc11", "tc12", "ts11", "tc111", "tc112", "ts12", "tc121", "tc122", "tc123", "ts2", "ts21", "tc211", "ts211", "tc2111", "tc2112", "tc2113", "tc2114", "ts212", "tc2121", "tc2122", "ts213", "tc2131", "tc2132", "ts3", "tc31", "tc32"]
		expectedPostOrder = ["tc111", "tc112", "ts11", "tc121", "tc122", "tc123", "ts12", "tc11", "tc12", "ts1", "tc2111", "tc2112", "tc2113", "tc2114", "ts211", "tc2121", "tc2122", "ts212", "tc2131", "tc2132", "ts213", "tc211", "ts21", "ts2", "tc31", "tc32", "ts3", "tc1", "tc2"]

		self.assertListEqual(
			expectedPreOrder,
			[ts.Name for ts in root.Iterate()]
		)
		self.assertListEqual(
			expectedPreOrder,
			[ts.Name for ts in root.Iterate(IterationScheme.Default)]
		)
		self.assertListEqual(
			["root"] + expectedPreOrder,
			[ts.Name for ts in root.Iterate(IterationScheme.Default | IterationScheme.IncludeSelf)]
		)
		self.assertListEqual(
			expectedPostOrder,
			[ts.Name for ts in root.Iterate(IterationScheme.IncludeTestsuites | IterationScheme.IncludeTestcases | IterationScheme.PostOrder)]
		)

	def test_Testsuite_IterateTestsuites(self) -> None:
		root = CreateTestsuiteStructure(rootIsSummary=False)

		expectedPreorder =  ["ts1", "ts11", "ts12", "ts2", "ts21", "ts211", "ts212", "ts213", "ts3"]
		expectedPostOrder = ["ts11", "ts12", "ts1", "ts211", "ts212", "ts213", "ts21", "ts2", "ts3"]

		self.assertListEqual(
			expectedPreorder,
			[ts.Name for ts in root.IterateTestsuites()]
		)
		self.assertListEqual(
			expectedPreorder,
			[ts.Name for ts in root.IterateTestsuites(IterationScheme.TestsuiteDefault)]
		)
		self.assertListEqual(
			["root"] + expectedPreorder,
			[ts.Name for ts in root.IterateTestsuites(IterationScheme.TestsuiteDefault | IterationScheme.IncludeSelf)]
		)
		self.assertListEqual(
			expectedPostOrder,
			[ts.Name for ts in root.IterateTestsuites(IterationScheme.IncludeTestsuites | IterationScheme.PostOrder)]
		)

	def test_Testsuite_IterateTestcases(self) -> None:
		root = CreateTestsuiteStructure(rootIsSummary=False)

		expectedPreOrder =  ["tc1", "tc2", "tc11", "tc12", "tc111", "tc112", "tc121", "tc122", "tc123", "tc211", "tc2111", "tc2112", "tc2113", "tc2114", "tc2121", "tc2122", "tc2131", "tc2132", "tc31", "tc32"]
		expectedPostOrder = ["tc111", "tc112", "tc121", "tc122", "tc123", "tc11", "tc12", "tc2111", "tc2112", "tc2113", "tc2114", "tc2121", "tc2122", "tc2131", "tc2132", "tc211", "tc31", "tc32", "tc1", "tc2"]

		self.assertListEqual(
			expectedPreOrder,
			[ts.Name for ts in root.IterateTestcases()]
		)
		self.assertListEqual(
			expectedPreOrder,
			[ts.Name for ts in root.IterateTestcases(IterationScheme.TestcaseDefault)]
		)
		self.assertListEqual(
			expectedPreOrder,
			[ts.Name for ts in root.IterateTestcases(IterationScheme.TestcaseDefault | IterationScheme.IncludeSelf)]
		)
		self.assertListEqual(
			expectedPostOrder,
			[ts.Name for ts in root.IterateTestcases(IterationScheme.IncludeTestcases | IterationScheme.PostOrder)]
		)
