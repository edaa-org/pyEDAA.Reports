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
from datetime import timedelta

from enum   import Flag
from typing import Dict, Iterator, Optional as Nullable, Iterable, Any

from pyTooling.Decorators  import export
from pyTooling.MetaClasses import abstractmethod, ExtendedType

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
class Status(Flag):
	Unknown = 0
	Skipped = 1
	Passed = 2
	Failed = 4
	UnexpectedPassed = 10
	ExpectedFailed = 12
	Errored = 16


@export
class Base(metaclass=ExtendedType, slots=True):
	_parent: Nullable["Testsuite"]
	_name:   str
	_status: Status

	def __init__(self, name: str, parent: Nullable["Testsuite"] = None):
		if name is None:
			raise TypeError(f"Parameter 'name' must not be None.")

		self._parent = parent
		self._name = name
		self._status = Status.Unknown

	@property
	def Parent(self) -> Nullable["Testsuite"]:
		return self._parent

	@property
	def Name(self) -> str:
		return self._name

	@property
	def Status(self) -> Status:
		return self._status

	@abstractmethod
	def Aggregate(self):
		pass


@export
class Testsuite(Base):
	_testsuites: Dict[str, "Testsuite"]
	_testcases:  Dict[str, "Testcase"]

	def __init__(
		self,
		name: str,
		testsuites: Nullable[Iterable["Testsuite"]] = None,
		testcases: Nullable[Iterable["Testcase"]] = None,
		parent: Nullable["Testsuite"] = None):
		super().__init__(name, parent)

		self._testsuites = {}
		if testsuites is not None:
			for testsuite in testsuites:
				if testsuite._parent is not None:
					raise ValueError(f"Testsuite '{testsuite._name}' is already part of a testsuite hierarchy.")

				if testsuite._name in self._testsuites:
					raise DuplicateTestsuiteException(f"Testsuite already contains a testsuite with same name '{testsuite._name}'.")

				testsuite._parent = self
				self._testsuites[testsuite._name] = testsuite

		self._testcases = {}
		if testcases is not None:
			for testcase in testcases:
				if testcase._parent is not None:
					raise ValueError(f"Testcase '{testcase._name}' is already part of a testsuite hierarchy.")

				if testcase._name in self._testcases:
					raise DuplicateTestcaseException(f"Testsuite already contains a testcase with same name '{testcase._name}'.")

				testcase._parent = self
				self._testcases[testcase._name] = testcase

	@property
	def Testsuites(self) -> Dict[str, "Testsuite"]:
		return self._testsuites

	@property
	def Testcases(self) -> Dict[str, "Testcase"]:
		return self._testcases

	@property
	def AssertionCount(self) -> int:
		raise NotImplementedError()
		# return self._assertionCount

	@property
	def FailedAssertionCount(self) -> int:
		raise NotImplementedError()
		# return self._assertionCount - (self._warningCount + self._errorCount + self._fatalCount)

	@property
	def PassedAssertionCount(self) -> int:
		raise NotImplementedError()
		# return self._assertionCount - (self._warningCount + self._errorCount + self._fatalCount)

	@property
	def WarningCount(self) -> int:
		raise NotImplementedError()
		# return self._warningCount

	@property
	def ErrorCount(self) -> int:
		raise NotImplementedError()
		# return self._errorCount

	@property
	def FatalCount(self) -> int:
		raise NotImplementedError()
		# return self._fatalCount

	def __contains__(self, key: str) -> bool:
		return key in self._testcases

	def __iter__(self) -> Iterator["Testcase"]:
		return iter(self._testcases.values())

	def __getitem__(self, key: str) -> "Testcase":
		return self._testcases[key]

	def __len__(self) -> int:
		return self._testcases.__len__()

	def Aggregate(self) -> None:
		for testsuite in self._testsuites.values():
			testsuite.Aggregate()
		for testcase in self._testcases.values():
			testcase.Aggregate()

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


@export
class Testcase(Base):
	_setupDuration:    Nullable[timedelta]
	_testDuration:     Nullable[timedelta]
	_teardownDuration: Nullable[timedelta]
	_totalDuration:    Nullable[timedelta]

	_assertionCount:       Nullable[int]
	_failedAssertionCount: Nullable[int]
	_passedAssertionCount: Nullable[int]

	_warningCount: int
	_errorCount:   int
	_fatalCount:   int

	_dict:         Dict[str, Any]

	def __init__(
		self,
		name: str,
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
		super().__init__(name, parent)

		self._setupDuration = setupDuration
		self._testDuration = testDuration
		self._teardownDuration = teardownDuration
		self._totalDuration = totalDuration
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

		self._warningCount = warningCount
		self._errorCount = errorCount
		self._fatalCount = fatalCount

	@property
	def AssertionCount(self) -> int:
		return self._assertionCount

	@property
	def FailedAssertionCount(self) -> int:
		return self._failedAssertionCount

	@property
	def PassedAssertionCount(self) -> int:
		return self._passedAssertionCount

	@property
	def WarningCount(self) -> int:
		return self._warningCount

	@property
	def ErrorCount(self) -> int:
		return self._errorCount

	@property
	def FatalCount(self) -> int:
		return self._fatalCount

	def Aggregate(self) -> None:
		pass
