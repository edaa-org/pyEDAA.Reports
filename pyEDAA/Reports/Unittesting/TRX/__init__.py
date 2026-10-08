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

This package's data model mirrors these elements: a :class:`TestRun` holds :class:`UnitTest` definitions and
:class:`UnitTestResult` results. A :class:`Document` reads a TRX file into it, and :meth:`TestRun.ToTestsuiteSummary`
converts it to the unified test entity hierarchy of :mod:`pyEDAA.Reports.Unittesting`.

.. rubric:: Example

.. code-block:: Python

   from pathlib import Path
   from pyEDAA.Reports.Unittesting.TRX import Document

   document = Document(Path("TestResults/MyLibrary.Tests.trx"), analyzeAndConvert=True)
   summary = document.ToTestsuiteSummary()
   for testcase in summary.IterateTestcases():
     print(f"{testcase.Name}: {testcase.Status.name}")
"""
from __future__                 import annotations

from datetime                   import datetime, timedelta
from enum                       import Enum
from pathlib                    import Path, PureWindowsPath
from re                         import fullmatch
from typing                     import Dict, Iterable, List, Mapping, Optional as Nullable
from uuid                       import UUID

from lxml.etree                 import XMLParser, XMLSchema, XMLSchemaParseError, XMLSyntaxError, parse
from lxml.etree                 import _Element, _ElementTree
from pyTooling.Common           import getFullyQualifiedName, getResourceFile
from pyTooling.Decorators       import export, readonly
from pyTooling.Exceptions       import ToolingException
from pyTooling.MetaClasses      import ExtendedType
from pyTooling.Stopwatch        import Stopwatch

from pyEDAA.Reports             import Resources
from pyEDAA.Reports.Unittesting import UnittestError, TestcaseStatus, TestsuiteKind, TestcaseOutputMixin
from pyEDAA.Reports.Unittesting import Document as ut_Document, TestsuiteSummary as ut_TestsuiteSummary
from pyEDAA.Reports.Unittesting import Testsuite as ut_Testsuite, Testcase as ut_Testcase


__all__ = ["TRX_NAMESPACE", "STATUS_MAP"]

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


STATUS_MAP: Dict[TestOutcome, TestcaseStatus] = {
	TestOutcome.Error:               TestcaseStatus.Errored,
	TestOutcome.Failed:              TestcaseStatus.Failed,
	TestOutcome.Timeout:             TestcaseStatus.Failed,
	TestOutcome.Aborted:             TestcaseStatus.Errored,
	TestOutcome.Inconclusive:        TestcaseStatus.Skipped,
	TestOutcome.PassedButRunAborted: TestcaseStatus.Passed,
	TestOutcome.NotRunnable:         TestcaseStatus.Errored,
	TestOutcome.NotExecuted:         TestcaseStatus.Skipped,
	TestOutcome.Disconnected:        TestcaseStatus.Errored,
	TestOutcome.Warning:             TestcaseStatus.Passed,
	TestOutcome.Passed:              TestcaseStatus.Passed,
	TestOutcome.Completed:           TestcaseStatus.Passed,
	TestOutcome.InProgress:          TestcaseStatus.Inconsistent,
	TestOutcome.Pending:             TestcaseStatus.Inconsistent,
}  #: Mapping of a test's outcome to a test case status.


@export
class UnitTest(metaclass=ExtendedType, slots=True):
	"""
	The definition of a test (``<UnitTest>``): the test method, its class and the assembly containing it.

	A parameterized test has a definition per data row, unless its rows are folded into one. Its results refer to it by
	:attr:`Id`.
	"""

	_id:              UUID  #: Identifier of the test, referred to by its results.
	_name:            str   #: Name of the test, e.g. ``Rows (1,1)``.
	_className:       str   #: Fully qualified name of the test class.
	_methodName:      str   #: Name of the test method.
	_codeBase:        Path  #: Path to the assembly containing the test.
	_adapterTypeName: str   #: Test adapter running the test, e.g. ``executor://xunit/VsTestRunner3/netcore/``.

	def __init__(
		self,
		id: UUID,
		name: str,
		className: str,
		methodName: str,
		codeBase: Path,
		adapterTypeName: str
	) -> None:
		"""
		Initializes a test definition.

		:param id:              Identifier of the test.
		:param name:            Name of the test.
		:param className:       Fully qualified name of the test class.
		:param methodName:      Name of the test method.
		:param codeBase:        Path to the assembly containing the test.
		:param adapterTypeName: Test adapter running the test.
		:raises ValueError:     If parameter 'id' is None.
		:raises TypeError:      If parameter 'id' is not of type :class:`~uuid.UUID`.
		:raises ValueError:     If parameter 'name' is None.
		:raises TypeError:      If parameter 'name' is not of type :class:`str`.
		:raises ValueError:     If parameter 'name' is empty.
		:raises ValueError:     If parameter 'className' is None.
		:raises TypeError:      If parameter 'className' is not of type :class:`str`.
		:raises ValueError:     If parameter 'className' is empty.
		:raises ValueError:     If parameter 'methodName' is None.
		:raises TypeError:      If parameter 'methodName' is not of type :class:`str`.
		:raises ValueError:     If parameter 'methodName' is empty.
		:raises ValueError:     If parameter 'adapterTypeName' is None.
		:raises TypeError:      If parameter 'adapterTypeName' is not of type :class:`str`.
		:raises ValueError:     If parameter 'adapterTypeName' is empty.
		:raises ValueError:     If parameter 'codeBase' is None.
		:raises TypeError:      If parameter 'codeBase' is not of type :class:`~pathlib.Path`.
		"""
		if id is None:
			raise ValueError(f"Parameter 'id' is None.")
		elif not isinstance(id, UUID):
			ex = TypeError(f"Parameter 'id' is not of type 'UUID'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(id)}'.")
			raise ex

		for parameterName, value in (
			("name", name), ("className", className), ("methodName", methodName), ("adapterTypeName", adapterTypeName)
		):
			if value is None:
				raise ValueError(f"Parameter '{parameterName}' is None.")
			elif not isinstance(value, str):
				ex = TypeError(f"Parameter '{parameterName}' is not of type 'str'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
				raise ex
			elif value == "":
				raise ValueError(f"Parameter '{parameterName}' is empty.")

		if codeBase is None:
			raise ValueError(f"Parameter 'codeBase' is None.")
		elif not isinstance(codeBase, Path):
			ex = TypeError(f"Parameter 'codeBase' is not of type 'Path'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(codeBase)}'.")
			raise ex

		self._id =              id
		self._name =            name
		self._className =       className
		self._methodName =      methodName
		self._codeBase =        codeBase
		self._adapterTypeName = adapterTypeName

	@readonly
	def Id(self) -> UUID:
		"""
		Read-only property to access the test's identifier (:attr:`_id`).

		:returns: The test's identifier.
		"""
		return self._id

	@readonly
	def Name(self) -> str:
		"""
		Read-only property to access the test's name (:attr:`_name`).

		:returns: The test's name.
		"""
		return self._name

	@readonly
	def ClassName(self) -> str:
		"""
		Read-only property to access the fully qualified name of the test class (:attr:`_className`).

		:returns: The test class' name, e.g. ``MyLibrary.Tests.CalculatorTests``.
		"""
		return self._className

	@readonly
	def MethodName(self) -> str:
		"""
		Read-only property to access the name of the test method (:attr:`_methodName`).

		:returns: The test method's name.
		"""
		return self._methodName

	@readonly
	def CodeBase(self) -> Path:
		"""
		Read-only property to access the path to the assembly containing the test (:attr:`_codeBase`).

		:returns: The assembly's path.
		"""
		return self._codeBase

	@readonly
	def AdapterTypeName(self) -> str:
		"""
		Read-only property to access the test adapter running the test (:attr:`_adapterTypeName`).

		:returns: The test adapter's URI.
		"""
		return self._adapterTypeName


@export
class UnitTestResult(TestcaseOutputMixin, metaclass=ExtendedType, slots=True):
	"""
	The result of a test (``<UnitTestResult>``).

	The message and stack trace of ``<ErrorInfo>`` - why a test failed or was skipped - are provided as
	:data:`~pyEDAA.Reports.Unittesting.TestcaseOutputMixin.Message` and
	:data:`~pyEDAA.Reports.Unittesting.TestcaseOutputMixin.Details`, the test's output as
	:data:`~pyEDAA.Reports.Unittesting.TestcaseOutputMixin.StandardOutput` and
	:data:`~pyEDAA.Reports.Unittesting.TestcaseOutputMixin.StandardError` by
	:class:`~pyEDAA.Reports.Unittesting.TestcaseOutputMixin`.

	A data-driven test or an ordered test is a container: it lists the results of its rows or tests as inner results.
	"""

	_executionId:  UUID                  #: Identifier of this execution of the test.
	_testId:       UUID                  #: Identifier of the test's definition.
	_testName:     str                   #: Name of the test.
	_computerName: str                   #: Name of the computer the test ran on.
	_outcome:      TestOutcome           #: Outcome of the test.
	_testListId:   UUID                  #: Identifier of the test list the result is filed in.
	_startTime:    Nullable[datetime]    #: Time the test started.
	_endTime:      Nullable[datetime]    #: Time the test ended.
	_duration:     Nullable[timedelta]   #: Duration of the test.
	_innerResults: List[UnitTestResult]  #: Results of the rows of a data-driven test or the tests of an ordered test.

	def __init__(
		self,
		executionId: UUID,
		testId: UUID,
		testName: str,
		computerName: str,
		outcome: TestOutcome,
		testListId: UUID,
		startTime: Nullable[datetime] = None,
		endTime: Nullable[datetime] = None,
		duration: Nullable[timedelta] = None,
		message: Nullable[str] = None,
		details: Nullable[str] = None,
		standardOutput: Nullable[str] = None,
		standardError: Nullable[str] = None,
		innerResults: Nullable[Iterable[UnitTestResult]] = None
	) -> None:
		"""
		Initializes a test result.

		:param executionId:    Identifier of this execution of the test.
		:param testId:         Identifier of the test's definition.
		:param testName:       Name of the test.
		:param computerName:   Name of the computer the test ran on.
		:param outcome:        Outcome of the test.
		:param testListId:     Identifier of the test list the result is filed in.
		:param startTime:      Optional, time the test started.
		:param endTime:        Optional, time the test ended.
		:param duration:       Optional, duration of the test.
		:param message:        Optional, message why the test failed or was skipped.
		:param details:        Optional, stack trace of a failed test.
		:param standardOutput: Optional, captured standard output of the test.
		:param standardError:  Optional, captured standard error of the test.
		:param innerResults:   Optional, results of the rows of a data-driven test or the tests of an ordered test.
		:raises TypeError:     If parameter 'message' is not of type :class:`str`.
		:raises TypeError:     If parameter 'details' is not of type :class:`str`.
		:raises TypeError:     If parameter 'standardOutput' is not of type :class:`str`.
		:raises TypeError:     If parameter 'standardError' is not of type :class:`str`.
		:raises ValueError:    If parameter 'executionId' is None.
		:raises TypeError:     If parameter 'executionId' is not of type :class:`~uuid.UUID`.
		:raises ValueError:    If parameter 'testId' is None.
		:raises TypeError:     If parameter 'testId' is not of type :class:`~uuid.UUID`.
		:raises ValueError:    If parameter 'testListId' is None.
		:raises TypeError:     If parameter 'testListId' is not of type :class:`~uuid.UUID`.
		:raises ValueError:    If parameter 'testName' is None.
		:raises TypeError:     If parameter 'testName' is not of type :class:`str`.
		:raises ValueError:    If parameter 'testName' is empty.
		:raises ValueError:    If parameter 'computerName' is None.
		:raises TypeError:     If parameter 'computerName' is not of type :class:`str`.
		:raises ValueError:    If parameter 'computerName' is empty.
		:raises ValueError:    If parameter 'outcome' is None.
		:raises TypeError:     If parameter 'outcome' is not of type :class:`TestOutcome`.
		:raises TypeError:     If parameter 'startTime' is not of type :class:`~datetime.datetime`.
		:raises TypeError:     If parameter 'endTime' is not of type :class:`~datetime.datetime`.
		:raises TypeError:     If parameter 'duration' is not of type :class:`~datetime.timedelta`.
		:raises TypeError:     If parameter 'innerResults' is not iterable.
		:raises TypeError:     If an element of parameter 'innerResults' is not of type :class:`UnitTestResult`.
		"""
		TestcaseOutputMixin.__init__(self, message, details, standardOutput, standardError)

		for parameterName, value in (("executionId", executionId), ("testId", testId), ("testListId", testListId)):
			if value is None:
				raise ValueError(f"Parameter '{parameterName}' is None.")
			elif not isinstance(value, UUID):
				ex = TypeError(f"Parameter '{parameterName}' is not of type 'UUID'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
				raise ex

		for parameterName, value in (("testName", testName), ("computerName", computerName)):
			if value is None:
				raise ValueError(f"Parameter '{parameterName}' is None.")
			elif not isinstance(value, str):
				ex = TypeError(f"Parameter '{parameterName}' is not of type 'str'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
				raise ex
			elif value == "":
				raise ValueError(f"Parameter '{parameterName}' is empty.")

		if outcome is None:
			raise ValueError(f"Parameter 'outcome' is None.")
		elif not isinstance(outcome, TestOutcome):
			ex = TypeError(f"Parameter 'outcome' is not of type 'TestOutcome'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(outcome)}'.")
			raise ex

		for parameterName, value in (("startTime", startTime), ("endTime", endTime)):
			if value is not None and not isinstance(value, datetime):
				ex = TypeError(f"Parameter '{parameterName}' is not of type 'datetime'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
				raise ex

		if duration is not None and not isinstance(duration, timedelta):
			ex = TypeError(f"Parameter 'duration' is not of type 'timedelta'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(duration)}'.")
			raise ex

		self._executionId =  executionId
		self._testId =       testId
		self._testName =     testName
		self._computerName = computerName
		self._outcome =      outcome
		self._testListId =   testListId
		self._startTime =    startTime
		self._endTime =      endTime
		self._duration =     duration

		self._innerResults = []
		if innerResults is not None:
			if not isinstance(innerResults, Iterable):
				ex = TypeError(f"Parameter 'innerResults' is not iterable.")
				ex.add_note(f"Got type '{getFullyQualifiedName(innerResults)}'.")
				raise ex

			for innerResult in innerResults:
				if not isinstance(innerResult, UnitTestResult):
					ex = TypeError(f"Element of parameter 'innerResults' is not of type 'UnitTestResult'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(innerResult)}'.")
					raise ex

				self._innerResults.append(innerResult)

	@readonly
	def ExecutionId(self) -> UUID:
		"""
		Read-only property to access the identifier of this execution of the test (:attr:`_executionId`).

		:returns: The execution's identifier.
		"""
		return self._executionId

	@readonly
	def TestId(self) -> UUID:
		"""
		Read-only property to access the identifier of the test's definition (:attr:`_testId`).

		:returns: The test's identifier.
		"""
		return self._testId

	@readonly
	def TestName(self) -> str:
		"""
		Read-only property to access the test's name (:attr:`_testName`).

		Test adapters name a test differently: xUnit.net prefixes the class name
		(``MyLibrary.Tests.CalculatorTests.Absolute(value: 3, expected: 3)``), MSTest and NUnit don't (``Rows (1,1)``).

		:returns: The test's name.
		"""
		return self._testName

	@readonly
	def ComputerName(self) -> str:
		"""
		Read-only property to access the name of the computer the test ran on (:attr:`_computerName`).

		:returns: The computer's name.
		"""
		return self._computerName

	@readonly
	def Outcome(self) -> TestOutcome:
		"""
		Read-only property to access the test's outcome (:attr:`_outcome`).

		:returns: The test's outcome.
		"""
		return self._outcome

	@readonly
	def TestListId(self) -> UUID:
		"""
		Read-only property to access the identifier of the test list the result is filed in (:attr:`_testListId`).

		:returns: The test list's identifier.
		"""
		return self._testListId

	@readonly
	def StartTime(self) -> Nullable[datetime]:
		"""
		Read-only property to access the time the test started (:attr:`_startTime`).

		:returns: The start time, or ``None`` if it wasn't recorded.
		"""
		return self._startTime

	@readonly
	def EndTime(self) -> Nullable[datetime]:
		"""
		Read-only property to access the time the test ended (:attr:`_endTime`).

		:returns: The end time, or ``None`` if it wasn't recorded.
		"""
		return self._endTime

	@readonly
	def Duration(self) -> Nullable[timedelta]:
		"""
		Read-only property to access the test's duration (:attr:`_duration`).

		The duration is measured by the test adapter; it can differ from the difference of start and end time. xUnit.net
		rounds it to milliseconds.

		:returns: The duration, or ``None`` if it wasn't recorded.
		"""
		return self._duration

	@readonly
	def InnerResults(self) -> List[UnitTestResult]:
		"""
		Read-only property to access the results of the rows of a data-driven test or the tests of an ordered test
		(:attr:`_innerResults`).

		:returns: The inner results; an empty list for a single test.
		"""
		return self._innerResults


@export
class TestRun(metaclass=ExtendedType, slots=True):
	"""
	A test run (``<TestRun>``): the test definitions, their results, the test lists and the run's summary.

	The summary's counters are kept as written. They can contradict the results: VSTest's TRX logger counts a skipped
	test only in ``total``. :meth:`ToTestsuiteSummary` counts the results instead.
	"""

	_id:             Nullable[UUID]         #: Identifier of the test run.
	_name:           str                    #: Name of the test run, e.g. ``user@host 2026-10-08 11:09:27``.
	_startTime:      Nullable[datetime]     #: Time the test run started.
	_finishTime:     Nullable[datetime]     #: Time the test run finished.
	_outcome:        Nullable[TestOutcome]  #: Outcome of the test run.
	_counters:       Dict[str, int]         #: Counters of the run's summary, by attribute name (e.g. ``total``).
	_standardOutput: Nullable[str]          #: Messages of the test framework and the test adapter for the whole run.
	_testLists:      Dict[UUID, str]        #: Names of the test lists, by identifier.
	_unitTests:      Dict[UUID, UnitTest]   #: Test definitions, by identifier.
	_results:        List[UnitTestResult]   #: Test results, in the order of the file.

	def __init__(
		self,
		name: str,
		id: Nullable[UUID] = None,
		startTime: Nullable[datetime] = None,
		finishTime: Nullable[datetime] = None,
		outcome: Nullable[TestOutcome] = None,
		counters: Nullable[Mapping[str, int]] = None,
		standardOutput: Nullable[str] = None,
		testLists: Nullable[Mapping[UUID, str]] = None,
		unitTests: Nullable[Iterable[UnitTest]] = None,
		results: Nullable[Iterable[UnitTestResult]] = None
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
		:param unitTests:      Optional, test definitions.
		:param results:        Optional, test results.
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
		:raises TypeError:     If parameter 'unitTests' is not iterable.
		:raises TypeError:     If an element of parameter 'unitTests' is not of type :class:`UnitTest`.
		:raises TypeError:     If parameter 'results' is not iterable.
		:raises TypeError:     If an element of parameter 'results' is not of type :class:`UnitTestResult`.
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

		self._unitTests = {}
		if unitTests is not None:
			if not isinstance(unitTests, Iterable):
				ex = TypeError(f"Parameter 'unitTests' is not iterable.")
				ex.add_note(f"Got type '{getFullyQualifiedName(unitTests)}'.")
				raise ex

			for unitTest in unitTests:
				if not isinstance(unitTest, UnitTest):
					ex = TypeError(f"Element of parameter 'unitTests' is not of type 'UnitTest'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(unitTest)}'.")
					raise ex

				self._unitTests[unitTest._id] = unitTest

		self._results = []
		if results is not None:
			if not isinstance(results, Iterable):
				ex = TypeError(f"Parameter 'results' is not iterable.")
				ex.add_note(f"Got type '{getFullyQualifiedName(results)}'.")
				raise ex

			for result in results:
				if not isinstance(result, UnitTestResult):
					ex = TypeError(f"Element of parameter 'results' is not of type 'UnitTestResult'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(result)}'.")
					raise ex

				self._results.append(result)

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

	@readonly
	def UnitTests(self) -> Dict[UUID, UnitTest]:
		"""
		Read-only property to access the test definitions (:attr:`_unitTests`).

		:returns: The test definitions, by identifier.
		"""
		return self._unitTests

	@readonly
	def Results(self) -> List[UnitTestResult]:
		"""
		Read-only property to access the test results (:attr:`_results`).

		:returns: The test results, in the order of the file.
		"""
		return self._results

	def ToTestsuiteSummary(self) -> ut_TestsuiteSummary:
		"""
		Convert the test run to a test suite summary of the unified data model.

		The summary is named after the test run. It contains a test suite per test assembly (named after the assembly's
		file), which contains a test suite per namespace and a test suite per test class. A result becomes a test case in
		its class' test suite, named after the test without the class name. A container's inner results become test cases,
		the container doesn't. Afterwards, the hierarchy is aggregated: the counters are computed from the results; the
		run's :attr:`Counters` aren't used.

		:returns:                       A test suite summary of the unified data model.
		:raises UnittestError:          If a result refers to no test definition.
		:raises DuplicateTestcaseError: If two results of a test class have the same name.
		"""
		summary = ut_TestsuiteSummary(
			self._name,
			startTime=self._startTime,
			totalDuration=None if self._startTime is None or self._finishTime is None else self._finishTime - self._startTime
		)

		def convertResult(result: UnitTestResult) -> None:
			"""
			Nested function for recursion.

			:param result:                  The test result to convert.
			:raises UnittestError:          If the result refers to no test definition.
			:raises DuplicateTestcaseError: If the test suite of the result's class has a test case of the same name.
			"""
			if len(result._innerResults) > 0:
				for innerResult in result._innerResults:
					convertResult(innerResult)
				return

			try:
				unitTest = self._unitTests[result._testId]
			except KeyError:
				ex = UnittestError(f"Test result '{result._testName}' refers to no test definition.")
				ex.add_note(f"Got test ID '{result._testId}'.")
				raise ex from None

			assemblyName = unitTest._codeBase.name
			if (testsuite := summary._testsuites.get(assemblyName, None)) is None:
				testsuite = ut_Testsuite(assemblyName, hostname=result._computerName, parent=summary)

			*namespaces, className = unitTest._className.split(".")
			for namespace in namespaces:
				if (namespaceTestsuite := testsuite._testsuites.get(namespace, None)) is None:
					namespaceTestsuite = ut_Testsuite(namespace, kind=TestsuiteKind.Namespace, parent=testsuite)
				testsuite = namespaceTestsuite

			if (classTestsuite := testsuite._testsuites.get(className, None)) is None:
				classTestsuite = ut_Testsuite(className, kind=TestsuiteKind.Class, parent=testsuite)

			classTestsuite.AddTestcase(ut_Testcase(
				result._testName.removeprefix(f"{unitTest._className}."),
				startTime=result._startTime,
				testDuration=result._duration,
				status=STATUS_MAP[result._outcome],
				message=result._message,
				details=result._details,
				standardOutput=result._standardOutput,
				standardError=result._standardError
			))

		for result in self._results:
			convertResult(result)

		summary.Aggregate()
		return summary


@export
class Document(TestRun, ut_Document):
	"""
	A document reader for TRX files written by VSTest's TRX logger.

	The file is validated against :file:`VSTest-TRX.xsd`, an XML schema reverse engineered from the logger's source
	code. Afterwards, its content is converted into a :class:`TestRun`.
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
		Convert the parsed and validated XML data structure into a test run.

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

			for element in rootElement.iterfind("trx:TestDefinitions/trx:UnitTest", namespaces):  # type: _Element
				methodElement = element.find("trx:TestMethod", namespaces)
				unitTest = UnitTest(
					UUID(element.attrib["id"]),
					element.attrib["name"],
					methodElement.attrib["className"],
					methodElement.attrib["name"],
					Path(PureWindowsPath(methodElement.attrib["codeBase"]).as_posix()),
					methodElement.attrib["adapterTypeName"]
				)
				self._unitTests[unitTest._id] = unitTest

			for element in rootElement.iterfind("trx:Results/*", namespaces):  # type: _Element
				self._results.append(self._ConvertResult(element))

		self._modelConversion = sw.Duration

	def _ConvertResult(self, resultElement: _Element) -> UnitTestResult:
		"""
		Convert a ``<UnitTestResult>`` or ``<TestResultAggregation>`` element and its inner results to a test result.

		:param resultElement: The XML element node representing a test result.
		:returns:             The test result.
		"""
		namespaces = {"trx": TRX_NAMESPACE}
		attributes = resultElement.attrib

		duration = None
		durationMatch = fullmatch(r"(?:(\d+)\.)?(\d{2}):(\d{2}):(\d{2})(?:\.(\d{7}))?", attributes.get("duration", ""))
		if durationMatch is not None:
			days, hours, minutes, seconds, ticks = durationMatch.groups(default="0")
			duration = timedelta(
				days=int(days), hours=int(hours), minutes=int(minutes), seconds=int(seconds), microseconds=int(ticks) // 10
			)

		return UnitTestResult(
			UUID(attributes["executionId"]),
			UUID(attributes["testId"]),
			attributes["testName"],
			attributes["computerName"],
			TestOutcome(attributes.get("outcome", TestOutcome.Error.value)),
			UUID(attributes["testListId"]),
			startTime=None if (startTime := attributes.get("startTime", None)) is None else datetime.fromisoformat(startTime),
			endTime=None if (endTime := attributes.get("endTime", None)) is None else datetime.fromisoformat(endTime),
			duration=duration,
			message=resultElement.findtext("trx:Output/trx:ErrorInfo/trx:Message", namespaces=namespaces),
			details=resultElement.findtext("trx:Output/trx:ErrorInfo/trx:StackTrace", namespaces=namespaces),
			standardOutput=resultElement.findtext("trx:Output/trx:StdOut", namespaces=namespaces),
			standardError=resultElement.findtext("trx:Output/trx:StdErr", namespaces=namespaces),
			innerResults=(
				self._ConvertResult(element) for element in resultElement.iterfind("trx:InnerResults/*", namespaces)
			)
		)
