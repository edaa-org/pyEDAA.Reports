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
"""Unit tests of the functional coverage model: value ranges and the bins of coverpoints."""
from pyTooling.MetaClasses             import AbstractClassError
from pyTooling.Testing                 import Testcase

from pyEDAA.Reports.FunctionalCoverage import Bin, BinKind, Covergroup, Coverpoint, CoverpointBin, \
                                              FunctionalCoverageReport, ValueRange


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


class Enumerations(Testcase):
	def test_BinKind(self) -> None:
		self.assertEqual(["Count", "Ignore", "Illegal", "Default"], [kind.name for kind in BinKind])


class ValueRanges(Testcase):
	def test_ValueRange(self) -> None:
		valueRange = ValueRange(3, 11)

		self.assertEqual(3, valueRange.Low)
		self.assertEqual(11, valueRange.High)
		self.assertEqual("<ValueRange 3..11>", repr(valueRange))

	def test_SingleValue(self) -> None:
		valueRange = ValueRange(-5, -5)

		self.assertEqual(-5, valueRange.Low)
		self.assertEqual(-5, valueRange.High)

	def test_Equality(self) -> None:
		self.assertEqual(ValueRange(0, 7), ValueRange(0, 7))
		self.assertNotEqual(ValueRange(0, 7), ValueRange(0, 8))
		self.assertEqual(1, len({ValueRange(0, 7), ValueRange(0, 7)}))

	def test_Equality_OtherType(self) -> None:
		with self.assertRaises(TypeError) as context:
			_ = ValueRange(0, 7) == (0, 7)

		self.assertEqual("Second operand is not supported by == operator.", str(context.exception))
		self.assertEqual("Got type 'tuple'.", context.exception.__notes__[0])
		self.assertEqual("Supported types for second operand: ValueRange", context.exception.__notes__[1])

	def test_ParameterChecks(self) -> None:
		for arguments, exception, message in (
			((None, 1),    ValueError, "Parameter 'low' is None."),
			(("0",  1),    TypeError,  "Parameter 'low' is not of type 'int'."),
			((True, 1),    TypeError,  "Parameter 'low' is not of type 'int'."),
			((0,    None), ValueError, "Parameter 'high' is None."),
			((0,    1.0),  TypeError,  "Parameter 'high' is not of type 'int'."),
			((2,    1),    ValueError, "Parameter 'high' is less than parameter 'low'."),
		):
			with self.subTest(arguments=arguments):
				with self.assertRaises(exception) as context:
					_ = ValueRange(*arguments)
				self.assertEqual(message, str(context.exception))

	def test_ParameterChecks_Notes(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = ValueRange(2, 1)
		self.assertEqual(["Got range 2 to 1."], context.exception.__notes__)

		with self.assertRaises(TypeError) as context:
			_ = ValueRange("0", 1)
		self.assertEqual(["Got type 'str'."], context.exception.__notes__)


class BinInstantiation(Testcase):
	def test_CoverpointBin(self) -> None:
		coverpointBin = CoverpointBin(None, BinKind.Count, [ValueRange(3, 11)], 19, 80)

		self.assertIsNone(coverpointBin.Name)
		self.assertIs(BinKind.Count, coverpointBin.Kind)
		self.assertEqual([ValueRange(3, 11)], coverpointBin.Ranges)
		self.assertEqual(19, coverpointBin.Count)
		self.assertEqual(80, coverpointBin.AtLeast)
		self.assertIsNone(coverpointBin.Parent)
		self.assertIsNone(coverpointBin.Root)
		self.assertEqual("<CoverpointBin (unnamed) Count: 19/80>", repr(coverpointBin))

	def test_Named(self) -> None:
		coverpointBin = CoverpointBin("short", BinKind.Count, (ValueRange(1, 2), ValueRange(5, 5)), 1)

		self.assertEqual("short", coverpointBin.Name)
		self.assertEqual([ValueRange(1, 2), ValueRange(5, 5)], coverpointBin.Ranges)
		self.assertEqual(1, coverpointBin.AtLeast)
		self.assertEqual("<CoverpointBin short Count: 1/1>", repr(coverpointBin))

	def test_ParameterChecks(self) -> None:
		count =  BinKind.Count
		ranges = [ValueRange(0, 1)]
		for arguments, exception, message in (
			((1,    count,   ranges, 0),        TypeError,  "Parameter 'name' is not of type 'str'."),
			(("",   count,   ranges, 0),        ValueError, "Parameter 'name' is empty."),
			((None, None,    ranges, 0),        ValueError, "Parameter 'kind' is None."),
			((None, "COUNT", ranges, 0),        TypeError,  "Parameter 'kind' is not of type 'BinKind'."),
			((None, count,   ranges, None),     ValueError, "Parameter 'count' is None."),
			((None, count,   ranges, 1.0),      TypeError,  "Parameter 'count' is not of type 'int'."),
			((None, count,   ranges, -1),       ValueError, "Parameter 'count' is negative."),
			((None, count,   ranges, 0, None),  ValueError, "Parameter 'atLeast' is None."),
			((None, count,   ranges, 0, False), TypeError,  "Parameter 'atLeast' is not of type 'int'."),
			((None, count,   ranges, 0, -1),    ValueError, "Parameter 'atLeast' is negative."),
		):
			with self.subTest(arguments=arguments):
				with self.assertRaises(exception) as context:
					_ = CoverpointBin(*arguments)
				self.assertEqual(message, str(context.exception))

		for ranges, exception, message in (
			(None,     ValueError, "Parameter 'ranges' is None."),
			(1,        TypeError,  "Parameter 'ranges' is not iterable."),
			([(0, 1)], TypeError,  "Parameter 'ranges' contains an element not of type 'ValueRange'."),
		):
			with self.subTest(ranges=ranges):
				with self.assertRaises(exception) as context:
					_ = CoverpointBin(None, count, ranges, 0)
				self.assertEqual(message, str(context.exception))

	def test_Parent(self) -> None:
		with self.assertRaises(TypeError) as context:
			_ = CoverpointBin(None, BinKind.Count, [], 0, parent=Covergroup("G"))
		self.assertEqual("Parameter 'parent' is not of type 'Coverpoint'.", str(context.exception))

	def test_Abstract(self) -> None:
		with self.assertRaises(AbstractClassError):
			_ = Bin(None, BinKind.Count, 0)


class BinHierarchy(Testcase):
	def test_Constructors(self) -> None:
		report =        FunctionalCoverageReport("T")
		coverpoint =    Coverpoint("Bin1", parent=Covergroup("DelayCov BurstLength", parent=report))
		coverpointBin = CoverpointBin(None, BinKind.Count, [ValueRange(3, 11)], 19, 80, parent=coverpoint)

		self.assertEqual([coverpointBin], coverpoint.Bins)
		self.assertIs(coverpoint, coverpointBin.Parent)
		self.assertIs(report, coverpointBin.Root)

	def test_ParentSetter(self) -> None:
		"""A bin joins a coverpoint, which joins a report later: the bin takes the report's root."""
		coverpointBin = CoverpointBin(None, BinKind.Count, [ValueRange(3, 11)], 19, 80)
		coverpoint =    Coverpoint("Bin1")
		covergroup =    Covergroup("DelayCov BurstLength")
		report =        FunctionalCoverageReport("T")

		self.assertEqual([], coverpoint.Bins)

		coverpointBin.Parent = coverpoint
		coverpoint.Parent =    covergroup
		self.assertIsNone(coverpointBin.Root)

		covergroup.Parent = report

		self.assertEqual([coverpointBin], coverpoint.Bins)
		self.assertIs(report, coverpointBin.Root)

	def test_Iterate(self) -> None:
		coverpoint = Coverpoint("Short")
		low =        CoverpointBin(None, BinKind.Count, [ValueRange(0, 3)], 1, parent=coverpoint)
		ignored =    CoverpointBin(None, BinKind.Ignore, [ValueRange(4, 7)], 1, 0, parent=coverpoint)

		self.assertEqual([low, ignored], list(coverpoint.IterateBins()))
		self.assertEqual([ignored], list(coverpoint.IterateBins(lambda coverageBin: coverageBin.Kind is BinKind.Ignore)))
