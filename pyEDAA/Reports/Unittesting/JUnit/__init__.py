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
The pyEDAA.Reports.Unittesting.JUnit package implements a hierarchy of test entities for the JUnit unit testing summary
file format (XML format). This test entity hierarchy is not derived from :class:`pyEDAA.Reports.Unittesting`, because it
doesn't match the unified data model. Nonetheless, both data models can be converted to each other. In addition, derived
data models are provided for the many dialects of that XML file format. See the list modules in this package for the
implemented dialects.

The test entity hierarchy consists of test cases, test classes, test suites and a test summary. Test cases are the leaf
elements in the hierarchy and represent an individual test run. Next, test classes group test cases, because the
original Ant + JUnit format groups test cases (Java methods) in a Java class. Next, test suites are used to group
multiple test classes. Finally, the root element is a test summary. When such a summary is stored in a file format like
Ant + JUnit4 XML, a file format specific document is derived from a summary class.

**Data Model**

.. mermaid::

	 graph TD;
		 doc[Document]
		 sum[Summary]
		 ts1[Testsuite]
		 ts11[Testsuite]
		 ts2[Testsuite]

		 tc111[Testclass]
		 tc112[Testclass]
		 tc23[Testclass]

		 tc1111[Testcase]
		 tc1112[Testcase]
		 tc1113[Testcase]
		 tc1121[Testcase]
		 tc1122[Testcase]
		 tc231[Testcase]
		 tc232[Testcase]
		 tc233[Testcase]

		 doc:::root -.-> sum:::summary
		 sum --> ts1:::suite
		 sum ---> ts2:::suite
		 ts1 --> ts11:::suite

		 ts11 --> tc111:::cls
		 ts11 --> tc112:::cls
		 ts2  --> tc23:::cls

		 tc111 --> tc1111:::case
		 tc111 --> tc1112:::case
		 tc111 --> tc1113:::case
		 tc112 --> tc1121:::case
		 tc112 --> tc1122:::case
		 tc23 --> tc231:::case
		 tc23 --> tc232:::case
		 tc23 --> tc233:::case

		 classDef root fill:#4dc3ff
		 classDef summary fill:#80d4ff
		 classDef suite fill:#b3e6ff
		 classDef cls fill:#ff9966
		 classDef case fill:#eeccff
