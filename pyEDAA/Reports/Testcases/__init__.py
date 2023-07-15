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
# Copyright 2021-2023 Electronic Design Automation Abstraction (EDA²)                                                  #
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
"""Abstraction of testsuits and testcases."""
from enum import Enum
from typing import Dict, Iterator

from pyTooling.Decorators import export


@export
class Status(Enum):
	Passed = 0
	Failed = 1
	XFailed = 2
	Skipped = 3


@export
class Base:
	pass


@export
class Parameter(Base):
	_name: str


@export
class Testsuite(Base):
	_name: str
	_testsuites: Dict[str, 'Testsuite']
	_testcases:  Dict[str, 'Testcase']

	def __init__(self, name: str):
		self._name = name
		self._testsuites = {}
		self._testcases = {}

	@property
	def Name(self) -> str:
		return self._name

	@property
	def AssertionCount(self) -> int:
		raise NotImplementedError()
		# return self._assertionCount

	@property
	def PassedCount(self) -> int:
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


@export
class Testcase(Base):
	_name: str
	_subtests:  Dict[str, 'Subtest']
	_assertionCount: int
	_warningCount: int
	_errorCount: int
	_fatalCount: int

	def __init__(self, name: str, assertionCount: int, warningCount: int, errorCount: int, fatalCount: int):
		self._name = name
		self._subtests = {}

		self._assertionCount = assertionCount
		self._warningCount = warningCount
		self._errorCount = errorCount
		self._fatalCount = fatalCount

	@property
	def Name(self) -> str:
		return self._name

	@property
	def AssertionCount(self) -> int:
		return self._assertionCount

	@property
	def PassedCount(self) -> int:
		return self._assertionCount - (self._warningCount + self._errorCount + self._fatalCount)

	@property
	def WarningCount(self) -> int:
		return self._warningCount

	@property
	def ErrorCount(self) -> int:
		return self._errorCount

	@property
	def FatalCount(self) -> int:
		return self._fatalCount


@export
class Subtest(Base):
	_name: str
