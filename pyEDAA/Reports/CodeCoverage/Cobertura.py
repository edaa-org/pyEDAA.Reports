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
"""
The Cobertura XML code coverage format: a model of the format, read from a report and converted to the common model.

Cobertura's XML format is written by many tools - e.g. coverage.py (``coverage xml``) or gcovr (``--cobertura``) - and
read by many CI services. The format's model follows Cobertura's DTD ``coverage-04.dtd``: a :class:`Document` holds
:class:`Package` elements, a package :class:`Class` elements, a class :class:`Method` elements and :class:`Line`
elements, and a line :class:`Condition` elements; each keeps the attributes the report states, e.g. its rates.

A report is validated against :file:`Any-Cobertura.xsd`, which accepts the attributes tools add.
:file:`Cobertura-04.xsd` is the DTD's strict translation to XML Schema.

:meth:`Document.ToCoverageSummary` converts the model to the common model of :mod:`pyEDAA.Reports.CodeCoverage`:

* A class' ``filename`` is a file's path, relative to one of the ``<source>`` directories; several classes of one file
  - e.g. Java's nested classes - are one file, their lines merged.
* A line's ``hits`` is its count; a branching line's ``condition-coverage`` - e.g. ``50% (1/2)`` - states its taken and
  all branches, which become as many branches without count.
* The packages, classes and methods become units of the logical hierarchy; a package's name is split at ``.`` into
  nested packages. A class or method spans its file from the first to the last line it lists.
* The format has no excluded lines.

.. rubric:: Example

.. code-block:: Python

   from pathlib import Path
   from pyEDAA.Reports.CodeCoverage.Cobertura import Document

   report = Document(Path("coverage.xml"), analyzeAndConvert=True)
   summary = report.ToCoverageSummary()
   for file in summary.IterateFiles():
     print(f"{file.Path}: {file.LineCoverage:.1%}")
"""
from __future__                  import annotations

from pathlib                     import Path
from re                          import compile as re_compile
from typing                      import Optional as Nullable

from lxml.etree                  import XMLParser, XMLSchema, XMLSchemaParseError, XMLSyntaxError, parse
from lxml.etree                  import _Element, _ElementTree
from pyTooling.Common            import getResourceFile
from pyTooling.Decorators        import export, readonly
from pyTooling.Exceptions        import ToolingException
from pyTooling.MetaClasses       import ExtendedType
from pyTooling.Stopwatch         import Stopwatch

from pyEDAA.Reports              import Resources
from pyEDAA.Reports.CodeCoverage import Branch as cc_Branch, Class as cc_Class, CodeCoverageError, CoverageSummary
from pyEDAA.Reports.CodeCoverage import Document as cc_Document, File as cc_File, Line as cc_Line, LineCoverageStatus
from pyEDAA.Reports.CodeCoverage import Method as cc_Method, Package as cc_Package, Unit as cc_Unit


__all__ = ["READ_SCHEMA", "STRICT_SCHEMA", "CONDITION_COVERAGE"]

READ_SCHEMA =   "Any-Cobertura.xsd"  #: The XML schema a report is validated against when read: lenient.
STRICT_SCHEMA = "Cobertura-04.xsd"   #: The XML schema translating Cobertura's DTD ``coverage-04.dtd``: strict.

#: Pattern of attribute ``condition-coverage``: the taken and all branches, e.g. ``(1/2)`` of ``50% (1/2)``.
CONDITION_COVERAGE = re_compile(r"\((\d+)/(\d+)\)$")


def _float(element: _Element, name: str) -> Nullable[float]:
	"""
	Read an attribute holding a decimal number.

	:param element: The element.
	:param name:    The attribute's name.
	:returns:       The number, or ``None`` if the element has no such attribute.
	"""
	return None if (value := element.attrib.get(name)) is None else float(value)


def _int(element: _Element, name: str) -> Nullable[int]:
	"""
	Read an attribute holding an integer.

	:param element: The element.
	:param name:    The attribute's name.
	:returns:       The number, or ``None`` if the element has no such attribute.
	"""
	return None if (value := element.attrib.get(name)) is None else int(value)


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


