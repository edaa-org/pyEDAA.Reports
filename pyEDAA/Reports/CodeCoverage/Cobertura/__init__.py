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
The Cobertura XML code coverage format: a model of the format, read from a report and converted to the common model, or
converted from the common model and written to a report.

Cobertura's XML format is written by many tools - e.g. coverage.py (``coverage xml``) or gcovr (``--cobertura``) - and
read by many CI services. The format's model follows Cobertura's DTD ``coverage-04.dtd``: a :class:`Document` holds
:class:`~pyEDAA.Reports.CodeCoverage.Cobertura.Records.Package` elements, a package
:class:`~pyEDAA.Reports.CodeCoverage.Cobertura.Records.Class` elements, a class
:class:`~pyEDAA.Reports.CodeCoverage.Cobertura.Records.Method` elements and
:class:`~pyEDAA.Reports.CodeCoverage.Cobertura.Records.Line` elements, and a line
:class:`~pyEDAA.Reports.CodeCoverage.Cobertura.Records.Condition` elements; each keeps the attributes the report states,
e.g. its rates. The elements below the root element ``<coverage>`` are in
:mod:`~pyEDAA.Reports.CodeCoverage.Cobertura.Records`.

A report is validated against :file:`Any-Cobertura.xsd`, which accepts the attributes tools add.
:file:`Cobertura-04.xsd` is the DTD's strict translation to XML Schema.

A dialect - the format as one tool writes it - has a module of its own in this package: a :class:`Document` derived
from this one, validating against a strict XML schema of the dialect, and reading what the dialect adds.

.. seealso::

   :mod:`~pyEDAA.Reports.CodeCoverage.Cobertura.CoveragePyCobertura`
      |rarr| coverage.py's dialect (``coverage xml``).

:meth:`Document.ToCoverageSummary` converts the model to the common model of :mod:`pyEDAA.Reports.CodeCoverage`:

* A class' ``filename`` is a file's path, relative to one of the ``<source>`` directories; several classes of one file
  - e.g. Java's nested classes - are one file, their lines merged.
* A line's ``hits`` is its count; a branching line's ``condition-coverage`` - e.g. ``50% (1/2)`` - states its taken and
  all branches, which become as many branches without count.
* The packages, classes and methods become units of the logical hierarchy; a package's name is split at ``.`` into
  nested packages. A class or method spans its file from the first to the last line it lists.
* The format has no excluded lines.

:meth:`Document.FromCoverageSummary` converts the common model to the format's model, which :meth:`Document.Write`
writes following the DTD:

* Every source file, module and class of the logical hierarchy becomes a ``<class>`` of its file, named by its
  qualified name below its packages; its packages - or the file's directories, if it has none - name its
  ``<package>``. A file's line is listed by the innermost of them spanning it, a line outside of every one by a
  ``<class>`` named after the file.
* Every function and method becomes a ``<method>`` of the ``<class>`` of the unit containing it, listing its lines.
* A line's count is its ``hits`` - ``1`` or ``0``, if the report didn't say -; a branching line states its taken and
  all branches in ``condition-coverage``. Excluded lines are left out.

.. rubric:: Example

.. code-block:: Python

   from pathlib import Path
   from pyEDAA.Reports.CodeCoverage.Cobertura import Document

   report = Document(Path("coverage.xml"), analyzeAndConvert=True)
   summary = report.ToCoverageSummary()
   for file in summary.IterateFiles():
     print(f"{file.Path}: {file.LineCoverage:.1%}")

   Document.FromCoverageSummary(Path("Cobertura.xml"), summary).Write(regenerate=True)
