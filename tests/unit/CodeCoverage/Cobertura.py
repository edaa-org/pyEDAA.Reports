from pathlib import Path
from unittest import TestCase

from pyEDAA.Reports.CodeCoverage.Cobertura import Document


class ExampleFiles(TestCase):
	def test_Cobertura(self) -> None:
		print()

		gcovrExampleFile = Path("tests/data/Cobertura/example.Cobertura.xml")
		doc = Document(gcovrExampleFile)

		print(f"Cobertura file:")
		print(f"  Lines:    {doc._coveredLines:>5} out of {doc._validLines:>5} -> {doc._lineRate:.2f}%")
		print(f"  Branches: {doc._coveredBranches:>5} out of {doc._validBranches:>5} -> {doc._branchRate:.2f}%")

		totalLines, coveredLines, lineRate = doc.GetStatistics()
		print()
		print(f"Statistics:")
		print(f"  Lines: total:   {totalLines:>5}    covered: {coveredLines:>5}  -> {lineRate:.2f}%")
		print(f"  Times: MiniDOM: {doc._readingByMiniDom:.3f}s   convert: {doc._modelConversion:.3f}s")

		self.assertEqual(51928, doc._validLines)
		self.assertEqual(11411, doc._coveredLines)
		self.assertAlmostEqual(0.219, doc._lineRate, delta=0.001)

		self.assertAlmostEqual(0.146, doc._branchRate, delta=0.001)

	def test_gcovr(self) -> None:
		print()

		gcovrExampleFile = Path("tests/data/Cobertura/example.gcovr.xml")
		doc = Document(gcovrExampleFile)

		print(f"Cobertura file:")
		print(f"  Lines:    {doc._coveredLines:>5} out of {doc._validLines:>5} -> {doc._lineRate:.2f}%")
		print(f"  Branches: {doc._coveredBranches:>5} out of {doc._validBranches:>5} -> {doc._branchRate:.2f}%")

		totalLines, coveredLines, lineRate = doc.GetStatistics()
		print()
		print(f"Statistics:")
		print(f"  Lines: total:   {totalLines:>5}    covered: {coveredLines:>5}  -> {lineRate:.2f}%")
		print(f"  Times: MiniDOM: {doc._readingByMiniDom:.3f}s   convert: {doc._modelConversion:.3f}s")

		self.assertEqual(7, doc._validLines)
		self.assertEqual(6, doc._coveredLines)
		self.assertAlmostEqual(0.857, doc._lineRate, delta=0.001)

		self.assertAlmostEqual(0.5, doc._branchRate, delta=0.001)

	def test_CoveragePy(self) -> None:
		print()

		coveragePyExampleFile = Path("tests/data/Cobertura/example.Coverage.py.xml")
		doc = Document(coveragePyExampleFile)

		print(f"Cobertura file:")
		print(f"  Lines:    {doc._coveredLines:>5} out of {doc._validLines:>5} -> {doc._lineRate:.2f}%")
		print(f"  Branches: {doc._coveredBranches:>5} out of {doc._validBranches:>5} -> {doc._branchRate:.2f}%")

		totalLines, coveredLines, lineRate = doc.GetStatistics()
		print()
		print(f"Statistics:")
		print(f"  Lines: total:   {totalLines:>5}    covered: {coveredLines:>5}  -> {lineRate:.2f}%")
		print(f"  Times: MiniDOM: {doc._readingByMiniDom:.3f}s   convert: {doc._modelConversion:.3f}s")

		self.assertEqual(5488, doc._validLines)
		self.assertEqual(4758, doc._coveredLines)
		self.assertAlmostEqual(0.867, doc._lineRate, delta=0.001)

		self.assertEqual(2641, doc._validBranches)
		self.assertEqual(2124, doc._coveredBranches)
		self.assertAlmostEqual(0.804, doc._branchRate, delta=0.001)
