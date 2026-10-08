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
#
"""Unit tests of the records of a line of GCC's gcov JSON format: its branches, calls and conditions."""
from pathlib                                   import Path

from pyEDAA.Reports.CodeCoverage.Gcov          import File
from pyEDAA.Reports.CodeCoverage.Gcov.Branches import Branch, Call, Condition
from pyEDAA.Reports.CodeCoverage.Gcov.Records  import Line
from pyTooling.Testing                         import Testcase


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


class Construction(Testcase):
	"""The records of a line are built by hand: each constructor takes typed values and checks them."""

	def test_Branch(self) -> None:
		branch = Branch(0, True, False, 4, 8)

		self.assertEqual((0, True, False, 4, 8), (
			branch.Count, branch.Throw, branch.Fallthrough, branch.SourceBlockID, branch.DestinationBlockID
		))
		self.assertEqual((None, None), (Branch(1, False, True).SourceBlockID, Branch(1, False, True).DestinationBlockID))

	def test_Call(self) -> None:
		call = Call(5, 1, 0)

		self.assertEqual((5, 1, 0), (call.SourceBlockID, call.DestinationBlockID, call.Returned))

	def test_Condition(self) -> None:
		condition = Condition(4, 2, (), (0, 1))

		self.assertEqual((4, 2, [], [0, 1]),
		                 (condition.Count, condition.Covered, condition.NotCoveredTrue, condition.NotCoveredFalse))
		self.assertEqual(([], []), (Condition(2, 2).NotCoveredTrue, Condition(2, 2).NotCoveredFalse))

	def test_Branch_Throw(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = Branch(1, None, False)
		self.assertEqual("Parameter 'throw' is None.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = Branch(1, 0, False)
		self.assertEqual("Parameter 'throw' is not of type 'bool'.", str(context.exception))
		self.assertEqual(["Got type 'int'."], context.exception.__notes__)

	def test_Branch_SourceBlockID(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = Branch(1, False, True, -1)
		self.assertEqual("Parameter 'sourceBlockID' is negative.", str(context.exception))
		self.assertEqual(["Got value '-1'."], context.exception.__notes__)

	def test_Call_Returned(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = Call(3, 1, None)
		self.assertEqual("Parameter 'returned' is None.", str(context.exception))

	def test_Condition_NotCoveredFalse(self) -> None:
		with self.assertRaises(TypeError) as context:
			_ = Condition(4, 2, notCoveredFalse=5)
		self.assertEqual("Parameter 'notCoveredFalse' is not iterable.", str(context.exception))
		self.assertEqual(["Got type 'int'."], context.exception.__notes__)


class ParentRelation(Testcase):
	"""Each record of a line names its line as its parent and is added to it."""

	def test_Branch(self) -> None:
		line = Line(21, 1, False)
		branches = [Branch(1, False, True, 4, 5, parent=line), Branch(0, True, False, 4, 8, parent=line)]

		self.assertEqual([line, line], [branch.Parent for branch in branches])
		self.assertEqual(branches, line.Branches)

	def test_Call(self) -> None:
		line = Line(21, 1, False)
		call = Call(3, 1, 1, parent=line)

		self.assertIs(line, call.Parent)
		self.assertEqual([call], line.Calls)

	def test_Condition(self) -> None:
		line = Line(20, 4, False)
		condition = Condition(4, 2, (), (0, 1), parent=line)

		self.assertIs(line, condition.Parent)
		self.assertEqual([condition], line.Conditions)

	def test_Defaults(self) -> None:
		self.assertEqual((None, None, None), (Branch(1, False, True).Parent, Call(3, 1, 1).Parent, Condition(2, 2).Parent))

	def test_Branch_Parent(self) -> None:
		with self.assertRaises(TypeError) as context:
			_ = Branch(1, False, True, parent=Call(3, 1, 1))
		self.assertEqual("Parameter 'parent' is not of type 'Line'.", str(context.exception))
		self.assertEqual(["Got type 'pyEDAA.Reports.CodeCoverage.Gcov.Branches.Call'."], context.exception.__notes__)

	def test_Call_Parent(self) -> None:
		with self.assertRaises(TypeError) as context:
			_ = Call(3, 1, 1, parent=21)
		self.assertEqual("Parameter 'parent' is not of type 'Line'.", str(context.exception))
		self.assertEqual(["Got type 'int'."], context.exception.__notes__)

	def test_Condition_Parent(self) -> None:
		with self.assertRaises(TypeError) as context:
			_ = Condition(2, 2, parent=File(Path("main.c")))
		self.assertEqual("Parameter 'parent' is not of type 'Line'.", str(context.exception))
		self.assertEqual(["Got type 'pyEDAA.Reports.CodeCoverage.Gcov.File'."], context.exception.__notes__)


class Parsing(Testcase):
	"""Each record of a line parses its JSON object."""

	def test_Line_Records(self) -> None:
		line = Line.Parse({
			"line_number": 20, "function_name": "Clamp", "count": 4, "unexecuted_block": False, "block_ids": [2],
			"branches": [{"count": 3, "throw": False, "fallthrough": True, "source_block_id": 2, "destination_block_id": 3}],
			"calls": [{"source_block_id": 2, "destination_block_id": 3, "returned": 4}],
			"conditions": [{"count": 4, "covered": 2, "not_covered_true": [], "not_covered_false": [0, 1]}]
		})

		branch, = line.Branches
		call, = line.Calls
		condition, = line.Conditions
		self.assertEqual((line, line, line), (branch.Parent, call.Parent, condition.Parent))
		self.assertEqual((3, False, True, 2, 3), (
			branch.Count, branch.Throw, branch.Fallthrough, branch.SourceBlockID, branch.DestinationBlockID
		))
		self.assertEqual((2, 3, 4), (call.SourceBlockID, call.DestinationBlockID, call.Returned))
		self.assertEqual((4, 2, [], [0, 1]),
		                 (condition.Count, condition.Covered, condition.NotCoveredTrue, condition.NotCoveredFalse))

	def test_Branch(self) -> None:
		branch = Branch.Parse({
			"count": 0, "throw": True, "fallthrough": False, "source_block_id": 4, "destination_block_id": 8
		})

		self.assertEqual((0, True, False, 4, 8), (
			branch.Count, branch.Throw, branch.Fallthrough, branch.SourceBlockID, branch.DestinationBlockID
		))

	def test_Call(self) -> None:
		call = Call.Parse({"source_block_id": 5, "destination_block_id": 1, "returned": 0})

		self.assertEqual((5, 1, 0), (call.SourceBlockID, call.DestinationBlockID, call.Returned))

	def test_Condition(self) -> None:
		condition = Condition.Parse({"count": 6, "covered": 5, "not_covered_true": [2], "not_covered_false": []})

		self.assertEqual((6, 5, [2], []),
		                 (condition.Count, condition.Covered, condition.NotCoveredTrue, condition.NotCoveredFalse))
