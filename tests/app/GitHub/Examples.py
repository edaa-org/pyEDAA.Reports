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
# Copyright 2021-2026 Electronic Design Automation Abstraction (EDA²)                                                  #
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
"""Testcase for application testing report files generated on GitHub."""
from datetime                                           import datetime, timezone
from pathlib                                            import Path
from unittest                                           import TestCase

from lxml.etree                                         import XMLSchema, parse
from pyTooling.Common                                   import getResourceFile, zipdicts

from pyEDAA.Reports                                     import Resources
from pyEDAA.Reports.CodeCoverage                        import CodeCoverageError
from pyEDAA.Reports.CodeCoverage.Cobertura              import STRICT_SCHEMA, Document as CoberturaDocument
from pyEDAA.Reports.CodeCoverage.Cobertura.NVCCobertura import Document as NVCCoberturaDocument
from pyEDAA.Reports.CodeCoverage.CoveragePy             import Document as CoveragePyDocument
from pyEDAA.Reports.CodeCoverage.GHDL                   import Document as GHDLDocument, MergedReport
from pyEDAA.Reports.CodeCoverage.Gcov                   import Document as GcovDocument
from pyEDAA.Reports.CodeCoverage.Gcov                   import FormatVersion as GcovFormatVersion
from pyEDAA.Reports.Unittesting                         import TestcaseStatus, UnittestError
from pyEDAA.Reports.Unittesting.JUnit                   import Document as AnyJUnitDocument
# FIXME: change to generic JUnit
from pyEDAA.Reports.Unittesting.JUnit.AntJUnit4         import Document as JUnit4Document
from pyEDAA.Reports.Unittesting.JUnit.Catch2JUnit       import Document as Catch2Document
from pyEDAA.Reports.Unittesting.JUnit.CTestJUnit        import Document as CTestDocument
from pyEDAA.Reports.Unittesting.JUnit.GoogleTestJUnit   import Document as GTestDocument
from pyEDAA.Reports.Unittesting.JUnit.NextestJUnit      import Document as NextestDocument
from pyEDAA.Reports.Unittesting.JUnit.PyTestJUnit       import Document as PyTestDocument
from pyTooling.Testing                                  import Testcase


if __name__ == "__main__": # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unitest <testcase module>'")
	exit(1)


class CppGoogleTest(TestCase):
	def test_gtest(self) -> None:
		print()

		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Cpp-GoogleTest/gtest.xml")
		doc = GTestDocument(junitExampleFile, analyzeAndConvert=True)

		self.assertEqual(1, doc.TestsuiteCount)
		self.assertEqual(3, doc.TestcaseCount)

		print(f"JUnit file:")
		print(f"  Testsuites: {doc.TestsuiteCount}")
		print(f"  Testcases:  {doc.TestcaseCount}")

		print()
		print(f"Statistics:")
		print(f"  Times: parsing by lxml: {doc.AnalysisDuration.total_seconds():.3f}s   convert: {doc.ModelConversionDuration.total_seconds():.3f}s")

	def test_ReadWrite(self) -> None:
		print()

		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Cpp-GoogleTest/gtest.xml")
		doc = GTestDocument(junitExampleFile, analyzeAndConvert=True)

		junitOutputFile = Path("tests/output/JUnit/pyEDAA.Reports/Cpp-GoogleTest/gtest.xml")
		junitOutputFile.parent.mkdir(parents=True, exist_ok=True)
		doc.Write(junitOutputFile, regenerate=True, overwrite=True)

		sameDoc = GTestDocument(junitOutputFile, analyzeAndConvert=True)

		self.assertEqual(doc.TestsuiteCount, sameDoc.TestsuiteCount)
		self.assertEqual(doc.TestcaseCount, sameDoc.TestcaseCount)
		self.assertEqual(doc.Errored, sameDoc.Errored)
		self.assertEqual(doc.Skipped, sameDoc.Skipped)
		self.assertEqual(doc.Failed, sameDoc.Failed)
		self.assertEqual(doc.Passed, sameDoc.Passed)
		self.assertEqual(doc.Tests, sameDoc.Tests)

		for tsName, ts, sameTS in zipdicts(doc._testsuites, sameDoc._testsuites):
			self.assertEqual(ts.Name, sameTS.Name)
			self.assertEqual(ts.Duration, sameTS.Duration)
			self.assertEqual(ts.TestcaseCount, sameTS.TestcaseCount)
			self.assertEqual(ts.AssertionCount, sameTS.AssertionCount)
			self.assertEqual(ts.Errored, sameTS.Errored)
			self.assertEqual(ts.Skipped, sameTS.Skipped)
			self.assertEqual(ts.Failed, sameTS.Failed)
			self.assertEqual(ts.Passed, sameTS.Passed)
			self.assertEqual(ts.Tests, sameTS.Tests)

			for tclsName, tcls, sameTCls in zipdicts(ts._testclasses, sameTS._testclasses):
				self.assertEqual(tcls.Name, sameTCls.Name)
				self.assertEqual(tcls.Classname, sameTCls.Classname)
				self.assertEqual(tcls.TestcaseCount, sameTCls.TestcaseCount)
				self.assertEqual(tcls.AssertionCount, sameTCls.AssertionCount)

				for tcName, tc, sameTC in zipdicts(tcls._testcases, sameTCls._testcases):
					self.assertEqual(tc.Name, sameTC.Name)
					self.assertEqual(tc.Classname, sameTC.Classname)
					self.assertEqual(tc.Status, sameTC.Status)
					self.assertEqual(tc.Duration, sameTC.Duration)
					self.assertEqual(tc.AssertionCount, sameTC.AssertionCount)


