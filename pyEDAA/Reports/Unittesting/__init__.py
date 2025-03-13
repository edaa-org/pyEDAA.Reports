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
# Copyright 2024-2025 Electronic Design Automation Abstraction (EDA²)                                                  #
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
The pyEDAA.Reports.Unittesting package implements a hierarchy of test entities. These are test cases, test suites and a
test summary provided as a class hierarchy. Test cases are the leaf elements in the hierarchy and abstract an
individual test run. Test suites are used to group multiple test cases or other test suites. The root element is a test
summary. When such a summary is stored in a file format like Ant + JUnit4 XML, a file format specific document is
derived from a summary class.

**Data Model**

.. mermaid::

	 graph TD;
		 doc[Document]
		 sum[Summary]
		 ts1[Testsuite]
		 ts2[Testsuite]
		 ts21[Testsuite]
		 tc11[Testcase]
		 tc12[Testcase]
		 tc13[Testcase]
		 tc21[Testcase]
		 tc22[Testcase]
		 tc211[Testcase]
		 tc212[Testcase]
		 tc213[Testcase]

		 doc:::root -.-> sum:::summary
		 sum --> ts1:::suite
		 sum --> ts2:::suite
		 ts2 --> ts21:::suite
		 ts1 --> tc11:::case
		 ts1 --> tc12:::case
		 ts1 --> tc13:::case
		 ts2 --> tc21:::case
		 ts2 --> tc22:::case
		 ts21 --> tc211:::case
		 ts21 --> tc212:::case
		 ts21 --> tc213:::case

		 classDef root fill:#4dc3ff
		 classDef summary fill:#80d4ff
		 classDef suite fill:#b3e6ff
		 classDef case fill:#eeccff
