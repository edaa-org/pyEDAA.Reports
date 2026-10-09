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
#   Artur Porebski (Aldec Inc.)                                                                                        #
#   Michal Pacula  (Aldec Inc.)                                                                                        #
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
Aldec's UCDB XML code coverage format: a model of the format, read from a report and converted to the common model.

Aldec's simulators Riviera-PRO and Active-HDL keep code coverage in a coverage database (ACDB), which the tool
``acdb2xml`` exports as XML: ``acdb2xml -i aggregate.acdb -o ucdb.xml``. The XML names its namespace ``www.aldec.com``
and its root ``<ux:ucdb>``; it is a dump of the database's UCIS data model - scopes, coverage items (bins) and history
nodes -, not the XML interchange format of the UCIS standard. A report states no format version, only the tool's name
and version, e.g. ``Riviera-PRO 2022.04``; it is validated against :file:`Aldec-UCDB.xsd` (:data:`SCHEMA`),
reverse-engineered from reports of Riviera-PRO.

The format's model keeps what the report states: a :class:`Document` holds its attributes,
:class:`~pyEDAA.Reports.CodeCoverage.AldecUCDB.Elements.HistoryNode` elements - nested, a merge holds the tests it
merged -, :class:`~pyEDAA.Reports.CodeCoverage.AldecUCDB.Scopes.Scope` elements - nested, e.g. design units, their
instances, processes and branching statements - with their :class:`~pyEDAA.Reports.CodeCoverage.AldecUCDB.Scopes.Bin`
elements, and :class:`~pyEDAA.Reports.CodeCoverage.AldecUCDB.Elements.Command` elements. Each element's constructor
takes typed values, so the model can be built by hand: an element below the report names its parent with the keyword
parameter ``parent`` and is added to it. Its class method ``Parse`` reads the element's XML element.

:meth:`Document.ToCoverageSummary` converts the statement coverage to the common model of
:mod:`pyEDAA.Reports.CodeCoverage`:

