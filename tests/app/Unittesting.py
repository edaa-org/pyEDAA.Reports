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
