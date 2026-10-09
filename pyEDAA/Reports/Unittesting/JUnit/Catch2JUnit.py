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
Reader and writer for the JUnit XML report written by Catch2's JUnit reporter.

.. seealso::

   :ref:`UNITTEST/SpecificDataModel/JUnit/Dialect/Catch2`
      |rarr| Differences of the Catch2 JUnit dialect.
   :ref:`SCHEMAS/Catch2-JUnit`
      |rarr| XML schema of the Catch2 JUnit dialect.
"""
from __future__                       import annotations

from datetime                         import timezone
from pathlib                          import Path
from typing                           import Optional as Nullable, Type, ClassVar

from lxml.etree                       import ElementTree, Element, SubElement, tostring, _Element
from pyTooling.Common                 import firstValue
from pyTooling.Decorators             import export, InheritDocString, DocStringMergeStrategy
from pyTooling.Stopwatch              import Stopwatch

from pyEDAA.Reports.Unittesting       import UnittestError, TestsuiteKind, TestcaseStatus
from pyEDAA.Reports.Unittesting       import TestsuiteSummary as ut_TestsuiteSummary, Testsuite as ut_Testsuite
from pyEDAA.Reports.Unittesting.JUnit import Testcase as ju_Testcase, Testclass as ju_Testclass
from pyEDAA.Reports.Unittesting.JUnit import Testsuite as ju_Testsuite, TestsuiteSummary as ju_TestsuiteSummary
from pyEDAA.Reports.Unittesting.JUnit import Document as ju_Document


@export
@InheritDocString(ju_Testcase, DocStringMergeStrategy.BaseLast)
class Testcase(ju_Testcase):
	"""
	This is a derived implementation for the Catch2 JUnit dialect.
	"""


@export
@InheritDocString(ju_Testclass, DocStringMergeStrategy.BaseLast)
class Testclass(ju_Testclass):
	"""
	This is a derived implementation for the Catch2 JUnit dialect.
	"""


@export
@InheritDocString(ju_Testsuite, DocStringMergeStrategy.BaseLast)
class Testsuite(ju_Testsuite):
	"""
	This is a derived implementation for the Catch2 JUnit dialect.
	"""

	@classmethod
	def FromTestsuite(cls, testsuite: ut_Testsuite) -> Testsuite:
		"""
		Convert a test suite of the unified test entity data model to the JUnit specific data model's test suite object
		adhering to the Catch2 JUnit dialect.

		:param testsuite:      Test suite from unified data model.
		:returns:              Test suite from JUnit specific data model (Catch2 JUnit dialect).
		:raises UnittestError: If a test case is not part of a test suite hierarchy.
		"""
		juTestsuite = cls(
			testsuite._name,
			hostname=testsuite._hostname,
			startTime=testsuite._startTime,
			duration=testsuite._totalDuration,
			status= testsuite._status,
		)

		juTestsuite._tests = testsuite._tests
		juTestsuite._skipped = testsuite._skipped
		juTestsuite._errored = testsuite._errored
		juTestsuite._failed = testsuite._failed
		juTestsuite._passed = testsuite._passed

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


@export
@InheritDocString(ju_TestsuiteSummary, DocStringMergeStrategy.BaseLast)
class TestsuiteSummary(ju_TestsuiteSummary):
	"""
	This is a derived implementation for the Catch2 JUnit dialect.
	"""

	@classmethod
	def FromTestsuiteSummary(cls, testsuiteSummary: ut_TestsuiteSummary) -> TestsuiteSummary:
		"""
		Convert a test suite summary of the unified test entity data model to the JUnit specific data model's test suite
		summary object adhering to the Catch2 JUnit dialect.

		:param testsuiteSummary: Test suite summary from unified data model.
		:returns:                Test suite summary from JUnit specific data model (Catch2 JUnit dialect).
		"""
		return cls(
			testsuiteSummary._name,
			startTime=testsuiteSummary._startTime,
			duration=testsuiteSummary._totalDuration,
			status=testsuiteSummary._status,
			testsuites=(ut_Testsuite.FromTestsuite(testsuite) for testsuite in testsuiteSummary._testsuites.values())
		)


@export
class Document(ju_Document):
	"""
	A document reader and writer for the Catch2 JUnit XML file format.

	This class reads, validates and transforms an XML file in the Catch2 JUnit format into a JUnit data model. It can then
	be converted into a unified test entity data model.

	In reverse, a JUnit data model instance with the specific Catch2 JUnit file format can be created from a unified test
	entity data model. This data model can be written as XML into a file.
	"""

	_DIALECT:   ClassVar[str] =             "Catch2 + JUnit"  #: Name of the dialect in messages.
	_TESTCASE:  ClassVar[Type[Testcase]] =  Testcase          #: Class of test cases read by this dialect.
	_TESTCLASS: ClassVar[Type[Testclass]] = Testclass         #: Class of test classes read by this dialect.
	_TESTSUITE: ClassVar[Type[Testsuite]] = Testsuite         #: Class of test suites read by this dialect.

	@classmethod
	def FromTestsuiteSummary(cls, xmlReportFile: Path, testsuiteSummary: ut_TestsuiteSummary):
		doc = cls(xmlReportFile)
		doc._name = testsuiteSummary._name
		doc._startTime = testsuiteSummary._startTime
		doc._duration = testsuiteSummary._totalDuration
		doc._status = testsuiteSummary._status
		doc._tests = testsuiteSummary._tests
		doc._skipped = testsuiteSummary._skipped
		doc._errored = testsuiteSummary._errored
		doc._failed = testsuiteSummary._failed
		doc._passed = testsuiteSummary._passed

		doc.AddTestsuites(Testsuite.FromTestsuite(testsuite) for testsuite in testsuiteSummary._testsuites.values())

		return doc

	def Analyze(self) -> None:
		"""
		Analyze the XML file, parse the content into an XML data structure and validate the data structure using an XML
		schema.

		.. hint::

		   The time spend for analysis will be made available via property :data:`AnalysisDuration`.

		The used XML schema definition is specific to the Catch2 JUnit dialect.
		"""
		xmlSchemaFile = "Catch2-JUnit.xsd"
		self._Analyze(xmlSchemaFile)

	def Write(self, path: Nullable[Path] = None, overwrite: bool = False, regenerate: bool = False) -> None:
		"""
		Write the data model as XML into a file adhering to the Catch2 dialect.

		:param path:           Optional, path to the XML file, if internal path shouldn't be used.
		:param overwrite:      Optional, if true, overwrite an existing file.
		:param regenerate:     Optional, if true, regenerate the XML structure from data model.
		:raises UnittestError: If the file cannot be overwritten.
		:raises UnittestError: If the internal XML data structure wasn't generated.
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
			ex.add_note(f"Call 'JUnitDocument.Generate()' or 'JUnitDocument.Write(..., regenerate=True)'.")
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

		:raises UnittestError: If XML was not read and parsed before.
		"""
		if self._xmlDocument is None:
			ex = UnittestError(f"JUnit XML file '{self._path}' needs to be read and analyzed by an XML parser.")
			ex.add_note(f"Call 'JUnitDocument.Analyze()' or create the document using 'JUnitDocument(path, parse=True)'.")
			raise ex

		with Stopwatch() as sw:
			rootElement: _Element = self._xmlDocument.getroot()

			self._name = self._ConvertName(rootElement, optional=True)

			for rootNode in rootElement.iterchildren(tag="testsuite"):  # type: _Element
				self._ConvertTestsuite(self, rootNode)

			self.Aggregate()

		self._modelConversion = sw.Duration

	def _ConvertTestsuite(self, parent: TestsuiteSummary, testsuitesNode: _Element) -> None:
		"""
		Convert the XML data structure of a ``<testsuite>`` to a test suite.

		This method uses private helper methods provided by the base-class.

		:param parent:         The test suite summary as a parent element in the test entity hierarchy.
		:param testsuitesNode: The current XML element node representing a test suite.
		"""
		newTestsuite = Testsuite(
			self._ConvertName(testsuitesNode, optional=False),
			self._ConvertHostname(testsuitesNode, optional=False),
			self._ConvertTimestamp(testsuitesNode, optional=False),
			self._ConvertTime(testsuitesNode, optional=True),
			parent=parent
		)

		self._ConvertTestsuiteChildren(testsuitesNode, newTestsuite)

	def _ConvertTestcaseChildren(self, testcaseNode: _Element, newTestcase: Testcase) -> None:
		"""
		Convert the child elements of a ``<testcase>`` to the test case's status, message, details and captured output.

		A test case tagged with ``[!mayfail]`` or ``[!shouldfail]`` failing as expected has a ``<skipped>`` element in front
		of its ``<failure>`` or ``<error>`` element. Its status is skipped, its message is the ``<skipped>`` element's
		message, its details are the text of the ``<failure>`` or ``<error>`` element.

		:param testcaseNode:   The current XML element node representing a test case.
		:param newTestcase:    The test case to update.
		:raises UnittestError: If an unknown element is found.
		"""
		super()._ConvertTestcaseChildren(testcaseNode, newTestcase)

		statusNodes = list(testcaseNode.iterchildren("skipped", "failure", "error"))
		if len(statusNodes) == 2:
			newTestcase._status = TestcaseStatus.Skipped
			newTestcase._message = statusNodes[0].attrib["message"]

	def Generate(self, overwrite: bool = False) -> None:
		"""
		Generate the internal XML data structure from test suites and test cases.

		This method generates the XML root element (``<testsuites>``) without attributes and recursively calls other
		generated methods.

		:param overwrite:      Optional, overwrite the internal XML data structure.
		:raises UnittestError: If overwrite is false and the internal XML data structure is not empty.
		:raises UnittestError: If the document has not exactly one test suite.
		"""
		if not overwrite and self._xmlDocument is not None:
			raise UnittestError(f"Internal XML document is populated with data.")

		if self.TestsuiteCount != 1:
			ex = UnittestError(f"The {self._DIALECT} format requires exactly one test suite.")
			ex.add_note(f"Found {self.TestsuiteCount} test suites.")
			raise ex

		rootElement = Element("testsuites")

		self._xmlDocument = ElementTree(rootElement)

		self._GenerateTestsuite(firstValue(self._testsuites), rootElement)

	def _GenerateTestsuite(self, testsuite: Testsuite, parentElement: _Element) -> None:
		"""
		Generate the internal XML data structure for a test suite.

		This method generates the XML element (``<testsuite>``) and recursively calls other generated methods. The
		``tests``, ``failures``, ``errors`` and ``skipped`` attributes count test cases, an unrecorded hostname is written
		as ``tbd``.

		:param testsuite:      The test suite to convert to an XML data structures.
		:param parentElement:  The parent XML data structure element, this data structure part will be added to.
		:raises UnittestError: If the test suite has no start time.
		"""
		if testsuite._startTime is None:
			raise UnittestError(f"The {self._DIALECT} format requires a timestamp on <testsuite>, but the report has none.")

		testsuiteElement = SubElement(parentElement, "testsuite")
		testsuiteElement.attrib["name"] = testsuite._name
		testsuiteElement.attrib["errors"] = str(testsuite._errored)
		testsuiteElement.attrib["failures"] = str(testsuite._failed)
		testsuiteElement.attrib["skipped"] = str(testsuite._skipped)
		testsuiteElement.attrib["tests"] = str(testsuite._tests)
		testsuiteElement.attrib["hostname"] = "tbd" if testsuite._hostname is None else testsuite._hostname
		if testsuite._duration is not None:
			testsuiteElement.attrib["time"] = f"{testsuite._duration.total_seconds():.3f}"
		testsuiteElement.attrib["timestamp"] = testsuite._startTime.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

		for testclass in testsuite._testclasses.values():
			for tc in testclass._testcases.values():
				self._GenerateTestcase(tc, testsuiteElement)

		SubElement(testsuiteElement, "system-out")
		SubElement(testsuiteElement, "system-err")

	def _GenerateTestcase(self, testcase: Testcase, parentElement: _Element) -> None:
		"""
		Generate the internal XML data structure for a test case.

		This method generates the XML element (``<testcase>``) and recursively calls other generated methods.

		:param testcase:       The test case to convert to an XML data structures.
		:param parentElement:  The parent XML data structure element, this data structure part will be added to.
		:raises UnittestError: If the test case has no duration.
		"""
		if testcase._duration is None:
			raise UnittestError(f"The {self._DIALECT} format requires a time on <testcase>, but the report has none.")

		testcaseElement = SubElement(parentElement, "testcase")
		testcaseElement.attrib["classname"] = testcase.Classname
		testcaseElement.attrib["name"] = testcase._name
		testcaseElement.attrib["time"] = f"{testcase._duration.total_seconds():.3f}"
		testcaseElement.attrib["status"] = "run"

		self._GenerateTestcaseChildren(testcase, testcaseElement)
