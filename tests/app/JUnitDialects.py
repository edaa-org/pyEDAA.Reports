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
The dialect conversion matrix, driven through the command line.

The unit tests exercise the readers and writers directly; this module runs ``pyedaa-reports`` as a user does, so
the chain under test includes the argument parsing, the dialect dispatch, the console-script wiring and the exit
codes. The two matrices are deliberately the same shape: a difference between them is a defect in the layer this
module adds.
"""
from pathlib   import Path
from typing    import ClassVar, Dict, Tuple

from pyTooling.Testing import ApplicationTestcaseMixin
from unittest          import TestCase
from xmlschema         import XMLSchema

from ..unit.JUnitDialects import DIALECTS, SCHEMA_DIRECTORY


OUTPUT_DIRECTORY = Path("tests/output/AppJUnitDialects")

#: The command line spells a dialect ``<dialect>-JUnit``, and its vocabulary is not the one the documents use:
#: ``Ant-JUnit4`` and ``GoogleTest-JUnit`` are not accepted there.
COMMANDLINE_NAMES: Dict[str, str] = {
	"Ant-JUnit4":       "Ant-JUnit",
	"Any-JUnit":        "Any-JUnit",
	"CTest-JUnit":      "CTest-JUnit",
	"GoogleTest-JUnit": "gtest-JUnit",
	"pyTest-JUnit":     "pyTest-JUnit",
}

#: Dialects the command line can write. ``Any-JUnit`` is readable but has no branch in ``_output``.
WRITABLE = ("Ant-JUnit4", "CTest-JUnit", "GoogleTest-JUnit", "pyTest-JUnit")

#: (source, target) -> why the conversion cannot work, mirroring the unit-level table.
FORMAT_LIMITS: Dict[Tuple[str, str], str] = {
	("pyTest-JUnit", "CTest-JUnit"):
		"CTest-JUnit requires 'timestamp' on <testsuite>, which pytest does not write on <testsuites>.",
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


class ConversionMixin(ApplicationTestcaseMixin):
	"""
	Classic mixin: convert this dialect's reference report into every writable dialect, through the command line.
	"""

	_consoleScript:  ClassVar[str] = "pyedaa-reports"
	_runnableModule: ClassVar[str] = "pyEDAA.Reports.CLI"
	_dialectName:    ClassVar[str] = None

	def _convert(self, targetName: str) -> Path:
		"""
		Run the command line converting this dialect's reference report into the target dialect.

		:param targetName: Name of the dialect to convert to.
		:returns:          The file the command line was asked to write.
		"""
		source = DIALECTS[self._dialectName]
		target = DIALECTS[targetName]
		OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
		outputFile = OUTPUT_DIRECTORY / f"{source.Name}-to-{target.Name}.xml"
		outputFile.unlink(missing_ok=True)

		result = self.RunEntrypoint(
			"unittest",
			f"--merge={COMMANDLINE_NAMES[source.Name]}:{source.ReferenceFiles[0]}",
			f"--output={COMMANDLINE_NAMES[target.Name]}:{outputFile}",
			timeout=60.0
		)

		if (self._dialectName, targetName) in FORMAT_LIMITS:
			return outputFile if result.returncode == 0 else None

		self.assertExitCode(result)
		self.assertTrue(outputFile.exists(), msg=f"'{outputFile}' was not written.\n{result.stdout}\n{result.stderr}")
		XMLSchema(str(SCHEMA_DIRECTORY / f"{target._schemaName}.xsd")).validate(str(outputFile))

		return outputFile

	def _readBack(self, targetName: str, writtenFile: Path) -> None:
		"""
		Read a converted report back through the command line and require it to succeed.

		:param targetName:  Name of the dialect the file was written in.
		:param writtenFile: The file to read back.
		"""
		self.assertExitCode(self._readBackResult(targetName, writtenFile))

	def _readBackResult(self, targetName: str, writtenFile: Path):
		"""
		Read a converted report back through the command line, in the dialect it was written in.

		:param targetName:  Name of the dialect the file was written in.
		:param writtenFile: The file to read back.
		:returns:           The completed process, so the caller decides what the exit code has to be.
		"""
		return self.RunEntrypoint(
			"unittest",
			f"--merge={COMMANDLINE_NAMES[targetName]}:{writtenFile}",
			f"--output=pyTest-JUnit:{writtenFile.with_suffix('.reread.xml')}",
			timeout=60.0
		)

	def _roundTripThroughTheCommandLine(self, targetName: str) -> None:
		"""
		Convert into the target dialect and read the result back in it, or assert that a format limit stops the chain.

		A limit can bite in either step: the target format may refuse to write a report it cannot express, or accept
		it and refuse to read it back. The chain is what has to fail, not a particular command.

		:param targetName: Name of the dialect to convert to.
		"""
		reason = FORMAT_LIMITS.get((self._dialectName, targetName))
		writtenFile = self._convert(targetName)

		if reason is None:
			self._readBack(targetName, writtenFile)
			return

		if writtenFile is None:      # the write already refused
			return

		result = self._readBackResult(targetName, writtenFile)
		self.assertNotEqual(
			0, result.returncode,
			msg=f"This conversion works end to end now, so the limit is gone: {reason}"
		)

	def test_ToAntJUnit4(self) -> None:
		self._roundTripThroughTheCommandLine("Ant-JUnit4")

	def test_ToCTestJUnit(self) -> None:
		self._roundTripThroughTheCommandLine("CTest-JUnit")

	def test_ToGoogleTestJUnit(self) -> None:
		self._roundTripThroughTheCommandLine("GoogleTest-JUnit")

	def test_ToPyTestJUnit(self) -> None:
		self._roundTripThroughTheCommandLine("pyTest-JUnit")


class FromAntJUnit4(ConversionMixin, TestCase):
	_dialectName = "Ant-JUnit4"


class FromCTestJUnit(ConversionMixin, TestCase):
	_dialectName = "CTest-JUnit"


class FromGoogleTestJUnit(ConversionMixin, TestCase):
	_dialectName = "GoogleTest-JUnit"


class FromPyTestJUnit(ConversionMixin, TestCase):
	_dialectName = "pyTest-JUnit"


class FromAnyJUnit(ConversionMixin, TestCase):
	_dialectName = "Any-JUnit"


class TheCommandLineVocabulary(ApplicationTestcaseMixin, TestCase):
	"""What the command line accepts as a dialect, which is not what the documents and schemas call them."""

	_consoleScript:  ClassVar[str] = "pyedaa-reports"
	_runnableModule: ClassVar[str] = "pyEDAA.Reports.CLI"

	def _merge(self, dialect: str) -> str:
		reference = DIALECTS["pyTest-JUnit"].ReferenceFiles[0]
		result = self.RunEntrypoint(
			"unittest", f"--merge={dialect}:{reference}", f"--output=pyTest-JUnit:{OUTPUT_DIRECTORY / 'vocabulary.xml'}",
			timeout=60.0
		)

		return f"{result.stdout}\n{result.stderr}"

	def test_TheDocumentedAntNameIsRejected(self) -> None:
		"""``Ant-JUnit4`` is how the schema and the reports name it; the command line splits on '-' and sees 'junit4'."""
		self.assertIn("Unsupported", self._merge("Ant-JUnit4"))

	def test_TheDocumentedGoogleTestNameIsRejected(self) -> None:
		""":file:`GoogleTest-JUnit.xsd` names it so, the command line wants ``gtest-JUnit``."""
		self.assertIn("Unsupported", self._merge("GoogleTest-JUnit"))

	def test_AnyJUnitCannotBeWritten(self) -> None:
		"""It can be read, but ``_output`` has no branch for it."""
		reference = DIALECTS["pyTest-JUnit"].ReferenceFiles[0]
		result = self.RunEntrypoint(
			"unittest", f"--merge=pyTest-JUnit:{reference}", f"--output=Any-JUnit:{OUTPUT_DIRECTORY / 'any.xml'}",
			timeout=60.0
		)

		self.assertIn("Unsupported JUnit XML dialect for writing", f"{result.stdout}\n{result.stderr}")