"""
from datetime              import timedelta, datetime
from enum                  import Flag, IntEnum
from pathlib               import Path
from sys                   import version_info
from typing                import Optional as Nullable, Dict, Iterable, Any, Tuple, Generator, Union, List, Generic, TypeVar, Mapping

from pyTooling.Common      import getFullyQualifiedName
from pyTooling.Decorators  import export, readonly
from pyTooling.MetaClasses import ExtendedType, abstractmethod
from pyTooling.Tree        import Node

from pyEDAA.Reports        import ReportException


@export
class UnittestException(ReportException):
	"""Base-exception for all unit test related exceptions."""


@export
class AlreadyInHierarchyException(UnittestException):
	"""
	A unit test exception raised if the element is already part of a hierarchy.

	This exception is caused by an inconsistent data model. Elements added to the hierarchy should be part of the same
	hierarchy should occur only once in the hierarchy.

	.. hint::

	   This is usually caused by a non-None parent reference.
	"""


@export
class DuplicateTestsuiteException(UnittestException):
	"""
	A unit test exception raised on duplicate test suites (by name).

	This exception is raised, if a child test suite with same name already exist in the test suite.

	.. hint::

	   Test suite names need to be unique per parent element (test suite or test summary).
	"""


@export
class DuplicateTestcaseException(UnittestException):
	"""
	A unit test exception raised on duplicate test cases (by name).

	This exception is raised, if a child test case with same name already exist in the test suite.

	.. hint::

	   Test case names need to be unique per parent element (test suite).
	"""


@export
class TestcaseStatus(Flag):
	"""A flag enumeration describing the status of a test case."""
	Unknown =    0                         #: Testcase status is uninitialized and therefore unknown.
	Excluded =   1                         #: Testcase was permanently excluded / disabled
	Skipped =    2                         #: Testcase was temporarily skipped (e.g. based on a condition)
	Weak =       4                         #: No assertions were recorded.
	Passed =     8                         #: A passed testcase, because all assertions were successful.
	Failed =    16                         #: A failed testcase due to at least one failed assertion.

	Mask = Excluded | Skipped | Weak | Passed | Failed

	Inverted = 128                         #: To mark inverted results
	UnexpectedPassed = Failed | Inverted
	ExpectedFailed =   Passed | Inverted

	Warned =  1024                         #: Runtime warning
	Errored = 2048                         #: Runtime error (mostly caught exceptions)
	Aborted = 4096                         #: Uncaught runtime exception

	SetupError =     8192                  #: Preparation / compilation error
	TearDownError = 16384                  #: Cleanup error / resource release error
	Inconsistent = 32768                   #: Dataset is inconsistent

	Flags = Warned | Errored | Aborted | SetupError | TearDownError | Inconsistent

	# TODO: timed out ?
	# TODO: some passed (if merged, mixed results of passed and failed)

	def __matmul__(self, other: "TestcaseStatus") -> "TestcaseStatus":
		s = self & self.Mask
		o = other & self.Mask
		if s is self.Excluded:
			resolved = self.Excluded if o is self.Excluded else self.Unknown
		elif s is self.Skipped:
			resolved = self.Unknown if (o is self.Unknown) or (o is self.Excluded) else o
		elif s is self.Weak:
			resolved = self.Weak if o is self.Weak else self.Unknown
		elif s is self.Passed:
			if o is self.Failed:
				resolved = self.Failed
			else:
				resolved = self.Passed if (o is self.Skipped) or (o is self.Passed) else self.Unknown
		elif s is self.Failed:
			resolved = self.Failed if (o is self.Skipped) or (o is self.Passed) or (o is self.Failed) else self.Unknown
		else:
			resolved = self.Unknown

		resolved |= (self & self.Flags) | (other & self.Flags)
		return resolved


@export
class TestsuiteStatus(Flag):
	"""A flag enumeration describing the status of a test suite."""
	Unknown =    0
	Excluded =   1                         #: Testcase was permanently excluded / disabled
	Skipped =    2                         #: Testcase was temporarily skipped (e.g. based on a condition)
	Empty =      4                         #: No tests in suite
	Passed =     8                         #: Passed testcase, because all assertions succeeded
	Failed =    16                         #: Failed testcase due to failing assertions

	Mask = Excluded | Skipped | Empty | Passed | Failed

	Inverted = 128                         #: To mark inverted results
	UnexpectedPassed = Failed | Inverted
	ExpectedFailed =   Passed | Inverted

	Warned =  1024                         #: Runtime warning
	Errored = 2048                         #: Runtime error (mostly caught exceptions)
	Aborted = 4096                         #: Uncaught runtime exception

	SetupError =     8192                  #: Preparation / compilation error
	TearDownError = 16384                  #: Cleanup error / resource release error

	Flags = Warned | Errored | Aborted | SetupError | TearDownError


@export
class TestsuiteKind(IntEnum):
	"""Enumeration describing the kind of test suite."""
	Root = 0       #: Root element of the hierarchy.
	Logical = 1    #: Represents a logical unit.
	Namespace = 2  #: Represents a namespace.
	Package = 3    #: Represents a package.
	Module = 4     #: Represents a module.
	Class = 5      #: Represents a class.


@export
class IterationScheme(Flag):
	"""
	A flag enumeration for selecting the test suite iteration scheme.

	When a test entity hierarchy is (recursively) iterated, this iteration scheme describes how to iterate the hierarchy
	and what elements to return as a result.
	"""
	Unknown =           0    #: Neutral element.
	IncludeSelf =       1    #: Also include the element itself.
	IncludeTestsuites = 2    #: Include test suites into the result.
	IncludeTestcases =  4    #: Include test cases into the result.

	Recursive =         8    #: Iterate recursively.

	PreOrder =         16    #: Iterate in pre-order (top-down: current node, then child element left-to-right).
	PostOrder =        32    #: Iterate in pre-order (bottom-up: child element left-to-right, then current node).

	Default =          IncludeTestsuites | Recursive | IncludeTestcases | PreOrder  #: Recursively iterate all test entities in pre-order.
	TestsuiteDefault = IncludeTestsuites | Recursive | PreOrder                     #: Recursively iterate only test suites in pre-order.
	TestcaseDefault =  IncludeTestcases  | Recursive | PreOrder                     #: Recursively iterate only test cases in pre-order.


TestsuiteType = TypeVar("TestsuiteType", bound="Testsuite")
TestcaseAggregateReturnType = Tuple[int, int, int, timedelta]
TestsuiteAggregateReturnType = Tuple[int, int, int, int, int, int, int, int, int, int, int, timedelta]


@export
class Base(metaclass=ExtendedType, slots=True):
	"""
	Base-class for all test entities (test cases, test suites, ...).

	It provides a reference to the parent test entity, so bidirectional referencing can be used in the test entity
	hierarchy.

	Every test entity has a name to identity it. It's also used in the parent's child element dictionaries to identify the
	child. |br|
	E.g. it's used as a test case name in the dictionary of test cases in a test suite.

	Every test entity has fields for time tracking. If known, a start time and a test duration can be set. For more
	details, a setup duration and teardown duration can be added. All durations are summed up in a total duration field.

	As tests can have warnings and errors or even fail, these messages are counted and aggregated in the test entity
	hierarchy.

	Every test entity offers an internal dictionary for annotations. |br|
	This feature is for example used by Ant + JUnit4's XML property fields.
	"""

	_parent: Nullable["TestsuiteBase"]
	_name:   str

	_startTime:        Nullable[datetime]
	_setupDuration:    Nullable[timedelta]
	_testDuration:     Nullable[timedelta]
	_teardownDuration: Nullable[timedelta]
	_totalDuration:    Nullable[timedelta]

	_warningCount: int
	_errorCount:   int
	_fatalCount:   int

	_dict:         Dict[str, Any]

	def __init__(
		self,
		name: str,
		startTime: Nullable[datetime] = None,
		setupDuration: Nullable[timedelta] = None,
		testDuration: Nullable[timedelta] = None,
		teardownDuration: Nullable[timedelta] = None,
		totalDuration:  Nullable[timedelta] = None,
		warningCount: int = 0,
		errorCount: int = 0,
		fatalCount: int = 0,
		keyValuePairs: Nullable[Mapping[str, Any]] = None,
		parent: Nullable["TestsuiteBase"] = None
	):
		"""
		Initializes the fields of the base-class.

		:param name:               Name of the test entity.
		:param startTime:          Time when the test entity was started.
		:param setupDuration:      Duration it took to set up the entity.
		:param testDuration:       Duration of the entity's test run.
		:param teardownDuration:   Duration it took to tear down the entity.
		:param totalDuration:      Total duration of the entity's execution (setup + test + teardown).
		:param warningCount:       Count of encountered warnings.
		:param errorCount:         Count of encountered errors.
		:param fatalCount:         Count of encountered fatal errors.
		:param keyValuePairs:      Mapping of key-value pairs to initialize the test entity with.
		:param parent:             Reference to the parent test entity.
		:raises TypeError:         If parameter 'parent' is not a TestsuiteBase.
		:raises ValueError:        If parameter 'name' is None.
		:raises TypeError:         If parameter 'name' is not a string.
		:raises ValueError:        If parameter 'name' is empty.
		:raises TypeError:         If parameter 'testDuration' is not a timedelta.
		:raises TypeError:         If parameter 'setupDuration' is not a timedelta.
		:raises TypeError:         If parameter 'teardownDuration' is not a timedelta.
		:raises TypeError:         If parameter 'totalDuration' is not a timedelta.
		:raises TypeError:         If parameter 'warningCount' is not an integer.
		:raises TypeError:         If parameter 'errorCount' is not an integer.
		:raises TypeError:         If parameter 'fatalCount' is not an integer.
		:raises TypeError:         If parameter 'keyValuePairs' is not a Mapping.
		:raises ValueError:        If parameter 'totalDuration' is not consistent.
		"""

		if parent is not None and not isinstance(parent, TestsuiteBase):
			ex = TypeError(f"Parameter 'parent' is not of type 'TestsuiteBase'.")
			if version_info >= (3, 11):  # pragma: no cover
				ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		if name is None:
			raise ValueError(f"Parameter 'name' is None.")
		elif not isinstance(name, str):
			ex = TypeError(f"Parameter 'name' is not of type 'str'.")
			if version_info >= (3, 11):  # pragma: no cover
				ex.add_note(f"Got type '{getFullyQualifiedName(name)}'.")
			raise ex
		elif name.strip() == "":
			raise ValueError(f"Parameter 'name' is empty.")

		self._parent = parent
		self._name = name

		if testDuration is not None and not isinstance(testDuration, timedelta):
			ex = TypeError(f"Parameter 'testDuration' is not of type 'timedelta'.")
			if version_info >= (3, 11):  # pragma: no cover
				ex.add_note(f"Got type '{getFullyQualifiedName(testDuration)}'.")
			raise ex

		if setupDuration is not None and not isinstance(setupDuration, timedelta):
			ex = TypeError(f"Parameter 'setupDuration' is not of type 'timedelta'.")
			if version_info >= (3, 11):  # pragma: no cover
				ex.add_note(f"Got type '{getFullyQualifiedName(setupDuration)}'.")
			raise ex

		if teardownDuration is not None and not isinstance(teardownDuration, timedelta):
			ex = TypeError(f"Parameter 'teardownDuration' is not of type 'timedelta'.")
			if version_info >= (3, 11):  # pragma: no cover
				ex.add_note(f"Got type '{getFullyQualifiedName(teardownDuration)}'.")
			raise ex

		if totalDuration is not None and not isinstance(totalDuration, timedelta):
			ex = TypeError(f"Parameter 'totalDuration' is not of type 'timedelta'.")
			if version_info >= (3, 11):  # pragma: no cover
				ex.add_note(f"Got type '{getFullyQualifiedName(totalDuration)}'.")
			raise ex

		if testDuration is not None:
			if setupDuration is not None:
				if teardownDuration is not None:
					if totalDuration is not None:
						if totalDuration < (setupDuration + testDuration + teardownDuration):
							raise ValueError(f"Parameter 'totalDuration' can not be less than the sum of setup, test and teardown durations.")
					else:  # no total
						totalDuration = setupDuration + testDuration + teardownDuration
				# no teardown
				elif totalDuration is not None:
					if totalDuration < (setupDuration + testDuration):
						raise ValueError(f"Parameter 'totalDuration' can not be less than the sum of setup and test durations.")
				# no teardown, no total
				else:
					totalDuration = setupDuration + testDuration
			# no setup
			elif teardownDuration is not None:
				if totalDuration is not None:
					if totalDuration < (testDuration + teardownDuration):
						raise ValueError(f"Parameter 'totalDuration' can not be less than the sum of test and teardown durations.")
				else:  # no setup, no total
					totalDuration = testDuration + teardownDuration
			# no setup, no teardown
			elif totalDuration is not None:
				if totalDuration < testDuration:
					raise ValueError(f"Parameter 'totalDuration' can not be less than test durations.")
			else:  # no setup, no teardown, no total
				totalDuration = testDuration
		# no test
		elif totalDuration is not None:
			testDuration = totalDuration
			if setupDuration is not None:
				testDuration -= setupDuration
			if teardownDuration is not None:
				testDuration -= teardownDuration

		self._startTime = startTime
		self._setupDuration = setupDuration
		self._testDuration = testDuration
		self._teardownDuration = teardownDuration
		self._totalDuration = totalDuration

		if not isinstance(warningCount, int):
			ex = TypeError(f"Parameter 'warningCount' is not of type 'int'.")
			if version_info >= (3, 11):  # pragma: no cover
				ex.add_note(f"Got type '{getFullyQualifiedName(warningCount)}'.")
			raise ex

		if not isinstance(errorCount, int):
			ex = TypeError(f"Parameter 'errorCount' is not of type 'int'.")
			if version_info >= (3, 11):  # pragma: no cover
				ex.add_note(f"Got type '{getFullyQualifiedName(errorCount)}'.")
			raise ex

		if not isinstance(fatalCount, int):
			ex = TypeError(f"Parameter 'fatalCount' is not of type 'int'.")
			if version_info >= (3, 11):  # pragma: no cover
				ex.add_note(f"Got type '{getFullyQualifiedName(fatalCount)}'.")
			raise ex

		self._warningCount = warningCount
		self._errorCount = errorCount
		self._fatalCount = fatalCount

		if keyValuePairs is not None and not isinstance(keyValuePairs, Mapping):
			ex = TypeError(f"Parameter 'keyValuePairs' is not a mapping.")
			if version_info >= (3, 11):  # pragma: no cover
				ex.add_note(f"Got type '{getFullyQualifiedName(keyValuePairs)}'.")
			raise ex

		self._dict = {} if keyValuePairs is None else {k: v for k, v in keyValuePairs}

	# QUESTION: allow Parent as setter?
	@readonly
	def Parent(self) -> Nullable["TestsuiteBase"]:
		"""
		Read-only property returning the reference to the parent test entity.

		:return: Reference to the parent entity.
		"""
		return self._parent

	@readonly
	def Name(self) -> str:
		"""
		Read-only property returning the test entity's name.

		:return:
		"""
		return self._name

	@readonly
	def StartTime(self) -> Nullable[datetime]:
		"""
		Read-only property returning the time when the test entity was started.

		:return: Time when the test entity was started.
		"""
		return self._startTime

	@readonly
	def SetupDuration(self) -> Nullable[timedelta]:
		"""
		Read-only property returning the duration of the test entity's setup.

		:return: Duration it took to set up the entity.
		"""
		return self._setupDuration

	@readonly
	def TestDuration(self) -> Nullable[timedelta]:
		"""
		Read-only property returning the duration of a test entities run.

		This duration is excluding setup and teardown durations. In case setup and/or teardown durations are unknown or not
		distinguishable, assign setup and teardown durations with zero.

		:return: Duration of the entity's test run.
		"""
		return self._testDuration

	@readonly
	def TeardownDuration(self) -> Nullable[timedelta]:
		"""
		Read-only property returning the duration of the test entity's teardown.

		:return: Duration it took to tear down the entity.
		"""
		return self._teardownDuration

	@readonly
	def TotalDuration(self) -> Nullable[timedelta]:
		"""
		Read-only property returning the total duration of a test entity run.

		this duration includes setup and teardown durations.

		:return: Total duration of the entity's execution (setup + test + teardown)
		"""
		return self._totalDuration

	@readonly
	def WarningCount(self) -> int:
		"""
		Read-only property returning the number of encountered warnings.

		:return: Count of encountered warnings.
		"""
		return self._warningCount

	@readonly
	def ErrorCount(self) -> int:
		"""
		Read-only property returning the number of encountered errors.

		:return: Count of encountered errors.
		"""
		return self._errorCount

	@readonly
	def FatalCount(self) -> int:
		"""
		Read-only property returning the number of encountered fatal errors.

		:return: Count of encountered fatal errors.
		"""
		return self._fatalCount

	def __len__(self) -> int:
		"""
		Returns the number of annotated key-value pairs.

		:return: Number of annotated key-value pairs.
		"""
		return len(self._dict)

	def __getitem__(self, key: str) -> Any:
		"""
		Access a key-value pair by key.

		:param key: Name if the key-value pair.
		:return:    Value of the accessed key.
		"""
		return self._dict[key]

	def __setitem__(self, key: str, value: Any) -> None:
		"""
		Set the value of a key-value pair by key.

		If the pair doesn't exist yet, it's created.

		:param key:   Key of the key-value pair.
		:param value: Value of the key-value pair.
		"""
		self._dict[key] = value

	def __delitem__(self, key: str) -> None:
		"""
		Delete a key-value pair by key.

		:param key: Name if the key-value pair.
		"""
		del self._dict[key]

	def __contains__(self, key: str) -> bool:
		"""
		Returns True, if a key-value pairs was annotated by this key.

		:param key: Name of the key-value pair.
		:return:    True, if the pair was annotated.
		"""
		return key in self._dict

	def __iter__(self) -> Generator[Tuple[str, Any], None, None]:
		"""
		Iterate all annotated key-value pairs.

		:return: A generator of key-value pair tuples (key, value).
		"""
		yield from self._dict.items()

	@abstractmethod
	def Aggregate(self, strict: bool = True):
		"""
		Aggregate all test entities in the hierarchy.

		:return:
		"""

	@abstractmethod
	def __str__(self) -> str:
		"""
		Formats the test entity as human-readable incl. some statistics.
		"""


@export
class Testcase(Base):
	"""
	A testcase is the leaf-entity in the test entity hierarchy representing an individual test run.

	Test cases are grouped by test suites in the test entity hierarchy. The root of the hierarchy is a test summary.

	Every test case has an overall status like unknown, skipped, failed or passed.

	In addition to all features from its base-class, test cases provide additional statistics for passed and failed
	assertions (checks) as well as a sum thereof.
	"""

	_status:               TestcaseStatus
	_assertionCount:       Nullable[int]
	_failedAssertionCount: Nullable[int]
	_passedAssertionCount: Nullable[int]

	def __init__(
		self,
		name: str,
		startTime: Nullable[datetime] = None,
		setupDuration: Nullable[timedelta] = None,
		testDuration: Nullable[timedelta] = None,
		teardownDuration: Nullable[timedelta] = None,
		totalDuration:  Nullable[timedelta] = None,
		status: TestcaseStatus = TestcaseStatus.Unknown,
		assertionCount: Nullable[int] = None,
		failedAssertionCount: Nullable[int] = None,
		passedAssertionCount: Nullable[int] = None,
		warningCount: int = 0,
		errorCount: int = 0,
		fatalCount: int = 0,
		keyValuePairs: Nullable[Mapping[str, Any]] = None,
		parent: Nullable["Testsuite"] = None
	):
		"""
		Initializes the fields of a test case.

		:param name:                 Name of the test entity.
		:param startTime:            Time when the test entity was started.
		:param setupDuration:        Duration it took to set up the entity.
		:param testDuration:         Duration of the entity's test run.
		:param teardownDuration:     Duration it took to tear down the entity.
		:param totalDuration:        Total duration of the entity's execution (setup + test + teardown)
		:param status:               Status of the test case.
		:param assertionCount:       Number of assertions within the test.
		:param failedAssertionCount: Number of failed assertions within the test.
		:param passedAssertionCount: Number of passed assertions within the test.
		:param warningCount:         Count of encountered warnings.
		:param errorCount:           Count of encountered errors.
		:param fatalCount:           Count of encountered fatal errors.
		:param keyValuePairs:        Mapping of key-value pairs to initialize the test case.
		:param parent:               Reference to the parent test suite.
		:raises TypeError:           If parameter 'parent' is not a Testsuite.
		:raises ValueError:          If parameter 'assertionCount' is not consistent.
		"""

		if parent is not None:
			if not isinstance(parent, Testsuite):
				ex = TypeError(f"Parameter 'parent' is not of type 'Testsuite'.")
				if version_info >= (3, 11):  # pragma: no cover
					ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
				raise ex

			parent._testcases[name] = self

		super().__init__(
			name,
			startTime,
			setupDuration,
			testDuration,
			teardownDuration,
			totalDuration,
			warningCount,
			errorCount,
			fatalCount,
			keyValuePairs,
			parent
		)

		if not isinstance(status, TestcaseStatus):
			ex = TypeError(f"Parameter 'status' is not of type 'TestcaseStatus'.")
			if version_info >= (3, 11):  # pragma: no cover
				ex.add_note(f"Got type '{getFullyQualifiedName(status)}'.")
			raise ex

		self._status = status

		if assertionCount is not None and not isinstance(assertionCount, int):
			ex = TypeError(f"Parameter 'assertionCount' is not of type 'int'.")
			if version_info >= (3, 11):  # pragma: no cover
				ex.add_note(f"Got type '{getFullyQualifiedName(assertionCount)}'.")
			raise ex

		if failedAssertionCount is not None and not isinstance(failedAssertionCount, int):
			ex = TypeError(f"Parameter 'failedAssertionCount' is not of type 'int'.")
			if version_info >= (3, 11):  # pragma: no cover
				ex.add_note(f"Got type '{getFullyQualifiedName(failedAssertionCount)}'.")
			raise ex

		if passedAssertionCount is not None and not isinstance(passedAssertionCount, int):
			ex = TypeError(f"Parameter 'passedAssertionCount' is not of type 'int'.")
			if version_info >= (3, 11):  # pragma: no cover
				ex.add_note(f"Got type '{getFullyQualifiedName(passedAssertionCount)}'.")
			raise ex

		self._assertionCount = assertionCount
		if assertionCount is not None:
			if failedAssertionCount is not None:
				self._failedAssertionCount = failedAssertionCount

				if passedAssertionCount is not None:
					if passedAssertionCount + failedAssertionCount != assertionCount:
						raise ValueError(f"passed assertion count ({passedAssertionCount}) + failed assertion count ({failedAssertionCount} != assertion count ({assertionCount}")

					self._passedAssertionCount = passedAssertionCount
				else:
					self._passedAssertionCount = assertionCount - failedAssertionCount
			elif passedAssertionCount is not None:
				self._passedAssertionCount = passedAssertionCount
				self._failedAssertionCount = assertionCount - passedAssertionCount
			else:
				raise ValueError(f"Neither passed assertion count nor failed assertion count are provided.")
		elif failedAssertionCount is not None:
			self._failedAssertionCount = failedAssertionCount

			if passedAssertionCount is not None:
				self._passedAssertionCount = passedAssertionCount
				self._assertionCount = passedAssertionCount + failedAssertionCount
			else:
				raise ValueError(f"Passed assertion count is mandatory, if failed assertion count is provided instead of assertion count.")
		elif passedAssertionCount is not None:
			raise ValueError(f"Assertion count or failed assertion count is mandatory, if passed assertion count is provided.")
		else:
			self._passedAssertionCount = None
			self._failedAssertionCount = None

	@readonly
	def Status(self) -> TestcaseStatus:
		"""
		Read-only property returning the status of the test case.

		:return: The test case's status.
		"""
		return self._status

	@readonly
	def AssertionCount(self) -> int:
		"""
		Read-only property returning the number of assertions (checks) in a test case.

		:return: Number of assertions.
		"""
		if self._assertionCount is None:
			return 0
		return self._assertionCount

	@readonly
	def FailedAssertionCount(self) -> int:
		"""
		Read-only property returning the number of failed assertions (failed checks) in a test case.

		:return: Number of assertions.
		"""
		return self._failedAssertionCount

	@readonly
	def PassedAssertionCount(self) -> int:
		"""
		Read-only property returning the number of passed assertions (successful checks) in a test case.

		:return: Number of passed assertions.
		"""
		return self._passedAssertionCount

	def Copy(self) -> "Testcase":
		return self.__class__(
			self._name,
			self._startTime,
			self._setupDuration,
			self._testDuration,
			self._teardownDuration,
			self._totalDuration,
			self._status,
			self._warningCount,
			self._errorCount,
			self._fatalCount,
		)

	def Aggregate(self, strict: bool = True) -> TestcaseAggregateReturnType:
		if self._status is TestcaseStatus.Unknown:
			if self._assertionCount is None:
				self._status = TestcaseStatus.Passed
			elif self._assertionCount == 0:
				self._status = TestcaseStatus.Weak
			elif self._failedAssertionCount == 0:
				self._status = TestcaseStatus.Passed
			else:
				self._status = TestcaseStatus.Failed

			if self._warningCount > 0:
				self._status |= TestcaseStatus.Warned

			if self._errorCount > 0:
				self._status |= TestcaseStatus.Errored

			if self._fatalCount > 0:
				self._status |= TestcaseStatus.Aborted

				if strict:
					self._status = self._status & ~TestcaseStatus.Passed | TestcaseStatus.Failed

			# TODO: check for setup errors
			# TODO: check for teardown errors

		totalDuration = timedelta() if self._totalDuration is None else self._totalDuration

		return self._warningCount, self._errorCount, self._fatalCount, totalDuration

	def __str__(self) -> str:
		"""
		Formats the test case as human-readable incl. statistics.

		:pycode:`f"<Testcase {}: {} - assert/pass/fail:{}/{}/{} - warn/error/fatal:{}/{}/{} - setup/test/teardown:{}/{}/{}>"`

		:return: Human-readable summary of a test case object.
		"""
		return (
			f"<Testcase {self._name}: {self._status.name} -"
			f" assert/pass/fail:{self._assertionCount}/{self._passedAssertionCount}/{self._failedAssertionCount} -"
			f" warn/error/fatal:{self._warningCount}/{self._errorCount}/{self._fatalCount} -"
			f" setup/test/teardown:{self._setupDuration:.3f}/{self._testDuration:.3f}/{self._teardownDuration:.3f}>"
		)


@export
class TestsuiteBase(Base, Generic[TestsuiteType]):
	"""
	Base-class for all test suites and for test summaries.

	A test suite is a mid-level grouping element in the test entity hierarchy, whereas the test summary is the root
	element in that hierarchy. While a test suite groups other test suites and test cases, a test summary can only group
	test suites. Thus, a test summary contains no test cases.
	"""

	_kind:       TestsuiteKind
	_status:     TestsuiteStatus
	_testsuites: Dict[str, TestsuiteType]

	_tests:        int
	_inconsistent: int
	_excluded:     int
	_skipped:      int
	_errored:      int
	_weak:         int
	_failed:       int
	_passed:       int

	def __init__(
		self,
		name: str,
		kind: TestsuiteKind = TestsuiteKind.Logical,
		startTime: Nullable[datetime] = None,
		setupDuration: Nullable[timedelta] = None,
		testDuration: Nullable[timedelta] = None,
		teardownDuration: Nullable[timedelta] = None,
		totalDuration:  Nullable[timedelta] = None,
		status: TestsuiteStatus = TestsuiteStatus.Unknown,
		warningCount: int = 0,
		errorCount: int = 0,
		fatalCount: int = 0,
		testsuites: Nullable[Iterable[TestsuiteType]] = None,
		keyValuePairs: Nullable[Mapping[str, Any]] = None,
		parent: Nullable["Testsuite"] = None
	):
		"""
		Initializes the based-class fields of a test suite or test summary.

		:param name:               Name of the test entity.
		:param kind:               Kind of the test entity.
		:param startTime:          Time when the test entity was started.
		:param setupDuration:      Duration it took to set up the entity.
		:param testDuration:       Duration of all tests listed in the test entity.
		:param teardownDuration:   Duration it took to tear down the entity.
		:param totalDuration:      Total duration of the entity's execution (setup + test + teardown)
		:param status:             Overall status of the test entity.
		:param warningCount:       Count of encountered warnings incl. warnings from sub-elements.
		:param errorCount:         Count of encountered errors incl. errors from sub-elements.
		:param fatalCount:         Count of encountered fatal errors incl. fatal errors from sub-elements.
		:param testsuites:         List of test suites to initialize the test entity with.
		:param keyValuePairs:      Mapping of key-value pairs to initialize the test entity with.
		:param parent:             Reference to the parent test entity.
		:raises TypeError:         If parameter 'parent' is not a TestsuiteBase.
		:raises TypeError:         If parameter 'testsuites' is not iterable.
		:raises TypeError:         If element in parameter 'testsuites' is not a Testsuite.
		:raises AlreadyInHierarchyException: If a test suite in parameter 'testsuites' is already part of a test entity hierarchy.
		:raises DuplicateTestsuiteException: If a test suite in parameter 'testsuites' is already listed (by name) in the list of test suites.
		"""
		if parent is not None:
			if not isinstance(parent, TestsuiteBase):
				ex = TypeError(f"Parameter 'parent' is not of type 'TestsuiteBase'.")
				if version_info >= (3, 11):  # pragma: no cover
					ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
				raise ex

			parent._testsuites[name] = self

		super().__init__(
			name,
			startTime,
			setupDuration,
			testDuration,
			teardownDuration,
			totalDuration,
			warningCount,
			errorCount,
			fatalCount,
			keyValuePairs,
			parent
		)

		self._kind = kind
		self._status = status

		self._testsuites = {}
		if testsuites is not None:
			if not isinstance(testsuites, Iterable):
				ex = TypeError(f"Parameter 'testsuites' is not iterable.")
				if version_info >= (3, 11):  # pragma: no cover
					ex.add_note(f"Got type '{getFullyQualifiedName(testsuites)}'.")
				raise ex

			for testsuite in testsuites:
				if not isinstance(testsuite, Testsuite):
					ex = TypeError(f"Element of parameter 'testsuites' is not of type 'Testsuite'.")
					if version_info >= (3, 11):  # pragma: no cover
						ex.add_note(f"Got type '{getFullyQualifiedName(testsuite)}'.")
					raise ex

				if testsuite._parent is not None:
					raise AlreadyInHierarchyException(f"Testsuite '{testsuite._name}' is already part of a testsuite hierarchy.")

				if testsuite._name in self._testsuites:
					raise DuplicateTestsuiteException(f"Testsuite already contains a testsuite with same name '{testsuite._name}'.")

				testsuite._parent = self
				self._testsuites[testsuite._name] = testsuite

		self._status = TestsuiteStatus.Unknown
		self._tests =        0
		self._inconsistent = 0
		self._excluded =     0
		self._skipped =      0
		self._errored =      0
		self._weak =         0
		self._failed =       0
		self._passed =       0

	@readonly
	def Kind(self) -> TestsuiteKind:
		"""
		Read-only property returning the kind of the test suite.

		Test suites are used to group test cases. This grouping can be due to language/framework specifics like tests
		grouped by a module file or namespace. Others might be just logically grouped without any relation to a programming
		language construct.

		Test summaries always return kind ``Root``.

		:return: Kind of the test suite.
		"""
		return self._kind

	@readonly
	def Status(self) -> TestsuiteStatus:
		"""
		Read-only property returning the aggregated overall status of the test suite.

		:return: Overall status of the test suite.
		"""
		return self._status

	@readonly
	def Testsuites(self) -> Dict[str, TestsuiteType]:
		"""
		Read-only property returning a reference to the internal dictionary of test suites.

		:return: Reference to the dictionary of test suite.
		"""
		return self._testsuites

	@readonly
	def TestsuiteCount(self) -> int:
		"""
		Read-only property returning the number of all test suites in the test suite hierarchy.

		:return: Number of test suites.
		"""
		return 1 + sum(testsuite.TestsuiteCount for testsuite in self._testsuites.values())

	@readonly
	def TestcaseCount(self) -> int:
		"""
		Read-only property returning the number of all test cases in the test entity hierarchy.

		:return: Number of test cases.
		"""
		return sum(testsuite.TestcaseCount for testsuite in self._testsuites.values())

	@readonly
	def AssertionCount(self) -> int:
		"""
		Read-only property returning the number of all assertions in all test cases in the test entity hierarchy.

		:return: Number of assertions in all test cases.
		"""
		return sum(ts.AssertionCount for ts in self._testsuites.values())

	@readonly
	def FailedAssertionCount(self) -> int:
		"""
		Read-only property returning the number of all failed assertions in all test cases in the test entity hierarchy.

		:return: Number of failed assertions in all test cases.
		"""
		raise NotImplementedError()
		# return self._assertionCount - (self._warningCount + self._errorCount + self._fatalCount)

	@readonly
	def PassedAssertionCount(self) -> int:
		"""
		Read-only property returning the number of all passed assertions in all test cases in the test entity hierarchy.

		:return: Number of passed assertions in all test cases.
		"""
		raise NotImplementedError()
		# return self._assertionCount - (self._warningCount + self._errorCount + self._fatalCount)

	@readonly
	def Tests(self) -> int:
		return self._tests

	@readonly
	def Inconsistent(self) -> int:
		"""
		Read-only property returning the number of inconsistent tests in the test suite hierarchy.

		:return: Number of inconsistent tests.
		"""
		return self._inconsistent

	@readonly
	def Excluded(self) -> int:
		"""
		Read-only property returning the number of excluded tests in the test suite hierarchy.

		:return: Number of excluded tests.
		"""
		return self._excluded

	@readonly
	def Skipped(self) -> int:
		"""
		Read-only property returning the number of skipped tests in the test suite hierarchy.

		:return: Number of skipped tests.
		"""
		return self._skipped

	@readonly
	def Errored(self) -> int:
		"""
		Read-only property returning the number of tests with errors in the test suite hierarchy.

		:return: Number of errored tests.
		"""
		return self._errored

	@readonly
	def Weak(self) -> int:
		"""
		Read-only property returning the number of weak tests in the test suite hierarchy.

		:return: Number of weak tests.
		"""
		return self._weak

	@readonly
	def Failed(self) -> int:
		"""
		Read-only property returning the number of failed tests in the test suite hierarchy.

		:return: Number of failed tests.
		"""
		return self._failed

	@readonly
	def Passed(self) -> int:
		"""
		Read-only property returning the number of passed tests in the test suite hierarchy.

		:return: Number of passed tests.
		"""
		return self._passed

	@readonly
	def WarningCount(self) -> int:
		raise NotImplementedError()
		# return self._warningCount

	@readonly
	def ErrorCount(self) -> int:
		raise NotImplementedError()
		# return self._errorCount

	@readonly
	def FatalCount(self) -> int:
		raise NotImplementedError()
		# return self._fatalCount

	def Aggregate(self, strict: bool = True) -> TestsuiteAggregateReturnType:
		tests = 0
		inconsistent = 0
		excluded = 0
		skipped = 0
		errored = 0
		weak = 0
		failed = 0
		passed = 0

		warningCount = 0
		errorCount = 0
		fatalCount = 0

		totalDuration = timedelta()

		for testsuite in self._testsuites.values():
			t, i, ex, s, e, w, f, p, wc, ec, fc, td = testsuite.Aggregate(strict)
			tests += t
			inconsistent += i
			excluded += ex
			skipped += s
			errored += e
			weak += w
			failed += f
			passed += p

			warningCount += wc
			errorCount += ec
			fatalCount += fc

			totalDuration += td

		return tests, inconsistent, excluded, skipped, errored, weak, failed, passed, warningCount, errorCount, fatalCount, totalDuration

	def AddTestsuite(self, testsuite: TestsuiteType) -> None:
		"""
		Add a test suite to the list of test suites.

		:param testsuite:   The test suite to add.
		:raises ValueError: If parameter 'testsuite' is None.
		:raises TypeError:  If parameter 'testsuite' is not a Testsuite.
		:raises AlreadyInHierarchyException: If parameter 'testsuite' is already part of a test entity hierarchy.
		:raises DuplicateTestcaseException:  If parameter 'testsuite' is already listed (by name) in the list of test suites.
		"""
		if testsuite is None:
			raise ValueError("Parameter 'testsuite' is None.")
		elif not isinstance(testsuite, Testsuite):
			ex = TypeError(f"Parameter 'testsuite' is not of type 'Testsuite'.")
			if version_info >= (3, 11):  # pragma: no cover
				ex.add_note(f"Got type '{getFullyQualifiedName(testsuite)}'.")
			raise ex

		if testsuite._parent is not None:
			raise AlreadyInHierarchyException(f"Testsuite '{testsuite._name}' is already part of a testsuite hierarchy.")

		if testsuite._name in self._testsuites:
			raise DuplicateTestsuiteException(f"Testsuite already contains a testsuite with same name '{testsuite._name}'.")

		testsuite._parent = self
		self._testsuites[testsuite._name] = testsuite

	def AddTestsuites(self, testsuites: Iterable[TestsuiteType]) -> None:
		"""
		Add a list of test suites to the list of test suites.

		:param testsuites:  List of test suites to add.
		:raises ValueError: If parameter 'testsuites' is None.
		:raises TypeError:  If parameter 'testsuites' is not iterable.
		"""
		if testsuites is None:
			raise ValueError("Parameter 'testsuites' is None.")
		elif not isinstance(testsuites, Iterable):
			ex = TypeError(f"Parameter 'testsuites' is not iterable.")
			if version_info >= (3, 11):  # pragma: no cover
				ex.add_note(f"Got type '{getFullyQualifiedName(testsuites)}'.")
			raise ex

		for testsuite in testsuites:
			self.AddTestsuite(testsuite)

	@abstractmethod
	def Iterate(self, scheme: IterationScheme = IterationScheme.Default) -> Generator[Union[TestsuiteType, Testcase], None, None]:
		pass

	def IterateTestsuites(self, scheme: IterationScheme = IterationScheme.TestsuiteDefault) -> Generator[TestsuiteType, None, None]:
		return self.Iterate(scheme)

	def IterateTestcases(self, scheme: IterationScheme = IterationScheme.TestcaseDefault) -> Generator[Testcase, None, None]:
		return self.Iterate(scheme)

	def ToTree(self) -> Node:
		rootNode = Node(value=self._name)

		def convertTestcase(testcase: Testcase, parentNode: Node) -> None:
			_ = Node(value=testcase._name, parent=parentNode)

		def convertTestsuite(testsuite: Testsuite, parentNode: Node) -> None:
			testsuiteNode = Node(value=testsuite._name, parent=parentNode)

			for ts in testsuite._testsuites.values():
				convertTestsuite(ts, testsuiteNode)

			for tc in testsuite._testcases.values():
				convertTestcase(tc, testsuiteNode)

		for testsuite in self._testsuites.values():
			convertTestsuite(testsuite, rootNode)

		return rootNode


@export
class Testsuite(TestsuiteBase[TestsuiteType]):
	"""
	A testsuite is a mid-level element in the test entity hierarchy representing a group of tests.

	Test suites contain test cases and optionally other test suites. Test suites can be grouped by test suites to form a
	hierarchy of test entities. The root of the hierarchy is a test summary.
	"""

	_testcases: Dict[str, "Testcase"]

	def __init__(
		self,
		name: str,
		kind: TestsuiteKind = TestsuiteKind.Logical,
		startTime: Nullable[datetime] = None,
		setupDuration: Nullable[timedelta] = None,
		testDuration: Nullable[timedelta] = None,
		teardownDuration: Nullable[timedelta] = None,
		totalDuration:  Nullable[timedelta] = None,
		status: TestsuiteStatus = TestsuiteStatus.Unknown,
		warningCount: int = 0,
		errorCount: int = 0,
		fatalCount: int = 0,
		testsuites: Nullable[Iterable[TestsuiteType]] = None,
		testcases: Nullable[Iterable["Testcase"]] = None,
		keyValuePairs: Nullable[Mapping[str, Any]] = None,
		parent: Nullable[TestsuiteType] = None
	):
		"""
		Initializes the fields of a test suite.

		:param name:               Name of the test suite.
		:param kind:               Kind of the test suite.
		:param startTime:          Time when the test suite was started.
		:param setupDuration:      Duration it took to set up the test suite.
		:param testDuration:       Duration of all tests listed in the test suite.
		:param teardownDuration:   Duration it took to tear down the test suite.
		:param totalDuration:      Total duration of the entity's execution (setup + test + teardown)
		:param status:             Overall status of the test suite.
		:param warningCount:       Count of encountered warnings incl. warnings from sub-elements.
		:param errorCount:         Count of encountered errors incl. errors from sub-elements.
		:param fatalCount:         Count of encountered fatal errors incl. fatal errors from sub-elements.
		:param testsuites:         List of test suites to initialize the test suite with.
		:param testcases:          List of test cases to initialize the test suite with.
		:param keyValuePairs:      Mapping of key-value pairs to initialize the test suite with.
		:param parent:             Reference to the parent test entity.
		:raises TypeError:         If parameter 'testcases' is not iterable.
		:raises TypeError:         If element in parameter 'testcases' is not a Testcase.
		:raises AlreadyInHierarchyException: If a test case in parameter 'testcases' is already part of a test entity hierarchy.
		:raises DuplicateTestcaseException:  If a test case in parameter 'testcases' is already listed (by name) in the list of test cases.
		"""
		super().__init__(
			name,
			kind,
			startTime,
			setupDuration,
			testDuration,
			teardownDuration,
			totalDuration,
			status,
			warningCount,
			errorCount,
			fatalCount,
			testsuites,
			keyValuePairs,
			parent
		)

		# self._testDuration = testDuration

		self._testcases = {}
		if testcases is not None:
			if not isinstance(testcases, Iterable):
				ex = TypeError(f"Parameter 'testcases' is not iterable.")
				if version_info >= (3, 11):  # pragma: no cover
					ex.add_note(f"Got type '{getFullyQualifiedName(testcases)}'.")
				raise ex

			for testcase in testcases:
				if not isinstance(testcase, Testcase):
					ex = TypeError(f"Element of parameter 'testcases' is not of type 'Testcase'.")
					if version_info >= (3, 11):  # pragma: no cover
						ex.add_note(f"Got type '{getFullyQualifiedName(testcase)}'.")
					raise ex

				if testcase._parent is not None:
					raise AlreadyInHierarchyException(f"Testcase '{testcase._name}' is already part of a testsuite hierarchy.")

				if testcase._name in self._testcases:
					raise DuplicateTestcaseException(f"Testsuite already contains a testcase with same name '{testcase._name}'.")

				testcase._parent = self
				self._testcases[testcase._name] = testcase

	@readonly
	def Testcases(self) -> Dict[str, "Testcase"]:
		"""
		Read-only property returning a reference to the internal dictionary of test cases.

		:return: Reference to the dictionary of test cases.
		"""
		return self._testcases

	@readonly
	def TestcaseCount(self) -> int:
		"""
		Read-only property returning the number of all test cases in the test entity hierarchy.

		:return: Number of test cases.
		"""
		return super().TestcaseCount + len(self._testcases)

	@readonly
	def AssertionCount(self) -> int:
		return super().AssertionCount + sum(tc.AssertionCount for tc in self._testcases.values())

	def Copy(self) -> "Testsuite":
		return self.__class__(
			self._name,
			self._startTime,
			self._setupDuration,
			self._teardownDuration,
			self._totalDuration,
			self._status,
			self._warningCount,
			self._errorCount,
			self._fatalCount
		)

	def Aggregate(self, strict: bool = True) -> TestsuiteAggregateReturnType:
		tests, inconsistent, excluded, skipped, errored, weak, failed, passed, warningCount, errorCount, fatalCount, totalDuration = super().Aggregate()

		for testcase in self._testcases.values():
			wc, ec, fc, td = testcase.Aggregate(strict)

			tests += 1

			warningCount += wc
			errorCount +=   ec
			fatalCount +=   fc

			totalDuration += td

			status = testcase._status
			if status is TestcaseStatus.Unknown:
				raise UnittestException(f"Found testcase '{testcase._name}' with state 'Unknown'.")
			elif TestcaseStatus.Inconsistent in status:
				inconsistent += 1
			elif status is TestcaseStatus.Excluded:
				excluded += 1
			elif status is TestcaseStatus.Skipped:
				skipped += 1
			elif status is TestcaseStatus.Errored:
				errored += 1
			elif status is TestcaseStatus.Weak:
				weak += 1
			elif status is TestcaseStatus.Passed:
				passed += 1
			elif status is TestcaseStatus.Failed:
				failed += 1
			elif status & TestcaseStatus.Mask is not TestcaseStatus.Unknown:
				raise UnittestException(f"Found testcase '{testcase._name}' with unsupported state '{status}'.")
			else:
				raise UnittestException(f"Internal error for testcase '{testcase._name}', field '_status' is '{status}'.")

		self._tests = tests
		self._inconsistent = inconsistent
		self._excluded = excluded
		self._skipped = skipped
		self._errored = errored
		self._weak = weak
		self._failed = failed
		self._passed = passed

		self._warningCount = warningCount
		self._errorCount = errorCount
		self._fatalCount = fatalCount

		if self._totalDuration is None:
			self._totalDuration = totalDuration

		if errored > 0:
			self._status = TestsuiteStatus.Errored
		elif failed > 0:
			self._status = TestsuiteStatus.Failed
		elif tests == 0:
			self._status = TestsuiteStatus.Empty
		elif tests - skipped == passed:
			self._status = TestsuiteStatus.Passed
		elif tests == skipped:
			self._status = TestsuiteStatus.Skipped
		else:
			self._status = TestsuiteStatus.Unknown

		return tests, inconsistent, excluded, skipped, errored, weak, failed, passed, warningCount, errorCount, fatalCount, totalDuration

	def AddTestcase(self, testcase: "Testcase") -> None:
		"""
		Add a test case to the list of test cases.

		:param testcase:    The test case to add.
		:raises ValueError: If parameter 'testcase' is None.
		:raises TypeError:  If parameter 'testcase' is not a Testcase.
		:raises AlreadyInHierarchyException: If parameter 'testcase' is already part of a test entity hierarchy.
		:raises DuplicateTestcaseException:  If parameter 'testcase' is already listed (by name) in the list of test cases.
		"""
		if testcase is None:
			raise ValueError("Parameter 'testcase' is None.")
		elif not isinstance(testcase, Testcase):
			ex = TypeError(f"Parameter 'testcase' is not of type 'Testcase'.")
			if version_info >= (3, 11):  # pragma: no cover
				ex.add_note(f"Got type '{getFullyQualifiedName(testcase)}'.")
			raise ex

		if testcase._parent is not None:
			raise ValueError(f"Testcase '{testcase._name}' is already part of a testsuite hierarchy.")

		if testcase._name in self._testcases:
			raise DuplicateTestcaseException(f"Testsuite already contains a testcase with same name '{testcase._name}'.")

		testcase._parent = self
		self._testcases[testcase._name] = testcase

	def AddTestcases(self, testcases: Iterable["Testcase"]) -> None:
		"""
		Add a list of test cases to the list of test cases.

		:param testcases:   List of test cases to add.
		:raises ValueError: If parameter 'testcases' is None.
		:raises TypeError:  If parameter 'testcases' is not iterable.
		"""
		if testcases is None:
			raise ValueError("Parameter 'testcases' is None.")
		elif not isinstance(testcases, Iterable):
			ex = TypeError(f"Parameter 'testcases' is not iterable.")
			if version_info >= (3, 11):  # pragma: no cover
				ex.add_note(f"Got type '{getFullyQualifiedName(testcases)}'.")
			raise ex

		for testcase in testcases:
			self.AddTestcase(testcase)

	def Iterate(self, scheme: IterationScheme = IterationScheme.Default) -> Generator[Union[TestsuiteType, Testcase], None, None]:
		assert IterationScheme.PreOrder | IterationScheme.PostOrder not in scheme

		if IterationScheme.PreOrder in scheme:
			if IterationScheme.IncludeSelf | IterationScheme.IncludeTestsuites in scheme:
				yield self

			if IterationScheme.IncludeTestcases in scheme:
				for testcase in self._testcases.values():
					yield testcase

		for testsuite in self._testsuites.values():
			yield from testsuite.Iterate(scheme | IterationScheme.IncludeSelf)

		if IterationScheme.PostOrder in scheme:
			if IterationScheme.IncludeTestcases in scheme:
				for testcase in self._testcases.values():
					yield testcase

			if IterationScheme.IncludeSelf | IterationScheme.IncludeTestsuites in scheme:
				yield self

	def __str__(self) -> str:
		return (
			f"<Testsuite {self._name}: {self._status.name} -"
			# f" assert/pass/fail:{self._assertionCount}/{self._passedAssertionCount}/{self._failedAssertionCount} -"
			f" warn/error/fatal:{self._warningCount}/{self._errorCount}/{self._fatalCount}>"
		)


@export
class TestsuiteSummary(TestsuiteBase[TestsuiteType]):
	"""
	A testsuite summary is the root element in the test entity hierarchy representing a summary of all test suites and cases.

	The testsuite summary contains test suites, which in turn can contain test suites and test cases.
	"""

	def __init__(
		self,
		name: str,
		startTime: Nullable[datetime] = None,
		setupDuration: Nullable[timedelta] = None,
		testDuration: Nullable[timedelta] = None,
		teardownDuration: Nullable[timedelta] = None,
		totalDuration:  Nullable[timedelta] = None,
		status: TestsuiteStatus = TestsuiteStatus.Unknown,
		warningCount: int = 0,
		errorCount: int = 0,
		fatalCount: int = 0,
		testsuites: Nullable[Iterable[TestsuiteType]] = None,
		keyValuePairs: Nullable[Mapping[str, Any]] = None,
		parent: Nullable[TestsuiteType] = None
	):
		"""
		Initializes the fields of a test summary.

		:param name:               Name of the test summary.
		:param startTime:          Time when the test summary was started.
		:param setupDuration:      Duration it took to set up the test summary.
		:param testDuration:       Duration of all tests listed in the test summary.
		:param teardownDuration:   Duration it took to tear down the test summary.
		:param totalDuration:      Total duration of the entity's execution (setup + test + teardown)
		:param status:             Overall status of the test summary.
		:param warningCount:       Count of encountered warnings incl. warnings from sub-elements.
		:param errorCount:         Count of encountered errors incl. errors from sub-elements.
		:param fatalCount:         Count of encountered fatal errors incl. fatal errors from sub-elements.
		:param testsuites:         List of test suites to initialize the test summary with.
		:param keyValuePairs:      Mapping of key-value pairs to initialize the test summary with.
		:param parent:             Reference to the parent test summary.
		"""
		super().__init__(
			name,
			TestsuiteKind.Root,
			startTime,
			setupDuration,
			testDuration,
			teardownDuration,
			totalDuration,
			status,
			warningCount,
			errorCount,
			fatalCount,
			testsuites,
			keyValuePairs,
			parent
		)

	def Aggregate(self, strict: bool = True) -> TestsuiteAggregateReturnType:
		tests, inconsistent, excluded, skipped, errored, weak, failed, passed, warningCount, errorCount, fatalCount, totalDuration = super().Aggregate(strict)

		self._tests = tests
		self._inconsistent = inconsistent
		self._excluded = excluded
		self._skipped = skipped
		self._errored = errored
		self._weak = weak
		self._failed = failed
		self._passed = passed

		self._warningCount = warningCount
		self._errorCount = errorCount
		self._fatalCount = fatalCount

		if self._totalDuration is None:
			self._totalDuration = totalDuration

		if errored > 0:
			self._status = TestsuiteStatus.Errored
		elif failed > 0:
			self._status = TestsuiteStatus.Failed
		elif tests == 0:
			self._status = TestsuiteStatus.Empty
		elif tests - skipped == passed:
			self._status = TestsuiteStatus.Passed
		elif tests == skipped:
			self._status = TestsuiteStatus.Skipped
		elif tests == excluded:
			self._status = TestsuiteStatus.Excluded
		else:
			self._status = TestsuiteStatus.Unknown

		return tests, inconsistent, excluded, skipped, errored, weak, failed, passed, warningCount, errorCount, fatalCount, totalDuration

	def Iterate(self, scheme: IterationScheme = IterationScheme.Default) -> Generator[Union[TestsuiteType, Testcase], None, None]:
		if IterationScheme.IncludeSelf | IterationScheme.IncludeTestsuites | IterationScheme.PreOrder in scheme:
			yield self

		for testsuite in self._testsuites.values():
			yield from testsuite.IterateTestsuites(scheme | IterationScheme.IncludeSelf)

		if IterationScheme.IncludeSelf | IterationScheme.IncludeTestsuites | IterationScheme.PostOrder in scheme:
			yield self

	def __str__(self) -> str:
		return (
			f"<TestsuiteSummary {self._name}: {self._status.name} -"
			# f" assert/pass/fail:{self._assertionCount}/{self._passedAssertionCount}/{self._failedAssertionCount} -"
			f" warn/error/fatal:{self._warningCount}/{self._errorCount}/{self._fatalCount}>"
		)


@export
class Document(metaclass=ExtendedType, mixin=True):
	"""A mixin-class representing a unit test summary document (file)."""

	_path:             Path

	_analysisDuration: float  #: TODO: replace by Timer; should be timedelta?
	_modelConversion:  float  #: TODO: replace by Timer; should be timedelta?

	def __init__(self, reportFile: Path, analyzeAndConvert: bool = False):
		self._path = reportFile

		self._analysisDuration = -1.0
		self._modelConversion = -1.0

		if analyzeAndConvert:
			self.Analyze()
			self.Convert()

	@readonly
	def Path(self) -> Path:
		"""
		Read-only property returning the path to the file of this document.

		:return: The document's path to the file.
		"""
		return self._path

	@readonly
	def AnalysisDuration(self) -> timedelta:
		"""
		Read-only property returning analysis duration.

		.. note::

		   This includes usually the duration to validate and parse the file format, but it excludes the time to convert the
		   content to the test entity hierarchy.

		:return: Duration to analyze the document.
		"""
		return timedelta(seconds=self._analysisDuration)

	@readonly
	def ModelConversionDuration(self) -> timedelta:
		"""
		Read-only property returning conversion duration.

		.. note::

		   This includes usually the duration to convert the document's content to the test entity hierarchy. It might also
		   include the duration to (re-)aggregate all states and statistics in the hierarchy.

		:return: Duration to convert the document.
		"""
		return timedelta(seconds=self._modelConversion)

	@abstractmethod
	def Analyze(self) -> None:
		"""Analyze and validate the document's content."""

	# @abstractmethod
	# def Write(self, path: Nullable[Path] = None, overwrite: bool = False):
	# 	pass

	@abstractmethod
	def Convert(self):
		"""Convert the document's content to an instance of the test entity hierarchy."""


