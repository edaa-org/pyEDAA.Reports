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
from datetime import datetime
from pathlib import Path
from sys import version_info
from time import perf_counter_ns
from typing  import Tuple, List, Dict, Optional as Nullable
from xml.dom import minidom, Node
from xml.dom.minidom import Element

from pyTooling.Common import getFullyQualifiedName
from pyTooling.Decorators import export
from pyTooling.MetaClasses import ExtendedType


@export
class CoberturaException(Exception):
	pass


@export
class DuplicateEntity(CoberturaException):
	pass


@export
class DuplicatePackageException(DuplicateEntity):
	pass


@export
class DuplicateClassException(DuplicateEntity):
	pass


@export
class DuplicateMethodException(DuplicateEntity):
	pass


@export
class DuplicateLineException(DuplicateEntity):
	pass


@export
class DuplicateConditionException(DuplicateEntity):
	pass


@export
class Entity(metaclass=ExtendedType, slots=True):
	_parent: "Entity"

	def __init__(self, parent: "Entity" = None) -> None:
		self._parent = parent

	@property
	def Parent(self) -> Nullable["Entity"]:
		return self._parent

	@Parent.setter
	def Parent(self, value: "Entity"):
		if not isinstance(value, Entity):
			ex = TypeError(f"Parameter 'value' is not of type 'Entity'.")
			if version_info >= (3, 11):  # pragma: no cover
				ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
			raise ex

		self._parent = value


