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
"""Reading pyTooling's XML test report format into the unified data model."""
from datetime import timedelta
from pathlib  import Path
from textwrap import dedent

from pyEDAA.Reports.Unittesting           import Testcase as ut_Testcase, TestcaseStatus, Testsuite, TestsuiteStatus
from pyEDAA.Reports.Unittesting           import UnittestError, TestsuiteSummary, MergedTestsuiteSummary
from pyEDAA.Reports.Unittesting.pyTooling import SCHEMA_FILES, Document, FormatVersion
from pyTooling.Testing                    import Testcase


REPORT = dedent("""\
	<?xml version='1.0' encoding='utf-8'?>
	<TestReport xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="{schema}"
	            duration="1.5" tests="6" failures="1" errors="1" skipped="1">
		<Title>Report</Title>
		<Testsuite name="suite">
			<Testcase name="passed" status="passed" duration="0.25" />
			<Testcase name="failed" status="failed" duration="0.25"><Message>assert 1 == 2</Message></Testcase>
			<Testcase name="errored" status="errored" duration="0.25"><Message>KeyError</Message></Testcase>
			<Testcase name="skipped" status="skipped" duration="0.25" />
			<Testcase name="xfail" status="expectedToFail" duration="0.25" />
			<Testcase name="xpass" status="unexpectedlyPassed" duration="0.25" />
		</Testsuite>
	</TestReport>
	""")


class DataModel(Testcase):
	"""Every test entity can carry a title, a summary and a description."""

	def test_Default(self) -> None:
		for entity in (ut_Testcase("tc"), Testsuite("ts"), TestsuiteSummary("tss")):
			with self.subTest(entity=entity.__class__.__name__):
				self.assertIsNone(entity.Title)
				self.assertIsNone(entity.Summary)
				self.assertIsNone(entity.Description)

	def test_Values(self) -> None:
		for entityClass in (ut_Testcase, Testsuite, TestsuiteSummary):
			with self.subTest(entity=entityClass.__name__):
				entity = entityClass("name", title="Title", summary="Summary.", description="Summary.\n\nMore.")

				self.assertEqual("Title", entity.Title)
				self.assertEqual("Summary.", entity.Summary)
				self.assertEqual("Summary.\n\nMore.", entity.Description)

	def test_WrongType(self) -> None:
		with self.assertRaises(TypeError) as context:
			_ = Testsuite("ts", title=1)

		self.assertEqual("Parameter 'title' is not of type 'str'.", str(context.exception))
		self.assertEqual(["Got type 'int'."], context.exception.__notes__)

	def test_Merge(self) -> None:
		"""A merged entity keeps the first title, summary and description it finds."""
		first = TestsuiteSummary("tss", testsuites=(Testsuite("ts", testcases=(ut_Testcase("tc"),)),))
		second = TestsuiteSummary("tss", title="Summary", testsuites=(
			Testsuite("ts", title="Suite", testcases=(ut_Testcase("tc", title="Case", description="Case."),)),
		))
		merged = MergedTestsuiteSummary("tss")
		merged.Merge(first)
		merged.Merge(second)

		summary = merged.ToTestsuiteSummary()

		self.assertEqual("Summary", summary.Title)
		self.assertEqual("Suite", summary.Testsuites["ts"].Title)
		self.assertEqual("Case", summary.Testsuites["ts"].Testcases["tc"].Title)
		self.assertEqual("Case.", summary.Testsuites["ts"].Testcases["tc"].Description)


