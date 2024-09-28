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
from sys             import version_info
from time            import perf_counter_ns
from typing          import Optional as Nullable, Iterable, Dict, Any, Generator, Tuple, Union, TypeVar, Type, ClassVar

from lxml.etree                 import XMLParser, parse, XMLSchema, XMLSyntaxError, _ElementTree, _Element, _Comment, XMLSchemaParseError
from lxml.etree                 import ElementTree, Element, SubElement, tostring
from pyTooling.Common           import getFullyQualifiedName, getResourceFile
from pyTooling.Decorators       import export, readonly
from pyTooling.Exceptions       import ToolingException
from pyTooling.MetaClasses      import ExtendedType, mustoverride, abstractmethod
from pyTooling.Tree             import Node

from pyEDAA.Reports             import resources
from pyEDAA.Reports.Unittesting import UnittestException, DuplicateTestsuiteException, DuplicateTestcaseException, \
	TestsuiteKind
from pyEDAA.Reports.Unittesting import TestcaseStatus, TestsuiteStatus, IterationScheme
from pyEDAA.Reports.Unittesting import Document as ut_Document, TestsuiteSummary as ut_TestsuiteSummary
from pyEDAA.Reports.Unittesting import Testsuite as ut_Testsuite, Testcase as ut_Testcase


@export
class JUnitException:
	"""An exception mixin for JUnit format specific exceptions."""


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


TestsuiteType = TypeVar("TestsuiteType", bound="Testsuite")
TestcaseAggregateReturnType = Tuple[int, int, int]
TestsuiteAggregateReturnType = Tuple[int, int, int, int, int]


@export
class Base(metaclass=ExtendedType, slots=True):
	_parent:         Nullable["Testsuite"]
	_name:           str

	def __init__(self, name: str, parent: Nullable["Testsuite"] = None):
		if name is None:
			raise ValueError(f"Parameter 'name' is None.")
		elif not isinstance(name, str):
			ex = TypeError(f"Parameter 'name' is not of type 'str'.")
			if version_info >= (3, 11):  # pragma: no cover
				ex.add_note(f"Got type '{getFullyQualifiedName(name)}'.")
			raise ex

		# TODO: check parameter parent

		self._parent = parent
		self._name = name

	@readonly
	def Parent(self) -> Nullable["Testsuite"]:
		return self._parent

	# QUESTION: allow Parent as setter?

	@readonly
	def Name(self) -> str:
		return self._name


@export
class BaseWithProperties(Base):
	_duration:       Nullable[timedelta]
	_assertionCount: Nullable[int]
	_properties:     Dict[str, Any]

	def __init__(self, name: str, duration: Nullable[timedelta] = None, assertionCount: Nullable[int] = None, parent: Nullable["Testsuite"] = None):
		super().__init__(name, parent)

		# TODO: check parameter duration
		self._duration = duration
		self._assertionCount = assertionCount

		self._properties = {}

	@readonly
	def Duration(self) -> timedelta:
		return self._duration

	@readonly
	@abstractmethod
	def AssertionCount(self) -> int:
		pass

	def __len__(self) -> int:
		return len(self._properties)

	def __getitem__(self, key: str) -> Any:
		return self._properties[key]

	def __setitem__(self, key: str, value: Any) -> None:
		self._properties[key] = value

	def __delitem__(self, key: str) -> None:
		del self._properties[key]

	def __contains__(self, key: str) -> bool:
		return key in self._properties

	def __iter__(self) -> Generator[Tuple[str, Any], None, None]:
		yield from self._properties.items()