class CppGoogleTestCTest(TestCase):
	def test_ctest(self) -> None:
		print()

		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Cpp-GoogleTest/ctest.xml")
		doc = CTestDocument(junitExampleFile, analyzeAndConvert=True)

		# self.assertEqual(1, doc.TestsuiteCount)
		# self.assertEqual(3, doc.TestcaseCount)

		print(f"JUnit file:")
		print(f"  Testsuites: {doc.TestsuiteCount}")
		print(f"  Testcases:  {doc.TestcaseCount}")

		print()
		print(f"Statistics:")
		print(f"  Times: parsing by lxml: {doc.AnalysisDuration.total_seconds():.3f}s   convert: {doc.ModelConversionDuration.total_seconds():.3f}s")

	def test_ReadWrite(self) -> None:
		print()

		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Cpp-GoogleTest/ctest.xml")
		doc = CTestDocument(junitExampleFile, analyzeAndConvert=True)

		junitOutputFile = Path("tests/output/JUnit/pyEDAA.Reports/Cpp-GoogleTest/ctest.xml")
		junitOutputFile.parent.mkdir(parents=True, exist_ok=True)
		doc.Write(junitOutputFile, regenerate=True, overwrite=True)

		sameDoc = CTestDocument(junitOutputFile, analyzeAndConvert=True)

		self.assertEqual(doc.TestsuiteCount, sameDoc.TestsuiteCount)
		self.assertEqual(doc.TestcaseCount, sameDoc.TestcaseCount)
		self.assertEqual(doc.Errored, sameDoc.Errored)
		self.assertEqual(doc.Skipped, sameDoc.Skipped)
		self.assertEqual(doc.Failed, sameDoc.Failed)
		self.assertEqual(doc.Passed, sameDoc.Passed)
		self.assertEqual(doc.Tests, sameDoc.Tests)

		for tsName, ts, sameTS in zipdicts(doc._testsuites, sameDoc._testsuites):
			self.assertEqual(ts.Name, sameTS.Name)
			self.assertEqual(ts.Duration, sameTS.Duration)
			self.assertEqual(ts.TestcaseCount, sameTS.TestcaseCount)
			self.assertEqual(ts.AssertionCount, sameTS.AssertionCount)
			self.assertEqual(ts.Errored, sameTS.Errored)
			self.assertEqual(ts.Skipped, sameTS.Skipped)
			self.assertEqual(ts.Failed, sameTS.Failed)
			self.assertEqual(ts.Passed, sameTS.Passed)
			self.assertEqual(ts.Tests, sameTS.Tests)

			for tclsName, tcls, sameTCls in zipdicts(ts._testclasses, sameTS._testclasses):
				self.assertEqual(tcls.Name, sameTCls.Name)
				self.assertEqual(tcls.Classname, sameTCls.Classname)
				self.assertEqual(tcls.TestcaseCount, sameTCls.TestcaseCount)
				self.assertEqual(tcls.AssertionCount, sameTCls.AssertionCount)

				for tcName, tc, sameTC in zipdicts(tcls._testcases, sameTCls._testcases):
					self.assertEqual(tc.Name, sameTC.Name)
					self.assertEqual(tc.Classname, sameTC.Classname)
					self.assertEqual(tc.Status, sameTC.Status)
					self.assertEqual(tc.Duration, sameTC.Duration)
					self.assertEqual(tc.AssertionCount, sameTC.AssertionCount)


class CppGoogleTestCoverage(TestCase):
	"""gcov measures the library of the GoogleTest example in its direct test run and writes gcov JSON."""

	def test_Gcov(self) -> None:
		report = GcovDocument(Path("tests/data/CodeCoverage/Cpp-GoogleTest/Counter.cpp.gcov.json"), analyzeAndConvert=True)

		self.assertEqual(1, len(report.DataFiles))
		self.assertEqual(GcovFormatVersion.Version2, report.DataFiles[0].FormatVersion)

		summary = report.ToCoverageSummary()
		files = list(summary.IterateFiles())
		self.assertEqual(1, len(files))
		self.assertEqual(("src", "Counter.cpp"), files[0].Path.parts[-2:])
		self.assertEqual((6, 6), (files[0].TotalLines, files[0].CoveredLines))
		self.assertEqual(
			[(3, 4), (4, 4), (7, 1), (8, 1), (11, 1), (12, 1)],
			[(line.LineNumber, line.CoverageCount) for line in files[0].IterateLines()]
		)
		self.assertEqual(
			["Counter::Decrement()", "Counter::Increment()", "Counter::Value()"],
			sorted(unit.Name for unit in summary.IterateUnits() if unit.Name.startswith("Counter::"))
		)


class CppCatch2(TestCase):
	def test_JUnit(self) -> None:
		"""Each test case and each path of nested sections is a testcase; Catch2's console counts 6 test cases."""
		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Cpp-Catch2/catch2-junit.xml")
		doc = Catch2Document(junitExampleFile, analyzeAndConvert=True)

		self.assertEqual(1, doc.TestsuiteCount)
		self.assertEqual(9, doc.TestcaseCount)
		self.assertEqual(6, doc.Passed)
		self.assertEqual(1, doc.Failed)
		self.assertEqual(1, doc.Errored)
		self.assertEqual(1, doc.Skipped)

		testsuite = doc.Testsuites["unit_tests"]
		self.assertEqual("tbd", testsuite.Hostname)
		self.assertEqual(datetime(2026, 10, 8, 10, 47, 45, tzinfo=timezone.utc), testsuite.StartTime)

		statuses = {
			(testcase.Classname, testcase.Name): testcase.Status
			for testclass in testsuite.Testclasses.values()
			for testcase in testclass.Testcases.values()
		}
		self.assertEqual({
			("unit_tests.global",         "Init"):                           TestcaseStatus.Passed,
			("unit_tests.global",         "Operations"):                     TestcaseStatus.Passed,
			("unit_tests.global",         "Operations/Increment"):           TestcaseStatus.Passed,
			("unit_tests.global",         "Operations/Decrement"):           TestcaseStatus.Passed,
			("unit_tests.global",         "Operations/Decrement/Underflow"): TestcaseStatus.Passed,
			("unit_tests.CounterFixture", "Fixture"):                        TestcaseStatus.Passed,
			("unit_tests.global",         "Failing"):                        TestcaseStatus.Failed,
			("unit_tests.global",         "Skipped"):                        TestcaseStatus.Skipped,
			("unit_tests.global",         "Exception"):                      TestcaseStatus.Errored,
		}, statuses)

	def test_ReadWrite(self) -> None:
		print()

		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Cpp-Catch2/catch2-junit.xml")
		doc = Catch2Document(junitExampleFile, analyzeAndConvert=True)

		junitOutputFile = Path("tests/output/JUnit/pyEDAA.Reports/Cpp-Catch2/catch2-junit.xml")
		junitOutputFile.parent.mkdir(parents=True, exist_ok=True)
		doc.Write(junitOutputFile, regenerate=True, overwrite=True)

		sameDoc = Catch2Document(junitOutputFile, analyzeAndConvert=True)

		self.assertEqual(doc.TestsuiteCount, sameDoc.TestsuiteCount)
		self.assertEqual(doc.TestcaseCount, sameDoc.TestcaseCount)
		self.assertEqual(doc.Errored, sameDoc.Errored)
		self.assertEqual(doc.Skipped, sameDoc.Skipped)
		self.assertEqual(doc.Failed, sameDoc.Failed)
		self.assertEqual(doc.Passed, sameDoc.Passed)
		self.assertEqual(doc.Tests, sameDoc.Tests)

		for tsName, ts, sameTS in zipdicts(doc._testsuites, sameDoc._testsuites):
			self.assertEqual(ts.Name, sameTS.Name)
			self.assertEqual(ts.Hostname, sameTS.Hostname)
			self.assertEqual(ts.StartTime, sameTS.StartTime)
			self.assertEqual(ts.Duration, sameTS.Duration)
			self.assertEqual(ts.TestcaseCount, sameTS.TestcaseCount)
			self.assertEqual(ts.AssertionCount, sameTS.AssertionCount)
			self.assertEqual(ts.Errored, sameTS.Errored)
			self.assertEqual(ts.Skipped, sameTS.Skipped)
			self.assertEqual(ts.Failed, sameTS.Failed)
			self.assertEqual(ts.Passed, sameTS.Passed)
			self.assertEqual(ts.Tests, sameTS.Tests)

			for tclsName, tcls, sameTCls in zipdicts(ts._testclasses, sameTS._testclasses):
				self.assertEqual(tcls.Name, sameTCls.Name)
				self.assertEqual(tcls.Classname, sameTCls.Classname)
				self.assertEqual(tcls.TestcaseCount, sameTCls.TestcaseCount)
				self.assertEqual(tcls.AssertionCount, sameTCls.AssertionCount)

				for tcName, tc, sameTC in zipdicts(tcls._testcases, sameTCls._testcases):
					self.assertEqual(tc.Name, sameTC.Name)
					self.assertEqual(tc.Classname, sameTC.Classname)
					self.assertEqual(tc.Status, sameTC.Status)
					self.assertEqual(tc.Duration, sameTC.Duration)
					self.assertEqual(tc.AssertionCount, sameTC.AssertionCount)


