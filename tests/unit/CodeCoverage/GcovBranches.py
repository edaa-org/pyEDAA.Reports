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
from json                                      import dumps
from pathlib                                   import Path
from tempfile                                  import TemporaryDirectory
from typing                                    import Any

from pyEDAA.Reports.CodeCoverage               import CodeCoverageError
from pyEDAA.Reports.CodeCoverage.Gcov          import Document, File
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


	def test_Condition_CheckOrder(self) -> None:
		"""The parameters are checked in their order: 'notCoveredTrue' and 'notCoveredFalse' before 'parent'."""
		with self.assertRaises(TypeError) as context:
			_ = Condition(4, 2, notCoveredTrue=5, parent=21)
		self.assertEqual("Parameter 'notCoveredTrue' is not iterable.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = Condition(4, 2, notCoveredFalse=["0"], parent=21)
		self.assertEqual("Parameter 'notCoveredFalse' contains an element not of type 'int'.", str(context.exception))

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

	def test_Record(self) -> None:
		"""Each class method 'Parse' checks the JSON object it is given."""
		for recordClass in (Branch, Call, Condition):
			with self.subTest(recordClass=recordClass.__name__):
				with self.assertRaises(ValueError) as context:
					_ = recordClass.Parse(None)
				self.assertEqual("Parameter 'record' is None.", str(context.exception))

				with self.assertRaises(TypeError) as context:
					_ = recordClass.Parse("x")
				self.assertEqual("Parameter 'record' is not of type 'dict'.", str(context.exception))
				self.assertEqual(["Got type 'str'."], context.exception.__notes__)


class Schema(Testcase):
	"""The JSON Schema of each format version checks the records of a line."""

	def _Analyze(self, formatVersion: str, line: dict[str, Any]) -> CodeCoverageError:
		"""
		Read a report of one line, which its JSON Schema rejects.

		:param formatVersion: The format version the report states.
		:param line:          The JSON object of the line.
		:returns:             The validation error.
		"""
		document = {
			"format_version": formatVersion, "gcc_version": "14.2.0", "data_file": "main.c", "files": [
				{"file": "main.c", "functions": [], "lines": [line]}
			]
		}
		with TemporaryDirectory() as directory:
			jsonFile = Path(directory) / "test.gcov.json"
			jsonFile.write_text(dumps(document), encoding="utf-8")

			with self.assertRaises(CodeCoverageError) as context:
				_ = Document(jsonFile, analyzeAndConvert=True)

		self.assertEqual(
			f"Validation error for '{jsonFile}' using JSON Schema 'Gcov-{formatVersion}.schema.json'.",
			str(context.exception)
		)
		return context.exception

	def test_Format1_Branch(self) -> None:
		"""The schema of format 1 rejects the basic blocks of a branch."""
		error = self._Analyze("1", {"line_number": 1, "count": 1, "unexecuted_block": False, "branches": [
			{"count": 1, "throw": False, "fallthrough": True, "source_block_id": 2, "destination_block_id": 3}
		]})

		self.assertEqual([
			"/files/0/lines/0/branches/0: Additional properties are not allowed ('destination_block_id', 'source_block_id' "
			"were unexpected)"
		], error.__notes__)

	def test_Format2_Branch(self) -> None:
		"""gcov of GCC 14 and later writes the basic blocks of a branch."""
		error = self._Analyze("2", {
			"line_number": 1, "count": 1, "unexecuted_block": False, "block_ids": [2], "calls": [], "conditions": [],
			"branches": [{"count": 1, "throw": False, "fallthrough": True}]
		})

		self.assertEqual([
			"/files/0/lines/0/branches/0: 'source_block_id' is a required property",
			"/files/0/lines/0/branches/0: 'destination_block_id' is a required property"
		], error.__notes__)

	def test_Format2_Records(self) -> None:
		"""The schema of format 2 checks the fields of a call and a condition."""
		error = self._Analyze("2", {
			"line_number": 1, "count": 1, "unexecuted_block": False, "block_ids": [2], "branches": [],
			"calls": [{"source_block_id": 2, "destination_block_id": 3}],
			"conditions": [{"count": 4, "covered": 2, "not_covered_true": [], "not_covered_false": [0, 1], "terms": 2}]
		})

		self.assertEqual([
			"/files/0/lines/0/calls/0: 'returned' is a required property",
			"/files/0/lines/0/conditions/0: Additional properties are not allowed ('terms' was unexpected)"
		], error.__notes__)
