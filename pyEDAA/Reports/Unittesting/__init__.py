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
"""Abstraction of testsuites and testcases."""
from datetime import timedelta, datetime

from enum    import Flag
from math    import log2
from pathlib import Path
from typing  import Optional as Nullable, Dict, Iterable, Any, Tuple, Generator, Union, List

from pyTooling.Decorators  import export, readonly
from pyTooling.MetaClasses import abstractmethod, ExtendedType, mustoverride

from pyEDAA.Reports        import ReportException


@export
class UnittestException(ReportException):
	pass


@export
class DuplicateTestsuiteException(UnittestException):
	pass


@export
class DuplicateTestcaseException(UnittestException):
	pass


@export
class TestcaseState(Flag):
	Unknown =    0
	Excluded =   1                         #: testcase was permanently excluded / disabled
	Skipped =    2                         #: testcase was temporarily skipped (e.g. based on a condition)
	Weak =       4                         #: no assertions
	Passed =     8                         #: passed testcase, because all assertions succeeded
	Failed =    16                         #: failed testcase due to failing assertions

	Mask = Excluded | Skipped | Weak | Passed | Failed

	Inverted = 128                         #: to mark inverted results
	UnexpectedPassed = Failed | Inverted
	ExpectedFailed =   Passed | Inverted

	Warned =  1024                         #: runtime warning
	Errored = 2048                         #: runtime error (mostly caught exceptions)
	Aborted = 4096                         #: uncaught runtime exception

	SetupError =     8192                  #: preparation / compilation error
	TearDownError = 16384                  #: cleanup error / resource release error

	Flags = Warned | Errored | Aborted | SetupError | TearDownError

	# TODO: timed out ?

	__MATRIX = (
	#  unknown  excluded  skipped  weak     passed   failed  < other / self vv
		(Unknown, Unknown,  Unknown, Unknown, Unknown, Unknown),       # unknown
		(Unknown, Excluded, Unknown, Unknown, Unknown, Unknown),       # excluded
		(Unknown, Unknown,  Skipped, Weak,    Passed,  Failed),        # skipped
		(Unknown, Unknown,  Unknown, Weak,    Unknown, Unknown),       # weak
		(Unknown, Unknown,  Passed,  Unknown, Passed,  Unknown),       # passed
		(Unknown, Unknown,  Failed,  Unknown, Unknown, Failed),        # failed
	)

	@classmethod
	def __conv(cls, value) -> int:
		try:
			return int(log2((value & cls.Mask).value)) + 1
		except ValueError:
			return 0

	def __matmul__(self, other: "TestcaseState") -> "TestcaseState":
		resolved = self.__class__(self.__MATRIX[self.__conv(self)][self.__conv(other)])
		resolved |= (self & self.Flags) | (other & self.Flags)
		return resolved


@export
class IterationScheme(Flag):
	Unknown =           0
	IncludeSelf =       1
	IncludeTestsuites = 2
	IncludeTestcases =  4

	PreOrder =         16
	PostOrder =        32

	Default =          IncludeTestsuites | IncludeTestcases | PreOrder
	TestsuiteDefault = IncludeTestsuites | PreOrder
	TestcaseDefault =  IncludeTestcases  | PreOrder