class CSharpXUnit(Testcase):
	def test_JUnit(self) -> None:
		"""Known gap: no dialect reads the report of the .NET test logger ``JunitXml.TestLogger`` yet."""
		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/CSharp-xUnit/MyLibrary.Tests.junit.xml")

		for documentClass in (AnyJUnitDocument, JUnit4Document, CTestDocument, GTestDocument, PyTestDocument):
			with self.subTest(dialect=documentClass.__module__):
				with self.assertRaises(UnittestError):
					documentClass(junitExampleFile, analyzeAndConvert=True)


class GoTest(TestCase):
	def test_gotestsum(self) -> None:
		"""gotestsum's report is Any-JUnit: a test suite per package, a test case per test, subtest and example."""
		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Go-Test/gotestsum.xml")
		doc = AnyJUnitDocument(junitExampleFile, analyzeAndConvert=True)

		self.assertEqual(3, doc.TestsuiteCount)
		self.assertEqual(18, doc.TestcaseCount)
		self.assertEqual(0, doc.Errored)
		self.assertEqual(1, doc.Skipped)
		self.assertEqual(4, doc.Failed)
		self.assertEqual(13, doc.Passed)
		self.assertEqual(18, doc.Tests)

		module = "github.com/edaa-org/pyEDAA.Reports/examples/Go/testing"
		counter = doc._testsuites[f"{module}/counter"]._testclasses[f"{module}/counter"]
		stack = doc._testsuites[f"{module}/stack"]._testclasses[f"{module}/stack"]
		self.assertEqual(0, doc._testsuites[f"{module}/version"].TestcaseCount)
		self.assertEqual(TestcaseStatus.Passed, counter._testcases["TestOperations/Decrement/Underflow"].Status)
		self.assertEqual(TestcaseStatus.Skipped, counter._testcases["TestSkipped"].Status)
		self.assertEqual(TestcaseStatus.Failed, stack._testcases["TestPushPop/sorted"].Status)
		self.assertEqual(TestcaseStatus.Failed, stack._testcases["TestPushPop"].Status)
		# A panic is a failure, not an error.
		self.assertEqual(TestcaseStatus.Failed, stack._testcases["TestPopEmpty"].Status)

	def test_ReadWrite(self) -> None:
		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Go-Test/gotestsum.xml")
		doc = AnyJUnitDocument(junitExampleFile, analyzeAndConvert=True)

		junitOutputFile = Path("tests/output/JUnit/pyEDAA.Reports/Go-Test/gotestsum.xml")
		junitOutputFile.parent.mkdir(parents=True, exist_ok=True)
		doc.Write(junitOutputFile, regenerate=True, overwrite=True)

		sameDoc = AnyJUnitDocument(junitOutputFile, analyzeAndConvert=True)

		self.assertEqual(doc.TestsuiteCount, sameDoc.TestsuiteCount)
		self.assertEqual(doc.TestcaseCount, sameDoc.TestcaseCount)
		self.assertEqual(doc.Errored, sameDoc.Errored)
		self.assertEqual(doc.Skipped, sameDoc.Skipped)
		self.assertEqual(doc.Failed, sameDoc.Failed)
		self.assertEqual(doc.Passed, sameDoc.Passed)
		self.assertEqual(doc.Tests, sameDoc.Tests)

		for tsName, ts, sameTS in zipdicts(doc._testsuites, sameDoc._testsuites):
			self.assertEqual(ts.Name, sameTS.Name)
			self.assertEqual(ts.Duration, sameTS.Duration)
			self.assertEqual(ts.TestcaseCount, sameTS.TestcaseCount)
			self.assertEqual(ts.Errored, sameTS.Errored)
			self.assertEqual(ts.Skipped, sameTS.Skipped)
			self.assertEqual(ts.Failed, sameTS.Failed)
			self.assertEqual(ts.Passed, sameTS.Passed)
			self.assertEqual(ts.Tests, sameTS.Tests)

			for tclsName, tcls, sameTCls in zipdicts(ts._testclasses, sameTS._testclasses):
				self.assertEqual(tcls.Name, sameTCls.Name)
				self.assertEqual(tcls.Classname, sameTCls.Classname)
				self.assertEqual(tcls.TestcaseCount, sameTCls.TestcaseCount)

				for tcName, tc, sameTC in zipdicts(tcls._testcases, sameTCls._testcases):
					self.assertEqual(tc.Name, sameTC.Name)
					self.assertEqual(tc.Classname, sameTC.Classname)
					self.assertEqual(tc.Status, sameTC.Status)
					self.assertEqual(tc.Duration, sameTC.Duration)

	def test_gotestsum_OtherDialects(self) -> None:
		"""Specific dialects reject gotestsum's report; pyTest-JUnit's schema accepts it, its reader needs a hostname."""
		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Go-Test/gotestsum.xml")

		for documentClass in (JUnit4Document, CTestDocument, GTestDocument, PyTestDocument):
			with self.subTest(dialect=documentClass.__module__):
				with self.assertRaises(UnittestError):
					documentClass(junitExampleFile, analyzeAndConvert=True)

	def test_GoJUnitReport(self) -> None:
		"""Known gap: no dialect reads go-junit-report's report, because of the ``id`` attribute of ``<testsuite>``."""
		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Go-Test/go-junit-report.xml")

		for documentClass in (AnyJUnitDocument, JUnit4Document, CTestDocument, GTestDocument, PyTestDocument):
			with self.subTest(dialect=documentClass.__module__):
				with self.assertRaises(UnittestError):
					documentClass(junitExampleFile, analyzeAndConvert=True)


