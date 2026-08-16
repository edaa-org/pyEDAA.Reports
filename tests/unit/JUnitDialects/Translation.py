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
Converting a report of one dialect into another.

This is what ``pyedaa-reports unittest --merge=<dialect>:... --output=<dialect>:...`` does, and it is where a
dialect's writer meets another dialect's reader. Where a target format cannot express a report - it needs data the
source never carried, or holds only one test suite - the pair is listed in :data:`FORMAT_LIMITS` with the reason and
asserted to *keep* failing, so that lifting a limit shows up here rather than passing unnoticed.
"""
from typing   import ClassVar, Dict, Tuple
from unittest import TestCase as ut_TestCase

from pyTooling.Decorators import readonly
from pyTooling.MetaClasses import ExtendedType

from . import DIALECTS, OUTPUT_DIRECTORY, Dialect, readReference, writeAs


#: (source dialect, target dialect) -> why the target format cannot express this report.
#:
#: These are limits of the formats, not defects: a dialect whose schema requires a timestamp cannot be written from
#: a report that carries none, and a dialect holding exactly one test suite cannot hold many. Every entry names the
#: data the target needs and the source lacks. A conversion that fails for any *other* reason is a defect and has
#: no place here.
FORMAT_LIMITS: Dict[Tuple[str, str], str] = {
	("pyTest-JUnit", "CTest-JUnit"):
		"CTest-JUnit requires 'timestamp' on <testsuite>. pytest writes none on <testsuites>, so the summary has no "
		"start time to carry over.",
	("pyTest-JUnit", "GoogleTest-JUnit"):
		"GoogleTest-JUnit requires 'timestamp' on <testsuites>, which pytest does not write.",
	("Any-JUnit", "Ant-JUnit4"):
		"Ant + JUnit4 holds exactly one test suite; the OSVVM report has many.",
	("Any-JUnit", "CTest-JUnit"):
		"CTest-JUnit holds exactly one test suite; the OSVVM report has many.",
	("Any-JUnit", "GoogleTest-JUnit"):
		"GoogleTest-JUnit requires 'timestamp' down to <testcase>; the OSVVM report has none.",
	("Any-JUnit", "pyTest-JUnit"):
		"pyTest-JUnit requires 'timestamp' on <testsuite>; the OSVVM report has none.",
}


class TranslationMixin(metaclass=ExtendedType):
	"""Base class: a report of this dialect is converted into every dialect, and read back in that dialect."""

	_dialectName: ClassVar[str]

	@readonly
	def Dialect(self) -> Dialect:
		"""
		Read-only property to return the source dialect, looked up by :attr:`_dialectName`.

		:returns: The dialect the report is read with.
		"""
		return DIALECTS[self._dialectName]

	def _convert(self, target: Dialect) -> None:
		"""
		Read this dialect's reference report, write it as the target dialect, validate it and read it back.

		:param target: The dialect to convert to.
		"""
		source = self.Dialect
		summary = readReference(source, source.ReferenceFiles[0])
		outputFile = writeAs(target, summary, OUTPUT_DIRECTORY / "Translation" / f"{source.Name}-to-{target.Name}.xml")
		target.Schema().validate(str(outputFile))
		target.DocumentClass(outputFile, analyzeAndConvert=True)

	def _translate(self, targetName: str) -> None:
		"""
		Convert into the named dialect, or assert that a format limit still stands.

		:param targetName: Name of the dialect to convert to.
		"""
		target = DIALECTS[targetName]
		reason = FORMAT_LIMITS.get((self._dialectName, targetName))

		if reason is None:
			self._convert(target)
		else:
			with self.assertRaises(Exception, msg=f"This conversion works now, so the limit is gone: {reason}"):
				self._convert(target)

	def test_ToAntJUnit4(self) -> None:
		self._translate("Ant-JUnit4")

	def test_ToCTestJUnit(self) -> None:
		self._translate("CTest-JUnit")

	def test_ToGoogleTestJUnit(self) -> None:
		self._translate("GoogleTest-JUnit")

	def test_ToPyTestJUnit(self) -> None:
		self._translate("pyTest-JUnit")

	def test_ToAnyJUnit(self) -> None:
		self._translate("Any-JUnit")


class FromAntJUnit4(TranslationMixin, ut_TestCase):
	_dialectName = "Ant-JUnit4"


class FromCTestJUnit(TranslationMixin, ut_TestCase):
	_dialectName = "CTest-JUnit"


class FromGoogleTestJUnit(TranslationMixin, ut_TestCase):
	_dialectName = "GoogleTest-JUnit"


class FromPyTestJUnit(TranslationMixin, ut_TestCase):
	_dialectName = "pyTest-JUnit"


class FromAnyJUnit(TranslationMixin, ut_TestCase):
	_dialectName = "Any-JUnit"
