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
"""Unit tests of the functional coverage model: counters, weights, and the bin and hit coverage."""
from pyTooling.Testing                 import Testcase

from pyEDAA.Reports.FunctionalCoverage import BinKind, Covergroup, Coverpoint, CoverpointBin, Cross, CrossBin, \
                                              FunctionalCoverageReport, ValueRange


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


def CreateOSVVMReport(weight: int) -> FunctionalCoverageReport:
	"""
	Create a report of three OSVVM coverage models of ``TbStream_SendGetRandom1``, each of the same weight.

	:param weight: The weight of each covergroup.
	:returns:      The aggregated report.
	"""
	report = FunctionalCoverageReport("TbStream_SendGetRandom1")

	length = Coverpoint("Bin1", parent=Covergroup("DelayCov BurstLength", weight, parent=report))
	for valueRange, count, atLeast in (
		(ValueRange(3, 11),   19, 80),
		(ValueRange(109, 131), 3, 20)
	):
		_ = CoverpointBin(None, BinKind.Count, [valueRange], count, atLeast, parent=length)

	beat = Coverpoint("Bin1", parent=Covergroup("DelayCov BeatDelay", weight, parent=report))
	for valueRange, count, atLeast in (
		(ValueRange(0, 0), 414, 85),
		(ValueRange(1, 1),  49, 10),
		(ValueRange(2, 2),  27,  5)
	):
		_ = CoverpointBin(None, BinKind.Count, [valueRange], count, atLeast, parent=beat)

	delayGroup = Covergroup("DelayCov BurstDelay", weight, parent=report)
	delay =      Cross("DelayCov BurstDelay", ["Bin1", "Bin2"], parent=delayGroup)
	for first, second, count, atLeast in (
		(ValueRange(0, 0), ValueRange(2, 8),     13, 65),
		(ValueRange(0, 0), ValueRange(108, 156),  3, 10),
		(ValueRange(1, 1), ValueRange(2, 8),      3, 15),
		(ValueRange(1, 1), ValueRange(108, 156),  2, 10)
	):
		_ = CrossBin(None, BinKind.Count, [[first], [second]], count, atLeast, parent=delay)

	report.Aggregate()
	return report