"""
from datetime        import datetime, timedelta
from enum            import Flag
from pathlib         import Path
from sys             import version_info
from time            import perf_counter_ns
from typing          import Optional as Nullable, Iterable, Dict, Any, Generator, Tuple, Union, TypeVar, Type, ClassVar

from lxml.etree                 import XMLParser, parse, XMLSchema, ElementTree, Element, SubElement, tostring
from lxml.etree                 import XMLSyntaxError, _ElementTree, _Element, _Comment, XMLSchemaParseError
from pyTooling.Common           import getFullyQualifiedName, getResourceFile
from pyTooling.Decorators       import export, readonly
from pyTooling.Exceptions       import ToolingException
from pyTooling.MetaClasses      import ExtendedType, mustoverride, abstractmethod
from pyTooling.Tree             import Node

from pyEDAA.Reports             import Resources
from pyEDAA.Reports.Unittesting import UnittestException, AlreadyInHierarchyException, DuplicateTestsuiteException, DuplicateTestcaseException
from pyEDAA.Reports.Unittesting import TestcaseStatus, TestsuiteStatus, TestsuiteKind, IterationScheme
from pyEDAA.Reports.Unittesting import Document as ut_Document, TestsuiteSummary as ut_TestsuiteSummary
from pyEDAA.Reports.Unittesting import Testsuite as ut_Testsuite, Testcase as ut_Testcase


@export
class JUnitException:
	"""An exception-mixin for JUnit format specific exceptions."""


@export
class UnittestException(UnittestException, JUnitException):
	pass


@export
class AlreadyInHierarchyException(AlreadyInHierarchyException, JUnitException):
	"""
	A unit test exception raised if the element is already part of a hierarchy.

	This exception is caused by an inconsistent data model. Elements added to the hierarchy should be part of the same
	hierarchy should occur only once in the hierarchy.

	.. hint::

	   This is usually caused by a non-None parent reference.
	"""


@export
class DuplicateTestsuiteException(DuplicateTestsuiteException, JUnitException):
	"""
	A unit test exception raised on duplicate test suites (by name).

	This exception is raised, if a child test suite with same name already exist in the test suite.

	.. hint::

	   Test suite names need to be unique per parent element (test suite or test summary).
	"""


@export
class DuplicateTestcaseException(DuplicateTestcaseException, JUnitException):
	"""
	A unit test exception raised on duplicate test cases (by name).

	This exception is raised, if a child test case with same name already exist in the test suite.

	.. hint::

	   Test case names need to be unique per parent element (test suite).
	"""


@export
class JUnitReaderMode(Flag):
	Default = 0                                         #: Default behavior
	DecoupleTestsuiteHierarchyAndTestcaseClassName = 1  #: Undocumented


TestsuiteType = TypeVar("TestsuiteType", bound="Testsuite")
TestcaseAggregateReturnType = Tuple[int, int, int]
TestsuiteAggregateReturnType = Tuple[int, int, int, int, int]


@export
class Base(metaclass=ExtendedType, slots=True):
	"""
	Base-class for all test entities (test cases, test classes, test suites, ...).

	It provides a reference to the parent test entity, so bidirectional referencing can be used in the test entity
	hierarchy.

	Every test entity has a name to identity it. It's also used in the parent's child element dictionaries to identify the
	child. |br|
	E.g. it's used as a test case name in the dictionary of test cases in a test class.
	"""

	_parent:         Nullable["Testsuite"]
	_name:           str

	def __init__(self, name: str, parent: Nullable["Testsuite"] = None):
		"""
		Initializes the fields of the base-class.

		:param name:        Name of the test entity.
		:param parent:      Reference to the parent test entity.
		:raises ValueError: If parameter 'name' is None.
		:raises TypeError:  If parameter 'name' is not a string.
		:raises ValueError: If parameter 'name' is empty.
		"""
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

	@readonly
	def Parent(self) -> Nullable["Testsuite"]:
		"""
		Read-only property returning the reference to the parent test entity.

		:return: Reference to the parent entity.
		"""
		return self._parent

	# QUESTION: allow Parent as setter?

	@readonly
	def Name(self) -> str:
		"""
		Read-only property returning the test entity's name.

		:return:
		"""
		return self._name


@export
class BaseWithProperties(Base):
	"""
	Base-class for all test entities supporting properties (test cases, test suites, ...).

	Every test entity has fields for the test duration and number of executed assertions.

	Every test entity offers an internal dictionary for properties.
	"""

	_duration:       Nullable[timedelta]
	_assertionCount: Nullable[int]
	_properties:     Dict[str, Any]

	def __init__(
		self,
		name: str,
		duration: Nullable[timedelta] = None,
		assertionCount: Nullable[int] = None,
		parent: Nullable["Testsuite"] = None
	):
		"""
		Initializes the fields of the base-class.

		:param name:           Name of the test entity.
		:param duration:       Duration of the entity's execution.
		:param assertionCount: Number of assertions within the test.
		:param parent:         Reference to the parent test entity.
		:raises TypeError:     If parameter 'duration' is not a timedelta.
		:raises TypeError:     If parameter 'assertionCount' is not an integer.
		"""
		super().__init__(name, parent)

		if duration is not None and not isinstance(duration, timedelta):
			ex = TypeError(f"Parameter 'duration' is not of type 'timedelta'.")
			if version_info >= (3, 11):  # pragma: no cover
				ex.add_note(f"Got type '{getFullyQualifiedName(duration)}'.")
			raise ex

		if assertionCount is not None and not isinstance(assertionCount, int):
			ex = TypeError(f"Parameter 'assertionCount' is not of type 'int'.")
			if version_info >= (3, 11):  # pragma: no cover
				ex.add_note(f"Got type '{getFullyQualifiedName(assertionCount)}'.")
			raise ex

		self._duration = duration
		self._assertionCount = assertionCount

		self._properties = {}

	@readonly
	def Duration(self) -> timedelta:
		"""
		Read-only property returning the duration of a test entity run.

		.. note::

		   The JUnit format doesn't distinguish setup, run and teardown durations.

		:return: Duration of the entity's execution.
		"""
		return self._duration

	@readonly
	@abstractmethod
	def AssertionCount(self) -> int:
		"""
		Read-only property returning the number of assertions (checks) in a test case.

		.. note::

		   The JUnit format doesn't distinguish passed and failed assertions.

		:return: Number of assertions.
		"""

	def __len__(self) -> int:
		"""
		Returns the number of annotated properties.

		Syntax: :pycode:`length = len(obj)`

		:return: Number of annotated properties.
		"""
		return len(self._properties)

	def __getitem__(self, name: str) -> Any:
		"""
		Access a property by name.

		Syntax: :pycode:`value = obj[name]`

		:param name: Name if the property.
		:return:     Value of the accessed property.
		"""
		return self._properties[name]

	def __setitem__(self, name: str, value: Any) -> None:
		"""
		Set the value of a property by name.

		If the property doesn't exist yet, it's created.

		Syntax: :pycode:`obj[name] = value`

		:param name:  Name of the property.
		:param value: Value of the property.
		"""
		self._properties[name] = value

	def __delitem__(self, name: str) -> None:
		"""
		Delete a property by name.

		Syntax: :pycode:`del obj[name]`

		:param name: Name if the property.
		"""
		del self._properties[name]

	def __contains__(self, name: str) -> bool:
		"""
		Returns True, if a property was annotated by this name.

		Syntax: :pycode:`name in obj`

		:param name: Name of the property.
		:return:     True, if the property was annotated.
		"""
		return name in self._properties

	def __iter__(self) -> Generator[Tuple[str, Any], None, None]:
		"""
		Iterate all annotated properties.

		Syntax: :pycode:`for name, value in obj:`

		:return: A generator of property tuples (name, value).
		"""
		yield from self._properties.items()


@export
class Testcase(BaseWithProperties):
	"""
	A testcase is the leaf-entity in the test entity hierarchy representing an individual test run.

	Test cases are grouped by test classes in the test entity hierarchy. These are again grouped by test suites. The root
	of the hierarchy is a test summary.

	Every test case has an overall status like unknown, skipped, failed or passed.
	"""

	_status:         TestcaseStatus

	def __init__(
		self,
		name: str,
		duration:  Nullable[timedelta] = None,
		status: TestcaseStatus = TestcaseStatus.Unknown,
		assertionCount: Nullable[int] = None,
		parent: Nullable["Testclass"] = None
	):
		"""
		Initializes the fields of a test case.

		:param name:           Name of the test entity.
		:param duration:       Duration of the entity's execution.
		:param status:         Status of the test case.
		:param assertionCount: Number of assertions within the test.
		:param parent:         Reference to the parent test class.
		:raises TypeError:     If parameter 'parent' is not a Testsuite.
		:raises ValueError:    If parameter 'assertionCount' is not consistent.
		"""
		if parent is not None:
			if not isinstance(parent, Testclass):
				ex = TypeError(f"Parameter 'parent' is not of type 'Testclass'.")
				if version_info >= (3, 11):  # pragma: no cover
					ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
				raise ex

			parent._testcases[name] = self

		super().__init__(name, duration, assertionCount, parent)

		if not isinstance(status, TestcaseStatus):
			ex = TypeError(f"Parameter 'status' is not of type 'TestcaseStatus'.")
			if version_info >= (3, 11):  # pragma: no cover
				ex.add_note(f"Got type '{getFullyQualifiedName(status)}'.")
			raise ex

		self._status = status

	@readonly
	def Classname(self) -> str:
		"""
		Read-only property returning the class name of the test case.

		:return: The test case's class name.

		.. note::

		   In the JUnit format, a test case is uniquely identified by a tuple of class name and test case name. This
		   structure has been decomposed by this data model into 2 leaf-levels in the test entity hierarchy. Thus, the class
		   name is represented by its own level and instances of test classes.
		"""
		if self._parent is None:
			raise UnittestException("Standalone Testcase instance is not linked to a Testclass.")
		return self._parent._name

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

		.. note::

		   The JUnit format doesn't distinguish passed and failed assertions.

		:return: Number of assertions.
		"""
		if self._assertionCount is None:
			return 0
		return self._assertionCount

	def Copy(self) -> "Testcase":
		return self.__class__(
			self._name,
			self._duration,
			self._status,
			self._assertionCount
		)

	def Aggregate(self) -> None:
		if self._status is TestcaseStatus.Unknown:
			if self._assertionCount is None:
				self._status = TestcaseStatus.Passed
			elif self._assertionCount == 0:
				self._status = TestcaseStatus.Weak
			else:
				self._status = TestcaseStatus.Failed

			# TODO: check for setup errors
			# TODO: check for teardown errors

	@classmethod
	def FromTestcase(cls, testcase: ut_Testcase) -> "Testcase":
		"""
		Convert a test case of the unified test entity data model to the JUnit specific data model's test case object.

		:param testcase: Test case from unified data model.
		:return:         Test case from JUnit specific data model.
		"""
		return cls(
			testcase._name,
			duration=testcase._testDuration,
			status= testcase._status,
			assertionCount=testcase._assertionCount
		)

	def ToTestcase(self) -> ut_Testcase:
		return ut_Testcase(
			self._name,
			testDuration=self._duration,
			status=self._status,
			assertionCount=self._assertionCount,
			# TODO: as only assertions are recorded by JUnit files, all are marked as passed
			passedAssertionCount=self._assertionCount
		)

	def ToTree(self) -> Node:
		node = Node(value=self._name)
		node["status"] = self._status
		node["assertionCount"] = self._assertionCount
		node["duration"] = self._duration

		return node

	def __str__(self) -> str:
		moduleName = self.__module__.split(".")[-1]
		className = self.__class__.__name__
		return (
			f"<{moduleName}{className} {self._name}: {self._status.name} - asserts:{self._assertionCount}>"
		)


