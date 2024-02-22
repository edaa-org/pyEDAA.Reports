from pathlib import Path
from unittest import TestCase

from pyEDAA.Reports.DocumentationCoverage.Python import CoverageState, ClassCoverage, ModuleCoverage, PackageCoverage


class ClassCoverageInstantiation(TestCase):
	def test_ClassCoverage_NoName(self) -> None:
		with self.assertRaises(TypeError):
			_ = ClassCoverage(None)

	def test_ClassCoverage_Name(self) -> None:
		cc = ClassCoverage("class")

		self.assertIsNone(cc.Parent)
		self.assertEqual("class", cc.Name)
		# self.assertEqual(CoverageState.Unknown, cc.Status)
		self.assertEqual(0, len(cc.Fields))
		self.assertEqual(0, len(cc.Methods))
		self.assertEqual(0, len(cc.Classes))


class ModuleCoverageInstantiation(TestCase):
	def test_ModuleCoverage_NoName(self) -> None:
		with self.assertRaises(TypeError):
			_ = ModuleCoverage(None, Path("module.py"))

	def test_ModuleCoverage_Name(self) -> None:
		mc = ModuleCoverage("module", Path("module.py"))

		self.assertIsNone(mc.Parent)
		self.assertEqual("module", mc.Name)
		# self.assertEqual(CoverageState.Unknown, mc.Status)


class PackageCoverageInstantiation(TestCase):
	def test_PackageCoverage_NoName(self) -> None:
		with self.assertRaises(TypeError):
			_ = PackageCoverage(None, Path("package"))

	def test_PackageCoverage_Name(self) -> None:
		pc = PackageCoverage("package", Path("package"))

		self.assertIsNone(pc.Parent)
		self.assertEqual("package", pc.Name)
		# self.assertEqual(CoverageState.Unknown, pc.Status)


class Hierarchy(TestCase):
	def test_Hierarchy1(self) -> None:
		pc = PackageCoverage("package", Path("package"))
		mc1 = ModuleCoverage("module1", Path("module1.py"), parent=pc)
		mc2 = ModuleCoverage("module2", Path("module2.py"), parent=pc)
		cc11 = ClassCoverage("class11", parent=mc1)
		cc12 = ClassCoverage("class12", parent=mc1)
		cc21 = ClassCoverage("class21", parent=mc2)
		cc22 = ClassCoverage("class22", parent=mc2)

		pc.Aggregate()