@export
class Document(Entity):
	_path: Path
	_generatorVersion: str
	_timestamp: datetime

	_sources: List[str]
	_packages: Dict[str, "Package"]

	_validLines: int
	_coveredLines: int
	_lineRate: float

	_validBranches: int
	_coveredBranches: int
	_branchRate: float

	_complexity: float

	_readingByMiniDom: float  #: TODO: replace by Timer
	_modelConversion: float   #: TODO: replace by Timer

	def __init__(self, path: Path) -> None:
		self._path = path

		self._sources = []
		self._packages = {}

		if not self._path.exists():
			raise CoberturaException(f"Cobertura code coverage file '{self._path!s}' not found.") \
				from FileNotFoundError(f"File '{self._path!s}' not found.")

		try:
			startMiniDom = perf_counter_ns()
			root = minidom.parse(str(self._path)).documentElement
			self._readingByMiniDom = (perf_counter_ns() - startMiniDom) / 1e9
		except Exception as ex:
			raise CoberturaException(f"Couldn't open '{self._path!s}'.") from ex

		startConversion = perf_counter_ns()
		self._ParseRootElement(root)
		self._modelConversion = (perf_counter_ns() - startConversion) / 1e9

	def _ParseRootElement(self, rootNode: Element) -> None:
		self._generatorVersion = rootNode.getAttribute("version")
		timestamp = int(rootNode.getAttribute("timestamp"))
		self._timestamp = datetime.fromtimestamp(timestamp/1000)

		self._validLines = int(rootNode.getAttribute("lines-valid"))
		self._coveredLines = int(rootNode.getAttribute("lines-covered"))
		self._lineRate = float(rootNode.getAttribute("line-rate"))

		self._validBranches = int(rootNode.getAttribute("branches-valid"))
		self._coveredBranches = int(rootNode.getAttribute("branches-covered"))
		self._branchRate = float(rootNode.getAttribute("branch-rate"))

		self._complexity = float(rootNode.getAttribute("complexity"))

		for node in rootNode.childNodes:
			if node.nodeName == "sources":
				self._ParseSources(node)
			elif node.nodeName == "packages":
				self._ParsePackages(node)

	def _ParseSources(self, sourcesNode: Element) -> None:
		for sourceNode in sourcesNode.childNodes:
			if sourceNode.nodeType == Node.ELEMENT_NODE and sourceNode.tagName == "source":
				self._ParseSource(sourceNode)

	def _ParseSource(self, sourceNode: Element) -> None:
		if len(sourceNode.childNodes) != 1:
			raise CoberturaException(f"Source tag has no content")

		contentNode = sourceNode.firstChild
		self._sources.append(contentNode.nodeValue)

	def _ParsePackages(self, packagesNode: Element) -> None:
		for packageNode in packagesNode.childNodes:
			if packageNode.nodeType == Node.ELEMENT_NODE and packageNode.tagName == "package":
				self._ParsePackage(packageNode)

	def _ParsePackage(self, packageNode: Element) -> None:
		packageName = packageNode.getAttribute("name")
		lineRate = float(packageNode.getAttribute("line-rate"))
		branchRate = float(packageNode.getAttribute("branch-rate"))
		complexity = float(packageNode.getAttribute("complexity"))

		package = Package(packageName, lineRate, branchRate, complexity)
		package.Parent = self

		for node in packageNode.childNodes:
			if node.nodeName == "classes":
				self._ParseClasses(node, package)

	def _ParseClasses(self, classesNode: Element, package: "Package") -> None:
		for classNode in classesNode.childNodes:
			if classNode.nodeType == Node.ELEMENT_NODE and classNode.tagName == "class":
				self._ParseClass(classNode, package)

	def _ParseClass(self, classNode: Element, package: "Package") -> None:
		className = classNode.getAttribute("name")
		fileName = Path(classNode.getAttribute("filename"))
		lineRate = float(classNode.getAttribute("line-rate"))
		branchRate = float(classNode.getAttribute("branch-rate"))
		complexity = float(classNode.getAttribute("complexity"))

		cls = Class(className, fileName, lineRate, branchRate, complexity)
		cls.Parent = package

		for node in classNode.childNodes:
			if node.nodeName == "methods":
				self._ParseMethods(node, cls)
			elif node.nodeName == "lines":
				self._ParseLines(node, cls)

	def _ParseMethods(self, methodesNode: Element, cls: "Class") -> None:
		for methodNode in methodesNode.childNodes:
			if methodNode.nodeType == Node.ELEMENT_NODE and methodNode.tagName == "method":
				self._ParseMethod(methodNode, cls)

	def _ParseLines(self, linesNode: Element, cls: "Class") -> None:
		for lineNode in linesNode.childNodes:
			if lineNode.nodeType == Node.ELEMENT_NODE and lineNode.tagName == "line":
				self._ParseLine(lineNode, cls)

	def _ParseMethod(self, methodNode: Element, cls: "Class") -> None:
		methodName = methodNode.getAttribute("name")
		signature = methodNode.getAttribute("signature")
		lineRate = float(methodNode.getAttribute("line-rate"))
		branchRate = float(methodNode.getAttribute("branch-rate"))

		method = Method(methodName, signature, lineRate, branchRate)
		method.Parent = cls

		for node in methodNode.childNodes:
			if node.nodeName == "lines":
				self._ParseLines(node, method)

	def _ParseLine(self, lineNode: Element, cls: "Class") -> None:
		lineNumber = int(lineNode.getAttribute("number"))
		hits = int(lineNode.getAttribute("hits"))
		branch = lineNode.hasAttribute("branch") and bool(lineNode.getAttribute("branch"))

		line = Line(lineNumber, hits, branch)
		line.Parent = cls

		for node in lineNode.childNodes:
			if node.nodeName == "conditions":
				self._ParseConditions(node, line)

	def _ParseConditions(self, conditionsNode: Element, line: "Line") -> None:
		for conditionNode in conditionsNode.childNodes:
			if conditionNode.nodeType == Node.ELEMENT_NODE and conditionNode.tagName == "condition":
				self._ParseCondition(conditionNode, line)

	def _ParseCondition(self, conditionNode: Element, line: "Line") -> None:
		lineNumber = int(conditionNode.getAttribute("number"))
		conditionType = conditionNode.getAttribute("type")
		coverage = conditionNode.getAttribute("coverage")

		cond = Condition(lineNumber, conditionType, coverage)
		cond.Parent = line

	def GetStatistics(self) -> Tuple[int, int, float]:
		validLines = 0
		coveredLines = 0
		for package in self._packages.values():
			for cls in package._classes.values():
				validLines += len(cls._lines)
				for line in cls._lines.values():
					if line._hits > 0:
						coveredLines += 1

		return (validLines, coveredLines, coveredLines/validLines)