"""
from __future__                                    import annotations

from pathlib                                       import Path
from re                                            import compile as re_compile
from time                                          import time_ns
from typing                                        import Optional as Nullable

from lxml.etree                                    import Element as XMLElement, ElementTree, SubElement, XMLParser
from lxml.etree                                    import XMLSchema, XMLSchemaParseError, XMLSyntaxError, parse
from lxml.etree                                    import tostring, _Element, _ElementTree
from pyTooling.Common                              import getFullyQualifiedName, getResourceFile
from pyTooling.Decorators                          import export, readonly
from pyTooling.Exceptions                          import ToolingException
from pyTooling.MetaClasses                         import ExtendedType
from pyTooling.Stopwatch                           import Stopwatch

from pyEDAA.Reports                                import Resources, __version__
from pyEDAA.Reports.CodeCoverage                   import Branch as cc_Branch, Class as cc_Class, CodeCoverageError
from pyEDAA.Reports.CodeCoverage                   import CoverageSummary, Document as cc_Document, File as cc_File
from pyEDAA.Reports.CodeCoverage                   import Line as cc_Line, LineCoverageStatus, Method as cc_Method
from pyEDAA.Reports.CodeCoverage                   import Package as cc_Package, Unit as cc_Unit
from pyEDAA.Reports.CodeCoverage.Cobertura.Records import Class, Condition, Element, Line, Method, Package


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
class Coverage(metaclass=ExtendedType, mixin=True):
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
class Document(cc_Document, Coverage):
	"""
	A Cobertura XML code coverage report: read into the format's model and converted to the common model, or converted
	from the common model and written.
	"""

	_xmlDocument: Nullable[_ElementTree]  #: The XML document, parsed by :meth:`Analyze` or built by :meth:`Generate`.

	def __init__(self, xmlReportFile: Path, analyzeAndConvert: bool = False) -> None:
		"""
		Initialize the report, and optionally read it.

		:param xmlReportFile:     Path to the Cobertura XML file.
		:param analyzeAndConvert: Optional, if true, analyze the file and convert its content. Default: ``False``.
		"""
		super().__init__(xmlReportFile)
		Coverage.__init__(self)

		self._xmlDocument = None

		if analyzeAndConvert:
			self.Analyze()
			self.Convert()

	@classmethod
	def FromCoverageSummary(cls, xmlReportFile: Path, coverageSummary: CoverageSummary) -> Document:
		"""
		Create a report from the common model, ready to be generated and written.

		Every source file, module and class of the logical hierarchy becomes a
		:class:`~pyEDAA.Reports.CodeCoverage.Cobertura.Records.Class` of its file, named by its qualified name below its
		packages; its packages - or the file's directories, if it has none - name its
		:class:`~pyEDAA.Reports.CodeCoverage.Cobertura.Records.Package`. A file's line is listed by the innermost of these
		classes spanning it; a line outside of every one by a class named after the file. Every function and method becomes
		a :class:`~pyEDAA.Reports.CodeCoverage.Cobertura.Records.Method` of the class of the unit containing it. Excluded
		lines are left out. The rates and figures are computed from the lines; the version names pyEDAA.Reports, the
		timestamp is the current time in milliseconds since the epoch.

		:param xmlReportFile:   Path to the Cobertura XML file to write.
		:param coverageSummary: The report's root of the common model.
		:returns:               The report.
		:raises ValueError:     If parameter ``xmlReportFile`` is ``None``.
		:raises TypeError:      If parameter ``xmlReportFile`` isn't of type :class:`~pathlib.Path`.
		:raises ValueError:     If parameter ``coverageSummary`` is ``None``.
		:raises TypeError:      If parameter ``coverageSummary`` isn't of type
		                        :class:`~pyEDAA.Reports.CodeCoverage.CoverageSummary`.
		"""
		if xmlReportFile is None:
			raise ValueError(f"Parameter 'xmlReportFile' is None.")
		elif not isinstance(xmlReportFile, Path):
			ex = TypeError(f"Parameter 'xmlReportFile' is not of type 'Path'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(xmlReportFile)}'.")
			raise ex

		if coverageSummary is None:
			raise ValueError(f"Parameter 'coverageSummary' is None.")
		elif not isinstance(coverageSummary, CoverageSummary):
			ex = TypeError(f"Parameter 'coverageSummary' is not of type 'CoverageSummary'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(coverageSummary)}'.")
			raise ex

		document = cls(xmlReportFile)
		document._version =    f"pyEDAA.Reports {__version__}"
		document._timestamp =  str(time_ns() // 1_000_000)
		document._complexity = 0.0
		document._sources =    [directory.as_posix() for directory in coverageSummary._sourceDirectories]
		document._packages =   Package._FromFiles(coverageSummary.IterateFiles())

		counts = Element._CountLines(
			line for package in document._packages for klass in package._classes for line in klass._lines.values()
		)
		document._linesValid, document._linesCovered, document._branchesValid, document._branchesCovered = counts
		document._lineRate, document._branchRate = Element._Rates(counts)

		return document

	def Analyze(self) -> None:
		"""
		Parse the XML file and validate it against the lenient XML schema :data:`READ_SCHEMA`.

		:raises CodeCoverageError: If the file doesn't exist.
		:raises CodeCoverageError: If the file isn't well-formed XML.
		:raises CodeCoverageError: If the root element isn't ``<coverage>``.
		:raises CodeCoverageError: If the XML schema can't be located or parsed.
		:raises CodeCoverageError: If the file isn't valid according to the XML schema.
		"""
		self._Analyze(READ_SCHEMA)

	def _Analyze(self, xmlSchemaFile: str) -> None:
		"""
		Parse the XML file and validate it against an XML schema of the package resources.

		A dialect's :meth:`Analyze` calls it with the dialect's XML schema.

		:param xmlSchemaFile:      File name of the XML schema in :mod:`pyEDAA.Reports.Resources`.
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
				schemaResourceFile = getResourceFile(Resources, xmlSchemaFile)
			except ToolingException as ex:
				raise CodeCoverageError(f"Couldn't locate XML Schema '{xmlSchemaFile}' in package resources.") from ex

			try:
				xmlSchema = XMLSchema(parse(schemaResourceFile, XMLParser(ns_clean=True)))
			except (XMLSyntaxError, XMLSchemaParseError) as ex:
				raise CodeCoverageError(f"Error while parsing XML Schema '{xmlSchemaFile}'.") from ex

			if not xmlSchema.validate(xmlDocument):
				ex = CodeCoverageError(f"Validation error for '{self._path}' using XSD schema '{xmlSchemaFile}'.")
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

	def Generate(self, overwrite: bool = False) -> None:
		"""
		Generate the XML document from the format's model, following Cobertura's DTD.

		A rate or figure the model doesn't state - e.g. read from a report without it - is computed from the lines; a
		missing complexity is written as ``0``, a missing version, timestamp or signature as empty text.

		:param overwrite:          Optional, if true, replace the XML document read or generated before. Default: ``False``.
		:raises ValueError:        If parameter ``overwrite`` is ``None``.
		:raises TypeError:         If parameter ``overwrite`` isn't of type :class:`bool`.
		:raises CodeCoverageError: If parameter ``overwrite`` is false and the XML document was read or generated before.
		"""
		if overwrite is None:
			raise ValueError(f"Parameter 'overwrite' is None.")
		elif not isinstance(overwrite, bool):
			ex = TypeError(f"Parameter 'overwrite' is not of type 'bool'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(overwrite)}'.")
			raise ex
		elif not overwrite and self._xmlDocument is not None:
			ex = CodeCoverageError(f"XML document of Cobertura report file '{self._path}' is already populated.")
			ex.add_note(f"Call 'Document.Generate(overwrite=True)' to replace it.")
			raise ex

		counts = Element._CountLines(
			line for package in self._packages for klass in package._classes for line in klass._lines.values()
		)
		linesValid, linesCovered, branchesValid, branchesCovered = counts
		lineRate, branchRate = Element._Rates(counts)

		rootElement = XMLElement("coverage")
		rootElement.attrib["line-rate"] =   str(round(lineRate if self._lineRate is None else self._lineRate, 4))
		rootElement.attrib["branch-rate"] = str(round(branchRate if self._branchRate is None else self._branchRate, 4))
		for name, stated, computed in (
			("lines-covered",    self._linesCovered,    linesCovered),
			("lines-valid",      self._linesValid,      linesValid),
			("branches-covered", self._branchesCovered, branchesCovered),
			("branches-valid",   self._branchesValid,   branchesValid)
		):
			rootElement.attrib[name] = str(computed if stated is None else stated)
		rootElement.attrib["complexity"] = str(0 if self._complexity is None else self._complexity)
		rootElement.attrib["version"] =    "" if self._version is None else self._version
		rootElement.attrib["timestamp"] =  "" if self._timestamp is None else self._timestamp

		sourcesElement = SubElement(rootElement, "sources")
		for source in self._sources:
			SubElement(sourcesElement, "source").text = source

		packagesElement = SubElement(rootElement, "packages")
		for package in self._packages:
			packagesElement.append(package.Generate())

		document = ElementTree(rootElement)
		document.docinfo.system_url = "http://cobertura.sourceforge.net/xml/coverage-04.dtd"
		self._xmlDocument = document

	def Write(self, path: Nullable[Path] = None, overwrite: bool = False, regenerate: bool = False) -> None:
		"""
		Write the XML document to a file.

		:param path:               Optional, path to the XML file, if not the report's path. Default: ``None``.
		:param overwrite:          Optional, if true, overwrite an existing file. Default: ``False``.
		:param regenerate:         Optional, if true, generate the XML document from the format's model first.
		                           Default: ``False``.
		:raises TypeError:         If parameter ``path`` isn't of type :class:`~pathlib.Path`.
		:raises ValueError:        If parameter ``overwrite`` is ``None``.
		:raises TypeError:         If parameter ``overwrite`` isn't of type :class:`bool`.
		:raises ValueError:        If parameter ``regenerate`` is ``None``.
		:raises TypeError:         If parameter ``regenerate`` isn't of type :class:`bool`.
		:raises CodeCoverageError: If the file exists and parameter ``overwrite`` is false.
		:raises CodeCoverageError: If the XML document was neither read nor generated. |br|
		                           Call 'Document.Generate()' or 'Document.Write(..., regenerate=True)'.
		:raises CodeCoverageError: If the file can't be written.
		"""
		if path is None:
			path = self._path
		elif not isinstance(path, Path):
			ex = TypeError(f"Parameter 'path' is not of type 'Path'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(path)}'.")
			raise ex

		if overwrite is None:
			raise ValueError(f"Parameter 'overwrite' is None.")
		elif not isinstance(overwrite, bool):
			ex = TypeError(f"Parameter 'overwrite' is not of type 'bool'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(overwrite)}'.")
			raise ex

		if regenerate is None:
			raise ValueError(f"Parameter 'regenerate' is None.")
		elif not isinstance(regenerate, bool):
			ex = TypeError(f"Parameter 'regenerate' is not of type 'bool'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(regenerate)}'.")
			raise ex

		if not overwrite and path.exists():
			raise CodeCoverageError(f"Cobertura report file '{path}' can not be overwritten.") \
				from FileExistsError(f"File '{path}' already exists.")

		if regenerate:
			self.Generate(overwrite=True)

		if self._xmlDocument is None:
			ex = CodeCoverageError(f"XML document of Cobertura report file '{path}' needs to be generated first.")
			ex.add_note(f"Call 'Document.Generate()' or 'Document.Write(..., regenerate=True)'.")
			raise ex

		content = tostring(self._xmlDocument, encoding="utf-8", xml_declaration=True, pretty_print=True)
		try:
			with path.open("wb") as file:
				file.write(content)
		except OSError as ex:
			raise CodeCoverageError(f"Cobertura report file '{path}' can not be written.") from ex