class GoTestCoverage(TestCase):
	def test_Cobertura(self) -> None:
		"""gocover-cobertura writes a class per receiver type, ``-`` for a package's functions, a method per function."""
		report = CoberturaDocument(Path("tests/data/CodeCoverage/Go-Test/cobertura.xml"), analyzeAndConvert=True)

		self.assertEqual("", report.Version)
		self.assertEqual(
			(28, 20, 0, 0), (report.LinesValid, report.LinesCovered, report.BranchesValid, report.BranchesCovered)
		)

		module = "github.com/edaa-org/pyEDAA.Reports/examples/Go/testing"
		self.assertEqual([f"{module}/counter", f"{module}/version"], [package.Name for package in report.Packages])
		self.assertEqual(
			[[("-", "counter/counter.go"), ("Counter", "counter/counter.go")], [("-", "version/version.go")]],
			[[(klass.Name, klass.Filename) for klass in package.Classes] for package in report.Packages]
		)
		self.assertEqual(["Value", "Increment", "Decrement", "Reset"], list(report.Packages[0].Classes[1].Methods))

	def test_Cobertura_Strict(self) -> None:
		"""Known gap: the strict schema lacks a ``<method>``'s ``complexity``, which ``coverage-04.dtd`` requires."""
		strict = XMLSchema(parse(getResourceFile(Resources, STRICT_SCHEMA)))

		self.assertFalse(strict.validate(parse("tests/data/CodeCoverage/Go-Test/cobertura.xml")))
		self.assertEqual(
			{"Element 'method', attribute 'complexity': The attribute 'complexity' is not allowed."},
			{error.message for error in strict.error_log}
		)

	def test_Cobertura_Summary(self) -> None:
		report = CoberturaDocument(Path("tests/data/CodeCoverage/Go-Test/cobertura.xml"), analyzeAndConvert=True)
		summary = report.ToCoverageSummary()

		files = {file.Path.as_posix(): file for file in summary.IterateFiles()}
		self.assertEqual(["counter/counter.go", "version/version.go"], sorted(files))

		counter = files["counter/counter.go"]
		version = files["version/version.go"]
		self.assertEqual((23, 20), (counter.TotalLines, counter.CoveredLines))
		self.assertEqual((5, 0), (version.TotalLines, version.CoveredLines))

		# A block's count goes to every line it spans: also to a blank line and a comment line ...
		self.assertEqual((6, 6), (counter.GetLine(28).CoverageCount, counter.GetLine(29).CoverageCount))
		# ... and the counts of two blocks sharing a line are added: line 35 ran twice.
		self.assertEqual(3, counter.GetLine(35).CoverageCount)

	def test_Cobertura_Packages(self) -> None:
		"""Known gap: a Go package is named by its import path, which the reader splits at ``.`` instead of ``/``."""
		report = CoberturaDocument(Path("tests/data/CodeCoverage/Go-Test/cobertura.xml"), analyzeAndConvert=True)
		summary = report.ToCoverageSummary()

		self.assertEqual(["github"], list(summary.Units))
		self.assertEqual(["com/edaa-org/pyEDAA"], list(summary.Units["github"].Units))
		self.assertEqual(
			["Reports/examples/Go/testing/counter", "Reports/examples/Go/testing/version"],
			list(summary.Units["github"].Units["com/edaa-org/pyEDAA"].Units)
		)


class JavaAntJUnit4(TestCase):
	def test_JUnit4(self) -> None:
		print()

		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Java-Ant-JUnit4/TEST-my.AllTests.xml")
		doc = JUnit4Document(junitExampleFile, analyzeAndConvert=True)

		self.assertEqual(1, doc.TestsuiteCount)
		self.assertEqual(2, doc.TestcaseCount)

		print(f"JUnit file:")
		print(f"  Testsuites: {doc.TestsuiteCount}")
		print(f"  Testcases:  {doc.TestcaseCount}")

		print()
		print(f"Statistics:")
		print(f"  Times: parsing by lxml: {doc.AnalysisDuration.total_seconds():.3f}s   convert: {doc.ModelConversionDuration.total_seconds():.3f}s")

	def test_ReadWrite(self) -> None:
		print()

		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Java-Ant-JUnit4/TEST-my.AllTests.xml")
		doc = JUnit4Document(junitExampleFile, analyzeAndConvert=True)

		junitOutputFile = Path("tests/output/JUnit/pyEDAA.Reports/Java-Ant-JUnit4/TEST-my.AllTests.xml")
		junitOutputFile.parent.mkdir(parents=True, exist_ok=True)
		doc.Write(junitOutputFile, regenerate=True, overwrite=True)

		sameDoc = JUnit4Document(junitOutputFile, analyzeAndConvert=True)

		self.assertEqual(doc.TestsuiteCount, sameDoc.TestsuiteCount)
		self.assertEqual(doc.TestcaseCount, sameDoc.TestcaseCount)
		self.assertEqual(doc.Errored, sameDoc.Errored)
		self.assertEqual(doc.Skipped, sameDoc.Skipped)
		self.assertEqual(doc.Failed, sameDoc.Failed)
		self.assertEqual(doc.Passed, sameDoc.Passed)
		self.assertEqual(doc.Tests, sameDoc.Tests)

		for tsName, ts, sameTS in zipdicts(doc._testsuites, sameDoc._testsuites):
			self.assertEqual(ts.Name, sameTS.Name)
			self.assertEqual(ts.Duration, sameTS.Duration)
			self.assertEqual(ts.TestcaseCount, sameTS.TestcaseCount)
			self.assertEqual(ts.AssertionCount, sameTS.AssertionCount)
			self.assertEqual(ts.Errored, sameTS.Errored)
			self.assertEqual(ts.Skipped, sameTS.Skipped)
			self.assertEqual(ts.Failed, sameTS.Failed)
			self.assertEqual(ts.Passed, sameTS.Passed)
			self.assertEqual(ts.Tests, sameTS.Tests)

			for tclsName, tcls, sameTCls in zipdicts(ts._testclasses, sameTS._testclasses):
				self.assertEqual(tcls.Name, sameTCls.Name)
				self.assertEqual(tcls.Classname, sameTCls.Classname)
				self.assertEqual(tcls.TestcaseCount, sameTCls.TestcaseCount)
				self.assertEqual(tcls.AssertionCount, sameTCls.AssertionCount)

				for tcName, tc, sameTC in zipdicts(tcls._testcases, sameTCls._testcases):
					self.assertEqual(tc.Name, sameTC.Name)
					self.assertEqual(tc.Classname, sameTC.Classname)
					self.assertEqual(tc.Status, sameTC.Status)
					self.assertEqual(tc.Duration, sameTC.Duration)
					self.assertEqual(tc.AssertionCount, sameTC.AssertionCount)


