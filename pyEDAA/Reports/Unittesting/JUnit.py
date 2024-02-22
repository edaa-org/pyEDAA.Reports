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
from enum            import Flag
from datetime        import datetime, timedelta
from pathlib         import Path
from time            import perf_counter_ns
from typing          import Tuple, Dict, Optional as Nullable, Union
from xml.dom         import minidom, Node
from xml.dom.minidom import Element

from pyTooling.Decorators  import export, readonly
from pyTooling.MetaClasses import ExtendedType

from pyEDAA.Reports.Unittesting import UnittestException, DuplicateTestsuiteException, DuplicateTestcaseException
from pyEDAA.Reports.Unittesting import Testsuite as gen_Testsuite, Testcase as gen_Testcase


@export
class JUnitException:
	pass


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
class TestcaseState(Flag):
	Unknown = 0
	Failed =  1
	Error =   2
	Skipped = 4
	Passed =  8


@export
class Base(metaclass=ExtendedType, slots=True):
	_parent: Nullable["TestsuiteBase"]
	_name:   str
	_state:  TestcaseState
	_time:   timedelta

	def __init__(self, name: str, time: timedelta, parent: Nullable["TestsuiteBase"] = None) -> None:
		self._parent = parent
		self._name = name
		self._state = TestcaseState.Unknown
		self._time = time

	@readonly
	def Parent(self) -> Nullable["TestsuiteBase"]:
		return self._parent

	# QUESTION: allow Parent as setter?

	@readonly
	def Name(self) -> str:
		return self._name

	@readonly
	def State(self) -> TestcaseState:
		return self._state

	@readonly
	def Time(self) -> timedelta:
		return self._time


@export
class Testcase(Base):
	_assertions: int

	def __init__(self, name: str, time: timedelta, parent: Nullable["Testsuite"] = None) -> None:
		if parent is not None:
			if not isinstance(parent, TestsuiteBase):
				raise UnittestException(f"Parameter 'parent' is not of type TestsuiteBase.")

			parent._testcases[name] = self

		super().__init__(name, time, parent)

		self._assertions = 0

	@readonly
	def Assertions(self) -> int:
		return self._assertions


@export
class TestsuiteBase(Base):
	_testsuites: Dict[str, "Testsuite"]

	_tests:   int
	_skipped: int
	_errored: int
	_failed:  int
	_passed:  int

	def __init__(self, name: str, time: timedelta, parent: Nullable["TestsuiteBase"] = None) -> None:
		if parent is not None:
			if not isinstance(parent, TestsuiteBase):
				raise UnittestException(f"Parameter 'parent' is not of type TestsuiteBase.")

			parent._testsuites[name] = self

		super().__init__(name, time, parent)

		self._testsuites = {}

		self._tests =   0
		self._skipped = 0
		self._errored = 0
		self._failed =  0
		self._passed =  0

	def __getitem__(self, key: str) -> "Testsuite":
		return self._testsuites[key]

	def __contains__(self, key: str) -> bool:
		return key in self._testsuites

	@readonly
	def Testsuites(self) -> Dict[str, "Testsuite"]:
		return self._testsuites

	@readonly
	def Tests(self) -> int:
		return self._tests

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

	def Aggregate(self) -> Tuple[int, int, int, int, int]:
		tests = 0
		skipped = 0
		errored = 0
		failed = 0
		passed = 0

		for testsuite in self._testsuites.values():
			t, s, e, f, p = testsuite.Aggregate()
			tests += t
			skipped += s
			errored += e
			failed += f
			passed += p

		return tests, skipped, errored, failed, passed


@export
class Testsuite(TestsuiteBase):
	_testcases:  Dict[str, Testcase]

	def __init__(self, name: str, time: timedelta, parent: Nullable["Base"] = None) -> None:
		super().__init__(name, time, parent)

		self._testcases = {}

	def __getitem__(self, key: str) -> Union["Testsuite", Testcase]:
		try:
			return self._testsuites[key]
		except KeyError:
			return self._testcases[key]

	def __contains__(self, key: str) -> bool:
		if key not in self._testsuites:
			return key in self._testcases

		return False

	@readonly
	def Testcases(self) -> Dict[str, Testcase]:
		return self._testcases

	def Aggregate(self) -> Tuple[int, int, int, int, int]:
		tests, skipped, errored, failed, passed = super().Aggregate()

		for testcase in self._testcases.values():
			if testcase._state is TestcaseState.Passed:
				tests += 1
				passed += 1
			elif testcase._state is TestcaseState.Failed:
				tests += 1
				failed += 1
			elif testcase._state is TestcaseState.Skipped:
				tests += 1
				skipped += 1
			elif testcase._state is TestcaseState.Error:
				tests += 1
				errored += 1
			elif testcase._state is TestcaseState.Unknown:
				raise UnittestException(f"Found testcase '{testcase._name}' with unknown state.")

		self._tests = tests
		self._skipped = skipped
		self._errored = errored
		self._failed = failed
		self._passed = passed

		if errored > 0:
			self._state = TestcaseState.Error
		elif failed > 0:
			self._state = TestcaseState.Failed
		elif tests - skipped == passed:
			self._state = TestcaseState.Passed
		elif tests == skipped:
			self._state = TestcaseState.Skipped
		else:
			self._state = TestcaseState.Unknown

		return tests, skipped, errored, failed, passed


