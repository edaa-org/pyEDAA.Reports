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

A bin is covered, when its count reaches its *at least* count. :meth:`FunctionalCoverageReport.Aggregate` computes the
counters of every coverage item, covergroup and of the report, and two ratios:

* :attr:`~BaseWithCoverage.BinCoverage` - the ratio of covered bins, weighted by the coverage items' and covergroups'
  weights, as SystemVerilog and UCIS compute coverage.
* :attr:`~BaseWithCoverage.HitCoverage` - the ratio of hits counted toward the bins' *at least* counts, as OSVVM
  computes coverage.

Every element has key-value pairs (:class:`~pyTooling.DataModel.KeyValuePairsMixin`) for data the model doesn't name,
e.g. a tool's settings.

A report format's model derives its document from :class:`Document`, which converts it to this model.
"""
from __future__            import annotations

from datetime              import timedelta
from enum                  import Enum
from pathlib               import Path
from typing                import Any, Callable, ClassVar, Generator, Hashable, Iterable, Mapping, Optional as Nullable

from pyTooling.Common      import getFullyQualifiedName
from pyTooling.DataModel   import KeyValuePairsMixin
from pyTooling.Decorators  import export, readonly
from pyTooling.Exceptions  import AlreadyInHierarchyError, DuplicateElementError
from pyTooling.MetaClasses import ExtendedType, abstractclass, abstractmethod

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

		:param other:      The other range.
		:returns:          ``True``, if both ranges have the same lowest and highest value.
		:raises TypeError: If parameter ``other`` isn't of type :class:`ValueRange`.
		"""
		if not isinstance(other, ValueRange):
			ex = TypeError("Second operand is not supported by == operator.")
			ex.add_note(f"Got type '{getFullyQualifiedName(other)}'.")
			ex.add_note("Supported types for second operand: ValueRange")
			raise ex

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
		:raises ValueError:   If parameter ``name`` is ``None``.
		:raises TypeError:    If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError:   If parameter ``name`` is empty.
		:raises TypeError:    If parameter ``keyValuePairs`` isn't a mapping.
		:raises TypeError:    If parameter ``parent`` isn't of a type this class declares in :attr:`_PARENT_TYPE`.
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
class BaseWithCoverage(BaseWithName):
	"""
	Base-class of the elements with coverage counters: the report, covergroups and coverage items.

	The counters are zero until :meth:`Aggregate` computed them. A covergroup weights the hit counters of its coverage
	items by their weights, the report those of its covergroups; the bin counters are plain sums.
	"""

	_binCount:         int    #: Number of bins counting toward the coverage.
	_coveredBinCount:  int    #: Number of bins counting toward the coverage, which reached their *at least* count.
	_ignoreBinCount:   int    #: Number of ignored bins.
	_illegalBinCount:  int    #: Number of illegal bins.
	_defaultBinCount:  int    #: Number of default bins.
	_illegalHitCount:  int    #: Number of hits of illegal bins.
	_hitCount:         int    #: Number of hits counted toward the *at least* counts, each bin's capped at its own.
	_requiredHitCount: int    #: Number of hits required by the *at least* counts.
	_binCoverage:      float  #: The weighted ratio of covered bins.

	def __init__(
		self,
		name: str,
		keyValuePairs: Nullable[Mapping[Hashable, Any]] = None,
		*,
		parent: Nullable[Base] = None
	) -> None:
		"""
		Initializes the key-value pairs, the parent, the name and the counters.

		:param name:          Name of the element.
		:param keyValuePairs: Optional, the key-value pairs. Default: ``None``.
		:param parent:        Optional, the element containing this one. Default: ``None``.
		:raises TypeError:    If parameter ``keyValuePairs`` isn't a mapping.
		:raises TypeError:    If parameter ``parent`` isn't of a type this class declares in :attr:`_PARENT_TYPE`.
		:raises ValueError:   If parameter ``name`` is ``None``.
		:raises TypeError:    If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError:   If parameter ``name`` is empty.
		"""
		super().__init__(name, keyValuePairs=keyValuePairs, parent=parent)

		self._ResetCounters()

	def _ResetCounters(self) -> None:
		"""
		Set the counters to zero, and the bin coverage to ``1.0``.
		"""
		self._binCount =         0
		self._coveredBinCount =  0
		self._ignoreBinCount =   0
		self._illegalBinCount =  0
		self._defaultBinCount =  0
		self._illegalHitCount =  0
		self._hitCount =         0
		self._requiredHitCount = 0
		self._binCoverage =      1.0

	def _AggregateCounters(self, others: Iterable[BaseWithGoal]) -> None:
		"""
		Set the counters to the sums of the counters of covergroups or coverage items, the hit counters weighted by their
		weights, and the bin coverage to the mean of theirs, weighted by their weights.

		:param others: The aggregated covergroups or coverage items.
		"""
		self._ResetCounters()
		weightedBinCoverage = 0.0
		totalWeight =         0
		for other in others:
			self._binCount +=         other._binCount
			self._coveredBinCount +=  other._coveredBinCount
			self._ignoreBinCount +=   other._ignoreBinCount
			self._illegalBinCount +=  other._illegalBinCount
			self._defaultBinCount +=  other._defaultBinCount
			self._illegalHitCount +=  other._illegalHitCount
			self._hitCount +=         other._weight * other._hitCount
			self._requiredHitCount += other._weight * other._requiredHitCount
			weightedBinCoverage +=    other._weight * other._binCoverage
			totalWeight +=            other._weight

		if totalWeight > 0:
			self._binCoverage = weightedBinCoverage / totalWeight

	@readonly
	def BinCount(self) -> int:
		"""
		Read-only property to access the number of bins counting toward the coverage (:attr:`_binCount`).

		:returns: The number of bins of kind :attr:`BinKind.Count`.
		"""
		return self._binCount

	@readonly
	def CoveredBinCount(self) -> int:
		"""
		Read-only property to access the number of bins counting toward the coverage, which reached their *at least* count
		(:attr:`_coveredBinCount`).

		:returns: The number of covered bins.
		"""
		return self._coveredBinCount

	@readonly
	def MissingBinCount(self) -> int:
		"""
		Read-only property to return the number of bins counting toward the coverage, which missed their *at least* count.

		:returns: :attr:`BinCount` minus :attr:`CoveredBinCount`.
		"""
		return self._binCount - self._coveredBinCount

	@readonly
	def IgnoreBinCount(self) -> int:
		"""
		Read-only property to access the number of ignored bins (:attr:`_ignoreBinCount`).

		:returns: The number of bins of kind :attr:`BinKind.Ignore`.
		"""
		return self._ignoreBinCount

	@readonly
	def IllegalBinCount(self) -> int:
		"""
		Read-only property to access the number of illegal bins (:attr:`_illegalBinCount`).

		:returns: The number of bins of kind :attr:`BinKind.Illegal`.
		"""
		return self._illegalBinCount

	@readonly
	def DefaultBinCount(self) -> int:
		"""
		Read-only property to access the number of default bins (:attr:`_defaultBinCount`).

		:returns: The number of bins of kind :attr:`BinKind.Default`.
		"""
		return self._defaultBinCount

	@readonly
	def IllegalHitCount(self) -> int:
		"""
		Read-only property to access the number of hits of illegal bins (:attr:`_illegalHitCount`).

		:returns: The sum of the counts of the illegal bins; ``0``, if no illegal value occurred.
		"""
		return self._illegalHitCount

	@readonly
	def HitCount(self) -> int:
		"""
		Read-only property to access the number of hits counted toward the *at least* counts (:attr:`_hitCount`).

		A bin's hits count up to its *at least* count, so extra hits of one bin don't make up for missing hits of another.

		:returns: The number of hits, weighted by the weights of the coverage items and covergroups.
		"""
		return self._hitCount

	@readonly
	def RequiredHitCount(self) -> int:
		"""
		Read-only property to access the number of hits required by the *at least* counts (:attr:`_requiredHitCount`).

		:returns: The sum of the *at least* counts, weighted by the weights of the coverage items and covergroups.
		"""
		return self._requiredHitCount

	@readonly
	def BinCoverage(self) -> float:
		"""
		Read-only property to access the ratio of covered bins (:attr:`_binCoverage`).

		It is the coverage as SystemVerilog and UCIS compute it: of a coverage item, its covered bins divided by its bins
		counting toward the coverage; of a covergroup, the mean of its coverage items' bin coverage, weighted by their
		weights; of the report, the same over the covergroups.

		:returns: The bin coverage in range 0.0..1.0; ``1.0`` if there is nothing to cover.
		"""
		return self._binCoverage

	@readonly
	def HitCoverage(self) -> float:
		"""
		Read-only property to return the ratio of hits counted toward the *at least* counts.

		It is the coverage as OSVVM computes it.

		:returns: :attr:`HitCount` divided by :attr:`RequiredHitCount`, in range 0.0..1.0; ``1.0`` if no hit is
		          required.
		"""
		return 1.0 if self._requiredHitCount == 0 else self._hitCount / self._requiredHitCount

	@abstractmethod
	def Aggregate(self) -> None:
		"""
		Compute the counters.
		"""


