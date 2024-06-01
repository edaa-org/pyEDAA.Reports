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
# Copyright 2021-2024 Electronic Design Automation Abstraction (EDA²)                                                  #
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
"""Testcases for OSVVM's AlertLog YAML file format."""
from datetime import timedelta
from pathlib import Path
from unittest     import TestCase

from pyEDAA.Reports.OSVVM.AlertLog import Document as AlertLogDocument


if __name__ == "__main__": # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unitest <testcase module>'")
	exit(1)


class Instantiation(TestCase):
	pass


class Document(TestCase):
	def test_Create(self) -> None:
		print()
		invalidTimedelta = timedelta(seconds=-1.0)

		path = Path("tests/data/OSVVM/TbAxi4_BasicReadWrite_alerts.yml")
		doc = AlertLogDocument(path)

		self.assertEqual(path, doc.Path)
		self.assertEqual(invalidTimedelta, doc.AnalysisDuration)
		self.assertEqual(invalidTimedelta, doc.ModelConversionDuration)

	def test_Create_WithParse(self) -> None:
		print()
		zeroTime = timedelta()

		path = Path("tests/data/OSVVM/TbAxi4_BasicReadWrite_alerts.yml")
		doc = AlertLogDocument(path, parse=True)

		self.assertEqual(path, doc.Path)
		self.assertGreater(doc.AnalysisDuration, zeroTime)
		self.assertGreater(doc.ModelConversionDuration, zeroTime)

		tree = doc.ToTree()
		print(tree.Render())
