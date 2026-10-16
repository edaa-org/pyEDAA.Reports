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

The format's model keeps what the report states: a :class:`Document` holds the report's mode (:class:`ReportMode`) and
its scopes - instances, design units or source files (:class:`Scope`) -, each with its coverage statistics
(:class:`Statistics`), its source files and its coverage items: the statements, the ``if`` and ``case`` statements with
their branches, and the states and transitions of finite state machines. Each element's constructor takes typed values,
so the model can be built by hand: an element below the report names its parent with the keyword parameter ``parent``
and is added to it. Its class method ``Parse`` reads the element's XML element.

* A coverage statistics element states how many coverage items of a kind - e.g. statements or branches - a scope or a
  summary record (:class:`Totals`) has, and how many of them were hit.
* Which kind of scope a report lists, its mode decides: :class:`InstanceData`, :class:`DesignUnitData` or
  :class:`FileData`. With details (``vcover report -details``), a scope names its source files in a source table and
  lists its coverage items.
* ``-code`` chooses the kinds of coverage items, e.g. ``-code bcesf`` for branches, conditions, expressions, statements
  and finite state machines. A coverage item - :class:`Statement`, :class:`IfBranch`, :class:`CaseBranch` - names its
  source file by the number the scope's source table gives it, its line, and its index among the items of its kind in
  that line.
* Unlike the other coverage items, a state (:class:`FSMState`) and a transition (:class:`FSMTransition`) of a finite
  state machine name no file number: their file is the scope's, if the scope has a single file.

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
from __future__                  import annotations

from io                          import BytesIO
from pathlib                     import Path
from typing                      import Generator, Mapping, Optional as Nullable, Self

from lxml.etree                  import XMLParser, XMLSchema, XMLSchemaParseError, XMLSyntaxError
from lxml.etree                  import _Element, _ElementTree, parse
from pyTooling.Common            import getFullyQualifiedName, getResourceFile, StringEnum
from pyTooling.Decorators        import export, readonly
from pyTooling.Exceptions        import ToolingException
from pyTooling.MetaClasses       import ExtendedType
from pyTooling.Stopwatch         import Stopwatch

from pyEDAA.Reports              import Resources
from pyEDAA.Reports.CodeCoverage import CodeCoverageError, CoverageSummary, Document as cc_Document
from pyEDAA.Reports.CodeCoverage import Branch as cc_Branch, Line as cc_Line, LineCoverageStatus


__all__ = ["SCHEMA"]

SCHEMA = "QuestaSim-Coverage.xsd"  #: The XML schema a report is validated against.

# A class with a property named like a class - ``Path``, ``Totals`` - can't name that class in the annotation of a
# field: the class body's namespace, where annotations are evaluated, binds the name to the property.
_Path = Path


@export
class ReportMode(StringEnum):
	"""
	How a report groups its coverage data, as the attribute of ``<code_coverage_report>`` set to ``1`` states.
	"""

	ByInstance =   "byInstance"  #: Per instance (``<instanceData>``), ``vcover report -setdefault byinstance``.
	ByDesignUnit = "byDU"        #: Per design unit (``<DuData>``), ``vcover report -setdefault bydu``.
	ByFile =       "byFile"      #: Per source file (``<fileData>``), ``vcover report -setdefault byfile``.


@export
class CoverageKind(StringEnum):
	"""
	Kind of coverage items a coverage statistics element counts, as its element name states.
	"""

	Statements =  "statements"     #: Statements.
	Branches =    "branches"       #: Branches of ``if`` and ``case`` statements.
	Conditions =  "conditions"     #: Conditions.
	Expressions = "expressions"    #: Expressions.
	States =      "states"         #: States of finite state machines.
	Transitions = "transitions"    #: Transitions of finite state machines.
	Toggles =     "toggleSummary"  #: Signal toggles.


@export
class Statistics(metaclass=ExtendedType, slots=True):
	"""
	A coverage statistics element of a scope or a summary record: how many coverage items of a kind it has, and how many
	of them were hit.

	The element is named after the kind of coverage items, e.g. ``<statements>`` or ``<branches>``.
	"""

	_parent:  Nullable[StatisticsMixin]  #: The scope or summary record the coverage statistics belong to.
	_kind:    CoverageKind               #: Kind of the coverage items.
	_active:  int                        #: Number of coverage items.
	_hits:    int                        #: Number of coverage items, which were hit.
	_percent: float                      #: Percentage of coverage items, which were hit, as the report states it.

	def __init__(
		self,
		kind: CoverageKind,
		active: int,
		hits: int,
		percent: float,
		*,
		parent: Nullable[StatisticsMixin] = None
	) -> None:
		"""
		Initialize the coverage statistics, and add them to the coverage statistics of their element.

		:param kind:               Kind of the coverage items.
		:param active:             Number of coverage items.
		:param hits:               Number of coverage items, which were hit.
		:param percent:            Percentage of coverage items, which were hit, as the report states it.
		:param parent:             Optional, the scope or summary record the coverage statistics belong to; they are added
		                           to its coverage statistics by :attr:`Kind`. Default: ``None``.
		:raises ValueError:        If parameter ``kind`` is ``None``.
		:raises TypeError:         If parameter ``kind`` isn't of type :class:`CoverageKind`.
		:raises ValueError:        If parameter ``active`` is ``None``.
		:raises TypeError:         If parameter ``active`` isn't of type :class:`int`.
		:raises ValueError:        If parameter ``active`` is negative.
		:raises ValueError:        If parameter ``hits`` is ``None``.
		:raises TypeError:         If parameter ``hits`` isn't of type :class:`int`.
		:raises ValueError:        If parameter ``hits`` is negative or greater than parameter ``active``.
		:raises ValueError:        If parameter ``percent`` is ``None``.
		:raises TypeError:         If parameter ``percent`` isn't of type :class:`float` or :class:`int`.
		:raises ValueError:        If parameter ``percent`` is out of range 0..100.
		:raises TypeError:         If parameter ``parent`` isn't of type :class:`StatisticsMixin`.
		:raises CodeCoverageError: If the parent already has coverage statistics of this kind.
		"""
		if kind is None:
			raise ValueError(f"Parameter 'kind' is None.")
		elif not isinstance(kind, CoverageKind):
			ex = TypeError(f"Parameter 'kind' is not of type 'CoverageKind'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(kind)}'.")
			raise ex

		if active is None:
			raise ValueError(f"Parameter 'active' is None.")
		elif not isinstance(active, int):
			ex = TypeError(f"Parameter 'active' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(active)}'.")
			raise ex
		elif active < 0:
			ex = ValueError(f"Parameter 'active' is negative.")
			ex.add_note(f"Got value '{active}'.")
			raise ex

		if hits is None:
			raise ValueError(f"Parameter 'hits' is None.")
		elif not isinstance(hits, int):
			ex = TypeError(f"Parameter 'hits' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(hits)}'.")
			raise ex
		elif not (0 <= hits <= active):
			ex = ValueError(f"Parameter 'hits' is out of range 0..{active}.")
			ex.add_note(f"Got value '{hits}'.")
			raise ex

		if percent is None:
			raise ValueError(f"Parameter 'percent' is None.")
		elif not isinstance(percent, (float, int)):
			ex = TypeError(f"Parameter 'percent' is not of type 'float' or 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(percent)}'.")
			raise ex
		elif not (0.0 <= percent <= 100.0):
			ex = ValueError(f"Parameter 'percent' is out of range 0..100.")
			ex.add_note(f"Got value '{percent}'.")
			raise ex

		if parent is not None:
			if not isinstance(parent, StatisticsMixin):
				ex = TypeError(f"Parameter 'parent' is not of type 'StatisticsMixin'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
				raise ex
			elif kind in parent._statistics:
				raise CodeCoverageError(f"Coverage statistics '{kind}' are stated twice.")

		self._parent =  parent
		self._kind =    kind
		self._active =  active
		self._hits =    hits
		self._percent = float(percent)

		if parent is not None:
			parent._statistics[kind] = self

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[StatisticsMixin] = None) -> Self:
		"""
		Parse coverage statistics from their element.

		:param element:            The coverage statistics element.
		:param parent:             Optional, the scope or summary record the coverage statistics belong to. Default:
		                           ``None``.
		:returns:                  The coverage statistics.
		:raises CodeCoverageError: If the element states more hit items than items.
		:raises CodeCoverageError: If the parent already has coverage statistics of this kind.
		"""
		active = int(element.attrib["active"])
		hits =   int(element.attrib["hits"])
		if hits > active:
			ex = CodeCoverageError(f"Coverage statistics '<{element.tag}>' state more hit items than items.")
			ex.add_note(f"Got '{hits}' hit items of '{active}' items in line {element.sourceline}.")
			raise ex

		return cls(CoverageKind(element.tag), active, hits, float(element.attrib["percent"]), parent=parent)

	@readonly
	def Parent(self) -> Nullable[StatisticsMixin]:
		"""
		Read-only property to access the scope or summary record the coverage statistics belong to (:attr:`_parent`).

		:returns: The scope or summary record; ``None`` if the coverage statistics belong to none.
		"""
		return self._parent

	@readonly
	def Kind(self) -> CoverageKind:
		"""
		Read-only property to access the kind of the coverage items (:attr:`_kind`).

		:returns: The kind of the coverage items.
		"""
		return self._kind

	@readonly
	def Active(self) -> int:
		"""
		Read-only property to access the number of coverage items (:attr:`_active`).

		:returns: The number of coverage items.
		"""
		return self._active

	@readonly
	def Hits(self) -> int:
		"""
		Read-only property to access the number of coverage items, which were hit (:attr:`_hits`).

		:returns: The number of hit coverage items.
		"""
		return self._hits

	@readonly
	def Percent(self) -> float:
		"""
		Read-only property to access the percentage of coverage items, which were hit, as the report states it
		(:attr:`_percent`).

		Questa truncates the percentage to two decimals: 66 of 74 items are ``89.18`` percent.

		:returns: The percentage, from 0 to 100.
		"""
		return self._percent


