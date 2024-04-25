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

from lxml.etree                 import XMLParser, parse, XMLSchema, XMLSyntaxError, _ElementTree, _Element, _Comment
from lxml.etree                 import ElementTree, Element, SubElement, tostring
from pyTooling.Decorators       import export

from pyEDAA.Reports             import resources, getResourceFile
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
	_xmlDocument:      Nullable[_ElementTree]

	def __init__(self, xmlReportFile: Path, parse: bool = False, readerMode: JUnitReaderMode = JUnitReaderMode.Default):
		super().__init__("Unprocessed JUnit XML file")
		ut_Document.__init__(self, xmlReportFile)

		self._readerMode = readerMode
		self._xmlDocument = None

		if parse:
			self.Read()
			self.Parse()

	@classmethod
	def FromTestsuiteSummary(cls, xmlReportFile: Path, testsuiteSummary: TestsuiteSummary):
		doc = cls(xmlReportFile)
		doc._name = testsuiteSummary._name
		doc._startTime = testsuiteSummary._startTime
		doc._setupDuration = testsuiteSummary._setupDuration
		doc._teardownDuration = testsuiteSummary._teardownDuration
		doc._totalDuration = testsuiteSummary._totalDuration
		doc._status = testsuiteSummary._status
		doc._warningCount = testsuiteSummary._warningCount
		doc._errorCount = testsuiteSummary._errorCount
		doc._fatalCount = testsuiteSummary._fatalCount

		for name, testsuite in testsuiteSummary._testsuites.items():
			doc._testsuites[name] = testsuite
			testsuite._parent = doc

		return doc

	def Read(self) -> None:
		if not self._path.exists():
			raise UnittestException(f"JUnit XML file '{self._path}' does not exist.") \
				from FileNotFoundError(f"File '{self._path}' not found.")

		startAnalysis = perf_counter_ns()
		try:
			# xmlSchemaFile = getResourceFile(resources, "JUnit.xsd")
			xmlSchemaFile = getResourceFile(resources, "Unittesting.xsd")
			schemaParser = XMLParser(ns_clean=True)
			schemaRoot = parse(xmlSchemaFile, schemaParser)

			junitSchema = XMLSchema(schemaRoot)
			junitParser = XMLParser(schema=junitSchema, ns_clean=True)
			junitDocument = parse(self._path, parser=junitParser)

			self._xmlDocument = junitDocument
		except XMLSyntaxError as ex:
			print(ex)

			print(junitParser.error_log)
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

		with path.open("wb") as file:
			file.write(tostring(self._xmlDocument, encoding="utf-8", xml_declaration=True, pretty_print=True))

	def Parse(self) -> None:
		if self._xmlDocument is None:
			ex = UnittestException(f"JUnit XML file '{self._path}' needs to be read and analyzed by an XML parser.")
			ex.add_note(f"Call 'JUnitDocument.Read()' or create document using 'JUnitDocument(path, parse=True)'.")
			raise ex

		startConversion = perf_counter_ns()
		rootElement: _Element = self._xmlDocument.getroot()

		self._name =          rootElement.attrib["name"]                              if "name"      in rootElement.attrib else "root"
		self._startTime =     datetime.fromisoformat(rootElement.attrib["timestamp"]) if "timestamp" in rootElement.attrib else None
		self._totalDuration = timedelta(seconds=float(rootElement.attrib["time"]))    if "time"      in rootElement.attrib else None

		# tests = rootElement.getAttribute("tests")
		# skipped = rootElement.getAttribute("skipped")
		# errors = rootElement.getAttribute("errors")
		# failures = rootElement.getAttribute("failures")
		# assertions = rootElement.getAttribute("assertions")

		for rootNode in rootElement.iterchildren(tag="testsuite"):  # type: _Element
			self._ParseTestsuite(self, rootNode)

		self.Aggregate()
		endConversation = perf_counter_ns()
		self._modelConversion = (endConversation - startConversion) / 1e9

	def _ParseTestsuite(self, parentTestsuite: Testsuite, testsuitesNode: _Element) -> None:
		name = testsuitesNode.attrib["name"]

		kwargs = {}
		if "timestamp" in testsuitesNode.attrib:
			kwargs["startTime"] = datetime.fromisoformat(testsuitesNode.attrib["timestamp"])
		if "time" in testsuitesNode.attrib:
			kwargs["totalDuration"] = timedelta(seconds=float(testsuitesNode.attrib["time"]))

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

		for node in testsuitesNode.iterchildren():   # type: _Element
			if node.tag == "testsuite":
				self._ParseTestsuite(currentTestsuite, node)
			elif node.tag == "testcase":
				self._ParseTestcase(currentTestsuite, node)

	def _ParseTestcase(self, parentTestsuite: Testsuite, testsuiteNode: _Element) -> None:
		className = testsuiteNode.attrib["classname"]
		name = testsuiteNode.attrib["name"]
		time = float(testsuiteNode.attrib["time"])

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

		for node in testsuiteNode.iterchildren():   # type: _Element
			if isinstance(node, _Comment):
				pass
			elif isinstance(node, _Element):
				if node.tag == "skipped":
					testcase._status = TestcaseStatus.Skipped
				elif node.tag == "failure":
					testcase._status = TestcaseStatus.Failed
				elif node.tag == "error":
					testcase._status = TestcaseStatus.Errored
				elif node.tag == "system-out":
					pass
				elif node.tag == "system-err":
					pass
				elif node.tag == "properties":
					pass
				else:
					raise UnittestException(f"Unknown element '{node.tag}' in junit file.")
			else:
				pass

		if testcase._status is TestcaseStatus.Unknown:
			testcase._status = TestcaseStatus.Passed

	def Generate(self, overwrite: bool = False) -> None:
		if self._xmlDocument is not None:
			raise UnittestException(f"Internal XML document is populated with data.")

		rootElement = Element("testsuites")
		rootElement.attrib["name"] = self._name
		if self._startTime is not None:
			rootElement.attrib["timestamp"] = f"{self._startTime.isoformat()}"
		if self._totalDuration is not None:
			rootElement.attrib["time"] = f"{self._totalDuration.total_seconds():.6f}"
		rootElement.attrib["tests"] = str(self._tests)
		rootElement.attrib["failures"] = str(self._failed)
		rootElement.attrib["errors"] = str(self._errored)
		rootElement.attrib["skipped"] = str(self._skipped)
		# if self._assertionCount is not None:
		# 	rootElement.attrib["assertions"] = f"{self._assertionCount}"

		self._xmlDocument = ElementTree(rootElement)

		for testsuite in self._testsuites.values():
			self._GenerateTestsuite(testsuite, rootElement)

	def _GenerateTestsuite(self, testsuite: Testsuite, parentElement: _Element):
		testsuiteElement = SubElement(parentElement, "testsuite")
		testsuiteElement.attrib["name"] = testsuite._name
		if testsuite._startTime is not None:
			testsuiteElement.attrib["timestamp"] = f"{testsuite._startTime.isoformat()}"
		if testsuite._totalDuration is not None:
			testsuiteElement.attrib["time"] = f"{testsuite._totalDuration.total_seconds():.6f}"
		testsuiteElement.attrib["tests"] = str(testsuite._tests)
		testsuiteElement.attrib["failures"] = str(testsuite._failed)
		testsuiteElement.attrib["errors"] = str(testsuite._errored)
		testsuiteElement.attrib["skipped"] = str(testsuite._skipped)
		# if testsuite._assertionCount is not None:
		# 	testsuiteElement.attrib["assertions"] = f"{testsuite._assertionCount}"

		for ts in testsuite._testsuites.values():
			self._GenerateTestsuite(ts, testsuiteElement)

		for tc in testsuite._testcases.values():
			self._GenerateTestcase(tc, testsuiteElement)

	def _GenerateTestcase(self, testcase: Testcase, parentElement: _Element):
		testcaseElement = SubElement(parentElement, "testcase")
		testcaseElement.attrib["name"] = testcase._name
		if testcase._totalDuration is not None:
			testcaseElement.attrib["time"] = f"{testcase._totalDuration.total_seconds():.6f}"
		if testcase._assertionCount is not None:
			testcaseElement.attrib["assertions"] = f"{testcase._assertionCount}"

		if testcase._status is TestcaseStatus.Passed:
			pass
		elif testcase._status is TestcaseStatus.Failed:
			failureElement = SubElement(testcaseElement, "failure")
		elif testcase._status is TestcaseStatus.Skipped:
			skippedElement = SubElement(testcaseElement, "skipped")
		else:
			errorElement = SubElement(testcaseElement, "error")