@export
class BaseWithGoal(BaseWithCoverage):
	"""
	Base-class of the elements with a weight and a goal: covergroups and coverage items.
	"""

	_weight: int    #: Weight in computing the coverage of the element containing this one.
	_goal:   float  #: Coverage goal, in percent.

	def __init__(
		self,
		name: str,
		weight: int = 1,
		goal: float = 100.0,
		keyValuePairs: Nullable[Mapping[Hashable, Any]] = None,
		*,
		parent: Nullable[Base] = None
	) -> None:
		"""
		Initializes the key-value pairs, the parent, the name, the counters, the weight and the goal.

		:param name:          Name of the element.
		:param weight:        Optional, weight in computing the coverage of the element containing this one; ``0``
		                      excludes it. Default: ``1``.
		:param goal:          Optional, coverage goal, in percent. Default: ``100.0``.
		:param keyValuePairs: Optional, the key-value pairs. Default: ``None``.
		:param parent:        Optional, the element containing this one. Default: ``None``.
		:raises TypeError:    If parameter ``keyValuePairs`` isn't a mapping.
		:raises TypeError:    If parameter ``parent`` isn't of a type this class declares in :attr:`_PARENT_TYPE`.
		:raises ValueError:   If parameter ``name`` is ``None``.
		:raises TypeError:    If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError:   If parameter ``name`` is empty.
		:raises ValueError:   If parameter ``weight`` is ``None``.
		:raises TypeError:    If parameter ``weight`` isn't of type :class:`int`.
		:raises ValueError:   If parameter ``weight`` is negative.
		:raises ValueError:   If parameter ``goal`` is ``None``.
		:raises TypeError:    If parameter ``goal`` isn't of type :class:`float` or :class:`int`.
		:raises ValueError:   If parameter ``goal`` is negative.
		"""
		super().__init__(name, keyValuePairs=keyValuePairs, parent=parent)

		if weight is None:
			raise ValueError("Parameter 'weight' is None.")
		elif not isinstance(weight, int) or isinstance(weight, bool):
			ex = TypeError("Parameter 'weight' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(weight)}'.")
			raise ex
		elif weight < 0:
			ex = ValueError("Parameter 'weight' is negative.")
			ex.add_note(f"Got value '{weight}'.")
			raise ex

		if goal is None:
			raise ValueError("Parameter 'goal' is None.")
		elif not isinstance(goal, (float, int)) or isinstance(goal, bool):
			ex = TypeError("Parameter 'goal' is not of type 'float' or 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(goal)}'.")
			raise ex
		elif goal < 0:
			ex = ValueError("Parameter 'goal' is negative.")
			ex.add_note(f"Got value '{goal}'.")
			raise ex

		self._weight = weight
		self._goal =   float(goal)

	@readonly
	def Weight(self) -> int:
		"""
		Read-only property to access the weight in computing the coverage of the element containing this one
		(:attr:`_weight`).

		:returns: The weight; ``0``, if the element is excluded from the coverage of the element containing it.
		"""
		return self._weight

	@readonly
	def Goal(self) -> float:
		"""
		Read-only property to access the coverage goal (:attr:`_goal`).

		:returns: The goal, in percent.
		"""
		return self._goal


