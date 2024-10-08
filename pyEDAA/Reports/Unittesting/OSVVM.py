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
from datetime              import timedelta, datetime
from pathlib               import Path
from time                  import perf_counter_ns
from typing                import Optional as Nullable

from ruamel.yaml           import YAML, CommentedMap, CommentedSeq
from pyTooling.Decorators  import export, notimplemented

from pyEDAA.Reports.Unittesting import UnittestException, Document, TestcaseStatus
from pyEDAA.Reports.Unittesting import TestsuiteSummary as ut_TestsuiteSummary, Testsuite as ut_Testsuite
from pyEDAA.Reports.Unittesting import Testcase as ut_Testcase


from typing import Callable

@export
def InheritDocumentation(baseClass: type, merge: bool = False) -> Callable[[type], type]:
	"""xxx"""
	def decorator(c: type) -> type:
		"""yyy"""
		if merge:
			if c.__doc__ is None:
				c.__doc__ = baseClass.__doc__
			elif baseClass.__doc__ is not None:
				c.__doc__ = baseClass.__doc__ + "\n\n" + c.__doc__
		else:
			c.__doc__ = baseClass.__doc__
		return c

	return decorator


@export
class OsvvmException:
	pass


@export
@InheritDocumentation(UnittestException)
class UnittestException(UnittestException, OsvvmException):
	"""@InheritDocumentation(UnittestException)"""


@export
@InheritDocumentation(ut_Testcase)
class Testcase(ut_Testcase):
	"""@InheritDocumentation(ut_Testcase)"""


@export
@InheritDocumentation(ut_Testsuite)
class Testsuite(ut_Testsuite):
	"""@InheritDocumentation(ut_Testsuite)"""


@export
@InheritDocumentation(ut_TestsuiteSummary)
class TestsuiteSummary(ut_TestsuiteSummary):
	"""@InheritDocumentation(ut_TestsuiteSummary)"""


