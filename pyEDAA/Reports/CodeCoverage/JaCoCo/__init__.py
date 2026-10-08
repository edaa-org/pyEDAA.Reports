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
JaCoCo's XML code coverage format: a model of the format, read from a report and converted to the common model.

JaCoCo - the Java code coverage library - writes its XML report with ``jacococli.jar report --xml``, Maven's goals
``report`` and ``report-aggregate``, Ant's task ``report`` or Gradle's task ``jacocoTestReport``. A report names its
DTD by a public identifier, e.g. ``-//JACOCO//DTD Report 1.1//EN``, whose version (:class:`FormatVersion`) chooses the
XML schema a report is validated against: :file:`JaCoCo-1.1.xsd`, a translation of JaCoCo's DTD ``report.dtd``. The
format's model keeps what the report states: a :class:`Document` holds
:class:`~pyEDAA.Reports.CodeCoverage.JaCoCo.Elements.SessionInfo` elements, :class:`Group` elements - nested -, and
:class:`Package` elements; a package holds
:class:`~pyEDAA.Reports.CodeCoverage.JaCoCo.Classes.Class` elements with their
:class:`~pyEDAA.Reports.CodeCoverage.JaCoCo.Classes.Method` elements, and
:class:`~pyEDAA.Reports.CodeCoverage.JaCoCo.Classes.SourceFile` elements with their
:class:`~pyEDAA.Reports.CodeCoverage.JaCoCo.Classes.Line` elements. Every element but a line and a session states its
:class:`~pyEDAA.Reports.CodeCoverage.JaCoCo.Elements.Counter` elements. The elements below a package are in
:mod:`~pyEDAA.Reports.CodeCoverage.JaCoCo.Classes`, the sessions and counters in
:mod:`~pyEDAA.Reports.CodeCoverage.JaCoCo.Elements`.
Each element's constructor takes typed values, so the model can be built by hand: an element below the report names its
parent with the keyword parameter ``parent`` and is added to it. Its class method ``Parse`` reads the element's XML
element.

:meth:`Document.ToCoverageSummary` converts the model to the common model of :mod:`pyEDAA.Reports.CodeCoverage`:

* A source file's path is its package's name in VM notation - e.g. ``my/pack`` - and its name, relative to a source
  directory, which the report doesn't name.
* A line ran, if it has a covered instruction - partially covered, if it has a missed branch. Its missed and covered
  branches become as many branches. The format has no counts, no branch targets and no excluded lines.
* The packages, classes and methods become units of the logical hierarchy; a package's name is split at ``/`` into
  nested packages. A method spans its first line and the next lines of its file, as many as its ``LINE`` counter
  counts; a class spans its methods. The groups have no counterpart.

.. rubric:: Example

.. code-block:: Python

   from pathlib import Path
   from pyEDAA.Reports.CodeCoverage.JaCoCo import Document

   report = Document(Path("jacocoTestReport.xml"), analyzeAndConvert=True)
   summary = report.ToCoverageSummary()
   for unit in summary.IterateUnits():
     print(f"{unit.QualifiedName}: {unit.LineCoverage:.1%}")