@export
class Package(Entity):
	_name: str

	_lineRate: float
	_branchRate: float
	_complexity: float

	_classes: Dict[str, "Class"]

	def __init__(self, name: str, lineRate: float, branchRate: float, complexity: float, parent: Nullable[Document] = None) -> None:
		super().__init__(parent)

		self._name = name
		self._lineRate = lineRate
		self._branchRate = branchRate
		self._complexity = complexity

		self._classes = {}

		if parent is not None:
			if name in parent._packages:
				raise DuplicatePackageException(f"Duplicate package '{name}'")

			parent._packages[name] = self

	@property
	def Parent(self) -> Nullable[Document]:
		return self._parent

	@Parent.setter
	def Parent(self, value: Document):
		if not isinstance(value, Document):
			ex = TypeError(f"Parameter 'value' is not of type 'Document'.")
			if version_info >= (3, 11):  # pragma: no cover
				ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
			raise ex

		if self._name in value._packages:
			raise DuplicatePackageException(f"Duplicate package '{self._name}'")

		self._parent = value
		value._packages[self._name] = self


@export
class Class(Entity):
	_name: str
	_fileName: Path

	_lineRate: float
	_branchRate: float
	_complexity: float

	_lines:   Dict[int, "Line"]
	_methods: Dict[str, "Method"]

	def __init__(self, name: str, filename: Path, lineRate: float, branchRate: float, complexity: float, parent: Nullable[Package] = None) -> None:
		super().__init__(parent)

		self._name = name
		self._fileName = filename
		self._lineRate = lineRate
		self._branchRate = branchRate
		self._complexity = complexity

		self._lines = {}
		self._methods = {}

		if parent is not None:
			if name in parent._classes:
				raise DuplicateClassException(f"Duplicate class '{name}'")

			parent._classes[name] = self

	@property
	def Parent(self) -> Nullable[Package]:
		return self._parent

	@Parent.setter
	def Parent(self, value: Package):
		if not isinstance(value, Package):
			ex = TypeError(f"Parameter 'value' is not of type 'Package'.")
			if version_info >= (3, 11):  # pragma: no cover
				ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
			raise ex

		if self._name in value._classes:
			raise DuplicateClassException(f"Duplicate class '{self._name}'")

		self._parent = value
		value._classes[self._name] = self


@export
class Method(Entity):
	_name: str
	_signature: str

	_lineRate: float
	_branchRate: float

	_lines: Dict[int, "Line"]

	def __init__(self, name: str, signature: str, lineRate: float, branchRate: float, parent: Nullable[Class] = None) -> None:
		super().__init__(parent)

		self._name = name
		self._signature = signature
		self._lineRate = lineRate
		self._branchRate = branchRate

		self._lines = {}

		if parent is not None:
			if name in parent._methods:
				raise DuplicateMethodException(f"Duplicate method '{name}'")

			parent._methods[name] = self

	@property
	def Parent(self) -> Nullable[Class]:
		return self._parent

	@Parent.setter
	def Parent(self, value: Class):
		if not isinstance(value, Class):
			ex = TypeError(f"Parameter 'value' is not of type 'Document'.")
			if version_info >= (3, 11):  # pragma: no cover
				ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
			raise ex

		if self._name in value._methods:
			raise DuplicateMethodException(f"Duplicate method '{self._name}'")

		self._parent = value
		value._methods[self._name] = self


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
			if number in parent._lines:
				raise DuplicateLineException(f"Duplicate line {number}")

			parent._lines[number] = self

	@property
	def Parent(self) -> Nullable[Class | Method]:
		return self._parent

	@Parent.setter
	def Parent(self, value: Class | Method):
		if not isinstance(value, (Class, Method)):
			ex = TypeError(f"Parameter 'value' is not of type 'Class' or 'Method'.")
			if version_info >= (3, 11):  # pragma: no cover
				ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
			raise ex

		if self._number in value._lines:
			raise DuplicateLineException(f"Duplicate line {self._number}")

		self._parent = value
		value._lines[self._number] = self


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
			if number in parent._conditions:
				raise DuplicateConditionException(f"Duplicate condition for line {number}.")

			parent._conditions[number] = self

	@property
	def Parent(self) -> Nullable[Line]:
		return self._parent

	@Parent.setter
	def Parent(self, value: Line):
		if not isinstance(value, Line):
			ex = TypeError(f"Parameter 'value' is not of type 'Document'.")
			if version_info >= (3, 11):  # pragma: no cover
				ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
			raise ex

		if self._number in value._conditions:
			raise DuplicateConditionException(f"Duplicate condition for line {self._number}.")

		self._parent = value
		value._conditions[self._number] = self