class Reader(Testcase):
	"""A report written by pyTooling's pytest plugin is read into the unified data model."""

	_reportFile = Path("tests/data/pyTooling/TestReport.xml")
	_outputDirectory = Path("tests/output/pyToolingTestReport")

	@classmethod
	def setUpClass(cls) -> None:
		cls._outputDirectory.mkdir(parents=True, exist_ok=True)

	def _write(self, name: str, content: str) -> Path:
		path = self._outputDirectory / name
		path.write_text(content, encoding="utf-8")
		return path

	def test_Hierarchy(self) -> None:
		document = Document(self._reportFile, analyzeAndConvert=True)

		self.assertEqual(FormatVersion.Version0_1, document.SchemaVersion)
		self.assertIsInstance(document.SchemaVersion, FormatVersion)
		self.assertEqual("TestReport", document.Name)
		self.assertEqual(6, document.TestcaseCount)
		self.assertEqual(TestsuiteStatus.Failed, document.Status)

		arithmetic = document.Testsuites["tests"].Testsuites["unit"].Testsuites["Arithmetic"]
		self.assertEqual(["Addition", "Division"], list(arithmetic.Testsuites))
		self.assertEqual("Unit tests for the arithmetic operations.", arithmetic.Summary)
		self.assertIsNone(arithmetic.Title)

		addition = arithmetic.Testsuites["Addition"]
		self.assertEqual("Addition of integers", addition.Title)
		self.assertEqual("Add two integers.", addition.Summary)
		self.assertEqual(
			"Add two integers.\n\nEvery testcase adds two small integers and checks the sum.",
			addition.Description
		)
		self.assertEqual(["OnePlusOne", "OnePlusTwo", "Negative"], list(addition.Testcases))

	def test_Testcase(self) -> None:
		document = Document(self._reportFile, analyzeAndConvert=True)
		addition = document.Testsuites["tests"].Testsuites["unit"].Testsuites["Arithmetic"].Testsuites["Addition"]

		passed = addition.Testcases["OnePlusOne"]
		self.assertEqual(TestcaseStatus.Passed, passed.Status)
		self.assertEqual("One plus one is two.", passed.Title)
		self.assertEqual("One plus one is two.", passed.Summary)
		self.assertEqual("One plus one is two.\n\nThe simplest addition there is.", passed.Description)
		self.assertEqual(timedelta(seconds=0.004088), passed.TotalDuration)
		self.assertEqual("tests/unit/Arithmetic.py::Addition::OnePlusOne", passed["nodeID"])
		self.assertIsNone(passed.Message)

		failed = addition.Testcases["OnePlusTwo"]
		self.assertEqual(TestcaseStatus.Failed, failed.Status)
		self.assertIn("E    AssertionError: 4 != 3", failed.Message)

		unmarked = addition.Testcases["Negative"]
		self.assertEqual("Negative", unmarked.Title)
		self.assertIsNone(unmarked.Summary)
		self.assertIsNone(unmarked.Description)

	def test_Status(self) -> None:
		document = Document(self._write("status.xml", REPORT.format(schema="TestReport-v0.1.xsd")), analyzeAndConvert=True)
		testcases = document.Testsuites["suite"].Testcases

		self.assertEqual("Report", document.Title)
		self.assertEqual(TestcaseStatus.Passed, testcases["passed"].Status)
		self.assertEqual(TestcaseStatus.Failed, testcases["failed"].Status)
		self.assertEqual("assert 1 == 2", testcases["failed"].Message)
		self.assertEqual(TestcaseStatus.Errored, testcases["errored"].Status)
		self.assertEqual("KeyError", testcases["errored"].Message)
		self.assertEqual(TestcaseStatus.Skipped, testcases["skipped"].Status)
		self.assertEqual(TestcaseStatus.ExpectedFailed, testcases["xfail"].Status)
		self.assertEqual(TestcaseStatus.UnexpectedPassed, testcases["xpass"].Status)
		self.assertEqual(timedelta(seconds=1.5), document.TotalDuration)

		# An expected failure counts as passed, an unexpected pass as failed.
		self.assertEqual(2, document.Passed)
		self.assertEqual(2, document.Failed)
		self.assertEqual(1, document.Errored)
		self.assertEqual(1, document.Skipped)

	def test_UnknownVersion(self) -> None:
		path = self._write("unknown.xml", REPORT.format(schema="TestReport-v9.9.xsd"))

		with self.assertRaises(UnittestError) as context:
			_ = Document(path, analyzeAndConvert=True)

		self.assertEqual(
			f"Unsupported pyTooling test report format 'TestReport-v9.9.xsd' in '{path}'.",
			str(context.exception)
		)
		self.assertEqual(["Supported schemas: TestReport-v0.1.xsd"], context.exception.__notes__)

	def test_NoSchemaLocation(self) -> None:
		path = self._write("noschema.xml", "<TestReport />")

		with self.assertRaises(UnittestError) as context:
			_ = Document(path, analyzeAndConvert=True)

		self.assertEqual(
			f"Root element of '{path}' has no 'xsi:noNamespaceSchemaLocation' attribute.",
			str(context.exception)
		)

	def test_NotATestReport(self) -> None:
		path = self._write("junit.xml", "<testsuites />")

		with self.assertRaises(UnittestError) as context:
			_ = Document(path, analyzeAndConvert=True)

		self.assertEqual(f"Root element of '{path}' is not '<TestReport>'.", str(context.exception))
		self.assertEqual(["Got root element '<testsuites>'."], context.exception.__notes__)

	def test_Invalid(self) -> None:
		content = REPORT.format(schema="TestReport-v0.1.xsd").replace('status="skipped"', 'status="maybe"')
		path = self._write("invalid.xml", content)

		with self.assertRaises(UnittestError) as context:
			_ = Document(path, analyzeAndConvert=True)

		self.assertEqual(f"Validation error for '{path}' using XSD schema 'TestReport-v0.1.xsd'.", str(context.exception))
		self.assertGreater(len(context.exception.__notes__), 0)

	def test_MissingFile(self) -> None:
		with self.assertRaises(UnittestError):
			_ = Document(Path("tests/data/pyTooling/missing.xml"), analyzeAndConvert=True)

	def test_Unreadable(self) -> None:
		"""A directory can't be read as a file."""
		directory = Path("tests/data")
		with self.assertRaises(UnittestError) as context:
			_ = Document(directory, analyzeAndConvert=True)

		self.assertEqual(f"Couldn't read pyTooling test report file '{directory}'.", str(context.exception))
		self.assertIsInstance(context.exception.__cause__, OSError)

	def test_SchemaVersionNotAnalyzed(self) -> None:
		document = Document(self._reportFile)

		with self.assertRaises(UnittestError):
			_ = document.SchemaVersion

		document.Analyze()
		self.assertEqual(FormatVersion.Version0_1, document.SchemaVersion)

	def test_SchemaPerVersion(self) -> None:
		"""Each format version has one XML schema, named after the version."""
		self.assertEqual(list(FormatVersion), list(SCHEMA_FILES.values()))
		for schemaFile, version in SCHEMA_FILES.items():
			self.assertEqual(f"TestReport-v{version}.xsd", schemaFile)
