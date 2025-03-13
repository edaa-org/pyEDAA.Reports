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
# Copyright 2024-2025 Electronic Design Automation Abstraction (EDA²)                                                  #
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
"""
**Abstract code documentation coverage data model for Python code.**
"""
from pathlib                              import Path
from typing                               import Optional as Nullable, Iterable, Dict, Union, Tuple, List

from pyTooling.Decorators                 import export, readonly
from pyTooling.MetaClasses                import ExtendedType

from pyEDAA.Reports.DocumentationCoverage import Class, Module, Package, CoverageState, DocCoverageException


@export
class Coverage(metaclass=ExtendedType, mixin=True):
	"""
	This base-class for :class:`ClassCoverage` and :class:`AggregatedCoverage` represents a basic set of documentation coverage metrics.

	Besides the *total* number of coverable items, it distinguishes items as *excluded*, *ignored*, and *expected*. |br|
	Expected items are further distinguished into *covered* and *uncovered* items. |br|
	If no item is expected, then *coverage* is always 100 |%|.

	All coverable items
	  total = excluded + ignored + expected

	All expected items
	  expected = covered + uncovered

	Coverage [0.00..1.00]
	  coverage = covered / expected
	"""
	_total:     int
	_excluded:  int
	_ignored:   int
	_expected:  int
	_covered:   int
	_uncovered: int

	_coverage:  float

	def __init__(self) -> None:
		self._total =     0
		self._excluded =  0
		self._ignored =   0
		self._expected =  0
		self._covered =   0
		self._uncovered = 0

		self._coverage = -1.0

	@readonly
	def Total(self) -> int:
		return self._total

	@readonly
	def Excluded(self) -> int:
		return self._excluded

	@readonly
	def Ignored(self) -> int:
		return self._ignored

	@readonly
	def Expected(self) -> int:
		return self._expected

	@readonly
	def Covered(self) -> int:
		return self._covered

	@readonly
	def Uncovered(self) -> int:
		return self._uncovered

	@readonly
	def Coverage(self) -> float:
		return self._coverage

	def CalculateCoverage(self) -> None:
		self._uncovered = self._expected - self._covered
		if self._expected != 0:
			self._coverage = self._covered / self._expected
		else:
			self._coverage = 1.0

	def _CountCoverage(self, iterator: Iterable[CoverageState]) -> Tuple[int, int, int, int, int]:
		total =    0
		excluded = 0
		ignored =  0
		expected = 0
		covered =  0
		for coverageState in iterator:
			if coverageState is CoverageState.Unknown:
				raise Exception(f"")

			total += 1

			if CoverageState.Excluded in coverageState:
				excluded += 1
			elif CoverageState.Ignored in coverageState:
				ignored += 1

			expected += 1
			if CoverageState.Covered in coverageState:
				covered += 1

		return total, excluded, ignored, expected, covered


@export
class AggregatedCoverage(Coverage, mixin=True):
	"""
	This base-class for :class:`ModuleCoverage` and :class:`PackageCoverage` represents an extended set of documentation coverage metrics, especially with aggregated metrics.

	As inherited from :class:`~Coverage`, it provides the *total* number of coverable items, which are distinguished into
	*excluded*, *ignored*, and *expected* items. |br|
	Expected items are further distinguished into *covered* and *uncovered* items. |br|
	If no item is expected, then *coverage* and *aggregated coverage* are always 100 |%|.

	In addition, all previously mentioned metrics are collected as *aggregated...*, too. |br|

	All coverable items
	  total = excluded + ignored + expected

	All expected items
	  expected = covered + uncovered

	Coverage [0.00..1.00]
	  coverage = covered / expected
	"""
	_file:                Path

	_aggregatedTotal:     int
	_aggregatedExcluded:  int
	_aggregatedIgnored:   int
	_aggregatedExpected:  int
	_aggregatedCovered:   int
	_aggregatedUncovered: int

	_aggregatedCoverage:  float

	def __init__(self, file: Path) -> None:
		super().__init__()
		self._file = file

	@readonly
	def File(self) -> Path:
		return self._file

	@readonly
	def AggregatedTotal(self) -> int:
		return self._aggregatedTotal

	@readonly
	def AggregatedExcluded(self) -> int:
		return self._aggregatedExcluded

	@readonly
	def AggregatedIgnored(self) -> int:
		return self._aggregatedIgnored

	@readonly
	def AggregatedExpected(self) -> int:
		return self._aggregatedExpected

	@readonly
	def AggregatedCovered(self) -> int:
		return self._aggregatedCovered

	@readonly
	def AggregatedUncovered(self) -> int:
		return self._aggregatedUncovered

	@readonly
	def AggregatedCoverage(self) -> float:
		return self._aggregatedCoverage

	def Aggregate(self) -> None:
		assert self._aggregatedUncovered == self._aggregatedExpected - self._aggregatedCovered

		if self._aggregatedExpected != 0:
			self._aggregatedCoverage = self._aggregatedCovered / self._aggregatedExpected
		else:
			self._aggregatedCoverage = 1.0


