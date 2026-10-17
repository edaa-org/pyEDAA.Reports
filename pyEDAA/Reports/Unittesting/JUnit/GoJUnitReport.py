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
"""
Reader and writer for JUnit XML files written by go-junit-report.

`go-junit-report <https://github.com/jstemmer/go-junit-report>`__ converts the output of ``go test`` into JUnit XML. A
test suite is a Go package named by its import path, a test case is a test, a subtest or an example.
"""
from __future__                       import annotations

from datetime                         import timedelta
from pathlib                          import Path
from re                               import fullmatch
from typing                           import Optional as Nullable, Type, ClassVar

from lxml.etree                       import ElementTree, Element, SubElement, tostring, _Element
from pyTooling.Decorators             import export, InheritDocString, DocStringMergeStrategy
from pyTooling.Stopwatch              import Stopwatch

from pyEDAA.Reports.Unittesting       import UnittestError, TestsuiteKind
from pyEDAA.Reports.Unittesting       import TestsuiteSummary as ut_TestsuiteSummary, Testsuite as ut_Testsuite
from pyEDAA.Reports.Unittesting.JUnit import Testcase as ju_Testcase, Testclass as ju_Testclass
from pyEDAA.Reports.Unittesting.JUnit import Testsuite as ju_Testsuite, TestsuiteSummary as ju_TestsuiteSummary
from pyEDAA.Reports.Unittesting.JUnit import Document as ju_Document


@export
@InheritDocString(ju_Testcase, DocStringMergeStrategy.BaseLast)
class Testcase(ju_Testcase):
	"""
	This is a derived implementation for the go-junit-report JUnit dialect.
	"""


@export
@InheritDocString(ju_Testclass, DocStringMergeStrategy.BaseLast)
class Testclass(ju_Testclass):
	"""
	This is a derived implementation for the go-junit-report JUnit dialect.
	"""


@export
@InheritDocString(ju_Testsuite, DocStringMergeStrategy.BaseLast)
class Testsuite(ju_Testsuite):
	"""
	This is a derived implementation for the go-junit-report JUnit dialect.
	"""

	@classmethod
	def FromTestsuite(cls, testsuite: ut_Testsuite) -> Testsuite:
		"""
		Convert a test suite of the unified test entity data model to the JUnit specific data model's test suite object
		adhering to the go-junit-report JUnit dialect.

		:param testsuite:      Test suite from unified data model.
		:returns:              Test suite from JUnit specific data model (go-junit-report JUnit dialect).
		:raises UnittestError: If a test case of the test suite isn't part of a hierarchy.
		"""
		juTestsuite = cls(
			testsuite._name,
			hostname=testsuite._hostname,
			startTime=testsuite._startTime,
			duration=testsuite._totalDuration,
			status=testsuite._status,
		)

		for tc in testsuite.IterateTestcases():
			ts = tc._parent
			if ts is None:
				raise UnittestError(f"Testcase '{tc._name}' is not part of a hierarchy.")

			classname = ts._name
			ts = ts._parent
			while ts is not None and ts._kind > TestsuiteKind.Logical:
				classname = f"{ts._name}.{classname}"
				ts = ts._parent

			if classname in juTestsuite._testclasses:
				juClass = juTestsuite._testclasses[classname]
			else:
				juClass = Testclass(classname, parent=juTestsuite)

			juClass.AddTestcase(Testcase.FromTestcase(tc))

		return juTestsuite

	def ToTestsuite(self) -> ut_Testsuite:
		"""
		Convert this test suite to a test suite of the unified test entity data model.

		Each test class becomes a child test suite of kind :attr:`~pyEDAA.Reports.Unittesting.TestsuiteKind.Class`, named
		by the whole class name. A class name is a Go import path like ``github.com/user/module/package``, so it isn't
		split at ``.`` into packages.

		:returns: A test suite of the unified test entity data model.
		"""
		return ut_Testsuite(
			self._name,
			kind=TestsuiteKind.Logical,
			hostname=self._hostname,
			startTime=self._startTime,
			totalDuration=self._duration,
			status=self._status,
			testsuites=(testclass.ToTestsuite() for testclass in self._testclasses.values())
		)


@export
@InheritDocString(ju_TestsuiteSummary, DocStringMergeStrategy.BaseLast)
class TestsuiteSummary(ju_TestsuiteSummary):
	"""
	This is a derived implementation for the go-junit-report JUnit dialect.
	"""

	@classmethod
	def FromTestsuiteSummary(cls, testsuiteSummary: ut_TestsuiteSummary) -> TestsuiteSummary:
		"""
		Convert a test suite summary of the unified test entity data model to the JUnit specific data model's test suite
		summary object adhering to the go-junit-report JUnit dialect.

		:param testsuiteSummary: Test suite summary from unified data model.
		:returns:                Test suite summary from JUnit specific data model (go-junit-report JUnit dialect).
		"""
		return cls(
			testsuiteSummary._name,
			startTime=testsuiteSummary._startTime,
			duration=testsuiteSummary._totalDuration,
			status=testsuiteSummary._status,
			testsuites=(Testsuite.FromTestsuite(testsuite) for testsuite in testsuiteSummary._testsuites.values())
		)


