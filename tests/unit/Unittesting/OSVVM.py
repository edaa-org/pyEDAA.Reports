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
"""Testcase for OSVVM specific file formats."""
from pathlib      import Path
from unittest     import TestCase

from pyEDAA.Reports.Unittesting.OSVVM import OsvvmYamlDocument


if __name__ == "__main__": # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unitest <testcase module>'")
	exit(1)


class TestResults(TestCase):
	def test_ReadOSVVMTestSummaryYAML(self) -> None:
		yamlPath = Path("tests/data/OSVVM/osvvm.Summary.yml")

		osvvmTestSummary = OsvvmYamlDocument(yamlPath, parse=True)
		print(osvvmTestSummary.ToTree().Render())

		self.assertEqual(14, len(osvvmTestSummary.Testsuites))
		self.assertIn("Axi4Lite", osvvmTestSummary)
		self.assertIn("Axi4Full", osvvmTestSummary)
		self.assertIn("AxiStream", osvvmTestSummary)
		self.assertIn("Uart", osvvmTestSummary)

		axi4lite = osvvmTestSummary["Axi4Lite"]
		self.assertEqual(17, len(axi4lite.Testcases))

		axi4 = osvvmTestSummary["Axi4Full"]
		self.assertEqual(68, len(axi4.Testcases))

		axi4stream = osvvmTestSummary["AxiStream"]
		self.assertEqual(65, len(axi4stream.Testcases))

		uart = osvvmTestSummary["Uart"]
		self.assertEqual(8, len(uart.Testcases))

	# 	for suite in osvvmTestSummary:
	# 		self.printTestsuite(suite)
	#
	# def printTestsuite(self, testsuite: Testsuite, indent: int = 0):
	# 	print(f"{'  '*indent}{testsuite.Name}")
	# 	for suite in testsuite._testsuites.values():
	# 		self.printTestsuite(suite, indent + 2)
	# 	for case in testsuite:
	# 		self.printTestcase(case, indent + 2)
	#
	# def printTestcase(self, testcase: Testcase, indent: int = 0):
	# 	print(f"{'  ' * indent}{testcase.Name}")
