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
"""
**Abstract documentation coverage data model for Python code.**
"""
from pathlib import Path
from typing  import Optional as Nullable, Dict, Union

from pyTooling.Decorators  import export, readonly
from pyTooling.MetaClasses import ExtendedType


@export
class Coverage(metaclass=ExtendedType, slots=True):
	_parent:    Nullable["Coverage"]
	_name:      str

	def __init__(self, name: str, parent: Nullable["Coverage"] = None) -> None:
		self._parent = parent
		self._name =   name

	@readonly
	def Parent(self) -> Nullable["Coverage"]:
		return self._parent

	@readonly
	def Name(self) -> str:
		return self._name


@export
class AggregatedCoverage(Coverage):
	_file:               Path

	_totalStatements:    int
	_excludedStatements: int
	_coveredStatements:  int
	_missingStatements:  int
	_totalBranches:      int
	_partialBranches:    int

	_coverage:           float

	def __init__(self, name: str, file: Path, parent: Nullable["Coverage"] = None) -> None:
		super().__init__(name, parent)

		self._file = file

		self._totalStatements =    0
		self._excludedStatements = 0
		self._coveredStatements =  0
		self._missingStatements =  0

		self._totalBranches =      0
		self._coveredBranches =    0
		self._partialBranches =    0
		self._missingBranches =    0

		self._coverage = -1.0

	@readonly
	def File(self) -> Path:
		return self._file

	@readonly
	def TotalStatements(self) -> int:
		return self._totalStatements

	@readonly
	def ExcludedStatements(self) -> int:
		return self._excludedStatements

	@readonly
	def CoveredStatements(self) -> int:
		return self._coveredStatements

	@readonly
	def MissingStatements(self) -> int:
		return self._missingStatements

	@readonly
	def TotalBranches(self) -> int:
		return self._totalBranches

	@readonly
	def CoveredBranches(self) -> int:
		return self._coveredBranches

	@readonly
	def PartialBranches(self) -> int:
		return self._partialBranches

	@readonly
	def MissingBranches(self) -> int:
		return self._missingBranches

	@readonly
	def Coverage(self) -> float:
		return self._coverage


@export
class ModuleCoverage(AggregatedCoverage):
	def __init__(self, name: str, file: Path, parent: Nullable["PackageCoverage"] = None) -> None:
		super().__init__(name, file, parent)

		if parent is not None:
			parent._modules[name] = self


@export
class PackageCoverage(AggregatedCoverage):
	_fileCount: int

	_modules:   Dict[str, ModuleCoverage]
	_packages:  Dict[str, "PackageCoverage"]

	def __init__(self, name: str, file: Path, parent: Nullable["PackageCoverage"] = None) -> None:
		super().__init__(name, file, parent)

		if parent is not None:
			parent._packages[name] = self

		self._fileCount = 1
		self._modules =   {}
		self._packages =  {}

	@readonly
	def FileCount(self) -> int:
		return self._fileCount

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
