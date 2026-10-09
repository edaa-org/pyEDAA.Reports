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
The XML interchange format of the Accellera UCIS standard: a model of the format, read from a report and converted to
the common model.

The `Unified Coverage Interoperability Standard (UCIS) <https://www.accellera.org/downloads/standards/ucis>`__ 1.0
specifies a coverage database's data model, a C API and an XML interchange format. An XML report names the namespace
``UCIS`` and its root ``<UCIS>``, which states the UCIS version (:class:`FormatVersion`), the tool, which wrote the
report, and when. It is validated against the XML schema of that version (:data:`SCHEMAS`): :file:`UCIS-1.0.xsd`,
written after the schema the standard specifies.

The format's model keeps what the report states: a :class:`Document` holds
:class:`~pyEDAA.Reports.CodeCoverage.UCIS.Instances.SourceFile` elements - by their ID -,
:class:`~pyEDAA.Reports.CodeCoverage.UCIS.HistoryNodes.HistoryNode` elements - the tests and merges, by their ID - and
:class:`~pyEDAA.Reports.CodeCoverage.UCIS.Instances.InstanceCoverage` elements. An instance holds its coverage of each
kind, once per metric mode: :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Blocks.BlockCoverage` - statements, blocks,
processes -, :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Branches.BranchCoverage` - branching statements and their
branches -, :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Toggles.ToggleCoverage`,
:class:`~pyEDAA.Reports.CodeCoverage.UCIS.Conditions.ConditionCoverage`,
:class:`~pyEDAA.Reports.CodeCoverage.UCIS.FSMs.FSMCoverage`,
:class:`~pyEDAA.Reports.CodeCoverage.UCIS.Assertions.AssertionCoverage` and
:class:`~pyEDAA.Reports.CodeCoverage.UCIS.Covergroups.CovergroupCoverage`. A coverage item states its count in a
:class:`~pyEDAA.Reports.CodeCoverage.UCIS.Bins.Bin`, and where it is in a
:class:`~pyEDAA.Reports.CodeCoverage.UCIS.Elements.StatementID`: the source file's ID, the line and the index of the
statement in the line. Each element's constructor takes typed values, so the model can be built by hand: an element
below the report names its parent with the keyword parameter ``parent`` and is added to it. Its class method ``Parse``
reads the element's XML element.

:meth:`Document.ToCoverageSummary` converts the statement and branch coverage to the common model of
:mod:`pyEDAA.Reports.CodeCoverage`:

* The statements are the statements of the block coverages, and the statements of their blocks, which ran as often as
  their block. A statement is identified by its file, its line and its index in the line; with ``mergeInstances``, the
  statements of all instances are merged into one, which ran as often as in all instances together.
* A file's path is the one its source file states.
* A line ran as often as its least often run statement: it is covered, if all its statements ran. A line, whose
  statements are all excluded, is excluded; an excluded statement doesn't count for its line.
* A branching statement's branches - with ``mergeInstances`` summed over the instances - become branches of its line; a
  line, which ran without taking all its branches, is partially covered. A branch goes to the line of its first
  statement. An excluded branch or branching statement isn't converted.
* A design unit, whose instances name it, becomes a :class:`~pyEDAA.Reports.CodeCoverage.Module`, spanning the lines
  of its statements, if they are in one file.
* The toggle, condition, expression, FSM, assertion and covergroup coverage stays in the format's model.

.. rubric:: Example

.. code-block:: Python

   from pathlib import Path
   from pyEDAA.Reports.CodeCoverage.UCIS import Document

   report = Document(Path("coverage.xml"), analyzeAndConvert=True)
   summary = report.ToCoverageSummary(mergeInstances=True)
   for file in summary.IterateFiles():
     print(f"{file.Path}: {file.LineCoverage:.1%}")
"""
from __future__                                    import annotations

from datetime                                      import datetime
from pathlib                                       import Path
from typing                                        import ClassVar, Generator, Optional as Nullable

from lxml.etree                                    import XMLParser, XMLSchema, XMLSchemaParseError, XMLSyntaxError
from lxml.etree                                    import _Element, _ElementTree, parse
from pyTooling.Common                              import getFullyQualifiedName, getResourceFile, StringEnum
from pyTooling.Decorators                          import export, readonly
from pyTooling.Exceptions                          import ToolingException
from pyTooling.MetaClasses                         import ExtendedType
from pyTooling.Stopwatch                           import Stopwatch

from pyEDAA.Reports                                import Resources
from pyEDAA.Reports.CodeCoverage                   import Branch as cc_Branch, CodeCoverageError, CoverageSummary
from pyEDAA.Reports.CodeCoverage                   import Document as cc_Document, Line as cc_Line, LineCoverageStatus
from pyEDAA.Reports.CodeCoverage                   import Module as cc_Module
from pyEDAA.Reports.CodeCoverage.UCIS.Blocks       import Statement
from pyEDAA.Reports.CodeCoverage.UCIS.Branches     import BranchStatement
from pyEDAA.Reports.CodeCoverage.UCIS.HistoryNodes import HistoryNode
from pyEDAA.Reports.CodeCoverage.UCIS.Instances    import InstanceCoverage, SourceFile


__all__ = ["NAMESPACE", "SCHEMAS"]

NAMESPACE = "UCIS"  #: The XML namespace of the format's elements.


@export
class FormatVersion(StringEnum):
	"""
	Version of the UCIS XML interchange format: the UCIS version a report's root states in ``ucisVersion``.
	"""

	Version1_0 = "1.0"  #: UCIS 1.0, June 2012.


# A class with a property named like a class - ``FormatVersion`` - can't name that class in the annotation of a field:
# the class body's namespace, where annotations are evaluated, binds the name to the property.
_FormatVersion = FormatVersion

SCHEMAS: dict[FormatVersion, str] = {
	FormatVersion.Version1_0: "UCIS-1.0.xsd"
}  #: Per format version, the XML schema a report of that version is validated against.


@export
class Report(metaclass=ExtendedType, mixin=True):
	"""
	The root element ``<UCIS>``: its UCIS version, the tool, which wrote it, and when, its source files, history nodes and
	instances.

	The root of the format's model: a source file, a history node or an instance names it as its parent.
	"""

	_formatVersion: Nullable[_FormatVersion]       #: The UCIS version the report states.
	_writtenBy:     Nullable[str]                  #: Name of the tool, which wrote the report.
	_writtenTime:   Nullable[datetime]             #: When the report was written.
	_sourceFiles:   dict[int, SourceFile]          #: The source files, by ID.
	_historyNodes:  dict[int, HistoryNode]         #: The history nodes, by ID.
	_instances:     list[InstanceCoverage]         #: The instances.

	def __init__(self) -> None:
		"""
		Initialize an empty report.
		"""
		self._formatVersion = None
		self._writtenBy =     None
		self._writtenTime =   None
		self._sourceFiles =   {}
		self._historyNodes =  {}
		self._instances =     []

	@readonly
	def FormatVersion(self) -> Nullable[_FormatVersion]:
		"""
		Read-only property to access the UCIS version the report states (:attr:`_formatVersion`).

		:returns: The version; ``None`` before the report was analyzed.
		"""
		return self._formatVersion

	@readonly
	def WrittenBy(self) -> Nullable[str]:
		"""
		Read-only property to access the name of the tool, which wrote the report (:attr:`_writtenBy`).

		:returns: The tool's name, as stated; ``None`` before the report was converted.
		"""
		return self._writtenBy

	@readonly
	def WrittenTime(self) -> Nullable[datetime]:
		"""
		Read-only property to access when the report was written (:attr:`_writtenTime`).

		:returns: The date and time; ``None`` before the report was converted.
		"""
		return self._writtenTime

	@readonly
	def SourceFiles(self) -> dict[int, SourceFile]:
		"""
		Read-only property to access the source files (:attr:`_sourceFiles`).

		:returns: The source files, by the ID statement identifiers name them by.
		"""
		return self._sourceFiles

	@readonly
	def HistoryNodes(self) -> dict[int, HistoryNode]:
		"""
		Read-only property to access the history nodes (:attr:`_historyNodes`).

		:returns: The history nodes, by the ID bins name them by.
		"""
		return self._historyNodes

	@readonly
	def Instances(self) -> list[InstanceCoverage]:
		"""
		Read-only property to access the instances (:attr:`_instances`).

		:returns: The instances, in the order the report lists them.
		"""
		return self._instances

	def IterateStatements(self) -> Generator[Statement, None, None]:
		"""
		Iterate the statements of all instances' block coverages.

		:returns: A generator of the statements, in the order the report lists them.
		"""
		for instance in self._instances:
			for blockCoverage in instance._blockCoverages:
				yield from blockCoverage._statements

	def IterateBranchStatements(self) -> Generator[BranchStatement, None, None]:
		"""
		Iterate the branching statements of all instances' branch coverages, nested ones included.

		:returns: A generator of the branching statements, each followed by the branching statements nested in it.
		"""
		for instance in self._instances:
			for branchCoverage in instance._branchCoverages:
				yield from branchCoverage.IterateStatements()


@export
class Document(cc_Document, Report):
	"""
	A UCIS XML code coverage report: read into the format's model, and converted to the common model.
	"""

	_NAMESPACE: ClassVar[Nullable[str]] =            NAMESPACE  #: The XML namespace of the elements; ``None`` for none.
	_SCHEMAS:   ClassVar[dict[FormatVersion, str]] = SCHEMAS    #: Per format version, the XML schema to validate with.

	_xmlDocument: Nullable[_ElementTree]  #: The parsed and validated XML document, after :meth:`Analyze`.

	def __init__(self, xmlReportFile: Path, analyzeAndConvert: bool = False) -> None:
		"""
		Initialize the report, and optionally read it.

		:param xmlReportFile:     Path to the UCIS XML file.
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
		Parse the XML file, check its root element, read its UCIS version, and validate the file against the XML schema of
		that version (:attr:`_SCHEMAS`).

		:raises CodeCoverageError: If the file doesn't exist.
		:raises CodeCoverageError: If the file can't be read.
		:raises CodeCoverageError: If the file isn't well-formed XML.
		:raises CodeCoverageError: If the root element isn't ``<UCIS>`` of the namespace :attr:`_NAMESPACE`.
		:raises CodeCoverageError: If the file states no supported UCIS version.
		:raises CodeCoverageError: If the XML schema can't be located or parsed.
		:raises CodeCoverageError: If the file isn't valid according to the XML schema.
		"""
		if not self._path.exists():
			raise CodeCoverageError(f"UCIS XML file '{self._path}' does not exist.") \
				from FileNotFoundError(f"File '{self._path}' not found.")

		with Stopwatch() as sw:
			try:
				with self._path.open("rb") as file:
					xmlDocument = parse(file, XMLParser(ns_clean=True))
			except OSError as ex:
				raise CodeCoverageError(f"Couldn't read UCIS XML file '{self._path}'.") from ex
			except XMLSyntaxError as ex:
				raise CodeCoverageError(f"XML syntax error in UCIS XML file '{self._path}'.") from ex

			rootElement: _Element = xmlDocument.getroot()
			rootTag = "UCIS" if self._NAMESPACE is None else f"{{{self._NAMESPACE}}}UCIS"
			if rootElement.tag != rootTag:
				ex = CodeCoverageError(f"Root element of '{self._path}' is not '<{rootTag}>'.")
				ex.add_note(f"Got root element '<{rootElement.tag}>'.")
				raise ex

			version = rootElement.attrib.get("ucisVersion")
			if version not in [member.value for member in FormatVersion]:
				ex = CodeCoverageError(f"UCIS XML file '{self._path}' states an unsupported UCIS version.")
				ex.add_note(f"Got version '{version}'." if version is not None else "Got no version.")
				ex.add_note(f"Supported UCIS versions: {', '.join(member.value for member in FormatVersion)}.")
				raise ex

			formatVersion = FormatVersion(version)
			schemaFile = self._SCHEMAS[formatVersion]
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
		:raises CodeCoverageError: If the report states a source file's or a history node's ID twice.
		:raises CodeCoverageError: If a user-defined attribute's value isn't of the type the attribute states.
		"""
		if self._xmlDocument is None:
			ex = CodeCoverageError(f"UCIS XML file '{self._path}' needs to be read and analyzed by an XML parser.")
			ex.add_note(f"Call 'Document.Analyze()' or create the document using 'Document(path, analyzeAndConvert=True)'.")
			raise ex

		with Stopwatch() as sw:
			root: _Element = self._xmlDocument.getroot()
			self._writtenBy =   root.attrib["writtenBy"]
			self._writtenTime = datetime.fromisoformat(root.attrib["writtenTime"])

			for sourceFileElement in root.iterfind("{*}sourceFiles"):
				if (sourceFileID := int(sourceFileElement.attrib["id"])) in self._sourceFiles:
					raise CodeCoverageError(f"UCIS XML file '{self._path}' states source file ID '{sourceFileID}' twice.")

				SourceFile.Parse(sourceFileElement, parent=self)

			for historyNodeElement in root.iterfind("{*}historyNodes"):
				if (historyNodeID := int(historyNodeElement.attrib["historyNodeId"])) in self._historyNodes:
					raise CodeCoverageError(f"UCIS XML file '{self._path}' states history node ID '{historyNodeID}' twice.")

				HistoryNode.Parse(historyNodeElement, parent=self)

			for instanceElement in root.iterfind("{*}instanceCoverages"):
				InstanceCoverage.Parse(instanceElement, parent=self)

		self._conversionDuration = sw.Duration

	def ToCoverageSummary(self, mergeInstances: bool = False) -> CoverageSummary:
		"""
		Convert the statement and branch coverage of the format's model to the common model, and aggregate it.

		A line ran as often as its least often run statement: it is covered, if all its statements ran, otherwise
		uncovered; partially covered, if it ran without taking all its branches. A line, whose statements are all excluded,
		is excluded. A design unit, whose statements are in one file, becomes a module spanning their lines.

		:param mergeInstances:     Optional, if true, merge the statements and branches of all instances. Default:
		                           ``False``.
		:returns:                  The report's root of the common model, named after the report file. Its source
		                           directories are the directories the tests ran in.
		:raises ValueError:        If parameter ``mergeInstances`` is ``None``.
		:raises TypeError:         If parameter ``mergeInstances`` isn't of type :class:`bool`.
		:raises CodeCoverageError: If a statement identifier names a source file the report doesn't state.
		:raises CodeCoverageError: If a file's path runs through another file.
		"""
		if mergeInstances is None:
			raise ValueError(f"Parameter 'mergeInstances' is None.")
		elif not isinstance(mergeInstances, bool):
			ex = TypeError(f"Parameter 'mergeInstances' is not of type 'bool'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(mergeInstances)}'.")
			raise ex

		# A statement's or branching statement's key: the instance's index - 0, if merged -, file ID, line, index in line.
		statementCounts: dict[tuple[int, int, int, int], Nullable[int]] = {}          # None: excluded
		branchCounts:    dict[tuple[int, int, int, int], list[Nullable[int]]] = {}    # per branch; None: excluded
		branchTargets:   dict[tuple[int, int, int, int], list[int]] = {}              # per branch: the line it goes to
		moduleLines:     dict[str, set[tuple[int, int]]] = {}                         # file ID and line, per design unit

		for instanceIndex, instance in enumerate(self._instances):
			scope = 0 if mergeInstances else instanceIndex
			lines = moduleLines.setdefault(instance._moduleName, set()) if instance._moduleName is not None else set()
			for blockCoverage in instance._blockCoverages:
				counted = [(statement._id, statement._bin, statement._isExcluded) for statement in blockCoverage._statements]
				for block in blockCoverage.IterateBlocks():
					for statementID in block._statementIDs if len(block._statementIDs) > 0 else (block._id, ):
						counted.append((statementID, block._bin, block._isExcluded))

				for statementID, coverBin, isExcluded in counted:
					if statementID._fileID not in self._sourceFiles:
						ex = CodeCoverageError(f"UCIS statement identifier names source file ID '{statementID._fileID}'.")
						ex.add_note(f"The report states source file IDs: {', '.join(str(i) for i in self._sourceFiles)}.")
						raise ex

					key = (scope, statementID._fileID, statementID._lineNumber, statementID._inlineCount)
					if isExcluded or coverBin._isExcluded:
						statementCounts.setdefault(key, None)
					else:
						previous = statementCounts.get(key)
						statementCounts[key] = coverBin._contents._coverageCount + (0 if previous is None else previous)

					lines.add((statementID._fileID, statementID._lineNumber))

			for branchCoverage in instance._branchCoverages:
				for branchStatement in branchCoverage.IterateStatements():
					statementID = branchStatement._id
					if statementID._fileID not in self._sourceFiles:
						ex = CodeCoverageError(f"UCIS statement identifier names source file ID '{statementID._fileID}'.")
						ex.add_note(f"The report states source file IDs: {', '.join(str(i) for i in self._sourceFiles)}.")
						raise ex
					elif branchStatement._isExcluded:
						continue

					lines.add((statementID._fileID, statementID._lineNumber))
					key = (scope, statementID._fileID, statementID._lineNumber, statementID._inlineCount)
					counts = branchCounts.setdefault(key, [])
					targets = branchTargets.setdefault(key, [])
					for index, branch in enumerate(branchStatement._branches):
						count = None if branch._bin._isExcluded else branch._bin._contents._coverageCount
						if index < len(counts):
							counts[index] = count if counts[index] is None else counts[index] + (0 if count is None else count)
						else:
							counts.append(count)
							targets.append(branch._id._lineNumber if branch._id._fileID == statementID._fileID else 0)

		lineCounts: dict[tuple[int, int], list[Nullable[int]]] = {}
		for (_, fileID, lineNumber, _), count in statementCounts.items():
			lineCounts.setdefault((fileID, lineNumber), []).append(count)

		lineBranches: dict[tuple[int, int], list[tuple[int, int]]] = {}
		for key, counts in branchCounts.items():
			branches = lineBranches.setdefault((key[1], key[2]), [])
			branches.extend(
				(count, target) for count, target in zip(counts, branchTargets[key]) if count is not None
			)
			if (key[1], key[2]) not in lineCounts:
				lineCounts[(key[1], key[2])] = [sum(count for count in counts if count is not None)]

		sourceDirectories = {
			historyNode._runDirectory: None
			for historyNode in self._historyNodes.values() if historyNode._runDirectory is not None
		}
		summary = CoverageSummary(self._path.stem, sourceDirectories=sourceDirectories)
		files = {
			fileID: summary.GetOrAddFile(self._sourceFiles[fileID]._path) for fileID in sorted({key[0] for key in lineCounts})
		}
		for (fileID, lineNumber) in sorted(lineCounts):
			counts = [count for count in lineCounts[(fileID, lineNumber)] if count is not None]
			if len(counts) == 0:
				cc_Line(lineNumber, LineCoverageStatus.Excluded, parent=files[fileID])
				continue

			count = min(counts)
			branches = lineBranches.get((fileID, lineNumber), [])
			if count == 0:
				status = LineCoverageStatus.Uncovered
			elif any(branchCount == 0 for branchCount, _ in branches):
				status = LineCoverageStatus.PartiallyCovered
			else:
				status = LineCoverageStatus.Covered

			cc_Line(lineNumber, status, count, parent=files[fileID])

		for (fileID, lineNumber), branches in lineBranches.items():
			file = files[fileID]
			line = file.GetLine(lineNumber)
			for count, target in branches:
				status = LineCoverageStatus.Covered if count > 0 else LineCoverageStatus.Uncovered
				targetLine = file.GetLine(target) if 0 < target <= file._lastLineNumber else None
				cc_Branch(status, count, targetLine, parent=line)

		for moduleName, lines in moduleLines.items():
			if len(fileIDs := {fileID for fileID, _ in lines}) == 1:
				file = files[fileIDs.pop()]
				lineNumbers = [lineNumber for _, lineNumber in lines]
				cc_Module(
					moduleName,
					file=file,
					startLine=file.GetLine(min(lineNumbers)),
					endLine=file.GetLine(max(lineNumbers)),
					parent=summary
				)

		summary.Aggregate()
		return summary
