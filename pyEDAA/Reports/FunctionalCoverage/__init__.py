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
Abstract data model of functional coverage: covergroups, their coverpoints and crosses, and the bins counting how often
a value - or a combination of values - was sampled.

The model is tool-neutral: it follows the terms of SystemVerilog covergroups and of the Accellera UCIS standard, and
an OSVVM coverage model maps to it too.

* The root, :class:`FunctionalCoverageReport`, holds the covergroups of a report, e.g. of a testcase.
* A :class:`Covergroup` holds its coverage items, each by name: :class:`Coverpoint` - one sampled value - and
  :class:`Cross` - a combination of values, one per crossed item.
* A coverage item holds its bins: a :class:`CoverpointBin` counts the values of its :class:`ValueRange` objects, a
  :class:`CrossBin` the combinations of values, one set of ranges per crossed item. A bin's :class:`BinKind` says
  whether it counts toward the coverage, is ignored or must not be hit.

Every element has key-value pairs (:class:`~pyTooling.DataModel.KeyValuePairsMixin`) for data the model doesn't name,
e.g. a tool's settings.
"""
from __future__            import annotations

from enum                  import Enum
from typing                import Any, Callable, ClassVar, Generator, Hashable, Iterable, Mapping, Optional as Nullable

from pyTooling.Common      import getFullyQualifiedName
from pyTooling.DataModel   import KeyValuePairsMixin
from pyTooling.Decorators  import export, readonly
from pyTooling.Exceptions  import AlreadyInHierarchyError, DuplicateElementError
from pyTooling.MetaClasses import ExtendedType, abstractclass

from pyEDAA.Reports        import ReportException


@export
class FunctionalCoverageError(ReportException):
	"""Base-exception of the functional coverage model."""


@export
class AlreadyInFunctionalCoverageReportError(FunctionalCoverageError, AlreadyInHierarchyError):
	"""The exception is raised when an element is added to an element, but it already has a parent."""


@export
class DuplicateCoverpointError(FunctionalCoverageError, DuplicateElementError):
	"""The exception is raised when a covergroup already contains a coverpoint or a cross of the same name."""


@export
class DuplicateCrossError(FunctionalCoverageError, DuplicateElementError):
	"""The exception is raised when a covergroup already contains a cross or a coverpoint of the same name."""


@export
class BinKind(Enum):
	"""The kind of a bin: whether it counts toward the coverage, is ignored or must not be hit."""

	Count =   0  #: Counts toward the coverage; covered, when its count reaches its *at least* count.
	Ignore =  1  #: Excluded from the coverage: its values aren't of interest.
	Illegal = 2  #: Excluded from the coverage: its values must not occur, a hit is an error.
	Default = 3  #: Excluded from the coverage: counts the values no other bin of the coverage item counts.


@export
class ValueRange(metaclass=ExtendedType, slots=True):
	"""
	A range of values - from a lowest to a highest value, both included - a bin counts.

	A single value is a range from and to this value. It is a value, as a path is: it names no parent.
	"""

	_low:  int  #: The lowest value of the range.
	_high: int  #: The highest value of the range.

	def __init__(self, low: int, high: int) -> None:
		"""
		Initializes a range of values.

		:param low:         The lowest value of the range.
		:param high:        The highest value of the range.
		:raises ValueError: If parameter ``low`` is ``None``.
		:raises TypeError:  If parameter ``low`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``high`` is ``None``.
		:raises TypeError:  If parameter ``high`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``high`` is less than parameter ``low``.
		"""
		for parameterName, value in (
			("low",  low),
			("high", high)
		):
			if value is None:
				raise ValueError(f"Parameter '{parameterName}' is None.")
			elif not isinstance(value, int) or isinstance(value, bool):
				ex = TypeError(f"Parameter '{parameterName}' is not of type 'int'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
				raise ex

		if high < low:
			ex = ValueError("Parameter 'high' is less than parameter 'low'.")
			ex.add_note(f"Got range {low} to {high}.")
			raise ex

		self._low =  low
		self._high = high

	@readonly
	def Low(self) -> int:
		"""
		Read-only property to access the lowest value of the range (:attr:`_low`).

		:returns: The lowest value.
		"""
		return self._low

	@readonly
	def High(self) -> int:
		"""
		Read-only property to access the highest value of the range (:attr:`_high`).

		:returns: The highest value.
		"""
		return self._high

	def __eq__(self, other: Any) -> bool:
		"""
		Compare two ranges of values.

		:param other: The other range.
		:returns:     ``True``, if both ranges have the same lowest and highest value.
		"""
		if not isinstance(other, ValueRange):
			return NotImplemented

		return self._low == other._low and self._high == other._high

	def __hash__(self) -> int:
		"""
		Return a hash of the range of values, so equal ranges have the same hash.

		:returns: The hash of the lowest and highest value.
		"""
		return hash((self._low, self._high))

	def __repr__(self) -> str:
		"""
		Return a representation of the range of values for debugging.

		A range from 3 to 11 reads ``<ValueRange 3..11>``.

		:returns: The lowest and the highest value.
		"""
		return f"<ValueRange {self._low}..{self._high}>"


@export
class Base(KeyValuePairsMixin, metaclass=ExtendedType, slots=True):
	"""
	Base-class of every element of the functional coverage model: key-value pairs, a reference to the element containing
	it, and to the report's root.
	"""

	_PARENT_TYPE: ClassVar[tuple[type, ...]]  #: The types a parent may have; assigned by each class having a parent.

	_parent: Nullable[Base]                      #: The element containing this one, or ``None``.
	_root:   Nullable[FunctionalCoverageReport]  #: The report's root, or ``None`` while the element isn't part of one.

	def __init__(self, keyValuePairs: Nullable[Mapping[Hashable, Any]] = None, *, parent: Nullable[Base] = None) -> None:
		"""
		Initializes an element with its key-value pairs, its parent and the parent's root.

		The parent doesn't list the element yet: the class setting the fields the parent checks - a name, the crossed
		items - adds it with ``parent._AddElement(self)``.

		:param keyValuePairs: Optional, the key-value pairs. Default: ``None``.
		:param parent:        Optional, the element containing this one. Default: ``None``.
		:raises TypeError:    If parameter ``keyValuePairs`` isn't a mapping.
		:raises TypeError:    If parameter ``parent`` isn't of a type this class declares in :attr:`_PARENT_TYPE`.
		"""
		super().__init__(keyValuePairs)

		if parent is None:
			self._parent = None
			self._root =   None
		elif not isinstance(parent, self._PARENT_TYPE):
			typeNames = " or ".join(f"'{parentType.__name__}'" for parentType in self._PARENT_TYPE)
			ex = TypeError(f"Parameter 'parent' is not of type {typeNames}.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex
		else:
			self._parent = parent
			self._root =   parent._root

	@property
	def Parent(self) -> Nullable[Base]:
		"""
		Property to access the element containing this one (:attr:`_parent`).

		Assigning a parent adds this element to it, and sets the parent's root as the root of this element and of every
		element below it.

		:returns:                                       The parent, or ``None``.
		:raises ValueError:                             If ``None`` is assigned.
		:raises TypeError:                              If the assigned parent isn't of a type this class declares in
		                                                :attr:`_PARENT_TYPE`.
		:raises TypeError:                              If a parent is assigned to a :class:`FunctionalCoverageReport`,
		                                                which has no parent.
		:raises AlreadyInFunctionalCoverageReportError: If the element already has a parent.
		:raises DuplicateCoverpointError:               If the assigned covergroup already contains a coverpoint or a
		                                                cross of the coverpoint's name.
		:raises DuplicateCrossError:                    If the assigned covergroup already contains a cross or a
		                                                coverpoint of the cross' name.
		:raises FunctionalCoverageError:                If a cross bin has not one set of ranges per crossed item of the
		                                                assigned cross.
		"""
		return self._parent

	@Parent.setter
	def Parent(self, parent: Base) -> None:
		if parent is None:
			raise ValueError("Parameter 'parent' is None.")
		elif not isinstance(parent, self._PARENT_TYPE):
			typeNames = " or ".join(f"'{parentType.__name__}'" for parentType in self._PARENT_TYPE)
			ex = TypeError(f"Parameter 'parent' is not of type {typeNames}.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex
		elif self._parent is not None:
			ex = AlreadyInFunctionalCoverageReportError(f"{self.__class__.__name__} already has a parent.")
			ex.add_note(f"Got element '{self!r}'.")
			raise ex

		parent._AddElement(self)
		self._parent = parent
		self._SetRoot(parent._root)

	@readonly
	def Root(self) -> Nullable[FunctionalCoverageReport]:
		"""
		Read-only property to access the report's root (:attr:`_root`).

		The root is maintained by :attr:`Parent`: assigning a parent sets it for this element and every element below it.

		:returns: The root, or ``None`` while the element isn't part of a report.
		"""
		return self._root

	def _SetRoot(self, root: Nullable[FunctionalCoverageReport]) -> None:
		"""
		Set the report's root of this element.

		A class with child elements extends it to set the root of its children too.

		:param root: The report's root, or ``None`` while the element isn't part of a report.
		"""
		self._root = root


@export
class BaseWithName(Base):
	"""
	Base-class of the named elements: the report, covergroups and coverage items.
	"""

	_name: str  #: Name of the element.

	def __init__(
		self,
		name: str,
		keyValuePairs: Nullable[Mapping[Hashable, Any]] = None,
		*,
		parent: Nullable[Base] = None
	) -> None:
		"""
		Initializes the key-value pairs, the parent and the name.

		:param name:          Name of the element.
		:param keyValuePairs: Optional, the key-value pairs. Default: ``None``.
		:param parent:        Optional, the element containing this one. Default: ``None``.
		:raises TypeError:    If parameter ``keyValuePairs`` isn't a mapping.
		:raises TypeError:    If parameter ``parent`` isn't of a type this class declares in :attr:`_PARENT_TYPE`.
		:raises ValueError:   If parameter ``name`` is ``None``.
		:raises TypeError:    If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError:   If parameter ``name`` is empty.
		"""
		super().__init__(keyValuePairs, parent=parent)

		if name is None:
			raise ValueError("Parameter 'name' is None.")
		elif not isinstance(name, str):
			ex = TypeError("Parameter 'name' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(name)}'.")
			raise ex
		elif name == "":
			raise ValueError("Parameter 'name' is empty.")

		self._name = name

	@readonly
	def Name(self) -> str:
		"""
		Read-only property to access the name (:attr:`_name`).

		:returns: The name.
		"""
		return self._name


@export
class FunctionalCoverageReport(BaseWithName):
	"""
	The root of a functional coverage report: its covergroups.

	It is its own root, and has no parent. A covergroup joins it by naming it as its parent, in the covergroup's
	constructor or by :attr:`~Base.Parent`. The names of covergroups needn't be unique: several instances of a covergroup
	may share a name.
	"""

	_covergroups: list[Covergroup]  #: The covergroups, in the order they were added.

	def __init__(self, name: str, keyValuePairs: Nullable[Mapping[Hashable, Any]] = None) -> None:
		"""
		Initializes the root of a functional coverage report.

		:param name:          Name of the report, e.g. of the testcase measured.
		:param keyValuePairs: Optional, the key-value pairs. Default: ``None``.
		:raises TypeError:    If parameter ``keyValuePairs`` isn't a mapping.
		:raises ValueError:   If parameter ``name`` is ``None``.
		:raises TypeError:    If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError:   If parameter ``name`` is empty.
		"""
		super().__init__(name, keyValuePairs=keyValuePairs)

		self._root =        self
		self._covergroups = []

	@Base.Parent.setter
	def Parent(self, parent: None) -> None:
		ex = TypeError(f"A '{getFullyQualifiedName(self)}' has no parent.")
		ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
		raise ex

	def _AddElement(self, covergroup: Covergroup) -> None:
		"""
		Add a covergroup, which names the report as its parent.

		:param covergroup: The covergroup.
		"""
		self._covergroups.append(covergroup)

	@readonly
	def Covergroups(self) -> list[Covergroup]:
		"""
		Read-only property to access the covergroups (:attr:`_covergroups`).

		:returns: The covergroups, in the order they were added.
		"""
		return self._covergroups

	@readonly
	def CovergroupCount(self) -> int:
		"""
		Read-only property to return the number of covergroups.

		:returns: The number of covergroups.
		"""
		return len(self._covergroups)

	def IterateCovergroups(
		self,
		predicate: Nullable[Callable[[Covergroup], bool]] = None
	) -> Generator[Covergroup, None, None]:
		"""
		Iterate all or selected covergroups.

		The covergroups are iterated in the order they were added. If parameter ``predicate`` is not None, the given filter
		function is used to skip covergroups in the generator.

		:param predicate: Optional, filter function accepting any covergroup and returning a boolean. Default: ``None``.
		:returns:         A generator of the covergroups.
		"""
		if predicate is None:
			yield from self._covergroups
		else:
			for covergroup in self._covergroups:
				if predicate(covergroup):
					yield covergroup

	def __repr__(self) -> str:
		"""
		Return a representation of the report for debugging.

		A report ``TbStream_SendGetRandom1`` of 6 covergroups reads
		``<FunctionalCoverageReport TbStream_SendGetRandom1: 6 covergroups>``.

		:returns: The report's name and its number of covergroups.
		"""
		return f"<FunctionalCoverageReport {self._name}: {len(self._covergroups)} covergroups>"


@export
class Covergroup(BaseWithName):
	"""
	A covergroup: its coverage items - coverpoints and crosses -, each by name, and the testcases, which sampled it.

	Its parent is the :class:`FunctionalCoverageReport`. Coverpoints and crosses share one namespace.
	"""

	_PARENT_TYPE: ClassVar[tuple[type, ...]] = (FunctionalCoverageReport, )  #: A covergroup is in a report.

	_testcases:   list[str]              #: The names of the testcases, which sampled the covergroup.
	_coverpoints: dict[str, Coverpoint]  #: The coverpoints, by name.
	_crosses:     dict[str, Cross]       #: The crosses, by name.

	def __init__(
		self,
		name: str,
		testcases: Nullable[Iterable[str]] = None,
		keyValuePairs: Nullable[Mapping[Hashable, Any]] = None,
		*,
		parent: Nullable[FunctionalCoverageReport] = None
	) -> None:
		"""
		Initializes a covergroup, and adds it to its report.

		Its coverpoints and crosses are added by creating them with this covergroup as their parent.

		:param name:          Name of the covergroup.
		:param testcases:     Optional, the names of the testcases, which sampled the covergroup. Default: ``None``.
		:param keyValuePairs: Optional, the key-value pairs, e.g. a tool's settings. Default: ``None``.
		:param parent:        Optional, the report containing the covergroup. Default: ``None``.
		:raises TypeError:    If parameter ``keyValuePairs`` isn't a mapping.
		:raises TypeError:    If parameter ``parent`` isn't of type :class:`FunctionalCoverageReport`.
		:raises ValueError:   If parameter ``name`` is ``None``.
		:raises TypeError:    If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError:   If parameter ``name`` is empty.
		:raises TypeError:    If parameter ``testcases`` isn't iterable.
		:raises TypeError:    If parameter ``testcases`` contains an element not of type :class:`str`.
		"""
		super().__init__(name, keyValuePairs=keyValuePairs, parent=parent)

		self._testcases = testcaseList = []
		self._coverpoints =              {}
		self._crosses =                  {}

		if testcases is not None:
			if not isinstance(testcases, Iterable):
				ex = TypeError("Parameter 'testcases' is not iterable.")
				ex.add_note(f"Got type '{getFullyQualifiedName(testcases)}'.")
				raise ex

			for testcase in testcases:
				if not isinstance(testcase, str):
					ex = TypeError("Parameter 'testcases' contains an element not of type 'str'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(testcase)}'.")
					raise ex

				testcaseList.append(testcase)

		if parent is not None:
			parent._AddElement(self)

	def _AddElement(self, item: Coverpoint | Cross) -> None:
		"""
		Add a coverpoint or a cross, which names this covergroup as its parent.

		:param item:                      The coverpoint or cross.
		:raises DuplicateCoverpointError: If this covergroup already contains a coverpoint or cross of the coverpoint's
		                                  name.
		:raises DuplicateCrossError:      If this covergroup already contains a cross or coverpoint of the cross' name.
		"""
		if isinstance(item, Coverpoint):
			items =     self._coverpoints
			exception = DuplicateCoverpointError
		else:
			items =     self._crosses
			exception = DuplicateCrossError

		if item._name in self._coverpoints or item._name in self._crosses:
			raise exception(f"Covergroup '{self._name}' already contains '{item._name}'.")

		items[item._name] = item

	def _SetRoot(self, root: Nullable[FunctionalCoverageReport]) -> None:
		"""
		Set the report's root of this covergroup, and of its coverpoints and crosses.

		:param root: The report's root, or ``None`` while the covergroup isn't part of a report.
		"""
		super()._SetRoot(root)
		for item in (*self._coverpoints.values(), *self._crosses.values()):
			item._SetRoot(root)

	@readonly
	def Testcases(self) -> list[str]:
		"""
		Read-only property to access the names of the testcases, which sampled the covergroup (:attr:`_testcases`).

		:returns: The names of the testcases; empty, if the report doesn't say.
		"""
		return self._testcases

	@readonly
	def Coverpoints(self) -> dict[str, Coverpoint]:
		"""
		Read-only property to access the coverpoints (:attr:`_coverpoints`).

		:returns: The coverpoints, by name.
		"""
		return self._coverpoints

	@readonly
	def CoverpointCount(self) -> int:
		"""
		Read-only property to return the number of coverpoints.

		:returns: The number of coverpoints.
		"""
		return len(self._coverpoints)

	@readonly
	def Crosses(self) -> dict[str, Cross]:
		"""
		Read-only property to access the crosses (:attr:`_crosses`).

		:returns: The crosses, by name.
		"""
		return self._crosses

	@readonly
	def CrossCount(self) -> int:
		"""
		Read-only property to return the number of crosses.

		:returns: The number of crosses.
		"""
		return len(self._crosses)

	def IterateCoverpoints(
		self,
		predicate: Nullable[Callable[[Coverpoint], bool]] = None
	) -> Generator[Coverpoint, None, None]:
		"""
		Iterate all or selected coverpoints.

		The coverpoints are iterated in the order they were added. If parameter ``predicate`` is not None, the given filter
		function is used to skip coverpoints in the generator.

		:param predicate: Optional, filter function accepting any coverpoint and returning a boolean. Default: ``None``.
		:returns:         A generator of the coverpoints.
		"""
		if predicate is None:
			yield from self._coverpoints.values()
		else:
			for coverpoint in self._coverpoints.values():
				if predicate(coverpoint):
					yield coverpoint

	def IterateCrosses(self, predicate: Nullable[Callable[[Cross], bool]] = None) -> Generator[Cross, None, None]:
		"""
		Iterate all or selected crosses.

		The crosses are iterated in the order they were added. If parameter ``predicate`` is not None, the given filter
		function is used to skip crosses in the generator.

		:param predicate: Optional, filter function accepting any cross and returning a boolean. Default: ``None``.
		:returns:         A generator of the crosses.
		"""
		if predicate is None:
			yield from self._crosses.values()
		else:
			for cross in self._crosses.values():
				if predicate(cross):
					yield cross

	def __repr__(self) -> str:
		"""
		Return a representation of the covergroup for debugging.

		A covergroup ``DelayCov`` of one coverpoint reads ``<Covergroup DelayCov: 1 coverpoints, 0 crosses>``.

		:returns: The covergroup's name, and its number of coverpoints and crosses.
		"""
		return f"<Covergroup {self._name}: {len(self._coverpoints)} coverpoints, {len(self._crosses)} crosses>"


@export
@abstractclass
class CoverageItem(BaseWithName):
	"""
	Base-class of the coverage items of a covergroup - coverpoints and crosses -: their bins.

	Its parent is the :class:`Covergroup` containing it.
	"""

	_PARENT_TYPE: ClassVar[tuple[type, ...]] = (Covergroup, )  #: A coverage item is in a covergroup.

	_bins: list[Bin]  #: The bins, in the order they were added.

	def __init__(
		self,
		name: str,
		*,
		keyValuePairs: Nullable[Mapping[Hashable, Any]] = None,
		parent: Nullable[Covergroup] = None
	) -> None:
		"""
		Initializes the key-value pairs, the parent, the name and the bins.

		:param name:          Name of the coverage item.
		:param keyValuePairs: Optional, the key-value pairs. Default: ``None``.
		:param parent:        Optional, the covergroup containing the coverage item. Default: ``None``.
		:raises TypeError:    If parameter ``keyValuePairs`` isn't a mapping.
		:raises TypeError:    If parameter ``parent`` isn't of type :class:`Covergroup`.
		:raises ValueError:   If parameter ``name`` is ``None``.
		:raises TypeError:    If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError:   If parameter ``name`` is empty.
		"""
		super().__init__(name, keyValuePairs=keyValuePairs, parent=parent)

		self._bins = []

	def _AddElement(self, coverageBin: Bin) -> None:
		"""
		Add a bin, which names this coverage item as its parent.

		:param coverageBin: The bin.
		"""
		self._bins.append(coverageBin)

	def _SetRoot(self, root: Nullable[FunctionalCoverageReport]) -> None:
		"""
		Set the report's root of this coverage item, and of its bins.

		:param root: The report's root, or ``None`` while the coverage item isn't part of a report.
		"""
		super()._SetRoot(root)
		for coverageBin in self._bins:
			coverageBin._SetRoot(root)

	@readonly
	def Bins(self) -> list[Bin]:
		"""
		Read-only property to access the bins (:attr:`_bins`).

		:returns: The bins, in the order they were added.
		"""
		return self._bins

	def IterateBins(self, predicate: Nullable[Callable[[Bin], bool]] = None) -> Generator[Bin, None, None]:
		"""
		Iterate all or selected bins.

		The bins are iterated in the order they were added. If parameter ``predicate`` is not None, the given filter
		function is used to skip bins in the generator.

		:param predicate: Optional, filter function accepting any bin and returning a boolean. Default: ``None``.
		:returns:         A generator of the bins.
		"""
		if predicate is None:
			yield from self._bins
		else:
			for coverageBin in self._bins:
				if predicate(coverageBin):
					yield coverageBin

	def __repr__(self) -> str:
		"""
		Return a representation of the coverage item for debugging.

		A coverpoint ``Length`` of two bins reads ``<Coverpoint Length: 2 bins>``.

		:returns: The coverage item's kind, name and number of bins.
		"""
		return f"<{self.__class__.__name__} {self._name}: {len(self._bins)} bins>"


@export
class Coverpoint(CoverageItem):
	"""
	A coverpoint: the bins counting the values of one sampled expression.

	Its bins are :class:`CoverpointBin` objects.
	"""

	_expression: Nullable[str]  #: The sampled expression, if the report says.

	def __init__(
		self,
		name: str,
		expression: Nullable[str] = None,
		keyValuePairs: Nullable[Mapping[Hashable, Any]] = None,
		*,
		parent: Nullable[Covergroup] = None
	) -> None:
		"""
		Initializes a coverpoint, and adds it to its covergroup.

		Its bins are added by creating them with this coverpoint as their parent.

		:param name:                      Name of the coverpoint.
		:param expression:                Optional, the sampled expression, e.g. a signal's name. Default: ``None``.
		:param keyValuePairs:             Optional, the key-value pairs. Default: ``None``.
		:param parent:                    Optional, the covergroup containing the coverpoint. Default: ``None``.
		:raises TypeError:                If parameter ``keyValuePairs`` isn't a mapping.
		:raises TypeError:                If parameter ``parent`` isn't of type :class:`Covergroup`.
		:raises ValueError:               If parameter ``name`` is ``None``.
		:raises TypeError:                If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError:               If parameter ``name`` is empty.
		:raises TypeError:                If parameter ``expression`` isn't of type :class:`str`.
		:raises ValueError:               If parameter ``expression`` is empty.
		:raises DuplicateCoverpointError: If the covergroup already contains a coverpoint or cross of this name.
		"""
		super().__init__(name, keyValuePairs=keyValuePairs, parent=parent)

		if expression is not None:
			if not isinstance(expression, str):
				ex = TypeError("Parameter 'expression' is not of type 'str'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(expression)}'.")
				raise ex
			elif expression == "":
				raise ValueError("Parameter 'expression' is empty.")

		self._expression = expression

		if parent is not None:
			parent._AddElement(self)

	@readonly
	def Expression(self) -> Nullable[str]:
		"""
		Read-only property to access the sampled expression (:attr:`_expression`).

		:returns: The expression, or ``None`` if the report doesn't say.
		"""
		return self._expression


@export
class Cross(CoverageItem):
	"""
	A cross: the bins counting combinations of values, one value per crossed item.

	Its bins are :class:`CrossBin` objects, each with one set of ranges per crossed item. The crossed items are named:
	the covergroup may contain them as coverpoints, as a SystemVerilog cross crosses coverpoints, or not, as an OSVVM
	coverage model has no coverpoints of its own.
	"""

	_crossedItems: list[str]  #: The names of the crossed items, e.g. of coverpoints, one per dimension.

	def __init__(
		self,
		name: str,
		crossedItems: Iterable[str],
		*,
		keyValuePairs: Nullable[Mapping[Hashable, Any]] = None,
		parent: Nullable[Covergroup] = None
	) -> None:
		"""
		Initializes a cross, and adds it to its covergroup.

		Its bins are added by creating them with this cross as their parent.

		:param name:                 Name of the cross.
		:param crossedItems:         The names of the crossed items, e.g. of coverpoints, one per dimension.
		:param keyValuePairs:        Optional, the key-value pairs. Default: ``None``.
		:param parent:               Optional, the covergroup containing the cross. Default: ``None``.
		:raises TypeError:           If parameter ``keyValuePairs`` isn't a mapping.
		:raises TypeError:           If parameter ``parent`` isn't of type :class:`Covergroup`.
		:raises ValueError:          If parameter ``name`` is ``None``.
		:raises TypeError:           If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError:          If parameter ``name`` is empty.
		:raises ValueError:          If parameter ``crossedItems`` is ``None``.
		:raises TypeError:           If parameter ``crossedItems`` isn't iterable.
		:raises TypeError:           If parameter ``crossedItems`` contains an element not of type :class:`str`.
		:raises ValueError:          If parameter ``crossedItems`` contains an empty name.
		:raises ValueError:          If parameter ``crossedItems`` contains less than two names.
		:raises DuplicateCrossError: If the covergroup already contains a cross or coverpoint of this name.
		"""
		super().__init__(name, keyValuePairs=keyValuePairs, parent=parent)

		if crossedItems is None:
			raise ValueError("Parameter 'crossedItems' is None.")
		elif not isinstance(crossedItems, Iterable):
			ex = TypeError("Parameter 'crossedItems' is not iterable.")
			ex.add_note(f"Got type '{getFullyQualifiedName(crossedItems)}'.")
			raise ex

		self._crossedItems = crossedItemList = []
		for crossedItem in crossedItems:
			if not isinstance(crossedItem, str):
				ex = TypeError("Parameter 'crossedItems' contains an element not of type 'str'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(crossedItem)}'.")
				raise ex
			elif crossedItem == "":
				raise ValueError("Parameter 'crossedItems' contains an empty name.")

			crossedItemList.append(crossedItem)

		if len(crossedItemList) < 2:
			ex = ValueError("Parameter 'crossedItems' contains less than two names.")
			ex.add_note(f"Got {len(crossedItemList)} names.")
			raise ex

		if parent is not None:
			parent._AddElement(self)

	def _AddElement(self, coverageBin: CrossBin) -> None:
		"""
		Add a cross bin, which names this cross as its parent.

		:param coverageBin:              The cross bin.
		:raises FunctionalCoverageError: If the cross bin has not one set of ranges per crossed item.
		"""
		if len(coverageBin._ranges) != len(self._crossedItems):
			ex = FunctionalCoverageError(f"Bin has not one set of ranges per crossed item of cross '{self._name}'.")
			ex.add_note(f"Got {len(coverageBin._ranges)} sets of ranges for {len(self._crossedItems)} crossed items.")
			raise ex from ValueError("Parameter 'ranges' doesn't match the crossed items.")

		self._bins.append(coverageBin)

	@readonly
	def CrossedItems(self) -> list[str]:
		"""
		Read-only property to access the names of the crossed items (:attr:`_crossedItems`).

		:returns: The names, one per dimension.
		"""
		return self._crossedItems

	@readonly
	def Dimensions(self) -> int:
		"""
		Read-only property to return the number of crossed items.

		:returns: The number of crossed items; at least ``2``.
		"""
		return len(self._crossedItems)


@export
@abstractclass
class Bin(Base):
	"""
	Base-class of the bins of a coverage item - coverpoint bins and cross bins -: a name, a kind, how often it was hit,
	and how often it must be hit to be covered.
	"""

	_name:    Nullable[str]  #: Name of the bin, if the report says.
	_kind:    BinKind        #: Kind of the bin.
	_count:   int            #: How often the bin was hit.
	_atLeast: int            #: How often the bin must be hit to be covered.

	def __init__(
		self,
		name: Nullable[str],
		kind: BinKind,
		count: int,
		atLeast: int = 1,
		*,
		keyValuePairs: Nullable[Mapping[Hashable, Any]] = None,
		parent: Nullable[CoverageItem] = None
	) -> None:
		"""
		Initializes the key-value pairs, the parent, the name, the kind and the counts.

		:param name:          Name of the bin; ``None``, if the report doesn't say.
		:param kind:          Kind of the bin.
		:param count:         How often the bin was hit.
		:param atLeast:       Optional, how often the bin must be hit to be covered. Default: ``1``.
		:param keyValuePairs: Optional, the key-value pairs. Default: ``None``.
		:param parent:        Optional, the coverage item containing the bin. Default: ``None``.
		:raises TypeError:    If parameter ``keyValuePairs`` isn't a mapping.
		:raises TypeError:    If parameter ``parent`` isn't of a type this class declares in :attr:`_PARENT_TYPE`.
		:raises TypeError:    If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError:   If parameter ``name`` is empty.
		:raises ValueError:   If parameter ``kind`` is ``None``.
		:raises TypeError:    If parameter ``kind`` isn't of type :class:`BinKind`.
		:raises ValueError:   If parameter ``count`` is ``None``.
		:raises TypeError:    If parameter ``count`` isn't of type :class:`int`.
		:raises ValueError:   If parameter ``count`` is negative.
		:raises ValueError:   If parameter ``atLeast`` is ``None``.
		:raises TypeError:    If parameter ``atLeast`` isn't of type :class:`int`.
		:raises ValueError:   If parameter ``atLeast`` is negative.
		"""
		super().__init__(keyValuePairs, parent=parent)

		if name is not None:
			if not isinstance(name, str):
				ex = TypeError("Parameter 'name' is not of type 'str'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(name)}'.")
				raise ex
			elif name == "":
				raise ValueError("Parameter 'name' is empty.")

		if kind is None:
			raise ValueError("Parameter 'kind' is None.")
		elif not isinstance(kind, BinKind):
			ex = TypeError("Parameter 'kind' is not of type 'BinKind'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(kind)}'.")
			raise ex

		for parameterName, value in (
			("count",   count),
			("atLeast", atLeast)
		):
			if value is None:
				raise ValueError(f"Parameter '{parameterName}' is None.")
			elif not isinstance(value, int) or isinstance(value, bool):
				ex = TypeError(f"Parameter '{parameterName}' is not of type 'int'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
				raise ex
			elif value < 0:
				ex = ValueError(f"Parameter '{parameterName}' is negative.")
				ex.add_note(f"Got value '{value}'.")
				raise ex

		self._name =    name
		self._kind =    kind
		self._count =   count
		self._atLeast = atLeast

	@readonly
	def Name(self) -> Nullable[str]:
		"""
		Read-only property to access the name of the bin (:attr:`_name`).

		:returns: The name, or ``None`` if the report doesn't say.
		"""
		return self._name

	@readonly
	def Kind(self) -> BinKind:
		"""
		Read-only property to access the kind of the bin (:attr:`_kind`).

		:returns: The kind.
		"""
		return self._kind

	@readonly
	def Count(self) -> int:
		"""
		Read-only property to access how often the bin was hit (:attr:`_count`).

		:returns: The number of hits.
		"""
		return self._count

	@readonly
	def AtLeast(self) -> int:
		"""
		Read-only property to access how often the bin must be hit to be covered (:attr:`_atLeast`).

		:returns: The number of hits required.
		"""
		return self._atLeast

	def __repr__(self) -> str:
		"""
		Return a representation of the bin for debugging.

		An unnamed bin hit 19 of 80 times reads ``<CoverpointBin (unnamed) Count: 19/80>``.

		:returns: The bin's class, name, kind and counts.
		"""
		name = "(unnamed)" if self._name is None else self._name
		return f"<{self.__class__.__name__} {name} {self._kind.name}: {self._count}/{self._atLeast}>"


@export
class CoverpointBin(Bin):
	"""
	A bin of a coverpoint: the ranges of values it counts.

	Its parent is the :class:`Coverpoint` containing it.
	"""

	_PARENT_TYPE: ClassVar[tuple[type, ...]] = (Coverpoint, )  #: A coverpoint bin is in a coverpoint.

	_ranges: list[ValueRange]  #: The ranges of values the bin counts.

	def __init__(
		self,
		name: Nullable[str],
		kind: BinKind,
		ranges: Iterable[ValueRange],
		count: int,
		atLeast: int = 1,
		*,
		keyValuePairs: Nullable[Mapping[Hashable, Any]] = None,
		parent: Nullable[Coverpoint] = None
	) -> None:
		"""
		Initializes a coverpoint bin, and adds it to its coverpoint.

		:param name:          Name of the bin; ``None``, if the report doesn't say.
		:param kind:          Kind of the bin.
		:param ranges:        The ranges of values the bin counts; empty for a default bin.
		:param count:         How often the bin was hit.
		:param atLeast:       Optional, how often the bin must be hit to be covered. Default: ``1``.
		:param keyValuePairs: Optional, the key-value pairs. Default: ``None``.
		:param parent:        Optional, the coverpoint containing the bin. Default: ``None``.
		:raises TypeError:    If parameter ``keyValuePairs`` isn't a mapping.
		:raises TypeError:    If parameter ``parent`` isn't of type :class:`Coverpoint`.
		:raises TypeError:    If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError:   If parameter ``name`` is empty.
		:raises ValueError:   If parameter ``kind`` is ``None``.
		:raises TypeError:    If parameter ``kind`` isn't of type :class:`BinKind`.
		:raises ValueError:   If parameter ``count`` is ``None``.
		:raises TypeError:    If parameter ``count`` isn't of type :class:`int`.
		:raises ValueError:   If parameter ``count`` is negative.
		:raises ValueError:   If parameter ``atLeast`` is ``None``.
		:raises TypeError:    If parameter ``atLeast`` isn't of type :class:`int`.
		:raises ValueError:   If parameter ``atLeast`` is negative.
		:raises ValueError:   If parameter ``ranges`` is ``None``.
		:raises TypeError:    If parameter ``ranges`` isn't iterable.
		:raises TypeError:    If parameter ``ranges`` contains an element not of type :class:`ValueRange`.
		"""
		super().__init__(name, kind, count, atLeast, keyValuePairs=keyValuePairs, parent=parent)

		if ranges is None:
			raise ValueError("Parameter 'ranges' is None.")
		elif not isinstance(ranges, Iterable):
			ex = TypeError("Parameter 'ranges' is not iterable.")
			ex.add_note(f"Got type '{getFullyQualifiedName(ranges)}'.")
			raise ex

		self._ranges = rangeList = []
		for valueRange in ranges:
			if not isinstance(valueRange, ValueRange):
				ex = TypeError("Parameter 'ranges' contains an element not of type 'ValueRange'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(valueRange)}'.")
				raise ex

			rangeList.append(valueRange)

		if parent is not None:
			parent._AddElement(self)

	@readonly
	def Ranges(self) -> list[ValueRange]:
		"""
		Read-only property to access the ranges of values the bin counts (:attr:`_ranges`).

		:returns: The ranges; empty for a default bin.
		"""
		return self._ranges


@export
class CrossBin(Bin):
	"""
	A bin of a cross: the combinations of values it counts, one set of ranges per crossed item.

	Its parent is the :class:`Cross` containing it.
	"""

	_PARENT_TYPE: ClassVar[tuple[type, ...]] = (Cross, )  #: A cross bin is in a cross.

	_ranges: list[tuple[ValueRange, ...]]  #: Per crossed item, the ranges of values the bin counts.

	def __init__(
		self,
		name: Nullable[str],
		kind: BinKind,
		ranges: Iterable[Iterable[ValueRange]],
		count: int,
		atLeast: int = 1,
		*,
		keyValuePairs: Nullable[Mapping[Hashable, Any]] = None,
		parent: Nullable[Cross] = None
	) -> None:
		"""
		Initializes a cross bin, and adds it to its cross.

		:param name:                     Name of the bin; ``None``, if the report doesn't say.
		:param kind:                     Kind of the bin.
		:param ranges:                   Per crossed item, the ranges of values the bin counts.
		:param count:                    How often the bin was hit.
		:param atLeast:                  Optional, how often the bin must be hit to be covered. Default: ``1``.
		:param keyValuePairs:            Optional, the key-value pairs. Default: ``None``.
		:param parent:                   Optional, the cross containing the bin. Default: ``None``.
		:raises TypeError:               If parameter ``keyValuePairs`` isn't a mapping.
		:raises TypeError:               If parameter ``parent`` isn't of type :class:`Cross`.
		:raises TypeError:               If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError:              If parameter ``name`` is empty.
		:raises ValueError:              If parameter ``kind`` is ``None``.
		:raises TypeError:               If parameter ``kind`` isn't of type :class:`BinKind`.
		:raises ValueError:              If parameter ``count`` is ``None``.
		:raises TypeError:               If parameter ``count`` isn't of type :class:`int`.
		:raises ValueError:              If parameter ``count`` is negative.
		:raises ValueError:              If parameter ``atLeast`` is ``None``.
		:raises TypeError:               If parameter ``atLeast`` isn't of type :class:`int`.
		:raises ValueError:              If parameter ``atLeast`` is negative.
		:raises ValueError:              If parameter ``ranges`` is ``None``.
		:raises TypeError:               If parameter ``ranges`` isn't iterable, or contains an element, which isn't.
		:raises TypeError:               If parameter ``ranges`` contains a range not of type :class:`ValueRange`.
		:raises FunctionalCoverageError: If parameter ``ranges`` has not one set of ranges per crossed item of the cross.
		"""
		super().__init__(name, kind, count, atLeast, keyValuePairs=keyValuePairs, parent=parent)

		if ranges is None:
			raise ValueError("Parameter 'ranges' is None.")
		elif not isinstance(ranges, Iterable):
			ex = TypeError("Parameter 'ranges' is not iterable.")
			ex.add_note(f"Got type '{getFullyQualifiedName(ranges)}'.")
			raise ex

		self._ranges = rangeList = []
		for itemRanges in ranges:
			if not isinstance(itemRanges, Iterable):
				ex = TypeError("Parameter 'ranges' contains an element, which isn't iterable.")
				ex.add_note(f"Got type '{getFullyQualifiedName(itemRanges)}'.")
				raise ex

			itemRanges = tuple(itemRanges)
			for valueRange in itemRanges:
				if not isinstance(valueRange, ValueRange):
					ex = TypeError("Parameter 'ranges' contains a range not of type 'ValueRange'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(valueRange)}'.")
					raise ex

			rangeList.append(itemRanges)

		if parent is not None:
			parent._AddElement(self)

	@readonly
	def Ranges(self) -> list[tuple[ValueRange, ...]]:
		"""
		Read-only property to access the ranges of values the bin counts, per crossed item (:attr:`_ranges`).

		:returns: Per crossed item, in the order of :attr:`Cross.CrossedItems`, the ranges of values.
		"""
		return self._ranges

