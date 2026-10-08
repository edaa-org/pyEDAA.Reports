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
The elements of JaCoCo's XML format beside the packages: the sessions, the counters every level states, and the
base-class of the named elements.
"""
from __future__                           import annotations

from datetime                             import datetime, timedelta, timezone
from typing                               import TYPE_CHECKING, Optional as Nullable, Self

from lxml.etree                           import _Element
from pyTooling.Common                     import getFullyQualifiedName, StringEnum
from pyTooling.Decorators                 import export, readonly
from pyTooling.MetaClasses                import ExtendedType, abstractclass

if TYPE_CHECKING:
	from pyEDAA.Reports.CodeCoverage.JaCoCo import Report


@export
class SessionInfo(metaclass=ExtendedType, slots=True):
	"""
	A ``<sessioninfo>`` of the report: a session, which contributed execution data - its ID, its start and its dump.
	"""

	_parent:    Nullable[Report]  #: The report the session belongs to.
	_sessionID: str               #: ID of the session.
	_start:     datetime          #: Time the session started.
	_dump:      datetime          #: Time the session's execution data was dumped.

	def __init__(self, sessionID: str, start: datetime, dump: datetime, *, parent: Nullable[Report] = None) -> None:
		"""
		Initialize the session, and append it to the sessions of its report.

		:param sessionID:   ID of the session, e.g. the host's name and a random number.
		:param start:       Time the session started.
		:param dump:        Time the session's execution data was dumped.
		:param parent:      Optional, the report the session belongs to; the session is appended to its sessions.
		                    Default: ``None``.
		:raises ValueError: If parameter ``sessionID`` is ``None``.
		:raises TypeError:  If parameter ``sessionID`` isn't of type :class:`str`.
		:raises ValueError: If parameter ``start`` is ``None``.
		:raises TypeError:  If parameter ``start`` isn't of type :class:`~datetime.datetime`.
		:raises ValueError: If parameter ``dump`` is ``None``.
		:raises TypeError:  If parameter ``dump`` isn't of type :class:`~datetime.datetime`.
		:raises TypeError:  If parameter ``parent`` isn't of type :class:`~pyEDAA.Reports.CodeCoverage.JaCoCo.Report`.
		"""
		from pyEDAA.Reports.CodeCoverage.JaCoCo import Report

		if sessionID is None:
			raise ValueError(f"Parameter 'sessionID' is None.")
		elif not isinstance(sessionID, str):
			ex = TypeError(f"Parameter 'sessionID' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(sessionID)}'.")
			raise ex

		if start is None:
			raise ValueError(f"Parameter 'start' is None.")
		elif not isinstance(start, datetime):
			ex = TypeError(f"Parameter 'start' is not of type 'datetime'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(start)}'.")
			raise ex

		if dump is None:
			raise ValueError(f"Parameter 'dump' is None.")
		elif not isinstance(dump, datetime):
			ex = TypeError(f"Parameter 'dump' is not of type 'datetime'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(dump)}'.")
			raise ex

		if parent is not None and not isinstance(parent, Report):
			ex = TypeError(f"Parameter 'parent' is not of type 'Report'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =    parent
		self._sessionID = sessionID
		self._start =     start
		self._dump =      dump

		if parent is not None:
			parent._sessionInfos.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[Report] = None) -> Self:
		"""
		Parse a session from its ``<sessioninfo>`` element.

		The times are stated in milliseconds since the epoch.

		:param element: The ``<sessioninfo>`` element.
		:param parent:  Optional, the report the session belongs to. Default: ``None``.
		:returns:       The session.
		"""
		epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
		return cls(
			element.attrib["id"],
			epoch + timedelta(milliseconds=int(element.attrib["start"])),
			epoch + timedelta(milliseconds=int(element.attrib["dump"])),
			parent=parent
		)

	@readonly
	def Parent(self) -> Nullable[Report]:
		"""
		Read-only property to access the report the session belongs to (:attr:`_parent`).

		:returns: The report; ``None`` if the session belongs to no report.
		"""
		return self._parent

	@readonly
	def SessionID(self) -> str:
		"""
		Read-only property to access the ID of the session (:attr:`_sessionID`).

		JaCoCo's agent names a session by the host's name and a random number, e.g. ``dffa20ef8728-f9da5560``.

		:returns: The ID.
		"""
		return self._sessionID

	@readonly
	def Start(self) -> datetime:
		"""
		Read-only property to access the time the session started (:attr:`_start`).

		:returns: The time, with time zone UTC, if read from a report.
		"""
		return self._start

	@readonly
	def Dump(self) -> datetime:
		"""
		Read-only property to access the time the session's execution data was dumped (:attr:`_dump`).

		:returns: The time, with time zone UTC, if read from a report.
		"""
		return self._dump


@export
class CounterType(StringEnum):
	"""
	Kind of items a ``<counter>`` counts, as its ``type`` states.
	"""

	Instruction = "INSTRUCTION"  #: Java bytecode instructions.
	Branch =      "BRANCH"       #: Branches of ``if`` and ``switch`` statements.
	Line =        "LINE"         #: Source lines with at least one instruction.
	Complexity =  "COMPLEXITY"   #: Cyclomatic complexity: paths, which in linear combination generate all paths.
	Method =      "METHOD"       #: Methods - also constructors and static initializers - with at least one instruction.
	Class =       "CLASS"        #: Classes with at least one method.


@export
class CountersMixin(metaclass=ExtendedType, mixin=True):
	"""
	A mixin-class adding the counters an element states: per kind of items, how many were missed and covered.
	"""

	_counters: dict[CounterType, Counter]  #: The counters, by kind.

	def __init__(self) -> None:
		"""
		Initialize the counters to none.

		A counter is added by creating it with the element as its parent.
		"""
		self._counters = {}

	@readonly
	def Counters(self) -> dict[CounterType, Counter]:
		"""
		Read-only property to access the counters (:attr:`_counters`).

		:returns: The counters, by kind; a kind without items has no counter.
		"""
		return self._counters


@export
class Counter(metaclass=ExtendedType, slots=True):
	"""
	A ``<counter>`` of an element: how many items of a kind were missed and covered.
	"""

	_parent:       Nullable[CountersMixin]  #: The element the counter belongs to.
	_type:         CounterType              #: Kind of items the counter counts.
	_missedCount:  int                      #: Number of missed items.
	_coveredCount: int                      #: Number of covered items.

	def __init__(
		self,
		counterType:  CounterType,
		missedCount:  int,
		coveredCount: int,
		*,
		parent:       Nullable[CountersMixin] = None
	) -> None:
		"""
		Initialize the counter, and add it to the counters of its element.

		:param counterType:  Kind of items the counter counts.
		:param missedCount:  Number of missed items.
		:param coveredCount: Number of covered items.
		:param parent:       Optional, the element the counter belongs to; the counter is added to its counters by
		                     :attr:`Type`. Default: ``None``.
		:raises ValueError:  If parameter ``counterType`` is ``None``.
		:raises TypeError:   If parameter ``counterType`` isn't of type :class:`CounterType`.
		:raises ValueError:  If parameter ``missedCount`` is ``None``.
		:raises TypeError:   If parameter ``missedCount`` isn't of type :class:`int`.
		:raises ValueError:  If parameter ``missedCount`` is negative.
		:raises ValueError:  If parameter ``coveredCount`` is ``None``.
		:raises TypeError:   If parameter ``coveredCount`` isn't of type :class:`int`.
		:raises ValueError:  If parameter ``coveredCount`` is negative.
		:raises TypeError:   If parameter ``parent`` isn't of type :class:`CountersMixin`.
		"""
		if counterType is None:
			raise ValueError(f"Parameter 'counterType' is None.")
		elif not isinstance(counterType, CounterType):
			ex = TypeError(f"Parameter 'counterType' is not of type 'CounterType'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(counterType)}'.")
			raise ex

		if missedCount is None:
			raise ValueError(f"Parameter 'missedCount' is None.")
		elif not isinstance(missedCount, int):
			ex = TypeError(f"Parameter 'missedCount' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(missedCount)}'.")
			raise ex
		elif missedCount < 0:
			ex = ValueError(f"Parameter 'missedCount' is negative.")
			ex.add_note(f"Got value '{missedCount}'.")
			raise ex

		if coveredCount is None:
			raise ValueError(f"Parameter 'coveredCount' is None.")
		elif not isinstance(coveredCount, int):
			ex = TypeError(f"Parameter 'coveredCount' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(coveredCount)}'.")
			raise ex
		elif coveredCount < 0:
			ex = ValueError(f"Parameter 'coveredCount' is negative.")
			ex.add_note(f"Got value '{coveredCount}'.")
			raise ex

		if parent is not None and not isinstance(parent, CountersMixin):
			ex = TypeError(f"Parameter 'parent' is not of type 'CountersMixin'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =       parent
		self._type =         counterType
		self._missedCount =  missedCount
		self._coveredCount = coveredCount

		if parent is not None:
			parent._counters[self._type] = self

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[CountersMixin] = None) -> Self:
		"""
		Parse a counter from its ``<counter>`` element.

		:param element: The ``<counter>`` element.
		:param parent:  Optional, the element the counter belongs to. Default: ``None``.
		:returns:       The counter.
		"""
		return cls(
			CounterType(element.attrib["type"]),
			int(element.attrib["missed"]),
			int(element.attrib["covered"]),
			parent=parent
		)

	@readonly
	def Parent(self) -> Nullable[CountersMixin]:
		"""
		Read-only property to access the element the counter belongs to (:attr:`_parent`).

		:returns: The element; ``None`` if the counter belongs to no element.
		"""
		return self._parent

	@readonly
	def Type(self) -> CounterType:
		"""
		Read-only property to access the kind of items the counter counts (:attr:`_type`).

		:returns: The kind of items.
		"""
		return self._type

	@readonly
	def MissedCount(self) -> int:
		"""
		Read-only property to access the number of missed items (:attr:`_missedCount`).

		:returns: The number of missed items.
		"""
		return self._missedCount

	@readonly
	def CoveredCount(self) -> int:
		"""
		Read-only property to access the number of covered items (:attr:`_coveredCount`).

		:returns: The number of covered items.
		"""
		return self._coveredCount


@export
@abstractclass
class Base(metaclass=ExtendedType, slots=True):
	"""
	Base-class of the named elements below the report, e.g. packages and classes.
	"""

	_name: str  #: Name of the element.

	def __init__(self, name: str) -> None:
		"""
		Initialize the name of the element.

		:param name:        Name of the element.
		:raises ValueError: If parameter ``name`` is ``None``.
		:raises TypeError:  If parameter ``name`` isn't of type :class:`str`.
		"""
		if name is None:
			raise ValueError(f"Parameter 'name' is None.")
		elif not isinstance(name, str):
			ex = TypeError(f"Parameter 'name' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(name)}'.")
			raise ex

		self._name = name

	@readonly
	def Name(self) -> str:
		"""
		Read-only property to access the name of the element (:attr:`_name`).

		:returns: The name.
		"""
		return self._name
