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
dialect's writer meets another dialect's reader. Where a conversion cannot work today, the pair is listed in
:data:`KNOWN_GAPS` with the reason and asserted to *keep* failing, so that fixing one shows up here as a failing
expectation rather than passing unnoticed.
"""
from typing   import ClassVar, Dict, Tuple
from unittest import TestCase as ut_TestCase

from . import DIALECTS, OUTPUT_DIRECTORY, Dialect, readReference, writeAs


#: (source dialect, target dialect) -> why the conversion does not work yet.
KNOWN_GAPS: Dict[Tuple[str, str], str] = {
	("pyTest-JUnit", "CTest-JUnit"):
		"The CTest writer emits a <testsuite> that CTest-JUnit.xsd rejects.",
	("pyTest-JUnit", "GoogleTest-JUnit"):
		"The GoogleTest writer emits a <testsuites> that GoogleTest-JUnit.xsd rejects.",
	("Any-JUnit", "Ant-JUnit4"):
		"Ant + JUnit4 holds exactly one test suite, and the OSVVM report has many. A format limit, not a defect.",
	("Any-JUnit", "CTest-JUnit"):
		"CTest-JUnit holds exactly one test suite, and the OSVVM report has many. A format limit, not a defect.",
	("Any-JUnit", "GoogleTest-JUnit"):
		"The GoogleTest writer calls isoformat() on a timestamp the OSVVM report does not have.",
	("Any-JUnit", "pyTest-JUnit"):
		"The pyTest reader requires a timestamp, and the OSVVM report has none to carry over.",
}


class Translation(ut_TestCase):
	"""Base class: a report of this dialect is converted into every dialect, and read back in that dialect."""

	_dialectName: ClassVar[str] = None

	def setUp(self) -> None:
		if self._dialectName is None:
			self.skipTest("Base class: it describes the checks, the derived classes name the dialect.")

	@property
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
		Convert into the named dialect, or assert that a known gap is still a gap.

		:param targetName: Name of the dialect to convert to.
		"""
		target = DIALECTS[targetName]
		reason = KNOWN_GAPS.get((self._dialectName, targetName))

		if reason is None:
			self._convert(target)
		else:
			with self.assertRaises(Exception, msg=f"This conversion works now: {reason}"):
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


class FromAntJUnit4(Translation):
	_dialectName = "Ant-JUnit4"


class FromCTestJUnit(Translation):
	_dialectName = "CTest-JUnit"


class FromGoogleTestJUnit(Translation):
	_dialectName = "GoogleTest-JUnit"


class FromPyTestJUnit(Translation):
	_dialectName = "pyTest-JUnit"


class FromAnyJUnit(Translation):
	_dialectName = "Any-JUnit"