class WeightsAndGoals(Testcase):
	def test_Covergroup(self) -> None:
		covergroup = Covergroup("DelayCov BurstLength")
		self.assertEqual(1, covergroup.Weight)
		self.assertEqual(100.0, covergroup.Goal)

		covergroup = Covergroup("DelayCov BurstLength", 0, 50, ["TbStream_SendGetRandom1"])
		self.assertEqual(0, covergroup.Weight)
		self.assertIsInstance(covergroup.Goal, float)
		self.assertEqual(50.0, covergroup.Goal)
		self.assertEqual(["TbStream_SendGetRandom1"], covergroup.Testcases)

	def test_Coverpoint(self) -> None:
		coverpoint = Coverpoint("Length")
		self.assertEqual(1, coverpoint.Weight)
		self.assertEqual(100.0, coverpoint.Goal)

		coverpoint = Coverpoint("Length", "BurstLength", 2, 90)
		self.assertEqual(2, coverpoint.Weight)
		self.assertIsInstance(coverpoint.Goal, float)
		self.assertEqual(90.0, coverpoint.Goal)

	def test_Cross(self) -> None:
		cross = Cross("X", ["a", "b"])
		self.assertEqual(1, cross.Weight)
		self.assertEqual(100.0, cross.Goal)

		cross = Cross("X", ["a", "b"], 3, 75.5)
		self.assertEqual(3, cross.Weight)
		self.assertEqual(75.5, cross.Goal)

	def test_ParameterChecks(self) -> None:
		for weight, goal, exception, message in (
			(None, 100.0, ValueError, "Parameter 'weight' is None."),
			(1.0,  100.0, TypeError,  "Parameter 'weight' is not of type 'int'."),
			(True, 100.0, TypeError,  "Parameter 'weight' is not of type 'int'."),
			(-1,   100.0, ValueError, "Parameter 'weight' is negative."),
			(1,    None,  ValueError, "Parameter 'goal' is None."),
			(1,    "100", TypeError,  "Parameter 'goal' is not of type 'float' or 'int'."),
			(1,    False, TypeError,  "Parameter 'goal' is not of type 'float' or 'int'."),
			(1,    -0.5,  ValueError, "Parameter 'goal' is negative."),
		):
			with self.subTest(message=message):
				with self.assertRaises(exception) as context:
					_ = Covergroup("G", weight, goal)
				self.assertEqual(message, str(context.exception))

	def test_ParameterChecks_CoverageItems(self) -> None:
		"""Coverpoints and crosses check their weight and goal as covergroups do."""
		with self.assertRaises(ValueError) as context:
			_ = Coverpoint("P", None, -1)
		self.assertEqual("Parameter 'weight' is negative.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = Cross("X", ["a", "b"], 1, "100")
		self.assertEqual("Parameter 'goal' is not of type 'float' or 'int'.", str(context.exception))


class Bins(Testcase):
	def test_IsCovered(self) -> None:
		self.assertTrue(CoverpointBin(None, BinKind.Count, [ValueRange(0, 0)], 85, 85).IsCovered)
		self.assertTrue(CoverpointBin(None, BinKind.Count, [ValueRange(0, 0)], 0, 0).IsCovered)
		self.assertFalse(CoverpointBin(None, BinKind.Count, [ValueRange(0, 0)], 84, 85).IsCovered)
		self.assertFalse(CrossBin(None, BinKind.Count, [[ValueRange(0, 0)], [ValueRange(2, 8)]], 13, 65).IsCovered)

		for kind in (BinKind.Ignore, BinKind.Illegal, BinKind.Default):
			with self.subTest(kind=kind):
				self.assertFalse(CoverpointBin(None, kind, [], 5, 0).IsCovered)


class CoverageItems(Testcase):
	def test_Coverpoint(self) -> None:
		coverpoint = Coverpoint("Bin1")
		for count, atLeast in ((19, 80), (3, 20), (25, 20)):
			_ = CoverpointBin(None, BinKind.Count, [ValueRange(0, 0)], count, atLeast, parent=coverpoint)
		coverpoint.Aggregate()

		self.assertEqual(3, coverpoint.BinCount)
		self.assertEqual(1, coverpoint.CoveredBinCount)
		self.assertEqual(2, coverpoint.MissingBinCount)
		self.assertEqual(19 + 3 + 20, coverpoint.HitCount)
		self.assertEqual(120, coverpoint.RequiredHitCount)
		self.assertAlmostEqual(1 / 3, coverpoint.BinCoverage)
		self.assertAlmostEqual(42 / 120, coverpoint.HitCoverage)
		self.assertEqual("<Coverpoint Bin1: 1/3 bins, hits 35.0%>", repr(coverpoint))

	def test_Kinds(self) -> None:
		"""Ignored, illegal and default bins don't count toward the coverage; illegal hits are counted."""
		coverpoint = Coverpoint("Opcode")
		_ = CoverpointBin("valid",   BinKind.Count,   [ValueRange(0, 3)], 4, 2, parent=coverpoint)
		_ = CoverpointBin("nop",     BinKind.Ignore,  [ValueRange(4, 4)], 9, 0, parent=coverpoint)
		_ = CoverpointBin("invalid", BinKind.Illegal, [ValueRange(5, 6)], 2, 0, parent=coverpoint)
		_ = CoverpointBin("reserve", BinKind.Illegal, [ValueRange(7, 7)], 1, 0, parent=coverpoint)
		_ = CoverpointBin("others",  BinKind.Default, [],                 3, 0, parent=coverpoint)
		coverpoint.Aggregate()

		self.assertEqual(1, coverpoint.BinCount)
		self.assertEqual(1, coverpoint.CoveredBinCount)
		self.assertEqual(1, coverpoint.IgnoreBinCount)
		self.assertEqual(2, coverpoint.IllegalBinCount)
		self.assertEqual(1, coverpoint.DefaultBinCount)
		self.assertEqual(3, coverpoint.IllegalHitCount)
		self.assertEqual(2, coverpoint.HitCount)
		self.assertEqual(2, coverpoint.RequiredHitCount)
		self.assertEqual(1.0, coverpoint.BinCoverage)
		self.assertEqual(1.0, coverpoint.HitCoverage)

	def test_NothingToCover(self) -> None:
		coverpoint = Coverpoint("Opcode")
		_ = CoverpointBin("nop", BinKind.Ignore, [ValueRange(4, 4)], 0, 0, parent=coverpoint)
		coverpoint.Aggregate()

		self.assertEqual(0, coverpoint.BinCount)
		self.assertEqual(1.0, coverpoint.BinCoverage)
		self.assertEqual(1.0, coverpoint.HitCoverage)

	def test_Reaggregate(self) -> None:
		"""Aggregating again starts from zero."""
		coverpoint = Coverpoint("Bin1")
		_ = CoverpointBin(None, BinKind.Count, [ValueRange(0, 0)], 0, 1, parent=coverpoint)
		coverpoint.Aggregate()
		coverpoint.Aggregate()

		self.assertEqual(1, coverpoint.BinCount)
		self.assertEqual(0.0, coverpoint.BinCoverage)


class Covergroups(Testcase):
	def test_Weights(self) -> None:
		"""A covergroup's coverage is the mean of its coverage items' coverage, weighted by their weights."""
		covergroup = Covergroup("G")
		first =      Coverpoint("A", weight=2, parent=covergroup)
		second =     Coverpoint("B", parent=covergroup)
		excluded =   Coverpoint("C", weight=0, parent=covergroup)
		_ = CoverpointBin(None, BinKind.Count, [ValueRange(0, 0)], 1, 1, parent=first)
		_ = CoverpointBin(None, BinKind.Count, [ValueRange(1, 1)], 0, 1, parent=first)
		_ = CoverpointBin(None, BinKind.Count, [ValueRange(0, 0)], 3, 2, parent=second)
		_ = CoverpointBin(None, BinKind.Count, [ValueRange(0, 0)], 0, 5, parent=excluded)
		covergroup.Aggregate()

		self.assertEqual(4, covergroup.BinCount)
		self.assertEqual(2, covergroup.CoveredBinCount)
		self.assertEqual(2 * 1 + 1 * 2 + 0 * 0, covergroup.HitCount)
		self.assertEqual(2 * 2 + 1 * 2 + 0 * 5, covergroup.RequiredHitCount)
		self.assertAlmostEqual((2 * 0.5 + 1 * 1.0) / 3, covergroup.BinCoverage)
		self.assertAlmostEqual(4 / 6, covergroup.HitCoverage)
		self.assertEqual("<Covergroup G: 3 coverpoints, 0 crosses, bins 66.7%, hits 66.7%>", repr(covergroup))

	def test_ZeroWeights(self) -> None:
		"""Coverage items all excluded by weight 0 leave nothing to cover."""
		covergroup = Covergroup("G")
		coverpoint = Coverpoint("A", weight=0, parent=covergroup)
		_ = CoverpointBin(None, BinKind.Count, [ValueRange(0, 0)], 0, 1, parent=coverpoint)
		covergroup.Aggregate()

		self.assertEqual(1, covergroup.BinCount)
		self.assertEqual(0, covergroup.RequiredHitCount)
		self.assertEqual(1.0, covergroup.BinCoverage)
		self.assertEqual(1.0, covergroup.HitCoverage)


class Report(Testcase):
	def test_OSVVM(self) -> None:
		"""The hit coverage equals the coverage OSVVM writes for each model."""
		report = CreateOSVVMReport(1)
		length, beat, delay = report.Covergroups

		self.assertAlmostEqual(0.22, length.HitCoverage)
		self.assertAlmostEqual(1.00, beat.HitCoverage)
		self.assertAlmostEqual(0.21, delay.HitCoverage)
		self.assertEqual(0.0, length.BinCoverage)
		self.assertEqual(1.0, beat.BinCoverage)
		self.assertEqual(0.0, delay.BinCoverage)

		self.assertEqual(9, report.BinCount)
		self.assertEqual(3, report.CoveredBinCount)
		self.assertEqual(22 + 100 + 21, report.HitCount)
		self.assertEqual(300, report.RequiredHitCount)
		self.assertAlmostEqual(143 / 300, report.HitCoverage)
		self.assertAlmostEqual(1 / 3, report.BinCoverage)
		self.assertEqual(
			"<FunctionalCoverageReport TbStream_SendGetRandom1: 3 covergroups, bins 33.3%, hits 47.7%>",
			repr(report)
		)

	def test_OSVVM_ZeroWeights(self) -> None:
		"""OSVVM writes a total coverage of 100 %, if every model has weight 0."""
		report = CreateOSVVMReport(0)

		self.assertEqual(0, report.HitCount)
		self.assertEqual(0, report.RequiredHitCount)
		self.assertEqual(1.0, report.HitCoverage)
		self.assertEqual(1.0, report.BinCoverage)
		self.assertAlmostEqual(0.22, report.Covergroups[0].HitCoverage)
