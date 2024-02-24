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
from datetime import timedelta
from pathlib  import Path
from unittest import TestCase as ut_TestCase

from pyEDAA.Reports.Unittesting.JUnit import JUnitDocument


class Document(ut_TestCase):
	_outputDirectory = Path("tests/output")

	@classmethod
	def setUpClass(cls):
		if cls._outputDirectory.exists():
			print(f"Output directory '{cls._outputDirectory}' already exists.")
		else:
			print(f"Creating output directory '{cls._outputDirectory}' ...")
			cls._outputDirectory.mkdir(parents=True)

	def setUp(self):
		print(f"Cleaning XML files from '{self._outputDirectory}' ...")
		for file in self._outputDirectory.glob("*.xml"):
			print(f"  unlinking file: {file}")
			file.unlink()

	def test_Create_WithoutParse(self) -> None:
		junitExampleFile = Path("tests/data/JUnit/pytest.pyAttributes.xml")
		doc = JUnitDocument(junitExampleFile)

		self.assertEqual(junitExampleFile, doc.Path)
		self.assertLess(doc.AnalysisDuration, timedelta(seconds=0))
		self.assertLess(doc.ModelConversionDuration, timedelta(seconds=0))

		doc.Read()
		doc.Parse()

		self.assertGreaterEqual(doc.AnalysisDuration, timedelta(seconds=0))
		self.assertGreaterEqual(doc.ModelConversionDuration, timedelta(seconds=0))

	def test_Create_WithParse(self) -> None:
		junitExampleFile = Path("tests/data/JUnit/pytest.pyAttributes.xml")
		doc = JUnitDocument(junitExampleFile, parse=True)

		self.assertEqual(junitExampleFile, doc.Path)
		self.assertGreaterEqual(doc.AnalysisDuration, timedelta(seconds=0))
		self.assertGreaterEqual(doc.ModelConversionDuration, timedelta(seconds=0))

	def test_ReadWrite(self) -> None:
		junitExampleFile = Path("tests/data/JUnit/pytest.pyAttributes.xml")
		doc = JUnitDocument(junitExampleFile, parse=True)

		doc.Write(self._outputDirectory / "ReadWrite.xml")


class ExampleFiles(ut_TestCase):
	def test_pytest_pyAttributes(self) -> None:
		print()

		junitExampleFile = Path("tests/data/JUnit/pytest.pyAttributes.xml")
		doc = JUnitDocument(junitExampleFile, parse=True)

		self.assertGreater(doc.TestsuiteCount, 0)
		self.assertGreater(doc.TestcaseCount, 0)

		print(f"JUnit file:")
		print(f"  Testsuites: {len(doc.Testsuites)}")
		print(f"  Testcases:  ")

		print()
		print(f"Statistics:")
		print(f"  Times: MiniDOM: {doc.AnalysisDuration.total_seconds():.3f}s   convert: {doc.ModelConversionDuration.total_seconds():.3f}s")

	def test_OSVVM_Libraries(self) -> None:
		print()

		junitExampleFile = Path("tests/data/JUnit/osvvm.Libraries.xml")
		doc = JUnitDocument(junitExampleFile, parse=True)

		self.assertGreater(doc.TestsuiteCount, 0)
		self.assertGreater(doc.TestcaseCount, 0)

		print(f"JUnit file:")
		print(f"  Testsuites: {len(doc.Testsuites)}")
		print(f"  Testcases:  ")

		print()
		print(f"Statistics:")
		print(f"  Times: MiniDOM: {doc.AnalysisDuration.total_seconds():.3f}s   convert: {doc.ModelConversionDuration.total_seconds():.3f}s")
