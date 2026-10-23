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
# Copyright 2023-2023 Patrick Lehmann - Bötzingen, Germany                                                             #
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
"""Unit tests of the converter of docstr_coverage's analysis to the documentation coverage model."""
from datetime                                            import timedelta
from importlib                                           import import_module
from pathlib                                             import Path
from sys                                                 import modules as sys_modules
from unittest.mock                                       import patch

from pyTooling.Exceptions                                import MissingDependencyError
from pyTooling.Testing                                   import Testcase

from pyEDAA.Reports.DocumentationCoverage                import CoverageState, ItemKind
from pyEDAA.Reports.DocumentationCoverage.DocStrCoverage import DocStrCoverage, DocStrCoverageError


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


class Analyze(Testcase):
	def test_PackageCode(self) -> None:
		"""A directory without ``__init__.py`` is a package with nothing to document."""
		docStrCov = DocStrCoverage("pyEDAA", Path("pyEDAA"))
		docStrCov.Analyze()
		coverage = docStrCov.Convert()

		self.assertIs(CoverageState.Empty, coverage.Items[0].Status)
		self.assertIs(ItemKind.Package, coverage.Items[0]["Reports"].Kind)
		self.assertGreaterEqual(coverage.Counters.Coverage, 0.10)

	def test_PackageCode_Aggregation(self) -> None:
		"""The model counts what docstr_coverage counts, per file and in total."""
		docStrCov = DocStrCoverage("pyEDAA.Reports", Path("pyEDAA/Reports"))
		docStrCov.Analyze()
		coverage = docStrCov.Convert()

		fileCounts = {
			Path(path).relative_to(Path("pyEDAA/Reports")): result.count_aggregate()
			for path, result in docStrCov.CoverageReport.files()
		}
		for path, fileCount in fileCounts.items():
			file = coverage.GetOrAddFile(path)
			self.assertEqual(fileCount.needed, file.Counters.Expected, f"{path}: expected")
			self.assertEqual(fileCount.found, file.Counters.Covered, f"{path}: covered")

		self.assertEqual(sum(fileCount.needed for fileCount in fileCounts.values()), coverage.Counters.Expected)
		self.assertEqual(sum(fileCount.found for fileCount in fileCounts.values()), coverage.Counters.Covered)
		self.assertEqual(sum(fileCount.missing for fileCount in fileCounts.values()), coverage.Counters.Uncovered)

	def test_Undocumented(self) -> None:
		docStrCov = DocStrCoverage("MyPackage", Path("tests/packages/undocumented"))
		docStrCov.Analyze()
		coverage = docStrCov.Convert()
		package = coverage.Items[0]

		self.assertEqual(12, coverage.Counters.Total)
		self.assertEqual(0, coverage.Counters.Excluded)
		self.assertEqual(0, coverage.Counters.Ignored)
		self.assertEqual(12, coverage.Counters.Expected)
		self.assertEqual(0, coverage.Counters.Covered)
		self.assertEqual(12, coverage.Counters.Uncovered)
		self.assertEqual(0.0, coverage.Counters.Coverage)

		self.assertEqual(6, coverage.Files[Path("__init__.py")].Counters.Expected)
		self.assertEqual(0, coverage.Files[Path("__init__.py")].Counters.Covered)
		self.assertEqual(CoverageState.Undocumented, package.Status)
		self.assertEqual(["PackageClass", "DerivedPackageClass", "MyModule"], [item.Name for item in package])
		self.assertEqual(["__init__", "Method", "__str__"], [item.Name for item in package["PackageClass"]])
		self.assertIs(ItemKind.Module, package["MyModule"].Kind)
		self.assertIs(ItemKind.Other, package["PackageClass"].Kind)

	def test_Partial(self) -> None:
		docStrCov = DocStrCoverage("MyPackage", Path("tests/packages/partially"))
		docStrCov.Analyze()
		coverage = docStrCov.Convert()

		self.assertEqual(12, coverage.Counters.Total)
		self.assertEqual(12, coverage.Counters.Expected)
		self.assertEqual(5, coverage.Counters.Covered)
		self.assertEqual(7, coverage.Counters.Uncovered)
		self.assertAlmostEqual(0.417, coverage.Counters.Coverage, 3)

		self.assertEqual(6, coverage.Files[Path("__init__.py")].Counters.Expected)
		self.assertEqual(3, coverage.Files[Path("__init__.py")].Counters.Covered)
		self.assertEqual(0.5, coverage.Files[Path("__init__.py")].Counters.Coverage)

	def test_Documented(self) -> None:
		docStrCov = DocStrCoverage("MyPackage", Path("tests/packages/documented"))
		docStrCov.Analyze()
		coverage = docStrCov.Convert()

		self.assertEqual(12, coverage.Counters.Expected)
		self.assertEqual(12, coverage.Counters.Covered)
		self.assertEqual(1.0, coverage.Counters.Coverage)
		self.assertEqual(6, coverage.Files[Path("MyModule.py")].Counters.Covered)

	def test_Durations(self) -> None:
		"""Analysis and conversion are measured; the report takes the analysis' duration."""
		docStrCov = DocStrCoverage("MyPackage", Path("tests/packages/documented"))

		self.assertIsNone(docStrCov.AnalysisDuration)
		self.assertIsNone(docStrCov.ModelConversionDuration)

		docStrCov.Analyze()
		coverage = docStrCov.Convert()

		self.assertGreaterEqual(docStrCov.AnalysisDuration, timedelta(0))
		self.assertGreaterEqual(docStrCov.ModelConversionDuration, timedelta(0))
		self.assertEqual(docStrCov.AnalysisDuration, coverage.AnalysisDuration)
		self.assertEqual(Path("MyPackage"), coverage.Name)

	def test_ConvertBeforeAnalyze(self) -> None:
		docStrCov = DocStrCoverage("MyPackage", Path("tests/packages/documented"))

		self.assertIsNone(docStrCov.CoverageReport)
		with self.assertRaises(DocStrCoverageError) as context:
			docStrCov.Convert()
		self.assertEqual("docstr_coverage's analysis didn't run.", str(context.exception))

	def test_MissingDirectory(self) -> None:
		with self.assertRaises(DocStrCoverageError) as context:
			_ = DocStrCoverage("MyPackage", Path("tests/packages/missing"))
		self.assertEqual("Package source directory 'tests/packages/missing' does not exist.", str(context.exception))

	def test_Parameters(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = DocStrCoverage(None, Path("tests/packages/documented"))
		self.assertEqual("Parameter 'packageName' is None.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = DocStrCoverage("MyPackage", "tests/packages/documented")
		self.assertEqual("Parameter 'directory' is not of type 'Path'.", str(context.exception))


class MissingDependency(Testcase):
	def test_Analyze(self) -> None:
		"""Without docstr_coverage, the module imports and ``Analyze()`` raises a :exc:`MissingDependencyError`."""
		moduleName = "pyEDAA.Reports.DocumentationCoverage.DocStrCoverage"
		package =    sys_modules["pyEDAA.Reports.DocumentationCoverage"]

		with patch.dict(sys_modules, {"docstr_coverage": None}), patch.object(package, "DocStrCoverage"):
			del sys_modules[moduleName]
			module = import_module(moduleName)

			docStrCov = module.DocStrCoverage("MyPackage", Path("tests/packages/documented"))
			with self.assertRaises(MissingDependencyError) as context:
				docStrCov.Analyze()

		self.assertEqual("Optional dependency 'docstr_coverage' not installed.", str(context.exception))
		self.assertEqual("docstr_coverage", context.exception.Dependency)
		self.assertIsNone(context.exception.Extra)
		self.assertIsInstance(context.exception.__cause__, ImportError)
		self.assertIsNone(docStrCov.CoverageReport)
		self.assertIsNot(module, sys_modules[moduleName])