@export
class Merged(metaclass=ExtendedType, mixin=True):
	"""A mixin-class representing a merged test entity."""

	_mergedCount: int

	def __init__(self, mergedCount: int = 1):
		self._mergedCount = mergedCount

	@readonly
	def MergedCount(self) -> int:
		return self._mergedCount


@export
class Combined(metaclass=ExtendedType, mixin=True):
	_combinedCount: int

	def __init__(self, combinedCound: int = 1):
		self._combinedCount = combinedCound

	@readonly
	def CombinedCount(self) -> int:
		return self._combinedCount


@export
class MergedTestcase(Testcase, Merged):
	_mergedTestcases: List[Testcase]

	def __init__(
		self,
		testcase: Testcase,
		parent: Nullable["Testsuite"] = None
	):
		if testcase is None:
			raise ValueError(f"Parameter 'testcase' is None.")

		super().__init__(
			testcase._name,
			testcase._startTime,
			testcase._setupDuration, testcase._testDuration, testcase._teardownDuration, testcase._totalDuration,
			TestcaseStatus.Unknown,
			testcase._assertionCount, testcase._failedAssertionCount, testcase._passedAssertionCount,
			testcase._warningCount, testcase._errorCount, testcase._fatalCount,
			parent
		)
		Merged.__init__(self)

		self._mergedTestcases = [testcase]

	@readonly
	def Status(self) -> TestcaseStatus:
		if self._status is TestcaseStatus.Unknown:
			status = self._mergedTestcases[0]._status
			for mtc in self._mergedTestcases[1:]:
				status @= mtc._status

			self._status = status

		return self._status

	@readonly
	def SummedAssertionCount(self) -> int:
		return sum(tc._assertionCount for tc in self._mergedTestcases)

	@readonly
	def SummedPassedAssertionCount(self) -> int:
		return sum(tc._passedAssertionCount for tc in self._mergedTestcases)

	@readonly
	def SummedFailedAssertionCount(self) -> int:
		return sum(tc._failedAssertionCount for tc in self._mergedTestcases)

	def Aggregate(self, strict: bool = True) -> TestcaseAggregateReturnType:
		firstMTC = self._mergedTestcases[0]

		status =        firstMTC._status
		warningCount =  firstMTC._warningCount
		errorCount =    firstMTC._errorCount
		fatalCount =    firstMTC._fatalCount
		totalDuration = firstMTC._totalDuration

		for mtc in self._mergedTestcases[1:]:
			status @=       mtc._status
			warningCount += mtc._warningCount
			errorCount +=   mtc._errorCount
			fatalCount +=   mtc._fatalCount

		self._status = status

		return warningCount, errorCount, fatalCount, totalDuration

	def Merge(self, tc: Testcase) -> None:
		self._mergedCount += 1

		self._mergedTestcases.append(tc)

		self._warningCount += tc._warningCount
		self._errorCount += tc._errorCount
		self._fatalCount += tc._fatalCount

	def ToTestcase(self) -> Testcase:
		return Testcase(
			self._name,
			self._startTime,
			self._setupDuration,
			self._testDuration,
			self._teardownDuration,
			self._totalDuration,
			self._status,
			self._assertionCount,
			self._failedAssertionCount,
			self._passedAssertionCount,
			self._warningCount,
			self._errorCount,
			self._fatalCount
		)


