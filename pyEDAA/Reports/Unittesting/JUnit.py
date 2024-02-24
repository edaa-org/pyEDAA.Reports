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
from enum            import Flag
from pathlib         import Path
from time            import perf_counter_ns
from typing          import Optional as Nullable
from xml.dom         import minidom, Node
from xml.dom.minidom import Element, Document

from pyTooling.Decorators       import export, readonly

from pyEDAA.Reports.Unittesting import UnittestException, DuplicateTestsuiteException, DuplicateTestcaseException
from pyEDAA.Reports.Unittesting import TestsuiteSummary, Testsuite, Testcase, TestcaseState


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
	_xmlDocument:      Nullable[Document]

	_readingByMiniDom: float  #: TODO: replace by Timer; should be timedelta?
	_modelConversion:  float  #: TODO: replace by Timer; should be timedelta?

	def __init__(self, path: Path, parse: bool = False, readerMode: JUnitReaderMode = JUnitReaderMode.Default):
		self._path = path
		self._readerMode = readerMode

		super().__init__("Unread JUnit XML file")

		self._xmlDocument = None
		self._readingByMiniDom = -1.0
		self._modelConversion = -1.0

		if parse:
			self.Read()
			self.Parse()

	def Read(self) -> None:
		if not self._path.exists():
			raise UnittestException(f"JUnit XML file '{self._path}' does not exist.") \
				from FileNotFoundError(f"File '{self._path}' not found.")

		startMiniDom = perf_counter_ns()
		try:
			self._xmlDocument = minidom.parse(str(self._path))
		except Exception as ex:
			raise UnittestException(f"Couldn't open '{self._path}'.") from ex

		endMiniDom = perf_counter_ns()
		self._readingByMiniDom = (endMiniDom - startMiniDom) / 1e9

	def Write(self, path: Nullable[Path] = None, overwrite: bool = False) -> None:
		if path is None:
			path = self._path

		if not overwrite and path.exists():
			raise UnittestException(f"JUnit XML file '{path}' can not be written.") \
				from FileExistsError(f"File '{path}' already exists.")

		if self._xmlDocument is None:
			ex = UnittestException(f"Internal XML document tree is empty and needs to be generated before write is possible.")
			# ex.add_note(f"Call 'JUnitDocument.FromTestsuiteSummary()'.")
			raise ex

		with path.open("w") as file:
			self._xmlDocument.writexml(file, encoding="utf-8", standalone=True, newl="")

	def Parse(self) -> None:
		if self._xmlDocument is None:
			ex = UnittestException(f"JUnit XML file '{self._path}' needs to be read and analyzed by an XML parser.")
			ex.add_note(f"Call 'JUnitDocument.Read()' or create document using 'JUnitDocument(path, parse=True)'.")
			raise ex

		startConversion = perf_counter_ns()
		rootElement = self._xmlDocument.documentElement

		self._name =          rootElement.getAttribute("name")                              if rootElement.hasAttribute("name")      else "root"
		self._startTime =     datetime.fromisoformat(rootElement.getAttribute("timestamp")) if rootElement.hasAttribute("timestamp") else None
		self._totalDuration = timedelta(seconds=float(rootElement.getAttribute("time")))    if rootElement.hasAttribute("time")      else None

		# tests = rootElement.getAttribute("tests")
		# skipped = rootElement.getAttribute("skipped")
		# errors = rootElement.getAttribute("errors")
		# failures = rootElement.getAttribute("failures")
		# assertions = rootElement.getAttribute("assertions")

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