@export
class TestsuiteSummary(TestsuiteBase):
	def __init__(self, name: str, time: timedelta):
		super().__init__(name, time)

	def Aggregate(self) -> Tuple[int, int, int, int, int]:
		tests, skipped, errored, failed, passed = super().Aggregate()

		self._tests = tests
		self._skipped = skipped
		self._errored = errored
		self._failed = failed
		self._passed = passed

		if errored > 0:
			self._state = TestcaseState.Error
		elif failed > 0:
			self._state = TestcaseState.Failed
		elif tests - skipped == passed:
			self._state = TestcaseState.Passed
		elif tests == skipped:
			self._state = TestcaseState.Skipped
		else:
			self._state = TestcaseState.Unknown

		return tests, skipped, errored, failed, passed

	def ConvertToGeneric(self) -> gen_Testsuite:
		def convertTestsuite(testsuite: Testsuite) -> gen_Testsuite:
			newTestsuite = gen_Testsuite(testsuite._name)

			for testsuite in testsuite._testsuites.values():
				newTestsuite.AddTestsuite(convertTestsuite(testsuite))

			for testcase in testsuite._testcases.values():
				newTestsuite.AddTestcase(gen_Testcase(testcase._name))

			return newTestsuite

		rootTS = gen_Testsuite(self._name)

		for testsuite in self._testsuites.values():
			rootTS.AddTestsuite(convertTestsuite(testsuite))

		return rootTS


@export
class Document(TestsuiteSummary):
	_path:             Path
	_documentElement:  Element

	_readingByMiniDom: float  #: TODO: replace by Timer; should be timedelta?
	_modelConversion:  float  #: TODO: replace by Timer; should be timedelta?

	def __init__(self, path: Path):
		if not path.exists():
			raise UnittestException(f"JUnit XML file '{path}' does not exist.") from FileNotFoundError(f"File '{path}' not found.")

		self._path = path

		try:
			startMiniDom = perf_counter_ns()
			rootElement = minidom.parse(str(path)).documentElement
			endMiniDom = perf_counter_ns()
		except Exception as ex:
			raise UnittestException(f"Couldn't open '{path}'.") from ex

		self._documentElement = rootElement
		self._readingByMiniDom = (endMiniDom - startMiniDom) / 1e9

		startConversion = perf_counter_ns()
		name = rootElement.getAttribute("name") if rootElement.hasAttribute("name") else "root"
		testsuiteRuntime = float(rootElement.getAttribute("time")) if rootElement.hasAttribute("time") else -1.0
		timestamp = datetime.fromisoformat(rootElement.getAttribute("timestamp")) if rootElement.hasAttribute("timestamp") else None

		super().__init__(name, timedelta(seconds=testsuiteRuntime))

		tests = rootElement.getAttribute("tests")
		skipped = rootElement.getAttribute("skipped")
		errors = rootElement.getAttribute("errors")
		failures = rootElement.getAttribute("failures")
		assertions = rootElement.getAttribute("assertions")

		for rootNode in rootElement.childNodes:
			if rootNode.nodeName == "testsuite":
				self._ParseTestsuite(rootNode)

		self.Aggregate()
		endConversation = perf_counter_ns()
		self._modelConversion = (endConversation - startConversion) / 1e9

	def _ParseTestsuite(self, testsuitesNode: Element) -> None:
		for node in testsuitesNode.childNodes:
			if node.nodeType == Node.ELEMENT_NODE:
				if node.tagName == "testsuite":
					self._ParseTestsuite(node)
				elif node.tagName == "testcase":
					self._ParseTestcase(node)

	def _ParseTestcase(self, testsuiteNode: Element) -> None:
		className = testsuiteNode.getAttribute("classname")
		name = testsuiteNode.getAttribute("name")
		time = float(testsuiteNode.getAttribute("time"))

		concurrentSuite = self

		testsuitePath = className.split(".")
		for testsuiteName in testsuitePath:
			try:
				concurrentSuite = concurrentSuite[testsuiteName]
			except KeyError:
				new = Testsuite(testsuiteName, timedelta(seconds=time))
				concurrentSuite._testsuites[testsuiteName] = new
				concurrentSuite = new

		testcase = Testcase(name, timedelta(seconds=time))
		concurrentSuite._testcases[name] = testcase

		for node in testsuiteNode.childNodes:
			if node.nodeType == Node.ELEMENT_NODE:
				if node.tagName == "skipped":
					testcase._state = TestcaseState.Skipped
				elif node.tagName == "failure":
					testcase._state = TestcaseState.Failed
				elif node.tagName == "error":
					testcase._state = TestcaseState.Error
				elif node.tagName == "system-out":
					pass
				elif node.tagName == "system-err":
					pass
				elif node.tagName == "properties":
					pass
				else:
					raise UnittestException(f"Unknown element '{node.tagName}' in junit file.")

		if testcase._state is TestcaseState.Unknown:
			testcase._state = TestcaseState.Passed