@export
class MergedTestsuite(Testsuite, Merged):
	def __init__(
		self,
		testsuite: Testsuite,
		addTestsuites: bool = False,
		addTestcases: bool = False,
		parent: Nullable["Testsuite"] = None
	):
		if testsuite is None:
			raise ValueError(f"Parameter 'testsuite' is None.")

		super().__init__(
			testsuite._name,
			testsuite._kind,
			testsuite._startTime,
			testsuite._setupDuration, testsuite._testDuration, testsuite._teardownDuration, testsuite._totalDuration,
			TestsuiteStatus.Unknown,
			testsuite._warningCount, testsuite._errorCount, testsuite._fatalCount,
			parent
		)
		Merged.__init__(self)

		if addTestsuites:
			for ts in testsuite._testsuites.values():
				mergedTestsuite = MergedTestsuite(ts, addTestsuites, addTestcases)
				self.AddTestsuite(mergedTestsuite)

		if addTestcases:
			for tc in testsuite._testcases.values():
				mergedTestcase = MergedTestcase(tc)
				self.AddTestcase(mergedTestcase)

	def Merge(self, testsuite: Testsuite) -> None:
		self._mergedCount += 1

		for ts in testsuite._testsuites.values():
			if ts._name in self._testsuites:
				self._testsuites[ts._name].Merge(ts)
			else:
				mergedTestsuite = MergedTestsuite(ts, addTestsuites=True, addTestcases=True)
				self.AddTestsuite(mergedTestsuite)

		for tc in testsuite._testcases.values():
			if tc._name in self._testcases:
				self._testcases[tc._name].Merge(tc)
			else:
				mergedTestcase = MergedTestcase(tc)
				self.AddTestcase(mergedTestcase)

	def ToTestsuite(self) -> Testsuite:
		testsuite = Testsuite(
			self._name,
			self._kind,
			self._startTime,
			self._setupDuration,
			self._testDuration,
			self._teardownDuration,
			self._totalDuration,
			self._status,
			self._warningCount,
			self._errorCount,
			self._fatalCount,
			testsuites=(ts.ToTestsuite() for ts in self._testsuites.values()),
			testcases=(tc.ToTestcase() for tc in self._testcases.values())
		)

		testsuite._tests = self._tests
		testsuite._excluded = self._excluded
		testsuite._inconsistent = self._inconsistent
		testsuite._skipped = self._skipped
		testsuite._errored = self._errored
		testsuite._weak = self._weak
		testsuite._failed = self._failed
		testsuite._passed = self._passed

		return testsuite


