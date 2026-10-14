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
The coverage statistics of QuestaSim's coverage report XML, and the summary records holding them for a whole report.

A coverage statistics element states how many coverage items of a kind - e.g. statements or branches - a scope or a
summary record has, and how many of them were hit.
"""
from __future__                              import annotations

from typing                                  import TYPE_CHECKING, Optional as Nullable, Self

from lxml.etree                              import _Element
from pyTooling.Common                        import getFullyQualifiedName, StringEnum
from pyTooling.Decorators                    import export, readonly
from pyTooling.MetaClasses                   import ExtendedType

from pyEDAA.Reports.CodeCoverage             import CodeCoverageError

if TYPE_CHECKING:
	from pyEDAA.Reports.CodeCoverage.QuestaSim import Report


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
		                           :class:`~pyEDAA.Reports.CodeCoverage.QuestaSim.Report`.
		:raises CodeCoverageError: If the report already has a summary record of this mode.
		"""
		from pyEDAA.Reports.CodeCoverage.QuestaSim import Report

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