@export
class ClassCoverage(Class, Coverage):
	"""
	This class represents the class documentation coverage for Python classes.
	"""
	_fields:  Dict[str, CoverageState]
	_methods: Dict[str, CoverageState]
	_classes: Dict[str, "ClassCoverage"]

	def __init__(self, name: str, parent: Union["PackageCoverage", "ClassCoverage", None] = None) -> None:
		super().__init__(name, parent)
		Coverage.__init__(self)

		if parent is not None:
			parent._classes[name] = self

		self._fields =  {}
		self._methods = {}
		self._classes = {}

	@readonly
	def Fields(self) -> Dict[str, CoverageState]:
		return self._fields

	@readonly
	def Methods(self) -> Dict[str, CoverageState]:
		return self._methods

	@readonly
	def Classes(self) -> Dict[str, "ClassCoverage"]:
		return self._classes

	def CalculateCoverage(self) -> None:
		for cls in self._classes.values():
			cls.CalculateCoverage()

		self._total, self._excluded, self._ignored, self._expected, self._covered = \
			self._CountCoverage(zip(
				self._fields.values(),
				self._methods.values()
			))

		super().CalculateCoverage()

	def __str__(self) -> str:
		return f"<ClassCoverage - tot:{self._total}, ex:{self._excluded}, ig:{self._ignored}, exp:{self._expected}, cov:{self._covered}, un:{self._uncovered} => {self._coverage:.1%}>"


@export
class ModuleCoverage(Module, AggregatedCoverage):
	"""
	This class represents the module documentation coverage for Python modules.
	"""
	_variables: Dict[str, CoverageState]
	_functions: Dict[str, CoverageState]
	_classes:   Dict[str, ClassCoverage]

	def __init__(self, name: str, file: Path, parent: Nullable["PackageCoverage"] = None) -> None:
		super().__init__(name, parent)
		AggregatedCoverage.__init__(self, file)

		if parent is not None:
			parent._modules[name] = self

		self._file =      file
		self._variables = {}
		self._functions = {}
		self._classes =   {}

	@readonly
	def Variables(self) -> Dict[str, CoverageState]:
		return self._variables

	@readonly
	def Functions(self) -> Dict[str, CoverageState]:
		return self._functions

	@readonly
	def Classes(self) -> Dict[str, ClassCoverage]:
		return self._classes

	def CalculateCoverage(self) -> None:
		for cls in self._classes.values():
			cls.CalculateCoverage()

		self._total, self._excluded, self._ignored, self._expected, self._covered = \
			self._CountCoverage(zip(
				self._variables.values(),
				self._functions.values()
			))

		super().CalculateCoverage()

	def Aggregate(self) -> None:
		self._aggregatedTotal =     self._total
		self._aggregatedExcluded =  self._excluded
		self._aggregatedIgnored =   self._ignored
		self._aggregatedExpected =  self._expected
		self._aggregatedCovered =   self._covered
		self._aggregatedUncovered = self._uncovered

		for cls in self._classes.values():
			self._aggregatedTotal +=     cls._total
			self._aggregatedExcluded +=  cls._excluded
			self._aggregatedIgnored +=   cls._ignored
			self._aggregatedExpected +=  cls._expected
			self._aggregatedCovered +=   cls._covered
			self._aggregatedUncovered += cls._uncovered

		super().Aggregate()

	def __str__(self) -> str:
		return f"<ModuleCoverage - tot:{self._total}|{self._aggregatedTotal}, ex:{self._excluded}|{self._aggregatedExcluded}, ig:{self._ignored}|{self._aggregatedIgnored}, exp:{self._expected}|{self._aggregatedExpected}, cov:{self._covered}|{self._aggregatedCovered}, un:{self._uncovered}|{self._aggregatedUncovered} => {self._coverage:.1%}|{self._aggregatedCoverage:.1%}>"


