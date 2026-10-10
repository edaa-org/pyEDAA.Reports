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
QuestaSim's coverage report XML: a model of the format, read from a report and converted to the common model.

Questa SIM keeps coverage in a coverage database (UCDB), whose format is proprietary. The command
``vcover report -xml -details`` - or ``coverage report -xml -details`` in a simulation - writes a report of it as XML,
with the coverage items of each instance:

.. code-block:: bash

   vcover report -xml -details -output CoverageReport.xml Testsuite.ucdb

The XML's root is ``<coverage_report>``, without namespace and without format version; it isn't the XML interchange
format of the UCIS standard. Questa states its version - e.g. ``2026.2`` - and the command, which wrote the report. A
report is validated against :file:`QuestaSim-Coverage.xsd` (:data:`SCHEMA`).

The format's model keeps what the report states: a :class:`Document` holds the report's mode
(:class:`~pyEDAA.Reports.CodeCoverage.QuestaSim.Elements.ReportMode`) and its scopes - instances, design units or source
files (:class:`~pyEDAA.Reports.CodeCoverage.QuestaSim.Scopes.Scope`) -, each with its coverage statistics
(:class:`~pyEDAA.Reports.CodeCoverage.QuestaSim.Elements.Statistics`), its source files and its coverage items: the
statements, the ``if`` and ``case`` statements with their branches
(:mod:`~pyEDAA.Reports.CodeCoverage.QuestaSim.Details`), and the states and transitions of finite state machines
(:mod:`~pyEDAA.Reports.CodeCoverage.QuestaSim.StateMachines`). Each element's constructor takes typed values, so the
model can be built by hand: an element below the report names its parent with the keyword parameter ``parent`` and is
added to it. Its class method ``Parse`` reads the element's XML element.

:meth:`Document.ToCoverageSummary` converts the statements and branches to the common model of
:mod:`pyEDAA.Reports.CodeCoverage`:

* Coverage items are identified by their file, their line and their index in the line. The items of all scopes are
  merged: an item of a design unit with several instances counts as often as in all instances together.
* A line ran as often as its least often run statement or branching statement. An ``if`` or ``case`` statement adds
  its branches to the line of its first branch - the ``if``, or the first case item -, each taken as often as Questa
  counted.
* A line, which ran, is covered, if all its branches were taken, otherwise partially covered.

The coverage statistics, the states and transitions of finite state machines, conditions, expressions and toggles
aren't converted.

.. rubric:: Example

.. code-block:: Python

   from pathlib import Path
   from pyEDAA.Reports.CodeCoverage.QuestaSim import Document

   report = Document(Path("CoverageReport.xml"), analyzeAndConvert=True)
   summary = report.ToCoverageSummary()
   print(f"Lines:    {summary.CoveredLines} of {summary.TotalLines}")
   print(f"Branches: {summary.CoveredBranches} of {summary.TotalBranches}")
