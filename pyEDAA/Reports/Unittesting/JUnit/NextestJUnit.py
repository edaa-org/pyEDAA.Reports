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
Reader and writer for the JUnit XML dialect of cargo-nextest.

.. seealso::

   :ref:`UNITTEST/SpecificDataModel/JUnit/Dialect/nextest`
      |rarr| The dialect's mapping to the unified data model and its known issues.
"""
from __future__                       import annotations

from datetime                         import datetime, timedelta
from pathlib                          import Path
from typing                           import Optional as Nullable, Type, ClassVar
from uuid                             import UUID

from lxml.etree                       import ElementTree, Element, SubElement, tostring, _Element
from pyTooling.Common                 import getFullyQualifiedName
from pyTooling.Decorators             import export, readonly, InheritDocString, DocStringMergeStrategy
from pyTooling.Stopwatch              import Stopwatch

from pyEDAA.Reports.Unittesting       import UnittestError, TestsuiteKind, TestcaseStatus
from pyEDAA.Reports.Unittesting       import TestsuiteSummary as ut_TestsuiteSummary, Testsuite as ut_Testsuite
from pyEDAA.Reports.Unittesting       import Testcase as ut_Testcase
from pyEDAA.Reports.Unittesting.JUnit import Testcase as ju_Testcase, Testclass as ju_Testclass, Testsuite as ju_Testsuite
from pyEDAA.Reports.Unittesting.JUnit import TestsuiteSummary as ju_TestsuiteSummary, Document as ju_Document
from pyEDAA.Reports.Unittesting.JUnit import JUnitReaderMode


@export
@InheritDocString(ju_Testcase, DocStringMergeStrategy.BaseLast)
class Testcase(ju_Testcase):
	"""
	This is a derived implementation for the cargo-nextest JUnit dialect.

	Besides the fields of a JUnit test case, it carries the time the test case was started and the number of reruns
	nextest recorded for it.
	"""

	_startTime:  Nullable[datetime]  #: Time when the test case was started.
	_rerunCount: int                 #: Number of reruns recorded as ``<flakyFailure>``, ``<rerunFailure>``, etc.

	def __init__(
		self,
		name: str,
		duration:  Nullable[timedelta] = None,
		status: TestcaseStatus = TestcaseStatus.Unknown,
		assertionCount: Nullable[int] = None,
		message: Nullable[str] = None,
		details: Nullable[str] = None,
		standardOutput: Nullable[str] = None,
		standardError: Nullable[str] = None,
		startTime: Nullable[datetime] = None,
		rerunCount: int = 0,
		*,
		parent: Nullable[Testclass] = None
	) -> None:
		"""
		Initializes the fields of a test case.

		:param name:           Name of the test entity.
		:param duration:       Optional, duration of the entity's execution.
		:param status:         Optional, status of the test case.
		:param assertionCount: Optional, number of assertions within the test.
		:param message:        Optional, message explaining the test case's status.
		:param details:        Optional, details explaining the test case's status (e.g. a traceback).
		:param standardOutput: Optional, captured standard output of the test case.
		:param standardError:  Optional, captured standard error of the test case.
		:param startTime:      Optional, time when the test case was started.
		:param rerunCount:     Optional, number of reruns recorded for the test case.
		:param parent:         Optional, reference to the parent test class.
		:raises TypeError:     If parameter 'startTime' is not a datetime.
		:raises ValueError:    If parameter 'rerunCount' is None.
		:raises TypeError:     If parameter 'rerunCount' is not an integer.
		:raises ValueError:    If parameter 'rerunCount' is negative.
		"""
		super().__init__(
			name, duration, status, assertionCount, message, details, standardOutput, standardError, parent=parent
		)

		if startTime is not None and not isinstance(startTime, datetime):
			ex = TypeError(f"Parameter 'startTime' is not of type 'datetime'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(startTime)}'.")
			raise ex

		if rerunCount is None:
			raise ValueError(f"Parameter 'rerunCount' is None.")
		elif not isinstance(rerunCount, int):
			ex = TypeError(f"Parameter 'rerunCount' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(rerunCount)}'.")
			raise ex
		elif rerunCount < 0:
			ex = ValueError(f"Parameter 'rerunCount' is negative.")
			ex.add_note(f"Got value '{rerunCount}'.")
			raise ex

		self._startTime =  startTime
		self._rerunCount = rerunCount

	@readonly
	def StartTime(self) -> Nullable[datetime]:
		"""
		Read-only property to access the time when the test case was started (:attr:`_startTime`).

		nextest writes no start time for a skipped test case.

		:returns: Start time of the test case, or ``None`` if it wasn't recorded.
		"""
		return self._startTime

	@readonly
	def RerunCount(self) -> int:
		"""
		Read-only property to access the number of reruns nextest recorded for the test case (:attr:`_rerunCount`).

		A test case passing after a rerun is *flaky*: its status is passed and its rerun count is not zero.

		:returns: Number of reruns.
		"""
		return self._rerunCount

	def Copy(self) -> Testcase:
		"""
		Copy the test case without its parent.

		:returns: A copy of the test case, including its start time and rerun count.
		"""
		testcase = super().Copy()
		testcase._startTime = self._startTime
		testcase._rerunCount = self._rerunCount

		return testcase

	@classmethod
	def FromTestcase(cls, testcase: ut_Testcase) -> Testcase:
		"""
		Convert a test case of the unified test entity data model to the JUnit specific data model's test case object
		adhering to the cargo-nextest JUnit dialect.

		:param testcase: Test case from unified data model.
		:returns:        Test case from JUnit specific data model (cargo-nextest JUnit dialect).
		"""
		juTestcase = super().FromTestcase(testcase)
		juTestcase._startTime = testcase._startTime

		return juTestcase

	def ToTestcase(self) -> ut_Testcase:
		"""
		Convert this test case to a test case of the unified test entity data model.

		The start time is kept, the rerun count is lost.

		:returns: Test case of the unified test entity data model.
		"""
		testcase = super().ToTestcase()
		testcase._startTime = self._startTime

		return testcase


@export
@InheritDocString(ju_Testclass, DocStringMergeStrategy.BaseLast)
class Testclass(ju_Testclass):
	"""
	This is a derived implementation for the cargo-nextest JUnit dialect.
	"""


@export
@InheritDocString(ju_Testsuite, DocStringMergeStrategy.BaseLast)
class Testsuite(ju_Testsuite):
	"""
	This is a derived implementation for the cargo-nextest JUnit dialect.
	"""

	@classmethod
	def FromTestsuite(cls, testsuite: ut_Testsuite) -> Testsuite:
		"""
		Convert a test suite of the unified test entity data model to the JUnit specific data model's test suite object
		adhering to the cargo-nextest JUnit dialect.

		:param testsuite:      Test suite from unified data model.
		:returns:              Test suite from JUnit specific data model (cargo-nextest JUnit dialect).
		:raises UnittestError: If a test case of the test suite is not part of a hierarchy.
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
	This is a derived implementation for the cargo-nextest JUnit dialect.
	"""

	@classmethod
	def FromTestsuiteSummary(cls, testsuiteSummary: ut_TestsuiteSummary) -> TestsuiteSummary:
		"""
		Convert a test suite summary of the unified test entity data model to the JUnit specific data model's test suite
		summary object adhering to the cargo-nextest JUnit dialect.

		:param testsuiteSummary: Test suite summary from unified data model.
		:returns:                Test suite summary from JUnit specific data model (cargo-nextest JUnit dialect).
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
	A document reader and writer for the cargo-nextest JUnit XML file format.

	This class reads, validates and transforms an XML file in the cargo-nextest JUnit format into a JUnit data model. It
	can then be converted into a unified test entity data model.

	In reverse, a JUnit data model instance with the specific cargo-nextest JUnit file format can be created from a
	unified test entity data model. This data model can be written as XML into a file.
	"""

	_DIALECT:   ClassVar[str] =             "cargo-nextest + JUnit"  #: Name of the dialect in messages.
	_TESTCASE:  ClassVar[Type[Testcase]] =  Testcase                 #: Class of the test cases read.
	_TESTCLASS: ClassVar[Type[Testclass]] = Testclass                #: Class of the test classes read.
	_TESTSUITE: ClassVar[Type[Testsuite]] = Testsuite                #: Class of the test suites read.

	_runID:     Nullable[UUID]                                       #: Run ID of the test run, which wrote the report.

	def __init__(
		self,
		xmlReportFile: Path,
		analyzeAndConvert: bool = False,
		readerMode: JUnitReaderMode = JUnitReaderMode.Default
	) -> None:
		"""
		Initializes a cargo-nextest JUnit document.

		:param xmlReportFile:     Path to the XML file.
		:param analyzeAndConvert: Optional, if true, read, validate and convert the file.
		:param readerMode:        Optional, mode of the JUnit reader.
		"""
		super().__init__(xmlReportFile, False, readerMode)

		self._runID = None

		if analyzeAndConvert:
			self.Analyze()
			self.Convert()

	@readonly
	def RunID(self) -> Nullable[UUID]:
		"""
		Read-only property to access the run ID of the test run, which wrote the report (:attr:`_runID`).

		:returns: The run ID, or ``None`` if the report has none.
		"""
		return self._runID

	@classmethod
	def FromTestsuiteSummary(cls, xmlReportFile: Path, testsuiteSummary: ut_TestsuiteSummary) -> Document:
		"""
		Convert a test suite summary of the unified test entity data model to a cargo-nextest JUnit document.

		The unified data model has no run ID, so the document has none.

		:param xmlReportFile:    Path to the XML file the document will be written to.
		:param testsuiteSummary: Test suite summary from unified data model.
		:returns:                A cargo-nextest JUnit document.
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

		The used XML schema definition is specific to the cargo-nextest JUnit dialect.
		"""
		xmlSchemaFile = "Nextest-JUnit.xsd"
		self._Analyze(xmlSchemaFile)

	def Write(self, path: Nullable[Path] = None, overwrite: bool = False, regenerate: bool = False) -> None:
		"""
		Write the data model as XML into a file adhering to the cargo-nextest dialect.

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

		try:
			with path.open("wb") as file:
				file.write(tostring(self._xmlDocument, encoding="utf-8", xml_declaration=True, pretty_print=True))
		except Exception as ex:
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

			self._name = self._ConvertName(rootElement, optional=False)
			self._runID = UUID(rootElement.attrib["uuid"]) if "uuid" in rootElement.attrib else None
			self._startTime = self._ConvertTimestamp(rootElement, optional=False)
			self._duration = self._ConvertTime(rootElement, optional=False)

			for rootNode in rootElement.iterchildren(tag="testsuite"):  # type: _Element
				self._ConvertTestsuite(self, rootNode)

			self.Aggregate()

		self._modelConversion = sw.Duration

	def _ConvertTestsuite(self, parent: TestsuiteSummary, testsuitesNode: _Element) -> None:
		"""
		Convert the XML data structure of a ``<testsuite>`` to a test suite.

		A ``<testsuite>`` written by nextest has neither a hostname, nor a start time, nor a duration.

		:param parent:         The test suite summary as a parent element in the test entity hierarchy.
		:param testsuitesNode: The current XML element node representing a test suite.
		"""
		newTestsuite = self._TESTSUITE(self._ConvertName(testsuitesNode, optional=False), parent=parent)

		self._ConvertTestsuiteChildren(testsuitesNode, newTestsuite)

	def _ConvertTestcase(self, parent: Testsuite, testcaseNode: _Element) -> None:
		"""
		Convert the XML data structure of a ``<testcase>`` to a test case.

		Besides the fields of a JUnit test case, the start time (``timestamp``) and the number of reruns
		(``<flakyFailure>``, ``<flakyError>``, ``<rerunFailure>`` and ``<rerunError>`` elements) are converted.

		:param parent:       The test suite as a parent element in the test entity hierarchy.
		:param testcaseNode: The current XML element node representing a test case.
		"""
		className = self._ConvertClassname(testcaseNode)
		testclass = self._FindOrCreateTestclass(parent, className)

		newTestcase = self._TESTCASE(
			self._ConvertName(testcaseNode, optional=False),
			self._ConvertTime(testcaseNode, optional=False),
			startTime=self._ConvertTimestamp(testcaseNode, optional=True),
			rerunCount=len(tuple(testcaseNode.iterchildren("flakyFailure", "flakyError", "rerunFailure", "rerunError"))),
			parent=testclass
		)

		self._ConvertTestcaseChildren(testcaseNode, newTestcase)

	def Generate(self, overwrite: bool = False) -> None:
		"""
		Generate the internal XML data structure from test suites and test cases.

		This method generates the XML root element (``<testsuites>``) and recursively calls other generated methods.

		:param overwrite:      Optional, overwrite the internal XML data structure.
		:raises UnittestError: If overwrite is false and the internal XML data structure is not empty.
		:raises UnittestError: If the test suite summary has no start time.
		:raises UnittestError: If the test suite summary has no duration.
		"""
		if not overwrite and self._xmlDocument is not None:
			raise UnittestError(f"Internal XML document is populated with data.")

		if self._startTime is None:
			raise UnittestError(
				f"The {self._DIALECT} format requires a timestamp on <testsuites>, but the report has none."
			)

		if self._duration is None:
			raise UnittestError(f"The {self._DIALECT} format requires a time on <testsuites>, but the report has none.")

		rootElement = Element("testsuites")
		rootElement.attrib["name"] = self._name
		rootElement.attrib["tests"] = str(self._tests)
		rootElement.attrib["skipped"] = str(self._skipped)
		rootElement.attrib["failures"] = str(self._failed)
		rootElement.attrib["errors"] = str(self._errored)
		if self._runID is not None:
			rootElement.attrib["uuid"] = str(self._runID)
		rootElement.attrib["timestamp"] = f"{self._startTime.isoformat()}"
		rootElement.attrib["time"] = f"{self._duration.total_seconds():.6f}"

		self._xmlDocument = ElementTree(rootElement)

		for testsuite in self._testsuites.values():
			self._GenerateTestsuite(testsuite, rootElement)

	def _GenerateTestsuite(self, testsuite: Testsuite, parentElement: _Element) -> None:
		"""
		Generate the internal XML data structure for a test suite.

		This method generates the XML element (``<testsuite>``) and recursively calls other generated methods. The
		dialect has no hostname, start time and duration on a ``<testsuite>``, so these are not written.

		:param testsuite:     The test suite to convert to an XML data structures.
		:param parentElement: The parent XML data structure element, this data structure part will be added to.
		"""
		testsuiteElement = SubElement(parentElement, "testsuite")
		testsuiteElement.attrib["name"] = testsuite._name
		testsuiteElement.attrib["tests"] = str(testsuite._tests)
		testsuiteElement.attrib["skipped"] = str(testsuite._skipped)
		testsuiteElement.attrib["errors"] = str(testsuite._errored)
		testsuiteElement.attrib["failures"] = str(testsuite._failed)

		for testclass in testsuite._testclasses.values():
			for tc in testclass._testcases.values():
				self._GenerateTestcase(tc, testsuiteElement)

	def _GenerateTestcase(self, testcase: Testcase, parentElement: _Element) -> None:
		"""
		Generate the internal XML data structure for a test case.

		This method generates the XML element (``<testcase>``) and recursively calls other generated methods. Reruns are
		not written.

		:param testcase:       The test case to convert to an XML data structures.
		:param parentElement:  The parent XML data structure element, this data structure part will be added to.
		:raises UnittestError: If the test case has no duration.
		"""
		if testcase._duration is None:
			raise UnittestError(
				f"The {self._DIALECT} format requires a time on <testcase>, but test case '{testcase._name}' has none."
			)

		testcaseElement = SubElement(parentElement, "testcase")
		testcaseElement.attrib["name"] = testcase._name
		testcaseElement.attrib["classname"] = testcase.Classname
		if testcase._startTime is not None:
			testcaseElement.attrib["timestamp"] = f"{testcase._startTime.isoformat()}"
		testcaseElement.attrib["time"] = f"{testcase._duration.total_seconds():.6f}"

		self._GenerateTestcaseChildren(testcase, testcaseElement)