@export
class Coverage(metaclass=ExtendedType, slots=True):
	"""
	The root element ``<coverage>``: the report's source directories, packages and figures, as the report states them.
	"""

	_version:         Nullable[str]    #: Version of the tool, which wrote the report.
	_timestamp:       Nullable[str]    #: Time the report was written, as the report states it.
	_lineRate:        Nullable[float]  #: Line coverage, as the report states it.
	_branchRate:      Nullable[float]  #: Branch coverage, as the report states it.
	_linesCovered:    Nullable[int]    #: Number of covered lines, as the report states it.
	_linesValid:      Nullable[int]    #: Number of executable lines, as the report states it.
	_branchesCovered: Nullable[int]    #: Number of taken branches, as the report states it.
	_branchesValid:   Nullable[int]    #: Number of branches, as the report states it.
	_complexity:      Nullable[float]  #: Complexity, as the report states it.
	_sources:         list[str]        #: The ``<source>`` directories.
	_packages:        list[Package]    #: The packages, in the report's order.

	def __init__(self) -> None:
		"""
		Initialize an empty report.
		"""
		self._version =         None
		self._timestamp =       None
		self._lineRate =        None
		self._branchRate =      None
		self._linesCovered =    None
		self._linesValid =      None
		self._branchesCovered = None
		self._branchesValid =   None
		self._complexity =      None
		self._sources =         []
		self._packages =        []

	@readonly
	def Version(self) -> Nullable[str]:
		"""
		Read-only property to access the version of the tool, which wrote the report (:attr:`_version`).

		:returns: The version, e.g. ``gcovr 8.4``, or ``None`` if the report doesn't state it.
		"""
		return self._version

	@readonly
	def Timestamp(self) -> Nullable[str]:
		"""
		Read-only property to access the time the report was written, as the report states it (:attr:`_timestamp`).

		:returns: The timestamp - e.g. milliseconds or seconds since the epoch, depending on the tool -, or ``None``.
		"""
		return self._timestamp

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

	@readonly
	def LinesCovered(self) -> Nullable[int]:
		"""
		Read-only property to access the number of covered lines, as the report states it (:attr:`_linesCovered`).

		:returns: The number, or ``None`` if the report doesn't state it.
		"""
		return self._linesCovered

	@readonly
	def LinesValid(self) -> Nullable[int]:
		"""
		Read-only property to access the number of executable lines, as the report states it (:attr:`_linesValid`).

		:returns: The number, or ``None`` if the report doesn't state it.
		"""
		return self._linesValid

	@readonly
	def BranchesCovered(self) -> Nullable[int]:
		"""
		Read-only property to access the number of taken branches, as the report states it (:attr:`_branchesCovered`).

		:returns: The number, or ``None`` if the report doesn't state it.
		"""
		return self._branchesCovered

	@readonly
	def BranchesValid(self) -> Nullable[int]:
		"""
		Read-only property to access the number of branches, as the report states it (:attr:`_branchesValid`).

		:returns: The number, or ``None`` if the report doesn't state it.
		"""
		return self._branchesValid

	@readonly
	def Complexity(self) -> Nullable[float]:
		"""
		Read-only property to access the complexity, as the report states it (:attr:`_complexity`).

		:returns: The complexity, or ``None`` if the report doesn't state it.
		"""
		return self._complexity

	@readonly
	def Sources(self) -> list[str]:
		"""
		Read-only property to access the ``<source>`` directories (:attr:`_sources`).

		:returns: The directories, as the report states them.
		"""
		return self._sources

	@readonly
	def Packages(self) -> list[Package]:
		"""
		Read-only property to access the packages (:attr:`_packages`).

		:returns: The packages, in the report's order.
		"""
		return self._packages


