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
"""Unit tests of the functional coverage model: the report, covergroups and coverpoints."""
from pyTooling.Exceptions              import AlreadyInHierarchyError, DuplicateElementError
from pyTooling.MetaClasses             import AbstractClassError
from pyTooling.Testing                 import Testcase

from pyEDAA.Reports.FunctionalCoverage import AlreadyInFunctionalCoverageReportError, CoverageItem, Covergroup, \
                                              Coverpoint, DuplicateCoverpointError, FunctionalCoverageError, \
                                              FunctionalCoverageReport


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


class ReportInstantiation(Testcase):
	def test_Report(self) -> None:
		report = FunctionalCoverageReport("TbStream_SendGetRandom1", keyValuePairs={"WritePassFail": 0})

		self.assertEqual("TbStream_SendGetRandom1", report.Name)
		self.assertIsNone(report.Parent)
		self.assertIs(report, report.Root)
		self.assertEqual([], report.Covergroups)
		self.assertEqual(0, report.CovergroupCount)
		self.assertEqual(0, report["WritePassFail"])
		self.assertEqual(
			"<FunctionalCoverageReport TbStream_SendGetRandom1: 0 covergroups>",
			repr(report)
		)

	def test_Name(self) -> None:
		for name, exception, message in (
			(None, ValueError, "Parameter 'name' is None."),
			(1,    TypeError,  "Parameter 'name' is not of type 'str'."),
			("",   ValueError, "Parameter 'name' is empty."),
		):
			with self.subTest(name=name):
				with self.assertRaises(exception) as context:
					_ = FunctionalCoverageReport(name)
				self.assertEqual(message, str(context.exception))

	def test_KeyValuePairs(self) -> None:
		with self.assertRaises(TypeError) as context:
			_ = FunctionalCoverageReport("T", keyValuePairs=[("WritePassFail", 0)])
		self.assertEqual("Parameter 'keyValuePairs' is not a mapping ('dict', ...).", str(context.exception))

	def test_NoParent(self) -> None:
		report = FunctionalCoverageReport("T")

		with self.assertRaises(TypeError) as context:
			report.Parent = FunctionalCoverageReport("U")
		self.assertEqual(
			"A 'pyEDAA.Reports.FunctionalCoverage.FunctionalCoverageReport' has no parent.",
			str(context.exception)
		)


class CovergroupInstantiation(Testcase):
	def test_Covergroup(self) -> None:
		covergroup = Covergroup("DelayCov BurstLength")

		self.assertEqual("DelayCov BurstLength", covergroup.Name)
		self.assertIsNone(covergroup.Parent)
		self.assertIsNone(covergroup.Root)
		self.assertEqual([], covergroup.Testcases)
		self.assertEqual({}, covergroup.Coverpoints)
		self.assertEqual(0, covergroup.CoverpointCount)
		self.assertEqual(
			"<Covergroup DelayCov BurstLength: 0 coverpoints, 0 crosses>",
			repr(covergroup)
		)

	def test_Testcases(self) -> None:
		covergroup = Covergroup(
			"DelayCov BurstLength",
			testcases=["TbStream_SendGetRandom1", "TbStream_SendGetRandom2"],
			keyValuePairs={"Seeds": [56101531, 1187811199]}
		)

		self.assertEqual(["TbStream_SendGetRandom1", "TbStream_SendGetRandom2"], covergroup.Testcases)
		self.assertEqual([56101531, 1187811199], covergroup["Seeds"])

	def test_ParameterChecks(self) -> None:
		for name, testcases, exception, message in (
			(None, None, ValueError, "Parameter 'name' is None."),
			(1,    None, TypeError,  "Parameter 'name' is not of type 'str'."),
			("",   None, ValueError, "Parameter 'name' is empty."),
			("G",  1,    TypeError,  "Parameter 'testcases' is not iterable."),
			("G",  [1],  TypeError,  "Parameter 'testcases' contains an element not of type 'str'."),
		):
			with self.subTest(message=message):
				with self.assertRaises(exception) as context:
					_ = Covergroup(name, testcases=testcases)
				self.assertEqual(message, str(context.exception))

	def test_Parent(self) -> None:
		with self.assertRaises(TypeError) as context:
			_ = Covergroup("G", parent=Covergroup("H"))
		self.assertEqual("Parameter 'parent' is not of type 'FunctionalCoverageReport'.", str(context.exception))
		self.assertEqual(["Got type 'pyEDAA.Reports.FunctionalCoverage.Covergroup'."], context.exception.__notes__)


class CoverpointInstantiation(Testcase):
	def test_Coverpoint(self) -> None:
		coverpoint = Coverpoint("Bin1")

		self.assertEqual("Bin1", coverpoint.Name)
		self.assertIsNone(coverpoint.Expression)
		self.assertIsNone(coverpoint.Parent)
		self.assertIsNone(coverpoint.Root)
		self.assertEqual("<Coverpoint Bin1: 0 bins>", repr(coverpoint))

	def test_Expression(self) -> None:
		coverpoint = Coverpoint("Length", "BurstLength")

		self.assertEqual("BurstLength", coverpoint.Expression)

	def test_ParameterChecks(self) -> None:
		for arguments, exception, message in (
			((None, ),  ValueError, "Parameter 'name' is None."),
			(("P", 1),  TypeError,  "Parameter 'expression' is not of type 'str'."),
			(("P", ""), ValueError, "Parameter 'expression' is empty."),
		):
			with self.subTest(arguments=arguments):
				with self.assertRaises(exception) as context:
					_ = Coverpoint(*arguments)
				self.assertEqual(message, str(context.exception))

	def test_Parent(self) -> None:
		with self.assertRaises(TypeError) as context:
			_ = Coverpoint("P", parent=FunctionalCoverageReport("T"))
		self.assertEqual("Parameter 'parent' is not of type 'Covergroup'.", str(context.exception))

	def test_Abstract(self) -> None:
		with self.assertRaises(AbstractClassError):
			_ = CoverageItem("P")


