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
"""Unit tests of the functional coverage model: crosses and cross bins."""
from pyTooling.Exceptions              import DuplicateElementError
from pyTooling.Testing                 import Testcase

from pyEDAA.Reports.FunctionalCoverage import BinKind, Covergroup, Coverpoint, Cross, CrossBin, \
                                              DuplicateCoverpointError, DuplicateCrossError, FunctionalCoverageError, \
                                              FunctionalCoverageReport, ValueRange


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


class CrossInstantiation(Testcase):
	def test_Cross(self) -> None:
		cross = Cross("DelayCov BurstDelay", ["Bin1", "Bin2"])

		self.assertEqual("DelayCov BurstDelay", cross.Name)
		self.assertEqual(["Bin1", "Bin2"], cross.CrossedItems)
		self.assertEqual(2, cross.Dimensions)
		self.assertIsNone(cross.Parent)
		self.assertIsNone(cross.Root)
		self.assertEqual([], cross.Bins)
		self.assertEqual("<Cross DelayCov BurstDelay: 0/0 bins, hits 100.0%>", repr(cross))

	def test_ParameterChecks(self) -> None:
		for arguments, exception, message in (
			((None, ["a", "b"]), ValueError, "Parameter 'name' is None."),
			(("X",  None),       ValueError, "Parameter 'crossedItems' is None."),
			(("X",  1),          TypeError,  "Parameter 'crossedItems' is not iterable."),
			(("X",  ["a", 1]),   TypeError,  "Parameter 'crossedItems' contains an element not of type 'str'."),
			(("X",  ["a", ""]),  ValueError, "Parameter 'crossedItems' contains an empty name."),
			(("X",  ["a"]),      ValueError, "Parameter 'crossedItems' contains less than two names."),
		):
			with self.subTest(arguments=arguments):
				with self.assertRaises(exception) as context:
					_ = Cross(*arguments)
				self.assertEqual(message, str(context.exception))

	def test_Parent(self) -> None:
		with self.assertRaises(TypeError) as context:
			_ = Cross("X", ["a", "b"], parent=Coverpoint("P"))
		self.assertEqual("Parameter 'parent' is not of type 'Covergroup'.", str(context.exception))


class CrossBinInstantiation(Testcase):
	def test_CrossBin(self) -> None:
		crossBin = CrossBin(None, BinKind.Count, [[ValueRange(0, 0)], [ValueRange(2, 8)]], 13, 65)

		self.assertIsNone(crossBin.Name)
		self.assertIs(BinKind.Count, crossBin.Kind)
		self.assertEqual([(ValueRange(0, 0), ), (ValueRange(2, 8), )], crossBin.Ranges)
		self.assertEqual(13, crossBin.Count)
		self.assertEqual(65, crossBin.AtLeast)
		self.assertIsNone(crossBin.Parent)
		self.assertEqual("<CrossBin (unnamed) Count: 13/65>", repr(crossBin))

	def test_SeveralRanges(self) -> None:
		"""A crossed item's values are several ranges, as a SystemVerilog bin of several ranges has them."""
		ranges =   ([ValueRange(0, 1), ValueRange(6, 7)], [ValueRange(0, 0)])
		crossBin = CrossBin("lowOrHigh", BinKind.Illegal, ranges, 0, 0)

		self.assertEqual([(ValueRange(0, 1), ValueRange(6, 7)), (ValueRange(0, 0), )], crossBin.Ranges)

	def test_ParameterChecks(self) -> None:
		count =  BinKind.Count
		single = ValueRange(0, 0)
		for arguments, exception, message in (
			((None, count, None,       0),  ValueError, "Parameter 'ranges' is None."),
			((None, count, 1,          0),  TypeError,  "Parameter 'ranges' is not iterable."),
			((None, count, [single],   0),  TypeError,  "Parameter 'ranges' contains an element, which isn't iterable."),
			((None, count, [[(0, 0)]], 0),  TypeError,  "Parameter 'ranges' contains a range not of type 'ValueRange'."),
			((None, count, [[single]], -1), ValueError, "Parameter 'count' is negative."),
		):
			with self.subTest(arguments=arguments):
				with self.assertRaises(exception) as context:
					_ = CrossBin(*arguments)
				self.assertEqual(message, str(context.exception))

	def test_Parent(self) -> None:
		with self.assertRaises(TypeError) as context:
			_ = CrossBin(None, BinKind.Count, [], 0, parent=Coverpoint("P"))
		self.assertEqual("Parameter 'parent' is not of type 'Cross'.", str(context.exception))


