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
Reader and writer for the JUnit XML dialect of the .NET test logger ``JunitXml.TestLogger``.

The logger writes it, when ``dotnet test`` is called with ``--logger junit``.

.. seealso::

   :ref:`UNITTEST/SpecificDataModel/JUnit/Dialect/TestLogger`
      |rarr| How the logger's report is read into the unified data model.
"""
from __future__                       import annotations

from datetime                         import timezone
from pathlib                          import Path
from typing                           import Optional as Nullable, ClassVar, Type

from lxml.etree                       import ElementTree, Element, SubElement, tostring, _Element
from pyTooling.Common                 import firstValue
from pyTooling.Decorators             import export, InheritDocString, DocStringMergeStrategy
from pyTooling.Stopwatch              import Stopwatch

from pyEDAA.Reports.Unittesting       import UnittestError, TestcaseStatus, TestsuiteKind
from pyEDAA.Reports.Unittesting       import TestsuiteSummary as ut_TestsuiteSummary, Testsuite as ut_Testsuite
from pyEDAA.Reports.Unittesting.JUnit import Testcase as ju_Testcase, Testclass as ju_Testclass
from pyEDAA.Reports.Unittesting.JUnit import Testsuite as ju_Testsuite, TestsuiteSummary as ju_TestsuiteSummary
from pyEDAA.Reports.Unittesting.JUnit import Document as ju_Document


@export
@InheritDocString(ju_Testcase, DocStringMergeStrategy.BaseLast)
class Testcase(ju_Testcase):
	"""
	This is a derived implementation for the JunitXml.TestLogger JUnit dialect.
	"""


@export
@InheritDocString(ju_Testclass, DocStringMergeStrategy.BaseLast)
class Testclass(ju_Testclass):
	"""
	This is a derived implementation for the JunitXml.TestLogger JUnit dialect.
	"""


@export
@InheritDocString(ju_Testsuite, DocStringMergeStrategy.BaseLast)
class Testsuite(ju_Testsuite):
	"""
	This is a derived implementation for the JunitXml.TestLogger JUnit dialect.
	"""

	@classmethod
	def FromTestsuite(cls, testsuite: ut_Testsuite) -> Testsuite:
		"""
		Convert a test suite of the unified test entity data model to the JUnit specific data model's test suite object
		adhering to the JunitXml.TestLogger JUnit dialect.

		:param testsuite:      Test suite from unified data model.
		:returns:              Test suite from JUnit specific data model (JunitXml.TestLogger JUnit dialect).
		:raises UnittestError: If a test case is not part of a test suite hierarchy.
		"""
		juTestsuite = cls(
			testsuite._name,
			hostname=testsuite._hostname,
			startTime=testsuite._startTime,
			duration=testsuite._totalDuration,
			status=testsuite._status,
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

	def ToTestsuite(self) -> ut_Testsuite:
		"""
		Convert this test suite to a test suite of the unified test entity data model.

		A test class' name is split into its namespace and its class at the last dot before the arguments of a
		parameterized test class. Each part of the namespace becomes a test suite of kind
		:attr:`~pyEDAA.Reports.Unittesting.TestsuiteKind.Namespace`, the class a test suite of kind
		:attr:`~pyEDAA.Reports.Unittesting.TestsuiteKind.Class` holding the test cases. A nested class keeps the name .NET
		gives it, e.g. ``Outer+Inner``.

		:returns: Test suite of the unified test entity data model.
		"""
		testsuite = ut_Testsuite(
			self._name,
			kind=TestsuiteKind.Logical,
			hostname=self._hostname,
			startTime=self._startTime,
			totalDuration=self._duration,
			status=self._status,
		)

		for testclass in self._testclasses.values():
			namespace, separator, _ = testclass._name.partition("(")[0].rpartition(".")

			suite = testsuite
			if namespace != "":
				for element in namespace.split("."):
					if element in suite._testsuites:
						suite = suite._testsuites[element]
					else:
						suite = ut_Testsuite(element, kind=TestsuiteKind.Namespace, parent=suite)

			ut_Testsuite(
				testclass._name[len(namespace) + len(separator):],
				kind=TestsuiteKind.Class,
				testcases=(tc.ToTestcase() for tc in testclass._testcases.values()),
				parent=suite
			)

		return testsuite


@export
@InheritDocString(ju_TestsuiteSummary, DocStringMergeStrategy.BaseLast)
class TestsuiteSummary(ju_TestsuiteSummary):
	"""
	This is a derived implementation for the JunitXml.TestLogger JUnit dialect.
	"""

	@classmethod
	def FromTestsuiteSummary(cls, testsuiteSummary: ut_TestsuiteSummary) -> TestsuiteSummary:
		"""
		Convert a test suite summary of the unified test entity data model to the JUnit specific data model's test suite
		summary object adhering to the JunitXml.TestLogger JUnit dialect.

		:param testsuiteSummary: Test suite summary from unified data model.
		:returns:                Test suite summary from JUnit specific data model (JunitXml.TestLogger JUnit dialect).
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
	A document reader and writer for the JunitXml.TestLogger JUnit XML file format.

	This class reads, validates and transforms an XML file in the JunitXml.TestLogger JUnit format into a JUnit data
	model. It can then be converted into a unified test entity data model.

	In reverse, a JUnit data model instance with the specific JunitXml.TestLogger JUnit file format can be created from a
	unified test entity data model. This data model can be written as XML into a file.
	"""

	_DIALECT:   ClassVar[str] =             "JunitXml.TestLogger JUnit"  #: Name of the dialect in error messages.
	_TESTCASE:  ClassVar[Type[Testcase]] =  Testcase                     #: Test case class of this dialect.
	_TESTCLASS: ClassVar[Type[Testclass]] = Testclass                    #: Test class class of this dialect.
	_TESTSUITE: ClassVar[Type[Testsuite]] = Testsuite                    #: Test suite class of this dialect.

	@classmethod
	def FromTestsuiteSummary(cls, xmlReportFile: Path, testsuiteSummary: ut_TestsuiteSummary) -> Document:
		"""
		Convert a test suite summary of the unified test entity data model to a document adhering to the
		JunitXml.TestLogger JUnit dialect.

		:param xmlReportFile:    Path of the XML file the document is written to.
		:param testsuiteSummary: Test suite summary from unified data model.
		:returns:                Document of the JUnit specific data model (JunitXml.TestLogger JUnit dialect).
		"""
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

		The used XML schema definition is specific to the JunitXml.TestLogger JUnit dialect.
		"""
		xmlSchemaFile = "TestLogger-JUnit.xsd"
		self._Analyze(xmlSchemaFile)

	def Write(self, path: Nullable[Path] = None, overwrite: bool = False, regenerate: bool = False) -> None:
		"""
		Write the data model as XML into a file adhering to the JunitXml.TestLogger JUnit dialect.

		:param path:           Optional, path to the XML file, if internal path shouldn't be used.
		:param overwrite:      Optional, if true, overwrite an existing file.
		:param regenerate:     Optional, if true, regenerate the XML structure from data model.
		:raises UnittestError: If the file cannot be overwritten.
		:raises UnittestError: If the internal XML data structure wasn't generated. |br|
		                       Call 'Document.Generate()' or 'Document.Write(..., regenerate=True)'.
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

		This method converts the root element. As ``<testsuites>`` has no attributes, the summary's start time is the one
		of the first test suite: the logger writes the start of the test run into every ``<testsuite>``.

		.. hint::

		   The time spend for model conversion will be made available via property :data:`ModelConversionDuration`.

		:raises UnittestError: If XML was not read and parsed before. |br|
		                       Call 'Document.Analyze()' or create the document using
		                       'Document(path, analyzeAndConvert=True)'.
		"""
		if self._xmlDocument is None:
			ex = UnittestError(f"JUnit XML file '{self._path}' needs to be read and analyzed by an XML parser.")
			ex.add_note(f"Call 'Document.Analyze()' or create the document using 'Document(path, analyzeAndConvert=True)'.")
			raise ex

		with Stopwatch() as sw:
			rootElement: _Element = self._xmlDocument.getroot()

			self._name = self._ConvertName(rootElement, optional=True)

			for rootNode in rootElement.iterchildren(tag="testsuite"):  # type: _Element
				self._ConvertTestsuite(self, rootNode)

			if len(self._testsuites) > 0:
				self._startTime = firstValue(self._testsuites)._startTime

			self.Aggregate()

		self._modelConversion = sw.Duration

	def _ConvertTestsuite(self, parent: TestsuiteSummary, testsuitesNode: _Element) -> None:
		"""
		Convert the XML data structure of a ``<testsuite>`` to a test suite.

		This method uses private helper methods provided by the base-class. The ``timestamp`` is read as UTC. The
		attributes ``id`` (always ``0``) and ``package`` (the same as ``name``) are not read.

		:param parent:         The test suite summary as a parent element in the test entity hierarchy.
		:param testsuitesNode: The current XML element node representing a test suite.
		"""
		newTestsuite = self._TESTSUITE(
			self._ConvertName(testsuitesNode, optional=False),
			self._ConvertHostname(testsuitesNode, optional=False),
			self._ConvertTimestamp(testsuitesNode, optional=False).replace(tzinfo=timezone.utc),
			self._ConvertTime(testsuitesNode, optional=False),
			parent=parent
		)

		self._ConvertTestsuiteChildren(testsuitesNode, newTestsuite)

	def Generate(self, overwrite: bool = False) -> None:
		"""
		Generate the internal XML data structure from test suites and test cases.

		This method generates the XML root element (``<testsuites>``), without attributes, and recursively calls other
		generated methods.

		:param overwrite:      Optional, overwrite the internal XML data structure.
		:raises UnittestError: If overwrite is false and the internal XML data structure is not empty.
		"""
		if not overwrite and self._xmlDocument is not None:
			raise UnittestError(f"Internal XML document is populated with data.")

		rootElement = Element("testsuites")

		self._xmlDocument = ElementTree(rootElement)

		for testsuite in self._testsuites.values():
			self._GenerateTestsuite(testsuite, rootElement)

	def _GenerateTestsuite(self, testsuite: Testsuite, parentElement: _Element) -> None:
		"""
		Generate the internal XML data structure for a test suite.

		This method generates the XML element (``<testsuite>``) and recursively calls other generated methods. Errored
		test cases are counted as failures, as the logger knows no errors. The start time is written in UTC. The
		attributes ``id`` and ``package`` are written as the logger does: ``0`` and the test suite's name.

		:param testsuite:      The test suite to convert to an XML data structures.
		:param parentElement:  The parent XML data structure element, this data structure part will be added to.
		:raises UnittestError: If the test suite has no test cases.
		:raises UnittestError: If the test suite has no start time.
		:raises UnittestError: If the test suite has no duration.
		:raises UnittestError: If the test suite has no host name.
		"""
		if testsuite.TestcaseCount == 0:
			raise UnittestError(
				f"The {self._DIALECT} format requires test cases in <testsuite>, but '{testsuite._name}' has none."
			)
		elif testsuite._startTime is None:
			raise UnittestError(
				f"The {self._DIALECT} format requires a timestamp on <testsuite>, but '{testsuite._name}' has none."
			)
		elif testsuite._duration is None:
			raise UnittestError(
				f"The {self._DIALECT} format requires a time on <testsuite>, but '{testsuite._name}' has none."
			)
		elif testsuite._hostname is None:
			raise UnittestError(
				f"The {self._DIALECT} format requires a hostname on <testsuite>, but '{testsuite._name}' has none."
			)

		startTime = testsuite._startTime
		if startTime.tzinfo is not None:
			startTime = startTime.astimezone(timezone.utc).replace(tzinfo=None)

		testsuiteElement = SubElement(parentElement, "testsuite")
		testsuiteElement.attrib["name"] = testsuite._name
		testsuiteElement.attrib["tests"] = str(testsuite.TestcaseCount)
		testsuiteElement.attrib["skipped"] = str(testsuite._skipped)
		testsuiteElement.attrib["failures"] = str(testsuite._failed + testsuite._errored)
		testsuiteElement.attrib["errors"] = "0"
		testsuiteElement.attrib["time"] = f"{testsuite._duration.total_seconds():.6f}"
		testsuiteElement.attrib["timestamp"] = startTime.isoformat(timespec="seconds")
		testsuiteElement.attrib["hostname"] = testsuite._hostname
		testsuiteElement.attrib["id"] = "0"
		testsuiteElement.attrib["package"] = testsuite._name

		SubElement(testsuiteElement, "properties")

		for testclass in testsuite._testclasses.values():
			for tc in testclass._testcases.values():
				self._GenerateTestcase(tc, testsuiteElement)

	def _GenerateTestcase(self, testcase: Testcase, parentElement: _Element) -> None:
		"""
		Generate the internal XML data structure for a test case.

		This method generates the XML element (``<testcase>``) and recursively calls other generated methods. The
		duration is written with seven decimals and at least ``0.0000001`` seconds, as the logger does.

		:param testcase:       The test case to convert to an XML data structures.
		:param parentElement:  The parent XML data structure element, this data structure part will be added to.
		:raises UnittestError: If the test case has no duration.
		"""
		if testcase._duration is None:
			raise UnittestError(
				f"The {self._DIALECT} format requires a time on <testcase>, but '{testcase._name}' has none."
			)

		testcaseElement = SubElement(parentElement, "testcase")
		testcaseElement.attrib["classname"] = testcase.Classname
		testcaseElement.attrib["name"] = testcase._name
		testcaseElement.attrib["time"] = f"{max(testcase._duration.total_seconds(), 0.0000001):.7f}"

		self._GenerateTestcaseChildren(testcase, testcaseElement)

	def _GenerateTestcaseChildren(self, testcase: Testcase, testcaseElement: _Element) -> None:
		"""
		Generate the child elements of a ``<testcase>`` from the test case's status, message, details and captured output.

		A skipped test case gets an empty ``<skipped/>``: its message and details are not written. Every other test case,
		which didn't pass, gets a ``<failure type="failure">`` carrying the message (``message`` attribute) and details
		(text) - errored ones too. Captured standard output and standard error are written as ``<system-out>`` and
		``<system-err>`` elements.

		:param testcase:        The test case to convert to XML child elements.
		:param testcaseElement: The ``<testcase>`` element, the child elements will be added to.
		"""
		if testcase._status is TestcaseStatus.Skipped:
			SubElement(testcaseElement, "skipped")
		elif testcase._status is not TestcaseStatus.Passed:
			failureElement = SubElement(testcaseElement, "failure")
			failureElement.attrib["type"] = "failure"

			if testcase._message is not None:
				failureElement.attrib["message"] = testcase._message

			if testcase._details is not None:
				failureElement.text = testcase._details

		if testcase._standardOutput is not None:
			SubElement(testcaseElement, "system-out").text = testcase._standardOutput

		if testcase._standardError is not None:
			SubElement(testcaseElement, "system-err").text = testcase._standardError
