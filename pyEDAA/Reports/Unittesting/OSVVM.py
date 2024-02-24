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
from datetime             import timedelta, datetime
from pathlib              import Path
from time                 import perf_counter_ns
from typing               import Optional as Nullable

from ruamel.yaml          import YAML
from pyTooling.Decorators import export, notimplemented

from pyEDAA.Reports.Unittesting import UnittestException, Document, TestcaseStatus
from pyEDAA.Reports.Unittesting import TestsuiteSummary as ut_TestsuiteSummary, Testsuite as ut_Testsuite
from pyEDAA.Reports.Unittesting import Testcase as ut_Testcase


@export
class OsvvmException:
	pass


@export
class UnittestException(UnittestException, OsvvmException):
	pass


@export
class TestsuiteSummary(ut_TestsuiteSummary):
	pass


@export
class Testsuite(ut_Testsuite):
	pass


@export
class Testcase(ut_Testcase):
	pass


@export
class OsvvmYamlDocument(TestsuiteSummary, Document):
	_yamlDocument: Nullable[YAML]

	def __init__(self, yamlReportFile: Path, parse: bool = False) -> None:
		super().__init__("Unread JUnit XML file")
		Document.__init__(self, yamlReportFile)

		self._yamlDocument = None

		if parse:
			self.Read()
			self.Parse()

	def Read(self) -> None:
		if not self._path.exists():
			raise UnittestException(f"OSVVM YAML file '{self._path}' does not exist.") \
				from FileNotFoundError(f"File '{self._path}' not found.")

		startAnalysis = perf_counter_ns()
		try:
			yamlReader = YAML()
			self._yamlDocument = yamlReader.load(self._path)
		except Exception as ex:
			raise UnittestException(f"Couldn't open '{self._path}'.") from ex

		endAnalysis = perf_counter_ns()
		self._analysisDuration = (endAnalysis - startAnalysis) / 1e9

	@notimplemented
	def Write(self, path: Nullable[Path] = None, overwrite: bool = False) -> None:
		if path is None:
			path = self._path

		if not overwrite and path.exists():
			raise UnittestException(f"OSVVM YAML file '{path}' can not be written.") \
				from FileExistsError(f"File '{path}' already exists.")

		# if regenerate:
		# 	self.Generate(overwrite=True)

		if self._yamlDocument is None:
			ex = UnittestException(f"Internal YAML document tree is empty and needs to be generated before write is possible.")
			ex.add_note(f"Call 'OsvvmYamlDocument.Generate()' or 'OsvvmYamlDocument.Write(..., regenerate=True)'.")
			raise ex

		# with path.open("w") as file:
		# 	self._yamlDocument.writexml(file, addindent="\t", encoding="utf-8", newl="\n")

	def Parse(self) -> None:
		if self._yamlDocument is None:
			ex = UnittestException(f"OSVVM YAML file '{self._path}' needs to be read and analyzed by a YAML parser.")
			ex.add_note(f"Call 'OsvvmYamlDocument.Read()' or create document using 'OsvvmYamlDocument(path, parse=True)'.")
			raise ex

		startConversion = perf_counter_ns()
		self._startTime = datetime.fromisoformat(self._yamlDocument["Date"])
		# yamlBuild = self._yamlDocument["BuildInfo"]

		for yamlTestsuite in self._yamlDocument['TestSuites']:
			self._ParseTestsuite(self, yamlTestsuite)

		self.Aggregate()
		endConversation = perf_counter_ns()
		self._modelConversion = (endConversation - startConversion) / 1e9

	def _ParseTestsuite(self, parentTestsuite: Testsuite, yamlTestsuite) -> None:
		testsuiteName = yamlTestsuite["Name"]
		totalDuration = timedelta(seconds=float(yamlTestsuite["ElapsedTime"]))

		testsuite = Testsuite(
			testsuiteName,
			totalDuration=totalDuration,
			parent=parentTestsuite
		)

		for yamlTestcase in yamlTestsuite['TestCases']:
			self._ParseTestcase(testsuite, yamlTestcase)

	def _ParseTestcase(self, parentTestsuite: Testsuite, yamlTestcase) -> None:
		testcaseName = yamlTestcase["Name"]
		totalDuration = timedelta(seconds=float(yamlTestcase["ElapsedTime"]))
		yamlStatus = yamlTestcase["Status"].lower()
		yamlResults = yamlTestcase["Results"]
		assertionCount = int(yamlResults["AffirmCount"])
		passedAssertionCount = int(yamlResults["PassedCount"])
		warningCount = int(yamlResults["AlertCount"]["Warning"])
		errorCount = int(yamlResults["AlertCount"]["Error"])
		fatalCount = int(yamlResults["AlertCount"]["Failure"])

		if yamlStatus == "passed":
			status = TestcaseStatus.Passed
		elif yamlStatus == "skipped":
			status = TestcaseStatus.Skipped
		elif yamlStatus == "failed":
			status = TestcaseStatus.Failed
		else:
			status = TestcaseStatus.Unknown

		if warningCount > 0:
			status |= TestcaseStatus.Warned
		if errorCount > 0:
			status |= TestcaseStatus.Errored
		if fatalCount > 0:
			status |= TestcaseStatus.Aborted

		testcase = Testcase(
			testcaseName,
			totalDuration=totalDuration,
			assertionCount=assertionCount,
			passedAssertionCount=passedAssertionCount,
			warningCount=warningCount,
			status=status,
			errorCount=errorCount,
			fatalCount=fatalCount,
			parent=parentTestsuite
		)

	def __contains__(self, key: str) -> bool:
		return key in self._testsuites

	def __iter__(self):
		return iter(self._testsuites.values())

	def __getitem__(self, key: str) -> Testsuite:
		return self._testsuites[key]

	def __len__(self) -> int:
		return self._testsuites.__len__()