class CrossHierarchy(Testcase):
	def test_Constructors(self) -> None:
		report =     FunctionalCoverageReport("T")
		covergroup = Covergroup("DelayCov BurstDelay", parent=report)
		cross =      Cross("DelayCov BurstDelay", ["Bin1", "Bin2"], parent=covergroup)
		crossBin =   CrossBin(None, BinKind.Count, [[ValueRange(0, 0)], [ValueRange(2, 8)]], 13, 65, parent=cross)

		self.assertEqual({"DelayCov BurstDelay": cross}, covergroup.Crosses)
		self.assertEqual(1, covergroup.CrossCount)
		self.assertEqual(0, covergroup.CoverpointCount)
		self.assertEqual([crossBin], cross.Bins)
		self.assertIs(covergroup, cross.Parent)
		self.assertIs(cross, crossBin.Parent)
		self.assertIs(report, cross.Root)
		self.assertIs(report, crossBin.Root)

	def test_ParentSetter(self) -> None:
		crossBin =   CrossBin(None, BinKind.Count, [[ValueRange(0, 0)], [ValueRange(2, 8)]], 13, 65)
		cross =      Cross("X", ["Bin1", "Bin2"])
		covergroup = Covergroup("G")
		report =     FunctionalCoverageReport("T")

		crossBin.Parent =   cross
		cross.Parent =      covergroup
		covergroup.Parent = report

		self.assertEqual([crossBin], cross.Bins)
		self.assertIs(report, cross.Root)
		self.assertIs(report, crossBin.Root)

	def test_Dimensions(self) -> None:
		"""A cross bin has one set of ranges per crossed item."""
		cross = Cross("X", ["Bin1", "Bin2"])

		with self.assertRaises(FunctionalCoverageError) as context:
			_ = CrossBin(None, BinKind.Count, [[ValueRange(0, 0)]], 13, 65, parent=cross)
		self.assertEqual("Bin has not one set of ranges per crossed item of cross 'X'.", str(context.exception))
		self.assertEqual(["Got 1 sets of ranges for 2 crossed items."], context.exception.__notes__)
		self.assertIsInstance(context.exception.__cause__, ValueError)

		crossBin = CrossBin(None, BinKind.Count, [[ValueRange(0, 0)]] * 3, 13, 65)
		with self.assertRaises(FunctionalCoverageError):
			crossBin.Parent = cross

		self.assertEqual([], cross.Bins)
		self.assertIsNone(crossBin.Parent)

	def test_SharedNamespace(self) -> None:
		"""Coverpoints and crosses of a covergroup share one namespace."""
		covergroup = Covergroup("G")
		_ = Coverpoint("A", parent=covergroup)
		_ = Cross("AxB", ["A", "B"], parent=covergroup)

		with self.assertRaises(DuplicateCrossError) as context:
			_ = Cross("A", ["A", "B"], parent=covergroup)
		self.assertEqual("Covergroup 'G' already contains 'A'.", str(context.exception))
		self.assertIsInstance(context.exception, DuplicateElementError)

		with self.assertRaises(DuplicateCoverpointError) as context:
			_ = Coverpoint("AxB", parent=covergroup)
		self.assertEqual("Covergroup 'G' already contains 'AxB'.", str(context.exception))

	def test_Iterate(self) -> None:
		covergroup = Covergroup("G")
		first =      Cross("AxB", ["A", "B"], parent=covergroup)
		second =     Cross("AxBxC", ["A", "B", "C"], parent=covergroup)

		self.assertEqual([first, second], list(covergroup.IterateCrosses()))
		self.assertEqual([second], list(covergroup.IterateCrosses(lambda cross: cross.Dimensions == 3)))