class JavaGradleJUnit4(Testcase):
	def test_JUnit4(self) -> None:
		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Java-Gradle-JUnit4/TEST-my.pack.MyClassTest.xml")
		doc = JUnit4Document(junitExampleFile, analyzeAndConvert=True)

		self.assertEqual(1, doc.TestsuiteCount)
		self.assertEqual(6, doc.TestcaseCount)
		self.assertEqual(6, doc.Tests)
		self.assertEqual(2, doc.Passed)
		self.assertEqual(2, doc.Failed)
		self.assertEqual(0, doc.Errored)
		self.assertEqual(2, doc.Skipped)

	def test_Status(self) -> None:
		"""Gradle writes an exception as ``<failure>``, an ignored test and a failed assumption as ``<skipped>``."""
		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Java-Gradle-JUnit4/TEST-my.pack.MyClassTest.xml")
		doc = JUnit4Document(junitExampleFile, analyzeAndConvert=True)

		testclass = doc._testsuites["my.pack.MyClassTest"]._testclasses["my.pack.MyClassTest"]
		self.assertEqual(
			{
				"testAbsolute":     TestcaseStatus.Passed,
				"testAssumption":   TestcaseStatus.Skipped,
				"testDivideByZero": TestcaseStatus.Failed,
				"testIgnored":      TestcaseStatus.Skipped,
				"testReturnFalse":  TestcaseStatus.Passed,
				"testReturnTrue":   TestcaseStatus.Failed,
			},
			{name: testcase.Status for name, testcase in testclass._testcases.items()}
		)

	def test_ReadWrite(self) -> None:
		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Java-Gradle-JUnit4/TEST-my.pack.MyClassTest.xml")
		doc = JUnit4Document(junitExampleFile, analyzeAndConvert=True)

		junitOutputFile = Path("tests/output/JUnit/pyEDAA.Reports/Java-Gradle-JUnit4/TEST-my.pack.MyClassTest.xml")
		junitOutputFile.parent.mkdir(parents=True, exist_ok=True)
		doc.Write(junitOutputFile, regenerate=True, overwrite=True)

		sameDoc = JUnit4Document(junitOutputFile, analyzeAndConvert=True)

		self.assertEqual(doc.TestsuiteCount, sameDoc.TestsuiteCount)
		self.assertEqual(doc.TestcaseCount, sameDoc.TestcaseCount)
		self.assertEqual(doc.Errored, sameDoc.Errored)
		self.assertEqual(doc.Skipped, sameDoc.Skipped)
		self.assertEqual(doc.Failed, sameDoc.Failed)
		self.assertEqual(doc.Passed, sameDoc.Passed)
		self.assertEqual(doc.Tests, sameDoc.Tests)

		for tsName, ts, sameTS in zipdicts(doc._testsuites, sameDoc._testsuites):
			self.assertEqual(ts.Name, sameTS.Name)
			self.assertEqual(ts.StartTime, sameTS.StartTime)
			self.assertEqual(ts.Duration, sameTS.Duration)
			self.assertEqual(ts.TestcaseCount, sameTS.TestcaseCount)
			self.assertEqual(ts.Errored, sameTS.Errored)
			self.assertEqual(ts.Skipped, sameTS.Skipped)
			self.assertEqual(ts.Failed, sameTS.Failed)
			self.assertEqual(ts.Passed, sameTS.Passed)
			self.assertEqual(ts.Tests, sameTS.Tests)

			for tclsName, tcls, sameTCls in zipdicts(ts._testclasses, sameTS._testclasses):
				self.assertEqual(tcls.Name, sameTCls.Name)
				self.assertEqual(tcls.Classname, sameTCls.Classname)
				self.assertEqual(tcls.TestcaseCount, sameTCls.TestcaseCount)

				for tcName, tc, sameTC in zipdicts(tcls._testcases, sameTCls._testcases):
					self.assertEqual(tc.Name, sameTC.Name)
					self.assertEqual(tc.Classname, sameTC.Classname)
					self.assertEqual(tc.Status, sameTC.Status)
					self.assertEqual(tc.Duration, sameTC.Duration)