@export
class Base(metaclass=ExtendedType, slots=True):
	_parent: Nullable["Testsuite"]
	_name:   str
	_state:  TestcaseState

	_startTime:        datetime
	_setupDuration:    Nullable[timedelta]
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
		teardownDuration: Nullable[timedelta] = None,
		totalDuration:  Nullable[timedelta] = None,
		warningCount: int = 0,
		errorCount: int = 0,
		fatalCount: int = 0,
		parent: Nullable["Testsuite"] = None
	):
		if name is None:
			raise ValueError(f"Parameter 'name' is None.")
		elif not isinstance(name, str):
			raise TypeError(f"Parameter 'name' is not of type 'str'.")

		self._parent = parent
		self._name = name
		self._state = TestcaseState.Unknown

		self._startTime = startTime
		self._setupDuration = setupDuration
		self._teardownDuration = teardownDuration
		self._totalDuration = totalDuration

		self._warningCount = warningCount
		self._errorCount = errorCount
		self._fatalCount = fatalCount

		self._dict = {}

	@readonly
	def Parent(self) -> Nullable["Testsuite"]:
		return self._parent

	# QUESTION: allow Parent as setter?

	@readonly
	def Name(self) -> str:
		return self._name

	@readonly
	def State(self) -> TestcaseState:
		return self._state

	@readonly
	def StartTime(self) -> datetime:
		return self._startTime

	@readonly
	def SetupDuration(self) -> timedelta:
		return self._setupDuration

	@readonly
	def TeardownDuration(self) -> timedelta:
		return self._teardownDuration

	@readonly
	def TotalDuration(self) -> timedelta:
		return self._totalDuration

	@readonly
	def WarningCount(self) -> int:
		return self._warningCount

	@readonly
	def ErrorCount(self) -> int:
		return self._errorCount

	@readonly
	def FatalCount(self) -> int:
		return self._fatalCount

	def __len__(self) -> int:
		return len(self._dict)

	def __getitem__(self, key: str) -> Any:
		return self._dict[key]

	def __setitem__(self, key: str, value: Any) -> None:
		self._dict[key] = value

	def __delitem__(self, key: str) -> None:
		del self._dict[key]

	def __contains__(self, key: str) -> bool:
		return key in self._dict

	def __iter__(self) -> Generator[Tuple[str, Any], None, None]:
		yield from self._dict.items()

	@abstractmethod
	def Aggregate(self):
		pass


@export
class Testcase(Base):
	_testDuration:     Nullable[timedelta]

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
		assertionCount: Nullable[int] = None,
		failedAssertionCount: Nullable[int] = None,
		passedAssertionCount: Nullable[int] = None,
		warningCount: int = 0,
		errorCount: int = 0,
		fatalCount: int = 0,
		parent: Nullable["Testsuite"] = None
	):
		if parent is not None:
			if not isinstance(parent, Testsuite):
				raise TypeError(f"Parameter 'parent' is not of type 'Testsuite'.")

			parent._testcases[name] = self

		super().__init__(name, startTime, setupDuration, teardownDuration, totalDuration, warningCount, errorCount, fatalCount, parent)

		self._testDuration = testDuration
		# if totalDuration is not None:

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
	def TestDuration(self) -> timedelta:
		return self._testDuration

	@readonly
	def AssertionCount(self) -> int:
		return self._assertionCount

	@readonly
	def FailedAssertionCount(self) -> int:
		return self._failedAssertionCount

	@readonly
	def PassedAssertionCount(self) -> int:
		return self._passedAssertionCount

	def Aggregate(self, strict: bool = True) -> None:
		if self._state is not TestcaseState.Unknown:
			return

		if self._assertionCount is None or self._assertionCount == 0:
			self._state = TestcaseState.Weak | (TestcaseState.Failed if strict else TestcaseState.Passed)
		elif self._failedAssertionCount == 0:
			self._state = TestcaseState.Passed
		else:
			self._state = TestcaseState.Failed

		if self._warningCount > 0:
			self._state |= TestcaseState.Warned

		if self._errorCount > 0:
			self._state |= TestcaseState.Errored

		if self._fatalCount > 0:
			self._state |= TestcaseState.Aborted

			if strict:
				self._state = self._state & ~TestcaseState.Passed | TestcaseState.Failed

		# TODO: check for setup errors
		# TODO: check for teardown errors