@export
class PackageCoverage(Package, AggregatedCoverage):
	"""
	This class represents the package documentation coverage for Python packages.
	"""
	_fileCount: int
	_variables: Dict[str, CoverageState]
	_functions: Dict[str, CoverageState]
	_classes:   Dict[str, ClassCoverage]
	_modules:   Dict[str, ModuleCoverage]
	_packages:  Dict[str, "PackageCoverage"]

	def __init__(self, name: str, file: Path, parent: Nullable["PackageCoverage"] = None) -> None:
		super().__init__(name, parent)
		AggregatedCoverage.__init__(self, file)

		if parent is not None:
			parent._packages[name] = self

		self._file =      file
		self._fileCount = 1
		self._variables = {}
		self._functions = {}
		self._classes =   {}
		self._modules =   {}
		self._packages =  {}

	@readonly
	def FileCount(self) -> int:
		return self._fileCount

	@readonly
	def Variables(self) -> Dict[str, CoverageState]:
		return self._variables

	@readonly
	def Functions(self) -> Dict[str, CoverageState]:
		return self._functions

	@readonly
	def Classes(self) -> Dict[str, ClassCoverage]:
		return self._classes

	@readonly
	def Modules(self) -> Dict[str, ModuleCoverage]:
		return self._modules

	@readonly
	def Packages(self) -> Dict[str, "PackageCoverage"]:
		return self._packages

	def __getitem__(self, key: str) -> Union["PackageCoverage", ModuleCoverage]:
		try:
			return self._modules[key]
		except KeyError:
			return self._packages[key]

	def CalculateCoverage(self) -> None:
		for cls in self._classes.values():
			cls.CalculateCoverage()

		for mod in self._modules.values():
			mod.CalculateCoverage()

		for pkg in self._packages.values():
			pkg.CalculateCoverage()

		self._total, self._excluded, self._ignored, self._expected, self._covered = \
			self._CountCoverage(zip(
				self._variables.values(),
				self._functions.values()
			))

		super().CalculateCoverage()

	def Aggregate(self) -> None:
		self._fileCount =           len(self._modules) + 1
		self._aggregatedTotal =     self._total
		self._aggregatedExcluded =  self._excluded
		self._aggregatedIgnored =   self._ignored
		self._aggregatedExpected =  self._expected
		self._aggregatedCovered =   self._covered
		self._aggregatedUncovered = self._uncovered

		for pkg in self._packages.values():
			pkg.Aggregate()
			self._fileCount +=           pkg._fileCount
			self._aggregatedTotal +=     pkg._total
			self._aggregatedExcluded +=  pkg._excluded
			self._aggregatedIgnored +=   pkg._ignored
			self._aggregatedExpected +=  pkg._expected
			self._aggregatedCovered +=   pkg._covered
			self._aggregatedUncovered += pkg._uncovered

		for mod in self._modules.values():
			mod.Aggregate()
			self._aggregatedTotal +=     mod._total
			self._aggregatedExcluded +=  mod._excluded
			self._aggregatedIgnored +=   mod._ignored
			self._aggregatedExpected +=  mod._expected
			self._aggregatedCovered +=   mod._covered
			self._aggregatedUncovered += mod._uncovered

		super().Aggregate()

	def __str__(self) -> str:
		return f"<PackageCoverage - tot:{self._total}|{self._aggregatedTotal}, ex:{self._excluded}|{self._aggregatedExcluded}, ig:{self._ignored}|{self._aggregatedIgnored}, exp:{self._expected}|{self._aggregatedExpected}, cov:{self._covered}|{self._aggregatedCovered}, un:{self._uncovered}|{self._aggregatedUncovered} => {self._coverage:.1%}|{self._aggregatedCoverage:.1%}>"


@export
class DocStrCoverageError(DocCoverageException):
	pass


@export
class DocStrCoverage(metaclass=ExtendedType):
	"""
	A wrapper class for the docstr_coverage package and it's analyzer producing a documentation coverage model.
	"""
	from docstr_coverage import ResultCollection

	_packageName:     str
	_searchDirectory: Path
	_moduleFiles:     List[Path]
	_coverageReport:  ResultCollection

	def __init__(self, packageName: str, directory: Path) -> None:
		if not directory.exists():
			raise DocStrCoverageError(f"Package source directory '{directory}' does not exist.") from FileNotFoundError(f"Directory '{directory}' does not exist.")

		self._searchDirectory = directory
		self._packageName = packageName
		self._moduleFiles = [file for file in directory.glob("**/*.py")]

	@readonly
	def SearchDirectories(self) -> Path:
		return self._searchDirectory

	@readonly
	def PackageName(self) -> str:
		return self._packageName

	@readonly
	def ModuleFiles(self) -> List[Path]:
		return self._moduleFiles

	@readonly
	def CoverageReport(self) -> ResultCollection:
		return self._coverageReport

	def Analyze(self) -> ResultCollection:
		from docstr_coverage import analyze, ResultCollection

		self._coverageReport: ResultCollection = analyze(self._moduleFiles, show_progress=False)
		return self._coverageReport

	def Convert(self) -> PackageCoverage:
		from docstr_coverage.result_collection import FileCount

		rootPackageCoverage = PackageCoverage(self._packageName, self._searchDirectory / "__init__.py")

		for key, value in self._coverageReport.files():
			path: Path = key.relative_to(self._searchDirectory)
			perFileResult: FileCount = value.count_aggregate()

			moduleName = path.stem
			modulePath = path.parent.parts

			currentCoverageObject: AggregatedCoverage = rootPackageCoverage
			for packageName in modulePath:
				try:
					currentCoverageObject = currentCoverageObject[packageName]
				except KeyError:
					currentCoverageObject = PackageCoverage(packageName, path, currentCoverageObject)

			if moduleName != "__init__":
				currentCoverageObject = ModuleCoverage(moduleName, path, currentCoverageObject)

			currentCoverageObject._expected = perFileResult.needed
			currentCoverageObject._covered = perFileResult.found
			currentCoverageObject._uncovered = perFileResult.missing

			if currentCoverageObject._expected != 0:
				currentCoverageObject._coverage = currentCoverageObject._covered / currentCoverageObject._expected
			else:
				currentCoverageObject._coverage = 1.0

			if currentCoverageObject._uncovered != currentCoverageObject._expected - currentCoverageObject._covered:
				currentCoverageObject._coverage = -2.0

		return rootPackageCoverage

	del ResultCollection
