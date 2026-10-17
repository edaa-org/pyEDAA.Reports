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
The schemas describe what the frameworks emit.

Each schema in :file:`pyEDAA/Reports/Resources` was reverse-engineered from real output, so the reference reports in
:file:`tests/data/JUnit` are the ground truth: a schema that rejects one of them describes the format wrongly. The
reader has to agree with the schema too - it is the same claim about the format, written twice.
"""
from pathlib  import Path
from re       import sub
from tempfile import TemporaryDirectory
from textwrap import dedent
from typing   import ClassVar
from unittest import TestCase as ut_TestCase

from pyTooling.Decorators import readonly
from pyTooling.Testing    import Testcase

from pyEDAA.Reports.Unittesting       import TestcaseStatus
from pyEDAA.Reports.Unittesting.JUnit import Document

from . import DATA_DIRECTORY, DIALECTS, OUTPUT_DIRECTORY, TESTSUITE_ROOTED_FILES, Dialect


class SchemaMixin:
	"""Classic mixin: the schema of a dialect accepts every report that framework produced."""

	_dialectName: ClassVar[str]

	@readonly
	def Dialect(self) -> Dialect:
		"""
		Read-only property to return the dialect under test, looked up by :attr:`_dialectName`.

		:returns: The dialect under test.
		"""
		return DIALECTS[self._dialectName]

	def _read(self, report: str) -> Document:
		"""
		Validate a report against the dialect's schema, then read it with the dialect's reader.

		:param report: The report's XML text.
		:returns:      The document read from the report.
		"""
		with TemporaryDirectory() as directory:
			reportFile = Path(directory) / "report.xml"
			reportFile.write_text(report, encoding="utf-8")
			self.Dialect.Schema().validate(str(reportFile))

			return self.Dialect.DocumentClass(reportFile, analyzeAndConvert=True)

	def test_ReferenceOutputIsValid(self) -> None:
		dialect = self.Dialect
		schema = dialect.Schema()

		for referenceFile in dialect.ReferenceFiles:
			with self.subTest(file=referenceFile.name):
				self.assertTrue(referenceFile.exists(), f"Reference file '{referenceFile}' is missing.")
				schema.validate(str(referenceFile))

	def test_TheReaderAcceptsWhatTheSchemaAccepts(self) -> None:
		dialect = self.Dialect

		for referenceFile in dialect.ReferenceFiles:
			with self.subTest(file=referenceFile.name):
				dialect.DocumentClass(referenceFile, analyzeAndConvert=True)


class AntJUnit4(SchemaMixin, ut_TestCase):
	_dialectName = "Ant-JUnit4"

	def test_TestcaseWithoutTime(self) -> None:
		"""The schema declares ``time`` of ``<testcase>`` optional: the reader accepts a test case without it."""
		document = self._read(dedent("""\
			<?xml version="1.0" encoding="utf-8"?>
			<testsuite name="s" tests="1" failures="0" errors="0" skipped="0" time="0.1" timestamp="2026-10-08T10:00:00"
			           hostname="h">
			  <properties/>
			  <testcase classname="C" name="t"/>
			  <system-out/>
			  <system-err/>
			</testsuite>
			"""))

		self.assertIsNone(document.Testsuites["s"].Testclasses["C"].Testcases["t"].Duration)


class Catch2JUnit(SchemaMixin, ut_TestCase):
	_dialectName = "Catch2-JUnit"

	def test_AnyJUnit(self) -> None:
		"""Catch2's JUnit report is Any-JUnit, except for the ``status`` attribute of each ``<testcase>``."""
		schema = DIALECTS["Any-JUnit"].Schema()
		referenceFile = self.Dialect.ReferenceFiles[0]

		errors = {(error.elem.tag, error.reason) for error in schema.iter_errors(str(referenceFile))}

		self.assertEqual({("testcase", "'status' attribute not allowed for element")}, errors)

	def test_SkippedWithoutMessage(self) -> None:
		"""The schema declares ``message`` of ``<skipped>`` optional: a failure expected by Catch2 has no message then."""
		document = self._read(dedent("""\
			<?xml version="1.0" encoding="UTF-8"?>
			<testsuites>
			  <testsuite name="t" errors="0" failures="1" skipped="1" tests="2" hostname="tbd" time="0.001"
			             timestamp="2026-10-08T10:00:00Z">
			    <testcase classname="t.global" name="x" time="0.000" status="run">
			      <skipped/>
			      <failure message="a == b" type="REQUIRE">boom</failure>
			    </testcase>
			    <system-out/>
			    <system-err/>
			  </testsuite>
			</testsuites>
			"""))
		testcase = document.Testsuites["t"].Testclasses["t.global"].Testcases["x"]

		self.assertIs(TestcaseStatus.Skipped, testcase.Status)
		self.assertIsNone(testcase.Message)
		self.assertEqual("boom", testcase.Details)

	def test_OtherSchemas(self) -> None:
		"""No other dialect's schema accepts Catch2's JUnit report."""
		for dialect in DIALECTS.values():
			if dialect is self.Dialect:
				continue

			schema = dialect.Schema()
			for referenceFile in self.Dialect.ReferenceFiles:
				with self.subTest(dialect=dialect.Name, file=referenceFile.name):
					self.assertFalse(schema.is_valid(str(referenceFile)), f"{dialect.Name} accepts '{referenceFile.name}'.")


