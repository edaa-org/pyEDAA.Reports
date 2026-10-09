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
The command ``unittest``, driven through the command line: a defective option or file ends with a message and a
non-zero exit code.
"""
from pathlib   import Path
from textwrap  import dedent
from typing    import ClassVar

from pyTooling.Testing import ApplicationTestcase


OUTPUT_DIRECTORY = Path("tests/output/AppUnittesting")
REFERENCE_FILE =   Path("tests/data/JUnit/pyEDAA.Reports/Python-pytest/TestReportSummary.xml")


class UnittestCommand(ApplicationTestcase):
	"""Read, merge and write unit test reports, with defective options and files."""

	_consoleScript:  ClassVar[str] = "pyedaa-reports"
	_runnableModule: ClassVar[str] = "pyEDAA.Reports.CLI"

	def test_UnreadableInput(self) -> None:
		"""A file that is no JUnit XML: the reader's message, exit code 1."""
		result = self.RunEntrypoint("unittest", "--input=pyTest-JUnit:README.md", timeout=60.0)

		self.assertExitCode(result, 1)
		self.assertIn("[FATAL]     XML syntax or validation error for", result.stdout)

	def test_UnreadableInput_Merge(self) -> None:
		result = self.RunEntrypoint("unittest", "--merge=pyTest-JUnit:README.md", timeout=60.0)

		self.assertNotIn(result.returncode, (0, 241))
		self.assertIn("[ERROR]     XML syntax or validation error for", result.stdout)
		self.assertIn("None of the pyTest-JUnit files were successfully read.", result.stdout)

	def test_MissingFile(self) -> None:
		result = self.RunEntrypoint("unittest", f"--input=pyTest-JUnit:{OUTPUT_DIRECTORY / 'missing.xml'}", timeout=60.0)

		self.assertExitCode(result, 1)
		self.assertIn("[FATAL]     Found 0 files for pattern", result.stdout)

	def test_AbsolutePath(self) -> None:
		"""An absolute file pattern is searched from its root; on Windows, its drive letter is a second ':' in the value."""
		OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
		for option in ("--input", "--merge"):
			with self.subTest(option=option):
				outputFile = (OUTPUT_DIRECTORY / f"absolute{option[1:]}.xml").absolute()
				outputFile.unlink(missing_ok=True)

				result = self.RunEntrypoint(
					"unittest", f"{option}=pyTest-JUnit:{REFERENCE_FILE.absolute()}", f"--output=pyTest-JUnit:{outputFile}",
					timeout=60.0
				)

				self.assertExitCode(result)
				self.assertTrue(outputFile.exists())

	def test_UnsupportedFormat(self) -> None:
		"""A format the option doesn't accept: the message names the option's value and lists the formats it accepts."""
		readFormats =  (
			"Ant-JUnit, Any-JUnit, Catch2-JUnit, CTest-JUnit, GoJUnitReport-JUnit, gtest-JUnit, nextest-JUnit, pyTest-JUnit, "
			"TestLogger-JUnit; without format: Any-JUnit"
		)
		writeFormats = (
			"Ant-JUnit, Catch2-JUnit, CTest-JUnit, GoJUnitReport-JUnit, gtest-JUnit, nextest-JUnit, pyTest-JUnit, "
			"TestLogger-JUnit; without format: pyTest-JUnit"
		)
		outputFile =   OUTPUT_DIRECTORY / "dialect.xml"
		merge = f"--merge=pyTest-JUnit:{REFERENCE_FILE}"
		for options, message, formats in (
			((f"--input=pyTest:{REFERENCE_FILE}", ),                f"input: 'pyTest:{REFERENCE_FILE}'",     readFormats),
			((f"--merge=pyTest:{REFERENCE_FILE}", ),                f"input: 'pyTest:{REFERENCE_FILE}'",     readFormats),
			((merge, f"--output=pyTest:{outputFile}"),              f"output: 'pyTest:{outputFile}'",        writeFormats),
			((merge, f"--output=Any-JUnit:{outputFile}"),           f"output: 'Any-JUnit:{outputFile}'",     writeFormats)
		):
			with self.subTest(options=options):
				result = self.RunEntrypoint("unittest", *options, timeout=60.0)

				self.assertNotIn(result.returncode, (0, 241))
				self.assertIn(f"Unsupported unit testing report format for {message}.", result.stdout)
				self.assertIn(f"Supported formats: {formats}.", result.stdout)

	def test_InputWithoutFormat(self) -> None:
		"""A file without format is read as ``Any-JUnit``, by ``--input`` and by ``--merge``."""
		for option in (f"--input={REFERENCE_FILE}", f"--merge={REFERENCE_FILE}"):
			with self.subTest(option=option):
				result = self.RunEntrypoint("unittest", option, timeout=60.0)

				self.assertExitCode(result, 0)
				self.assertNotIn("Unsupported", result.stdout)

	def test_OutputWithoutFormat(self) -> None:
		"""A file without format is written as ``pyTest-JUnit``."""
		OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
		outputFile = OUTPUT_DIRECTORY / "withoutFormat.xml"
		outputFile.unlink(missing_ok=True)

		result = self.RunEntrypoint(
			"unittest", f"--merge=pyTest-JUnit:{REFERENCE_FILE}", f"--output={outputFile}", timeout=60.0
		)

		self.assertExitCode(result, 0)
		self.assertIn(f"Output written to '{outputFile}' in pyTest-JUnit format.", result.stdout)
		self.assertTrue(outputFile.exists())

	def test_UnwritableOutput(self) -> None:
		"""A file that can't be written: the error, and no claim it was written."""
		outputFile = OUTPUT_DIRECTORY / "missing" / "unwritable.xml"
		result = self.RunEntrypoint(
			"unittest", f"--merge=pyTest-JUnit:{REFERENCE_FILE}", f"--output=pyTest-JUnit:{outputFile}", timeout=60.0
		)

		self.assertNotEqual(0, result.returncode)
		self.assertIn("can not be written.", result.stdout)
		self.assertNotIn("Output written to", result.stdout)

	def test_RewriteDunderInit_Duplicate(self) -> None:
		"""A test class in a package's ``__init__`` and beside it: the rewrite raises, the program exits with code 1."""
		OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
		inputFile = OUTPUT_DIRECTORY / "duplicate.xml"
		with inputFile.open("w", encoding="utf-8") as file:
			file.write(dedent("""\
				<?xml version="1.0" encoding="utf-8"?>
				<testsuites>
				  <testsuite name="pytest" errors="0" failures="0" skipped="0" tests="2" time="0.002"
				             timestamp="2024-10-06T11:28:52.276577+00:00" hostname="localhost">
				    <testcase classname="tests.unit.__init__.Cls" name="test_A" time="0.001"/>
				    <testcase classname="tests.unit.Cls" name="test_A" time="0.001"/>
				  </testsuite>
				</testsuites>
				"""))

		result = self.RunEntrypoint(
			"unittest", f"--merge=pyTest-JUnit:{inputFile}", "--pytest=rewrite-dunder-init", timeout=60.0
		)

		self.assertExitCode(result, 1)
		self.assertIn("[ERROR] Testsuite already contains a testsuite with same name 'Cls'.", result.stderr)
