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
Reader for pyTooling's XML test report format.

`pyTooling <https://github.com/pyTooling/pyTooling>`__ can write a test report (pytest option ``--pytooling-xml``) in a
format of its own, which carries two things JUnit XML can't express: test suites nest, and every test suite and test
case can carry a title, a summary and a description besides its name.

The format's version is the version of its XML schema, which a report names in its ``xsi:noNamespaceSchemaLocation``
attribute (e.g. ``TestReport-v0.1.xsd``). A report is validated against that schema and converted into the unified
test entity hierarchy of :mod:`pyEDAA.Reports.Unittesting`.

.. rubric:: Example

.. code-block:: Python

   from pathlib import Path
   from pyEDAA.Reports.Unittesting.pyTooling import Document

   document = Document(Path("report/unit/TestReport.xml"), analyzeAndConvert=True)
   for testcase in document.IterateTestcases():
     print(f"{testcase.Name}: {testcase.Status.name} - {testcase.Title}")
"""
from __future__                 import annotations

from datetime                   import datetime, timedelta
from pathlib                    import Path
from typing                     import Dict, Optional as Nullable

from lxml.etree                 import XMLParser, XMLSchema, XMLSchemaParseError, XMLSyntaxError, parse
from lxml.etree                 import _Element, _ElementTree
from pyTooling.Common           import getResourceFile
from pyTooling.Decorators       import export, readonly
from pyTooling.Exceptions       import ToolingException
from pyTooling.Stopwatch        import Stopwatch
from pyTooling.Versioning       import SemanticVersion

from pyEDAA.Reports             import Resources
from pyEDAA.Reports.Unittesting import UnittestError, TestcaseStatus, TestsuiteKind
from pyEDAA.Reports.Unittesting import Document as ut_Document, TestsuiteSummary, Testsuite, Testcase


__all__ = ["XML_SCHEMA_INSTANCE_NAMESPACE", "SCHEMA_FILES", "STATUS_MAP"]

XML_SCHEMA_INSTANCE_NAMESPACE = "http://www.w3.org/2001/XMLSchema-instance"  #: Namespace of the ``xsi:*`` attributes.

SCHEMA_FILES: Dict[str, SemanticVersion] = {
	"TestReport-v0.1.xsd": SemanticVersion(0, 1),
}  #: Supported schema files (as named by ``xsi:noNamespaceSchemaLocation``) and the format version they define.

STATUS_MAP: Dict[str, TestcaseStatus] = {
	"passed":             TestcaseStatus.Passed,
	"failed":             TestcaseStatus.Failed,
	"errored":            TestcaseStatus.Errored,
	"skipped":            TestcaseStatus.Skipped,
	"expectedToFail":     TestcaseStatus.ExpectedFailed,
	"unexpectedlyPassed": TestcaseStatus.UnexpectedPassed,
}  #: Mapping of a ``<Testcase>``'s ``status`` attribute to a test case status.


@export
class Document(TestsuiteSummary, ut_Document):
	"""
	A document reader for pyTooling's XML test report format.

	The root element ``<TestReport>`` becomes the test suite summary, every nested ``<Testsuite>`` a test suite and
	every ``<Testcase>`` a test case. The optional ``<Title>``, ``<Summary>`` and ``<Description>`` elements become the
	entities' :data:`~pyEDAA.Reports.Unittesting.Base.Title`, :data:`~pyEDAA.Reports.Unittesting.Base.Summary` and
	:data:`~pyEDAA.Reports.Unittesting.Base.Description`. A test case's ``<Message>`` (why it didn't pass) becomes its
	:data:`~pyEDAA.Reports.Unittesting.TestcaseOutputMixin.Message`, its ``nodeID`` attribute (the test runner's
	identifier) the key-value pair ``"nodeID"``.
	"""

	_xmlDocument:   Nullable[_ElementTree]     #: Parsed and validated XML document.
	_schemaVersion: Nullable[SemanticVersion]  #: Format version named by the report's schema location.

	def __init__(self, xmlReportFile: Path, analyzeAndConvert: bool = False) -> None:
		"""
		Initializes the document reader.

		:param xmlReportFile:     Path to the XML report file.
		:param analyzeAndConvert: Optional, if true, analyze (parse and validate) the file and convert its content.
		"""
		super().__init__("Unprocessed pyTooling test report")

		self._xmlDocument =   None
		self._schemaVersion = None

		ut_Document.__init__(self, xmlReportFile, analyzeAndConvert)

	@readonly
	def SchemaVersion(self) -> SemanticVersion:
		"""
		Read-only property to access the report format's version (:attr:`_schemaVersion`).

		The version is named by the schema the report points at, so it is known once the file was analyzed.

		:returns:              The format version, e.g. ``0.1``.
		:raises UnittestError: If the file wasn't analyzed yet.
		"""
		if self._schemaVersion is None:
			ex = UnittestError(f"pyTooling test report file '{self._path}' wasn't analyzed yet.")
			ex.add_note(f"Call 'Document.Analyze()' or create the document using 'Document(path, analyzeAndConvert=True)'.")
			raise ex

		return self._schemaVersion

	def Analyze(self) -> None:
		"""
		Analyze the XML file: parse it, determine the format version and validate it against the version's XML schema.

		.. hint::

		   The time spend for analysis will be made available via property :data:`AnalysisDuration`.

		:raises UnittestError: If the file doesn't exist.
		:raises UnittestError: If the file isn't well-formed XML.
		:raises UnittestError: If the root element isn't ``<TestReport>``.
		:raises UnittestError: If the root element has no ``xsi:noNamespaceSchemaLocation`` attribute.
		:raises UnittestError: If the format version named by the schema location is unknown.
		:raises UnittestError: If the XML schema can't be located or parsed.
		:raises UnittestError: If the file isn't valid according to the XML schema.
		"""
		if not self._path.exists():
			raise UnittestError(f"pyTooling test report file '{self._path}' does not exist.") \
				from FileNotFoundError(f"File '{self._path}' not found.")

		with Stopwatch() as sw:
			try:
				xmlDocument = parse(self._path, XMLParser(ns_clean=True))
			except XMLSyntaxError as ex:
				raise UnittestError(f"XML syntax error in pyTooling test report file '{self._path}'.") from ex

			rootElement: _Element = xmlDocument.getroot()
			if rootElement.tag != "TestReport":
				ex = UnittestError(f"Root element of '{self._path}' is not '<TestReport>'.")
				ex.add_note(f"Got root element '<{rootElement.tag}>'.")
				raise ex

			schemaLocation = rootElement.attrib.get(f"{{{XML_SCHEMA_INSTANCE_NAMESPACE}}}noNamespaceSchemaLocation", None)
			if schemaLocation is None:
				raise UnittestError(f"Root element of '{self._path}' has no 'xsi:noNamespaceSchemaLocation' attribute.")

			schemaFile = schemaLocation.replace("\\", "/").rsplit("/", 1)[-1]
			try:
				schemaVersion = SCHEMA_FILES[schemaFile]
			except KeyError:
				ex = UnittestError(f"Unsupported pyTooling test report format '{schemaLocation}' in '{self._path}'.")
				ex.add_note(f"Supported schemas: {', '.join(SCHEMA_FILES)}")
				raise ex from None

			try:
				schemaResourceFile = getResourceFile(Resources, schemaFile)
			except ToolingException as ex:
				raise UnittestError(f"Couldn't locate XML Schema '{schemaFile}' in package resources.") from ex

			try:
				xmlSchema = XMLSchema(parse(schemaResourceFile, XMLParser(ns_clean=True)))
			except (XMLSyntaxError, XMLSchemaParseError) as ex:
				raise UnittestError(f"Error while parsing XML Schema '{schemaFile}'.") from ex

			if not xmlSchema.validate(xmlDocument):
				ex = UnittestError(f"Validation error for '{self._path}' using XSD schema '{schemaFile}'.")
				for logEntry in xmlSchema.error_log:
					ex.add_note(str(logEntry))
				raise ex

			self._xmlDocument =   xmlDocument
			self._schemaVersion = schemaVersion

		self._analysisDuration = sw.Duration

	def Convert(self) -> None:
		"""
		Convert the parsed and validated XML data structure into a test entity hierarchy.

		The test suite summary is named after the report file (without extension). Afterwards, the hierarchy is
		aggregated, so all counters and states are computed.

		.. hint::

		   The time spend for model conversion will be made available via property :data:`ModelConversionDuration`.

		:raises UnittestError: If the XML file was not analyzed before. |br|
		                       Call 'Document.Analyze()' or create the document using
		                       'Document(path, analyzeAndConvert=True)'.
		"""
		if self._xmlDocument is None:
			ex = UnittestError(f"pyTooling test report file '{self._path}' needs to be read and analyzed by an XML parser.")
			ex.add_note(f"Call 'Document.Analyze()' or create the document using 'Document(path, analyzeAndConvert=True)'.")
			raise ex

		with Stopwatch() as sw:
			rootElement: _Element = self._xmlDocument.getroot()

			self._name = self._path.stem
			if (timestamp := rootElement.attrib.get("timestamp", None)) is not None:
				self._startTime = datetime.fromisoformat(timestamp)
			self._totalDuration = self._ConvertDuration(rootElement)
			self._ConvertTexts(rootElement, self)

			for element in rootElement.iterchildren(tag="Testsuite"):  # type: _Element
				self._ConvertTestsuite(element, self)

			self.Aggregate()

		self._modelConversion = sw.Duration

	def _ConvertTestsuite(self, testsuiteElement: _Element, parent: TestsuiteSummary | Testsuite) -> None:
		"""
		Convert a ``<Testsuite>`` element and its children to a test suite.

		:param testsuiteElement: The XML element node representing a test suite.
		:param parent:           The parent test entity.
		"""
		testsuite = Testsuite(
			testsuiteElement.attrib["name"],
			kind=TestsuiteKind.Logical,
			totalDuration=self._ConvertDuration(testsuiteElement),
			parent=parent
		)
		self._ConvertTexts(testsuiteElement, testsuite)

		for element in testsuiteElement.iterchildren(tag="Testsuite"):  # type: _Element
			self._ConvertTestsuite(element, testsuite)

		for element in testsuiteElement.iterchildren(tag="Testcase"):  # type: _Element
			self._ConvertTestcase(element, testsuite)

	def _ConvertTestcase(self, testcaseElement: _Element, parent: Testsuite) -> None:
		"""
		Convert a ``<Testcase>`` element and its children to a test case.

		:param testcaseElement: The XML element node representing a test case.
		:param parent:          The parent test suite.
		"""
		messageElement = testcaseElement.find("Message")

		testcase = Testcase(
			testcaseElement.attrib["name"],
			totalDuration=self._ConvertDuration(testcaseElement),
			status=STATUS_MAP[testcaseElement.attrib["status"]],
			message=None if messageElement is None else messageElement.text,
			parent=parent
		)
		self._ConvertTexts(testcaseElement, testcase)

		if (nodeID := testcaseElement.attrib.get("nodeID", None)) is not None:
			testcase["nodeID"] = nodeID

	def _ConvertDuration(self, element: _Element) -> Nullable[timedelta]:
		"""
		Convert the ``duration`` attribute (in seconds) of an XML element node.

		:param element: The XML element node with an optional ``duration`` attribute.
		:returns:       The duration, or ``None`` if the attribute is absent.
		"""
		if (duration := element.attrib.get("duration", None)) is None:
			return None

		return timedelta(seconds=float(duration))

	def _ConvertTexts(self, element: _Element, entity: TestsuiteSummary | Testsuite | Testcase) -> None:
		"""
		Convert the ``<Title>``, ``<Summary>`` and ``<Description>`` child elements of an XML element node.

		:param element: The XML element node with optional ``<Title>``, ``<Summary>`` and ``<Description>`` children.
		:param entity:  The test entity to update.
		"""
		if (titleElement := element.find("Title")) is not None:
			entity._title = titleElement.text

		if (summaryElement := element.find("Summary")) is not None:
			entity._summary = summaryElement.text

		if (descriptionElement := element.find("Description")) is not None:
			entity._description = descriptionElement.text
