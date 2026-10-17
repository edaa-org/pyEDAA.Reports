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
Writing a report into a file: an existing file is kept unless overwriting is asked for, a file that can't be written
raises a ``UnittestError`` caused by the operating system's error.
"""
from pathlib  import Path
from tempfile import TemporaryDirectory

from pyTooling.Testing import Testcase

from pyEDAA.Reports.Unittesting import UnittestError

from . import DIALECTS, readReference


class WriteErrors(Testcase):
	"""Each dialect's writer, on its first reference file."""

	def test_Overwrite(self) -> None:
		"""An existing file isn't overwritten without ``overwrite=True``; its content stays."""
		for name, dialect in DIALECTS.items():
			with self.subTest(dialect=name), TemporaryDirectory() as directory:
				summary = readReference(dialect, dialect.ReferenceFiles[0])
				outputFile = Path(directory) / "report.xml"
				outputFile.write_bytes(b"existing")

				with self.assertRaises(UnittestError) as context:
					dialect.DocumentClass.FromTestsuiteSummary(outputFile, summary).Write(regenerate=True)

				self.assertIsInstance(context.exception.__cause__, FileExistsError)
				self.assertEqual(b"existing", outputFile.read_bytes())

	def test_NotWritable(self) -> None:
		"""A file in a missing directory can't be written: the ``OSError`` is the cause."""
		for name, dialect in DIALECTS.items():
			with self.subTest(dialect=name), TemporaryDirectory() as directory:
				summary = readReference(dialect, dialect.ReferenceFiles[0])
				outputFile = Path(directory) / "missing" / "report.xml"

				with self.assertRaises(UnittestError) as context:
					dialect.DocumentClass.FromTestsuiteSummary(outputFile, summary).Write(regenerate=True)

				self.assertEqual(f"JUnit XML file '{outputFile}' can not be written.", str(context.exception))
				self.assertIsInstance(context.exception.__cause__, OSError)