"""
from __future__                                  import annotations

from collections.abc                             import Generator
from itertools                                   import islice
from pathlib                                     import Path
from re                                          import compile as re_compile
from typing                                      import Generic, Optional as Nullable, Self, TypeVar

from lxml.etree                                  import XMLParser, XMLSchema, XMLSchemaParseError, XMLSyntaxError
from lxml.etree                                  import _Element, _ElementTree, parse
from pyTooling.Common                            import getFullyQualifiedName, getResourceFile, StringEnum
from pyTooling.Decorators                        import export, readonly
from pyTooling.Exceptions                        import ToolingException
from pyTooling.Stopwatch                         import Stopwatch

from pyEDAA.Reports                              import Resources
from pyEDAA.Reports.CodeCoverage                 import Branch as cc_Branch, Class as cc_Class, CodeCoverageError
from pyEDAA.Reports.CodeCoverage                 import CoverageSummary, Document as cc_Document, Line as cc_Line
from pyEDAA.Reports.CodeCoverage                 import LineCoverageStatus, Method as cc_Method, Package as cc_Package
from pyEDAA.Reports.CodeCoverage                 import Unit as cc_Unit
from pyEDAA.Reports.CodeCoverage.JaCoCo.Classes  import Class, SourceFile
from pyEDAA.Reports.CodeCoverage.JaCoCo.Elements import Base, Counter, CountersMixin, CounterType, SessionInfo


__all__ = ["PUBLIC_IDENTIFIER", "SCHEMAS"]

#: Pattern of the DTD's public identifier a report states, capturing the version, e.g. ``1.1``.
PUBLIC_IDENTIFIER = re_compile(r"-//JACOCO//DTD Report (\S+)//EN")

ParentType = TypeVar("ParentType", bound="Report | Group")
"""A type variable for the parent of a :class:`Group` or :class:`Package`: a :class:`Report` or a :class:`Group`."""


@export
class FormatVersion(StringEnum):
	"""
	Version of the JaCoCo XML format: the version of the DTD, whose public identifier a report states.
	"""

	Version1_1 = "1.1"  #: Format 1.1, public identifier ``-//JACOCO//DTD Report 1.1//EN``.


# A class with a property named like a class - ``FormatVersion`` - can't name that class in the annotation of a field: the
# class body's namespace, where annotations are evaluated, binds the name to the property.
_FormatVersion = FormatVersion

SCHEMAS: dict[FormatVersion, str] = {
	FormatVersion.Version1_1: "JaCoCo-1.1.xsd"
}  #: Per format version, the XML schema a report of that version is validated against.


@export
class Group(Base, CountersMixin, Generic[ParentType]):
	"""
	A ``<group>`` of the report or of a group: its groups or packages, and its counters.

	JaCoCo groups packages, e.g. by module, if Maven's goal ``report-aggregate`` or Ant's task ``report`` asks for it.
	"""

	_parent:   Nullable[ParentType]       #: The report or group the group belongs to.
	_groups:   dict[str, Group[Group]]    #: The groups, by name.
	_packages: dict[str, Package[Group]]  #: The packages, by name.

	def __init__(self, name: str, *, parent: Nullable[ParentType] = None) -> None:
		"""
		Initialize the group, and add it to the groups of its report or group.

		Its groups, packages and counters are added by creating them with this group as their parent.

		:param name:        Name of the group, e.g. of a module.
		:param parent:      Optional, the report or group the group belongs to; the group is added to its groups by
		                    :attr:`Name`. Default: ``None``.
		:raises ValueError: If parameter ``name`` is ``None``.
		:raises TypeError:  If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError: If parameter ``name`` is empty.
		:raises TypeError:  If parameter ``parent`` isn't of type :class:`Report` or :class:`Group`.
		"""
		super().__init__(name)
		CountersMixin.__init__(self)

		if name == "":
			raise ValueError(f"Parameter 'name' is empty.")

		if parent is not None and not isinstance(parent, (Report, Group)):
			ex = TypeError(f"Parameter 'parent' is not of type 'Report' or 'Group'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =   parent
		self._groups =   {}
		self._packages = {}

		if parent is not None:
			parent._groups[self._name] = self

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[ParentType] = None) -> Self:
		"""
		Parse a group, its groups, packages and counters from its ``<group>`` element.

		:param element:            The ``<group>`` element.
		:param parent:             Optional, the report or group the group belongs to. Default: ``None``.
		:returns:                  The group.
		:raises CodeCoverageError: If the group states a group or package twice.
		:raises CodeCoverageError: If the group states a counter twice.
		"""
		group = cls(element.attrib["name"], parent=parent)

		for groupElement in element.iterfind("group"):
			if (name := groupElement.attrib["name"]) in group._groups:
				raise CodeCoverageError(f"JaCoCo group '{group._name}' states group '{name}' twice.")

			Group.Parse(groupElement, parent=group)

		for packageElement in element.iterfind("package"):
			if (name := packageElement.attrib["name"]) in group._packages:
				raise CodeCoverageError(f"JaCoCo group '{group._name}' states package '{name}' twice.")

			Package.Parse(packageElement, parent=group)

		for counterElement in element.iterfind("counter"):
			if (counterType := CounterType(counterElement.attrib["type"])) in group._counters:
				raise CodeCoverageError(f"JaCoCo group '{group._name}' states counter '{counterType}' twice.")

			Counter.Parse(counterElement, parent=group)

		return group

	@readonly
	def Parent(self) -> Nullable[ParentType]:
		"""
		Read-only property to access the report or group the group belongs to (:attr:`_parent`).

		:returns: The :class:`Report` or :class:`Group`; ``None`` if the group belongs to none.
		"""
		return self._parent

	@readonly
	def Groups(self) -> dict[str, Group[Group]]:
		"""
		Read-only property to access the groups (:attr:`_groups`).

		:returns: The groups, by name.
		"""
		return self._groups

	@readonly
	def Packages(self) -> dict[str, Package[Group]]:
		"""
		Read-only property to access the packages (:attr:`_packages`).

		:returns: The packages, by name.
		"""
		return self._packages


@export
class Package(Base, CountersMixin, Generic[ParentType]):
	"""
	A ``<package>`` of the report or of a group: its classes and source files, and its counters.
	"""

	_parent:      Nullable[ParentType]   #: The report or group the package belongs to.
	_classes:     dict[str, Class]       #: The classes, by name.
	_sourceFiles: dict[str, SourceFile]  #: The source files, by name.

	def __init__(self, name: str, *, parent: Nullable[ParentType] = None) -> None:
		"""
		Initialize the package, and add it to the packages of its report or group.

		Its classes, source files and counters are added by creating them with this package as their parent.

		:param name:        Name of the package in VM notation, e.g. ``my/pack``; empty for the default package.
		:param parent:      Optional, the report or group the package belongs to; the package is added to its packages
		                    by :attr:`Name`. Default: ``None``.
		:raises ValueError: If parameter ``name`` is ``None``.
		:raises TypeError:  If parameter ``name`` isn't of type :class:`str`.
		:raises TypeError:  If parameter ``parent`` isn't of type :class:`Report` or :class:`Group`.
		"""
		super().__init__(name)
		CountersMixin.__init__(self)

		if parent is not None and not isinstance(parent, (Report, Group)):
			ex = TypeError(f"Parameter 'parent' is not of type 'Report' or 'Group'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =      parent
		self._classes =     {}
		self._sourceFiles = {}

		if parent is not None:
			parent._packages[self._name] = self

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[ParentType] = None) -> Self:
		"""
		Parse a package, its classes, source files and counters from its ``<package>`` element.

		:param element:            The ``<package>`` element.
		:param parent:             Optional, the report or group the package belongs to. Default: ``None``.
		:returns:                  The package.
		:raises CodeCoverageError: If the package states a class or source file twice.
		:raises CodeCoverageError: If the package states a counter twice.
		"""
		package = cls(element.attrib["name"], parent=parent)

		for classElement in element.iterfind("class"):
			if (name := classElement.attrib["name"]) in package._classes:
				raise CodeCoverageError(f"JaCoCo package '{package._name}' states class '{name}' twice.")

			Class.Parse(classElement, parent=package)

		for sourceFileElement in element.iterfind("sourcefile"):
			if (name := sourceFileElement.attrib["name"]) in package._sourceFiles:
				raise CodeCoverageError(f"JaCoCo package '{package._name}' states source file '{name}' twice.")

			SourceFile.Parse(sourceFileElement, parent=package)

		for counterElement in element.iterfind("counter"):
			if (counterType := CounterType(counterElement.attrib["type"])) in package._counters:
				raise CodeCoverageError(f"JaCoCo package '{package._name}' states counter '{counterType}' twice.")

			Counter.Parse(counterElement, parent=package)

		return package

	@readonly
	def Parent(self) -> Nullable[ParentType]:
		"""
		Read-only property to access the report or group the package belongs to (:attr:`_parent`).

		:returns: The :class:`Report` or :class:`Group`; ``None`` if the package belongs to none.
		"""
		return self._parent

	@readonly
	def Classes(self) -> dict[str, Class]:
		"""
		Read-only property to access the classes (:attr:`_classes`).

		:returns: The classes, by name, e.g. ``my/pack/MyClass``; a nested class by its binary name, e.g.
		          ``my/pack/MyClass$Inner``.
		"""
		return self._classes

	@readonly
	def SourceFiles(self) -> dict[str, SourceFile]:
		"""
		Read-only property to access the source files (:attr:`_sourceFiles`).

		:returns: The source files, by name, e.g. ``MyClass.java``.
		"""
		return self._sourceFiles


@export
class Report(CountersMixin, mixin=True):
	"""
	The root element ``<report>``: its name, the sessions, the groups or packages, and the counters.

	The root of the format's model: a session, a group, a package or a counter names it as its parent.
	"""

	_name:          Nullable[str]               #: Name of the report, e.g. of the project measured.
	_formatVersion: Nullable[_FormatVersion]    #: Version of the report format.
	_sessionInfos:  list[SessionInfo]           #: The sessions, which contributed execution data.
	_groups:        dict[str, Group[Report]]    #: The groups, by name.
	_packages:      dict[str, Package[Report]]  #: The packages, by name.

	def __init__(self) -> None:
		"""
		Initialize an empty report.
		"""
		CountersMixin.__init__(self)

		self._name =          None
		self._formatVersion = None
		self._sessionInfos =  []
		self._groups =        {}
		self._packages =      {}

	@readonly
	def Name(self) -> Nullable[str]:
		"""
		Read-only property to access the name of the report (:attr:`_name`).

		:returns: The name, e.g. of the project measured; ``None`` before the report was converted.
		"""
		return self._name

	@readonly
	def FormatVersion(self) -> Nullable[FormatVersion]:
		"""
		Read-only property to access the version of the report format (:attr:`_formatVersion`).

		:returns: The format version; ``None`` before the report was analyzed.
		"""
		return self._formatVersion

	@readonly
	def SessionInfos(self) -> list[SessionInfo]:
		"""
		Read-only property to access the sessions, which contributed execution data (:attr:`_sessionInfos`).

		:returns: The sessions, in the order the report lists them.
		"""
		return self._sessionInfos

	@readonly
	def Groups(self) -> dict[str, Group[Report]]:
		"""
		Read-only property to access the groups (:attr:`_groups`).

		:returns: The groups, by name; empty, if the report has packages.
		"""
		return self._groups

	@readonly
	def Packages(self) -> dict[str, Package[Report]]:
		"""
		Read-only property to access the packages (:attr:`_packages`).

		:returns: The packages, by name; empty, if the report has groups.
		"""
		return self._packages


@export
class Document(cc_Document, Report):
	"""
	A JaCoCo XML code coverage report: read into the format's model, and converted to the common model.
	"""

	_xmlDocument: Nullable[_ElementTree]  #: The parsed and validated XML document, after :meth:`Analyze`.

	def __init__(self, xmlReportFile: Path, analyzeAndConvert: bool = False) -> None:
		"""
		Initialize the report, and optionally read it.

		:param xmlReportFile:     Path to the JaCoCo XML file.
		:param analyzeAndConvert: Optional, if true, analyze the file and convert its content. Default: ``False``.
		"""
		super().__init__(xmlReportFile)
		Report.__init__(self)

		self._xmlDocument = None

		if analyzeAndConvert:
			self.Analyze()
			self.Convert()

	def Analyze(self) -> None:
		"""
		Parse the XML file, read the format version from the DTD's public identifier, and validate the file against the
		XML schema of that version (:data:`SCHEMAS`).

		:raises CodeCoverageError: If the file doesn't exist.
		:raises CodeCoverageError: If the file isn't well-formed XML.
		:raises CodeCoverageError: If the root element isn't ``<report>``.
		:raises CodeCoverageError: If the file states no public identifier of a supported format version.
		:raises CodeCoverageError: If the XML schema can't be located or parsed.
		:raises CodeCoverageError: If the file isn't valid according to the XML schema.
		"""
		if not self._path.exists():
			raise CodeCoverageError(f"JaCoCo report file '{self._path}' does not exist.") \
				from FileNotFoundError(f"File '{self._path}' not found.")

		with Stopwatch() as sw:
			try:
				xmlDocument = parse(self._path, XMLParser(ns_clean=True))
			except XMLSyntaxError as ex:
				raise CodeCoverageError(f"XML syntax error in JaCoCo report file '{self._path}'.") from ex

			rootElement: _Element = xmlDocument.getroot()
			if rootElement.tag != "report":
				ex = CodeCoverageError(f"Root element of '{self._path}' is not '<report>'.")
				ex.add_note(f"Got root element '<{rootElement.tag}>'.")
				raise ex

			publicID = xmlDocument.docinfo.public_id
			match = PUBLIC_IDENTIFIER.fullmatch(publicID) if publicID is not None else None
			if match is None or match[1] not in [member.value for member in FormatVersion]:
				ex = CodeCoverageError(f"JaCoCo report file '{self._path}' states an unsupported format version.")
				ex.add_note(f"Got public identifier '{publicID}'." if publicID is not None else "Got no public identifier.")
				ex.add_note(f"Supported format versions: {', '.join(member.value for member in FormatVersion)}.")
				raise ex

			formatVersion = FormatVersion(match[1])
			schemaFile = SCHEMAS[formatVersion]
			try:
				schemaResourceFile = getResourceFile(Resources, schemaFile)
			except ToolingException as ex:
				raise CodeCoverageError(f"Couldn't locate XML Schema '{schemaFile}' in package resources.") from ex

			try:
				xmlSchema = XMLSchema(parse(schemaResourceFile, XMLParser(ns_clean=True)))
			except (XMLSyntaxError, XMLSchemaParseError) as ex:
				raise CodeCoverageError(f"Error while parsing XML Schema '{schemaFile}'.") from ex

			if not xmlSchema.validate(xmlDocument):
				ex = CodeCoverageError(f"Validation error for '{self._path}' using XSD schema '{schemaFile}'.")
				for logEntry in xmlSchema.error_log:
					ex.add_note(str(logEntry))
				raise ex

			self._xmlDocument =   xmlDocument
			self._formatVersion = formatVersion

		self._analysisDuration = sw.Duration

	def Convert(self) -> None:
		"""
		Convert the parsed and validated XML document to the format's model.

		:raises CodeCoverageError: If the XML file was not analyzed before. |br|
		                           Call 'Document.Analyze()' or create the document using
		                           'Document(path, analyzeAndConvert=True)'.
		:raises CodeCoverageError: If an element states a child element twice.
		"""
		if self._xmlDocument is None:
			ex = CodeCoverageError(f"JaCoCo report file '{self._path}' needs to be read and analyzed by an XML parser.")
			ex.add_note(f"Call 'Document.Analyze()' or create the document using 'Document(path, analyzeAndConvert=True)'.")
			raise ex

		with Stopwatch() as sw:
			root: _Element = self._xmlDocument.getroot()
			self._name = root.attrib["name"]

			for sessionInfoElement in root.iterfind("sessioninfo"):
				SessionInfo.Parse(sessionInfoElement, parent=self)

			for groupElement in root.iterfind("group"):
				if (name := groupElement.attrib["name"]) in self._groups:
					raise CodeCoverageError(f"JaCoCo report '{self._name}' states group '{name}' twice.")

				Group.Parse(groupElement, parent=self)

			for packageElement in root.iterfind("package"):
				if (name := packageElement.attrib["name"]) in self._packages:
					raise CodeCoverageError(f"JaCoCo report '{self._name}' states package '{name}' twice.")

				Package.Parse(packageElement, parent=self)

			for counterElement in root.iterfind("counter"):
				if (counterType := CounterType(counterElement.attrib["type"])) in self._counters:
					raise CodeCoverageError(f"JaCoCo report '{self._name}' states counter '{counterType}' twice.")

				Counter.Parse(counterElement, parent=self)

		self._conversionDuration = sw.Duration

	def ToCoverageSummary(self) -> CoverageSummary:
		"""
		Convert the format's model to the common model, and aggregate it.

		The packages of all groups are converted. A source file's path is its package's name and its name. A line's
		missed and covered branches become as many branches. A method spans its first line and the next lines of its file,
		as many as its ``LINE`` counter counts; a class spans its methods.

		:returns:                  The report's root of the common model, named after the report - or, if the report's
		                           name is empty, after the report file.
		:raises CodeCoverageError: If two packages of the same name state a source file of the same name.
		:raises CodeCoverageError: If a file's path runs through another file.
		"""
		def iteratePackages(element: Report | Group) -> Generator[Package, None, None]:
			"""
			Nested function for recursion.

			:param element: The report or a group.
			:returns:       A generator of the packages of the element and of its groups.
			"""
			for group in element._groups.values():
				yield from iteratePackages(group)

			yield from element._packages.values()

		def getStatus(element: CountersMixin, counterType: CounterType) -> LineCoverageStatus:
			"""
			Nested function returning the coverage state of a class or method by its ``CLASS`` or ``METHOD`` counter.

			:param element:     The class or method.
			:param counterType: The counter's kind.
			:returns:           Covered, if the counter counts a covered item, otherwise uncovered; unknown, if the element has
			                    no such counter.
			"""
			if (counter := element._counters.get(counterType)) is None:
				return LineCoverageStatus.Unknown

			return LineCoverageStatus.Covered if counter._coveredCount > 0 else LineCoverageStatus.Uncovered

		summary = CoverageSummary(self._name if self._name is not None and self._name != "" else self._path.stem)

		for package in iteratePackages(self):
			for sourceFile in package._sourceFiles.values():
				file = summary.GetOrAddFile(Path(package._name) / sourceFile._name)
				for number in sorted(sourceFile._lines):
					line = sourceFile._lines[number]
					missedBranchCount =  line._missedBranchCount if line._missedBranchCount is not None else 0
					coveredBranchCount = line._coveredBranchCount if line._coveredBranchCount is not None else 0
					branches =           [cc_Branch(LineCoverageStatus.Covered) for _ in range(coveredBranchCount)]
					branches.extend(cc_Branch(LineCoverageStatus.Uncovered) for _ in range(missedBranchCount))
					if line._coveredInstructionCount is None:
						status = LineCoverageStatus.Unknown
					elif line._coveredInstructionCount == 0:
						status = LineCoverageStatus.Uncovered
					elif missedBranchCount > 0:
						status = LineCoverageStatus.PartiallyCovered
					else:
						status = LineCoverageStatus.Covered
					cc_Line(number, status, None, branches, parent=file)

		for package in iteratePackages(self):
			parent: cc_Unit | CoverageSummary = summary
			for part in (part for part in package._name.split("/") if part != ""):
				parent = parent._units[part] if part in parent._units else cc_Package(part, parent=parent)

			for klass in package._classes.values():
				file = None
				if klass._sourceFileName is not None and klass._sourceFileName in package._sourceFiles:
					file = summary.GetOrAddFile(Path(package._name) / klass._sourceFileName)

				# per method with a first line in the file: its first and last line
				spans: dict[str, tuple[cc_Line, cc_Line]] = {}
				for key, method in klass._methods.items():
					if (
						file is None or method._lineNumber is None or method._lineNumber > file._lastLineNumber or
						(startLine := file._lines[method._lineNumber]) is None
					):
						continue

					counter =    method._counters.get(CounterType.Line)
					lineCount =  counter._missedCount + counter._coveredCount if counter is not None else 1
					lines =      list(islice(file.IterateLines(startLine), max(lineCount, 1)))
					spans[key] = (startLine, lines[-1])

				if (classUnit := parent._units.get(name := klass._name.rpartition("/")[2])) is None:
					classUnit = cc_Class(
						name,
						file=file,
						startLine=min((span[0] for span in spans.values()), key=lambda line: line._lineNumber, default=None),
						endLine=max((span[1] for span in spans.values()), key=lambda line: line._lineNumber, default=None),
						status=getStatus(klass, CounterType.Class),
						parent=parent
					)

				for key, method in klass._methods.items():
					if key not in classUnit._units:
						cc_Method(
							key,
							file=file,
							startLine=spans[key][0] if key in spans else None,
							endLine=spans[key][1] if key in spans else None,
							status=getStatus(method, CounterType.Method),
							parent=classUnit
						)

		summary.Aggregate()
		return summary