@export
class FunctionalCoverageReport(BaseWithCoverage):
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
		:raises ValueError:   If parameter ``name`` is ``None``.
		:raises TypeError:    If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError:   If parameter ``name`` is empty.
		:raises TypeError:    If parameter ``keyValuePairs`` isn't a mapping.
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

	def Aggregate(self) -> None:
		"""
		Aggregate the covergroups, then sum their counters, weighted by their weights.
		"""
		for covergroup in self._covergroups:
			covergroup.Aggregate()

		self._AggregateCounters(self._covergroups)

	def __repr__(self) -> str:
		"""
		Return a representation of the report for debugging.

		A report ``TbStream_SendGetRandom1`` of 6 covergroups reads
		``<FunctionalCoverageReport TbStream_SendGetRandom1: 6 covergroups, bins 50.0%, hits 47.6%>``.

		:returns: The report's name, its number of covergroups and its coverage.
		"""
		return (
			f"<FunctionalCoverageReport {self._name}: {len(self._covergroups)} covergroups, bins {self.BinCoverage:.1%}, "
			f"hits {self.HitCoverage:.1%}>"
		)


@export
class Covergroup(BaseWithGoal):
	"""
	A covergroup: its coverage items - coverpoints and crosses -, each by name, its weight in the report's coverage, its
	goal, and the testcases, which sampled it.

	Its parent is the :class:`FunctionalCoverageReport`. Coverpoints and crosses share one namespace.
	"""

	_PARENT_TYPE: ClassVar[tuple[type, ...]] = (FunctionalCoverageReport, )  #: A covergroup is in a report.

	_testcases:   list[str]              #: The names of the testcases, which sampled the covergroup.
	_coverpoints: dict[str, Coverpoint]  #: The coverpoints, by name.
	_crosses:     dict[str, Cross]       #: The crosses, by name.

	def __init__(
		self,
		name: str,
		weight: int = 1,
		goal: float = 100.0,
		testcases: Nullable[Iterable[str]] = None,
		keyValuePairs: Nullable[Mapping[Hashable, Any]] = None,
		*,
		parent: Nullable[FunctionalCoverageReport] = None
	) -> None:
		"""
		Initializes a covergroup, and adds it to its report.

		Its coverpoints and crosses are added by creating them with this covergroup as their parent.

		:param name:          Name of the covergroup.
		:param weight:        Optional, weight in computing the report's coverage; ``0`` excludes it. Default: ``1``.
		:param goal:          Optional, coverage goal, in percent. Default: ``100.0``.
		:param testcases:     Optional, the names of the testcases, which sampled the covergroup. Default: ``None``.
		:param keyValuePairs: Optional, the key-value pairs, e.g. a tool's settings. Default: ``None``.
		:param parent:        Optional, the report containing the covergroup. Default: ``None``.
		:raises ValueError:   If parameter ``name`` is ``None``.
		:raises TypeError:    If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError:   If parameter ``name`` is empty.
		:raises ValueError:   If parameter ``weight`` is ``None``.
		:raises TypeError:    If parameter ``weight`` isn't of type :class:`int`.
		:raises ValueError:   If parameter ``weight`` is negative.
		:raises ValueError:   If parameter ``goal`` is ``None``.
		:raises TypeError:    If parameter ``goal`` isn't of type :class:`float` or :class:`int`.
		:raises ValueError:   If parameter ``goal`` is negative.
		:raises TypeError:    If parameter ``testcases`` isn't iterable.
		:raises TypeError:    If parameter ``testcases`` contains an element not of type :class:`str`.
		:raises TypeError:    If parameter ``keyValuePairs`` isn't a mapping.
		:raises TypeError:    If parameter ``parent`` isn't of type :class:`FunctionalCoverageReport`.
		"""
		super().__init__(name, weight, goal, keyValuePairs=keyValuePairs, parent=parent)

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

	def Aggregate(self) -> None:
		"""
		Aggregate the coverpoints and crosses, then sum their counters, weighted by their weights.
		"""
		items = (*self._coverpoints.values(), *self._crosses.values())
		for item in items:
			item.Aggregate()

		self._AggregateCounters(items)

	def __repr__(self) -> str:
		"""
		Return a representation of the covergroup for debugging.

		A covergroup ``DelayCov`` of one coverpoint reads ``<Covergroup DelayCov: 1 coverpoints, 0 crosses, bins 0.0%,
		hits 22.0%>``.

		:returns: The covergroup's name, its number of coverpoints and crosses, and its coverage.
		"""
		return (
			f"<Covergroup {self._name}: {len(self._coverpoints)} coverpoints, {len(self._crosses)} crosses, "
			f"bins {self.BinCoverage:.1%}, hits {self.HitCoverage:.1%}>"
		)