@export
class StatisticsMixin(metaclass=ExtendedType, mixin=True):
	"""
	A mixin-class adding the coverage statistics an element states: per kind of coverage items, how many it has and how
	many were hit.
	"""

	_statistics: dict[CoverageKind, Statistics]  #: The coverage statistics, by kind.

	def __init__(self) -> None:
		"""
		Initialize the coverage statistics to none.

		Coverage statistics are added by creating them with the element as their parent.
		"""
		self._statistics = {}

	def _ParseStatistics(self, element: _Element) -> None:
		"""
		Parse the coverage statistics elements below an element, with this element as their parent.

		:param element:            The element holding the coverage statistics elements.
		:raises CodeCoverageError: If a coverage statistics element states more hit items than items.
		:raises CodeCoverageError: If the element states a kind of coverage statistics twice.
		"""
		kinds = [kind.value for kind in CoverageKind]
		for child in element:
			if child.tag in kinds:
				Statistics.Parse(child, parent=self)

	@readonly
	def Statistics(self) -> dict[CoverageKind, Statistics]:
		"""
		Read-only property to access the coverage statistics (:attr:`_statistics`).

		:returns: The coverage statistics, by kind; a kind the element doesn't state has none.
		"""
		return self._statistics


@export
class SourceItem(metaclass=ExtendedType, slots=True):
	"""
	Base-class of the coverage items, which name where they are in the sources: a file, a line and an index in the line.
	"""

	_file:       Path  #: Path of the source file, as the report states it.
	_lineNumber: int   #: Line number, counted from 1.
	_index:      int   #: Index of the item among the items of its kind in its line, counted from 1.

	def __init__(self, file: Path, lineNumber: int, index: int) -> None:
		"""
		Initialize where the coverage item is in the sources.

		:param file:        Path of the source file, as the report states it.
		:param lineNumber:  Line number, counted from 1.
		:param index:       Index of the item among the items of its kind in its line, counted from 1.
		:raises ValueError: If parameter ``file`` is ``None``.
		:raises TypeError:  If parameter ``file`` isn't of type :class:`~pathlib.Path`.
		:raises ValueError: If parameter ``lineNumber`` is ``None``.
		:raises TypeError:  If parameter ``lineNumber`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``lineNumber`` is less than 1.
		:raises ValueError: If parameter ``index`` is ``None``.
		:raises TypeError:  If parameter ``index`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``index`` is less than 1.
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
		elif index < 1:
			ex = ValueError(f"Parameter 'index' is less than 1.")
			ex.add_note(f"Got value '{index}'.")
			raise ex

		self._file =       file
		self._lineNumber = lineNumber
		self._index =      index

	@readonly
	def File(self) -> Path:
		"""
		Read-only property to access the path of the source file (:attr:`_file`).

		:returns: The path, as the report states it.
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
		Read-only property to access the index of the item among the items of its kind in its line (:attr:`_index`).

		:returns: The index, counted from 1.
		"""
		return self._index


@export
class Statement(SourceItem):
	"""
	A ``<stmt>`` of a scope: a statement, where it is in the sources, and how often it ran.
	"""

	_parent: Nullable[Scope]  #: The scope the statement belongs to.
	_hits:   int              #: How often the statement ran.

	def __init__(self, file: Path, lineNumber: int, index: int, hits: int, *, parent: Nullable[Scope] = None) -> None:
		"""
		Initialize the statement, and append it to the statements of its scope.

		:param file:        Path of the source file, as the report states it.
		:param lineNumber:  Line number, counted from 1.
		:param index:       Index of the statement in its line, counted from 1.
		:param hits:        How often the statement ran.
		:param parent:      Optional, the scope the statement belongs to; the statement is appended to its statements.
		                    Default: ``None``.
		:raises ValueError: If parameter ``file`` is ``None``.
		:raises TypeError:  If parameter ``file`` isn't of type :class:`~pathlib.Path`.
		:raises ValueError: If parameter ``lineNumber`` is ``None``.
		:raises TypeError:  If parameter ``lineNumber`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``lineNumber`` is less than 1.
		:raises ValueError: If parameter ``index`` is ``None``.
		:raises TypeError:  If parameter ``index`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``index`` is less than 1.
		:raises ValueError: If parameter ``hits`` is ``None``.
		:raises TypeError:  If parameter ``hits`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``hits`` is negative.
		:raises TypeError:  If parameter ``parent`` isn't of type
		                    :class:`Scope`.
		"""
		super().__init__(file, lineNumber, index)

		if hits is None:
			raise ValueError(f"Parameter 'hits' is None.")
		elif not isinstance(hits, int):
			ex = TypeError(f"Parameter 'hits' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(hits)}'.")
			raise ex
		elif hits < 0:
			ex = ValueError(f"Parameter 'hits' is negative.")
			ex.add_note(f"Got value '{hits}'.")
			raise ex

		if parent is not None and not isinstance(parent, Scope):
			ex = TypeError(f"Parameter 'parent' is not of type 'Scope'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent = parent
		self._hits =   hits

		if parent is not None:
			parent._statements.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Scope) -> Self:
		"""
		Parse a statement from its ``<stmt>`` element; its file is the one its file number names in the scope's source
		table.

		:param element:            The ``<stmt>`` element.
		:param parent:             The scope the statement belongs to.
		:returns:                  The statement.
		:raises CodeCoverageError: If the statement's file number isn't in the scope's source table.
		:raises CodeCoverageError: If the statement states no file number and its scope has no single file.
		"""
		return cls(
			parent._ResolveFile(element),
			int(element.attrib["ln"]),
			int(element.attrib["st"]),
			int(element.attrib["hits"]),
			parent=parent
		)

	@readonly
	def Parent(self) -> Nullable[Scope]:
		"""
		Read-only property to access the scope the statement belongs to (:attr:`_parent`).

		:returns: The scope; ``None`` if the statement belongs to no scope.
		"""
		return self._parent

	@readonly
	def Hits(self) -> int:
		"""
		Read-only property to access how often the statement ran (:attr:`_hits`).

		:returns: The count.
		"""
		return self._hits


@export
class IfBranch(SourceItem):
	"""
	An ``<ielem>`` of an ``if`` statement: a branch - ``if``, ``elsif``, ``else`` or the implicit *AllFalse* branch -, how
	often it was taken, and how often its condition was false.
	"""

	_parent:     Nullable[IfStatement]  #: The ``if`` statement the branch belongs to.
	_trueCount:  int                    #: How often the branch was taken.
	_falseCount: int                    #: How often the branch's condition was false: the evaluation went on.

	def __init__(
		self,
		file: Path,
		lineNumber: int,
		index: int,
		trueCount: int,
		falseCount: int,
		*,
		parent: Nullable[IfStatement] = None
	) -> None:
		"""
		Initialize the branch, and append it to the branches of its ``if`` statement.

		:param file:        Path of the source file, as the report states it.
		:param lineNumber:  Line number of the branch's condition, counted from 1.
		:param index:       Index of the ``if`` statement in its line, counted from 1.
		:param trueCount:   How often the branch was taken.
		:param falseCount:  How often the branch's condition was false; ``0`` for an ``else`` or *AllFalse* branch.
		:param parent:      Optional, the ``if`` statement the branch belongs to. Default: ``None``.
		:raises ValueError: If parameter ``file`` is ``None``.
		:raises TypeError:  If parameter ``file`` isn't of type :class:`~pathlib.Path`.
		:raises ValueError: If parameter ``lineNumber`` is ``None``.
		:raises TypeError:  If parameter ``lineNumber`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``lineNumber`` is less than 1.
		:raises ValueError: If parameter ``index`` is ``None``.
		:raises TypeError:  If parameter ``index`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``index`` is less than 1.
		:raises ValueError: If parameter ``trueCount`` is ``None``.
		:raises TypeError:  If parameter ``trueCount`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``trueCount`` is negative.
		:raises ValueError: If parameter ``falseCount`` is ``None``.
		:raises TypeError:  If parameter ``falseCount`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``falseCount`` is negative.
		:raises TypeError:  If parameter ``parent`` isn't of type :class:`IfStatement`.
		"""
		super().__init__(file, lineNumber, index)

		if trueCount is None:
			raise ValueError(f"Parameter 'trueCount' is None.")
		elif not isinstance(trueCount, int):
			ex = TypeError(f"Parameter 'trueCount' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(trueCount)}'.")
			raise ex
		elif trueCount < 0:
			ex = ValueError(f"Parameter 'trueCount' is negative.")
			ex.add_note(f"Got value '{trueCount}'.")
			raise ex

		if falseCount is None:
			raise ValueError(f"Parameter 'falseCount' is None.")
		elif not isinstance(falseCount, int):
			ex = TypeError(f"Parameter 'falseCount' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(falseCount)}'.")
			raise ex
		elif falseCount < 0:
			ex = ValueError(f"Parameter 'falseCount' is negative.")
			ex.add_note(f"Got value '{falseCount}'.")
			raise ex

		if parent is not None and not isinstance(parent, IfStatement):
			ex = TypeError(f"Parameter 'parent' is not of type 'IfStatement'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =     parent
		self._trueCount =  trueCount
		self._falseCount = falseCount

		if parent is not None:
			parent._branches.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: IfStatement) -> Self:
		"""
		Parse a branch from its ``<ielem>`` element.

		:param element:            The ``<ielem>`` element.
		:param parent:             The ``if`` statement the branch belongs to; it belongs to a scope.
		:returns:                  The branch.
		:raises CodeCoverageError: If the branch's file number isn't in the scope's source table, or it states none and
		                           the scope has no single file.
		"""
		return cls(
			parent._parent._ResolveFile(element),
			int(element.attrib["ln"]),
			int(element.attrib["st"]),
			int(element.attrib["true"]),
			int(element.attrib["false"]),
			parent=parent
		)

	@readonly
	def Parent(self) -> Nullable[IfStatement]:
		"""
		Read-only property to access the ``if`` statement the branch belongs to (:attr:`_parent`).

		:returns: The ``if`` statement; ``None`` if the branch belongs to none.
		"""
		return self._parent

	@readonly
	def TrueCount(self) -> int:
		"""
		Read-only property to access how often the branch was taken (:attr:`_trueCount`).

		:returns: The count.
		"""
		return self._trueCount

	@readonly
	def FalseCount(self) -> int:
		"""
		Read-only property to access how often the branch's condition was false (:attr:`_falseCount`).

		Then the evaluation went on to the next branch: the count is the sum of the next branches' true counts.

		:returns: The count; ``0`` for an ``else`` or *AllFalse* branch.
		"""
		return self._falseCount


@export
class IfStatement(metaclass=ExtendedType, slots=True):
	"""
	An ``<if>`` of a scope: an ``if`` statement - with its ``elsif`` and ``else`` branches - and how often each branch was
	taken.

	Each branch is an ``<ielem>`` (:class:`IfBranch`). An ``if`` statement without ``else`` has an implicit branch, the
	*AllFalse* branch, taken whenever no condition was true; Questa lists it as the last ``<ielem>``, in the line of the
	``if``.
	"""

	_parent:   Nullable[Scope]  #: The scope the ``if`` statement belongs to.
	_hasElse:  bool             #: Whether the ``if`` statement has an ``else`` branch.
	_branches: list[IfBranch]   #: The branches, in the order of their conditions.

	def __init__(self, hasElse: bool, *, parent: Nullable[Scope] = None) -> None:
		"""
		Initialize the ``if`` statement, and append it to the ``if`` statements of its scope.

		Its branches are added by creating them with this ``if`` statement as their parent.

		:param hasElse:     Whether the ``if`` statement has an ``else`` branch; otherwise its last branch is the implicit
		                    *AllFalse* branch.
		:param parent:      Optional, the scope the ``if`` statement belongs to. Default: ``None``.
		:raises ValueError: If parameter ``hasElse`` is ``None``.
		:raises TypeError:  If parameter ``hasElse`` isn't of type :class:`bool`.
		:raises TypeError:  If parameter ``parent`` isn't of type
		                    :class:`Scope`.
		"""
		if hasElse is None:
			raise ValueError(f"Parameter 'hasElse' is None.")
		elif not isinstance(hasElse, bool):
			ex = TypeError(f"Parameter 'hasElse' is not of type 'bool'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(hasElse)}'.")
			raise ex

		if parent is not None and not isinstance(parent, Scope):
			ex = TypeError(f"Parameter 'parent' is not of type 'Scope'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =   parent
		self._hasElse =  hasElse
		self._branches = []

		if parent is not None:
			parent._ifStatements.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Scope) -> Self:
		"""
		Parse an ``if`` statement and its branches from its ``<if>`` element.

		:param element:            The ``<if>`` element.
		:param parent:             The scope the ``if`` statement belongs to.
		:returns:                  The ``if`` statement.
		:raises CodeCoverageError: If a branch's file number isn't in the scope's source table, or it states none and the
		                           scope has no single file.
		:raises CodeCoverageError: If the ``if`` statement states other numbers of branches and taken branches than its
		                           branches have.
		"""
		ifStatement = cls(element.attrib["hasElse"] == "1", parent=parent)
		for branchElement in element.iterfind("ielem"):
			IfBranch.Parse(branchElement, parent=ifStatement)

		active = int(element.attrib["active"])
		hits =   int(element.attrib["hits"])
		if active != len(ifStatement._branches) or hits != ifStatement.TakenBranches:
			ex = CodeCoverageError(f"'<if>' in line {element.sourceline} states other figures than its branches have.")
			ex.add_note(f"Got '{hits}' of '{active}' branches taken, its branches have {ifStatement.TakenBranches} of "
			            f"{len(ifStatement._branches)}.")
			raise ex

		return ifStatement

	@readonly
	def Parent(self) -> Nullable[Scope]:
		"""
		Read-only property to access the scope the ``if`` statement belongs to (:attr:`_parent`).

		:returns: The scope; ``None`` if the ``if`` statement belongs to no scope.
		"""
		return self._parent

	@readonly
	def HasElse(self) -> bool:
		"""
		Read-only property to access whether the ``if`` statement has an ``else`` branch (:attr:`_hasElse`).

		:returns: ``True``, if it has an ``else`` branch; otherwise its last branch is the implicit *AllFalse* branch.
		"""
		return self._hasElse

	@readonly
	def Branches(self) -> list[IfBranch]:
		"""
		Read-only property to access the branches (:attr:`_branches`).

		:returns: The branches, in the order of their conditions; the ``else`` or *AllFalse* branch last.
		"""
		return self._branches

	@readonly
	def TakenBranches(self) -> int:
		"""
		Read-only property to return the number of branches, which were taken.

		:returns: The number of branches with a positive :attr:`IfBranch.TrueCount`.
		"""
		return sum(1 for branch in self._branches if branch._trueCount > 0)

	@readonly
	def EvaluationCount(self) -> int:
		"""
		Read-only property to return how often the ``if`` statement was evaluated.

		Each evaluation takes exactly one branch, so it is the sum of the branches' :attr:`IfBranch.TrueCount`.

		:returns: The number of evaluations.
		"""
		return sum(branch._trueCount for branch in self._branches)


@export
class CaseBranch(SourceItem):
	"""
	A ``<celem>`` of a ``case`` statement: a case item, and how often it was taken.
	"""

	_parent: Nullable[CaseStatement]  #: The ``case`` statement the branch belongs to.
	_hits:   int                      #: How often the branch was taken.

	def __init__(
		self,
		file: Path,
		lineNumber: int,
		index: int,
		hits: int,
		*,
		parent: Nullable[CaseStatement] = None
	) -> None:
		"""
		Initialize the branch, and append it to the branches of its ``case`` statement.

		:param file:        Path of the source file, as the report states it.
		:param lineNumber:  Line number of the case item, counted from 1.
		:param index:       Index of the case item in its line, counted from 1.
		:param hits:        How often the branch was taken.
		:param parent:      Optional, the ``case`` statement the branch belongs to. Default: ``None``.
		:raises ValueError: If parameter ``file`` is ``None``.
		:raises TypeError:  If parameter ``file`` isn't of type :class:`~pathlib.Path`.
		:raises ValueError: If parameter ``lineNumber`` is ``None``.
		:raises TypeError:  If parameter ``lineNumber`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``lineNumber`` is less than 1.
		:raises ValueError: If parameter ``index`` is ``None``.
		:raises TypeError:  If parameter ``index`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``index`` is less than 1.
		:raises ValueError: If parameter ``hits`` is ``None``.
		:raises TypeError:  If parameter ``hits`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``hits`` is negative.
		:raises TypeError:  If parameter ``parent`` isn't of type :class:`CaseStatement`.
		"""
		super().__init__(file, lineNumber, index)

		if hits is None:
			raise ValueError(f"Parameter 'hits' is None.")
		elif not isinstance(hits, int):
			ex = TypeError(f"Parameter 'hits' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(hits)}'.")
			raise ex
		elif hits < 0:
			ex = ValueError(f"Parameter 'hits' is negative.")
			ex.add_note(f"Got value '{hits}'.")
			raise ex

		if parent is not None and not isinstance(parent, CaseStatement):
			ex = TypeError(f"Parameter 'parent' is not of type 'CaseStatement'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent = parent
		self._hits =   hits

		if parent is not None:
			parent._branches.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: CaseStatement) -> Self:
		"""
		Parse a branch from its ``<celem>`` element.

		:param element:            The ``<celem>`` element.
		:param parent:             The ``case`` statement the branch belongs to; it belongs to a scope.
		:returns:                  The branch.
		:raises CodeCoverageError: If the branch's file number isn't in the scope's source table, or it states none and
		                           the scope has no single file.
		"""
		return cls(
			parent._parent._ResolveFile(element),
			int(element.attrib["ln"]),
			int(element.attrib["st"]),
			int(element.attrib["hits"]),
			parent=parent
		)

	@readonly
	def Parent(self) -> Nullable[CaseStatement]:
		"""
		Read-only property to access the ``case`` statement the branch belongs to (:attr:`_parent`).

		:returns: The ``case`` statement; ``None`` if the branch belongs to none.
		"""
		return self._parent

	@readonly
	def Hits(self) -> int:
		"""
		Read-only property to access how often the branch was taken (:attr:`_hits`).

		:returns: The count.
		"""
		return self._hits


@export
class CaseStatement(metaclass=ExtendedType, slots=True):
	"""
	A ``<case>`` of a scope: a ``case`` statement, and how often each of its branches was taken.

	Each case item is a branch (``<celem>``, :class:`CaseBranch`); the ``case`` statement's line isn't stated.
	"""

	_parent:   Nullable[Scope]   #: The scope the ``case`` statement belongs to.
	_branches: list[CaseBranch]  #: The branches, in the order of the case items.

	def __init__(self, *, parent: Nullable[Scope] = None) -> None:
		"""
		Initialize the ``case`` statement, and append it to the ``case`` statements of its scope.

		Its branches are added by creating them with this ``case`` statement as their parent.

		:param parent:     Optional, the scope the ``case`` statement belongs to. Default: ``None``.
		:raises TypeError: If parameter ``parent`` isn't of type
		                   :class:`Scope`.
		"""
		if parent is not None and not isinstance(parent, Scope):
			ex = TypeError(f"Parameter 'parent' is not of type 'Scope'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =   parent
		self._branches = []

		if parent is not None:
			parent._caseStatements.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Scope) -> Self:
		"""
		Parse a ``case`` statement and its branches from its ``<case>`` element.

		:param element:            The ``<case>`` element.
		:param parent:             The scope the ``case`` statement belongs to.
		:returns:                  The ``case`` statement.
		:raises CodeCoverageError: If a branch's file number isn't in the scope's source table, or it states none and the
		                           scope has no single file.
		:raises CodeCoverageError: If the ``case`` statement states other numbers of branches and taken branches than its
		                           branches have.
		"""
		caseStatement = cls(parent=parent)
		for branchElement in element.iterfind("celem"):
			CaseBranch.Parse(branchElement, parent=caseStatement)

		active = int(element.attrib["active"])
		hits =   int(element.attrib["hits"])
		if active != len(caseStatement._branches) or hits != caseStatement.TakenBranches:
			ex = CodeCoverageError(f"'<case>' in line {element.sourceline} states other figures than its branches have.")
			ex.add_note(f"Got '{hits}' of '{active}' branches taken, its branches have {caseStatement.TakenBranches} of "
			            f"{len(caseStatement._branches)}.")
			raise ex

		return caseStatement

	@readonly
	def Parent(self) -> Nullable[Scope]:
		"""
		Read-only property to access the scope the ``case`` statement belongs to (:attr:`_parent`).

		:returns: The scope; ``None`` if the ``case`` statement belongs to no scope.
		"""
		return self._parent

	@readonly
	def Branches(self) -> list[CaseBranch]:
		"""
		Read-only property to access the branches (:attr:`_branches`).

		:returns: The branches, in the order of the case items.
		"""
		return self._branches

	@readonly
	def TakenBranches(self) -> int:
		"""
		Read-only property to return the number of branches, which were taken.

		:returns: The number of branches with a positive :attr:`CaseBranch.Hits`.
		"""
		return sum(1 for branch in self._branches if branch._hits > 0)

	@readonly
	def EvaluationCount(self) -> int:
		"""
		Read-only property to return how often the ``case`` statement was evaluated.

		Each evaluation takes exactly one branch, so it is the sum of the branches' :attr:`CaseBranch.Hits`.

		:returns: The number of evaluations.
		"""
		return sum(branch._hits for branch in self._branches)


@export
class FSMState(metaclass=ExtendedType, slots=True):
	"""
	A ``<state>`` of a scope: a state of a finite state machine, and how often it was entered.
	"""

	_parent:     Nullable[Scope]  #: The scope the state belongs to.
	_name:       str              #: Name of the state.
	_file:       Nullable[Path]   #: Path of the source file, if known.
	_lineNumber: int              #: Line number of the state, counted from 1.
	_hits:       int              #: How often the state was entered.

	def __init__(
		self,
		name: str,
		file: Nullable[Path],
		lineNumber: int,
		hits: int,
		*,
		parent: Nullable[Scope] = None
	) -> None:
		"""
		Initialize the state, and append it to the states of its scope.

		:param name:        Name of the state.
		:param file:        Path of the source file, as the report states it; ``None``, if unknown.
		:param lineNumber:  Line number of the state, counted from 1.
		:param hits:        How often the state was entered.
		:param parent:      Optional, the scope the state belongs to. Default: ``None``.
		:raises ValueError: If parameter ``name`` is ``None``.
		:raises TypeError:  If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError: If parameter ``name`` is empty.
		:raises TypeError:  If parameter ``file`` isn't of type :class:`~pathlib.Path`.
		:raises ValueError: If parameter ``lineNumber`` is ``None``.
		:raises TypeError:  If parameter ``lineNumber`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``lineNumber`` is less than 1.
		:raises ValueError: If parameter ``hits`` is ``None``.
		:raises TypeError:  If parameter ``hits`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``hits`` is negative.
		:raises TypeError:  If parameter ``parent`` isn't of type
		                    :class:`Scope`.
		"""
		if name is None:
			raise ValueError(f"Parameter 'name' is None.")
		elif not isinstance(name, str):
			ex = TypeError(f"Parameter 'name' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(name)}'.")
			raise ex
		elif name == "":
			raise ValueError(f"Parameter 'name' is empty.")

		if file is not None and not isinstance(file, Path):
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

		if hits is None:
			raise ValueError(f"Parameter 'hits' is None.")
		elif not isinstance(hits, int):
			ex = TypeError(f"Parameter 'hits' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(hits)}'.")
			raise ex
		elif hits < 0:
			ex = ValueError(f"Parameter 'hits' is negative.")
			ex.add_note(f"Got value '{hits}'.")
			raise ex

		if parent is not None and not isinstance(parent, Scope):
			ex = TypeError(f"Parameter 'parent' is not of type 'Scope'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =     parent
		self._name =       name
		self._file =       file
		self._lineNumber = lineNumber
		self._hits =       hits

		if parent is not None:
			parent._states.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Scope) -> Self:
		"""
		Parse a state from its ``<state>`` element.

		A ``<state>`` names no file number: its file is the scope's, if the scope has a single file.

		:param element: The ``<state>`` element.
		:param parent:  The scope the state belongs to.
		:returns:       The state.
		"""
		file = next(iter(parent._files.values())) if len(parent._files) == 1 else None
		return cls(
			element.attrib["state"], file, int(element.attrib["ln"]), int(element.attrib["hits"]), parent=parent
		)

	@readonly
	def Parent(self) -> Nullable[Scope]:
		"""
		Read-only property to access the scope the state belongs to (:attr:`_parent`).

		:returns: The scope; ``None`` if the state belongs to no scope.
		"""
		return self._parent

	@readonly
	def Name(self) -> str:
		"""
		Read-only property to access the name of the state (:attr:`_name`).

		:returns: The state's name, as the enumeration of the state machine names it.
		"""
		return self._name

	@readonly
	def File(self) -> Nullable[Path]:
		"""
		Read-only property to access the path of the source file (:attr:`_file`).

		:returns: The path, as the report states it; ``None``, if the scope has several files.
		"""
		return self._file

	@readonly
	def LineNumber(self) -> int:
		"""
		Read-only property to access the line number of the state (:attr:`_lineNumber`).

		:returns: The line number, counted from 1.
		"""
		return self._lineNumber

	@readonly
	def Hits(self) -> int:
		"""
		Read-only property to access how often the state was entered (:attr:`_hits`).

		:returns: The count.
		"""
		return self._hits


@export
class FSMTransition(metaclass=ExtendedType, slots=True):
	"""
	A ``<trans>`` of a scope: a transition of a finite state machine from one state to another, and how often it was
	taken.
	"""

	_parent:     Nullable[Scope]  #: The scope the transition belongs to.
	_identifier: int              #: Number of the transition in its state machine, counted from 0.
	_fromState:  str              #: Name of the state the transition leaves.
	_toState:    str              #: Name of the state the transition enters.
	_file:       Nullable[Path]   #: Path of the source file, if known.
	_lineNumber: int              #: Line number of the transition, counted from 1.
	_hits:       int              #: How often the transition was taken.

	def __init__(
		self,
		identifier: int,
		fromState: str,
		toState: str,
		file: Nullable[Path],
		lineNumber: int,
		hits: int,
		*,
		parent: Nullable[Scope] = None
	) -> None:
		"""
		Initialize the transition, and append it to the transitions of its scope.

		:param identifier:  Number of the transition in its state machine, counted from 0.
		:param fromState:   Name of the state the transition leaves.
		:param toState:     Name of the state the transition enters.
		:param file:        Path of the source file, as the report states it; ``None``, if unknown.
		:param lineNumber:  Line number of the transition, counted from 1.
		:param hits:        How often the transition was taken.
		:param parent:      Optional, the scope the transition belongs to. Default: ``None``.
		:raises ValueError: If parameter ``identifier`` is ``None``.
		:raises TypeError:  If parameter ``identifier`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``identifier`` is negative.
		:raises ValueError: If parameter ``fromState`` is ``None``.
		:raises TypeError:  If parameter ``fromState`` isn't of type :class:`str`.
		:raises ValueError: If parameter ``fromState`` is empty.
		:raises ValueError: If parameter ``toState`` is ``None``.
		:raises TypeError:  If parameter ``toState`` isn't of type :class:`str`.
		:raises ValueError: If parameter ``toState`` is empty.
		:raises TypeError:  If parameter ``file`` isn't of type :class:`~pathlib.Path`.
		:raises ValueError: If parameter ``lineNumber`` is ``None``.
		:raises TypeError:  If parameter ``lineNumber`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``lineNumber`` is less than 1.
		:raises ValueError: If parameter ``hits`` is ``None``.
		:raises TypeError:  If parameter ``hits`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``hits`` is negative.
		:raises TypeError:  If parameter ``parent`` isn't of type
		                    :class:`Scope`.
		"""
		if identifier is None:
			raise ValueError(f"Parameter 'identifier' is None.")
		elif not isinstance(identifier, int):
			ex = TypeError(f"Parameter 'identifier' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(identifier)}'.")
			raise ex
		elif identifier < 0:
			ex = ValueError(f"Parameter 'identifier' is negative.")
			ex.add_note(f"Got value '{identifier}'.")
			raise ex

		if fromState is None:
			raise ValueError(f"Parameter 'fromState' is None.")
		elif not isinstance(fromState, str):
			ex = TypeError(f"Parameter 'fromState' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(fromState)}'.")
			raise ex
		elif fromState == "":
			raise ValueError(f"Parameter 'fromState' is empty.")

		if toState is None:
			raise ValueError(f"Parameter 'toState' is None.")
		elif not isinstance(toState, str):
			ex = TypeError(f"Parameter 'toState' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(toState)}'.")
			raise ex
		elif toState == "":
			raise ValueError(f"Parameter 'toState' is empty.")

		if file is not None and not isinstance(file, Path):
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

		if hits is None:
			raise ValueError(f"Parameter 'hits' is None.")
		elif not isinstance(hits, int):
			ex = TypeError(f"Parameter 'hits' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(hits)}'.")
			raise ex
		elif hits < 0:
			ex = ValueError(f"Parameter 'hits' is negative.")
			ex.add_note(f"Got value '{hits}'.")
			raise ex

		if parent is not None and not isinstance(parent, Scope):
			ex = TypeError(f"Parameter 'parent' is not of type 'Scope'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =     parent
		self._identifier = identifier
		self._fromState =  fromState
		self._toState =    toState
		self._file =       file
		self._lineNumber = lineNumber
		self._hits =       hits

		if parent is not None:
			parent._transitions.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Scope) -> Self:
		"""
		Parse a transition from its ``<trans>`` element, whose attribute ``state`` names both states.

		A ``<trans>`` names no file number: its file is the scope's, if the scope has a single file.

		:param element:            The ``<trans>`` element.
		:param parent:             The scope the transition belongs to.
		:returns:                  The transition.
		:raises CodeCoverageError: If attribute ``state`` doesn't name two states separated by ``->``. |br|
		                           Questa writes it as ``<state> -> <state>``.
		"""
		fromState, separator, toState = element.attrib["state"].partition(" -> ")
		if separator == "" or fromState == "" or toState == "":
			ex = CodeCoverageError(f"'<trans>' in line {element.sourceline} doesn't name the states it connects.")
			ex.add_note(f"Got state='{element.attrib['state']}'.")
			ex.add_note(f"Questa writes it as '<state> -> <state>'.")
			raise ex

		file = next(iter(parent._files.values())) if len(parent._files) == 1 else None
		return cls(
			int(element.attrib["tid"]),
			fromState,
			toState,
			file,
			int(element.attrib["ln"]),
			int(element.attrib["hits"]),
			parent=parent
		)

	@readonly
	def Parent(self) -> Nullable[Scope]:
		"""
		Read-only property to access the scope the transition belongs to (:attr:`_parent`).

		:returns: The scope; ``None`` if the transition belongs to no scope.
		"""
		return self._parent

	@readonly
	def Identifier(self) -> int:
		"""
		Read-only property to access the number of the transition in its state machine (:attr:`_identifier`).

		:returns: The number, counted from 0.
		"""
		return self._identifier

	@readonly
	def FromState(self) -> str:
		"""
		Read-only property to access the name of the state the transition leaves (:attr:`_fromState`).

		:returns: The state's name.
		"""
		return self._fromState

	@readonly
	def ToState(self) -> str:
		"""
		Read-only property to access the name of the state the transition enters (:attr:`_toState`).

		:returns: The state's name.
		"""
		return self._toState

	@readonly
	def File(self) -> Nullable[Path]:
		"""
		Read-only property to access the path of the source file (:attr:`_file`).

		:returns: The path, as the report states it; ``None``, if the scope has several files.
		"""
		return self._file

	@readonly
	def LineNumber(self) -> int:
		"""
		Read-only property to access the line number of the transition (:attr:`_lineNumber`).

		:returns: The line number, counted from 1.
		"""
		return self._lineNumber

	@readonly
	def Hits(self) -> int:
		"""
		Read-only property to access how often the transition was taken (:attr:`_hits`).

		:returns: The count.
		"""
		return self._hits


@export
class Scope(StatisticsMixin, slots=True):
	"""
	Base-class of the scopes: an instance, a design unit or a source file, with its coverage statistics, its source files
	and its statements.
	"""

	_parent:         Nullable[Report]     #: The report the scope belongs to.
	_files:          dict[int, Path]      #: The source files, by the number the report gives them.
	_statements:     list[Statement]      #: The statements.
	_ifStatements:   list[IfStatement]    #: The ``if`` statements.
	_caseStatements: list[CaseStatement]  #: The ``case`` statements.
	_states:         list[FSMState]       #: The states of finite state machines.
	_transitions:    list[FSMTransition]  #: The transitions of finite state machines.

	def __init__(self, files: Nullable[Mapping[int, Path]] = None, *, parent: Nullable[Report] = None) -> None:
		"""
		Initialize the scope, and append it to the scopes of its report.

		Its coverage statistics and coverage items are added by creating them with this scope as their parent.

		:param files:       Optional, the source files, by the number the report gives them. Default: ``None``.
		:param parent:      Optional, the report the scope belongs to; the scope is appended to its scopes. Default:
		                    ``None``.
		:raises TypeError:  If parameter ``files`` isn't a mapping.
		:raises TypeError:  If parameter ``files`` contains a key not of type :class:`int`.
		:raises ValueError: If parameter ``files`` contains a negative key.
		:raises TypeError:  If parameter ``files`` contains a value not of type :class:`~pathlib.Path`.
		:raises TypeError:  If parameter ``parent`` isn't of type
		                    :class:`Report`.
		"""
		super().__init__()

		self._files = {}
		if files is not None:
			if not isinstance(files, Mapping):
				ex = TypeError(f"Parameter 'files' is not a mapping.")
				ex.add_note(f"Got type '{getFullyQualifiedName(files)}'.")
				raise ex

			for fileNumber, path in files.items():
				if not isinstance(fileNumber, int):
					ex = TypeError(f"Parameter 'files' contains a key not of type 'int'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(fileNumber)}'.")
					raise ex
				elif fileNumber < 0:
					ex = ValueError(f"Parameter 'files' contains a negative key.")
					ex.add_note(f"Got value '{fileNumber}'.")
					raise ex
				elif not isinstance(path, Path):
					ex = TypeError(f"Parameter 'files' contains a value not of type 'Path'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(path)}'.")
					raise ex

				self._files[fileNumber] = path

		if parent is not None and not isinstance(parent, Report):
			ex = TypeError(f"Parameter 'parent' is not of type 'Report'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =         parent
		self._statements =     []
		self._ifStatements =   []
		self._caseStatements = []
		self._states =         []
		self._transitions =    []

		if parent is not None:
			parent._scopes.append(self)

	@staticmethod
	def _ParseSourceTable(element: _Element) -> dict[int, Path]:
		"""
		Parse the source files of a scope's ``<sourceTable>``.

		:param element: The scope's element.
		:returns:       The source files, by their number; none, if the scope has no source table.
		"""
		return {
			int(fileMap.attrib["fn"]): Path(fileMap.attrib["path"]) for fileMap in element.iterfind("sourceTable/fileMap")
		}

	def _ParseItems(self, element: _Element) -> None:
		"""
		Parse the coverage statistics and the coverage items of the scope from its element.

		:param element:            The scope's element.
		:raises CodeCoverageError: If a coverage statistics element states more hit items than items.
		:raises CodeCoverageError: If the scope states a kind of coverage statistics twice.
		:raises CodeCoverageError: If a coverage item names an unknown file number, or none in a scope of several files.
		:raises CodeCoverageError: If an ``if`` or ``case`` statement states other figures than its branches have.
		:raises CodeCoverageError: If a transition's name doesn't name its two states.
		"""
		self._ParseStatistics(element)
		for child in element:
			if child.tag == "stmt":
				Statement.Parse(child, parent=self)
			elif child.tag == "if":
				IfStatement.Parse(child, parent=self)
			elif child.tag == "case":
				CaseStatement.Parse(child, parent=self)
			elif child.tag == "state":
				FSMState.Parse(child, parent=self)
			elif child.tag == "trans":
				FSMTransition.Parse(child, parent=self)

	def _ResolveFile(self, element: _Element) -> Path:
		"""
		Return the source file a coverage item's element names by its file number.

		An element without file number is in the scope's file: the path of a ``<fileData>``, or the only file of the source
		table.

		:param element:            The coverage item's element, e.g. a ``<stmt>``.
		:returns:                  The source file's path, as the report states it.
		:raises CodeCoverageError: If the file number isn't in the scope's source table.
		:raises CodeCoverageError: If the element names no file number, and the scope has no single file.
		"""
		if (fileNumber := element.attrib.get("fn")) is not None:
			if (file := self._files.get(int(fileNumber))) is None:
				ex = CodeCoverageError(
					f"'<{element.tag}>' in line {element.sourceline} names file number '{fileNumber}', which is unknown."
				)
				ex.add_note(f"Known file numbers: {', '.join(str(number) for number in self._files) or 'none'}.")
				raise ex

			return file
		elif isinstance(self, FileData):
			return self._path
		elif len(self._files) == 1:
			return next(iter(self._files.values()))

		ex = CodeCoverageError(f"'<{element.tag}>' in line {element.sourceline} names no file number.")
		ex.add_note(f"Its scope names {len(self._files)} files.")
		raise ex

	@readonly
	def Parent(self) -> Nullable[Report]:
		"""
		Read-only property to access the report the scope belongs to (:attr:`_parent`).

		:returns: The report; ``None`` if the scope belongs to none.
		"""
		return self._parent

	@readonly
	def Files(self) -> dict[int, Path]:
		"""
		Read-only property to access the source files (:attr:`_files`).

		:returns: The source files, by the number the report gives them; none, if the report has no details.
		"""
		return self._files

	@readonly
	def Statements(self) -> list[Statement]:
		"""
		Read-only property to access the statements (:attr:`_statements`).

		:returns: The statements, in the order the report lists them; none, if the report has no details.
		"""
		return self._statements

	@readonly
	def IfStatements(self) -> list[IfStatement]:
		"""
		Read-only property to access the ``if`` statements (:attr:`_ifStatements`).

		:returns: The ``if`` statements, in the order the report lists them; none, if the report has no details.
		"""
		return self._ifStatements

	@readonly
	def CaseStatements(self) -> list[CaseStatement]:
		"""
		Read-only property to access the ``case`` statements (:attr:`_caseStatements`).

		:returns: The ``case`` statements, in the order the report lists them; none, if the report has no details.
		"""
		return self._caseStatements

	@readonly
	def States(self) -> list[FSMState]:
		"""
		Read-only property to access the states of finite state machines (:attr:`_states`).

		:returns: The states, in the order the report lists them; none, if the report has no details.
		"""
		return self._states

	@readonly
	def Transitions(self) -> list[FSMTransition]:
		"""
		Read-only property to access the transitions of finite state machines (:attr:`_transitions`).

		:returns: The transitions, in the order the report lists them; none, if the report has no details.
		"""
		return self._transitions


@export
class InstanceData(Scope):
	"""
	An ``<instanceData>``: an instance of a design unit, or a package.
	"""

	_path:          str            #: Hierarchical path of the instance.
	_designUnit:    str            #: Name of the design unit.
	_secondaryUnit: Nullable[str]  #: Name of the secondary unit (the architecture), if the design unit has one.

	def __init__(
		self,
		path: str,
		designUnit: str,
		secondaryUnit: Nullable[str] = None,
		files: Nullable[Mapping[int, Path]] = None,
		*,
		parent: Nullable[Report] = None
	) -> None:
		"""
		Initialize the instance, and append it to the scopes of its report.

		:param path:          Hierarchical path of the instance, separated by ``/``.
		:param designUnit:    Name of the design unit.
		:param secondaryUnit: Optional, name of the secondary unit (the architecture). Default: ``None``.
		:param files:         Optional, the source files, by the number the report gives them. Default: ``None``.
		:param parent:        Optional, the report the instance belongs to. Default: ``None``.
		:raises TypeError:    If parameter ``files`` isn't a mapping.
		:raises TypeError:    If parameter ``files`` contains a key not of type :class:`int`.
		:raises ValueError:   If parameter ``files`` contains a negative key.
		:raises TypeError:    If parameter ``files`` contains a value not of type :class:`~pathlib.Path`.
		:raises TypeError:    If parameter ``parent`` isn't of type
		                      :class:`Report`.
		:raises ValueError:   If parameter ``path`` is ``None``.
		:raises TypeError:    If parameter ``path`` isn't of type :class:`str`.
		:raises ValueError:   If parameter ``path`` is empty.
		:raises ValueError:   If parameter ``designUnit`` is ``None``.
		:raises TypeError:    If parameter ``designUnit`` isn't of type :class:`str`.
		:raises ValueError:   If parameter ``designUnit`` is empty.
		:raises TypeError:    If parameter ``secondaryUnit`` isn't of type :class:`str`.
		:raises ValueError:   If parameter ``secondaryUnit`` is empty.
		"""
		super().__init__(files, parent=parent)

		if path is None:
			raise ValueError(f"Parameter 'path' is None.")
		elif not isinstance(path, str):
			ex = TypeError(f"Parameter 'path' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(path)}'.")
			raise ex
		elif path == "":
			raise ValueError(f"Parameter 'path' is empty.")

		if designUnit is None:
			raise ValueError(f"Parameter 'designUnit' is None.")
		elif not isinstance(designUnit, str):
			ex = TypeError(f"Parameter 'designUnit' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(designUnit)}'.")
			raise ex
		elif designUnit == "":
			raise ValueError(f"Parameter 'designUnit' is empty.")

		if secondaryUnit is not None:
			if not isinstance(secondaryUnit, str):
				ex = TypeError(f"Parameter 'secondaryUnit' is not of type 'str'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(secondaryUnit)}'.")
				raise ex
			elif secondaryUnit == "":
				raise ValueError(f"Parameter 'secondaryUnit' is empty.")

		self._path =          path
		self._designUnit =    designUnit
		self._secondaryUnit = secondaryUnit

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[Report] = None) -> Self:
		"""
		Parse an instance, its source files, coverage statistics and statements from its ``<instanceData>`` element.

		:param element:            The ``<instanceData>`` element.
		:param parent:             Optional, the report the instance belongs to. Default: ``None``.
		:returns:                  The instance.
		:raises CodeCoverageError: If a coverage statistics element states more hit items than items.
		:raises CodeCoverageError: If the instance states a kind of coverage statistics twice.
		:raises CodeCoverageError: If a coverage item names an unknown file number, or none in an instance of several
		                           files.
		"""
		instance = cls(
			element.attrib["path"],
			element.attrib["du"],
			element.attrib.get("sec"),
			cls._ParseSourceTable(element),
			parent=parent
		)
		instance._ParseItems(element)
		return instance

	@readonly
	def Path(self) -> str:
		"""
		Read-only property to access the hierarchical path of the instance (:attr:`_path`).

		:returns: The path, separated by ``/``.
		"""
		return self._path

	@readonly
	def DesignUnit(self) -> str:
		"""
		Read-only property to access the name of the design unit (:attr:`_designUnit`).

		:returns: The design unit's name, as Questa writes it: in lower case for VHDL.
		"""
		return self._designUnit

	@readonly
	def SecondaryUnit(self) -> Nullable[str]:
		"""
		Read-only property to access the name of the secondary unit (:attr:`_secondaryUnit`).

		:returns: The architecture's name, or ``None`` - e.g. for a package.
		"""
		return self._secondaryUnit


@export
class DesignUnitData(Scope):
	"""
	A ``<DuData>``: a design unit, its instances' coverage combined.
	"""

	_designUnit:    str            #: Name of the design unit.
	_secondaryUnit: Nullable[str]  #: Name of the secondary unit (the architecture), if the design unit has one.

	def __init__(
		self,
		designUnit: str,
		secondaryUnit: Nullable[str] = None,
		files: Nullable[Mapping[int, Path]] = None,
		*,
		parent: Nullable[Report] = None
	) -> None:
		"""
		Initialize the design unit, and append it to the scopes of its report.

		:param designUnit:    Name of the design unit.
		:param secondaryUnit: Optional, name of the secondary unit (the architecture). Default: ``None``.
		:param files:         Optional, the source files, by the number the report gives them. Default: ``None``.
		:param parent:        Optional, the report the design unit belongs to. Default: ``None``.
		:raises TypeError:    If parameter ``files`` isn't a mapping.
		:raises TypeError:    If parameter ``files`` contains a key not of type :class:`int`.
		:raises ValueError:   If parameter ``files`` contains a negative key.
		:raises TypeError:    If parameter ``files`` contains a value not of type :class:`~pathlib.Path`.
		:raises TypeError:    If parameter ``parent`` isn't of type
		                      :class:`Report`.
		:raises ValueError:   If parameter ``designUnit`` is ``None``.
		:raises TypeError:    If parameter ``designUnit`` isn't of type :class:`str`.
		:raises ValueError:   If parameter ``designUnit`` is empty.
		:raises TypeError:    If parameter ``secondaryUnit`` isn't of type :class:`str`.
		:raises ValueError:   If parameter ``secondaryUnit`` is empty.
		"""
		super().__init__(files, parent=parent)

		if designUnit is None:
			raise ValueError(f"Parameter 'designUnit' is None.")
		elif not isinstance(designUnit, str):
			ex = TypeError(f"Parameter 'designUnit' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(designUnit)}'.")
			raise ex
		elif designUnit == "":
			raise ValueError(f"Parameter 'designUnit' is empty.")

		if secondaryUnit is not None:
			if not isinstance(secondaryUnit, str):
				ex = TypeError(f"Parameter 'secondaryUnit' is not of type 'str'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(secondaryUnit)}'.")
				raise ex
			elif secondaryUnit == "":
				raise ValueError(f"Parameter 'secondaryUnit' is empty.")

		self._designUnit =    designUnit
		self._secondaryUnit = secondaryUnit

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[Report] = None) -> Self:
		"""
		Parse a design unit, its source files, coverage statistics and statements from its ``<DuData>`` element.

		:param element:            The ``<DuData>`` element.
		:param parent:             Optional, the report the design unit belongs to. Default: ``None``.
		:returns:                  The design unit.
		:raises CodeCoverageError: If a coverage statistics element states more hit items than items.
		:raises CodeCoverageError: If the design unit states a kind of coverage statistics twice.
		:raises CodeCoverageError: If a coverage item names an unknown file number, or none in a design unit of several
		                           files.
		"""
		designUnit = cls(element.attrib["du"], element.attrib.get("sec"), cls._ParseSourceTable(element), parent=parent)
		designUnit._ParseItems(element)
		return designUnit

	@readonly
	def DesignUnit(self) -> str:
		"""
		Read-only property to access the name of the design unit (:attr:`_designUnit`).

		:returns: The design unit's name, as Questa writes it: in lower case for VHDL.
		"""
		return self._designUnit

	@readonly
	def SecondaryUnit(self) -> Nullable[str]:
		"""
		Read-only property to access the name of the secondary unit (:attr:`_secondaryUnit`).

		:returns: The architecture's name, or ``None`` - e.g. for a package.
		"""
		return self._secondaryUnit


@export
class FileData(Scope):
	"""
	A ``<fileData>``: a source file.
	"""

	_path: _Path  #: Path of the source file, as the report states it.

	def __init__(
		self,
		path: Path,
		files: Nullable[Mapping[int, Path]] = None,
		*,
		parent: Nullable[Report] = None
	) -> None:
		"""
		Initialize the source file, and append it to the scopes of its report.

		:param path:        Path of the source file, as the report states it.
		:param files:       Optional, the source files, by the number the report gives them. Default: ``None``.
		:param parent:      Optional, the report the source file belongs to. Default: ``None``.
		:raises TypeError:  If parameter ``files`` isn't a mapping.
		:raises TypeError:  If parameter ``files`` contains a key not of type :class:`int`.
		:raises ValueError: If parameter ``files`` contains a negative key.
		:raises TypeError:  If parameter ``files`` contains a value not of type :class:`~pathlib.Path`.
		:raises TypeError:  If parameter ``parent`` isn't of type
		                    :class:`Report`.
		:raises ValueError: If parameter ``path`` is ``None``.
		:raises TypeError:  If parameter ``path`` isn't of type :class:`~pathlib.Path`.
		"""
		super().__init__(files, parent=parent)

		if path is None:
			raise ValueError(f"Parameter 'path' is None.")
		elif not isinstance(path, Path):
			ex = TypeError(f"Parameter 'path' is not of type 'Path'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(path)}'.")
			raise ex

		self._path = path

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[Report] = None) -> Self:
		"""
		Parse a source file, its coverage statistics and statements from its ``<fileData>`` element.

		:param element:            The ``<fileData>`` element.
		:param parent:             Optional, the report the source file belongs to. Default: ``None``.
		:returns:                  The source file.
		:raises CodeCoverageError: If a coverage statistics element states more hit items than items.
		:raises CodeCoverageError: If the source file states a kind of coverage statistics twice.
		:raises CodeCoverageError: If a coverage item names an unknown file number.
		"""
		fileData = cls(Path(element.attrib["path"]), cls._ParseSourceTable(element), parent=parent)
		fileData._ParseItems(element)
		return fileData

	@readonly
	def Path(self) -> _Path:
		"""
		Read-only property to access the path of the source file (:attr:`_path`).

		:returns: The path, as the report states it.
		"""
		return self._path


@export
class Totals(StatisticsMixin):
	"""
	A summary record of a report - ``<summaryByFile>`` or ``<summaryByInstance>`` -: the coverage statistics of all its
	files or instances together.
	"""

	_parent: Nullable[Report]  #: The report the summary record belongs to.
	_mode:   ReportMode        #: What the summary record sums up: files or instances.
	_count:  int               #: Number of files or instances summed up.

	def __init__(self, mode: ReportMode, count: int, *, parent: Nullable[Report] = None) -> None:
		"""
		Initialize the summary record, and add it to the summary records of its report.

		Its coverage statistics are added by creating them with this summary record as their parent.

		:param mode:               What the summary record sums up: :attr:`ReportMode.ByFile` or
		                           :attr:`ReportMode.ByInstance`.
		:param count:              Number of files or instances summed up.
		:param parent:             Optional, the report the summary record belongs to; it is added to its summary records
		                           by :attr:`Mode`. Default: ``None``.
		:raises ValueError:        If parameter ``mode`` is ``None``.
		:raises TypeError:         If parameter ``mode`` isn't of type :class:`ReportMode`.
		:raises ValueError:        If parameter ``mode`` is :attr:`ReportMode.ByDesignUnit`.
		:raises ValueError:        If parameter ``count`` is ``None``.
		:raises TypeError:         If parameter ``count`` isn't of type :class:`int`.
		:raises ValueError:        If parameter ``count`` is negative.
		:raises TypeError:         If parameter ``parent`` isn't of type
		                           :class:`Report`.
		:raises CodeCoverageError: If the report already has a summary record of this mode.
		"""
		super().__init__()

		if mode is None:
			raise ValueError(f"Parameter 'mode' is None.")
		elif not isinstance(mode, ReportMode):
			ex = TypeError(f"Parameter 'mode' is not of type 'ReportMode'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(mode)}'.")
			raise ex
		elif mode is ReportMode.ByDesignUnit:
			ex = ValueError(f"Parameter 'mode' is not 'ByFile' or 'ByInstance'.")
			ex.add_note(f"Got value '{mode.name}'.")
			raise ex

		if count is None:
			raise ValueError(f"Parameter 'count' is None.")
		elif not isinstance(count, int):
			ex = TypeError(f"Parameter 'count' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(count)}'.")
			raise ex
		elif count < 0:
			ex = ValueError(f"Parameter 'count' is negative.")
			ex.add_note(f"Got value '{count}'.")
			raise ex

		if parent is not None:
			if not isinstance(parent, Report):
				ex = TypeError(f"Parameter 'parent' is not of type 'Report'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
				raise ex
			elif mode in parent._totals:
				raise CodeCoverageError(f"Summary record '{mode}' is stated twice.")

		self._parent = parent
		self._mode =   mode
		self._count =  count

		if parent is not None:
			parent._totals[mode] = self

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[Report] = None) -> Self:
		"""
		Parse a summary record and its coverage statistics from its ``<summaryByFile>`` or ``<summaryByInstance>``
		element.

		:param element:            The summary record's element.
		:param parent:             Optional, the report the summary record belongs to. Default: ``None``.
		:returns:                  The summary record.
		:raises CodeCoverageError: If a coverage statistics element states more hit items than items.
		"""
		if element.tag == "summaryByFile":
			totals = cls(ReportMode.ByFile, int(element.attrib["files"]), parent=parent)
		else:
			totals = cls(ReportMode.ByInstance, int(element.attrib["instances"]), parent=parent)

		totals._ParseStatistics(element)
		return totals

	@readonly
	def Parent(self) -> Nullable[Report]:
		"""
		Read-only property to access the report the summary record belongs to (:attr:`_parent`).

		:returns: The report; ``None`` if the summary record belongs to none.
		"""
		return self._parent

	@readonly
	def Mode(self) -> ReportMode:
		"""
		Read-only property to access what the summary record sums up (:attr:`_mode`).

		:returns: :attr:`ReportMode.ByFile` or :attr:`ReportMode.ByInstance`.
		"""
		return self._mode

	@readonly
	def Count(self) -> int:
		"""
		Read-only property to access the number of files or instances summed up (:attr:`_count`).

		:returns: The number of files or instances.
		"""
		return self._count


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
				content = self._path.read_bytes()
			except OSError as ex:
				raise CodeCoverageError(f"Couldn't read QuestaSim coverage report '{self._path}'.") from ex

			try:
				xmlDocument = parse(BytesIO(content), XMLParser(ns_clean=True), base_url=str(self._path))
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