class KeyValuePairsArgument(Testcase):
	"""``keyValuePairs`` is a positional or keyword argument, as in ``Base``; only ``parent`` is keyword-only."""

	def test_Report(self) -> None:
		report = FunctionalCoverageReport("T", {"WritePassFail": 0})

		self.assertEqual(0, report["WritePassFail"])

	def test_Covergroup(self) -> None:
		covergroup = Covergroup("cg", None, {"Seed": 5})

		self.assertEqual(5, covergroup["Seed"])

	def test_Coverpoint(self) -> None:
		coverpoint = Coverpoint("cp", "addr", {"Weight": 1})

		self.assertEqual(1, coverpoint["Weight"])


class Hierarchy(Testcase):
	def test_Constructors(self) -> None:
		"""Every element joins its parent in its constructor and takes the parent's root."""
		report =     FunctionalCoverageReport("T")
		covergroup = Covergroup("DelayCov BurstLength", parent=report)
		coverpoint = Coverpoint("Bin1", parent=covergroup)

		self.assertEqual([covergroup], report.Covergroups)
		self.assertEqual(1, report.CovergroupCount)
		self.assertEqual({"Bin1": coverpoint}, covergroup.Coverpoints)
		self.assertEqual(1, covergroup.CoverpointCount)

		self.assertIs(report, covergroup.Parent)
		self.assertIs(covergroup, coverpoint.Parent)
		self.assertIs(report, covergroup.Root)
		self.assertIs(report, coverpoint.Root)

	def test_ParentSetter(self) -> None:
		"""A subtree built bottom up joins a report: every element below takes the report's root."""
		coverpoint = Coverpoint("Bin1")
		covergroup = Covergroup("DelayCov BurstLength")
		report =     FunctionalCoverageReport("T")

		coverpoint.Parent = covergroup
		self.assertIsNone(coverpoint.Root)

		covergroup.Parent = report

		self.assertEqual([covergroup], report.Covergroups)
		self.assertEqual({"Bin1": coverpoint}, covergroup.Coverpoints)
		self.assertIs(report, covergroup.Root)
		self.assertIs(report, coverpoint.Root)

	def test_ParentSetter_Checks(self) -> None:
		covergroup = Covergroup("G", parent=FunctionalCoverageReport("T"))

		with self.assertRaises(ValueError) as context:
			covergroup.Parent = None
		self.assertEqual("Parameter 'parent' is None.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			Coverpoint("P").Parent = FunctionalCoverageReport("T")
		self.assertEqual("Parameter 'parent' is not of type 'Covergroup'.", str(context.exception))

		with self.assertRaises(AlreadyInFunctionalCoverageReportError) as context:
			covergroup.Parent = FunctionalCoverageReport("U")
		self.assertEqual("Covergroup already has a parent.", str(context.exception))
		self.assertIsInstance(context.exception, AlreadyInHierarchyError)
		self.assertIsInstance(context.exception, FunctionalCoverageError)

	def test_DuplicateCovergroupNames(self) -> None:
		"""Several instances of a covergroup share its name."""
		report = FunctionalCoverageReport("T")
		first =  Covergroup("DelayCov BurstLength", parent=report)
		second = Covergroup("DelayCov BurstLength", parent=report)

		self.assertEqual([first, second], report.Covergroups)

	def test_DuplicateCoverpoint(self) -> None:
		covergroup = Covergroup("G")
		_ = Coverpoint("P", parent=covergroup)

		with self.assertRaises(DuplicateCoverpointError) as context:
			_ = Coverpoint("P", parent=covergroup)
		self.assertEqual("Covergroup 'G' already contains 'P'.", str(context.exception))
		self.assertIsInstance(context.exception, DuplicateElementError)
		self.assertIsInstance(context.exception, FunctionalCoverageError)

		with self.assertRaises(DuplicateCoverpointError):
			Coverpoint("P").Parent = covergroup

	def test_Iterate(self) -> None:
		report = FunctionalCoverageReport("T")
		length = Covergroup("DelayCov BurstLength", parent=report)
		delay =  Covergroup("DelayCov BurstDelay", parent=report)
		short =  Coverpoint("Short", parent=length)
		long =   Coverpoint("Long", "BurstLength", parent=length)

		self.assertEqual([length, delay], list(report.IterateCovergroups()))
		self.assertEqual([delay], list(report.IterateCovergroups(lambda covergroup: covergroup.Name.endswith("Delay"))))
		self.assertEqual([short, long], list(length.IterateCoverpoints()))
		self.assertEqual([long], list(length.IterateCoverpoints(lambda coverpoint: coverpoint.Expression is not None)))