@export
@abstractclass
class CoverageItem(BaseWithGoal):
	"""
	Base-class of the coverage items of a covergroup - coverpoints and crosses -: their bins, their weight in the
	covergroup's coverage and their goal.

	Its parent is the :class:`Covergroup` containing it.
	"""

	_PARENT_TYPE: ClassVar[tuple[type, ...]] = (Covergroup, )  #: A coverage item is in a covergroup.

	_bins: list[Bin]  #: The bins, in the order they were added.

	def __init__(
		self,
		name: str,
		weight: int = 1,
		goal: float = 100.0,
		keyValuePairs: Nullable[Mapping[Hashable, Any]] = None,
		*,
		parent: Nullable[Covergroup] = None
	) -> None:
		"""
		Initializes the key-value pairs, the parent, the name, the counters, the weight, the goal and the bins.

		:param name:          Name of the coverage item.
		:param weight:        Optional, weight in computing the covergroup's coverage; ``0`` excludes it. Default: ``1``.
		:param goal:          Optional, coverage goal, in percent. Default: ``100.0``.
		:param keyValuePairs: Optional, the key-value pairs. Default: ``None``.
		:param parent:        Optional, the covergroup containing the coverage item. Default: ``None``.
		:raises ValueError:   If parameter ``name`` is ``None``.
		:raises TypeError:    If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError:   If parameter ``name`` is empty.
		:raises TypeError:    If parameter ``keyValuePairs`` isn't a mapping.
		:raises TypeError:    If parameter ``parent`` isn't of type :class:`Covergroup`.
		:raises ValueError:   If parameter ``weight`` is ``None``.
		:raises TypeError:    If parameter ``weight`` isn't of type :class:`int`.
		:raises ValueError:   If parameter ``weight`` is negative.
		:raises ValueError:   If parameter ``goal`` is ``None``.
		:raises TypeError:    If parameter ``goal`` isn't of type :class:`float` or :class:`int`.
		:raises ValueError:   If parameter ``goal`` is negative.
		"""
		super().__init__(name, weight, goal, keyValuePairs=keyValuePairs, parent=parent)

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

	def Aggregate(self) -> None:
		"""
		Compute the counters and the bin coverage from the bins.
		"""
		self._ResetCounters()
		for coverageBin in self._bins:
			kind = coverageBin._kind
			if kind is BinKind.Count:
				self._binCount +=         1
				self._requiredHitCount += coverageBin._atLeast
				if coverageBin._count >= coverageBin._atLeast:
					self._coveredBinCount += 1
					self._hitCount +=        coverageBin._atLeast
				else:
					self._hitCount +=        coverageBin._count
			elif kind is BinKind.Ignore:
				self._ignoreBinCount += 1
			elif kind is BinKind.Illegal:
				self._illegalBinCount += 1
				self._illegalHitCount += coverageBin._count
			else:
				self._defaultBinCount += 1

		if self._binCount > 0:
			self._binCoverage = self._coveredBinCount / self._binCount

	def __repr__(self) -> str:
		"""
		Return a representation of the coverage item for debugging.

		A coverpoint ``Length`` with one of two bins covered reads ``<Coverpoint Length: 1/2 bins, hits 60.0%>``.

		:returns: The coverage item's kind, name, its covered and counting bins, and its hit coverage.
		"""
		return (
			f"<{self.__class__.__name__} {self._name}: {self._coveredBinCount}/{self._binCount} bins, "
			f"hits {self.HitCoverage:.1%}>"
		)


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
		weight: int = 1,
		goal: float = 100.0,
		keyValuePairs: Nullable[Mapping[Hashable, Any]] = None,
		*,
		parent: Nullable[Covergroup] = None
	) -> None:
		"""
		Initializes a coverpoint, and adds it to its covergroup.

		Its bins are added by creating them with this coverpoint as their parent.

		:param name:                      Name of the coverpoint.
		:param expression:                Optional, the sampled expression, e.g. a signal's name. Default: ``None``.
		:param weight:                    Optional, weight in computing the covergroup's coverage; ``0`` excludes it.
		                                  Default: ``1``.
		:param goal:                      Optional, coverage goal, in percent. Default: ``100.0``.
		:param keyValuePairs:             Optional, the key-value pairs. Default: ``None``.
		:param parent:                    Optional, the covergroup containing the coverpoint. Default: ``None``.
		:raises ValueError:               If parameter ``name`` is ``None``.
		:raises TypeError:                If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError:               If parameter ``name`` is empty.
		:raises ValueError:               If parameter ``weight`` is ``None``.
		:raises TypeError:                If parameter ``weight`` isn't of type :class:`int`.
		:raises ValueError:               If parameter ``weight`` is negative.
		:raises ValueError:               If parameter ``goal`` is ``None``.
		:raises TypeError:                If parameter ``goal`` isn't of type :class:`float` or :class:`int`.
		:raises ValueError:               If parameter ``goal`` is negative.
		:raises TypeError:                If parameter ``expression`` isn't of type :class:`str`.
		:raises ValueError:               If parameter ``expression`` is empty.
		:raises TypeError:                If parameter ``keyValuePairs`` isn't a mapping.
		:raises TypeError:                If parameter ``parent`` isn't of type :class:`Covergroup`.
		:raises DuplicateCoverpointError: If the covergroup already contains a coverpoint or cross of this name.
		"""
		super().__init__(name, weight, goal, keyValuePairs=keyValuePairs, parent=parent)

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
		weight: int = 1,
		goal: float = 100.0,
		keyValuePairs: Nullable[Mapping[Hashable, Any]] = None,
		*,
		parent: Nullable[Covergroup] = None
	) -> None:
		"""
		Initializes a cross, and adds it to its covergroup.

		Its bins are added by creating them with this cross as their parent.

		:param name:                 Name of the cross.
		:param crossedItems:         The names of the crossed items, e.g. of coverpoints, one per dimension.
		:param weight:               Optional, weight in computing the covergroup's coverage; ``0`` excludes it. Default:
		                             ``1``.
		:param goal:                 Optional, coverage goal, in percent. Default: ``100.0``.
		:param keyValuePairs:        Optional, the key-value pairs. Default: ``None``.
		:param parent:               Optional, the covergroup containing the cross. Default: ``None``.
		:raises ValueError:          If parameter ``name`` is ``None``.
		:raises TypeError:           If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError:          If parameter ``name`` is empty.
		:raises ValueError:          If parameter ``weight`` is ``None``.
		:raises TypeError:           If parameter ``weight`` isn't of type :class:`int`.
		:raises ValueError:          If parameter ``weight`` is negative.
		:raises ValueError:          If parameter ``goal`` is ``None``.
		:raises TypeError:           If parameter ``goal`` isn't of type :class:`float` or :class:`int`.
		:raises ValueError:          If parameter ``goal`` is negative.
		:raises ValueError:          If parameter ``crossedItems`` is ``None``.
		:raises TypeError:           If parameter ``crossedItems`` isn't iterable.
		:raises TypeError:           If parameter ``crossedItems`` contains an element not of type :class:`str`.
		:raises ValueError:          If parameter ``crossedItems`` contains an empty name.
		:raises ValueError:          If parameter ``crossedItems`` contains less than two names.
		:raises TypeError:           If parameter ``keyValuePairs`` isn't a mapping.
		:raises TypeError:           If parameter ``parent`` isn't of type :class:`Covergroup`.
		:raises DuplicateCrossError: If the covergroup already contains a cross or coverpoint of this name.
		"""
		super().__init__(name, weight, goal, keyValuePairs=keyValuePairs, parent=parent)

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
		keyValuePairs: Nullable[Mapping[Hashable, Any]] = None,
		*,
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
		:raises TypeError:    If parameter ``keyValuePairs`` isn't a mapping.
		:raises TypeError:    If parameter ``parent`` isn't of a type this class declares in :attr:`_PARENT_TYPE`.
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

	@readonly
	def IsCovered(self) -> bool:
		"""
		Read-only property to return whether the bin counts toward the coverage and reached its *at least* count.

		:returns: ``True``, if the bin is of kind :attr:`BinKind.Count` and :attr:`Count` is at least :attr:`AtLeast`.
		"""
		return self._kind is BinKind.Count and self._count >= self._atLeast

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
		keyValuePairs: Nullable[Mapping[Hashable, Any]] = None,
		*,
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
		:raises TypeError:    If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError:   If parameter ``name`` is empty.
		:raises ValueError:   If parameter ``kind`` is ``None``.
		:raises TypeError:    If parameter ``kind`` isn't of type :class:`BinKind`.
		:raises ValueError:   If parameter ``ranges`` is ``None``.
		:raises TypeError:    If parameter ``ranges`` isn't iterable.
		:raises TypeError:    If parameter ``ranges`` contains an element not of type :class:`ValueRange`.
		:raises ValueError:   If parameter ``count`` is ``None``.
		:raises TypeError:    If parameter ``count`` isn't of type :class:`int`.
		:raises ValueError:   If parameter ``count`` is negative.
		:raises ValueError:   If parameter ``atLeast`` is ``None``.
		:raises TypeError:    If parameter ``atLeast`` isn't of type :class:`int`.
		:raises ValueError:   If parameter ``atLeast`` is negative.
		:raises TypeError:    If parameter ``keyValuePairs`` isn't a mapping.
		:raises TypeError:    If parameter ``parent`` isn't of type :class:`Coverpoint`.
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
		keyValuePairs: Nullable[Mapping[Hashable, Any]] = None,
		*,
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
		:raises TypeError:               If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError:              If parameter ``name`` is empty.
		:raises ValueError:              If parameter ``kind`` is ``None``.
		:raises TypeError:               If parameter ``kind`` isn't of type :class:`BinKind`.
		:raises ValueError:              If parameter ``ranges`` is ``None``.
		:raises TypeError:               If parameter ``ranges`` isn't iterable, or contains an element, which isn't.
		:raises TypeError:               If parameter ``ranges`` contains a range not of type :class:`ValueRange`.
		:raises FunctionalCoverageError: If parameter ``ranges`` has not one set of ranges per crossed item of the cross.
		:raises ValueError:              If parameter ``count`` is ``None``.
		:raises TypeError:               If parameter ``count`` isn't of type :class:`int`.
		:raises ValueError:              If parameter ``count`` is negative.
		:raises ValueError:              If parameter ``atLeast`` is ``None``.
		:raises TypeError:               If parameter ``atLeast`` isn't of type :class:`int`.
		:raises ValueError:              If parameter ``atLeast`` is negative.
		:raises TypeError:               If parameter ``keyValuePairs`` isn't a mapping.
		:raises TypeError:               If parameter ``parent`` isn't of type :class:`Cross`.
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


