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
# Copyright 2026-2026 Electronic Design Automation Abstraction (EDA²)                                                  #
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
The elements of the Cobertura XML format below ``<coverage>``: its packages, classes, methods, lines and conditions.
"""
from __future__                  import annotations

from typing                      import Iterable, Optional as Nullable

from lxml.etree                  import Element as XMLElement, SubElement, _Element
from pyTooling.Common            import getFullyQualifiedName
from pyTooling.Decorators        import export, readonly
from pyTooling.MetaClasses       import ExtendedType

from pyEDAA.Reports.CodeCoverage import Class as cc_Class, CoverageSummary, File as cc_File, Function as cc_Function
from pyEDAA.Reports.CodeCoverage import Line as cc_Line, LineCoverageStatus, Method as cc_Method, Module as cc_Module
from pyEDAA.Reports.CodeCoverage import Package as cc_Package, SourceFile as cc_SourceFile, Unit as cc_Unit


@export
class Condition(metaclass=ExtendedType, slots=True):
	"""
	A ``<condition>`` of a line: a condition of a branching line, as gcovr writes it.
	"""

	_number:   int  #: Number of the condition in its line.
	_type:     str  #: Kind of condition, e.g. ``jump``.
	_coverage: str  #: Coverage of the condition, e.g. ``50%``.

	def __init__(self, number: int, conditionType: str, coverage: str) -> None:
		"""
		Initialize a condition.

		:param number:        Number of the condition in its line.
		:param conditionType: Kind of condition, e.g. ``jump``.
		:param coverage:      Coverage of the condition, e.g. ``50%``.
		"""
		self._number =   number
		self._type =     conditionType
		self._coverage = coverage

	@readonly
	def Number(self) -> int:
		"""
		Read-only property to access the number of the condition in its line (:attr:`_number`).

		:returns: The number.
		"""
		return self._number

	@readonly
	def Type(self) -> str:
		"""
		Read-only property to access the kind of condition (:attr:`_type`).

		:returns: The kind, e.g. ``jump``.
		"""
		return self._type

	@readonly
	def Coverage(self) -> str:
		"""
		Read-only property to access the coverage of the condition (:attr:`_coverage`).

		:returns: The coverage, e.g. ``50%``.
		"""
		return self._coverage

	def Generate(self) -> _Element:
		"""
		Generate the condition's ``<condition>`` element.

		:returns: The ``<condition>`` element.
		"""
		conditionElement = XMLElement("condition")
		conditionElement.attrib["number"] =   str(self._number)
		conditionElement.attrib["type"] =     self._type
		conditionElement.attrib["coverage"] = self._coverage
		return conditionElement


@export
class Line(metaclass=ExtendedType, slots=True):
	"""
	A ``<line>``: a line's hits, whether it branches, its condition coverage and its conditions.
	"""

	_number:            int                         #: Line number.
	_hits:              int                         #: How often the line ran.
	_branch:            bool                        #: Whether the line branches.
	_conditionCoverage: Nullable[tuple[int, int]]   #: Taken and all branches, if the line states them.
	_conditions:        list[Condition]             #: The line's conditions.

	def __init__(
		self,
		number: int,
		hits: int,
		branch: bool = False,
		conditionCoverage: Nullable[tuple[int, int]] = None,
		conditions: list[Condition] | None = None
	) -> None:
		"""
		Initialize a line.

		:param number:            Line number.
		:param hits:              How often the line ran.
		:param branch:            Optional, whether the line branches. Default: ``False``.
		:param conditionCoverage: Optional, taken and all branches. Default: ``None``.
		:param conditions:        Optional, the line's conditions. Default: none.
		"""
		self._number =            number
		self._hits =              hits
		self._branch =            branch
		self._conditionCoverage = conditionCoverage
		self._conditions =        [] if conditions is None else conditions

	@readonly
	def Number(self) -> int:
		"""
		Read-only property to access the line number (:attr:`_number`).

		:returns: The line number.
		"""
		return self._number

	@readonly
	def Hits(self) -> int:
		"""
		Read-only property to access how often the line ran (:attr:`_hits`).

		:returns: The hits.
		"""
		return self._hits

	@readonly
	def Branch(self) -> bool:
		"""
		Read-only property to access whether the line branches (:attr:`_branch`).

		:returns: ``True``, if the line branches.
		"""
		return self._branch

	@readonly
	def ConditionCoverage(self) -> Nullable[tuple[int, int]]:
		"""
		Read-only property to access the line's taken and all branches (:attr:`_conditionCoverage`).

		:returns: The taken and all branches, e.g. ``(1, 2)``; ``None`` if the line doesn't state them.
		"""
		return self._conditionCoverage

	@readonly
	def Conditions(self) -> list[Condition]:
		"""
		Read-only property to access the line's conditions (:attr:`_conditions`).

		:returns: The conditions.
		"""
		return self._conditions

	@classmethod
	def FromLine(cls, line: cc_Line) -> Line:
		"""
		Convert a line of the common model.

		A line without count has ``1`` hit, if it ran, else ``0``. A line with branches is a branching line; its condition
		coverage counts its branches with state :attr:`~pyEDAA.Reports.CodeCoverage.LineCoverageStatus.Covered` and all its
		branches.

		:param line:        The line of the common model.
		:returns:           The line.
		:raises ValueError: If parameter ``line`` is ``None``.
		:raises TypeError:  If parameter ``line`` isn't of type :class:`~pyEDAA.Reports.CodeCoverage.Line`.
		"""
		if line is None:
			raise ValueError(f"Parameter 'line' is None.")
		elif not isinstance(line, cc_Line):
			ex = TypeError(f"Parameter 'line' is not of type 'Line'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(line)}'.")
			raise ex

		if line._coverageCount is not None:
			hits = line._coverageCount
		elif line._status in (LineCoverageStatus.Covered, LineCoverageStatus.PartiallyCovered):
			hits = 1
		else:
			hits = 0

		if len(line._branches) == 0:
			return cls(line._lineNumber, hits)

		covered = sum(1 for branch in line._branches if branch._status is LineCoverageStatus.Covered)
		return cls(line._lineNumber, hits, True, (covered, len(line._branches)))

	def Generate(self) -> _Element:
		"""
		Generate the line's ``<line>`` element with its conditions.

		:returns: The ``<line>`` element.
		"""
		lineElement = XMLElement("line")
		lineElement.attrib["number"] = str(self._number)
		lineElement.attrib["hits"] =   str(self._hits)
		if self._branch:
			lineElement.attrib["branch"] = "true"

		if self._conditionCoverage is not None:
			covered, total = self._conditionCoverage
			percent = 100 if total == 0 else 100 * covered // total
			lineElement.attrib["condition-coverage"] = f"{percent}% ({covered}/{total})"

		if len(self._conditions) > 0:
			conditionsElement = SubElement(lineElement, "conditions")
			for condition in self._conditions:
				conditionsElement.append(condition.Generate())

		return lineElement


@export
class Element(metaclass=ExtendedType, slots=True):
	"""
	Base-class of the named elements with rates - packages, classes and methods -, as the report states the rates.
	"""

	_name:       str              #: Name of the element.
	_lineRate:   Nullable[float]  #: Line coverage, as the report states it.
	_branchRate: Nullable[float]  #: Branch coverage, as the report states it.

	def __init__(self, name: str, lineRate: Nullable[float] = None, branchRate: Nullable[float] = None) -> None:
		"""
		Initialize the name and the rates.

		:param name:       Name of the element.
		:param lineRate:   Optional, line coverage, as the report states it. Default: ``None``.
		:param branchRate: Optional, branch coverage, as the report states it. Default: ``None``.
		"""
		self._name =       name
		self._lineRate =   lineRate
		self._branchRate = branchRate

	@readonly
	def Name(self) -> str:
		"""
		Read-only property to access the element's name (:attr:`_name`).

		:returns: The name.
		"""
		return self._name

	@readonly
	def LineRate(self) -> Nullable[float]:
		"""
		Read-only property to access the line coverage, as the report states it (:attr:`_lineRate`).

		:returns: The rate in range 0.0..1.0, or ``None`` if the report doesn't state it.
		"""
		return self._lineRate

	@readonly
	def BranchRate(self) -> Nullable[float]:
		"""
		Read-only property to access the branch coverage, as the report states it (:attr:`_branchRate`).

		:returns: The rate in range 0.0..1.0, or ``None`` if the report doesn't state it.
		"""
		return self._branchRate

	@staticmethod
	def _CountLines(lines: Iterable[Line]) -> tuple[int, int, int, int]:
		"""
		Count lines and their branches.

		:param lines: The lines.
		:returns:     The number of lines, of lines, which ran, of branches, and of branches, which were taken.
		"""
		linesValid = linesCovered = branchesValid = branchesCovered = 0
		for line in lines:
			linesValid += 1
			if line._hits > 0:
				linesCovered += 1

			if line._conditionCoverage is not None:
				branchesCovered += line._conditionCoverage[0]
				branchesValid +=   line._conditionCoverage[1]

		return linesValid, linesCovered, branchesValid, branchesCovered

	@staticmethod
	def _Rates(counts: tuple[int, int, int, int]) -> tuple[float, float]:
		"""
		Compute the line and branch rates from the counts of :meth:`_CountLines`.

		:param counts: The number of lines, of lines, which ran, of branches, and of branches, which were taken.
		:returns:      The line and the branch rate in range 0.0..1.0; ``1.0`` if there is no line or no branch.
		"""
		linesValid, linesCovered, branchesValid, branchesCovered = counts
		return (
			1.0 if linesValid == 0 else linesCovered / linesValid,
			1.0 if branchesValid == 0 else branchesCovered / branchesValid
		)

	def _GenerateRates(self, xmlElement: _Element, lines: Iterable[Line]) -> None:
		"""
		Add the line and branch rate to the element's XML element: as stated, or computed from its lines.

		:param xmlElement: The element's XML element.
		:param lines:      The element's lines.
		"""
		lineRate, branchRate = self._lineRate, self._branchRate
		if lineRate is None or branchRate is None:
			computedLineRate, computedBranchRate = self._Rates(self._CountLines(lines))
			lineRate =   computedLineRate if lineRate is None else lineRate
			branchRate = computedBranchRate if branchRate is None else branchRate

		xmlElement.attrib["line-rate"] =   str(round(lineRate, 4))
		xmlElement.attrib["branch-rate"] = str(round(branchRate, 4))


@export
class Method(Element):
	"""
	A ``<method>`` of a class: its signature and lines.
	"""

	_signature: Nullable[str]    #: Signature of the method.
	_lines:     dict[int, Line]  #: The method's lines, by number.

	def __init__(
		self,
		name: str,
		signature: Nullable[str] = None,
		lineRate: Nullable[float] = None,
		branchRate: Nullable[float] = None
	) -> None:
		"""
		Initialize a method.

		:param name:       Name of the method.
		:param signature:  Optional, signature of the method. Default: ``None``.
		:param lineRate:   Optional, line coverage, as the report states it. Default: ``None``.
		:param branchRate: Optional, branch coverage, as the report states it. Default: ``None``.
		"""
		super().__init__(name, lineRate, branchRate)

		self._signature = signature
		self._lines =     {}

	@readonly
	def Signature(self) -> Nullable[str]:
		"""
		Read-only property to access the method's signature (:attr:`_signature`).

		:returns: The signature, or ``None`` if the report doesn't state it.
		"""
		return self._signature

	@readonly
	def Lines(self) -> dict[int, Line]:
		"""
		Read-only property to access the method's lines (:attr:`_lines`).

		:returns: The lines, by number.
		"""
		return self._lines

	def Generate(self) -> _Element:
		"""
		Generate the method's ``<method>`` element with its lines.

		A rate the method doesn't state is computed from its lines; a missing signature is written as empty text.

		:returns: The ``<method>`` element.
		"""
		methodElement = XMLElement("method")
		methodElement.attrib["name"] =      self._name
		methodElement.attrib["signature"] = "" if self._signature is None else self._signature
		self._GenerateRates(methodElement, self._lines.values())

		linesElement = SubElement(methodElement, "lines")
		for line in self._lines.values():
			linesElement.append(line.Generate())

		return methodElement


@export
class Class(Element):
	"""
	A ``<class>`` of a package: its source file, methods and lines.
	"""

	_filename:   str                #: Path of the class' source file, relative to a ``<source>`` directory.
	_complexity: Nullable[float]    #: Complexity, as the report states it.
	_methods:    dict[str, Method]  #: The class' methods, by name and signature.
	_lines:      dict[int, Line]    #: The class' lines, by number.

	def __init__(
		self,
		name: str,
		filename: str,
		lineRate: Nullable[float] = None,
		branchRate: Nullable[float] = None,
		complexity: Nullable[float] = None
	) -> None:
		"""
		Initialize a class.

		:param name:       Name of the class.
		:param filename:   Path of the class' source file, relative to a ``<source>`` directory.
		:param lineRate:   Optional, line coverage, as the report states it. Default: ``None``.
		:param branchRate: Optional, branch coverage, as the report states it. Default: ``None``.
		:param complexity: Optional, complexity, as the report states it. Default: ``None``.
		"""
		super().__init__(name, lineRate, branchRate)

		self._filename =   filename
		self._complexity = complexity
		self._methods =    {}
		self._lines =      {}

	@readonly
	def Filename(self) -> str:
		"""
		Read-only property to access the path of the class' source file (:attr:`_filename`).

		:returns: The path, relative to a ``<source>`` directory.
		"""
		return self._filename

	@readonly
	def Complexity(self) -> Nullable[float]:
		"""
		Read-only property to access the complexity, as the report states it (:attr:`_complexity`).

		:returns: The complexity, or ``None`` if the report doesn't state it.
		"""
		return self._complexity

	@readonly
	def Methods(self) -> dict[str, Method]:
		"""
		Read-only property to access the class' methods (:attr:`_methods`).

		:returns: The methods, by name - and signature, if two methods share a name.
		"""
		return self._methods

	@readonly
	def Lines(self) -> dict[int, Line]:
		"""
		Read-only property to access the class' lines (:attr:`_lines`).

		:returns: The lines, by number.
		"""
		return self._lines

	@classmethod
	def _FromFile(cls, file: cc_File, packages: dict[str, Package]) -> None:
		"""
		Convert a file of the common model to classes, and add them to their packages.

		:param file:     The file of the common model.
		:param packages: The packages, by name; a missing package is added.
		"""
		filename = file.Path.as_posix()
		directories = file.Path.parent.parts
		directoryPackage = ".".join(directories) if len(directories) > 0 else "."

		fileClasses: list[Class] = []

		def addClass(packageName: str, className: str) -> Class:
			"""
			Nested function creating a class of this file, and adding it to its package.

			:param packageName: Name of the package.
			:param className:   Name of the class.
			:returns:           The class.
			"""
			if (package := packages.get(packageName)) is None:
				package = packages[packageName] = Package(packageName, complexity=0.0)

			klass = cls(className, filename, complexity=0.0)
			package._classes.append(klass)
			fileClasses.append(klass)
			return klass

		classes: dict[cc_Unit, Class] = {}
		spanned: list[cc_Unit] = []
		for unit in file._units:
			if not isinstance(unit, (cc_SourceFile, cc_Module, cc_Class)):
				continue

			chain: list[cc_Unit] = []
			element: cc_Unit | CoverageSummary = unit
			while isinstance(element, cc_Unit):
				chain.insert(0, element)
				element = element._parent

			packageCount = 0
			while isinstance(chain[packageCount], cc_Package):
				packageCount += 1

			classes[unit] = addClass(
				".".join(part._name for part in chain[:packageCount]) if packageCount > 0 else directoryPackage,
				".".join(part._name for part in chain[packageCount:])
			)
			if unit._startLine is not None and unit._endLine is not None:
				spanned.append(unit)

		# outer units first: an inner unit overwrites the owner of its lines
		owners: dict[int, Class] = {}
		for unit in sorted(spanned, key=lambda unit: (unit._startLine._lineNumber, -unit._endLine._lineNumber)):
			for line in file.IterateLines(unit._startLine, unit._endLine):
				owners[line._lineNumber] = classes[unit]

		fallback: Nullable[Class] = None
		lines: dict[int, Line] = {}
		for commonLine in file.IterateLines():
			if commonLine._status is LineCoverageStatus.Excluded:
				continue

			line = lines[commonLine._lineNumber] = Line.FromLine(commonLine)
			if (klass := owners.get(line._number)) is None:
				if fallback is None:
					fallback = addClass(directoryPackage, file._name)
				klass = fallback

			klass._lines[line._number] = line

		for unit in file._units:
			if not isinstance(unit, (cc_Function, cc_Method)):
				continue

			names = [unit._name]
			element = unit._parent
			while isinstance(element, cc_Unit) and element not in classes:
				if not isinstance(element, cc_Package):
					names.insert(0, element._name)
				element = element._parent

			if isinstance(element, cc_Unit):
				klass = classes[element]
			else:
				if fallback is None:
					fallback = addClass(directoryPackage, file._name)
				klass = fallback

			method = Method(".".join(names))
			if unit._startLine is not None and unit._endLine is not None:
				for commonLine in file.IterateLines(unit._startLine, unit._endLine):
					if (line := lines.get(commonLine._lineNumber)) is not None:
						method._lines[line._number] = line

			method._lineRate, method._branchRate = cls._Rates(cls._CountLines(method._lines.values()))
			klass._methods[method._name] = method

		for klass in fileClasses:
			klass._lineRate, klass._branchRate = cls._Rates(cls._CountLines(klass._lines.values()))

	def Generate(self) -> _Element:
		"""
		Generate the class' ``<class>`` element with its methods and lines.

		A rate the class doesn't state is computed from its lines; a missing complexity is written as ``0``.

		:returns: The ``<class>`` element.
		"""
		classElement = XMLElement("class")
		classElement.attrib["name"] =     self._name
		classElement.attrib["filename"] = self._filename
		self._GenerateRates(classElement, self._lines.values())
		classElement.attrib["complexity"] = str(0 if self._complexity is None else self._complexity)

		methodsElement = SubElement(classElement, "methods")
		for method in self._methods.values():
			methodsElement.append(method.Generate())

		linesElement = SubElement(classElement, "lines")
		for line in self._lines.values():
			linesElement.append(line.Generate())

		return classElement


@export
class Package(Element):
	"""
	A ``<package>``: its classes.
	"""

	_complexity: Nullable[float]   #: Complexity, as the report states it.
	_classes:    list[Class]       #: The package's classes, in the report's order.

	def __init__(
		self,
		name: str,
		lineRate: Nullable[float] = None,
		branchRate: Nullable[float] = None,
		complexity: Nullable[float] = None
	) -> None:
		"""
		Initialize a package.

		:param name:       Name of the package.
		:param lineRate:   Optional, line coverage, as the report states it. Default: ``None``.
		:param branchRate: Optional, branch coverage, as the report states it. Default: ``None``.
		:param complexity: Optional, complexity, as the report states it. Default: ``None``.
		"""
		super().__init__(name, lineRate, branchRate)

		self._complexity = complexity
		self._classes =    []

	@readonly
	def Complexity(self) -> Nullable[float]:
		"""
		Read-only property to access the complexity, as the report states it (:attr:`_complexity`).

		:returns: The complexity, or ``None`` if the report doesn't state it.
		"""
		return self._complexity

	@readonly
	def Classes(self) -> list[Class]:
		"""
		Read-only property to access the package's classes (:attr:`_classes`).

		:returns: The classes, in the report's order; two classes may share a name.
		"""
		return self._classes

	@classmethod
	def _FromFiles(cls, files: Iterable[cc_File]) -> list[Package]:
		"""
		Convert the files of the common model to packages of their classes.

		:param files: The files of the common model.
		:returns:     The packages, by name.
		"""
		packages: dict[str, Package] = {}
		for file in files:
			Class._FromFile(file, packages)

		for package in packages.values():
			package._lineRate, package._branchRate = cls._Rates(cls._CountLines(
				line for klass in package._classes for line in klass._lines.values()
			))

		return [packages[name] for name in sorted(packages)]

	def Generate(self) -> _Element:
		"""
		Generate the package's ``<package>`` element with its classes.

		A rate the package doesn't state is computed from its classes' lines; a missing complexity is written as ``0``.

		:returns: The ``<package>`` element.
		"""
		packageElement = XMLElement("package")
		packageElement.attrib["name"] = self._name
		self._GenerateRates(packageElement, [line for klass in self._classes for line in klass._lines.values()])
		packageElement.attrib["complexity"] = str(0 if self._complexity is None else self._complexity)

		classesElement = SubElement(packageElement, "classes")
		for klass in self._classes:
			classesElement.append(klass.Generate())

		return packageElement