@export
class TestsuiteBase(BaseWithProperties):
	"""
	Base-class for all test suites and for test summaries.

	A test suite is a mid-level grouping element in the test entity hierarchy, whereas the test summary is the root
	element in that hierarchy. While a test suite groups test classes, a test summary can only group test suites. Thus, a
	test summary contains no test classes and test cases.
	"""

	_startTime: Nullable[datetime]
	_status:    TestsuiteStatus

	_tests:     int
	_skipped:   int
	_errored:   int
	_failed:    int
	_passed:    int

	def __init__(
		self,
		name: str,
		startTime: Nullable[datetime] = None,
		duration:  Nullable[timedelta] = None,
		status: TestsuiteStatus = TestsuiteStatus.Unknown,
		parent: Nullable["Testsuite"] = None
	):
		"""
		Initializes the based-class fields of a test suite or test summary.

		:param name:       Name of the test entity.
		:param startTime:  Time when the test entity was started.
		:param duration:   Duration of the entity's execution.
		:param status:     Overall status of the test entity.
		:param parent:     Reference to the parent test entity.
		:raises TypeError: If parameter 'parent' is not a TestsuiteBase.
		"""
		if parent is not None:
			if not isinstance(parent, TestsuiteBase):
				ex = TypeError(f"Parameter 'parent' is not of type 'TestsuiteBase'.")
				if version_info >= (3, 11):  # pragma: no cover
					ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
				raise ex

			parent._testsuites[name] = self

		super().__init__(name, duration, None, parent)

		self._startTime = startTime
		self._status = status
		self._tests =        0
		self._skipped =      0
		self._errored =      0
		self._failed =       0
		self._passed =       0

	@readonly
	def StartTime(self) -> Nullable[datetime]:
		return self._startTime

	@readonly
	def Status(self) -> TestsuiteStatus:
		return self._status

	@readonly
	@mustoverride
	def TestcaseCount(self) -> int:
		pass

	@readonly
	def Tests(self) -> int:
		return self.TestcaseCount

	@readonly
	def Skipped(self) -> int:
		return self._skipped

	@readonly
	def Errored(self) -> int:
		return self._errored

	@readonly
	def Failed(self) -> int:
		return self._failed

	@readonly
	def Passed(self) -> int:
		return self._passed

	def Aggregate(self) -> TestsuiteAggregateReturnType:
		tests = 0
		skipped = 0
		errored = 0
		failed = 0
		passed = 0

		# for testsuite in self._testsuites.values():
		# 	t, s, e, w, f, p = testsuite.Aggregate()
		# 	tests += t
		# 	skipped += s
		# 	errored += e
		# 	weak += w
		# 	failed += f
		# 	passed += p

		return tests, skipped, errored, failed, passed

	@mustoverride
	def Iterate(self, scheme: IterationScheme = IterationScheme.Default) -> Generator[Union[TestsuiteType, Testcase], None, None]:
		pass


@export
class Testclass(Base):
	"""
	A test class is a low-level element in the test entity hierarchy representing a group of tests.

	Test classes contain test cases and are grouped by a test suites.
	"""

	_testcases: Dict[str, "Testcase"]

	def __init__(
		self,
		classname: str,
		testcases: Nullable[Iterable["Testcase"]] = None,
		parent: Nullable["Testsuite"] = None
	):
		"""
		Initializes the fields of the test class.

		:param classname:   Classname of the test entity.
		:param parent:      Reference to the parent test suite.
		:raises ValueError: If parameter 'classname' is None.
		:raises TypeError:  If parameter 'classname' is not a string.
		:raises ValueError: If parameter 'classname' is empty.
		"""
		if parent is not None:
			if not isinstance(parent, Testsuite):
				ex = TypeError(f"Parameter 'parent' is not of type 'Testsuite'.")
				if version_info >= (3, 11):  # pragma: no cover
					ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
				raise ex

			parent._testclasses[classname] = self

		super().__init__(classname, parent)

		self._testcases = {}
		if testcases is not None:
			for testcase in testcases:
				if testcase._parent is not None:
					raise AlreadyInHierarchyException(f"Testcase '{testcase._name}' is already part of a testsuite hierarchy.")

				if testcase._name in self._testcases:
					raise DuplicateTestcaseException(f"Class already contains a testcase with same name '{testcase._name}'.")

				testcase._parent = self
				self._testcases[testcase._name] = testcase

	@readonly
	def Classname(self) -> str:
		"""
		Read-only property returning the name of the test class.

		:return: The test class' name.
		"""
		return self._name

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
		return len(self._testcases)

	@readonly
	def AssertionCount(self) -> int:
		return sum(tc.AssertionCount for tc in self._testcases.values())

	def AddTestcase(self, testcase: "Testcase") -> None:
		if testcase._parent is not None:
			raise ValueError(f"Testcase '{testcase._name}' is already part of a testsuite hierarchy.")

		if testcase._name in self._testcases:
			raise DuplicateTestcaseException(f"Class already contains a testcase with same name '{testcase._name}'.")

		testcase._parent = self
		self._testcases[testcase._name] = testcase

	def AddTestcases(self, testcases: Iterable["Testcase"]) -> None:
		for testcase in testcases:
			self.AddTestcase(testcase)

	def ToTestsuite(self) -> ut_Testsuite:
		return ut_Testsuite(
			self._name,
			TestsuiteKind.Class,
			# startTime=self._startTime,
			# totalDuration=self._duration,
			# status=self._status,
			testcases=(tc.ToTestcase() for tc in self._testcases.values())
		)

	def ToTree(self) -> Node:
		node = Node(
			value=self._name,
			children=(tc.ToTree() for tc in self._testcases.values())
		)

		return node

	def __str__(self) -> str:
		moduleName = self.__module__.split(".")[-1]
		className = self.__class__.__name__
		return (
			f"<{moduleName}{className} {self._name}: {len(self._testcases)}>"
		)