@export
@abstractclass
class Document(metaclass=ExtendedType, slots=True):
	"""
	A functional coverage report file, which is read in two steps: analyzed, then converted.

	A format's document derives from this class and mixes in the root of the format's model.
	"""

	_path:               Path                 #: Path to the report file.
	_analysisDuration:   Nullable[timedelta]  #: Duration of :meth:`Analyze`, or ``None`` before it ran.
	_conversionDuration: Nullable[timedelta]  #: Duration of :meth:`Convert`, or ``None`` before it ran.

	def __init__(self, reportFile: Path) -> None:
		"""
		Initializes the report file.

		:param reportFile:  Path to the report file.
		:raises ValueError: If parameter ``reportFile`` is ``None``.
		:raises TypeError:  If parameter ``reportFile`` isn't of type :class:`~pathlib.Path`.
		"""
		if reportFile is None:
			raise ValueError("Parameter 'reportFile' is None.")
		elif not isinstance(reportFile, Path):
			ex = TypeError("Parameter 'reportFile' is not of type 'Path'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(reportFile)}'.")
			raise ex

		self._path =               reportFile
		self._analysisDuration =   None
		self._conversionDuration = None

	@readonly
	def ReportFile(self) -> Path:
		"""
		Read-only property to access the path to the report file (:attr:`_path`).

		:returns: The report file's path.
		"""
		return self._path

	@readonly
	def AnalysisDuration(self) -> Nullable[timedelta]:
		"""
		Read-only property to access the duration of :meth:`Analyze`: reading, parsing and validating the file
		(:attr:`_analysisDuration`).

		:returns: The duration, or ``None`` if the file wasn't analyzed yet.
		"""
		return self._analysisDuration

	@readonly
	def ModelConversionDuration(self) -> Nullable[timedelta]:
		"""
		Read-only property to access the duration of :meth:`Convert`: building the report format's model
		(:attr:`_conversionDuration`).

		:returns: The duration, or ``None`` if the content wasn't converted yet.
		"""
		return self._conversionDuration

	@abstractmethod
	def Analyze(self) -> None:
		"""
		Read, parse and validate the report file.
		"""

	@abstractmethod
	def Convert(self) -> None:
		"""
		Convert the analyzed content to the report format's model.
		"""

	@abstractmethod
	def ConvertToFunctionalCoverageReport(self) -> FunctionalCoverageReport:
		"""
		Convert the report format's model to the functional coverage model, and aggregate it.

		:returns: The report's root of the functional coverage model.
		"""
