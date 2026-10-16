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
Abstract data model of risk management: a risk register of risks, their implications and the mitigations against
them.

The root, :class:`RiskManagement`, holds every :class:`Risk`, :class:`Implication` and :class:`Mitigation` by ID. A risk
references its implications - what happens, if it occurs - and its mitigations - what reduces it. Implications and
mitigations are elements of their own, so several risks can share one, e.g. a mitigation reducing two risks.

The implications form a chain: an implication can have implications of its own, and a mitigation can have
implications too: its side effects. Both are the second-order implications of a risk. An implication can be mitigated
like a risk.

Risks of a register relate to each other by a :class:`Link`: from a source risk to a destination risk, of a
:class:`LinkKind`, e.g. one risk causing another. A link has no parent: its risks and the register list it.

A risk's :attr:`~Risk.Score` - the rank of its probability times the rank of its impact - classifies it by a
:class:`RiskLevel`. A risk names its owner - a :class:`~pyEDAA.Reports.Person` the register refers to - and the date of
its next review; a mitigation states its :class:`MitigationKind` and its :class:`MitigationState`.

Every element has key-value pairs (:class:`~pyEDAA.Reports.KeyValuePairsMixin`) for data the model doesn't name.
"""
from __future__            import annotations

from datetime              import datetime
from typing                import Any, Callable, ClassVar, Generator, Iterable, Mapping, Optional as Nullable

from pyTooling.Common      import getFullyQualifiedName, StringEnum
from pyTooling.Decorators  import export, readonly
from pyTooling.MetaClasses import ExtendedType
from pyTooling.Versioning  import SemanticVersion

from pyEDAA.Reports        import KeyValuePairsMixin, Person, ReportException


@export
class RiskManagementError(ReportException):
	"""Base-exception of the risk management model."""


@export
class Probability(StringEnum):
	"""
	The probability of a risk to occur.
	"""

	Low =      "low"       #: Identified, but sleeping.
	Medium =   "medium"    #: Likely to occur soon.
	High =     "high"      #: Very likely to occur.
	Occurred = "occurred"  #: Occurred: the risk is active and causes heavy effects.

	__RANKS: ClassVar[dict[str, int]] = {
		Low:      1,
		Medium:   2,
		High:     3,
		Occurred: 4,
	}  #: The rank of each probability, by the probability's value.

	@readonly
	def Rank(self) -> int:
		"""
		Read-only property to return the probability's rank on its ordinal scale.

		:returns: The rank in range 1..4; ``1`` is the lowest probability.
		"""
		return self.__RANKS[self]


@export
class Impact(StringEnum):
	"""
	The impact of a risk, if it occurs, as the delay it causes.
	"""

	Low =      "low"       #: A delay of a few days.
	Medium =   "medium"    #: A delay of multiple days.
	High =     "high"      #: A delay of a few weeks.
	Critical = "critical"  #: A delay of multiple weeks.

	__RANKS: ClassVar[dict[str, int]] = {
		Low:      1,
		Medium:   2,
		High:     3,
		Critical: 4,
	}  #: The rank of each impact, by the impact's value.

	@readonly
	def Rank(self) -> int:
		"""
		Read-only property to return the impact's rank on its ordinal scale.

		:returns: The rank in range 1..4; ``1`` is the lowest impact.
		"""
		return self.__RANKS[self]


@export
class RiskLevel(StringEnum):
	"""
	The level of a risk, classified by its score: the rank of its probability times the rank of its impact.

	.. code-block:: text

	                         Impact:  low  medium  high  critical
	   Probability: low                 1       2     3         4
	                medium              2       4     6         8
	                high                3       6     9        12
	                occurred            4       8    12        16
	"""

	Low =      "low"       #: A score of 1 to 3.
	Medium =   "medium"    #: A score of 4 to 6.
	High =     "high"      #: A score of 8 or 9.
	Critical = "critical"  #: A score of 12 to 16.


@export
class RiskState(StringEnum):
	"""
	The state of a risk in its life cycle.

	A risk ends either *solved* - its mitigations removed it - or *closed* - it isn't tracked anymore, without being
	solved.
	"""

	Open =    "open"     #: Identified and tracked.
	OnHold =  "on-hold"  #: Tracking is paused, e.g. until a decision is made.
	Closed =  "closed"   #: Not tracked anymore, without being solved, e.g. accepted, obsolete or its time has passed.
	Solved =  "solved"   #: Removed by its mitigations: it can't occur anymore.

	DEFAULT = Open       #: The state of a newly identified risk.


@export
class LinkKind(StringEnum):
	"""
	The relationship a :class:`Link` states from its source risk to its destination risk.
	"""

	Causes =     "causes"      #: The source, if it occurs, causes the destination to occur.
	Amplifies =  "amplifies"   #: The source, if it occurs, raises the probability or the impact of the destination.
	DependsOn =  "depends-on"  #: The source can only occur, if the destination occurred.
	Duplicates = "duplicates"  #: The source describes the same risk as the destination.
	Related =    "related"     #: The source relates to the destination in another way.

	DEFAULT =    Related       #: The relationship of a link, which states no other.


@export
class MitigationKind(StringEnum):
	"""
	The way a mitigation reduces a risk or an implication.
	"""

	Avoid =       "avoid"        #: Removes the cause, so the risk can't occur.
	Prevent =     "prevent"      #: Reduces the probability the risk occurs.
	Contingency = "contingency"  #: Reduces the impact: a plan applied, when the risk occurs.
	Transfer =    "transfer"     #: Moves the impact to a third party, e.g. by a contract or an insurance.

	DEFAULT =     Prevent        #: The way of a mitigation, which states no other.


@export
class MitigationState(StringEnum):
	"""
	The state of a mitigation: whether it is applied.

	A mitigation *on hold* waits to be planned; a new mitigation is *planned*.
	"""

	OnHold =    "on-hold"    #: Proposed, but waiting to be planned, e.g. for a decision or a budget.
	Planned =   "planned"    #: Decided, but not started.
	Active =    "active"     #: Being applied.
	Done =      "done"       #: Applied completely.
	Abandoned = "abandoned"  #: Not applied anymore, e.g. too expensive or without effect.

	DEFAULT =   Planned      #: The state of a newly decided mitigation.


@export
class Base(KeyValuePairsMixin, metaclass=ExtendedType, slots=True):
	"""
	Base-class of every element of the risk management model: key-value pairs, a reference to the risk register
	containing the element, and to the register's root.
	"""

	_parent: Nullable[RiskManagement]  #: The risk register containing this element, or ``None``.
	_root:   Nullable[RiskManagement]  #: The risk register's root, or ``None`` while the element isn't part of one.

	def __init__(
		self,
		keyValuePairs: Nullable[Mapping[str, Any]] = None,
		*,
		parent: Nullable[RiskManagement] = None
	) -> None:
		"""
		Initializes an element with its key-value pairs, its parent and the parent's root.

		The parent doesn't list the element yet: the class setting the fields the parent checks - an ID and the referenced
		elements - adds it with ``parent._AddElement(self)``.

		:param keyValuePairs: Optional, the key-value pairs. Default: ``None``.
		:param parent:        Optional, the risk register containing this element. Default: ``None``.
		:raises TypeError:    If parameter ``keyValuePairs`` isn't a mapping.
		:raises TypeError:    If parameter ``keyValuePairs`` contains a key not of type :class:`str`.
		:raises ValueError:   If parameter ``keyValuePairs`` contains an empty key.
		:raises TypeError:    If parameter ``parent`` isn't of type :class:`RiskManagement`.
		"""
		super().__init__(keyValuePairs)

		if parent is None:
			self._parent = None
			self._root =   None
		elif not isinstance(parent, RiskManagement):
			ex = TypeError(f"Parameter 'parent' is not of type 'RiskManagement'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex
		else:
			self._parent = parent
			self._root =   parent._root

	@property
	def Parent(self) -> Nullable[RiskManagement]:
		"""
		Property to access the risk register containing this element (:attr:`_parent`).

		Assigning a risk register adds this element to it, and sets the register's root as the root of this element.

		:returns:                    The parent, or ``None``.
		:raises ValueError:          If ``None`` is assigned.
		:raises TypeError:           If the assigned parent isn't of type :class:`RiskManagement`.
		:raises TypeError:           If a parent is assigned to a :class:`RiskManagement`, which has no parent.
		:raises RiskManagementError: If the element is already part of a risk register.
		:raises RiskManagementError: If the risk register already contains an element of the same kind and ID.
		:raises ValueError:          If the element references an element, which isn't part of the risk register. |br|
		                             Add the referenced elements to the risk register first.
		"""
		return self._parent

	@Parent.setter
	def Parent(self, parent: RiskManagement) -> None:
		if parent is None:
			raise ValueError(f"Parameter 'parent' is None.")
		elif not isinstance(parent, RiskManagement):
			ex = TypeError(f"Parameter 'parent' is not of type 'RiskManagement'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex
		elif self._parent is not None:
			ex = RiskManagementError(f"Element is already part of a risk register.")
			ex.add_note(f"Got element '{self!r}'.")
			raise ex

		parent._AddElement(self)
		self._parent = parent
		self._root =   parent._root

	@readonly
	def Root(self) -> Nullable[RiskManagement]:
		"""
		Read-only property to access the risk register's root (:attr:`_root`).

		The root is maintained by :attr:`Parent`: assigning a parent sets it.

		:returns: The root, or ``None`` while the element isn't part of a risk register.
		"""
		return self._root


@export
class RiskManagement(Base):
	"""
	The risk register: every risk, implication and mitigation, each by its ID, the links between the risks, the persons
	it refers to, the register's version and its optional name.

	It is its own root, and has no parent. An element joins it by naming it as its parent, in the element's constructor
	or by :attr:`~Base.Parent`.
	"""

	_version:      SemanticVersion         #: The version of the risk register.
	_name:         Nullable[str]           #: The name of the risk register, if given.
	_risks:        dict[str, Risk]         #: The risks, by ID.
	_implications: dict[str, Implication]  #: The implications, by ID.
	_mitigations:  dict[str, Mitigation]   #: The mitigations, by ID.
	_links:        list[Link]              #: The links between the risks, in the order they were added.
	_persons:      dict[str, Person]       #: The persons the register refers to, e.g. as risk owners, by user ID.

	def __init__(
		self,
		version: SemanticVersion,
		name: Nullable[str] = None,
		keyValuePairs: Nullable[Mapping[str, Any]] = None
	) -> None:
		"""
		Initializes an empty risk register of a version.

		:param version:       The version of the risk register.
		:param name:          Optional, the name of the risk register, e.g. the project's name. Default: ``None``.
		:param keyValuePairs: Optional, the key-value pairs. Default: ``None``.
		:raises TypeError:    If parameter ``keyValuePairs`` isn't a mapping.
		:raises TypeError:    If parameter ``keyValuePairs`` contains a key not of type :class:`str`.
		:raises ValueError:   If parameter ``keyValuePairs`` contains an empty key.
		:raises ValueError:   If parameter ``version`` is ``None``.
		:raises TypeError:    If parameter ``version`` isn't of type :class:`~pyTooling.Versioning.SemanticVersion`.
		:raises TypeError:    If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError:   If parameter ``name`` is empty.
		"""
		super().__init__(keyValuePairs)

		if version is None:
			raise ValueError(f"Parameter 'version' is None.")
		elif not isinstance(version, SemanticVersion):
			ex = TypeError(f"Parameter 'version' is not of type 'SemanticVersion'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(version)}'.")
			raise ex

		if name is not None:
			if not isinstance(name, str):
				ex = TypeError(f"Parameter 'name' is not of type 'str'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(name)}'.")
				raise ex
			elif name == "":
				raise ValueError(f"Parameter 'name' is empty.")

		self._root =         self
		self._version =      version
		self._name =         name
		self._risks =        {}
		self._implications = {}
		self._mitigations =  {}
		self._links =        []
		self._persons =      {}

	@Base.Parent.setter
	def Parent(self, parent: None) -> None:
		ex = TypeError(f"A '{getFullyQualifiedName(self)}' has no parent.")
		ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
		raise ex

	def _AddElement(self, element: BaseWithID) -> None:
		"""
		Add a risk, an implication or a mitigation, which names the risk register as its parent.

		:param element:              The risk, implication or mitigation.
		:raises RiskManagementError: If the risk register already contains an element of the same kind and ID.
		:raises ValueError:          If the element references an implication or a mitigation, which isn't part of the risk
		                             register. |br|
		                             Add the referenced elements to the risk register first.
		:raises ValueError:          If the element is a risk, whose owner isn't a person of the risk register. |br|
		                             Add the person to the risk register first.
		"""
		if isinstance(element, Risk):
			kind =     "Risk"
			elements = self._risks
		elif isinstance(element, Implication):
			kind =     "Implication"
			elements = self._implications
		else:
			kind =     "Mitigation"
			elements = self._mitigations

		if element._id in elements:
			raise RiskManagementError(f"{kind} '{element._id}' already exists in the risk register.")

		for implication in element._implications.values():
			if implication._root is not self:
				ex = ValueError(f"{kind} '{element._id}' references an implication outside the risk register.")
				ex.add_note(f"Got implication '{implication._id}'.")
				ex.add_note(f"Add the implication to the risk register first.")
				raise ex

		if isinstance(element, MitigationsMixin):
			for mitigation in element._mitigations.values():
				if mitigation._root is not self:
					ex = ValueError(f"{kind} '{element._id}' references a mitigation outside the risk register.")
					ex.add_note(f"Got mitigation '{mitigation._id}'.")
					ex.add_note(f"Add the mitigation to the risk register first.")
					raise ex

		if isinstance(element, Risk) and element._owner is not None:
			if self._persons.get(element._owner._userID) is not element._owner:
				ex = ValueError(f"Risk '{element._id}' has an owner outside the risk register.")
				ex.add_note(f"Got person '{element._owner._userID}'.")
				ex.add_note(f"Add the person to the risk register first.")
				raise ex

		elements[element._id] = element

	@readonly
	def Version(self) -> SemanticVersion:
		"""
		Read-only property to access the version of the risk register (:attr:`_version`).

		:returns: The version.
		"""
		return self._version

	@readonly
	def Name(self) -> Nullable[str]:
		"""
		Read-only property to access the name of the risk register (:attr:`_name`).

		:returns: The name, or ``None`` if none is given.
		"""
		return self._name

	@readonly
	def Risks(self) -> dict[str, Risk]:
		"""
		Read-only property to access the risks (:attr:`_risks`).

		:returns: The risks, by ID.
		"""
		return self._risks

	@readonly
	def Implications(self) -> dict[str, Implication]:
		"""
		Read-only property to access the implications (:attr:`_implications`).

		:returns: The implications, by ID.
		"""
		return self._implications

	@readonly
	def Mitigations(self) -> dict[str, Mitigation]:
		"""
		Read-only property to access the mitigations (:attr:`_mitigations`).

		:returns: The mitigations, by ID.
		"""
		return self._mitigations

	@readonly
	def Links(self) -> list[Link]:
		"""
		Read-only property to access the links between the risks (:attr:`_links`).

		:returns: The links, in the order they were added.
		"""
		return self._links

	@readonly
	def Persons(self) -> dict[str, Person]:
		"""
		Read-only property to access the persons the risk register refers to (:attr:`_persons`).

		A risk's owner is one of them.

		:returns: The persons, by user ID.
		"""
		return self._persons

	def AddPerson(self, person: Person) -> None:
		"""
		Add a person the risk register refers to.

		A risk's owner must be added first. The same person may be added to several risk registers.

		:param person:               The person.
		:raises ValueError:          If parameter ``person`` is ``None``.
		:raises TypeError:           If parameter ``person`` isn't of type :class:`~pyEDAA.Reports.Person`.
		:raises RiskManagementError: If the risk register already contains a person of the same user ID.
		"""
		if person is None:
			raise ValueError(f"Parameter 'person' is None.")
		elif not isinstance(person, Person):
			ex = TypeError(f"Parameter 'person' is not of type 'Person'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(person)}'.")
			raise ex
		elif person._userID in self._persons:
			raise RiskManagementError(f"Person '{person._userID}' already exists in the risk register.")

		self._persons[person._userID] = person

	def IterateRisks(self, predicate: Nullable[Callable[[Risk], bool]] = None) -> Generator[Risk, None, None]:
		"""
		Iterate all or selected risks.

		If parameter ``predicate`` is not None, the given filter function is used to skip risks in the generator.

		:param predicate: Optional, filter function accepting any risk and returning a boolean.
		:returns:         A generator of the risks, in the order they were added.
		"""
		if predicate is None:
			yield from self._risks.values()
		else:
			for risk in self._risks.values():
				if predicate(risk):
					yield risk

	def IterateImplications(
		self,
		predicate: Nullable[Callable[[Implication], bool]] = None
	) -> Generator[Implication, None, None]:
		"""
		Iterate all or selected implications.

		If parameter ``predicate`` is not None, the given filter function is used to skip implications in the generator.

		:param predicate: Optional, filter function accepting any implication and returning a boolean.
		:returns:         A generator of the implications, in the order they were added.
		"""
		if predicate is None:
			yield from self._implications.values()
		else:
			for implication in self._implications.values():
				if predicate(implication):
					yield implication

	def IterateMitigations(
		self,
		predicate: Nullable[Callable[[Mitigation], bool]] = None
	) -> Generator[Mitigation, None, None]:
		"""
		Iterate all or selected mitigations.

		If parameter ``predicate`` is not None, the given filter function is used to skip mitigations in the generator.

		:param predicate: Optional, filter function accepting any mitigation and returning a boolean.
		:returns:         A generator of the mitigations, in the order they were added.
		"""
		if predicate is None:
			yield from self._mitigations.values()
		else:
			for mitigation in self._mitigations.values():
				if predicate(mitigation):
					yield mitigation

	def IterateLinks(self, predicate: Nullable[Callable[[Link], bool]] = None) -> Generator[Link, None, None]:
		"""
		Iterate all or selected links between the risks.

		If parameter ``predicate`` is not None, the given filter function is used to skip links in the generator.

		:param predicate: Optional, filter function accepting any link and returning a boolean.
		:returns:         A generator of the links, in the order they were added.
		"""
		if predicate is None:
			yield from self._links
		else:
			for link in self._links:
				if predicate(link):
					yield link

	def __repr__(self) -> str:
		"""
		Return a representation of the risk register for debugging.

		A register of version 1.0.0 with 3 risks, 4 implications and 2 mitigations reads
		``<RiskManagement 1.0.0: 3 risks, 4 implications, 2 mitigations>``.

		:returns: The register's version and its numbers of risks, implications and mitigations.
		"""
		return (
			f"<RiskManagement {self._version}: {len(self._risks)} risks, {len(self._implications)} implications, "
			f"{len(self._mitigations)} mitigations>"
		)


@export
class BaseWithID(Base):
	"""
	Base-class of the elements a risk register holds by ID - risks, implications and mitigations -: an ID and a
	description.
	"""

	_id:          str  #: The element's ID, unique among the elements of its kind in a risk register.
	_description: str  #: The element's description.

	def __init__(
		self,
		identifier: str,
		description: str,
		keyValuePairs: Nullable[Mapping[str, Any]] = None,
		*,
		parent: Nullable[RiskManagement] = None
	) -> None:
		"""
		Initializes an element with its ID, its description, its key-value pairs and its parent.

		:param identifier:    The element's ID, unique among the elements of its kind in a risk register.
		:param description:   The element's description.
		:param keyValuePairs: Optional, the key-value pairs. Default: ``None``.
		:param parent:        Optional, the risk register containing this element. Default: ``None``.
		:raises TypeError:    If parameter ``keyValuePairs`` isn't a mapping.
		:raises TypeError:    If parameter ``keyValuePairs`` contains a key not of type :class:`str`.
		:raises ValueError:   If parameter ``keyValuePairs`` contains an empty key.
		:raises TypeError:    If parameter ``parent`` isn't of type :class:`RiskManagement`.
		:raises ValueError:   If parameter ``identifier`` is ``None``.
		:raises TypeError:    If parameter ``identifier`` isn't of type :class:`str`.
		:raises ValueError:   If parameter ``identifier`` is empty.
		:raises ValueError:   If parameter ``description`` is ``None``.
		:raises TypeError:    If parameter ``description`` isn't of type :class:`str`.
		:raises ValueError:   If parameter ``description`` is empty.
		"""
		super().__init__(keyValuePairs, parent=parent)

		if identifier is None:
			raise ValueError(f"Parameter 'identifier' is None.")
		elif not isinstance(identifier, str):
			ex = TypeError(f"Parameter 'identifier' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(identifier)}'.")
			raise ex
		elif identifier == "":
			raise ValueError(f"Parameter 'identifier' is empty.")

		if description is None:
			raise ValueError(f"Parameter 'description' is None.")
		elif not isinstance(description, str):
			ex = TypeError(f"Parameter 'description' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(description)}'.")
			raise ex
		elif description == "":
			raise ValueError(f"Parameter 'description' is empty.")

		self._id =          identifier
		self._description = description

	@readonly
	def ID(self) -> str:
		"""
		Read-only property to access the element's ID (:attr:`_id`).

		:returns: The ID.
		"""
		return self._id

	@readonly
	def Description(self) -> str:
		"""
		Read-only property to access the element's description (:attr:`_description`).

		:returns: The description.
		"""
		return self._description


@export
class ImplicationsMixin(metaclass=ExtendedType, mixin=True):
	"""
	A mixin-class adding implications to an element: the consequences the element has.

	The implications of a risk are what happens, if it occurs; those of a mitigation are its side effects. An element of
	a risk register references only implications of the same register.
	"""

	_implications: dict[str, Implication]  #: The implications, by ID.

	def __init__(self, implications: Nullable[Iterable[Implication]] = None) -> None:
		"""
		Initializes the implications.

		:param implications: Optional, the implications. Default: ``None``.
		:raises TypeError:   If parameter ``implications`` isn't iterable.
		:raises TypeError:   If parameter ``implications`` is a single element, not an iterable.
		:raises TypeError:   If parameter ``implications`` contains an element not of type :class:`Implication`.
		:raises ValueError:  If parameter ``implications`` contains two implications of the same ID.
		:raises ValueError:  If parameter ``implications`` contains an implication, which isn't part of the element's
		                     risk register. |br|
		                     Add the implication to the risk register first.
		"""
		self._implications = {}

		if implications is None:
			return
		elif not isinstance(implications, Iterable):
			ex = TypeError(f"Parameter 'implications' is not iterable.")
			ex.add_note(f"Got type '{getFullyQualifiedName(implications)}'.")
			raise ex
		elif isinstance(implications, KeyValuePairsMixin):
			ex = TypeError(f"Parameter 'implications' is a single element, not an iterable of elements.")
			ex.add_note(f"Got type '{getFullyQualifiedName(implications)}'.")
			raise ex

		for implication in implications:
			if not isinstance(implication, Implication):
				ex = TypeError(f"Parameter 'implications' contains an element not of type 'Implication'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(implication)}'.")
				raise ex
			elif implication._id in self._implications:
				raise ValueError(f"Parameter 'implications' contains implication '{implication._id}' twice.")
			elif self._root is not None and implication._root is not self._root:
				ex = ValueError(f"Parameter 'implications' contains an implication outside the element's risk register.")
				ex.add_note(f"Got implication '{implication._id}'.")
				ex.add_note(f"Add the implication to the risk register first.")
				raise ex

			self._implications[implication._id] = implication

	@readonly
	def Implications(self) -> dict[str, Implication]:
		"""
		Read-only property to access the implications (:attr:`_implications`).

		:returns: The implications, by ID.
		"""
		return self._implications

	def AddImplication(self, implication: Implication) -> None:
		"""
		Add an implication.

		:param implication:          The implication.
		:raises ValueError:          If parameter ``implication`` is ``None``.
		:raises TypeError:           If parameter ``implication`` isn't of type :class:`Implication`.
		:raises RiskManagementError: If the element already has an implication of the same ID.
		:raises ValueError:          If the implication isn't part of the element's risk register. |br|
		                             Add the implication to the risk register first.
		"""
		if implication is None:
			raise ValueError(f"Parameter 'implication' is None.")
		elif not isinstance(implication, Implication):
			ex = TypeError(f"Parameter 'implication' is not of type 'Implication'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(implication)}'.")
			raise ex
		elif implication._id in self._implications:
			raise RiskManagementError(f"Element already has implication '{implication._id}'.")
		elif self._root is not None and implication._root is not self._root:
			ex = ValueError(f"Parameter 'implication' is outside the element's risk register.")
			ex.add_note(f"Got implication '{implication._id}'.")
			ex.add_note(f"Add the implication to the risk register first.")
			raise ex

		self._implications[implication._id] = implication


@export
class MitigationsMixin(metaclass=ExtendedType, mixin=True):
	"""
	A mixin-class adding mitigations to an element: the measures reducing the element's probability or impact.

	An element of a risk register references only mitigations of the same register.
	"""

	_mitigations: dict[str, Mitigation]  #: The mitigations, by ID.

	def __init__(self, mitigations: Nullable[Iterable[Mitigation]] = None) -> None:
		"""
		Initializes the mitigations.

		:param mitigations: Optional, the mitigations. Default: ``None``.
		:raises TypeError:  If parameter ``mitigations`` isn't iterable.
		:raises TypeError:  If parameter ``mitigations`` is a single element, not an iterable.
		:raises TypeError:  If parameter ``mitigations`` contains an element not of type :class:`Mitigation`.
		:raises ValueError: If parameter ``mitigations`` contains two mitigations of the same ID.
		:raises ValueError: If parameter ``mitigations`` contains a mitigation, which isn't part of the element's risk
		                    register. |br|
		                    Add the mitigation to the risk register first.
		"""
		self._mitigations = {}

		if mitigations is None:
			return
		elif not isinstance(mitigations, Iterable):
			ex = TypeError(f"Parameter 'mitigations' is not iterable.")
			ex.add_note(f"Got type '{getFullyQualifiedName(mitigations)}'.")
			raise ex
		elif isinstance(mitigations, KeyValuePairsMixin):
			ex = TypeError(f"Parameter 'mitigations' is a single element, not an iterable of elements.")
			ex.add_note(f"Got type '{getFullyQualifiedName(mitigations)}'.")
			raise ex

		for mitigation in mitigations:
			if not isinstance(mitigation, Mitigation):
				ex = TypeError(f"Parameter 'mitigations' contains an element not of type 'Mitigation'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(mitigation)}'.")
				raise ex
			elif mitigation._id in self._mitigations:
				raise ValueError(f"Parameter 'mitigations' contains mitigation '{mitigation._id}' twice.")
			elif self._root is not None and mitigation._root is not self._root:
				ex = ValueError(f"Parameter 'mitigations' contains a mitigation outside the element's risk register.")
				ex.add_note(f"Got mitigation '{mitigation._id}'.")
				ex.add_note(f"Add the mitigation to the risk register first.")
				raise ex

			self._mitigations[mitigation._id] = mitigation

	@readonly
	def Mitigations(self) -> dict[str, Mitigation]:
		"""
		Read-only property to access the mitigations (:attr:`_mitigations`).

		:returns: The mitigations, by ID.
		"""
		return self._mitigations

	def AddMitigation(self, mitigation: Mitigation) -> None:
		"""
		Add a mitigation.

		:param mitigation:           The mitigation.
		:raises ValueError:          If parameter ``mitigation`` is ``None``.
		:raises TypeError:           If parameter ``mitigation`` isn't of type :class:`Mitigation`.
		:raises RiskManagementError: If the element already has a mitigation of the same ID.
		:raises ValueError:          If the mitigation isn't part of the element's risk register. |br|
		                             Add the mitigation to the risk register first.
		"""
		if mitigation is None:
			raise ValueError(f"Parameter 'mitigation' is None.")
		elif not isinstance(mitigation, Mitigation):
			ex = TypeError(f"Parameter 'mitigation' is not of type 'Mitigation'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(mitigation)}'.")
			raise ex
		elif mitigation._id in self._mitigations:
			raise RiskManagementError(f"Element already has mitigation '{mitigation._id}'.")
		elif self._root is not None and mitigation._root is not self._root:
			ex = ValueError(f"Parameter 'mitigation' is outside the element's risk register.")
			ex.add_note(f"Got mitigation '{mitigation._id}'.")
			ex.add_note(f"Add the mitigation to the risk register first.")
			raise ex

		self._mitigations[mitigation._id] = mitigation


@export
class Implication(BaseWithID, ImplicationsMixin, MitigationsMixin):
	"""
	An implication: a consequence of a risk, if it occurs, of another implication, or of a mitigation, if applied.

	An implication is shared by every element naming it, e.g. two risks delaying the same milestone. It has implications
	of its own - the next order of consequences -, and it can be mitigated like a risk.
	"""

	def __init__(
		self,
		identifier: str,
		description: str,
		implications: Nullable[Iterable[Implication]] = None,
		mitigations: Nullable[Iterable[Mitigation]] = None,
		keyValuePairs: Nullable[Mapping[str, Any]] = None,
		*,
		parent: Nullable[RiskManagement] = None
	) -> None:
		"""
		Initializes an implication, and adds it to its risk register.

		:param identifier:           The implication's ID, unique among the implications of a risk register.
		:param description:          The implication's description.
		:param implications:         Optional, the implications of this implication. Default: ``None``.
		:param mitigations:          Optional, the mitigations of this implication. Default: ``None``.
		:param keyValuePairs:        Optional, the key-value pairs. Default: ``None``.
		:param parent:               Optional, the risk register containing the implication. Default: ``None``.
		:raises TypeError:           If parameter ``keyValuePairs`` isn't a mapping.
		:raises TypeError:           If parameter ``keyValuePairs`` contains a key not of type :class:`str`.
		:raises ValueError:          If parameter ``keyValuePairs`` contains an empty key.
		:raises TypeError:           If parameter ``parent`` isn't of type :class:`RiskManagement`.
		:raises ValueError:          If parameter ``identifier`` is ``None``.
		:raises TypeError:           If parameter ``identifier`` isn't of type :class:`str`.
		:raises ValueError:          If parameter ``identifier`` is empty.
		:raises ValueError:          If parameter ``description`` is ``None``.
		:raises TypeError:           If parameter ``description`` isn't of type :class:`str`.
		:raises ValueError:          If parameter ``description`` is empty.
		:raises TypeError:           If parameter ``implications`` isn't iterable.
		:raises TypeError:           If parameter ``implications`` is a single element, not an iterable.
		:raises TypeError:           If parameter ``implications`` contains an element not of type :class:`Implication`.
		:raises ValueError:          If parameter ``implications`` contains two implications of the same ID.
		:raises ValueError:          If parameter ``implications`` contains an implication, which isn't part of the risk
		                             register. |br|
		                             Add the implication to the risk register first.
		:raises TypeError:           If parameter ``mitigations`` isn't iterable.
		:raises TypeError:           If parameter ``mitigations`` is a single element, not an iterable.
		:raises TypeError:           If parameter ``mitigations`` contains an element not of type :class:`Mitigation`.
		:raises ValueError:          If parameter ``mitigations`` contains two mitigations of the same ID.
		:raises ValueError:          If parameter ``mitigations`` contains a mitigation, which isn't part of the risk
		                             register. |br|
		                             Add the mitigation to the risk register first.
		:raises RiskManagementError: If the risk register already contains an implication of this ID.
		"""
		super().__init__(identifier, description, keyValuePairs, parent=parent)
		ImplicationsMixin.__init__(self, implications)
		MitigationsMixin.__init__(self, mitigations)

		if parent is not None:
			parent._AddElement(self)

	def __repr__(self) -> str:
		"""
		Return a representation of the implication for debugging.

		An implication ``I1`` with 2 implications and 1 mitigation reads ``<Implication I1: 2 implications,
		1 mitigations>``.

		:returns: The implication's ID and its numbers of implications and mitigations.
		"""
		return f"<Implication {self._id}: {len(self._implications)} implications, {len(self._mitigations)} mitigations>"


@export
class Mitigation(BaseWithID, ImplicationsMixin):
	"""
	A mitigation: a measure reducing the probability or the impact of a risk or of an implication.

	A mitigation is shared by every element naming it, e.g. a second supplier reducing two risks. Its implications are
	its side effects: the consequences of applying it.
	"""

	_kind:  MitigationKind   #: The way the mitigation reduces a risk or an implication.
	_state: MitigationState  #: Whether the mitigation is applied.

	def __init__(
		self,
		identifier: str,
		description: str,
		implications: Nullable[Iterable[Implication]] = None,
		kind: MitigationKind = MitigationKind.Prevent,
		state: MitigationState = MitigationState.Planned,
		keyValuePairs: Nullable[Mapping[str, Any]] = None,
		*,
		parent: Nullable[RiskManagement] = None
	) -> None:
		"""
		Initializes a mitigation, and adds it to its risk register.

		:param identifier:           The mitigation's ID, unique among the mitigations of a risk register.
		:param description:          The mitigation's description.
		:param implications:         Optional, the side effects of applying the mitigation. Default: ``None``.
		:param kind:                 Optional, the way the mitigation reduces a risk or an implication.
		                             Default: ``MitigationKind.Prevent``.
		:param state:                Optional, whether the mitigation is applied. Default: ``MitigationState.Planned``.
		:param keyValuePairs:        Optional, the key-value pairs. Default: ``None``.
		:param parent:               Optional, the risk register containing the mitigation. Default: ``None``.
		:raises TypeError:           If parameter ``keyValuePairs`` isn't a mapping.
		:raises TypeError:           If parameter ``keyValuePairs`` contains a key not of type :class:`str`.
		:raises ValueError:          If parameter ``keyValuePairs`` contains an empty key.
		:raises TypeError:           If parameter ``parent`` isn't of type :class:`RiskManagement`.
		:raises ValueError:          If parameter ``identifier`` is ``None``.
		:raises TypeError:           If parameter ``identifier`` isn't of type :class:`str`.
		:raises ValueError:          If parameter ``identifier`` is empty.
		:raises ValueError:          If parameter ``description`` is ``None``.
		:raises TypeError:           If parameter ``description`` isn't of type :class:`str`.
		:raises ValueError:          If parameter ``description`` is empty.
		:raises TypeError:           If parameter ``implications`` isn't iterable.
		:raises TypeError:           If parameter ``implications`` is a single element, not an iterable.
		:raises TypeError:           If parameter ``implications`` contains an element not of type :class:`Implication`.
		:raises ValueError:          If parameter ``implications`` contains two implications of the same ID.
		:raises ValueError:          If parameter ``implications`` contains an implication, which isn't part of the risk
		                             register. |br|
		                             Add the implication to the risk register first.
		:raises ValueError:          If parameter ``kind`` is ``None``.
		:raises TypeError:           If parameter ``kind`` isn't of type :class:`MitigationKind`.
		:raises ValueError:          If parameter ``state`` is ``None``.
		:raises TypeError:           If parameter ``state`` isn't of type :class:`MitigationState`.
		:raises RiskManagementError: If the risk register already contains a mitigation of this ID.
		"""
		super().__init__(identifier, description, keyValuePairs, parent=parent)
		ImplicationsMixin.__init__(self, implications)

		if kind is None:
			raise ValueError(f"Parameter 'kind' is None.")
		elif not isinstance(kind, MitigationKind):
			ex = TypeError(f"Parameter 'kind' is not of type 'MitigationKind'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(kind)}'.")
			raise ex

		if state is None:
			raise ValueError(f"Parameter 'state' is None.")
		elif not isinstance(state, MitigationState):
			ex = TypeError(f"Parameter 'state' is not of type 'MitigationState'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(state)}'.")
			raise ex

		self._kind =  kind
		self._state = state

		if parent is not None:
			parent._AddElement(self)

	@readonly
	def Kind(self) -> MitigationKind:
		"""
		Read-only property to access the way the mitigation reduces a risk or an implication (:attr:`_kind`).

		:returns: The mitigation's kind.
		"""
		return self._kind

	@property
	def State(self) -> MitigationState:
		"""
		Property to access whether the mitigation is applied (:attr:`_state`).

		:returns:           The mitigation's state.
		:raises ValueError: If ``None`` is assigned.
		:raises TypeError:  If the assigned value isn't of type :class:`MitigationState`.
		"""
		return self._state

	@State.setter
	def State(self, value: MitigationState) -> None:
		if value is None:
			raise ValueError(f"Parameter 'value' is None.")
		elif not isinstance(value, MitigationState):
			ex = TypeError(f"Parameter 'value' is not of type 'MitigationState'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
			raise ex

		self._state = value

	def __repr__(self) -> str:
		"""
		Return a representation of the mitigation for debugging.

		A planned, preventing mitigation ``M1`` with 1 side effect reads ``<Mitigation M1: prevent, planned,
		1 implications>``.

		:returns: The mitigation's ID, kind, state and number of implications.
		"""
		return f"<Mitigation {self._id}: {self._kind}, {self._state}, {len(self._implications)} implications>"


# A class with a property named like a class - ``Probability``, ``Impact`` - can't name that class in the annotation of
# a field: the class body's namespace, where annotations are evaluated, binds the name to the property.
_Probability = Probability
_Impact =      Impact


@export
class Risk(BaseWithID, ImplicationsMixin, MitigationsMixin):
	"""
	A risk: its title and description, the probability it occurs, its impact, its state, its owner, the date of its next
	review, the implications and mitigations it references, and its links to other risks.

	The implications of a risk are its first-order implications. Their implications and the side effects of the risk's
	mitigations are its second-order implications (:attr:`SecondOrderImplications`).
	"""

	_title:         str                 #: The risk's title.
	_probability:   _Probability        #: The probability the risk occurs.
	_impact:        _Impact             #: The impact of the risk, if it occurs.
	_state:         RiskState           #: The state of the risk in its life cycle.
	_owner:         Nullable[Person]    #: The person responsible for the risk, if named.
	_nextReview:    Nullable[datetime]  #: The date of the risk's next review, if scheduled.
	_outboundLinks: list[Link]          #: The links from this risk to other risks, in the order they were added.
	_inboundLinks:  list[Link]          #: The links from other risks to this risk, in the order they were added.

	def __init__(
		self,
		identifier: str,
		title: str,
		description: str,
		probability: Probability,
		impact: Impact,
		state: RiskState = RiskState.Open,
		implications: Nullable[Iterable[Implication]] = None,
		mitigations: Nullable[Iterable[Mitigation]] = None,
		owner: Nullable[Person] = None,
		nextReview: Nullable[datetime] = None,
		keyValuePairs: Nullable[Mapping[str, Any]] = None,
		*,
		parent: Nullable[RiskManagement] = None
	) -> None:
		"""
		Initializes a risk, and adds it to its risk register.

		:param identifier:           The risk's ID, unique among the risks of a risk register.
		:param title:                The risk's title.
		:param description:          The risk's description.
		:param probability:          The probability the risk occurs.
		:param impact:               The impact of the risk, if it occurs.
		:param state:                Optional, the state of the risk. Default: ``RiskState.Open``.
		:param implications:         Optional, the first-order implications of the risk. Default: ``None``.
		:param mitigations:          Optional, the mitigations of the risk. Default: ``None``.
		:param owner:                Optional, the person responsible for the risk; a person of the risk register.
		                             Default: ``None``.
		:param nextReview:           Optional, the date of the risk's next review; without a time zone, it is a local time.
		                             Default: ``None``.
		:param keyValuePairs:        Optional, the key-value pairs. Default: ``None``.
		:param parent:               Optional, the risk register containing the risk. Default: ``None``.
		:raises TypeError:           If parameter ``keyValuePairs`` isn't a mapping.
		:raises TypeError:           If parameter ``keyValuePairs`` contains a key not of type :class:`str`.
		:raises ValueError:          If parameter ``keyValuePairs`` contains an empty key.
		:raises TypeError:           If parameter ``parent`` isn't of type :class:`RiskManagement`.
		:raises ValueError:          If parameter ``identifier`` is ``None``.
		:raises TypeError:           If parameter ``identifier`` isn't of type :class:`str`.
		:raises ValueError:          If parameter ``identifier`` is empty.
		:raises ValueError:          If parameter ``description`` is ``None``.
		:raises TypeError:           If parameter ``description`` isn't of type :class:`str`.
		:raises ValueError:          If parameter ``description`` is empty.
		:raises TypeError:           If parameter ``implications`` isn't iterable.
		:raises TypeError:           If parameter ``implications`` is a single element, not an iterable.
		:raises TypeError:           If parameter ``implications`` contains an element not of type :class:`Implication`.
		:raises ValueError:          If parameter ``implications`` contains two implications of the same ID.
		:raises ValueError:          If parameter ``implications`` contains an implication, which isn't part of the risk
		                             register. |br|
		                             Add the implication to the risk register first.
		:raises TypeError:           If parameter ``mitigations`` isn't iterable.
		:raises TypeError:           If parameter ``mitigations`` is a single element, not an iterable.
		:raises TypeError:           If parameter ``mitigations`` contains an element not of type :class:`Mitigation`.
		:raises ValueError:          If parameter ``mitigations`` contains two mitigations of the same ID.
		:raises ValueError:          If parameter ``mitigations`` contains a mitigation, which isn't part of the risk
		                             register. |br|
		                             Add the mitigation to the risk register first.
		:raises ValueError:          If parameter ``title`` is ``None``.
		:raises TypeError:           If parameter ``title`` isn't of type :class:`str`.
		:raises ValueError:          If parameter ``title`` is empty.
		:raises ValueError:          If parameter ``probability`` is ``None``.
		:raises TypeError:           If parameter ``probability`` isn't of type :class:`Probability`.
		:raises ValueError:          If parameter ``impact`` is ``None``.
		:raises TypeError:           If parameter ``impact`` isn't of type :class:`Impact`.
		:raises ValueError:          If parameter ``state`` is ``None``.
		:raises TypeError:           If parameter ``state`` isn't of type :class:`RiskState`.
		:raises TypeError:           If parameter ``owner`` isn't of type :class:`~pyEDAA.Reports.Person`.
		:raises ValueError:          If parameter ``owner`` isn't a person of the risk register. |br|
		                             Add the person to the risk register first.
		:raises TypeError:           If parameter ``nextReview`` isn't of type :class:`~datetime.datetime`.
		:raises RiskManagementError: If the risk register already contains a risk of this ID.
		"""
		super().__init__(identifier, description, keyValuePairs, parent=parent)
		ImplicationsMixin.__init__(self, implications)
		MitigationsMixin.__init__(self, mitigations)

		if title is None:
			raise ValueError(f"Parameter 'title' is None.")
		elif not isinstance(title, str):
			ex = TypeError(f"Parameter 'title' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(title)}'.")
			raise ex
		elif title == "":
			raise ValueError(f"Parameter 'title' is empty.")

		if probability is None:
			raise ValueError(f"Parameter 'probability' is None.")
		elif not isinstance(probability, Probability):
			ex = TypeError(f"Parameter 'probability' is not of type 'Probability'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(probability)}'.")
			raise ex

		if impact is None:
			raise ValueError(f"Parameter 'impact' is None.")
		elif not isinstance(impact, Impact):
			ex = TypeError(f"Parameter 'impact' is not of type 'Impact'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(impact)}'.")
			raise ex

		if state is None:
			raise ValueError(f"Parameter 'state' is None.")
		elif not isinstance(state, RiskState):
			ex = TypeError(f"Parameter 'state' is not of type 'RiskState'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(state)}'.")
			raise ex

		if owner is not None:
			if not isinstance(owner, Person):
				ex = TypeError(f"Parameter 'owner' is not of type 'Person'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(owner)}'.")
				raise ex
			elif self._root is not None and self._root._persons.get(owner._userID) is not owner:
				ex = ValueError(f"Parameter 'owner' isn't a person of the risk register.")
				ex.add_note(f"Got person '{owner._userID}'.")
				ex.add_note(f"Add the person to the risk register first.")
				raise ex

		if nextReview is not None and not isinstance(nextReview, datetime):
			ex = TypeError(f"Parameter 'nextReview' is not of type 'datetime'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(nextReview)}'.")
			raise ex

		self._title =         title
		self._probability =   probability
		self._impact =        impact
		self._state =         state
		self._owner =         owner
		self._nextReview =    nextReview
		self._outboundLinks = []
		self._inboundLinks =  []

		if parent is not None:
			parent._AddElement(self)

	@readonly
	def Title(self) -> str:
		"""
		Read-only property to access the risk's title (:attr:`_title`).

		:returns: The title.
		"""
		return self._title

	@property
	def Probability(self) -> Probability:
		"""
		Property to access the probability the risk occurs (:attr:`_probability`).

		:returns:           The probability.
		:raises ValueError: If ``None`` is assigned.
		:raises TypeError:  If the assigned value isn't of type :class:`Probability`.
		"""
		return self._probability

	@Probability.setter
	def Probability(self, value: Probability) -> None:
		if value is None:
			raise ValueError(f"Parameter 'value' is None.")
		elif not isinstance(value, Probability):
			ex = TypeError(f"Parameter 'value' is not of type 'Probability'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
			raise ex

		self._probability = value

	@property
	def Impact(self) -> Impact:
		"""
		Property to access the impact of the risk, if it occurs (:attr:`_impact`).

		:returns:           The impact.
		:raises ValueError: If ``None`` is assigned.
		:raises TypeError:  If the assigned value isn't of type :class:`Impact`.
		"""
		return self._impact

	@Impact.setter
	def Impact(self, value: Impact) -> None:
		if value is None:
			raise ValueError(f"Parameter 'value' is None.")
		elif not isinstance(value, Impact):
			ex = TypeError(f"Parameter 'value' is not of type 'Impact'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
			raise ex

		self._impact = value

	@property
	def State(self) -> RiskState:
		"""
		Property to access the state of the risk in its life cycle (:attr:`_state`).

		:returns:           The state.
		:raises ValueError: If ``None`` is assigned.
		:raises TypeError:  If the assigned value isn't of type :class:`RiskState`.
		"""
		return self._state

	@State.setter
	def State(self, value: RiskState) -> None:
		if value is None:
			raise ValueError(f"Parameter 'value' is None.")
		elif not isinstance(value, RiskState):
			ex = TypeError(f"Parameter 'value' is not of type 'RiskState'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
			raise ex

		self._state = value

	@property
	def Owner(self) -> Nullable[Person]:
		"""
		Property to access the person responsible for the risk (:attr:`_owner`).

		The owner of a risk in a risk register is a person of that register (:attr:`RiskManagement.Persons`).

		:returns:           The owner, or ``None`` if none is named.
		:raises TypeError:  If the assigned value isn't of type :class:`~pyEDAA.Reports.Person`.
		:raises ValueError: If the assigned value isn't a person of the risk register. |br|
		                    Add the person to the risk register first.
		"""
		return self._owner

	@Owner.setter
	def Owner(self, value: Nullable[Person]) -> None:
		if value is not None:
			if not isinstance(value, Person):
				ex = TypeError(f"Parameter 'value' is not of type 'Person'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
				raise ex
			elif self._root is not None and self._root._persons.get(value._userID) is not value:
				ex = ValueError(f"Parameter 'value' isn't a person of the risk register.")
				ex.add_note(f"Got person '{value._userID}'.")
				ex.add_note(f"Add the person to the risk register first.")
				raise ex

		self._owner = value

	@property
	def NextReview(self) -> Nullable[datetime]:
		"""
		Property to access the date of the risk's next review (:attr:`_nextReview`).

		:returns:          The date, or ``None`` if no review is scheduled; without a time zone, it is a local time.
		:raises TypeError: If the assigned value isn't of type :class:`~datetime.datetime`.
		"""
		return self._nextReview

	@NextReview.setter
	def NextReview(self, value: Nullable[datetime]) -> None:
		if value is not None and not isinstance(value, datetime):
			ex = TypeError(f"Parameter 'value' is not of type 'datetime'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
			raise ex

		self._nextReview = value

	@readonly
	def Score(self) -> int:
		"""
		Read-only property to return the risk's score: the rank of its probability times the rank of its impact.

		:returns: The score in range 1..16.
		"""
		return self._probability.Rank * self._impact.Rank

	@readonly
	def Level(self) -> RiskLevel:
		"""
		Read-only property to return the risk's level, classified by its :attr:`Score` (see :class:`RiskLevel`).

		:returns: The risk's level.
		"""
		score = self.Score
		if score >= 12:
			return RiskLevel.Critical
		elif score >= 8:
			return RiskLevel.High
		elif score >= 4:
			return RiskLevel.Medium

		return RiskLevel.Low

	@readonly
	def SecondOrderImplications(self) -> dict[str, Implication]:
		"""
		Read-only property to return the second-order implications: the implications of the risk's implications and of its
		mitigations.

		The implications of a mitigation are its side effects. An implication reached several times is returned once.

		:returns: The second-order implications, by ID.
		"""
		implications = {}
		for element in (*self._implications.values(), *self._mitigations.values()):
			implications.update(element._implications)

		return implications

	@readonly
	def OutboundLinks(self) -> list[Link]:
		"""
		Read-only property to access the links from this risk to other risks (:attr:`_outboundLinks`).

		:returns: The links, in the order they were added.
		"""
		return self._outboundLinks

	@readonly
	def InboundLinks(self) -> list[Link]:
		"""
		Read-only property to access the links from other risks to this risk (:attr:`_inboundLinks`).

		:returns: The links, in the order they were added.
		"""
		return self._inboundLinks

	def LinkTo(
		self,
		destination: Risk,
		kind: LinkKind,
		*,
		keyValuePairs: Nullable[Mapping[str, Any]] = None
	) -> Link:
		"""
		Create an outbound link from this risk to the given risk.

		:param destination:          The risk the link ends at.
		:param kind:                 The relationship the link states.
		:param keyValuePairs:        Optional, the key-value pairs of the link. Default: ``None``.
		:returns:                    The link from this risk to the destination.
		:raises TypeError:           If parameter ``keyValuePairs`` isn't a mapping.
		:raises TypeError:           If parameter ``keyValuePairs`` contains a key not of type :class:`str`.
		:raises ValueError:          If parameter ``keyValuePairs`` contains an empty key.
		:raises ValueError:          If this risk isn't part of a risk register.
		:raises ValueError:          If parameter ``destination`` is ``None``.
		:raises TypeError:           If parameter ``destination`` isn't of type :class:`Risk`.
		:raises ValueError:          If parameter ``destination`` is this risk.
		:raises ValueError:          If parameter ``destination`` isn't part of this risk's risk register.
		:raises ValueError:          If parameter ``kind`` is ``None``.
		:raises TypeError:           If parameter ``kind`` isn't of type :class:`LinkKind`.
		:raises RiskManagementError: If this risk already has a link of this kind to the destination.

		.. seealso::

		   :meth:`LinkFrom`
		      |rarr| Create an inbound link from the given risk to this risk.
		"""
		return Link(self, destination, kind, keyValuePairs=keyValuePairs)

	def LinkFrom(
		self,
		source: Risk,
		kind: LinkKind,
		*,
		keyValuePairs: Nullable[Mapping[str, Any]] = None
	) -> Link:
		"""
		Create an inbound link from the given risk to this risk.

		:param source:               The risk the link starts at.
		:param kind:                 The relationship the link states.
		:param keyValuePairs:        Optional, the key-value pairs of the link. Default: ``None``.
		:returns:                    The link from the source to this risk.
		:raises ValueError:          If parameter ``source`` is this risk.
		:raises TypeError:           If parameter ``keyValuePairs`` isn't a mapping.
		:raises TypeError:           If parameter ``keyValuePairs`` contains a key not of type :class:`str`.
		:raises ValueError:          If parameter ``keyValuePairs`` contains an empty key.
		:raises ValueError:          If parameter ``source`` is ``None``.
		:raises TypeError:           If parameter ``source`` isn't of type :class:`Risk`.
		:raises ValueError:          If parameter ``source`` isn't part of a risk register.
		:raises ValueError:          If this risk isn't part of the source's risk register.
		:raises ValueError:          If parameter ``kind`` is ``None``.
		:raises TypeError:           If parameter ``kind`` isn't of type :class:`LinkKind`.
		:raises RiskManagementError: If the source already has a link of this kind to this risk.

		.. seealso::

		   :meth:`LinkTo`
		      |rarr| Create an outbound link from this risk to the given risk.
		"""
		if source is self:
			ex = ValueError(f"Parameter 'source' is this risk.")
			ex.add_note(f"Got risk '{source._id}'.")
			raise ex

		return Link(source, self, kind, keyValuePairs=keyValuePairs)

	def __repr__(self) -> str:
		"""
		Return a representation of the risk for debugging.

		An open risk ``R1`` of medium probability and high impact reads ``<Risk R1: open, probability medium,
		impact high, level medium>``.

		:returns: The risk's ID, state, probability, impact and level.
		"""
		return (
			f"<Risk {self._id}: {self._state}, probability {self._probability}, impact {self._impact}, level {self.Level}>"
		)


@export
class Link(KeyValuePairsMixin, metaclass=ExtendedType, slots=True):
	"""
	A link from a source risk to a destination risk of the same risk register, and the relationship it states.

	A link connects two risks; it is no element of the risk register and has no parent. The source lists it in
	:attr:`~Risk.OutboundLinks`, the destination in :attr:`~Risk.InboundLinks`, the risk register in
	:attr:`~RiskManagement.Links`.
	"""

	_source:      Risk      #: The risk the link starts at.
	_destination: Risk      #: The risk the link ends at.
	_kind:        LinkKind  #: The relationship the link states.

	def __init__(
		self,
		source: Risk,
		destination: Risk,
		kind: LinkKind,
		*,
		keyValuePairs: Nullable[Mapping[str, Any]] = None
	) -> None:
		"""
		Initializes a link, and adds it to its source, its destination and their risk register.

		:param source:               The risk the link starts at.
		:param destination:          The risk the link ends at.
		:param kind:                 The relationship the link states.
		:param keyValuePairs:        Optional, the key-value pairs. Default: ``None``.
		:raises TypeError:           If parameter ``keyValuePairs`` isn't a mapping.
		:raises TypeError:           If parameter ``keyValuePairs`` contains a key not of type :class:`str`.
		:raises ValueError:          If parameter ``keyValuePairs`` contains an empty key.
		:raises ValueError:          If parameter ``source`` is ``None``.
		:raises TypeError:           If parameter ``source`` isn't of type :class:`Risk`.
		:raises ValueError:          If parameter ``source`` isn't part of a risk register.
		:raises ValueError:          If parameter ``destination`` is ``None``.
		:raises TypeError:           If parameter ``destination`` isn't of type :class:`Risk`.
		:raises ValueError:          If parameter ``destination`` is the source.
		:raises ValueError:          If parameter ``destination`` isn't part of the source's risk register.
		:raises ValueError:          If parameter ``kind`` is ``None``.
		:raises TypeError:           If parameter ``kind`` isn't of type :class:`LinkKind`.
		:raises RiskManagementError: If the source already has a link of this kind to the destination.
		"""
		super().__init__(keyValuePairs)

		if source is None:
			raise ValueError(f"Parameter 'source' is None.")
		elif not isinstance(source, Risk):
			ex = TypeError(f"Parameter 'source' is not of type 'Risk'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(source)}'.")
			raise ex
		elif source._root is None:
			ex = ValueError(f"Parameter 'source' isn't part of a risk register.")
			ex.add_note(f"Got risk '{source._id}'.")
			raise ex

		if destination is None:
			raise ValueError(f"Parameter 'destination' is None.")
		elif not isinstance(destination, Risk):
			ex = TypeError(f"Parameter 'destination' is not of type 'Risk'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(destination)}'.")
			raise ex
		elif destination is source:
			ex = ValueError(f"Parameter 'destination' is the source.")
			ex.add_note(f"Got risk '{destination._id}'.")
			raise ex
		elif destination._root is not source._root:
			ex = ValueError(f"Parameter 'destination' isn't part of the source's risk register.")
			ex.add_note(f"Got risk '{destination._id}'.")
			raise ex

		if kind is None:
			raise ValueError(f"Parameter 'kind' is None.")
		elif not isinstance(kind, LinkKind):
			ex = TypeError(f"Parameter 'kind' is not of type 'LinkKind'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(kind)}'.")
			raise ex

		for link in source._outboundLinks:
			if link._destination is destination and link._kind is kind:
				raise RiskManagementError(f"Risk '{source._id}' already has a '{kind}' link to risk '{destination._id}'.")

		self._source =      source
		self._destination = destination
		self._kind =        kind

		source._outboundLinks.append(self)
		destination._inboundLinks.append(self)
		source._root._links.append(self)


	@readonly
	def Source(self) -> Risk:
		"""
		Read-only property to access the risk the link starts at (:attr:`_source`).

		:returns: The source risk.
		"""
		return self._source

	@readonly
	def Destination(self) -> Risk:
		"""
		Read-only property to access the risk the link ends at (:attr:`_destination`).

		:returns: The destination risk.
		"""
		return self._destination

	@readonly
	def Kind(self) -> LinkKind:
		"""
		Read-only property to access the relationship the link states (:attr:`_kind`).

		:returns: The link's kind.
		"""
		return self._kind

	def __repr__(self) -> str:
		"""
		Return a representation of the link for debugging.

		A link stating risk ``R1`` causes risk ``R2`` reads ``<Link R1 causes R2>``.

		:returns: The IDs of the source and the destination, and the link's kind.
		"""
		return f"<Link {self._source._id} {self._kind} {self._destination._id}>"