@export
class Testcase(BaseWithProperties):
	_classname:      str
	_status:         TestcaseStatus

	def __init__(
		self,
		name: str,
		duration:  Nullable[timedelta] = None,
		status: TestcaseStatus = TestcaseStatus.Unknown,
		assertionCount: Nullable[int] = None,
		parent: Nullable["Testclass"] = None
	):
		if parent is not None:
			if not isinstance(parent, Testclass):
				ex = TypeError(f"Parameter 'parent' is not of type 'Testclass'.")
				if version_info >= (3, 11):  # pragma: no cover
					ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
				raise ex

			parent._testcases[name] = self

		super().__init__(name, duration, assertionCount, parent)

		self._status = status

	@readonly
	def Classname(self) -> str:
		if self._parent is None:
			raise UnittestException("Standalone Testcase instance is not linked to a Testclass.")
		return self._parent._name

	@readonly
	def Status(self) -> TestcaseStatus:
		return self._status

	@readonly
	def AssertionCount(self) -> int:
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
	_testcases: Dict[str, "Testcase"]

	def __init__(
		self,
		classname: str,
		testcases: Nullable[Iterable["Testcase"]] = None,
		parent: Nullable["Testsuite"] = None
	):
		if parent is not None:
			# if not isinstance(parent, Testsuite):
			# 	raise TypeError(f"Parameter 'parent' is not of type 'Testsuite'.")
			# 	if version_info >= (3, 11):  # pragma: no cover
			#	ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			#	raise ex

			parent._testclasses[classname] = self

		super().__init__(classname, parent)

		self._testcases = {}
		if testcases is not None:
			for testcase in testcases:
				if testcase._parent is not None:
					raise ValueError(f"Testcase '{testcase._name}' is already part of a testsuite hierarchy.")

				if testcase._name in self._testcases:
					raise DuplicateTestcaseException(f"Class already contains a testcase with same name '{testcase._name}'.")

				testcase._parent = self
				self._testcases[testcase._name] = testcase

	@readonly
	def Classname(self) -> str:
		return self._name

	@readonly
	def Testcases(self) -> Dict[str, "Testcase"]:
		return self._testcases

	@readonly
	def TestcaseCount(self) -> int:
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
		assert IterationScheme.PreOrder | IterationScheme.PostOrder not in scheme

		if IterationScheme.PreOrder in scheme:
			if IterationScheme.IncludeSelf | IterationScheme.IncludeTestsuites in scheme:
				yield self

			if IterationScheme.IncludeTestcases in scheme:
				for testcase in self._testclasses.values():
					yield testcase

		for testsuite in self._testsuites.values():
			yield from testsuite.Iterate(scheme | IterationScheme.IncludeSelf)

		if IterationScheme.PostOrder in scheme:
			if IterationScheme.IncludeTestcases in scheme:
				for testcase in self._testclasses.values():
					yield testcase

			if IterationScheme.IncludeSelf | IterationScheme.IncludeTestsuites in scheme:
				yield self

	@classmethod
	def FromTestsuite(cls, testsuite: ut_Testsuite) -> "Testsuite":
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
		if IterationScheme.IncludeSelf | IterationScheme.IncludeTestsuites | IterationScheme.PreOrder in scheme:
			yield self

		for testsuite in self._testsuites.values():
			yield from testsuite.IterateTestsuites(scheme | IterationScheme.IncludeSelf)

		if IterationScheme.IncludeSelf | IterationScheme.IncludeTestsuites | IterationScheme.PostOrder in scheme:
			yield self

	@classmethod
	def FromTestsuiteSummary(cls, testsuiteSummary: ut_TestsuiteSummary) -> "TestsuiteSummary":
		return cls(
			testsuiteSummary._name,
			startTime=testsuiteSummary._startTime,
			duration=testsuiteSummary._totalDuration,
			status=testsuiteSummary._status,
			testsuites=(ut_Testsuite.FromTestsuite(testsuite) for testsuite in testsuiteSummary._testsuites.values())
		)

	def ToTestsuiteSummary(self) -> ut_TestsuiteSummary:
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

	def __init__(self, xmlReportFile: Path, parse: bool = False, readerMode: JUnitReaderMode = JUnitReaderMode.Default):
		super().__init__("Unprocessed JUnit XML file")
		ut_Document.__init__(self, xmlReportFile)

		self._readerMode = readerMode
		self._xmlDocument = None

		if parse:
			self.Read()
			self.Parse()

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

	def Read(self) -> None:
		xmlSchemaFile = "Generic-JUnit.xsd"
		self._Read(xmlSchemaFile)

	def _Read(self, xmlSchemaFile: str) -> None:
		if not self._path.exists():
			raise UnittestException(f"JUnit XML file '{self._path}' does not exist.") \
				from FileNotFoundError(f"File '{self._path}' not found.")

		startAnalysis = perf_counter_ns()
		try:
			xmlSchemaResourceFile = getResourceFile(resources, xmlSchemaFile)
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

		self._name = self._ParseName(rootElement, optional=True)
		self._startTime = self._ParseTimestamp(rootElement, optional=True)
		self._duration = self._ParseTime(rootElement, optional=True)

		if False:  # self._readerMode is JUnitReaderMode.
			self._tests = self._ParseTests(testsuitesNode)
			self._skipped = self._ParseSkipped(testsuitesNode)
			self._errored = self._ParseErrors(testsuitesNode)
			self._failed = self._ParseFailures(testsuitesNode)
			self._assertionCount = self._ParseAssertions(testsuitesNode)

		for rootNode in rootElement.iterchildren(tag="testsuite"):  # type: _Element
			self._ParseTestsuite(self, rootNode)

		if True:  # self._readerMode is JUnitReaderMode.
			self.Aggregate()

		endConversation = perf_counter_ns()
		self._modelConversion = (endConversation - startConversion) / 1e9

	def _ParseName(self, element: _Element, default: str = "root", optional: bool = True) -> str:
		if "name" in element.attrib:
			return element.attrib["name"]
		elif not optional:
			raise UnittestException(f"Required parameter 'name' not found in tag '{element.tag}'.")
		else:
			return default

	def _ParseTimestamp(self, element: _Element, optional: bool = True) -> Nullable[datetime]:
		if "timestamp" in element.attrib:
			timestamp = element.attrib["timestamp"]
			return datetime.fromisoformat(timestamp)
		elif not optional:
			raise UnittestException(f"Required parameter 'timestamp' not found in tag '{element.tag}'.")
		else:
			return None

	def _ParseTime(self, element: _Element, optional: bool = True) -> Nullable[timedelta]:
		if "time" in element.attrib:
			time = element.attrib["time"]
			return timedelta(seconds=float(time))
		elif not optional:
			raise UnittestException(f"Required parameter 'time' not found in tag '{element.tag}'.")
		else:
			return None

	def _ParseHostname(self, element: _Element, default: str = "localhost", optional: bool = True) -> str:
		if "hostname" in element.attrib:
			return element.attrib["hostname"]
		elif not optional:
			raise UnittestException(f"Required parameter 'hostname' not found in tag '{element.tag}'.")
		else:
			return default

	def _ParseClassname(self, element: _Element, optional: bool = True) -> str:
		if "classname" in element.attrib:
			return element.attrib["classname"]
		elif not optional:
			raise UnittestException(f"Required parameter 'classname' not found in tag '{element.tag}'.")

	def _ParseTests(self, element: _Element, default: Nullable[int] = None, optional: bool = True) -> Nullable[int]:
		if "tests" in element.attrib:
			return int(element.attrib["tests"])
		elif not optional:
			raise UnittestException(f"Required parameter 'tests' not found in tag '{element.tag}'.")
		else:
			return default

	def _ParseSkipped(self, element: _Element, default: Nullable[int] = None, optional: bool = True) -> Nullable[int]:
		if "skipped" in element.attrib:
			return int(element.attrib["skipped"])
		elif not optional:
			raise UnittestException(f"Required parameter 'skipped' not found in tag '{element.tag}'.")
		else:
			return default

	def _ParseErrors(self, element: _Element, default: Nullable[int] = None, optional: bool = True) -> Nullable[int]:
		if "errors" in element.attrib:
			return int(element.attrib["errors"])
		elif not optional:
			raise UnittestException(f"Required parameter 'errors' not found in tag '{element.tag}'.")
		else:
			return default

	def _ParseFailures(self, element: _Element, default: Nullable[int] = None, optional: bool = True) -> Nullable[int]:
		if "failures" in element.attrib:
			return int(element.attrib["failures"])
		elif not optional:
			raise UnittestException(f"Required parameter 'failures' not found in tag '{element.tag}'.")
		else:
			return default

	def _ParseAssertions(self, element: _Element, default: Nullable[int] = None, optional: bool = True) -> Nullable[int]:
		if "assertions" in element.attrib:
			return int(element.attrib["assertions"])
		elif not optional:
			raise UnittestException(f"Required parameter 'assertions' not found in tag '{element.tag}'.")
		else:
			return default

	def _ParseTestsuite(self, parent: TestsuiteSummary, testsuitesNode: _Element) -> None:
		newTestsuite = self._TESTSUITE(
			self._ParseName(testsuitesNode, optional=False),
			self._ParseHostname(testsuitesNode, optional=True),
			self._ParseTimestamp(testsuitesNode, optional=True),
			self._ParseTime(testsuitesNode, optional=True),
			parent=parent
		)

		if False:  # self._readerMode is JUnitReaderMode.
			self._tests = self._ParseTests(testsuitesNode)
			self._skipped = self._ParseSkipped(testsuitesNode)
			self._errored = self._ParseErrors(testsuitesNode)
			self._failed = self._ParseFailures(testsuitesNode)
			self._assertionCount = self._ParseAssertions(testsuitesNode)

		self._ParseTestsuiteChildren(testsuitesNode, newTestsuite)

	def _ParseTestsuiteChildren(self, testsuitesNode: _Element, newTestsuite: Testsuite) -> None:
		for node in testsuitesNode.iterchildren():   # type: _Element
			# if node.tag == "testsuite":
			# 	self._ParseTestsuite(newTestsuite, node)
			# el
			if node.tag == "testcase":
				self._ParseTestcase(newTestsuite, node)

	def _ParseTestcase(self, parent: Testsuite, testcaseNode: _Element) -> None:
		className = self._ParseClassname(testcaseNode, optional=False)
		testclass = self._FindOrCreateTestclass(parent, className)

		newTestcase = self._TESTCASE(
			self._ParseName(testcaseNode, optional=False),
			self._ParseTime(testcaseNode, optional=False),
			assertionCount=self._ParseAssertions(testcaseNode),
			parent=testclass
		)

		self._ParseTestcaseChildren(testcaseNode, newTestcase)

	def _FindOrCreateTestclass(self, parent: Testsuite, className: str) -> Testclass:
		if className in parent._testclasses:
			return parent._testclasses[className]
		else:
			return self._TESTCLASS(className, parent=parent)

	def _ParseTestcaseChildren(self, testcaseNode: _Element, newTestcase: Testcase) -> None:
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
		if self._xmlDocument is not None:
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

	def _GenerateTestsuite(self, testsuite: Testsuite, parentElement: _Element):
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

	def _GenerateTestcase(self, testcase: Testcase, parentElement: _Element):
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