class JavaGradleJUnit5(Testcase):
	def test_JUnit5(self) -> None:
		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Java-Gradle-JUnit5/TEST-my.pack.MyClassTest.xml")
		doc = JUnit4Document(junitExampleFile, analyzeAndConvert=True)

		self.assertEqual(1, doc.TestsuiteCount)
		self.assertEqual(8, doc.TestcaseCount)
		self.assertEqual(8, doc.Tests)
		self.assertEqual(3, doc.Passed)
		self.assertEqual(3, doc.Failed)
		self.assertEqual(0, doc.Errored)
		self.assertEqual(2, doc.Skipped)

	def test_Names(self) -> None:
		"""Test suite and test cases are named by their display names; ``classname`` is the class' name."""
		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Java-Gradle-JUnit5/TEST-my.pack.MyClassTest.xml")
		doc = JUnit4Document(junitExampleFile, analyzeAndConvert=True)

		self.assertEqual(["Tests of MyClass"], list(doc._testsuites))
		testsuite = doc._testsuites["Tests of MyClass"]
		self.assertEqual(["my.pack.MyClassTest"], list(testsuite._testclasses))
		self.assertEqual(
			{
				"[1] 5, 5":                    TestcaseStatus.Passed,
				"[2] -5, 5":                   TestcaseStatus.Passed,
				"[3] 0, 1":                    TestcaseStatus.Failed,
				"testAssumption()":            TestcaseStatus.Skipped,
				"testDivideByZero()":          TestcaseStatus.Failed,
				"testReturnTrue()":            TestcaseStatus.Failed,
				"testDisabled()":              TestcaseStatus.Skipped,
				"returnFalse() returns false": TestcaseStatus.Passed,
			},
			{name: testcase.Status for name, testcase in testsuite._testclasses["my.pack.MyClassTest"]._testcases.items()}
		)

	def test_NestedClass(self) -> None:
		"""A nested test class is a test suite and a file of its own."""
		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Java-Gradle-JUnit5/TEST-my.pack.MyClassTest$Divide.xml")
		doc = JUnit4Document(junitExampleFile, analyzeAndConvert=True)

		self.assertEqual(["my.pack.MyClassTest$Divide"], list(doc._testsuites))
		self.assertEqual(1, doc.Passed)

	def test_ReadWrite(self) -> None:
		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Java-Gradle-JUnit5/TEST-my.pack.MyClassTest.xml")
		doc = JUnit4Document(junitExampleFile, analyzeAndConvert=True)

		junitOutputFile = Path("tests/output/JUnit/pyEDAA.Reports/Java-Gradle-JUnit5/TEST-my.pack.MyClassTest.xml")
		junitOutputFile.parent.mkdir(parents=True, exist_ok=True)
		doc.Write(junitOutputFile, regenerate=True, overwrite=True)

		sameDoc = JUnit4Document(junitOutputFile, analyzeAndConvert=True)

		self.assertEqual(doc.TestsuiteCount, sameDoc.TestsuiteCount)
		self.assertEqual(doc.TestcaseCount, sameDoc.TestcaseCount)
		self.assertEqual(doc.Errored, sameDoc.Errored)
		self.assertEqual(doc.Skipped, sameDoc.Skipped)
		self.assertEqual(doc.Failed, sameDoc.Failed)
		self.assertEqual(doc.Passed, sameDoc.Passed)
		self.assertEqual(doc.Tests, sameDoc.Tests)

		for tsName, ts, sameTS in zipdicts(doc._testsuites, sameDoc._testsuites):
			self.assertEqual(ts.Name, sameTS.Name)
			self.assertEqual(ts.StartTime, sameTS.StartTime)
			self.assertEqual(ts.Duration, sameTS.Duration)
			self.assertEqual(ts.TestcaseCount, sameTS.TestcaseCount)
			self.assertEqual(ts.Errored, sameTS.Errored)
			self.assertEqual(ts.Skipped, sameTS.Skipped)
			self.assertEqual(ts.Failed, sameTS.Failed)
			self.assertEqual(ts.Passed, sameTS.Passed)
			self.assertEqual(ts.Tests, sameTS.Tests)

			for tclsName, tcls, sameTCls in zipdicts(ts._testclasses, sameTS._testclasses):
				self.assertEqual(tcls.Name, sameTCls.Name)
				self.assertEqual(tcls.Classname, sameTCls.Classname)
				self.assertEqual(tcls.TestcaseCount, sameTCls.TestcaseCount)

				for tcName, tc, sameTC in zipdicts(tcls._testcases, sameTCls._testcases):
					self.assertEqual(tc.Name, sameTC.Name)
					self.assertEqual(tc.Classname, sameTC.Classname)
					self.assertEqual(tc.Status, sameTC.Status)
					self.assertEqual(tc.Duration, sameTC.Duration)


class JavaGradleJUnit6(Testcase):
	def test_JUnit6(self) -> None:
		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Java-Gradle-JUnit6/TEST-my.pack.MyClassTest.xml")
		doc = JUnit4Document(junitExampleFile, analyzeAndConvert=True)

		self.assertEqual(1, doc.TestsuiteCount)
		self.assertEqual(8, doc.TestcaseCount)
		self.assertEqual(8, doc.Tests)
		self.assertEqual(3, doc.Passed)
		self.assertEqual(3, doc.Failed)
		self.assertEqual(0, doc.Errored)
		self.assertEqual(2, doc.Skipped)

	def test_Names(self) -> None:
		"""Test suite and test cases are named by their display names; ``classname`` is the class' name."""
		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Java-Gradle-JUnit6/TEST-my.pack.MyClassTest.xml")
		doc = JUnit4Document(junitExampleFile, analyzeAndConvert=True)

		self.assertEqual(["Tests of MyClass"], list(doc._testsuites))
		testsuite = doc._testsuites["Tests of MyClass"]
		self.assertEqual(["my.pack.MyClassTest"], list(testsuite._testclasses))
		self.assertEqual(
			{
				'[1] "5", "5"':                TestcaseStatus.Passed,
				'[2] "-5", "5"':               TestcaseStatus.Passed,
				'[3] "0", "1"':                TestcaseStatus.Failed,
				"testAssumption()":            TestcaseStatus.Skipped,
				"testDivideByZero()":          TestcaseStatus.Failed,
				"testReturnTrue()":            TestcaseStatus.Failed,
				"testDisabled()":              TestcaseStatus.Skipped,
				"returnFalse() returns false": TestcaseStatus.Passed,
			},
			{name: testcase.Status for name, testcase in testsuite._testclasses["my.pack.MyClassTest"]._testcases.items()}
		)

	def test_NestedClass(self) -> None:
		"""A nested test class is a test suite and a file of its own."""
		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Java-Gradle-JUnit6/TEST-my.pack.MyClassTest$Divide.xml")
		doc = JUnit4Document(junitExampleFile, analyzeAndConvert=True)

		self.assertEqual(["my.pack.MyClassTest$Divide"], list(doc._testsuites))
		self.assertEqual(1, doc.Passed)

	def test_ReadWrite(self) -> None:
		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Java-Gradle-JUnit6/TEST-my.pack.MyClassTest.xml")
		doc = JUnit4Document(junitExampleFile, analyzeAndConvert=True)

		junitOutputFile = Path("tests/output/JUnit/pyEDAA.Reports/Java-Gradle-JUnit6/TEST-my.pack.MyClassTest.xml")
		junitOutputFile.parent.mkdir(parents=True, exist_ok=True)
		doc.Write(junitOutputFile, regenerate=True, overwrite=True)

		sameDoc = JUnit4Document(junitOutputFile, analyzeAndConvert=True)

		self.assertEqual(doc.TestsuiteCount, sameDoc.TestsuiteCount)
		self.assertEqual(doc.TestcaseCount, sameDoc.TestcaseCount)
		self.assertEqual(doc.Errored, sameDoc.Errored)
		self.assertEqual(doc.Skipped, sameDoc.Skipped)
		self.assertEqual(doc.Failed, sameDoc.Failed)
		self.assertEqual(doc.Passed, sameDoc.Passed)
		self.assertEqual(doc.Tests, sameDoc.Tests)

		for tsName, ts, sameTS in zipdicts(doc._testsuites, sameDoc._testsuites):
			self.assertEqual(ts.Name, sameTS.Name)
			self.assertEqual(ts.StartTime, sameTS.StartTime)
			self.assertEqual(ts.Duration, sameTS.Duration)
			self.assertEqual(ts.TestcaseCount, sameTS.TestcaseCount)
			self.assertEqual(ts.Errored, sameTS.Errored)
			self.assertEqual(ts.Skipped, sameTS.Skipped)
			self.assertEqual(ts.Failed, sameTS.Failed)
			self.assertEqual(ts.Passed, sameTS.Passed)
			self.assertEqual(ts.Tests, sameTS.Tests)

			for tclsName, tcls, sameTCls in zipdicts(ts._testclasses, sameTS._testclasses):
				self.assertEqual(tcls.Name, sameTCls.Name)
				self.assertEqual(tcls.Classname, sameTCls.Classname)
				self.assertEqual(tcls.TestcaseCount, sameTCls.TestcaseCount)

				for tcName, tc, sameTC in zipdicts(tcls._testcases, sameTCls._testcases):
					self.assertEqual(tc.Name, sameTC.Name)
					self.assertEqual(tc.Classname, sameTC.Classname)
					self.assertEqual(tc.Status, sameTC.Status)
					self.assertEqual(tc.Duration, sameTC.Duration)