class CTestJUnit(SchemaMixin, ut_TestCase):
	_dialectName = "CTest-JUnit"


class GoogleTestJUnit(SchemaMixin, ut_TestCase):
	_dialectName = "GoogleTest-JUnit"


class PyTestJUnit(SchemaMixin, ut_TestCase):
	_dialectName = "pyTest-JUnit"

	def test_TestcaseWithoutTime(self) -> None:
		"""The schema declares ``time`` of ``<testcase>`` optional: the reader accepts a test case without it."""
		document = self._read(dedent("""\
			<?xml version="1.0" encoding="utf-8"?>
			<testsuites name="r">
			  <testsuite name="s" tests="1" failures="0" errors="0" skipped="0" time="0.1" timestamp="2026-10-08T10:00:00"
			             hostname="h">
			    <testcase classname="C" name="t"/>
			  </testsuite>
			</testsuites>
			"""))

		self.assertIsNone(document.Testsuites["s"].Testclasses["C"].Testcases["t"].Duration)


class TestLoggerJUnit(SchemaMixin, ut_TestCase):
	_dialectName = "TestLogger-JUnit"


class AnyJUnit(SchemaMixin, ut_TestCase):
	"""
	``Any-JUnit`` is the permissive dialect, so it has to accept what the specific ones accept.

	It currently does not: its schema declares only ``<testsuites>`` as a root element, while ``Ant-JUnit4`` and
	``CTest-JUnit`` are rooted at ``<testsuite>`` - and so are VUnit's reports.
	"""

	_dialectName = "Any-JUnit"

	def test_ATestsuiteRootedReportIsStillRejected(self) -> None:
		"""Known gap: when this starts failing, Any-JUnit has been widened and the expectation can go."""
		schema = self.Dialect.Schema()
		rejected = [*TESTSUITE_ROOTED_FILES, DIALECTS["Ant-JUnit4"].ReferenceFiles[0]]

		for referenceFile in rejected:
			with self.subTest(file=referenceFile.name):
				with self.assertRaises(Exception, msg="Any-JUnit accepts a <testsuite> root now - drop this expectation."):
					schema.validate(str(referenceFile))

	def test_TheReaderRejectsATestsuiteRootedReportToo(self) -> None:
		"""Known gap, reader side: it agrees with the schema, so both move together."""
		for referenceFile in TESTSUITE_ROOTED_FILES:
			with self.subTest(file=referenceFile.name):
				with self.assertRaises(Exception):
					self.Dialect.DocumentClass(referenceFile, analyzeAndConvert=True)

	def test_TestcaseWithoutTime(self) -> None:
		"""The schema declares ``time`` of ``<testcase>`` optional: the reader accepts a test case without it."""
		document = self._read(dedent("""\
			<?xml version="1.0" encoding="utf-8"?>
			<testsuites name="r">
			  <testsuite name="s" tests="1">
			    <testcase classname="C" name="t"/>
			  </testsuite>
			</testsuites>
			"""))

		self.assertIsNone(document.Testsuites["s"].Testclasses["C"].Testcases["t"].Duration)