@export
class Document(Coverage, cc_Document):
	"""
	A Cobertura XML code coverage report: read into the format's model, and converted to the common model.
	"""

	_xmlDocument: Nullable[_ElementTree]  #: The parsed and validated XML document, after :meth:`Analyze`.

	def __init__(self, xmlReportFile: Path, analyzeAndConvert: bool = False) -> None:
		"""
		Initialize the report, and optionally read it.

		:param xmlReportFile:     Path to the Cobertura XML file.
		:param analyzeAndConvert: Optional, if true, analyze the file and convert its content. Default: ``False``.
		"""
		super().__init__()

		self._xmlDocument = None

		cc_Document.__init__(self, xmlReportFile, analyzeAndConvert)

	def Analyze(self) -> None:
		"""
		Parse the XML file and validate it against the lenient XML schema :data:`READ_SCHEMA`.

		:raises CodeCoverageError: If the file doesn't exist.
		:raises CodeCoverageError: If the file isn't well-formed XML.
		:raises CodeCoverageError: If the root element isn't ``<coverage>``.
		:raises CodeCoverageError: If the XML schema can't be located or parsed.
		:raises CodeCoverageError: If the file isn't valid according to the XML schema.
		"""
		if not self._path.exists():
			raise CodeCoverageError(f"Cobertura report file '{self._path}' does not exist.") \
				from FileNotFoundError(f"File '{self._path}' not found.")

		with Stopwatch() as sw:
			try:
				xmlDocument = parse(self._path, XMLParser(ns_clean=True))
			except XMLSyntaxError as ex:
				raise CodeCoverageError(f"XML syntax error in Cobertura report file '{self._path}'.") from ex

			rootElement: _Element = xmlDocument.getroot()
			if rootElement.tag != "coverage":
				ex = CodeCoverageError(f"Root element of '{self._path}' is not '<coverage>'.")
				ex.add_note(f"Got root element '<{rootElement.tag}>'.")
				raise ex

			try:
				schemaResourceFile = getResourceFile(Resources, READ_SCHEMA)
			except ToolingException as ex:
				raise CodeCoverageError(f"Couldn't locate XML Schema '{READ_SCHEMA}' in package resources.") from ex

			try:
				xmlSchema = XMLSchema(parse(schemaResourceFile, XMLParser(ns_clean=True)))
			except (XMLSyntaxError, XMLSchemaParseError) as ex:
				raise CodeCoverageError(f"Error while parsing XML Schema '{READ_SCHEMA}'.") from ex

			if not xmlSchema.validate(xmlDocument):
				ex = CodeCoverageError(f"Validation error for '{self._path}' using XSD schema '{READ_SCHEMA}'.")
				for logEntry in xmlSchema.error_log:
					ex.add_note(str(logEntry))
				raise ex

			self._xmlDocument = xmlDocument

		self._analysisDuration = sw.Duration

	def Convert(self) -> None:
		"""
		Convert the parsed and validated XML document to the format's model.

		:raises CodeCoverageError: If the XML file was not analyzed before. |br|
		                           Call 'Document.Analyze()' or create the document using
		                           'Document(path, analyzeAndConvert=True)'.
		"""
		if self._xmlDocument is None:
			ex = CodeCoverageError(f"Cobertura report file '{self._path}' needs to be read and analyzed by an XML parser.")
			ex.add_note(f"Call 'Document.Analyze()' or create the document using 'Document(path, analyzeAndConvert=True)'.")
			raise ex

		with Stopwatch() as sw:
			root: _Element = self._xmlDocument.getroot()

			self._version =         root.attrib.get("version")
			self._timestamp =       root.attrib.get("timestamp")
			self._lineRate =        _float(root, "line-rate")
			self._branchRate =      _float(root, "branch-rate")
			self._linesCovered =    _int(root, "lines-covered")
			self._linesValid =      _int(root, "lines-valid")
			self._branchesCovered = _int(root, "branches-covered")
			self._branchesValid =   _int(root, "branches-valid")
			self._complexity =      _float(root, "complexity")

			self._sources = [
				element.text.strip() for element in root.iterfind("sources/source")
				if element.text is not None and element.text.strip() != ""
			]

			for packageElement in root.iterfind("packages/package"):  # type: _Element
				package = Package(
					packageElement.attrib["name"], _float(packageElement, "line-rate"), _float(packageElement, "branch-rate"),
					_float(packageElement, "complexity")
				)
				self._packages.append(package)

				for classElement in packageElement.iterfind("classes/class"):  # type: _Element
					package._classes.append(self._ConvertClass(classElement))

		self._conversionDuration = sw.Duration

	@classmethod
	def _ConvertClass(cls, classElement: _Element) -> Class:
		"""
		Convert a ``<class>`` element, its methods and lines.

		:param classElement: The ``<class>`` element.
		:returns:            The class.
		"""
		klass = Class(
			classElement.attrib.get("name", classElement.attrib["filename"]), classElement.attrib["filename"],
			_float(classElement, "line-rate"), _float(classElement, "branch-rate"), _float(classElement, "complexity")
		)

		for methodElement in classElement.iterfind("methods/method"):  # type: _Element
			method = Method(
				methodElement.attrib["name"], methodElement.attrib.get("signature"), _float(methodElement, "line-rate"),
				_float(methodElement, "branch-rate")
			)
			key = method._name if method._name not in klass._methods else f"{method._name}{method._signature}"
			klass._methods[key] = method
			for lineElement in methodElement.iterfind("lines/line"):  # type: _Element
				line = cls._ConvertLine(lineElement)
				method._lines[line._number] = line

		for lineElement in classElement.iterfind("lines/line"):  # type: _Element
			line = cls._ConvertLine(lineElement)
			klass._lines[line._number] = line

		return klass

	@staticmethod
	def _ConvertLine(lineElement: _Element) -> Line:
		"""
		Convert a ``<line>`` element and its conditions.

		:param lineElement: The ``<line>`` element.
		:returns:           The line.
		"""
		conditionCoverage = None
		if (match := CONDITION_COVERAGE.search(lineElement.attrib.get("condition-coverage", ""))) is not None:
			conditionCoverage = (int(match[1]), int(match[2]))

		conditions = [
			Condition(int(element.attrib["number"]), element.attrib.get("type", ""), element.attrib.get("coverage", ""))
			for element in lineElement.iterfind("conditions/condition")
		]

		return Line(
			int(lineElement.attrib["number"]), int(lineElement.attrib["hits"]),
			lineElement.attrib.get("branch", "false") in ("true", "1"), conditionCoverage, conditions
		)

	def ToCoverageSummary(self) -> CoverageSummary:
		"""
		Convert the format's model to the common model, and aggregate it.

		Several classes of one file - e.g. Java's nested classes - are one file: a line listed by several of them ran, if
		one of them says so, its hits are added, and of its branches the higher counts are kept. Every package, class and
		method becomes a unit; a class or method spans its file from its first to its last line.

		:returns:                  The report's root of the common model, named after the report file.
		:raises CodeCoverageError: If a file's path runs through another file.
		"""
		summary = CoverageSummary(self._path.stem, sourceDirectories=[Path(source) for source in self._sources])

		merged: dict[int, dict[int, tuple[int, int, int]]] = {}
		files: dict[int, cc_File] = {}
		for package in self._packages:
			for klass in package._classes:
				file = summary.GetOrAddFile(klass._filename)
				files[id(file)] = file
				lines = merged.setdefault(id(file), {})
				for line in klass._lines.values():
					covered, total = (0, 0) if line._conditionCoverage is None else line._conditionCoverage
					hits, oldCovered, oldTotal = lines.get(line._number, (0, 0, 0))
					lines[line._number] = (hits + line._hits, max(covered, oldCovered), max(total, oldTotal))

		for fileID, lines in merged.items():
			file = files[fileID]
			for number in sorted(lines):
				hits, covered, total = lines[number]
				branches = [cc_Branch(LineCoverageStatus.Covered) for _ in range(covered)]
				branches.extend(cc_Branch(LineCoverageStatus.Uncovered) for _ in range(total - covered))
				if hits == 0:
					status = LineCoverageStatus.Uncovered
				elif covered < total:
					status = LineCoverageStatus.PartiallyCovered
				else:
					status = LineCoverageStatus.Covered
				cc_Line(number, status, hits, branches, parent=file)

		for package in self._packages:
			parent: cc_Unit | CoverageSummary = summary
			for part in (part for part in package._name.split(".") if part != ""):
				parent = parent._units[part] if part in parent._units else cc_Package(part, parent=parent)

			for klass in package._classes:
				file = summary.GetOrAddFile(klass._filename)
				if (classUnit := parent._units.get(klass._name)) is None:
					numbers = list(klass._lines)
					classUnit = cc_Class(
						klass._name,
						file=file,
						startLine=file._lines[min(numbers)] if len(numbers) > 0 else None,
						endLine=file._lines[max(numbers)] if len(numbers) > 0 else None,
						parent=parent
					)

				for key, method in klass._methods.items():
					if key not in classUnit._units:
						numbers = [
							number for number in method._lines if number <= file._lastLineNumber and file._lines[number] is not None
						]
						cc_Method(
							key,
							file=file,
							startLine=file._lines[min(numbers)] if len(numbers) > 0 else None,
							endLine=file._lines[max(numbers)] if len(numbers) > 0 else None,
							parent=classUnit
						)

		summary.Aggregate()
		return summary
