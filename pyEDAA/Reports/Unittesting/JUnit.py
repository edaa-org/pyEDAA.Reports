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
from pyEDAA.Reports.Unittesting import Document as ut_Document
from pyEDAA.Reports.Unittesting import TestsuiteSummary, Testsuite, Testcase, TestcaseStatus


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
class JUnitDocument(TestsuiteSummary, ut_Document):
	_readerMode:       JUnitReaderMode
	_xmlDocument:      Nullable[Document]

	def __init__(self, xmlReportFile: Path, parse: bool = False, readerMode: JUnitReaderMode = JUnitReaderMode.Default):
		super().__init__("Unread JUnit XML file")
		ut_Document.__init__(self, xmlReportFile)

		self._readerMode = readerMode
		self._xmlDocument = None

		if parse:
			self.Read()
			self.Parse()

	def Read(self) -> None:
		if not self._path.exists():
			raise UnittestException(f"JUnit XML file '{self._path}' does not exist.") \
				from FileNotFoundError(f"File '{self._path}' not found.")

		startAnalysis = perf_counter_ns()
		try:
			self._xmlDocument = minidom.parse(str(self._path))
		except Exception as ex:
			raise UnittestException(f"Couldn't open '{self._path}'.") from ex

		endAnalysis = perf_counter_ns()
		self._analysisDuration = (endAnalysis - startAnalysis) / 1e9

	def Write(self, path: Nullable[Path] = None, overwrite: bool = False, regenerate: bool = False) -> None:
		if path is None:
			path = self._path

		if not overwrite and path.exists():
			raise UnittestException(f"JUnit XML file '{path}' can not be written.") \
				from FileExistsError(f"File '{path}' already exists.")

		if regenerate:
			self.Generate(overwrite=True)

		if self._xmlDocument is None:
			ex = UnittestException(f"Internal XML document tree is empty and needs to be generated before write is possible.")
			ex.add_note(f"Call 'JUnitDocument.Generate()' or 'JUnitDocument.Write(..., regenerate=True)'.")
			raise ex

		with path.open("w") as file:
			self._xmlDocument.writexml(file, addindent="\t", encoding="utf-8", newl="\n")

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
					testcase._status = TestcaseStatus.Skipped
				elif node.tagName == "failure":
					testcase._status = TestcaseStatus.Failed
				elif node.tagName == "error":
					testcase._status = TestcaseStatus.Errored
				elif node.tagName == "system-out":
					pass
				elif node.tagName == "system-err":
					pass
				elif node.tagName == "properties":
					pass
				else:
					raise UnittestException(f"Unknown element '{node.tagName}' in junit file.")

		if testcase._status is TestcaseStatus.Unknown:
			testcase._status = TestcaseStatus.Passed

	def Generate(self, overwrite: bool = False) -> None:
		if self._xmlDocument is not None:
			raise UnittestException(f"Internal XML document is populated with data.")

		self._xmlDocument = xmlDocument = Document()
		rootElement = xmlDocument.createElement("testsuites")
		rootElement.setAttribute("name", self._name)
		if self._startTime is not None:
			rootElement.setAttribute("timestamp", f"{self._startTime.isoformat()}")
		if self._totalDuration is not None:
			rootElement.setAttribute("time", f"{self._totalDuration.total_seconds():.6f}")

		xmlDocument.appendChild(rootElement)

		for testsuite in self._testsuites.values():
			self._GenerateTestsuite(testsuite, rootElement)

	def _GenerateTestsuite(self, testsuite: Testsuite, parentElement: Element):
		xmlDocument = parentElement.ownerDocument

		testsuiteElement = xmlDocument.createElement("testsuite")
		testsuiteElement.setAttribute("name", testsuite._name)
		if testsuite._startTime is not None:
			testsuiteElement.setAttribute("timestamp", f"{testsuite._startTime.isoformat()}")
		if testsuite._totalDuration is not None:
			testsuiteElement.setAttribute("time", f"{testsuite._totalDuration.total_seconds():.6f}")

		parentElement.appendChild(testsuiteElement)

		for testsuite in testsuite._testsuites.values():
			self._GenerateTestsuite(testsuite, testsuiteElement)

		for testcase in testsuite._testcases.values():
			self._GenerateTestcase(testcase, testsuiteElement)

	def _GenerateTestcase(self, testcase: Testcase, parentElement: Element):
		xmlDocument = parentElement.ownerDocument

		testcaseElement = xmlDocument.createElement("testcase")
		testcaseElement.setAttribute("name", testcase._name)
		if testcase._totalDuration is not None:
			testcaseElement.setAttribute("time", f"{testcase._totalDuration.total_seconds():.6f}")
		if testcase._assertionCount is not None:
			testcaseElement.setAttribute("assertions", f"{testcase._assertionCount}")

		if testcase._status is TestcaseStatus.Passed:
			pass
		elif testcase._status is TestcaseStatus.Failed:
			failureElement = xmlDocument.createElement("failure")
			testcaseElement.appendChild(failureElement)
		elif testcase._status is TestcaseStatus.Skipped:
			skippedElement = xmlDocument.createElement("skipped")
			testcaseElement.appendChild(skippedElement)
		else:
			errorElement = xmlDocument.createElement("error")

			testcaseElement.appendChild(errorElement)

		parentElement.appendChild(testcaseElement)