@export
class Document(ju_Document):
	"""
	A document reader and writer for the go-junit-report JUnit XML file format.

	This class reads, validates and transforms an XML file in the go-junit-report JUnit format into a JUnit data model. It
	can then be converted into a unified test entity data model.

	In reverse, a JUnit data model instance with the specific go-junit-report JUnit file format can be created from a
	unified test entity data model. This data model can be written as XML into a file.
	"""

	_DIALECT:   ClassVar[str] =             "go-junit-report"  #: Name of the dialect.
	_TESTCASE:  ClassVar[Type[Testcase]] =  Testcase           #: Test case class of the dialect.
	_TESTCLASS: ClassVar[Type[Testclass]] = Testclass          #: Test class class of the dialect.
	_TESTSUITE: ClassVar[Type[Testsuite]] = Testsuite          #: Test suite class of the dialect.

	def Analyze(self) -> None:
		"""
		Analyze the XML file, parse the content into an XML data structure and validate the data structure using an XML
		schema.

		.. hint::

		   The time spend for analysis will be made available via property :data:`AnalysisDuration`.

		The used XML schema definition is specific to the go-junit-report JUnit dialect.
		"""
		xmlSchemaFile = "GoJUnitReport-JUnit.xsd"
		self._Analyze(xmlSchemaFile)

	def Write(self, path: Nullable[Path] = None, overwrite: bool = False, regenerate: bool = False) -> None:
		"""
		Write the data model as XML into a file adhering to the go-junit-report dialect.

		:param path:           Optional, path to the XML file, if internal path shouldn't be used.
		:param overwrite:      Optional, if true, overwrite an existing file.
		:param regenerate:     Optional, if true, regenerate the XML structure from data model.
		:raises UnittestError: If the file cannot be overwritten.
		:raises UnittestError: If the internal XML data structure wasn't generated. |br|
		                       Call ``Document.Generate()`` or ``Document.Write(..., regenerate=True)``.
		:raises UnittestError: If the file cannot be opened or written.
		"""
		if path is None:
			path = self._path

		if not overwrite and path.exists():
			raise UnittestError(f"JUnit XML file '{path}' can not be overwritten.") \
				from FileExistsError(f"File '{path}' already exists.")

		if regenerate:
			self.Generate(overwrite=True)

		if self._xmlDocument is None:
			ex = UnittestError(f"Internal XML document tree is empty and needs to be generated before write is possible.")
			ex.add_note(f"Call 'Document.Generate()' or 'Document.Write(..., regenerate=True)'.")
			raise ex

		content = tostring(self._xmlDocument, encoding="utf-8", xml_declaration=True, pretty_print=True)
		try:
			with path.open("wb") as file:
				file.write(content)
		except OSError as ex:
			raise UnittestError(f"JUnit XML file '{path}' can not be written.") from ex

	def Convert(self) -> None:
		"""
		Convert the parsed and validated XML data structure into a JUnit test entity hierarchy.

		This method converts the root element.

		.. hint::

		   The time spend for model conversion will be made available via property :data:`ModelConversionDuration`.

		:raises UnittestError: If XML was not read and parsed before. |br|
		                       Call ``Document.Analyze()`` or create the document using
		                       ``Document(path, analyzeAndConvert=True)``.
		"""
		if self._xmlDocument is None:
			ex = UnittestError(f"JUnit XML file '{self._path}' needs to be read and analyzed by an XML parser.")
			ex.add_note(f"Call 'Document.Analyze()' or create the document using 'Document(path, analyzeAndConvert=True)'.")
			raise ex

		with Stopwatch() as sw:
			rootElement: _Element = self._xmlDocument.getroot()

			self._name = self._ConvertName(rootElement, optional=True)
			self._duration = self._ConvertTime(rootElement, optional=True)

			for rootNode in rootElement.iterchildren(tag="testsuite"):  # type: _Element
				self._ConvertTestsuite(self, rootNode)

			self.Aggregate()

		self._modelConversion = sw.Duration

	def _ConvertTestsuite(self, parent: TestsuiteSummary, testsuitesNode: _Element) -> None:
		"""
		Convert the XML data structure of a ``<testsuite>`` to a test suite.

		A ``<testsuite>`` whose ``<system-out>`` is ``go test``'s result line of a package without tests
		(``<tab><import path><tab><tab>coverage: ...``) is named by that import path. go-junit-report names such a package
		by its option ``-package-name``, which is empty by default.

		This method uses private helper methods provided by the base-class.

		:param parent:         The test suite summary as a parent element in the test entity hierarchy.
		:param testsuitesNode: The current XML element node representing a test suite.
		:raises UnittestError: If the test suite has an empty name and no result line naming the package.
		"""
		name = self._ConvertName(testsuitesNode, optional=False)
		if (systemOutNode := testsuitesNode.find("system-out")) is not None and systemOutNode.text is not None:
			if (match := fullmatch(r"\t(?P<importPath>\S+)\t\tcoverage: .+", systemOutNode.text)) is not None:
				name = match["importPath"]

		if name == "":
			ex = UnittestError(f"Test suite with id '{testsuitesNode.attrib['id']}' has an empty name.")
			ex.add_note("go-junit-report names a package by option '-package-name', if it found no result line for it.")
			raise ex

		newTestsuite = self._TESTSUITE(
			name,
			self._ConvertHostname(testsuitesNode, default=None, optional=True),
			self._ConvertTimestamp(testsuitesNode, optional=True),
			self._ConvertTime(testsuitesNode, optional=False),
			parent=parent
		)

		self._ConvertTestsuiteChildren(testsuitesNode, newTestsuite)

	def Generate(self, overwrite: bool = False) -> None:
		"""
		Generate the internal XML data structure from test suites and test cases.

		This method generates the XML root element (``<testsuites>``) and recursively calls other generated methods.

		:param overwrite:      Optional, overwrite the internal XML data structure.
		:raises UnittestError: If overwrite is false and the internal XML data structure is not empty.
		"""
		if not overwrite and self._xmlDocument is not None:
			raise UnittestError(f"Internal XML document is populated with data.")

		rootElement = Element("testsuites")
		rootElement.attrib["name"] = self._name
		if self._duration is not None:
			rootElement.attrib["time"] = f"{self._duration.total_seconds():.6f}"
		rootElement.attrib["tests"] = str(self._tests)
		rootElement.attrib["errors"] = str(self._errored)
		rootElement.attrib["failures"] = str(self._failed)
		rootElement.attrib["skipped"] = str(self._skipped)

		self._xmlDocument = ElementTree(rootElement)

		for testsuite in self._testsuites.values():
			self._GenerateTestsuite(testsuite, rootElement)

	def _GenerateTestsuite(self, testsuite: Testsuite, parentElement: _Element) -> None:
		"""
		Generate the internal XML data structure for a test suite.

		This method generates the XML element (``<testsuite>``) and recursively calls other generated methods.

		The ``id`` is the test suite's index in the document. Like go-junit-report, a test suite without a duration gets the
		sum of its test cases' durations as ``time``.

		:param testsuite:     The test suite to convert to an XML data structures.
		:param parentElement: The parent XML data structure element, this data structure part will be added to.
		"""
		testsuiteId = len(parentElement)
		testsuiteElement = SubElement(parentElement, "testsuite")
		testsuiteElement.attrib["name"] = testsuite._name
		testsuiteElement.attrib["tests"] = str(testsuite._tests)
		testsuiteElement.attrib["failures"] = str(testsuite._failed)
		testsuiteElement.attrib["errors"] = str(testsuite._errored)
		testsuiteElement.attrib["id"] = str(testsuiteId)
		if testsuite._hostname is not None:
			testsuiteElement.attrib["hostname"] = testsuite._hostname
		testsuiteElement.attrib["skipped"] = str(testsuite._skipped)
		if testsuite._duration is not None:
			duration = testsuite._duration
		else:
			duration = sum(
				(
					testcase._duration
					for testclass in testsuite._testclasses.values()
					for testcase in testclass._testcases.values()
					if testcase._duration is not None
				),
				timedelta()
			)
		testsuiteElement.attrib["time"] = f"{duration.total_seconds():.6f}"
		if testsuite._startTime is not None:
			testsuiteElement.attrib["timestamp"] = f"{testsuite._startTime.isoformat()}"

		for testclass in testsuite._testclasses.values():
			for tc in testclass._testcases.values():
				self._GenerateTestcase(tc, testsuiteElement)

	def _GenerateTestcase(self, testcase: Testcase, parentElement: _Element) -> None:
		"""
		Generate the internal XML data structure for a test case.

		This method generates the XML element (``<testcase>``) and recursively calls other generated methods.

		:param testcase:      The test case to convert to an XML data structures.
		:param parentElement: The parent XML data structure element, this data structure part will be added to.
		"""
		testcaseElement = SubElement(parentElement, "testcase")
		testcaseElement.attrib["name"] = testcase._name
		testcaseElement.attrib["classname"] = testcase.Classname
		if testcase._duration is not None:
			testcaseElement.attrib["time"] = f"{testcase._duration.total_seconds():.6f}"

		self._GenerateTestcaseChildren(testcase, testcaseElement)

	def _GenerateTestcaseChildren(self, testcase: Testcase, testcaseElement: _Element) -> None:
		"""
		Generate the child elements of a ``<testcase>`` from the test case's status, message, details and captured output.

		Like go-junit-report, every ``<skipped>``, ``<error>`` and ``<failure>`` element has a ``message`` attribute; it's
		empty for a test case without a message.

		:param testcase:        The test case to convert to XML child elements.
		:param testcaseElement: The ``<testcase>`` element, the child elements will be added to.
		"""
		super()._GenerateTestcaseChildren(testcase, testcaseElement)

		for statusElement in testcaseElement.iterchildren("skipped", "error", "failure"):  # type: _Element
			if "message" not in statusElement.attrib:
				statusElement.attrib["message"] = ""
