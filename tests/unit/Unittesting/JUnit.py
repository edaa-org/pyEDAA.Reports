from datetime import timedelta

from pathlib import Path
from unittest import TestCase as ut_TestCase

from pyEDAA.Reports.Unittesting.JUnit import Document, Testcase, TestcaseState, Testsuite, TestsuiteSummary


class Instantiation(ut_TestCase):
	def test_Summary(self):
		tss = TestsuiteSummary("tss", timedelta(milliseconds=9831))

		self.assertEqual("tss", tss.Name)
		self.assertEqual(TestcaseState.Unknown, tss.State)
		self.assertEqual(0, len(tss.Testsuites))
		self.assertEqual(9.831, tss.Time.total_seconds())

	def test_Testsuite(self):
		ts = Testsuite("ts", timedelta(milliseconds=4206))

		self.assertEqual("ts", ts.Name)
		self.assertEqual(TestcaseState.Unknown, ts.State)
		self.assertEqual(0, len(ts.Testsuites))
		self.assertEqual(0, len(ts.Testcases))
		self.assertEqual(4.206, ts.Time.total_seconds())

	def test_Testcase(self):
		tc = Testcase("tc", timedelta(milliseconds=1505))

		self.assertEqual("tc", tc.Name)
		self.assertEqual(TestcaseState.Unknown, tc.State)
		self.assertEqual(0, tc.Assertions)
		self.assertEqual(1.505, tc.Time.total_seconds())


class ExampleFiles(ut_TestCase):
	def test_pytest_pyAttributes(self):
		print()

		junitExampleFile = Path("data/JUnit/pytest.pyAttributes.xml")
		doc = Document(junitExampleFile)

		print(f"JUnit file:")
		print(f"  Testsuites: {len(doc.Testsuites)}")
		print(f"  Testcases:  ")

		print()
		print(f"Statistics:")
		print(f"  Times: MiniDOM: {doc._readingByMiniDom:.3f}s   convert: {doc._modelConversion:.3f}s")

	def test_OSVVM_Libraries(self):
		print()

		junitExampleFile = Path("data/JUnit/osvvm.Libraries.xml")
		doc = Document(junitExampleFile)

		print(f"JUnit file:")
		print(f"  Testsuites: {len(doc.Testsuites)}")
		print(f"  Testcases:  ")

		print()
		print(f"Statistics:")
		print(f"  Times: MiniDOM: {doc._readingByMiniDom:.3f}s   convert: {doc._modelConversion:.3f}s")