"""
from __future__                                     import annotations

from pathlib                                        import Path
from typing                                         import Generator, Optional as Nullable

from lxml.etree                                     import XMLParser, XMLSchema, XMLSchemaParseError, XMLSyntaxError
from lxml.etree                                     import _Element, _ElementTree, parse
from pyTooling.Common                               import getResourceFile
from pyTooling.Decorators                           import export, readonly
from pyTooling.Exceptions                           import ToolingException
from pyTooling.MetaClasses                          import ExtendedType
from pyTooling.Stopwatch                            import Stopwatch

from pyEDAA.Reports                                 import Resources
from pyEDAA.Reports.CodeCoverage                    import CodeCoverageError, CoverageSummary, Document as cc_Document
from pyEDAA.Reports.CodeCoverage                    import Branch as cc_Branch, Line as cc_Line, LineCoverageStatus
from pyEDAA.Reports.CodeCoverage.QuestaSim.Elements import ReportMode, Totals
from pyEDAA.Reports.CodeCoverage.QuestaSim.Scopes   import DesignUnitData, FileData, InstanceData, Scope, Statement


__all__ = ["SCHEMA"]

SCHEMA = "QuestaSim-Coverage.xsd"  #: The XML schema a report is validated against.

# A class with a property named like a class - ``Totals`` - can't name that class in the annotation of a field: the
# class body's namespace, where annotations are evaluated, binds the name to the property.
_Totals = Totals


@export
class Report(metaclass=ExtendedType, mixin=True):
	"""
	The root element ``<coverage_report>`` and its ``<code_coverage_report>``: the Questa version and the command, which
	wrote it, its mode, the summary records and the scopes.

	The root of the format's model: a summary record or a scope names it as its parent.
	"""

	_toolVersion:    Nullable[str]               #: Version of Questa, which wrote the report.
	_command:        Nullable[str]               #: The command, which wrote the report.
	_mode:           Nullable[ReportMode]        #: How the report groups its coverage data.
	_hasLineDetails: bool                        #: Whether the report has details: source files and coverage items.
	_totals:         dict[ReportMode, _Totals]   #: The summary records, by what they sum up.
	_scopes:         list[Scope]                 #: The scopes.

	def __init__(self) -> None:
		"""
		Initialize an empty report.
		"""
		self._toolVersion =    None
		self._command =        None
		self._mode =           None
		self._hasLineDetails = False
		self._totals =         {}
		self._scopes =         []

	@readonly
	def ToolVersion(self) -> Nullable[str]:
		"""
		Read-only property to access the version of Questa, which wrote the report (:attr:`_toolVersion`).

		Questa states its version since a release between 10.x and 2023.3, e.g. ``2026.2``.

		:returns: The version, as the report states it; ``None`` if the report doesn't state it, or before it was converted.
		"""
		return self._toolVersion

	@readonly
	def Command(self) -> Nullable[str]:
		"""
		Read-only property to access the command, which wrote the report (:attr:`_command`).

		:returns: The command, as the report states it; ``None`` if the report doesn't state it, or before it was converted.
		"""
		return self._command

	@readonly
	def Mode(self) -> Nullable[ReportMode]:
		"""
		Read-only property to access how the report groups its coverage data (:attr:`_mode`).

		:returns: The mode; ``None`` before the report was converted.
		"""
		return self._mode

	@readonly
	def HasLineDetails(self) -> bool:
		"""
		Read-only property to access whether the report has details (:attr:`_hasLineDetails`).

		A report written with ``-details`` names the source files of its scopes and lists their coverage items; it states
		``lines="1"``.

		:returns: ``True``, if the report states details.
		"""
		return self._hasLineDetails

	@readonly
	def Totals(self) -> dict[ReportMode, _Totals]:
		"""
		Read-only property to access the summary records (:attr:`_totals`).

		:returns: The summary records, by what they sum up; none, if the report has no summary records.
		"""
		return self._totals

	@readonly
	def Scopes(self) -> list[Scope]:
		"""
		Read-only property to access the scopes (:attr:`_scopes`).

		:returns: The scopes, in the order the report lists them.
		"""
		return self._scopes

	def IterateStatements(self) -> Generator[Statement, None, None]:
		"""
		Iterate the statements of all scopes.

		:returns: A generator of the statements, scope by scope, in the order the report lists them.
		"""
		for scope in self._scopes:
			yield from scope._statements


@export
class Document(cc_Document, Report):
	"""
	A QuestaSim coverage report XML file: read into the format's model, and converted to the common model.
	"""

	_xmlDocument: Nullable[_ElementTree]  #: The parsed and validated XML document, after :meth:`Analyze`.

	def __init__(self, xmlReportFile: Path, analyzeAndConvert: bool = False) -> None:
		"""
		Initialize the report, and optionally read it.

		:param xmlReportFile:     Path to the coverage report XML file.
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
		:raises CodeCoverageError: If the root element isn't ``<coverage_report>``.
		:raises CodeCoverageError: If the report is a functional coverage report. |br|
		                           Write the report without '-cvg', '-directive' and '-assert'.
		:raises CodeCoverageError: If the XML schema can't be located or parsed.
		:raises CodeCoverageError: If the file isn't valid according to the XML schema.
		"""
		if not self._path.exists():
			raise CodeCoverageError(f"QuestaSim coverage report '{self._path}' does not exist.") \
				from FileNotFoundError(f"File '{self._path}' not found.")

		with Stopwatch() as sw:
			try:
				with self._path.open("rb") as file:
					xmlDocument = parse(file, XMLParser(ns_clean=True))
			except OSError as ex:
				raise CodeCoverageError(f"Couldn't read QuestaSim coverage report '{self._path}'.") from ex
			except XMLSyntaxError as ex:
				raise CodeCoverageError(f"XML syntax error in QuestaSim coverage report '{self._path}'.") from ex

			rootElement: _Element = xmlDocument.getroot()
			if rootElement.tag != "coverage_report":
				ex = CodeCoverageError(f"Root element of '{self._path}' is not '<coverage_report>'.")
				ex.add_note(f"Got root element '<{rootElement.tag}>'.")
				raise ex
			elif rootElement.find("functional_coverage_report") is not None:
				ex = CodeCoverageError(f"'{self._path}' is a functional coverage report, not a code coverage report.")
				ex.add_note(f"Write the report without '-cvg', '-directive' and '-assert'.")
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
		:raises CodeCoverageError: If the report doesn't state exactly one mode.
		:raises CodeCoverageError: If a coverage statistics element states more hit items than items.
		:raises CodeCoverageError: If a scope or summary record states a kind of coverage statistics twice.
		:raises CodeCoverageError: If a statement names an unknown file number, or none in a scope of several files.
		"""
		if self._xmlDocument is None:
			ex = CodeCoverageError(
				f"QuestaSim coverage report '{self._path}' needs to be read and analyzed by an XML parser."
			)
			ex.add_note(f"Call 'Document.Analyze()' or create the document using 'Document(path, analyzeAndConvert=True)'.")
			raise ex

		with Stopwatch() as sw:
			root: _Element = self._xmlDocument.getroot()
			codeCoverage: _Element = root.find("code_coverage_report")

			modes = [mode for mode in ReportMode if codeCoverage.attrib.get(mode.value) == "1"]
			if len(modes) != 1:
				ex = CodeCoverageError(f"QuestaSim coverage report '{self._path}' doesn't state exactly one mode.")
				ex.add_note(f"Got modes: {', '.join(mode.value for mode in modes) or 'none'}.")
				ex.add_note(f"One of the attributes {', '.join(mode.value for mode in ReportMode)} is '1'.")
				raise ex

			self._toolVersion =    root.attrib.get("questa_version")
			self._command =        root.attrib.get("command")
			self._mode =           modes[0]
			self._hasLineDetails = codeCoverage.attrib.get("lines") == "1"

			for element in codeCoverage:
				if element.tag in ("summaryByFile", "summaryByInstance"):
					Totals.Parse(element, parent=self)
				elif element.tag == "instanceData":
					InstanceData.Parse(element, parent=self)
				elif element.tag == "DuData":
					DesignUnitData.Parse(element, parent=self)
				else:
					FileData.Parse(element, parent=self)

		self._conversionDuration = sw.Duration

	def ToCoverageSummary(self) -> CoverageSummary:
		"""
		Convert the statements and branches of the format's model to the common model, and aggregate it.

		The statements of all scopes are merged by file, line and index, the ``if`` and ``case`` statements by the file,
		line and index of their first branch; merged items count as often as their items together. Each branch of an ``if``
		or ``case`` statement becomes a branch of the line of its first branch, taken as often as the branch's true count
		or hits. A line ran as often as its least often run statement or branching statement - the sum of its branches'
		counts. A line, which ran, is covered, if all its branches were taken, otherwise partially covered.

		:returns:                  The report's root of the common model, named after the report file.
		:raises CodeCoverageError: If the report has no statements: it was written without details. |br|
		                           Write the report with details: 'vcover report -xml -details ...'.
		:raises CodeCoverageError: If two scopes state the same ``if`` or ``case`` statement with different numbers of
		                           branches.
		:raises CodeCoverageError: If a file's path runs through another file.
		"""
		hitsPerStatement: dict[tuple[Path, int, int], int] = {}
		branchesPerDecision: dict[tuple[Path, int, int, str], list[int]] = {}
		for scope in self._scopes:
			for statement in scope._statements:
				key = (statement._file, statement._lineNumber, statement._index)
				hitsPerStatement[key] = hitsPerStatement.get(key, 0) + statement._hits

			decisions = [
				("if", [branch._trueCount for branch in ifStatement._branches], ifStatement._branches[0])
				for ifStatement in scope._ifStatements
			] + [
				("case", [branch._hits for branch in caseStatement._branches], caseStatement._branches[0])
				for caseStatement in scope._caseStatements
			]
			for kind, counts, first in decisions:
				key = (first._file, first._lineNumber, first._index, kind)
				if (merged := branchesPerDecision.get(key)) is None:
					branchesPerDecision[key] = counts
				elif len(merged) != len(counts):
					ex = CodeCoverageError(
						f"The '{kind}' statement at '{first._file.as_posix()}:{first._lineNumber}' has {len(counts)} branches in "
						f"one scope, but {len(merged)} in another."
					)
					ex.add_note(f"The scopes merge their branches by position.")
					raise ex
				else:
					branchesPerDecision[key] = [total + count for total, count in zip(merged, counts)]

		if len(hitsPerStatement) == 0:
			ex = CodeCoverageError(f"QuestaSim coverage report '{self._path}' has no statements to convert.")
			ex.add_note(f"Write the report with details: 'vcover report -xml -details ...'.")
			raise ex

		countsPerLine:   dict[Path, dict[int, list[int]]] = {}
		branchesPerLine: dict[Path, dict[int, list[int]]] = {}
		for (file, lineNumber, _), hits in hitsPerStatement.items():
			countsPerLine.setdefault(file, {}).setdefault(lineNumber, []).append(hits)

		for (file, lineNumber, _, _), counts in branchesPerDecision.items():
			countsPerLine.setdefault(file, {}).setdefault(lineNumber, []).append(sum(counts))
			branchesPerLine.setdefault(file, {}).setdefault(lineNumber, []).extend(counts)

		summary = CoverageSummary(self._path.stem)
		for path, counts in countsPerLine.items():
			file = summary.GetOrAddFile(path)
			branches = branchesPerLine.get(path, {})
			for lineNumber in sorted(counts):
				count = min(counts[lineNumber])
				branchCounts = branches.get(lineNumber, [])
				if count == 0:
					status = LineCoverageStatus.Uncovered
				elif any(branchCount == 0 for branchCount in branchCounts):
					status = LineCoverageStatus.PartiallyCovered
				else:
					status = LineCoverageStatus.Covered

				line = cc_Line(lineNumber, status, count, parent=file)
				for branchCount in branchCounts:
					branchStatus = LineCoverageStatus.Covered if branchCount > 0 else LineCoverageStatus.Uncovered
					cc_Branch(branchStatus, branchCount, parent=line)

		summary.Aggregate()
		return summary