@export
class TestsuiteBase(Base):
	_testsuites: Dict[str, "Testsuite"]

	_excluded: int
	_skipped:  int
	_errored:  int
	_failed:   int
	_passed:   int

	def __init__(
		self,
		name: str,
		startTime: Nullable[datetime] = None,
		setupDuration: Nullable[timedelta] = None,
		teardownDuration: Nullable[timedelta] = None,
		totalDuration:  Nullable[timedelta] = None,
		warningCount: int = 0,
		errorCount: int = 0,
		fatalCount: int = 0,
		testsuites: Nullable[Iterable["Testsuite"]] = None,
		parent: Nullable["Testsuite"] = None
	):
		if parent is not None:
			if not isinstance(parent, TestsuiteBase):
				raise TypeError(f"Parameter 'parent' is not of type 'TestsuiteBase'.")

			parent._testsuites[name] = self

		super().__init__(name, startTime, setupDuration, teardownDuration, totalDuration, warningCount, errorCount, fatalCount, parent)

		self._testsuites = {}
		if testsuites is not None:
			for testsuite in testsuites:
				if testsuite._parent is not None:
					raise ValueError(f"Testsuite '{testsuite._name}' is already part of a testsuite hierarchy.")

				if testsuite._name in self._testsuites:
					raise DuplicateTestsuiteException(f"Testsuite already contains a testsuite with same name '{testsuite._name}'.")

				testsuite._parent = self
				self._testsuites[testsuite._name] = testsuite

		self._excluded = 0
		self._skipped =  0
		self._errored =  0
		self._failed =   0
		self._passed =   0

	@readonly
	def Testsuites(self) -> Dict[str, "Testsuite"]:
		return self._testsuites

	@readonly
	def TestsuiteCount(self) -> int:
		return 1 + sum(testsuite.TestsuiteCount for testsuite in self._testsuites.values())

	@readonly
	def TestcaseCount(self) -> int:
		return sum(testsuite.TestcaseCount for testsuite in self._testsuites.values())

	@readonly
	def AssertionCount(self) -> int:
		raise NotImplementedError()
		# return self._assertionCount

	@readonly
	def FailedAssertionCount(self) -> int:
		raise NotImplementedError()
		# return self._assertionCount - (self._warningCount + self._errorCount + self._fatalCount)

	@readonly
	def PassedAssertionCount(self) -> int:
		raise NotImplementedError()
		# return self._assertionCount - (self._warningCount + self._errorCount + self._fatalCount)

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

	@readonly
	def Excluded(self) -> int:
		return self._excluded

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

	def Aggregate(self) -> Tuple[int, int, int, int, int, int, int, int, int]:
		tests = 0
		excluded = 0
		skipped = 0
		errored = 0
		failed = 0
		passed = 0
		warningCount = 0
		errorCount = 0
		fatalCount = 0

		for testsuite in self._testsuites.values():
			t, ex, s, e, f, p, wc, ec, fc = testsuite.Aggregate()
			tests += t
			excluded += ex
			skipped += s
			errored += e
			failed += f
			passed += p
			warningCount += wc
			errorCount += ec
			fatalCount += fc

		return tests, excluded, skipped, errored, failed, passed, warningCount, errorCount, fatalCount

	def AddTestsuite(self, testsuite: "Testsuite") -> None:
		if testsuite._parent is not None:
			raise ValueError(f"Testsuite '{testsuite._name}' is already part of a testsuite hierarchy.")

		if testsuite._name in self._testsuites:
			raise DuplicateTestsuiteException(f"Testsuite already contains a testsuite with same name '{testsuite._name}'.")

		testsuite._parent = self
		self._testsuites[testsuite._name] = testsuite

	def AddTestsuites(self, testsuites: Iterable["Testsuite"]) -> None:
		for testsuite in testsuites:
			self.AddTestsuite(testsuite)

	def AddTestcase(self, testcase: "Testcase") -> None:
		if testcase._parent is not None:
			raise ValueError(f"Testcase '{testcase._name}' is already part of a testsuite hierarchy.")

		if testcase._name in self._testcases:
			raise DuplicateTestcaseException(f"Testsuite already contains a testcase with same name '{testcase._name}'.")

		testcase._parent = self
		self._testcases[testcase._name] = testcase

	def AddTestcases(self, testcases: Iterable["Testcase"]) -> None:
		for testcase in testcases:
			self.AddTestcase(testcase)

	@mustoverride
	def Iterate(self, scheme: IterationScheme = IterationScheme.Default) -> Generator[Union["Testsuite", Testcase], None, None]:
		pass

	def IterateTestsuites(self, scheme: IterationScheme = IterationScheme.TestsuiteDefault) -> Generator["Testsuite", None, None]:
		return self.Iterate(scheme)

	def IterateTestcases(self, scheme: IterationScheme = IterationScheme.TestcaseDefault) -> Generator[Testcase, None, None]:
		return self.Iterate(scheme)