class PythonPyTest(TestCase):
	def test_Read(self) -> None:
		print()

		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Python-pytest/TestReportSummary.xml")
		doc = PyTestDocument(junitExampleFile, analyzeAndConvert=True)

		self.assertEqual(1, doc.TestsuiteCount)
		self.assertEqual(8, doc.TestcaseCount)
		self.assertEqual(0, doc.Errored)
		self.assertEqual(0, doc.Skipped)
		self.assertEqual(0, doc.Failed)
		# self.assertEqual(8, doc.Passed)
		self.assertEqual(8, doc.Tests)

		print(f"JUnit file:")
		print(f"  Testsuites: {doc.TestsuiteCount}")
		print(f"  Testcases:  {doc.TestcaseCount}")

		print()
		print(f"Statistics:")
		print(f"  Times: parsing by lxml: {doc.AnalysisDuration.total_seconds():.3f}s   convert: {doc.ModelConversionDuration.total_seconds():.3f}s")

	def test_ReadWrite(self) -> None:
		print()

		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Python-pytest/TestReportSummary.xml")
		doc = PyTestDocument(junitExampleFile, analyzeAndConvert=True)

		junitOutputFile = Path("tests/output/JUnit/pyEDAA.Reports/Python-pytest/TestReportSummary.xml")
		junitOutputFile.parent.mkdir(parents=True, exist_ok=True)
		doc.Write(junitOutputFile, regenerate=True, overwrite=True)

		sameDoc = PyTestDocument(junitOutputFile, analyzeAndConvert=True)

		self.assertEqual(doc.TestsuiteCount, sameDoc.TestsuiteCount)
		self.assertEqual(doc.TestcaseCount, sameDoc.TestcaseCount)
		self.assertEqual(doc.Errored, sameDoc.Errored)
		self.assertEqual(doc.Skipped, sameDoc.Skipped)
		self.assertEqual(doc.Failed, sameDoc.Failed)
		self.assertEqual(doc.Passed, sameDoc.Passed)
		self.assertEqual(doc.Tests, sameDoc.Tests)

		for tsName, ts, sameTS in zipdicts(doc._testsuites, sameDoc._testsuites):
			self.assertEqual(ts.Name, sameTS.Name)
			self.assertEqual(ts.Duration, sameTS.Duration)
			self.assertEqual(ts.TestcaseCount, sameTS.TestcaseCount)
			self.assertEqual(ts.AssertionCount, sameTS.AssertionCount)
			self.assertEqual(ts.Errored, sameTS.Errored)
			self.assertEqual(ts.Skipped, sameTS.Skipped)
			self.assertEqual(ts.Failed, sameTS.Failed)
			self.assertEqual(ts.Passed, sameTS.Passed)
			self.assertEqual(ts.Tests, sameTS.Tests)

			for tclsName, tcls, sameTCls in zipdicts(ts._testclasses, sameTS._testclasses):
				self.assertEqual(tcls.Name, sameTCls.Name)
				self.assertEqual(tcls.Classname, sameTCls.Classname)
				self.assertEqual(tcls.TestcaseCount, sameTCls.TestcaseCount)
				self.assertEqual(tcls.AssertionCount, sameTCls.AssertionCount)

				for tcName, tc, sameTC in zipdicts(tcls._testcases, sameTCls._testcases):
					self.assertEqual(tc.Name, sameTC.Name)
					self.assertEqual(tc.Classname, sameTC.Classname)
					self.assertEqual(tc.Status, sameTC.Status)
					self.assertEqual(tc.Duration, sameTC.Duration)
					self.assertEqual(tc.AssertionCount, sameTC.AssertionCount)


class PythonPyTestCoverage(TestCase):
	"""coverage.py measures the example's test run and writes its JSON and its Cobertura XML report."""

	def test_CoveragePy(self) -> None:
		report = CoveragePyDocument(Path("tests/data/CodeCoverage/Python-pytest/coverage.json"), analyzeAndConvert=True)

		self.assertTrue(report.BranchCoverage)
		self.assertEqual(["TestModuleA.py", "TestModuleB.py"], sorted(path.as_posix() for path in report.Files))

		summary = report.ToCoverageSummary()
		self.assertEqual((60, 59), (summary.TotalLines, summary.CoveredLines))

	def test_Cobertura(self) -> None:
		report = CoberturaDocument(Path("tests/data/CodeCoverage/Python-pytest/coverage.xml"), analyzeAndConvert=True)

		self.assertEqual((60, 59), (report.LinesValid, report.LinesCovered))

		summary = report.ToCoverageSummary()
		self.assertEqual((60, 59), (summary.TotalLines, summary.CoveredLines))

	def test_SameMeasurement(self) -> None:
		"""Both reports of one measurement convert to the same files and line statuses."""
		json = CoveragePyDocument(Path("tests/data/CodeCoverage/Python-pytest/coverage.json"), analyzeAndConvert=True)
		xml =  CoberturaDocument(Path("tests/data/CodeCoverage/Python-pytest/coverage.xml"), analyzeAndConvert=True)

		jsonFiles = {file.Path.as_posix(): file for file in json.ToCoverageSummary().IterateFiles()}
		xmlFiles =  {file.Path.as_posix(): file for file in xml.ToCoverageSummary().IterateFiles()}
		self.assertEqual(sorted(jsonFiles), sorted(xmlFiles))

		for path, jsonFile, xmlFile in zipdicts(jsonFiles, xmlFiles):
			with self.subTest(path=path):
				self.assertEqual(
					[(line.LineNumber, line.Status) for line in jsonFile.IterateLines()],
					[(line.LineNumber, line.Status) for line in xmlFile.IterateLines()]
				)


