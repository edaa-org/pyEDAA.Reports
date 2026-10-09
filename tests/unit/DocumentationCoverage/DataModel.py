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
# Copyright 2024-2026 Electronic Design Automation Abstraction (EDA²)                                                  #
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
from pathlib                                     import Path
from unittest                                    import TestCase

from pyEDAA.Reports.DocumentationCoverage        import DocCoverageError
from pyEDAA.Reports.DocumentationCoverage.Python import CoverageState, ClassCoverage, ModuleCoverage, PackageCoverage
from pyTooling.Testing                           import Testcase


class ClassCoverageInstantiation(TestCase):
	def test_ClassCoverage_NoName(self) -> None:
		with self.assertRaises(ValueError):
			_ = ClassCoverage(None)

	def test_ClassCoverage_Name(self) -> None:
		cc = ClassCoverage("class")

		self.assertIsNone(cc.Parent)
		self.assertEqual("class", cc.Name)
		self.assertEqual(CoverageState.Unknown, cc.Status)
		self.assertEqual(0, len(cc.Fields))
		self.assertEqual(0, len(cc.Methods))
		self.assertEqual(0, len(cc.Classes))


class ModuleCoverageInstantiation(TestCase):
	def test_ModuleCoverage_NoName(self) -> None:
		with self.assertRaises(ValueError):
			_ = ModuleCoverage(None, Path("module.py"))

	def test_ModuleCoverage_Name(self) -> None:
		mc = ModuleCoverage("module", Path("module.py"))

		self.assertIsNone(mc.Parent)
		self.assertEqual("module", mc.Name)
		self.assertEqual(CoverageState.Unknown, mc.Status)


class PackageCoverageInstantiation(TestCase):
	def test_PackageCoverage_NoName(self) -> None:
		with self.assertRaises(ValueError):
			_ = PackageCoverage(None, Path("package"))

	def test_PackageCoverage_Name(self) -> None:
		pc = PackageCoverage("package", Path("package"))

		self.assertIsNone(pc.Parent)
		self.assertEqual("package", pc.Name)
		self.assertEqual(CoverageState.Unknown, pc.Status)


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


class Counting(Testcase):
	def test_ClassCoverage(self) -> None:
		cc = ClassCoverage("class")
		cc.Fields["field1"] =   CoverageState.Covered
		cc.Fields["field2"] =   CoverageState.Undocumented
		cc.Methods["method1"] = CoverageState.Covered
		cc.Methods["method2"] = CoverageState.Excluded
		cc.Methods["method3"] = CoverageState.Ignored

		cc.CalculateCoverage()

		self.assertEqual(5, cc.Total)
		self.assertEqual(1, cc.Excluded)
		self.assertEqual(1, cc.Ignored)
		self.assertEqual(3, cc.Expected)
		self.assertEqual(2, cc.Covered)
		self.assertEqual(1, cc.Uncovered)
		self.assertAlmostEqual(2 / 3, cc.Coverage)

	def test_ModuleCoverage_VariablesOnly(self) -> None:
		mc = ModuleCoverage("module", Path("module.py"))
		mc.Variables["variable1"] = CoverageState.Covered
		mc.Variables["variable2"] = CoverageState.Undocumented

		mc.CalculateCoverage()

		self.assertEqual(2, mc.Total)
		self.assertEqual(2, mc.Expected)
		self.assertEqual(1, mc.Covered)
		self.assertEqual(1, mc.Uncovered)
		self.assertEqual(0.5, mc.Coverage)

	def test_PackageCoverage_FunctionsOnly(self) -> None:
		pc = PackageCoverage("package", Path("package/__init__.py"))
		pc.Functions["function1"] = CoverageState.Covered
		pc.Functions["function2"] = CoverageState.Excluded | CoverageState.Covered

		pc.CalculateCoverage()

		self.assertEqual(2, pc.Total)
		self.assertEqual(1, pc.Excluded)
		self.assertEqual(1, pc.Expected)
		self.assertEqual(1, pc.Covered)
		self.assertEqual(0, pc.Uncovered)
		self.assertEqual(1.0, pc.Coverage)

	def test_UnknownState(self) -> None:
		cc = ClassCoverage("class")
		cc.Fields["field1"] =   CoverageState.Unknown
		cc.Methods["method1"] = CoverageState.Covered

		with self.assertRaises(DocCoverageError) as context:
			cc.CalculateCoverage()

		self.assertEqual("Element has coverage state 'Unknown', so it can't be counted.", str(context.exception))
