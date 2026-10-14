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
Reader for Visual Studio's test results format (TRX), as VSTest writes it.

``dotnet test --logger trx`` (VSTest's TRX logger) writes a test run as XML in namespace
``http://microsoft.com/schemas/VisualStudio/TeamTest/2010``. The file lists a result per executed test
(``<UnitTestResult>``), a definition per test (``<UnitTest>``: assembly, class and method), the test lists results are
filed in, and a summary with counters.

This package's data model mirrors these elements: a :class:`Document` reads a TRX file into a :class:`TestRun`.

.. rubric:: Example

.. code-block:: Python

   from pathlib import Path
   from pyEDAA.Reports.Unittesting.TRX import Document

   document = Document(Path("TestResults/MyLibrary.Tests.trx"), analyzeAndConvert=True)
   print(f"{document.Name}: {document.Outcome.name} - {document.Counters['total']} tests")
"""
from __future__                 import annotations

from datetime                   import datetime, timedelta
from enum                       import Enum
from pathlib                    import Path
from typing                     import Dict, Mapping, Optional as Nullable
from uuid                       import UUID

from lxml.etree                 import XMLParser, XMLSchema, XMLSchemaParseError, XMLSyntaxError, parse
from lxml.etree                 import _Element, _ElementTree
from pyTooling.Common           import getFullyQualifiedName, getResourceFile
from pyTooling.Decorators       import export, readonly
from pyTooling.Exceptions       import ToolingException
from pyTooling.MetaClasses      import ExtendedType
from pyTooling.Stopwatch        import Stopwatch

from pyEDAA.Reports             import Resources
from pyEDAA.Reports.Unittesting import UnittestError, Document as ut_Document


__all__ = ["TRX_NAMESPACE"]

TRX_NAMESPACE = "http://microsoft.com/schemas/VisualStudio/TeamTest/2010"  #: XML namespace of a TRX file.


@export
class TestOutcome(Enum):
	"""
	Outcome of a test or of a test run, as named by an ``outcome`` attribute.

	VSTest's TRX logger writes ``Passed``, ``Failed`` and ``NotExecuted`` for a test, and ``Completed``, ``Failed`` or
	``Error`` for the test run.
	"""

	Error =               "Error"                #: The test or the run hit an error; also a result without ``outcome``.
	Failed =              "Failed"               #: The test failed.
	Timeout =             "Timeout"              #: The test exceeded its time limit.
	Aborted =             "Aborted"              #: The test was aborted.
	Inconclusive =        "Inconclusive"         #: The test ran, but neither passed nor failed.
	PassedButRunAborted = "PassedButRunAborted"  #: The test passed, but the test run was aborted.
	NotRunnable =         "NotRunnable"          #: The test can't be run.
	NotExecuted =         "NotExecuted"          #: The test wasn't executed, e.g. it was skipped.
	Disconnected =        "Disconnected"         #: The connection to the test agent was lost.
	Warning =             "Warning"              #: The test passed with a warning.
	Passed =              "Passed"               #: The test passed.
	Completed =           "Completed"            #: The test run completed without a failed test.
	InProgress =          "InProgress"           #: The test is still running.
	Pending =             "Pending"              #: The test is waiting to run.


@export
class TestRun(metaclass=ExtendedType, slots=True):
	"""
	A test run (``<TestRun>``): the test lists and the run's summary.

	The summary's counters are kept as written. They can contradict the results: VSTest's TRX logger counts a skipped
	test only in ``total``.
	"""

	_id:             Nullable[UUID]         #: Identifier of the test run.
	_name:           str                    #: Name of the test run, e.g. ``user@host 2026-10-08 11:09:27``.
	_startTime:      Nullable[datetime]     #: Time the test run started.
	_finishTime:     Nullable[datetime]     #: Time the test run finished.
	_outcome:        Nullable[TestOutcome]  #: Outcome of the test run.
	_counters:       Dict[str, int]         #: Counters of the run's summary, by attribute name (e.g. ``total``).
	_standardOutput: Nullable[str]          #: Messages of the test framework and the test adapter for the whole run.
	_testLists:      Dict[UUID, str]        #: Names of the test lists, by identifier.

	def __init__(
		self,
		name: str,
		id: Nullable[UUID] = None,
		startTime: Nullable[datetime] = None,
		finishTime: Nullable[datetime] = None,
		outcome: Nullable[TestOutcome] = None,
		counters: Nullable[Mapping[str, int]] = None,
		standardOutput: Nullable[str] = None,
		testLists: Nullable[Mapping[UUID, str]] = None
	) -> None:
		"""
		Initializes a test run.

		:param name:           Name of the test run.
		:param id:             Optional, identifier of the test run.
		:param startTime:      Optional, time the test run started.
		:param finishTime:     Optional, time the test run finished.
		:param outcome:        Optional, outcome of the test run.
		:param counters:       Optional, counters of the run's summary, by attribute name.
		:param standardOutput: Optional, messages of the test framework and the test adapter for the whole run.
		:param testLists:      Optional, names of the test lists, by identifier.
		:raises ValueError:    If parameter 'name' is None.
		:raises TypeError:     If parameter 'name' is not of type :class:`str`.
		:raises ValueError:    If parameter 'name' is empty.
		:raises TypeError:     If parameter 'id' is not of type :class:`~uuid.UUID`.
		:raises TypeError:     If parameter 'startTime' is not of type :class:`~datetime.datetime`.
		:raises TypeError:     If parameter 'finishTime' is not of type :class:`~datetime.datetime`.
		:raises TypeError:     If parameter 'outcome' is not of type :class:`TestOutcome`.
		:raises TypeError:     If parameter 'standardOutput' is not of type :class:`str`.
		:raises TypeError:     If parameter 'counters' is not a mapping.
		:raises TypeError:     If a key of parameter 'counters' is not of type :class:`str`.
		:raises TypeError:     If a value of parameter 'counters' is not of type :class:`int`.
		:raises TypeError:     If parameter 'testLists' is not a mapping.
		:raises TypeError:     If a key of parameter 'testLists' is not of type :class:`~uuid.UUID`.
		:raises TypeError:     If a value of parameter 'testLists' is not of type :class:`str`.
		"""
		if name is None:
			raise ValueError(f"Parameter 'name' is None.")
		elif not isinstance(name, str):
			ex = TypeError(f"Parameter 'name' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(name)}'.")
			raise ex
		elif name == "":
			raise ValueError(f"Parameter 'name' is empty.")

		for parameterName, value, valueType in (
			("id", id, UUID),
			("startTime", startTime, datetime),
			("finishTime", finishTime, datetime),
			("outcome", outcome, TestOutcome),
			("standardOutput", standardOutput, str)
		):
			if value is not None and not isinstance(value, valueType):
				ex = TypeError(f"Parameter '{parameterName}' is not of type '{valueType.__name__}'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
				raise ex

		self._id =             id
		self._name =           name
		self._startTime =      startTime
		self._finishTime =     finishTime
		self._outcome =        outcome
		self._standardOutput = standardOutput

		self._counters = {}
		self._testLists = {}
		for parameterName, mapping, target, keyType, valueType in (
			("counters", counters, self._counters, str, int),
			("testLists", testLists, self._testLists, UUID, str)
		):
			if mapping is None:
				continue
			elif not isinstance(mapping, Mapping):
				ex = TypeError(f"Parameter '{parameterName}' is not a mapping.")
				ex.add_note(f"Got type '{getFullyQualifiedName(mapping)}'.")
				raise ex

			for key, value in mapping.items():
				if not isinstance(key, keyType):
					ex = TypeError(f"Key of parameter '{parameterName}' is not of type '{keyType.__name__}'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(key)}'.")
					raise ex
				elif not isinstance(value, valueType):
					ex = TypeError(f"Value of parameter '{parameterName}' is not of type '{valueType.__name__}'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
					raise ex

				target[key] = value

	@readonly
	def Id(self) -> Nullable[UUID]:
		"""
		Read-only property to access the test run's identifier (:attr:`_id`).

		:returns: The test run's identifier, or ``None`` if it's unknown.
		"""
		return self._id

	@readonly
	def Name(self) -> str:
		"""
		Read-only property to access the test run's name (:attr:`_name`).

		:returns: The test run's name.
		"""
		return self._name

	@readonly
	def StartTime(self) -> Nullable[datetime]:
		"""
		Read-only property to access the time the test run started (:attr:`_startTime`).

		:returns: The start time, or ``None`` if it's unknown.
		"""
		return self._startTime

	@readonly
	def FinishTime(self) -> Nullable[datetime]:
		"""
		Read-only property to access the time the test run finished (:attr:`_finishTime`).

		:returns: The finish time, or ``None`` if it's unknown.
		"""
		return self._finishTime

	@readonly
	def Outcome(self) -> Nullable[TestOutcome]:
		"""
		Read-only property to access the test run's outcome (:attr:`_outcome`).

		:returns: The test run's outcome, or ``None`` if it's unknown.
		"""
		return self._outcome

	@readonly
	def Counters(self) -> Dict[str, int]:
		"""
		Read-only property to access the counters of the run's summary (:attr:`_counters`).

		A counter is named by its attribute of ``<Counters>``, e.g. ``total`` or ``passed``.

		.. attention::

		   The counters can contradict the results. VSTest's TRX logger counts every result in ``total``, but only passed
		   and failed results in ``executed``; it writes ``0`` for every other counter, e.g. ``notExecuted``. A skipped
		   test is counted in ``total`` only.

		:returns: The counters, by attribute name.
		"""
		return self._counters

	@readonly
	def StandardOutput(self) -> Nullable[str]:
		"""
		Read-only property to access the messages of the test framework and the test adapter for the whole run
		(:attr:`_standardOutput`).

		:returns: The messages, or ``None`` if none were recorded.
		"""
		return self._standardOutput

	@readonly
	def TestLists(self) -> Dict[UUID, str]:
		"""
		Read-only property to access the names of the test lists (:attr:`_testLists`).

		VSTest's TRX logger writes two fixed lists, ``Results Not in a List`` and ``All Loaded Results``, and files every
		result in the first.

		:returns: The test lists' names, by identifier.
		"""
		return self._testLists


@export
class Document(TestRun, ut_Document):
	"""
	A document reader for TRX files written by VSTest's TRX logger.

	The file is validated against :file:`VSTest-TRX.xsd`, an XML schema reverse engineered from the logger's source
	code. Afterwards, the test run's identifier, name and times, its test lists and its summary are read.
	"""

	_xmlDocument: Nullable[_ElementTree]  #: Parsed and validated XML document.

	def __init__(self, xmlReportFile: Path, analyzeAndConvert: bool = False) -> None:
		"""
		Initializes the document reader.

		:param xmlReportFile:     Path to the TRX file.
		:param analyzeAndConvert: Optional, if true, analyze (parse and validate) the file and convert its content.
		"""
		super().__init__("Unprocessed TRX file")

		self._xmlDocument = None

		ut_Document.__init__(self, xmlReportFile, analyzeAndConvert)

	def Analyze(self) -> None:
		"""
		Analyze the TRX file: parse it and validate it against the XML schema.

		.. hint::

		   The time spend for analysis will be made available via property :data:`AnalysisDuration`.

		:raises UnittestError: If the file doesn't exist.
		:raises UnittestError: If the file isn't well-formed XML.
		:raises UnittestError: If the root element isn't ``<TestRun>`` in the TRX namespace.
		:raises UnittestError: If the XML schema can't be located or parsed.
		:raises UnittestError: If the file isn't valid according to the XML schema.
		"""
		if not self._path.exists():
			raise UnittestError(f"TRX file '{self._path}' does not exist.") \
				from FileNotFoundError(f"File '{self._path}' not found.")

		with Stopwatch() as sw:
			try:
				xmlDocument = parse(self._path, XMLParser(ns_clean=True))
			except XMLSyntaxError as ex:
				raise UnittestError(f"XML syntax error in TRX file '{self._path}'.") from ex

			rootElement: _Element = xmlDocument.getroot()
			if rootElement.tag != f"{{{TRX_NAMESPACE}}}TestRun":
				ex = UnittestError(f"Root element of '{self._path}' is not '<TestRun>' in namespace '{TRX_NAMESPACE}'.")
				ex.add_note(f"Got root element '{rootElement.tag}'.")
				raise ex

			schemaFile = "VSTest-TRX.xsd"
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

			self._xmlDocument = xmlDocument

		self._analysisDuration = sw.Duration

	def Convert(self) -> None:
		"""
		Read the test run's identifier, name and times, its test lists and its summary from the parsed and validated XML
		data structure.

		.. hint::

		   The time spend for model conversion will be made available via property :data:`ModelConversionDuration`.

		:raises UnittestError: If the TRX file was not analyzed before. |br|
		                       Call 'Document.Analyze()' or create the document using
		                       'Document(path, analyzeAndConvert=True)'.
		"""
		if self._xmlDocument is None:
			ex = UnittestError(f"TRX file '{self._path}' needs to be read and analyzed by an XML parser.")
			ex.add_note(f"Call 'Document.Analyze()' or create the document using 'Document(path, analyzeAndConvert=True)'.")
			raise ex

		with Stopwatch() as sw:
			namespaces = {"trx": TRX_NAMESPACE}
			rootElement: _Element = self._xmlDocument.getroot()
			timesElement = rootElement.find("trx:Times", namespaces)
			summaryElement = rootElement.find("trx:ResultSummary", namespaces)
			countersElement = summaryElement.find("trx:Counters", namespaces)

			self._id =             UUID(rootElement.attrib["id"])
			self._name =           rootElement.attrib["name"]
			self._startTime =      datetime.fromisoformat(timesElement.attrib["start"])
			self._finishTime =     datetime.fromisoformat(timesElement.attrib["finish"])
			self._outcome =        TestOutcome(summaryElement.attrib["outcome"])
			self._counters =       {name: int(value) for name, value in countersElement.attrib.items()}
			self._standardOutput = summaryElement.findtext("trx:Output/trx:StdOut", namespaces=namespaces)

			for element in rootElement.iterfind("trx:TestLists/trx:TestList", namespaces):  # type: _Element
				self._testLists[UUID(element.attrib["id"])] = element.attrib["name"]

		self._modelConversion = sw.Duration
