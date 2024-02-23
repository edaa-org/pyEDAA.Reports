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
# Copyright 2024-2024 Electronic Design Automation Abstraction (EDA²)                                                  #
# Copyright 2023-2023 Patrick Lehmann - Bötzingen, Germany                                                             #
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
"""
Reader for JUnit unit testing summary files in XML format.
"""
from datetime        import datetime, timedelta
from enum import Enum, Flag
from pathlib         import Path
from time            import perf_counter_ns
from xml.dom         import minidom, Node
from xml.dom.minidom import Element

from pyTooling.Decorators  import export, readonly

from pyEDAA.Reports.Unittesting import UnittestException, DuplicateTestsuiteException, DuplicateTestcaseException, \
	TestsuiteSummary, Testsuite, Testcase, TestcaseState



@export
class JUnitException:
	pass


@export
class UnittestException(UnittestException, JUnitException):
	pass


@export
class DuplicateTestsuiteException(DuplicateTestsuiteException, JUnitException):
	pass


@export
class DuplicateTestcaseException(DuplicateTestcaseException, JUnitException):
	pass


@export
class JUnitReaderMode(Flag):
	Default = 0
	DecoupleTestsuiteHierarchyAndTestcaseClassName = 1


@export
class JUnitDocument(TestsuiteSummary):
	_readerMode:       JUnitReaderMode
	_path:             Path
	_documentElement:  Element

	_readingByMiniDom: float  #: TODO: replace by Timer; should be timedelta?
	_modelConversion:  float  #: TODO: replace by Timer; should be timedelta?

	def __init__(self, path: Path, readerMode: JUnitReaderMode = JUnitReaderMode.Default):
		if not path.exists():
			raise UnittestException(f"JUnit XML file '{path}' does not exist.") from FileNotFoundError(f"File '{path}' not found.")

		self._readerMode = readerMode
		self._path = path

		try:
			startMiniDom = perf_counter_ns()
			rootElement = minidom.parse(str(path)).documentElement
			endMiniDom = perf_counter_ns()
		except Exception as ex:
			raise UnittestException(f"Couldn't open '{path}'.") from ex

		self._documentElement = rootElement
		self._readingByMiniDom = (endMiniDom - startMiniDom) / 1e9

		startConversion = perf_counter_ns()
		name = rootElement.getAttribute("name") if rootElement.hasAttribute("name") else "root"
		testsuiteRuntime = float(rootElement.getAttribute("time")) if rootElement.hasAttribute("time") else -1.0
		timestamp = datetime.fromisoformat(rootElement.getAttribute("timestamp")) if rootElement.hasAttribute("timestamp") else None

		super().__init__(
			name,
			startTime=timestamp,
			totalDuration=timedelta(seconds=testsuiteRuntime))

		tests = rootElement.getAttribute("tests")
		skipped = rootElement.getAttribute("skipped")
		errors = rootElement.getAttribute("errors")
		failures = rootElement.getAttribute("failures")
		assertions = rootElement.getAttribute("assertions")

		for rootNode in rootElement.childNodes:
			if rootNode.nodeName == "testsuite":
				self._ParseTestsuite(self, rootNode)

		self.Aggregate()
		endConversation = perf_counter_ns()
		self._modelConversion = (endConversation - startConversion) / 1e9

	def _ParseTestsuite(self, parentTestsuite: Testsuite, testsuitesNode: Element) -> None:
		name = testsuitesNode.getAttribute("name")

		kwargs = {}
		if testsuitesNode.hasAttribute("timestamp"):
			kwargs["startTime"] = datetime.fromisoformat(testsuitesNode.getAttribute("timestamp"))
		if testsuitesNode.hasAttribute("time"):
			kwargs["totalDuration"] = timedelta(seconds=float(testsuitesNode.getAttribute("time")))

		newTestsuite = Testsuite(
			name,
			**kwargs,
			parent=parentTestsuite
		)

		if self._readerMode is JUnitReaderMode.Default:
			currentTestsuite = parentTestsuite
		elif self._readerMode is JUnitReaderMode.DecoupleTestsuiteHierarchyAndTestcaseClassName:
			currentTestsuite = newTestsuite
		else:
			raise UnittestException(f"Unknown reader mode '{self._readerMode}'.")

		for node in testsuitesNode.childNodes:
			if node.nodeType == Node.ELEMENT_NODE:
				if node.tagName == "testsuite":
					self._ParseTestsuite(currentTestsuite, node)
				elif node.tagName == "testcase":
					self._ParseTestcase(currentTestsuite, node)

	def _ParseTestcase(self, parentTestsuite: Testsuite, testsuiteNode: Element) -> None:
		className = testsuiteNode.getAttribute("classname")
		name = testsuiteNode.getAttribute("name")
		time = float(testsuiteNode.getAttribute("time"))

		if self._readerMode is JUnitReaderMode.Default:
			currentTestsuite = self
		elif self._readerMode is JUnitReaderMode.DecoupleTestsuiteHierarchyAndTestcaseClassName:
			currentTestsuite = parentTestsuite
		else:
			raise UnittestException(f"Unknown reader mode '{self._readerMode}'.")

		testsuitePath = className.split(".")
		for testsuiteName in testsuitePath:
			try:
				currentTestsuite = currentTestsuite._testsuites[testsuiteName]
			except KeyError:
				currentTestsuite._testsuites[testsuiteName] = new = Testsuite(testsuiteName)
				currentTestsuite = new

		testcase = Testcase(name, totalDuration=timedelta(seconds=time))
		currentTestsuite._testcases[name] = testcase

		for node in testsuiteNode.childNodes:
			if node.nodeType == Node.ELEMENT_NODE:
				if node.tagName == "skipped":
					testcase._state = TestcaseState.Skipped
				elif node.tagName == "failure":
					testcase._state = TestcaseState.Failed
				elif node.tagName == "error":
					testcase._state = TestcaseState.Errored
				elif node.tagName == "system-out":
					pass
				elif node.tagName == "system-err":
					pass
				elif node.tagName == "properties":
					pass
				else:
					raise UnittestException(f"Unknown element '{node.tagName}' in junit file.")

		if testcase._state is TestcaseState.Unknown:
			testcase._state = TestcaseState.Passed

	@readonly
	def Path(self) -> Path:
		return self._path

	@readonly
	def AnalysisDuration(self) -> timedelta:
		return timedelta(seconds=self._readingByMiniDom)

	@readonly
	def ModelConversionDuration(self) -> timedelta:
		return timedelta(seconds=self._modelConversion)
