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
Reading a report, writing it out again and reading the result: the dialects have to survive their own output.

A round trip is where a writer and a reader that disagree about the format show up - the merge pipelines in CI do
exactly this, twice.
"""
from typing   import ClassVar
from unittest import TestCase as ut_TestCase

from . import DIALECTS, OUTPUT_DIRECTORY, Dialect, collectTestcaseNames, countTestcases, readReference, writeAs


class RoundTrip(ut_TestCase):
	"""Base class: a report of this dialect is read, written and read back."""

	_dialectName: ClassVar[str] = None

	def setUp(self) -> None:
		if self._dialectName is None:
			self.skipTest("Base class: it describes the checks, the derived classes name the dialect.")

	@property
	def Dialect(self) -> Dialect:
		"""
		Read-only property to return the dialect under test, looked up by :attr:`_dialectName`.

		:returns: The dialect under test.
		"""
		return DIALECTS[self._dialectName]

	def _roundTrip(self, referenceFile):
		"""
		Read a reference report, write it in the same dialect and read that back.

		:param referenceFile: The reference report to round trip.
		:returns:             A tuple of the summary read first, the file written, and the summary read back.
		"""
		dialect = self.Dialect
		summary = readReference(dialect, referenceFile)
		outputFile = writeAs(dialect, summary, OUTPUT_DIRECTORY / dialect.Name / referenceFile.name)
		rereadSummary = readReference(dialect, outputFile)

		return summary, outputFile, rereadSummary

	def test_WrittenReportIsValid(self) -> None:
		schema = self.Dialect.Schema()

		for referenceFile in self.Dialect.ReferenceFiles:
			with self.subTest(file=referenceFile.name):
				_, outputFile, _ = self._roundTrip(referenceFile)
				schema.validate(str(outputFile))

	def test_TestcaseCountSurvives(self) -> None:
		for referenceFile in self.Dialect.ReferenceFiles:
			with self.subTest(file=referenceFile.name):
				summary, _, rereadSummary = self._roundTrip(referenceFile)
				self.assertEqual(countTestcases(summary), countTestcases(rereadSummary))

	def test_TestcaseNamesSurvive(self) -> None:
		for referenceFile in self.Dialect.ReferenceFiles:
			with self.subTest(file=referenceFile.name):
				summary, _, rereadSummary = self._roundTrip(referenceFile)
				self.assertEqual(collectTestcaseNames(summary), collectTestcaseNames(rereadSummary))

	def test_HostnameSurvives(self) -> None:
		for referenceFile in self.Dialect.ReferenceFiles:
			with self.subTest(file=referenceFile.name):
				summary, _, rereadSummary = self._roundTrip(referenceFile)
				before = {ts._name: ts._hostname for ts in summary._testsuites.values()}
				after = {ts._name: ts._hostname for ts in rereadSummary._testsuites.values()}
				self.assertEqual(before, after)


class AntJUnit4(RoundTrip):
	_dialectName = "Ant-JUnit4"


class CTestJUnit(RoundTrip):
	_dialectName = "CTest-JUnit"


class GoogleTestJUnit(RoundTrip):
	_dialectName = "GoogleTest-JUnit"


class PyTestJUnit(RoundTrip):
	_dialectName = "pyTest-JUnit"


class AnyJUnit(RoundTrip):
	_dialectName = "Any-JUnit"
