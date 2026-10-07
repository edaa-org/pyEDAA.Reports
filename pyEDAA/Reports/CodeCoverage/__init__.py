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
from enum import Flag
from pathlib import Path
from sys import version_info
from typing import Optional as Nullable, Dict, Any, Tuple, List, Union

from pyTooling.Common import getFullyQualifiedName
from pyTooling.Decorators import export, readonly
from pyTooling.MetaClasses import ExtendedType

from pyEDAA.Reports.CodeCoverage.Cobertura import Document


@export
class CoverageState(Flag):
	Unknown = 0
	Excluded = 1
	Ignored = 2
	NotUsed = 4
	Used = 8

	Incomplete = 16
	Exception = 32

	Covered = 256
	Uncovered = 512

	Declaration = 1024
	Initializer = 2048


@export
class Base(metaclass=ExtendedType, slots=True):
	_parent: Nullable["Base"]
	_name:   str
	_status: CoverageState

	def __init__(self, name: str, parent: Nullable["Base"] = None) -> None:
		if name is None:
			raise ValueError(f"Parameter 'name' must not be None.")

		self._parent = parent
		self._name = name
		self._status = CoverageState.Unknown

	@property
	def Parent(self) -> Nullable["Base"]:
		return self._parent

	@property
	def Name(self) -> str:
		return self._name

	@property
	def Status(self) -> CoverageState:
		return self._status




















@export
class Entity(metaclass=ExtendedType, slots=True):
	_parent: "Entity"

	def __init__(self, parent: "Entity" = None) -> None:
		self._parent = parent


@export
class Coverage(Entity):
	_files: Dict[Path, "File"]
	_directories: Dict[Path, Any]
	_groups: Dict[str, Any]
	_packages: Dict[str, "Package"]

	def __init__(self) -> None:
		super().__init__(None)

		self._files = {}
		self._directories = {}
		self._groups = {}
		self._packages = {}

	def ImportCobertura(self, coberturaDocument: Document):
		if not isinstance(coberturaDocument, Document):
			ex = TypeError(f"Parameter 'coberturaDocument' is not a Cobertura code coverage database.")
			if version_info >= (3, 11):  # pragma: no cover
				ex.add_note(f"Got type '{getFullyQualifiedName(coberturaDocument)}'.")
			raise ex

		for package in coberturaDocument._packages.values():
			container = self

			packageNameParts = package._name.split(".")
			for packageNamePart in packageNameParts:
				if packageNamePart in container._packages:
					container = container._packages[packageNamePart]
				else:
					pkg = Package(packageNamePart, container)
					container._packages[packageNamePart] = pkg
					container = pkg

			for cls in package._classes.values():
				c = Class(cls._name, container)

				for line in cls._lines.values():
					l = Line(line._number, line._hits, line._branch, c)


@export
class Package(Entity):
	_name: str
	_packages: Dict[str, "Package"]
	_classes: Dict[str, "Class"]

	def __init__(self, name: str, parent: Nullable[Coverage] = None) -> None:
		super().__init__(parent)

		self._name = name
		self._packages = {}
		self._classes = {}

		if parent is not None:
			parent._packages[name] = self


@export
class Class(Entity):
	_name:    str
	_lines:   Dict[int, "Line"]
	_methods: Dict[str, "Method"]
	_classes: Dict[str, "Class"]

	def __init__(self, name: str, parent: Nullable[Package] = None) -> None:
		super().__init__(parent)

		self._name = name

		self._lines = {}
		self._methods = {}
		self._classes = {}

		if parent is not None:
			parent._classes[name] = self


@export
class Method(Entity):
	_name: str
	_signature: str

	_lines: Dict[int, "Line"]

	def __init__(self, name: str, signature: str, parent: Nullable[Class] = None) -> None:
		super().__init__(parent)

		self._name = name
		self._signature = signature

		self._lines = {}

		if parent is not None:
			parent._methods[name] = self


@export
class Line(Entity):
	_number: int
	_hits: int
	_branch: bool
	_conditions: Dict[int, "Condition"]
	_conditionCoverage: Tuple[int, int]
	_missingBranches:   List[int]

	def __init__(self, number: int, hits: int, branch: bool, parent: Class | Method = None) -> None:
		super().__init__(parent)

		self._number = number
		self._hits = hits
		self._branch = branch
		self._conditionCoverage = None
		self._missingBranches = None

		self._conditions = {}

		if parent is not None:
			parent._lines[number] = self


@export
class Condition(Entity):
	_number: int
	_type: str
	_coverage: float

	def __init__(self, number: int, conditionType: str, coverage: float, parent: Nullable[Line] = None) -> None:
		super().__init__(parent)

		self._number = number
		self._type = conditionType
		self._coverage = coverage

		if parent is not None:
			parent._conditions[number] = self


@export
class Branch:
	pass


@export
class Instruction:
	pass


# @export
# class Line:
# 	pass


@export
class State:
	pass


@export
class Transition:
	pass


@export
class Statemachine:
	pass


@export
class File:
	pass