class RustCargo(TestCase):
	def test_nextest(self) -> None:
		"""Console: '12 tests run: 8 passed, 4 failed, 1 skipped' - the ignored test is missing from the report."""
		print()

		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Rust-Cargo/nextest-junit.xml")
		doc = NextestDocument(junitExampleFile, analyzeAndConvert=True)

		self.assertEqual(2, doc.TestsuiteCount)
		self.assertEqual(12, doc.TestcaseCount)
		self.assertEqual(0, doc.Errored)
		self.assertEqual(0, doc.Skipped)
		self.assertEqual(4, doc.Failed)
		self.assertEqual(8, doc.Passed)
		self.assertEqual(12, doc.Tests)

		print(f"JUnit file:")
		print(f"  Testsuites: {doc.TestsuiteCount}")
		print(f"  Testcases:  {doc.TestcaseCount}")

		print()
		print(f"Statistics:")
		print(
			f"  Times: parsing by lxml: {doc.AnalysisDuration.total_seconds():.3f}s   "
			f"convert: {doc.ModelConversionDuration.total_seconds():.3f}s"
		)

	def test_ReadWrite(self) -> None:
		print()

		junitExampleFile = Path("tests/data/JUnit/pyEDAA.Reports/Rust-Cargo/nextest-junit.xml")
		doc = NextestDocument(junitExampleFile, analyzeAndConvert=True)

		junitOutputFile = Path("tests/output/JUnit/pyEDAA.Reports/Rust-Cargo/nextest-junit.xml")
		junitOutputFile.parent.mkdir(parents=True, exist_ok=True)
		doc.Write(junitOutputFile, regenerate=True, overwrite=True)

		sameDoc = NextestDocument(junitOutputFile, analyzeAndConvert=True)

		self.assertEqual(doc.RunID, sameDoc.RunID)
		self.assertEqual(doc.StartTime, sameDoc.StartTime)
		self.assertEqual(doc.Duration, sameDoc.Duration)
		self.assertEqual(doc.TestsuiteCount, sameDoc.TestsuiteCount)
		self.assertEqual(doc.TestcaseCount, sameDoc.TestcaseCount)
		self.assertEqual(doc.Errored, sameDoc.Errored)
		self.assertEqual(doc.Skipped, sameDoc.Skipped)
		self.assertEqual(doc.Failed, sameDoc.Failed)
		self.assertEqual(doc.Passed, sameDoc.Passed)
		self.assertEqual(doc.Tests, sameDoc.Tests)

		for tsName, ts, sameTS in zipdicts(doc._testsuites, sameDoc._testsuites):
			self.assertEqual(ts.Name, sameTS.Name)
			self.assertEqual(ts.Duration, sameTS.Duration)
			self.assertEqual(ts.TestcaseCount, sameTS.TestcaseCount)
			self.assertEqual(ts.AssertionCount, sameTS.AssertionCount)
			self.assertEqual(ts.Errored, sameTS.Errored)
			self.assertEqual(ts.Skipped, sameTS.Skipped)
			self.assertEqual(ts.Failed, sameTS.Failed)
			self.assertEqual(ts.Passed, sameTS.Passed)
			self.assertEqual(ts.Tests, sameTS.Tests)

			for tclsName, tcls, sameTCls in zipdicts(ts._testclasses, sameTS._testclasses):
				self.assertEqual(tcls.Name, sameTCls.Name)
				self.assertEqual(tcls.Classname, sameTCls.Classname)
				self.assertEqual(tcls.TestcaseCount, sameTCls.TestcaseCount)
				self.assertEqual(tcls.AssertionCount, sameTCls.AssertionCount)

				for tcName, tc, sameTC in zipdicts(tcls._testcases, sameTCls._testcases):
					self.assertEqual(tc.Name, sameTC.Name)
					self.assertEqual(tc.Classname, sameTC.Classname)
					self.assertEqual(tc.Status, sameTC.Status)
					self.assertEqual(tc.StartTime, sameTC.StartTime)
					self.assertEqual(tc.Duration, sameTC.Duration)
					self.assertEqual(tc.AssertionCount, sameTC.AssertionCount)


class VHDLGHDL(TestCase):
	"""GHDL simulates the example's testbench twice - counting, and counting with resets - with statement coverage."""

	def test_Runs(self) -> None:
		for run, expected in (
			("Count", [("src/Counter.vhdl", 6, 5), ("src/Utilities/Functions.vhdl", 6, 5), ("tb/Counter_tb.vhdl", 15, 13)]),
			("Reset", [("src/Counter.vhdl", 6, 6), ("src/Utilities/Functions.vhdl", 6, 5), ("tb/Counter_tb.vhdl", 15, 12)])
		):
			with self.subTest(run=run):
				report = GHDLDocument(Path(f"tests/data/CodeCoverage/VHDL-GHDL/coverage-{run}.json"), analyzeAndConvert=True)
				summary = report.ToCoverageSummary()

				self.assertEqual(
					expected,
					[(file.Path.as_posix(), file.TotalLines, file.CoveredLines) for file in summary.IterateFiles()]
				)

	def test_Merged(self) -> None:
		"""A line ran, if it ran in one of the runs: the reset run covers the counter's reset branch."""
		runs = [
			GHDLDocument(Path(f"tests/data/CodeCoverage/VHDL-GHDL/coverage-{run}.json"), analyzeAndConvert=True)
			for run in ("Count", "Reset")
		]
		summary = MergedReport("Counter", runs).ToCoverageSummary()

		self.assertEqual((27, 25), (summary.TotalLines, summary.CoveredLines))
		self.assertEqual(
			[("src/Counter.vhdl", 6, 6), ("src/Utilities/Functions.vhdl", 6, 5), ("tb/Counter_tb.vhdl", 15, 14)],
			[(file.Path.as_posix(), file.TotalLines, file.CoveredLines) for file in summary.IterateFiles()]
		)


class VHDLNVC(TestCase):
	"""NVC simulates the example's testbench twice, merges both coverage databases and exports them as Cobertura XML."""

	def test_NVCCobertura(self) -> None:
		"""NVC's dialect reads the merged report: the reset run covers the counter's reset branch."""
		report = NVCCoberturaDocument(Path("tests/data/CodeCoverage/VHDL-NVC/cobertura.xml"), analyzeAndConvert=True)
		summary = report.ToCoverageSummary()

		self.assertEqual((24, 20), (summary.TotalLines, summary.CoveredLines))
		self.assertEqual((18, 10), (summary.TotalBranches, summary.CoveredBranches))
		self.assertEqual(
			[("src/Counter.vhdl", 7, 7), ("tb/Counter_tb.vhdl", 17, 13)],
			[(file.Path.as_posix(), file.TotalLines, file.CoveredLines) for file in summary.IterateFiles()]
		)

	def test_AnyCobertura(self) -> None:
		"""The generic reader rejects it: NVC writes ``condition-coverage`` as e.g. ``100 %``, without the conditions."""
		with self.assertRaises(CodeCoverageError) as context:
			CoberturaDocument(Path("tests/data/CodeCoverage/VHDL-NVC/cobertura.xml"), analyzeAndConvert=True)

		notes = context.exception.__notes__
		self.assertEqual(9, len(notes))
		self.assertTrue(all("attribute 'condition-coverage': [facet 'pattern']" in note for note in notes))