@export
class Testsuite(TestsuiteBase):
	_testcases:  Dict[str, "Testcase"]

	def __init__(
		self,
		name: str,
		startTime: Nullable[datetime] = None,
		setupDuration: Nullable[timedelta] = None,
		# testDuration: Nullable[timedelta] = None,
		teardownDuration: Nullable[timedelta] = None,
		totalDuration:  Nullable[timedelta] = None,
		warningCount: int = 0,
		errorCount: int = 0,
		fatalCount: int = 0,
		testsuites: Nullable[Iterable["Testsuite"]] = None,
		testcases: Nullable[Iterable["Testcase"]] = None,
		parent: Nullable["Testsuite"] = None
	):
		super().__init__(name, startTime, setupDuration, teardownDuration, totalDuration, warningCount, errorCount, fatalCount, testsuites, parent)

		# self._testDuration = testDuration

		self._testcases = {}
		if testcases is not None:
			for testcase in testcases:
				if testcase._parent is not None:
					raise ValueError(f"Testcase '{testcase._name}' is already part of a testsuite hierarchy.")

				if testcase._name in self._testcases:
					raise DuplicateTestcaseException(f"Testsuite already contains a testcase with same name '{testcase._name}'.")

				testcase._parent = self
				self._testcases[testcase._name] = testcase

	@readonly
	def Testcases(self) -> Dict[str, "Testcase"]:
		return self._testcases

	@readonly
	def TestcaseCount(self) -> int:
		return super().TestcaseCount + len(self._testcases)

	def Aggregate(self, strict: bool = True) -> Tuple[int, int, int, int, int, int, int, int, int]:
		tests, excluded, skipped, errored, failed, passed, warningCount, errorCount, fatalCount = super().Aggregate()

		for testcase in self._testcases.values():
			testcase.Aggregate(strict)
			if testcase._state is TestcaseState.Passed:
				tests += 1
				passed += 1
			elif testcase._state is TestcaseState.Failed:
				tests += 1
				failed += 1
			elif testcase._state is TestcaseState.Skipped:
				tests += 1
				skipped += 1
			elif testcase._state is TestcaseState.Excluded:
				tests += 1
				excluded += 1
			elif testcase._state is TestcaseState.Errored:
				tests += 1
				errored += 1
			elif testcase._state is TestcaseState.Unknown:
				raise UnittestException(f"Found testcase '{testcase._name}' with unknown state.")

			warningCount += testcase._warningCount
			errorCount +=   testcase._errorCount
			fatalCount +=   testcase._fatalCount

		self._excluded = excluded
		self._skipped = skipped
		self._errored = errored
		self._failed = failed
		self._passed = passed
		self._warningCount = warningCount
		self._errorCount = errorCount
		self._fatalCount = fatalCount

		if errored > 0:
			self._state = TestcaseState.Errored
		elif failed > 0:
			self._state = TestcaseState.Failed
		elif tests - skipped == passed:
			self._state = TestcaseState.Passed
		elif tests == skipped:
			self._state = TestcaseState.Skipped
		else:
			self._state = TestcaseState.Unknown

		return tests, excluded, skipped, errored, failed, passed, warningCount, errorCount, fatalCount

	def Iterate(self, scheme: IterationScheme = IterationScheme.Default) -> Generator[Union["Testsuite", Testcase], None, None]:
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