* The statements are the statement bins (``STMTBIN``) of the instances: the bins of the scopes below each top-level
  scope, which isn't a design unit. A statement is identified by its file, its line and its index in the line
  (attribute ``#SINDEX#``); with ``mergeInstances``, the statements of all instances of a design unit are merged into
  one, which ran as often as in all instances together (:meth:`Report.IterateStatements`).
* A file's path is the one a statement bin's source location states, relative to the directory the tool ran in; these
  directories are the summary's source directories.
* A line ran as often as its least often run statement: it is covered, if all its statements ran. A line, whose
  statements are all excluded, is excluded; an excluded statement doesn't count for its line.
* The branches, the blocks and the other kinds of coverage aren't converted, and the format names no units.

.. rubric:: Example

.. code-block:: Python

   from pathlib import Path
   from pyEDAA.Reports.CodeCoverage.AldecUCDB import Document

   report = Document(Path("ucdb.xml"), analyzeAndConvert=True)
   summary = report.ToCoverageSummary(mergeInstances=True)
   for file in summary.IterateFiles():
     print(f"{file.Path}: {file.LineCoverage:.1%}")
"""
from __future__                                      import annotations

from pathlib                                         import Path
from typing                                          import Generator, Iterable, Optional as Nullable

from lxml.etree                                      import XMLParser, XMLSchema, XMLSchemaParseError, XMLSyntaxError
from lxml.etree                                      import _Element, _ElementTree, parse
from pyTooling.Common                                import getFullyQualifiedName, getResourceFile
from pyTooling.Decorators                            import export, readonly
from pyTooling.Exceptions                            import ToolingException
from pyTooling.MetaClasses                           import ExtendedType
from pyTooling.Stopwatch                             import Stopwatch
from pyTooling.Versioning                            import CalendarVersion

from pyEDAA.Reports                                  import Resources
from pyEDAA.Reports.CodeCoverage                     import CodeCoverageError, CoverageSummary, Document as cc_Document
from pyEDAA.Reports.CodeCoverage                     import Line as cc_Line, LineCoverageStatus
from pyEDAA.Reports.CodeCoverage.AldecUCDB.Elements  import AttributesMixin, Command, CoverType, HistoryNode, NAMESPACE
from pyEDAA.Reports.CodeCoverage.AldecUCDB.Elements  import NAMESPACES, ScopeType
from pyEDAA.Reports.CodeCoverage.AldecUCDB.Scopes    import Bin, Scope


__all__ = ["SCHEMA"]

SCHEMA = "Aldec-UCDB.xsd"  #: The XML schema a report is validated against.


@export
class Statement(metaclass=ExtendedType, slots=True):
	"""
	A statement of a source line: its statement bins - of one instance, or merged, of all instances -, and how often it
	ran.

	A statement isn't an element of the format: :meth:`Report.IterateStatements` computes it from the bins.
	"""

	_file:       Path       #: Path of the source file.
	_lineNumber: int        #: Line number, counted from 1.
	_index:      int        #: Index of the statement in its line.
	_bins:       list[Bin]  #: The statement bins of the statement.
	_count:      int        #: How often the statement ran: the sum of its bins' counts, without the excluded ones.
	_isExcluded: bool       #: Whether all the statement's bins are excluded.

	def __init__(self, file: Path, lineNumber: int, index: int, bins: Iterable[Bin]) -> None:
		"""
		Initialize the statement, its count and whether it is excluded.

		:param file:        Path of the source file, as the bins' source locations state it.
		:param lineNumber:  Line number, counted from 1.
		:param index:       Index of the statement in its line, counted from 1.
		:param bins:        The statement bins of the statement: one, or of all instances, if merged.
		:raises ValueError: If parameter ``file`` is ``None``.
		:raises TypeError:  If parameter ``file`` isn't of type :class:`~pathlib.Path`.
		:raises ValueError: If parameter ``lineNumber`` is ``None``.
		:raises TypeError:  If parameter ``lineNumber`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``lineNumber`` is less than 1.
		:raises ValueError: If parameter ``index`` is ``None``.
		:raises TypeError:  If parameter ``index`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``index`` is negative.
		:raises ValueError: If parameter ``bins`` is ``None``.
		:raises TypeError:  If parameter ``bins`` isn't iterable.
		:raises TypeError:  If parameter ``bins`` contains an element not of type
		                    :class:`~pyEDAA.Reports.CodeCoverage.AldecUCDB.Scopes.Bin`.
		:raises ValueError: If parameter ``bins`` is empty.
		"""
		if file is None:
			raise ValueError(f"Parameter 'file' is None.")
		elif not isinstance(file, Path):
			ex = TypeError(f"Parameter 'file' is not of type 'Path'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(file)}'.")
			raise ex

		if lineNumber is None:
			raise ValueError(f"Parameter 'lineNumber' is None.")
		elif not isinstance(lineNumber, int):
			ex = TypeError(f"Parameter 'lineNumber' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(lineNumber)}'.")
			raise ex
		elif lineNumber < 1:
			ex = ValueError(f"Parameter 'lineNumber' is less than 1.")
			ex.add_note(f"Got value '{lineNumber}'.")
			raise ex

		if index is None:
			raise ValueError(f"Parameter 'index' is None.")
		elif not isinstance(index, int):
			ex = TypeError(f"Parameter 'index' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(index)}'.")
			raise ex
		elif index < 0:
			ex = ValueError(f"Parameter 'index' is negative.")
			ex.add_note(f"Got value '{index}'.")
			raise ex

		if bins is None:
			raise ValueError(f"Parameter 'bins' is None.")
		elif not isinstance(bins, Iterable):
			ex = TypeError(f"Parameter 'bins' is not iterable.")
			ex.add_note(f"Got type '{getFullyQualifiedName(bins)}'.")
			raise ex

		self._file =       file
		self._lineNumber = lineNumber
		self._index =      index
		self._bins =       []
		self._count =      0
		self._isExcluded = True

		for coverBin in bins:
			if not isinstance(coverBin, Bin):
				ex = TypeError(f"Parameter 'bins' contains an element not of type 'Bin'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(coverBin)}'.")
				raise ex

			self._bins.append(coverBin)
			if not coverBin.IsExcluded:
				self._count +=     coverBin._count
				self._isExcluded = False

		if len(self._bins) == 0:
			raise ValueError(f"Parameter 'bins' is empty.")

	@readonly
	def File(self) -> Path:
		"""
		Read-only property to access the path of the source file (:attr:`_file`).

		:returns: The path, as the bins' source locations state it.
		"""
		return self._file

	@readonly
	def LineNumber(self) -> int:
		"""
		Read-only property to access the line number (:attr:`_lineNumber`).

		:returns: The line number, counted from 1.
		"""
		return self._lineNumber

	@readonly
	def Index(self) -> int:
		"""
		Read-only property to access the index of the statement in its line (:attr:`_index`).

		:returns: The index, counted from 1.
		"""
		return self._index

	@readonly
	def Bins(self) -> list[Bin]:
		"""
		Read-only property to access the statement bins of the statement (:attr:`_bins`).

		:returns: The bins: one, or of all instances, if merged.
		"""
		return self._bins

	@readonly
	def Count(self) -> int:
		"""
		Read-only property to access how often the statement ran (:attr:`_count`).

		:returns: The sum of the counts of the bins, which aren't excluded.
		"""
		return self._count

	@readonly
	def IsExcluded(self) -> bool:
		"""
		Read-only property to access whether the statement is excluded from the measurement (:attr:`_isExcluded`).

		:returns: ``True``, if all its bins are excluded.
		"""
		return self._isExcluded


@export
class Report(AttributesMixin, mixin=True):
	"""
	The root element ``<ux:ucdb>``: the tool, which wrote it, its attributes, the history nodes, the scopes and the
	commands.

	The root of the format's model: a history node, a scope or a command names it as its parent.
	"""

	_tool:         Nullable[str]               #: Name of the tool, which wrote the report.
	_toolVersion:  Nullable[CalendarVersion]   #: Version of the tool, which wrote the report.
	_historyNodes: list[HistoryNode[Report]]   #: The history nodes.
	_scopes:       list[Scope[Report]]         #: The top-level scopes.
	_commands:     list[Command]               #: The commands.

	def __init__(self) -> None:
		"""
		Initialize an empty report.
		"""
		AttributesMixin.__init__(self)

		self._tool =         None
		self._toolVersion =  None
		self._historyNodes = []
		self._scopes =       []
		self._commands =     []

	@readonly
	def Tool(self) -> Nullable[str]:
		"""
		Read-only property to access the name of the tool, which wrote the report (:attr:`_tool`).

		:returns: The tool's name, e.g. ``Riviera-PRO``; ``None`` before the report was converted.
		"""
		return self._tool

	@readonly
	def ToolVersion(self) -> Nullable[CalendarVersion]:
		"""
		Read-only property to access the version of the tool, which wrote the report (:attr:`_toolVersion`).

		:returns: The tool's version, e.g. ``2022.04``; ``None`` before the report was converted.
		"""
		return self._toolVersion

	@readonly
	def HistoryNodes(self) -> list[HistoryNode[Report]]:
		"""
		Read-only property to access the history nodes (:attr:`_historyNodes`).

		:returns: The history nodes, in the order the report lists them: the tests, or the merge of the tests.
		"""
		return self._historyNodes

	@readonly
	def Scopes(self) -> list[Scope[Report]]:
		"""
		Read-only property to access the top-level scopes (:attr:`_scopes`).

		:returns: The scopes, in the order the report lists them: e.g. the design units and the top-level instances.
		"""
		return self._scopes

	@readonly
	def Commands(self) -> list[Command]:
		"""
		Read-only property to access the commands (:attr:`_commands`).

		:returns: The commands, in the order the report lists them.
		"""
		return self._commands

	def IterateStatements(self, mergeInstances: bool = False) -> Generator[Statement, None, None]:
		"""
		Iterate the statements: the statement bins of the instances.

		The statement bins are those of the scopes below each top-level scope, which isn't a design unit. A statement is
		identified by its file, its line and its index in the line - attribute ``#SINDEX#`` of its bin.

		:param mergeInstances:     Optional, if true, merge the bins of all instances, which identify the same statement,
		                           into one statement; otherwise each bin is a statement. Default: ``False``.
		:returns:                  A generator of the statements, in the order of their first bin.
		:raises ValueError:        If parameter ``mergeInstances`` is ``None``.
		:raises TypeError:         If parameter ``mergeInstances`` isn't of type :class:`bool`.
		:raises CodeCoverageError: If a statement bin states no statement index.
		"""
		if mergeInstances is None:
			raise ValueError(f"Parameter 'mergeInstances' is None.")
		elif not isinstance(mergeInstances, bool):
			ex = TypeError(f"Parameter 'mergeInstances' is not of type 'bool'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(mergeInstances)}'.")
			raise ex

		designUnits = (
			ScopeType.DesignUnitModule, ScopeType.DesignUnitArchitecture, ScopeType.DesignUnitPackage,
			ScopeType.DesignUnitProgram, ScopeType.DesignUnitInterface
		)
		mergedBins: dict[tuple[Path, int, int], list[Bin]] = {}
		for scope in self._scopes:
			if scope._type in designUnits:
				continue

			for coverBin in scope.IterateBins():
				if coverBin._type is not CoverType.StatementBin:
					continue

				source = coverBin._source
				if not isinstance(index := coverBin._attributes.get("#SINDEX#"), int):
					ex = CodeCoverageError(
						f"UCDB statement bin at '{source._file.as_posix()}:{source._lineNumber}' states no statement index."
					)
					ex.add_note(f"A statement bin states its index in the line by attribute '#SINDEX#' of type 'int'.")
					raise ex

				if mergeInstances:
					mergedBins.setdefault((source._file, source._lineNumber, index), []).append(coverBin)
				else:
					yield Statement(source._file, source._lineNumber, index, (coverBin, ))

		for (file, lineNumber, index), bins in mergedBins.items():
			yield Statement(file, lineNumber, index, bins)


@export
class Document(cc_Document, Report):
	"""
	An Aldec UCDB XML code coverage report: read into the format's model, and converted to the common model.
	"""

	_xmlDocument: Nullable[_ElementTree]  #: The parsed and validated XML document, after :meth:`Analyze`.

	def __init__(self, xmlReportFile: Path, analyzeAndConvert: bool = False) -> None:
		"""
		Initialize the report, and optionally read it.

		:param xmlReportFile:     Path to the UCDB XML file.
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
		Parse the XML file, check its root element, and validate the file against the XML schema (:data:`SCHEMA`).

		:raises CodeCoverageError: If the file doesn't exist.
		:raises CodeCoverageError: If the file can't be read.
		:raises CodeCoverageError: If the file isn't well-formed XML.
		:raises CodeCoverageError: If the root element isn't ``<ux:ucdb>`` of namespace ``www.aldec.com``.
		:raises CodeCoverageError: If the XML schema can't be located or parsed.
		:raises CodeCoverageError: If the file isn't valid according to the XML schema.
		"""
		if not self._path.exists():
			raise CodeCoverageError(f"Aldec UCDB file '{self._path}' does not exist.") \
				from FileNotFoundError(f"File '{self._path}' not found.")

		with Stopwatch() as sw:
			try:
				with self._path.open("rb") as file:
					xmlDocument = parse(file, XMLParser(ns_clean=True))
			except OSError as ex:
				raise CodeCoverageError(f"Couldn't read Aldec UCDB file '{self._path}'.") from ex
			except XMLSyntaxError as ex:
				raise CodeCoverageError(f"XML syntax error in Aldec UCDB file '{self._path}'.") from ex

			rootElement: _Element = xmlDocument.getroot()
			if rootElement.tag != f"{{{NAMESPACE}}}ucdb":
				ex = CodeCoverageError(f"Root element of '{self._path}' is not '<ux:ucdb>' of namespace '{NAMESPACE}'.")
				ex.add_note(f"Got root element '<{rootElement.tag}>'.")
				raise ex

			try:
				schemaResourceFile = getResourceFile(Resources, SCHEMA)
			except ToolingException as ex:
				raise CodeCoverageError(f"Couldn't locate XML Schema '{SCHEMA}' in package resources.") from ex

			try:
				xmlSchema = XMLSchema(parse(schemaResourceFile, XMLParser(ns_clean=True)))
			except (XMLSyntaxError, XMLSchemaParseError) as ex:
				raise CodeCoverageError(f"Error while parsing XML Schema '{SCHEMA}'.") from ex

			if not xmlSchema.validate(xmlDocument):
				ex = CodeCoverageError(f"Validation error for '{self._path}' using XSD schema '{SCHEMA}'.")
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
		:raises CodeCoverageError: If an attribute's value isn't of the type the attribute states.
		"""
		if self._xmlDocument is None:
			ex = CodeCoverageError(f"Aldec UCDB file '{self._path}' needs to be read and analyzed by an XML parser.")
			ex.add_note(f"Call 'Document.Analyze()' or create the document using 'Document(path, analyzeAndConvert=True)'.")
			raise ex

		with Stopwatch() as sw:
			root: _Element = self._xmlDocument.getroot()
			tool, _, version = root.attrib["version"].rpartition(" ")
			self._tool =        tool
			self._toolVersion = CalendarVersion.Parse(version)
			self._attributes =  self._ParseAttributes(root)

			for historyNodeElement in root.iterfind("ux:hnode", NAMESPACES):
				HistoryNode.Parse(historyNodeElement, parent=self)

			for scopeElement in root.iterfind("ux:scope", NAMESPACES):
				Scope.Parse(scopeElement, parent=self)

			for commandElement in root.iterfind("ux:command", NAMESPACES):
				Command.Parse(commandElement, parent=self)

		self._conversionDuration = sw.Duration

	def ToCoverageSummary(self, mergeInstances: bool = False) -> CoverageSummary:
		"""
		Convert the statement coverage of the format's model to the common model, and aggregate it.

		A line ran as often as its least often run statement (:meth:`~Report.IterateStatements`): it is covered, if all its
		statements ran, otherwise uncovered. A line, whose statements are all excluded, is excluded.

		:param mergeInstances:     Optional, if true, merge the statements of all instances of a design unit. Default:
		                           ``False``.
		:returns:                  The report's root of the common model, named after the report file. Its source
		                           directories are the directories the tool ran in.
		:raises ValueError:        If parameter ``mergeInstances`` is ``None``.
		:raises TypeError:         If parameter ``mergeInstances`` isn't of type :class:`bool`.
		:raises CodeCoverageError: If a statement bin states no statement index.
		:raises CodeCoverageError: If a file's path runs through another file.
		"""
		statementsPerFile: dict[Path, dict[int, list[Statement]]] = {}
		sourceDirectories: dict[Path, None] = {}
		for statement in self.IterateStatements(mergeInstances):
			statementsPerFile.setdefault(statement._file, {}).setdefault(statement._lineNumber, []).append(statement)
			for coverBin in statement._bins:
				sourceDirectories[coverBin._source._workDirectory] = None

		summary = CoverageSummary(self._path.stem, sourceDirectories=sourceDirectories)
		for path, statementsPerLine in statementsPerFile.items():
			file = summary.GetOrAddFile(path)
			for lineNumber in sorted(statementsPerLine):
				counts = [statement._count for statement in statementsPerLine[lineNumber] if not statement._isExcluded]
				if len(counts) == 0:
					cc_Line(lineNumber, LineCoverageStatus.Excluded, parent=file)
				else:
					count = min(counts)
					status = LineCoverageStatus.Covered if count > 0 else LineCoverageStatus.Uncovered
					cc_Line(lineNumber, status, count, parent=file)

		summary.Aggregate()
		return summary
