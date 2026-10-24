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
Abstract data model of functional coverage: covergroups and their coverpoints.

The model is tool-neutral: it follows the terms of SystemVerilog covergroups and of the Accellera UCIS standard, and
an OSVVM coverage model maps to it too.

* The root, :class:`FunctionalCoverageReport`, holds the covergroups of a report, e.g. of a testcase.
* A :class:`Covergroup` holds its coverage items by name: :class:`Coverpoint` objects - one sampled value each.

Every element has key-value pairs (:class:`~pyTooling.DataModel.KeyValuePairsMixin`) for data the model doesn't name,
e.g. a tool's settings.
"""
from __future__            import annotations

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
	"""The exception is raised when a covergroup already contains a coverpoint of the same name."""


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

		The parent doesn't list the element yet: the class setting the fields the parent checks - a name - adds it with
		``parent._AddElement(self)``.

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
		:raises DuplicateCoverpointError:               If the assigned covergroup already contains a coverpoint of the
		                                                coverpoint's name.
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
		*,
		keyValuePairs: Nullable[Mapping[Hashable, Any]] = None,
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

	def __init__(self, name: str, *, keyValuePairs: Nullable[Mapping[Hashable, Any]] = None) -> None:
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
	A covergroup: its coverage items - coverpoints -, each by name, and the testcases, which sampled it.

	Its parent is the :class:`FunctionalCoverageReport`.
	"""

	_PARENT_TYPE: ClassVar[tuple[type, ...]] = (FunctionalCoverageReport, )  #: A covergroup is in a report.

	_testcases:   list[str]              #: The names of the testcases, which sampled the covergroup.
	_coverpoints: dict[str, Coverpoint]  #: The coverpoints, by name.

	def __init__(
		self,
		name: str,
		testcases: Nullable[Iterable[str]] = None,
		*,
		keyValuePairs: Nullable[Mapping[Hashable, Any]] = None,
		parent: Nullable[FunctionalCoverageReport] = None
	) -> None:
		"""
		Initializes a covergroup, and adds it to its report.

		Its coverpoints are added by creating them with this covergroup as their parent.

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

	def _AddElement(self, coverpoint: Coverpoint) -> None:
		"""
		Add a coverpoint, which names this covergroup as its parent.

		:param coverpoint:                The coverpoint.
		:raises DuplicateCoverpointError: If this covergroup already contains a coverpoint of the coverpoint's name.
		"""
		if coverpoint._name in self._coverpoints:
			raise DuplicateCoverpointError(f"Covergroup '{self._name}' already contains '{coverpoint._name}'.")

		self._coverpoints[coverpoint._name] = coverpoint

	def _SetRoot(self, root: Nullable[FunctionalCoverageReport]) -> None:
		"""
		Set the report's root of this covergroup, and of its coverpoints.

		:param root: The report's root, or ``None`` while the covergroup isn't part of a report.
		"""
		super()._SetRoot(root)
		for coverpoint in self._coverpoints.values():
			coverpoint._SetRoot(root)

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

	def __repr__(self) -> str:
		"""
		Return a representation of the covergroup for debugging.

		A covergroup ``DelayCov`` of one coverpoint reads ``<Covergroup DelayCov: 1 coverpoints>``.

		:returns: The covergroup's name and its number of coverpoints.
		"""
		return f"<Covergroup {self._name}: {len(self._coverpoints)} coverpoints>"


@export
@abstractclass
class CoverageItem(BaseWithName):
	"""
	Base-class of the coverage items of a covergroup: coverpoints.

	Its parent is the :class:`Covergroup` containing it.
	"""

	_PARENT_TYPE: ClassVar[tuple[type, ...]] = (Covergroup, )  #: A coverage item is in a covergroup.

	def __repr__(self) -> str:
		"""
		Return a representation of the coverage item for debugging.

		A coverpoint ``Length`` reads ``<Coverpoint Length>``.

		:returns: The coverage item's kind and name.
		"""
		return f"<{self.__class__.__name__} {self._name}>"


@export
class Coverpoint(CoverageItem):
	"""
	A coverpoint: one sampled expression.
	"""

	_expression: Nullable[str]  #: The sampled expression, if the report says.

	def __init__(
		self,
		name: str,
		expression: Nullable[str] = None,
		*,
		keyValuePairs: Nullable[Mapping[Hashable, Any]] = None,
		parent: Nullable[Covergroup] = None
	) -> None:
		"""
		Initializes a coverpoint, and adds it to its covergroup.

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
		:raises DuplicateCoverpointError: If the covergroup already contains a coverpoint of this name.
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