@export
class TestsuiteSummary(TestsuiteBase):
	def __init__(
		self,
		name: str,
		startTime: Nullable[datetime] = None,
		setupDuration: Nullable[timedelta] = None,
		teardownDuration: Nullable[timedelta] = None,
		totalDuration:  Nullable[timedelta] = None,
		warningCount: int = 0,
		errorCount: int = 0,
		fatalCount: int = 0,
		testsuites: Nullable[Iterable["Testsuite"]] = None,
		parent: Nullable["Testsuite"] = None
	):
		super().__init__(name, startTime, setupDuration, teardownDuration, totalDuration, warningCount, errorCount, fatalCount, testsuites, parent)

	def Aggregate(self) -> Tuple[int, int, int, int, int, int]:
		tests, excluded, skipped, errored, failed, passed, warningCount, errorCount, fatalCount = super().Aggregate()

		self._excluded = excluded
		self._skipped = skipped
		self._errored = errored
		self._failed = failed
		self._passed = passed
		self._warningCount = warningCount
		self._errorCount = errorCount
		self._fatalCount = fatalCount

		if errored > 0:
			self._state = TestcaseState.Errored
		elif failed > 0:
			self._state = TestcaseState.Failed
		elif tests - skipped == passed:
			self._state = TestcaseState.Passed
		elif tests == skipped:
			self._state = TestcaseState.Skipped
		elif tests == excluded:
			self._state = TestcaseState.Excluded
		else:
			self._state = TestcaseState.Unknown

		return tests, excluded, skipped, errored, failed, passed

	def Iterate(self, scheme: IterationScheme = IterationScheme.Default) -> Generator[Union["Testsuite", Testcase], None, None]:
		if IterationScheme.IncludeSelf | IterationScheme.IncludeTestsuites | IterationScheme.PreOrder in scheme:
			yield self

		for testsuite in self._testsuites.values():
			yield from testsuite.IterateTestsuites(scheme | IterationScheme.IncludeSelf)

		if IterationScheme.IncludeSelf | IterationScheme.IncludeTestsuites | IterationScheme.PostOrder in scheme:
			yield self


@export
class Merged(metaclass=ExtendedType, mixin=True):
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
		name: str,
		startTime: Nullable[datetime] = None,
		setupDuration: Nullable[timedelta] = None,
		testDuration: Nullable[timedelta] = None,
		teardownDuration: Nullable[timedelta] = None,
		totalDuration:  Nullable[timedelta] = None,
		assertionCount: Nullable[int] = None,
		failedAssertionCount: Nullable[int] = None,
		passedAssertionCount: Nullable[int] = None,
		warningCount: int = 0,
		errorCount: int = 0,
		fatalCount: int = 0,
		parent: Nullable["Testsuite"] = None
	):
		super().__init__(
			name,
			startTime, setupDuration, testDuration, teardownDuration, totalDuration,
			assertionCount, failedAssertionCount, passedAssertionCount,
			warningCount, errorCount, fatalCount,
			parent
		)
		Merged.__init__(self)

		self._mergedTestcases = []

	def Merge(self, tc: Testcase) -> None:
		self._mergedCount += 1

		self._mergedTestcases.append(tc)

		self._warningCount += tc._warningCount
		self._errorCount += tc._errorCount
		self._fatalCount += tc._fatalCount

	def Copy(self, tc: Testcase) -> None:
		pass

	@readonly
	def State(self) -> TestcaseState:
		result = self._mergedTestcases[0]._state
		for state in (tc._state for tc in self._mergedTestcases):
			result @= state

		return result

	@readonly
	def SummedAssertionCount(self) -> int:
		return sum(tc._assertionCount for tc in self._mergedTestcases)

	@readonly
	def SummedPassedAssertionCount(self) -> int:
		return sum(tc._passedAssertionCount for tc in self._mergedTestcases)

	@readonly
	def SummedFailedAssertionCount(self) -> int:
		return sum(tc._failedAssertionCount for tc in self._mergedTestcases)