@export
class BuildSummaryDocument(TestsuiteSummary, Document):
	_yamlDocument: Nullable[YAML]

	def __init__(self, yamlReportFile: Path, parse: bool = False) -> None:
		super().__init__("Unprocessed OSVVM YAML file")
		Document.__init__(self, yamlReportFile)

		self._yamlDocument = None

		if parse:
			self.Analyze()
			self.Convert()

	def Analyze(self) -> None:
		"""
		Analyze the YAML file, parse the content into an YAML data structure.

		.. hint::

		   The time spend for analysis will be made available via property :data:`AnalysisDuration`..
		"""
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
			ex.add_note(f"Call 'BuildSummaryDocument.Generate()' or 'BuildSummaryDocument.Write(..., regenerate=True)'.")
			raise ex

		# with path.open("w", encoding="utf-8") as file:
		# 	self._yamlDocument.writexml(file, addindent="\t", encoding="utf-8", newl="\n")

	@staticmethod
	def _ParseSequenceFromYAML(node: CommentedMap, fieldName: str) -> Nullable[CommentedSeq]:
		try:
			value = node[fieldName]
		except KeyError as ex:
			newEx = UnittestException(f"Sequence field '{fieldName}' not found in node starting at line {node.lc.line + 1}.")
			newEx.add_note(f"Available fields: {', '.join(key for key in node)}")
			raise newEx from ex

		if value is None:
			return ()
		elif not isinstance(value, CommentedSeq):
			line = node._yaml_line_col.data[fieldName][0] + 1
			ex = UnittestException(f"Field '{fieldName}' is not a sequence.")  # TODO: from TypeError??
			ex.add_note(f"Found type {value.__class__.__name__} at line {line}.")
			raise ex

		return value

	@staticmethod
	def _ParseMapFromYAML(node: CommentedMap, fieldName: str) -> Nullable[CommentedMap]:
		try:
			value = node[fieldName]
		except KeyError as ex:
			newEx = UnittestException(f"Dictionary field '{fieldName}' not found in node starting at line {node.lc.line + 1}.")
			newEx.add_note(f"Available fields: {', '.join(key for key in node)}")
			raise newEx from ex

		if value is None:
			return {}
		elif not isinstance(value, CommentedMap):
			line = node._yaml_line_col.data[fieldName][0] + 1
			ex = UnittestException(f"Field '{fieldName}' is not a list.")  # TODO: from TypeError??
			ex.add_note(f"Type mismatch found for line {line}.")
			raise ex
		return value

	@staticmethod
	def _ParseStrFieldFromYAML(node: CommentedMap, fieldName: str) -> Nullable[str]:
		try:
			value = node[fieldName]
		except KeyError as ex:
			newEx = UnittestException(f"String field '{fieldName}' not found in node starting at line {node.lc.line + 1}.")
			newEx.add_note(f"Available fields: {', '.join(key for key in node)}")
			raise newEx from ex

		if not isinstance(value, str):
			raise UnittestException(f"Field '{fieldName}' is not of type str.")  # TODO: from TypeError??

		return value

	@staticmethod
	def _ParseIntFieldFromYAML(node: CommentedMap, fieldName: str) -> Nullable[int]:
		try:
			value = node[fieldName]
		except KeyError as ex:
			newEx = UnittestException(f"Integer field '{fieldName}' not found in node starting at line {node.lc.line + 1}.")
			newEx.add_note(f"Available fields: {', '.join(key for key in node)}")
			raise newEx from ex

		if not isinstance(value, int):
			raise UnittestException(f"Field '{fieldName}' is not of type int.")  # TODO: from TypeError??

		return value

	@staticmethod
	def _ParseDateFieldFromYAML(node: CommentedMap, fieldName: str) -> Nullable[datetime]:
		try:
			value = node[fieldName]
		except KeyError as ex:
			newEx = UnittestException(f"Date field '{fieldName}' not found in node starting at line {node.lc.line + 1}.")
			newEx.add_note(f"Available fields: {', '.join(key for key in node)}")
			raise newEx from ex

		if not isinstance(value, datetime):
			raise UnittestException(f"Field '{fieldName}' is not of type datetime.")  # TODO: from TypeError??

		return value

	@staticmethod
	def _ParseDurationFieldFromYAML(node: CommentedMap, fieldName: str) -> Nullable[timedelta]:
		try:
			value = node[fieldName]
		except KeyError as ex:
			newEx = UnittestException(f"Duration field '{fieldName}' not found in node starting at line {node.lc.line + 1}.")
			newEx.add_note(f"Available fields: {', '.join(key for key in node)}")
			raise newEx from ex

		if not isinstance(value, float):
			raise UnittestException(f"Field '{fieldName}' is not of type float.")  # TODO: from TypeError??

		return timedelta(seconds=value)

	def Convert(self) -> None:
		"""
		Convert the parsed YAML data structure into a test entity hierarchy.

		.. hint::

		   The time spend for model conversion will be made available via property :data:`ModelConversionDuration`.

		:raises UnittestException: If XML was not read and parsed before.
		"""
		if self._yamlDocument is None:
			ex = UnittestException(f"OSVVM YAML file '{self._path}' needs to be read and analyzed by a YAML parser.")
			ex.add_note(f"Call 'Document.Analyze()' or create document using 'Document(path, parse=True)'.")
			raise ex

		startConversion = perf_counter_ns()
		# self._name = self._yamlDocument["name"]
		buildInfo = self._ParseMapFromYAML(self._yamlDocument, "BuildInfo")
		self._startTime = self._ParseDateFieldFromYAML(buildInfo, "StartTime")
		self._totalDuration = self._ParseDurationFieldFromYAML(buildInfo, "Elapsed")

		if "TestSuites" in self._yamlDocument:
			for yamlTestsuite in self._ParseSequenceFromYAML(self._yamlDocument, "TestSuites"):
				self._ParseTestsuite(self, yamlTestsuite)

		self.Aggregate()
		endConversation = perf_counter_ns()
		self._modelConversion = (endConversation - startConversion) / 1e9

	def _ParseTestsuite(self, parentTestsuite: Testsuite, yamlTestsuite: CommentedMap) -> None:
		testsuiteName = self._ParseStrFieldFromYAML(yamlTestsuite, "Name")
		totalDuration = self._ParseDurationFieldFromYAML(yamlTestsuite, "ElapsedTime")

		testsuite = Testsuite(
			testsuiteName,
			totalDuration=totalDuration,
			parent=parentTestsuite
		)

		# if yamlTestsuite['TestCases'] is not None:
		for yamlTestcase in self._ParseSequenceFromYAML(yamlTestsuite, 'TestCases'):
			self._ParseTestcase(testsuite, yamlTestcase)

	def _ParseTestcase(self, parentTestsuite: Testsuite, yamlTestcase: CommentedMap) -> None:
		testcaseName = self._ParseStrFieldFromYAML(yamlTestcase, "TestCaseName")
		totalDuration = self._ParseDurationFieldFromYAML(yamlTestcase, "ElapsedTime")
		yamlStatus = self._ParseStrFieldFromYAML(yamlTestcase, "Status").lower()
		yamlResults = self._ParseMapFromYAML(yamlTestcase, "Results")
		assertionCount = self._ParseIntFieldFromYAML(yamlResults, "AffirmCount")
		passedAssertionCount = self._ParseIntFieldFromYAML(yamlResults, "PassedCount")
		totalErrors = self._ParseIntFieldFromYAML(yamlResults, "TotalErrors")
		yamlAlertCount = self._ParseMapFromYAML(yamlResults, "AlertCount")
		warningCount = self._ParseIntFieldFromYAML(yamlAlertCount, "Warning")
		errorCount = self._ParseIntFieldFromYAML(yamlAlertCount, "Error")
		fatalCount = self._ParseIntFieldFromYAML(yamlAlertCount, "Failure")

		# FIXME: write a Parse classmethod in enum
		if yamlStatus == "passed":
			status = TestcaseStatus.Passed
		elif yamlStatus == "skipped":
			status = TestcaseStatus.Skipped
		elif yamlStatus == "failed":
			status = TestcaseStatus.Failed
		else:
			status = TestcaseStatus.Unknown

		if totalErrors == warningCount + errorCount + fatalCount:
			if warningCount > 0:
				status |= TestcaseStatus.Warned
			if errorCount > 0:
				status |= TestcaseStatus.Errored
			if fatalCount > 0:
				status |= TestcaseStatus.Aborted
		else:
			status |= TestcaseStatus.Inconsistent

		_ = Testcase(
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
