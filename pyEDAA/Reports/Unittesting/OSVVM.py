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
"""Reader for OSVVM test report summary files in YAML format."""
from pathlib              import Path
from typing               import Dict

from ruamel.yaml          import YAML
from pyTooling.Decorators import export

from pyEDAA.Reports.Unittesting import Testsuite as Abstract_Testsuite, Testcase as Abstract_Testcase, Status


@export
class Testsuite(Abstract_Testsuite):
	pass


@export
class Testcase(Abstract_Testcase):
	pass


@export
class Document:
	_yamlDocument: YAML
	_testsuites: Dict[str, Testsuite]

	def __init__(self, yamlReportFile: Path) -> None:
		yamlReader = YAML()
		self._yamlDocument = yamlReader.load(yamlReportFile)
		yamlBuild = self._yamlDocument["BuildInfo"]

		self._testsuites = {}

		self.translateDocument()

	def translateDocument(self) -> None:
		for yamlTestsuite in self._yamlDocument['TestSuites']:
			name = yamlTestsuite["Name"]
			self._testsuites[name] = self.translateTestsuite(yamlTestsuite, name)

	def translateTestsuite(self, yamlTestsuite, name) -> Testsuite:
		testsuite = Testsuite(name)

		for yamlTestcase in yamlTestsuite['TestCases']:
			testcaseName = yamlTestcase["Name"]
			testsuite._testcases[testcaseName] = self.translateTestcase(yamlTestcase, testcaseName)

		return testsuite

	def translateTestcase(self, yamlTestcase, name) -> Testcase:
		yamlStatus = yamlTestcase["Status"].lower()

		assertionCount = 0
		warningCount = 0
		errorCount = 0
		fatalCount = 0

		if yamlStatus == "passed":
			status = Status.Passed

			yamlResults = yamlTestcase["Results"]
			assertionCount = yamlResults["AffirmCount"]

		elif yamlStatus == "skipped":
			status = Status.Skipped

		elif yamlStatus == "failed":
			status = Status.Failed

		else:
			print(f"ERROR: Unknown testcase status '{yamlStatus}'.")

		return Testcase(name, assertionCount, warningCount, errorCount, fatalCount)

	def __contains__(self, key: str) -> bool:
		return key in self._testsuites

	def __iter__(self):
		return iter(self._testsuites.values())

	def __getitem__(self, key: str) -> Testsuite:
		return self._testsuites[key]

	def __len__(self) -> int:
		return self._testsuites.__len__()
