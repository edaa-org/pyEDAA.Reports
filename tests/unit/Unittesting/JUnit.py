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
from datetime import timedelta, datetime
from pathlib  import Path
from unittest import TestCase as ut_TestCase

from pyEDAA.Reports.Unittesting       import Testsuite, Testcase
from pyEDAA.Reports.Unittesting.JUnit import JUnitDocument


class Document(ut_TestCase):
	_outputDirectory = Path("tests/output")

	@classmethod
	def setUpClass(cls):
		print()
		if cls._outputDirectory.exists():
			print(f"Output directory '{cls._outputDirectory}' already exists.")
			print(f"Cleaning XML files from '{cls._outputDirectory}' ...")
			for file in cls._outputDirectory.glob("*.xml"):
				print(f"  unlinking file: {file}")
				file.unlink()
		else:
			print(f"Creating output directory '{cls._outputDirectory}' ...")
			cls._outputDirectory.mkdir(parents=True)

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

	def test_Generate(self) -> None:
		print()
		doc = JUnitDocument(self._outputDirectory / "Generate.xml")
		doc._name = "root"
		doc._startTime = datetime.fromisoformat("2024-02-24T12:12:12+01:00")
		ts1 = Testsuite("ts1", startTime=datetime.fromisoformat("2024-02-24T12:12:12+01:00"))
		ts11 = Testsuite("ts11", startTime=datetime.fromisoformat("2024-02-24T12:12:12+01:00"), parent=ts1)
		tc111 = Testcase("tc111", assertionCount=10, passedAssertionCount=10, totalDuration=timedelta(seconds=0.005), parent=ts11)
		tc112 = Testcase("tc112", assertionCount=24, passedAssertionCount=24, totalDuration=timedelta(seconds=0.859), parent=ts11)
		ts2 = Testsuite("ts2", startTime=datetime.fromisoformat("2024-02-24T12:12:13+01:00"))
		tc21 = Testcase("tc21", assertionCount=13, failedAssertionCount=1, totalDuration=timedelta(seconds=3.637), parent=ts2)
		tc22 = Testcase("tc22", assertionCount=48, failedAssertionCount=15, totalDuration=timedelta(seconds=2.473), parent=ts2)
		doc.AddTestsuite(ts1)
		doc.AddTestsuite(ts2)
		doc.Aggregate()

		tree = doc.ToTree()
		print(tree.Render())

		doc.Write(regenerate=True)


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