@export
class MergedTestsuite(Testsuite, Merged):
	def __init__(
		self,
		name: str,
		startTime: Nullable[datetime] = None,
		setupDuration: Nullable[timedelta] = None,
		# testDuration: Nullable[timedelta] = None,
		teardownDuration: Nullable[timedelta] = None,
		totalDuration:  Nullable[timedelta] = None,
		warningCount: int = 0,
		errorCount: int = 0,
		fatalCount: int = 0,
		testsuites: Nullable[Iterable["Testsuite"]] = None,
		testcases: Nullable[Iterable["Testcase"]] = None,
		parent: Nullable["Testsuite"] = None
	):
		super().__init__(
			name,
			# startTime, setupDuration, testDuration, teardownDuration, totalDuration,
			startTime, setupDuration, teardownDuration, totalDuration,
			warningCount, errorCount, fatalCount,
			testsuites, testcases,
			parent
		)
		Merged.__init__(self)

	def Merge(self, ts: Testsuite) -> None:
		self._mergedCount += 1

		for testsuite in ts._testsuites.values():
			try:
				mergedTestsuite: MergedTestsuite = self._testsuites[testsuite._name]
				mergedTestsuite.Merge(testsuite)
			except KeyError:
				mergedTestsuite = MergedTestsuite(
					testsuite._name,
					testsuite._startTime,
					testsuite._setupDuration,
					testsuite._teardownDuration,
					testsuite._totalDuration,
					testsuite._warningCount,
					testsuite._errorCount,
					testsuite._fatalCount,
					parent=self
				)
				mergedTestsuite.Copy(testsuite)

		for testcase in ts._testcases.values():
			try:
				mergedTestcase: MergedTestcase = self._testcases[testcase._name]
				mergedTestcase.Merge(testcase)
			except KeyError:
				mergedTestcase = MergedTestcase(
				testcase._name,
				testcase._startTime,
				testcase._setupDuration,
				testcase._testDuration,
				testcase._teardownDuration,
				testcase._totalDuration,
				testcase._assertionCount,
				testcase._failedAssertionCount,
				testcase._passedAssertionCount,
				testcase._warningCount,
				testcase._errorCount,
				testcase._fatalCount,
				parent=self
				)
				mergedTestcase.Copy(testcase)

	def Copy(self, ts: Testsuite) -> None:
		for testsuite in ts._testsuites.values():
			mergedTestsuite = MergedTestsuite(
					testsuite._name,
					testsuite._startTime,
					testsuite._setupDuration,
					testsuite._teardownDuration,
					testsuite._totalDuration,
					testsuite._warningCount,
					testsuite._errorCount,
					testsuite._fatalCount,
					parent=self
			)
			mergedTestsuite.Copy(testsuite)

		for testcase in ts._testcases.values():
			mergedTestcase = MergedTestcase(
				testcase._name,
				testcase._startTime,
				testcase._setupDuration,
				testcase._testDuration,
				testcase._teardownDuration,
				testcase._totalDuration,
				testcase._assertionCount,
				testcase._failedAssertionCount,
				testcase._passedAssertionCount,
				testcase._warningCount,
				testcase._errorCount,
				testcase._fatalCount,
				parent=self
			)
			mergedTestcase.Copy(testcase)


@export
class MergedTestsuiteSummary(TestsuiteSummary, Merged):
	_mergedFiles: Dict[Path, TestsuiteSummary]

	def __init__(self, name: str) -> None:
		super().__init__(name)
		Merged.__init__(self, mergedCount=0)

		self._mergedFiles = {}

	def Merge(self, summary: TestsuiteSummary) -> None:
		# if summary.File in self._mergedFiles:
		# 	raise

		self._mergedCount += 1
		self._mergedFiles[summary.Name] = summary

		for testsuite in summary._testsuites.values():
			try:
				mergedTestsuite: MergedTestsuite = self._testsuites[testsuite._name]
				mergedTestsuite.Merge(testsuite)
			except KeyError:
				mergedTestsuite = MergedTestsuite(
					testsuite._name,
					testsuite._startTime,
					testsuite._setupDuration,
					testsuite._teardownDuration,
					testsuite._totalDuration,
					testsuite._warningCount,
					testsuite._errorCount,
					testsuite._fatalCount,
					parent=self
				)
				mergedTestsuite.Copy(testsuite)

	def Aggregate(self) -> None:
		pass