class NextestJUnit(SchemaMixin, ut_TestCase):
	_dialectName = "nextest-JUnit"

	def test_AnyJUnit(self) -> None:
		"""The report is Any-JUnit, except for ``uuid`` on ``<testsuites>`` and ``timestamp`` on ``<testcase>``."""
		schema = DIALECTS["Any-JUnit"].Schema()

		errors = {(error.elem.tag, error.reason) for error in schema.iter_errors(str(self.Dialect.ReferenceFiles[0]))}

		self.assertEqual({
			("testsuites", "'uuid' attribute not allowed for element"),
			("testcase", "'timestamp' attribute not allowed for element"),
		}, errors)


class GoJUnitReport(SchemaMixin, ut_TestCase):
	"""
	go-junit-report's report and Any-JUnit.

	Any-JUnit's schema rejects the report only for the ``id`` attribute of ``<testsuite>``. Without it, Any-JUnit's
	reader still rejects the ``<testsuite>`` with an empty name, which go-junit-report writes for a package without tests.
	"""

	_dialectName = "GoJUnitReport-JUnit"

	def test_OtherSchemas(self) -> None:
		referenceFile = self.Dialect.ReferenceFiles[0]

		for dialect in DIALECTS.values():
			if dialect is self.Dialect:
				continue

			with self.subTest(dialect=dialect.Name):
				self.assertFalse(dialect.Schema().is_valid(str(referenceFile)), f"{dialect.Name} accepts the report now.")

	def test_AnyJUnit(self) -> None:
		schema = DIALECTS["Any-JUnit"].Schema()

		errors = {(error.elem.tag, error.reason) for error in schema.iter_errors(str(self.Dialect.ReferenceFiles[0]))}

		self.assertEqual({("testsuite", "'id' attribute not allowed for element")}, errors)

	def test_AnyJUnit_Reader(self) -> None:
		withoutIds = OUTPUT_DIRECTORY / "go-junit-report.without-id.xml"
		withoutIds.parent.mkdir(parents=True, exist_ok=True)
		withoutIds.write_text(sub(r' id="\d+"', "", self.Dialect.ReferenceFiles[0].read_text()))

		DIALECTS["Any-JUnit"].Schema().validate(str(withoutIds))
		with self.assertRaises(ValueError) as context:
			DIALECTS["Any-JUnit"].DocumentClass(withoutIds, analyzeAndConvert=True)

		self.assertEqual("Parameter 'name' is empty.", str(context.exception))


class JunitXmlTestLogger(Testcase):
	"""The .NET test logger ``JunitXml.TestLogger`` writes Any-JUnit, except for two attributes of ``<testsuite>``."""

	def test_Schemas(self) -> None:
		"""Known gap: ``id`` and ``package`` keep Any-JUnit and pyTest-JUnit from reading the report."""
		referenceFile = DATA_DIRECTORY / "pyEDAA.Reports/CSharp-xUnit/MyLibrary.Tests.junit.xml"

		for dialectName in ("Any-JUnit", "pyTest-JUnit"):
			with self.subTest(dialect=dialectName):
				schema = DIALECTS[dialectName].Schema()
				self.assertEqual(
					{
						("testsuite", "'id' attribute not allowed for element"),
						("testsuite", "'package' attribute not allowed for element"),
					},
					{(error.elem.tag, error.reason) for error in schema.iter_errors(str(referenceFile))}
				)