@export
class Testsuite(TestsuiteBase):
	"""
	A testsuite is a mid-level element in the test entity hierarchy representing a logical group of tests.

	Test suites contain test classes and are grouped by a test summary, which is the root of the hierarchy.
	"""

	_hostname:    str
	_testclasses: Dict[str, "Testclass"]

	def __init__(
		self,
		name: str,
		hostname: Nullable[str] = None,
		startTime: Nullable[datetime] = None,
		duration:  Nullable[timedelta] = None,
		status: TestsuiteStatus = TestsuiteStatus.Unknown,
		testclasses: Nullable[Iterable["Testclass"]] = None,
		parent: Nullable["TestsuiteSummary"] = None
	):
		"""
		Initializes the fields of a test suite.

		:param name:               Name of the test suite.
		:param startTime:          Time when the test suite was started.
		:param duration:           duration of the entity's execution.
		:param status:             Overall status of the test suite.
		:param parent:             Reference to the parent test summary.
		:raises TypeError:         If parameter 'testcases' is not iterable.
		:raises TypeError:         If element in parameter 'testcases' is not a Testcase.
		:raises AlreadyInHierarchyException: If a test case in parameter 'testcases' is already part of a test entity hierarchy.
		:raises DuplicateTestcaseException:  If a test case in parameter 'testcases' is already listed (by name) in the list of test cases.
		"""
		if parent is not None:
			if not isinstance(parent, TestsuiteSummary):
				ex = TypeError(f"Parameter 'parent' is not of type 'TestsuiteSummary'.")
				if version_info >= (3, 11):  # pragma: no cover
					ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
				raise ex

			parent._testsuites[name] = self

		super().__init__(name, startTime, duration, status, parent)

		self._hostname = hostname

		self._testclasses = {}
		if testclasses is not None:
			for testclass in testclasses:
				if testclass._parent is not None:
					raise ValueError(f"Class '{testclass._name}' is already part of a testsuite hierarchy.")

				if testclass._name in self._testclasses:
					raise DuplicateTestcaseException(f"Testsuite already contains a class with same name '{testclass._name}'.")

				testclass._parent = self
				self._testclasses[testclass._name] = testclass

	@readonly
	def Hostname(self) -> Nullable[str]:
		return self._hostname

	@readonly
	def Testclasses(self) -> Dict[str, "Testclass"]:
		return self._testclasses

	@readonly
	def TestclassCount(self) -> int:
		return len(self._testclasses)

	# @readonly
	# def Testcases(self) -> Dict[str, "Testcase"]:
	# 	return self._classes

	@readonly
	def TestcaseCount(self) -> int:
		return sum(cls.TestcaseCount for cls in self._testclasses.values())

	@readonly
	def AssertionCount(self) -> int:
		return sum(cls.AssertionCount for cls in self._testclasses.values())

	def AddTestclass(self, testclass: "Testclass") -> None:
		if testclass._parent is not None:
			raise ValueError(f"Class '{testclass._name}' is already part of a testsuite hierarchy.")

		if testclass._name in self._testclasses:
			raise DuplicateTestcaseException(f"Testsuite already contains a class with same name '{testclass._name}'.")

		testclass._parent = self
		self._testclasses[testclass._name] = testclass

	def AddTestclasses(self, testclasses: Iterable["Testclass"]) -> None:
		for testcase in testclasses:
			self.AddTestclass(testcase)

	# def IterateTestsuites(self, scheme: IterationScheme = IterationScheme.TestsuiteDefault) -> Generator[TestsuiteType, None, None]:
	# 	return self.Iterate(scheme)

	def IterateTestcases(self, scheme: IterationScheme = IterationScheme.TestcaseDefault) -> Generator[Testcase, None, None]:
		return self.Iterate(scheme)

	def Copy(self) -> "Testsuite":
		return self.__class__(
			self._name,
			self._hostname,
			self._startTime,
			self._duration,
			self._status
		)

	def Aggregate(self, strict: bool = True) -> TestsuiteAggregateReturnType:
		tests, skipped, errored, failed, passed = super().Aggregate()

		for testclass in self._testclasses.values():
			_ = testclass.Aggregate(strict)

			tests += 1

			status = testclass._status
			if status is TestcaseStatus.Unknown:
				raise UnittestException(f"Found testclass '{testclass._name}' with state 'Unknown'.")
			elif status is TestcaseStatus.Skipped:
				skipped += 1
			elif status is TestcaseStatus.Errored:
				errored += 1
			elif status is TestcaseStatus.Passed:
				passed += 1
			elif status is TestcaseStatus.Failed:
				failed += 1
			elif status & TestcaseStatus.Mask is not TestcaseStatus.Unknown:
				raise UnittestException(f"Found testclass '{testclass._name}' with unsupported state '{status}'.")
			else:
				raise UnittestException(f"Internal error for testclass '{testclass._name}', field '_status' is '{status}'.")

		self._tests = tests
		self._skipped = skipped
		self._errored = errored
		self._failed = failed
		self._passed = passed

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

		return tests, skipped, errored, failed, passed

	def Iterate(self, scheme: IterationScheme = IterationScheme.Default) -> Generator[Union[TestsuiteType, Testcase], None, None]:
		"""
		Iterate the test suite and its child elements according to the iteration scheme.

		If no scheme is given, use the default scheme.

		:param scheme: Scheme how to iterate the test suite and its child elements.
		:returns:      A generator for iterating the results filtered and in the order defined by the iteration scheme.
		"""
		assert IterationScheme.PreOrder | IterationScheme.PostOrder not in scheme

		if IterationScheme.PreOrder in scheme:
			if IterationScheme.IncludeSelf | IterationScheme.IncludeTestsuites in scheme:
				yield self

			if IterationScheme.IncludeTestcases in scheme:
				for testcase in self._testclasses.values():
					yield testcase

		for testclass in self._testclasses.values():
			yield from testclass.Iterate(scheme | IterationScheme.IncludeSelf)

		if IterationScheme.PostOrder in scheme:
			if IterationScheme.IncludeTestcases in scheme:
				for testcase in self._testclasses.values():
					yield testcase

			if IterationScheme.IncludeSelf | IterationScheme.IncludeTestsuites in scheme:
				yield self

	@classmethod
	def FromTestsuite(cls, testsuite: ut_Testsuite) -> "Testsuite":
		"""
		Convert a test suite of the unified test entity data model to the JUnit specific data model's test suite object.

		:param testsuite: Test suite from unified data model.
		:return:          Test suite from JUnit specific data model.
		"""
		juTestsuite = cls(
			testsuite._name,
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
				raise UnittestException(f"Testcase '{tc._name}' is not part of a hierarchy.")

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
		testsuite = ut_Testsuite(
			self._name,
			TestsuiteKind.Logical,
			startTime=self._startTime,
			totalDuration=self._duration,
			status=self._status,
		)

		for testclass in self._testclasses.values():
			suite = testsuite
			classpath = testclass._name.split(".")
			for element in classpath:
				if element in suite._testsuites:
					suite = suite._testsuites[element]
				else:
					suite = ut_Testsuite(element, kind=TestsuiteKind.Package, parent=suite)

			suite._kind = TestsuiteKind.Class
			if suite._parent is not testsuite:
				suite._parent._kind = TestsuiteKind.Module

			suite.AddTestcases(tc.ToTestcase() for tc in testclass._testcases.values())

		return testsuite

	def ToTree(self) -> Node:
		node = Node(
			value=self._name,
			children=(cls.ToTree() for cls in self._testclasses.values())
		)
		node["startTime"] = self._startTime
		node["duration"] = self._duration

		return node

	def __str__(self) -> str:
		moduleName = self.__module__.split(".")[-1]
		className = self.__class__.__name__
		return (
			f"<{moduleName}{className} {self._name}: {self._status.name} - tests:{self._tests}>"
		)


@export
class TestsuiteSummary(TestsuiteBase):
	_testsuites: Dict[str, Testsuite]

	def __init__(
		self,
		name: str,
		startTime: Nullable[datetime] = None,
		duration:  Nullable[timedelta] = None,
		status: TestsuiteStatus = TestsuiteStatus.Unknown,
		testsuites: Nullable[Iterable[Testsuite]] = None
	):
		super().__init__(name, startTime, duration, status, None)

		self._testsuites = {}
		if testsuites is not None:
			for testsuite in testsuites:
				if testsuite._parent is not None:
					raise ValueError(f"Testsuite '{testsuite._name}' is already part of a testsuite hierarchy.")

				if testsuite._name in self._testsuites:
					raise DuplicateTestsuiteException(f"Testsuite already contains a testsuite with same name '{testsuite._name}'.")

				testsuite._parent = self
				self._testsuites[testsuite._name] = testsuite

	@readonly
	def Testsuites(self) -> Dict[str, Testsuite]:
		return self._testsuites

	@readonly
	def TestcaseCount(self) -> int:
		return sum(ts.TestcaseCount for ts in self._testsuites.values())

	@readonly
	def TestsuiteCount(self) -> int:
		return len(self._testsuites)

	@readonly
	def AssertionCount(self) -> int:
		return sum(ts.AssertionCount for ts in self._testsuites.values())

	def AddTestsuite(self, testsuite: Testsuite) -> None:
		if testsuite._parent is not None:
			raise ValueError(f"Testsuite '{testsuite._name}' is already part of a testsuite hierarchy.")

		if testsuite._name in self._testsuites:
			raise DuplicateTestsuiteException(f"Testsuite already contains a testsuite with same name '{testsuite._name}'.")

		testsuite._parent = self
		self._testsuites[testsuite._name] = testsuite

	def AddTestsuites(self, testsuites: Iterable[Testsuite]) -> None:
		for testsuite in testsuites:
			self.AddTestsuite(testsuite)

	def Aggregate(self) -> TestsuiteAggregateReturnType:
		tests, skipped, errored, failed, passed = super().Aggregate()

		self._tests = tests
		self._skipped = skipped
		self._errored = errored
		self._failed = failed
		self._passed = passed

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

		return tests, skipped, errored, failed, passed

	def Iterate(self, scheme: IterationScheme = IterationScheme.Default) -> Generator[Union[Testsuite, Testcase], None, None]:
		"""
		Iterate the test suite summary and its child elements according to the iteration scheme.

		If no scheme is given, use the default scheme.

		:param scheme: Scheme how to iterate the test suite summary and its child elements.
		:returns:      A generator for iterating the results filtered and in the order defined by the iteration scheme.
		"""
		if IterationScheme.IncludeSelf | IterationScheme.IncludeTestsuites | IterationScheme.PreOrder in scheme:
			yield self

		for testsuite in self._testsuites.values():
			yield from testsuite.IterateTestsuites(scheme | IterationScheme.IncludeSelf)

		if IterationScheme.IncludeSelf | IterationScheme.IncludeTestsuites | IterationScheme.PostOrder in scheme:
			yield self

	@classmethod
	def FromTestsuiteSummary(cls, testsuiteSummary: ut_TestsuiteSummary) -> "TestsuiteSummary":
		"""
		Convert a test suite summary of the unified test entity data model to the JUnit specific data model's test suite.

		:param testsuiteSummary: Test suite summary from unified data model.
		:return:                 Test suite summary from JUnit specific data model.
		"""
		return cls(
			testsuiteSummary._name,
			startTime=testsuiteSummary._startTime,
			duration=testsuiteSummary._totalDuration,
			status=testsuiteSummary._status,
			testsuites=(ut_Testsuite.FromTestsuite(testsuite) for testsuite in testsuiteSummary._testsuites.values())
		)

	def ToTestsuiteSummary(self) -> ut_TestsuiteSummary:
		"""
		Convert this test suite summary a new test suite summary of the unified data model.

		All fields are copied to the new instance. Child elements like test suites are copied recursively.

		:return: A test suite summary of the unified test entity data model.
		"""
		return ut_TestsuiteSummary(
			self._name,
			startTime=self._startTime,
			totalDuration=self._duration,
			status=self._status,
			testsuites=(testsuite.ToTestsuite() for testsuite in self._testsuites.values())
		)

	def ToTree(self) -> Node:
		node = Node(
			value=self._name,
			children=(ts.ToTree() for ts in self._testsuites.values())
		)
		node["startTime"] = self._startTime
		node["duration"] = self._duration

		return node

	def __str__(self) -> str:
		moduleName = self.__module__.split(".")[-1]
		className = self.__class__.__name__
		return (
			f"<{moduleName}{className} {self._name}: {self._status.name} - tests:{self._tests}>"
		)


@export
class Document(TestsuiteSummary, ut_Document):
	_TESTCASE:          ClassVar[Type[Testcase]] =         Testcase
	_TESTCLASS:         ClassVar[Type[Testclass]] =        Testclass
	_TESTSUITE:         ClassVar[Type[Testsuite]] =        Testsuite

	_readerMode:        JUnitReaderMode
	_xmlDocument:       Nullable[_ElementTree]

	def __init__(self, xmlReportFile: Path, analyzeAndConvert: bool = False, readerMode: JUnitReaderMode = JUnitReaderMode.Default):
		super().__init__("Unprocessed JUnit XML file")

		self._readerMode = readerMode
		self._xmlDocument = None

		ut_Document.__init__(self, xmlReportFile, analyzeAndConvert)

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

		The used XML schema definition is generic to support "any" dialect.
		"""
		xmlSchemaFile = "Any-JUnit.xsd"
		self._Analyze(xmlSchemaFile)

	def _Analyze(self, xmlSchemaFile: str) -> None:
		if not self._path.exists():
			raise UnittestException(f"JUnit XML file '{self._path}' does not exist.") \
				from FileNotFoundError(f"File '{self._path}' not found.")

		startAnalysis = perf_counter_ns()
		try:
			xmlSchemaResourceFile = getResourceFile(Resources, xmlSchemaFile)
		except ToolingException as ex:
			raise UnittestException(f"Couldn't locate XML Schema '{xmlSchemaFile}' in package resources.") from ex

		try:
			schemaParser = XMLParser(ns_clean=True)
			schemaRoot = parse(xmlSchemaResourceFile, schemaParser)
		except XMLSyntaxError as ex:
			raise UnittestException(f"XML Syntax Error while parsing XML Schema '{xmlSchemaFile}'.") from ex

		try:
			junitSchema = XMLSchema(schemaRoot)
		except XMLSchemaParseError as ex:
			raise UnittestException(f"Error while parsing XML Schema '{xmlSchemaFile}'.")

		try:
			junitParser = XMLParser(schema=junitSchema, ns_clean=True)
			junitDocument = parse(self._path, parser=junitParser)

			self._xmlDocument = junitDocument
		except XMLSyntaxError as ex:
			if version_info >= (3, 11):  # pragma: no cover
				for logEntry in junitParser.error_log:
					ex.add_note(str(logEntry))
			raise UnittestException(f"XML syntax or validation error for '{self._path}' using XSD schema '{xmlSchemaResourceFile}'.") from ex
		except Exception as ex:
			raise UnittestException(f"Couldn't open '{self._path}'.") from ex

		endAnalysis = perf_counter_ns()
		self._analysisDuration = (endAnalysis - startAnalysis) / 1e9

	def Write(self, path: Nullable[Path] = None, overwrite: bool = False, regenerate: bool = False) -> None:
		"""
		Write the data model as XML into a file adhering to the Any JUnit dialect.

		:param path:               Optional path to the XMl file, if internal path shouldn't be used.
		:param overwrite:          If true, overwrite an existing file.
		:param regenerate:         If true, regenerate the XML structure from data model.
		:raises UnittestException: If the file cannot be overwritten.
		:raises UnittestException: If the internal XML data structure wasn't generated.
		:raises UnittestException: If the file cannot be opened or written.
		"""
		if path is None:
			path = self._path

		if not overwrite and path.exists():
			raise UnittestException(f"JUnit XML file '{path}' can not be overwritten.") \
				from FileExistsError(f"File '{path}' already exists.")

		if regenerate:
			self.Generate(overwrite=True)

		if self._xmlDocument is None:
			ex = UnittestException(f"Internal XML document tree is empty and needs to be generated before write is possible.")
			ex.add_note(f"Call 'JUnitDocument.Generate()' or 'JUnitDocument.Write(..., regenerate=True)'.")
			raise ex

		try:
			with path.open("wb") as file:
				file.write(tostring(self._xmlDocument, encoding="utf-8", xml_declaration=True, pretty_print=True))
		except Exception as ex:
			raise UnittestException(f"JUnit XML file '{path}' can not be written.") from ex

	def Convert(self) -> None:
		"""
		Convert the parsed and validated XML data structure into a JUnit test entity hierarchy.

		This method converts the root element.

		.. hint::

		   The time spend for model conversion will be made available via property :data:`ModelConversionDuration`.

		:raises UnittestException: If XML was not read and parsed before.
		"""
		if self._xmlDocument is None:
			ex = UnittestException(f"JUnit XML file '{self._path}' needs to be read and analyzed by an XML parser.")
			ex.add_note(f"Call 'JUnitDocument.Analyze()' or create the document using 'JUnitDocument(path, parse=True)'.")
			raise ex

		startConversion = perf_counter_ns()
		rootElement: _Element = self._xmlDocument.getroot()

		self._name = self._ConvertName(rootElement, optional=True)
		self._startTime = self._ConvertTimestamp(rootElement, optional=True)
		self._duration = self._ConvertTime(rootElement, optional=True)

		if False:  # self._readerMode is JUnitReaderMode.
			self._tests = self._ConvertTests(testsuitesNode)
			self._skipped = self._ConvertSkipped(testsuitesNode)
			self._errored = self._ConvertErrors(testsuitesNode)
			self._failed = self._ConvertFailures(testsuitesNode)
			self._assertionCount = self._ConvertAssertions(testsuitesNode)

		for rootNode in rootElement.iterchildren(tag="testsuite"):  # type: _Element
			self._ConvertTestsuite(self, rootNode)

		if True:  # self._readerMode is JUnitReaderMode.
			self.Aggregate()

		endConversation = perf_counter_ns()
		self._modelConversion = (endConversation - startConversion) / 1e9

	def _ConvertName(self, element: _Element, default: str = "root", optional: bool = True) -> str:
		"""
		Convert the ``name`` attribute from an XML element node to a string.

		:param element:            The XML element node with a ``name`` attribute.
		:param default:            The default value, if no ``name`` attribute was found.
		:param optional:           If false, an exception is raised for the missing attribute.
		:return:                   The ``name`` attribute's content if found, otherwise the given default value.
		:raises UnittestException: If optional is false and no ``name`` attribute exists on the given element node.
		"""
		if "name" in element.attrib:
			return element.attrib["name"]
		elif not optional:
			raise UnittestException(f"Required parameter 'name' not found in tag '{element.tag}'.")
		else:
			return default

	def _ConvertTimestamp(self, element: _Element, optional: bool = True) -> Nullable[datetime]:
		"""
		Convert the ``timestamp`` attribute from an XML element node to a datetime.

		:param element:            The XML element node with a ``timestamp`` attribute.
		:param optional:           If false, an exception is raised for the missing attribute.
		:return:                   The ``timestamp`` attribute's content if found, otherwise ``None``.
		:raises UnittestException: If optional is false and no ``timestamp`` attribute exists on the given element node.
		"""
		if "timestamp" in element.attrib:
			timestamp = element.attrib["timestamp"]
			return datetime.fromisoformat(timestamp)
		elif not optional:
			raise UnittestException(f"Required parameter 'timestamp' not found in tag '{element.tag}'.")
		else:
			return None

	def _ConvertTime(self, element: _Element, optional: bool = True) -> Nullable[timedelta]:
		"""
		Convert the ``time`` attribute from an XML element node to a timedelta.

		:param element:            The XML element node with a ``time`` attribute.
		:param optional:           If false, an exception is raised for the missing attribute.
		:return:                   The ``time`` attribute's content if found, otherwise ``None``.
		:raises UnittestException: If optional is false and no ``time`` attribute exists on the given element node.
		"""
		if "time" in element.attrib:
			time = element.attrib["time"]
			return timedelta(seconds=float(time))
		elif not optional:
			raise UnittestException(f"Required parameter 'time' not found in tag '{element.tag}'.")
		else:
			return None

	def _ConvertHostname(self, element: _Element, default: str = "localhost", optional: bool = True) -> str:
		"""
		Convert the ``hostname`` attribute from an XML element node to a string.

		:param element:            The XML element node with a ``hostname`` attribute.
		:param default:            The default value, if no ``hostname`` attribute was found.
		:param optional:           If false, an exception is raised for the missing attribute.
		:return:                   The ``hostname`` attribute's content if found, otherwise the given default value.
		:raises UnittestException: If optional is false and no ``hostname`` attribute exists on the given element node.
		"""
		if "hostname" in element.attrib:
			return element.attrib["hostname"]
		elif not optional:
			raise UnittestException(f"Required parameter 'hostname' not found in tag '{element.tag}'.")
		else:
			return default

	def _ConvertClassname(self, element: _Element) -> str:
		"""
		Convert the ``classname`` attribute from an XML element node to a string.

		:param element:            The XML element node with a ``classname`` attribute.
		:return:                   The ``classname`` attribute's content.
		:raises UnittestException: If no ``classname`` attribute exists on the given element node.
		"""
		if "classname" in element.attrib:
			return element.attrib["classname"]
		else:
			raise UnittestException(f"Required parameter 'classname' not found in tag '{element.tag}'.")

	def _ConvertTests(self, element: _Element, default: Nullable[int] = None, optional: bool = True) -> Nullable[int]:
		"""
		Convert the ``tests`` attribute from an XML element node to an integer.

		:param element:            The XML element node with a ``tests`` attribute.
		:param default:            The default value, if no ``tests`` attribute was found.
		:param optional:           If false, an exception is raised for the missing attribute.
		:return:                   The ``tests`` attribute's content if found, otherwise the given default value.
		:raises UnittestException: If optional is false and no ``tests`` attribute exists on the given element node.
		"""
		if "tests" in element.attrib:
			return int(element.attrib["tests"])
		elif not optional:
			raise UnittestException(f"Required parameter 'tests' not found in tag '{element.tag}'.")
		else:
			return default

	def _ConvertSkipped(self, element: _Element, default: Nullable[int] = None, optional: bool = True) -> Nullable[int]:
		"""
		Convert the ``skipped`` attribute from an XML element node to an integer.

		:param element:            The XML element node with a ``skipped`` attribute.
		:param default:            The default value, if no ``skipped`` attribute was found.
		:param optional:           If false, an exception is raised for the missing attribute.
		:return:                   The ``skipped`` attribute's content if found, otherwise the given default value.
		:raises UnittestException: If optional is false and no ``skipped`` attribute exists on the given element node.
		"""
		if "skipped" in element.attrib:
			return int(element.attrib["skipped"])
		elif not optional:
			raise UnittestException(f"Required parameter 'skipped' not found in tag '{element.tag}'.")
		else:
			return default

	def _ConvertErrors(self, element: _Element, default: Nullable[int] = None, optional: bool = True) -> Nullable[int]:
		"""
		Convert the ``errors`` attribute from an XML element node to an integer.

		:param element:            The XML element node with a ``errors`` attribute.
		:param default:            The default value, if no ``errors`` attribute was found.
		:param optional:           If false, an exception is raised for the missing attribute.
		:return:                   The ``errors`` attribute's content if found, otherwise the given default value.
		:raises UnittestException: If optional is false and no ``errors`` attribute exists on the given element node.
		"""
		if "errors" in element.attrib:
			return int(element.attrib["errors"])
		elif not optional:
			raise UnittestException(f"Required parameter 'errors' not found in tag '{element.tag}'.")
		else:
			return default

	def _ConvertFailures(self, element: _Element, default: Nullable[int] = None, optional: bool = True) -> Nullable[int]:
		"""
		Convert the ``failures`` attribute from an XML element node to an integer.

		:param element:            The XML element node with a ``failures`` attribute.
		:param default:            The default value, if no ``failures`` attribute was found.
		:param optional:           If false, an exception is raised for the missing attribute.
		:return:                   The ``failures`` attribute's content if found, otherwise the given default value.
		:raises UnittestException: If optional is false and no ``failures`` attribute exists on the given element node.
		"""
		if "failures" in element.attrib:
			return int(element.attrib["failures"])
		elif not optional:
			raise UnittestException(f"Required parameter 'failures' not found in tag '{element.tag}'.")
		else:
			return default

	def _ConvertAssertions(self, element: _Element, default: Nullable[int] = None, optional: bool = True) -> Nullable[int]:
		"""
		Convert the ``assertions`` attribute from an XML element node to an integer.

		:param element:            The XML element node with a ``assertions`` attribute.
		:param default:            The default value, if no ``assertions`` attribute was found.
		:param optional:           If false, an exception is raised for the missing attribute.
		:return:                   The ``assertions`` attribute's content if found, otherwise the given default value.
		:raises UnittestException: If optional is false and no ``assertions`` attribute exists on the given element node.
		"""
		if "assertions" in element.attrib:
			return int(element.attrib["assertions"])
		elif not optional:
			raise UnittestException(f"Required parameter 'assertions' not found in tag '{element.tag}'.")
		else:
			return default

	def _ConvertTestsuite(self, parent: TestsuiteSummary, testsuitesNode: _Element) -> None:
		"""
		Convert the XML data structure of a ``<testsuite>`` to a test suite.

		This method uses private helper methods provided by the base-class.

		:param parent:         The test suite summary as a parent element in the test entity hierarchy.
		:param testsuitesNode: The current XML element node representing a test suite.
		"""
		newTestsuite = self._TESTSUITE(
			self._ConvertName(testsuitesNode, optional=False),
			self._ConvertHostname(testsuitesNode, optional=True),
			self._ConvertTimestamp(testsuitesNode, optional=True),
			self._ConvertTime(testsuitesNode, optional=True),
			parent=parent
		)

		if False:  # self._readerMode is JUnitReaderMode.
			self._tests = self._ConvertTests(testsuitesNode)
			self._skipped = self._ConvertSkipped(testsuitesNode)
			self._errored = self._ConvertErrors(testsuitesNode)
			self._failed = self._ConvertFailures(testsuitesNode)
			self._assertionCount = self._ConvertAssertions(testsuitesNode)

		self._ConvertTestsuiteChildren(testsuitesNode, newTestsuite)

	def _ConvertTestsuiteChildren(self, testsuitesNode: _Element, newTestsuite: Testsuite) -> None:
		for node in testsuitesNode.iterchildren():   # type: _Element
			# if node.tag == "testsuite":
			# 	self._ConvertTestsuite(newTestsuite, node)
			# el
			if node.tag == "testcase":
				self._ConvertTestcase(newTestsuite, node)

	def _ConvertTestcase(self, parent: Testsuite, testcaseNode: _Element) -> None:
		"""
		Convert the XML data structure of a ``<testcase>`` to a test case.

		This method uses private helper methods provided by the base-class.

		:param parent:       The test suite as a parent element in the test entity hierarchy.
		:param testcaseNode: The current XML element node representing a test case.
		"""
		className = self._ConvertClassname(testcaseNode)
		testclass = self._FindOrCreateTestclass(parent, className)

		newTestcase = self._TESTCASE(
			self._ConvertName(testcaseNode, optional=False),
			self._ConvertTime(testcaseNode, optional=False),
			assertionCount=self._ConvertAssertions(testcaseNode),
			parent=testclass
		)

		self._ConvertTestcaseChildren(testcaseNode, newTestcase)

	def _FindOrCreateTestclass(self, parent: Testsuite, className: str) -> Testclass:
		if className in parent._testclasses:
			return parent._testclasses[className]
		else:
			return self._TESTCLASS(className, parent=parent)

	def _ConvertTestcaseChildren(self, testcaseNode: _Element, newTestcase: Testcase) -> None:
		for node in testcaseNode.iterchildren():   # type: _Element
			if isinstance(node, _Comment):
				pass
			elif isinstance(node, _Element):
				if node.tag == "skipped":
					newTestcase._status = TestcaseStatus.Skipped
				elif node.tag == "failure":
					newTestcase._status = TestcaseStatus.Failed
				elif node.tag == "error":
					newTestcase._status = TestcaseStatus.Errored
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

		if newTestcase._status is TestcaseStatus.Unknown:
			newTestcase._status = TestcaseStatus.Passed

	def Generate(self, overwrite: bool = False) -> None:
		"""
		Generate the internal XML data structure from test suites and test cases.

		This method generates the XML root element (``<testsuites>``) and recursively calls other generated methods.

		:param overwrite:          Overwrite the internal XML data structure.
		:raises UnittestException: If overwrite is false and the internal XML data structure is not empty.
		"""
		if not overwrite and self._xmlDocument is not None:
			raise UnittestException(f"Internal XML document is populated with data.")

		rootElement = Element("testsuites")
		rootElement.attrib["name"] = self._name
		if self._startTime is not None:
			rootElement.attrib["timestamp"] = f"{self._startTime.isoformat()}"
		if self._duration is not None:
			rootElement.attrib["time"] = f"{self._duration.total_seconds():.6f}"
		rootElement.attrib["tests"] = str(self._tests)
		rootElement.attrib["failures"] = str(self._failed)
		rootElement.attrib["errors"] = str(self._errored)
		rootElement.attrib["skipped"] = str(self._skipped)
		# if self._assertionCount is not None:
		# 	rootElement.attrib["assertions"] = f"{self._assertionCount}"

		self._xmlDocument = ElementTree(rootElement)

		for testsuite in self._testsuites.values():
			self._GenerateTestsuite(testsuite, rootElement)

	def _GenerateTestsuite(self, testsuite: Testsuite, parentElement: _Element) -> None:
		"""
		Generate the internal XML data structure for a test suite.

		This method generates the XML element (``<testsuite>``) and recursively calls other generated methods.

		:param testsuite:     The test suite to convert to an XML data structures.
		:param parentElement: The parent XML data structure element, this data structure part will be added to.
		:return:
		"""
		testsuiteElement = SubElement(parentElement, "testsuite")
		testsuiteElement.attrib["name"] = testsuite._name
		if testsuite._startTime is not None:
			testsuiteElement.attrib["timestamp"] = f"{testsuite._startTime.isoformat()}"
		if testsuite._duration is not None:
			testsuiteElement.attrib["time"] = f"{testsuite._duration.total_seconds():.6f}"
		testsuiteElement.attrib["tests"] = str(testsuite._tests)
		testsuiteElement.attrib["failures"] = str(testsuite._failed)
		testsuiteElement.attrib["errors"] = str(testsuite._errored)
		testsuiteElement.attrib["skipped"] = str(testsuite._skipped)
		# if testsuite._assertionCount is not None:
		# 	testsuiteElement.attrib["assertions"] = f"{testsuite._assertionCount}"
		if testsuite._hostname is not None:
			testsuiteElement.attrib["hostname"] = testsuite._hostname

		for testclass in testsuite._testclasses.values():
			for tc in testclass._testcases.values():
				self._GenerateTestcase(tc, testsuiteElement)

	def _GenerateTestcase(self, testcase: Testcase, parentElement: _Element) -> None:
		"""
		Generate the internal XML data structure for a test case.

		This method generates the XML element (``<testcase>``) and recursively calls other generated methods.

		:param testcase:      The test case to convert to an XML data structures.
		:param parentElement: The parent XML data structure element, this data structure part will be added to.
		:return:
		"""
		testcaseElement = SubElement(parentElement, "testcase")
		if testcase.Classname is not None:
			testcaseElement.attrib["classname"] = testcase.Classname
		testcaseElement.attrib["name"] = testcase._name
		if testcase._duration is not None:
			testcaseElement.attrib["time"] = f"{testcase._duration.total_seconds():.6f}"
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

	def __str__(self) -> str:
		moduleName = self.__module__.split(".")[-1]
		className = self.__class__.__name__
		return (
			f"<{moduleName}{className} {self._name} ({self._path}): {self._status.name} - suites/tests:{self.TestsuiteCount}/{self.TestcaseCount}>"
		)