@export
class MergedTestsuiteSummary(TestsuiteSummary, Merged):
	_mergedFiles: Dict[Path, TestsuiteSummary]

	def __init__(self, name: str) -> None:
		super().__init__(name)
		Merged.__init__(self, mergedCount=0)

		self._mergedFiles = {}

	def Merge(self, testsuiteSummary: TestsuiteSummary) -> None:
		# if summary.File in self._mergedFiles:
		# 	raise

		# FIXME: a summary is not necessarily a file
		self._mergedCount += 1
		self._mergedFiles[testsuiteSummary._name] = testsuiteSummary

		for testsuite in testsuiteSummary._testsuites.values():
			if testsuite._name in self._testsuites:
				self._testsuites[testsuite._name].Merge(testsuite)
			else:
				mergedTestsuite = MergedTestsuite(testsuite, addTestsuites=True, addTestcases=True)
				self.AddTestsuite(mergedTestsuite)

	def ToTestsuiteSummary(self) -> TestsuiteSummary:
		testsuiteSummary = TestsuiteSummary(
			self._name,
			self._startTime,
			self._setupDuration,
			self._testDuration,
			self._teardownDuration,
			self._totalDuration,
			self._status,
			self._warningCount,
			self._errorCount,
			self._fatalCount,
			testsuites=(ts.ToTestsuite() for ts in self._testsuites.values())
		)

		testsuiteSummary._tests = self._tests
		testsuiteSummary._excluded = self._excluded
		testsuiteSummary._inconsistent = self._inconsistent
		testsuiteSummary._skipped = self._skipped
		testsuiteSummary._errored = self._errored
		testsuiteSummary._weak = self._weak
		testsuiteSummary._failed = self._failed
		testsuiteSummary._passed = self._passed

		return testsuiteSummary
