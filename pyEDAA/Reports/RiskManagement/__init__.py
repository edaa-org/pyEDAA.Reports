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
Abstract data model of risk management: a risk register of risks.

The root, :class:`RiskManagement`, holds every :class:`Risk` by ID. A risk has a title and a description, the
:class:`Probability` it occurs, its :class:`Impact`, if it occurs, and its :class:`RiskState`.

Every element has key-value pairs (:class:`~pyEDAA.Reports.KeyValuePairsMixin`) for data the model doesn't name.
"""
from __future__            import annotations

from typing                import Any, Callable, Generator, Mapping, Optional as Nullable

from pyTooling.Common      import getFullyQualifiedName, StringEnum
from pyTooling.Decorators  import export, readonly
from pyTooling.MetaClasses import ExtendedType, abstractmethod
from pyTooling.Versioning  import SemanticVersion

from pyEDAA.Reports        import KeyValuePairsMixin


@export
class Probability(StringEnum):
	"""
	The probability of a risk to occur.
	"""

	Low =      "low"       #: Identified, but sleeping.
	Medium =   "medium"    #: Likely to occur soon.
	High =     "high"      #: Very likely to occur.
	Occurred = "occurred"  #: Occurred: the risk is active and causes heavy effects.


@export
class Impact(StringEnum):
	"""
	The impact of a risk, if it occurs, as the delay it causes.
	"""

	Low =      "low"       #: A delay of a few days.
	Medium =   "medium"    #: A delay of multiple days.
	High =     "high"      #: A delay of a few weeks.
	Critical = "critical"  #: A delay of multiple weeks.


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

		Assigning a risk register adds this element to it, and sets the register's root as the root of this element and of
		every element below it.

		:returns:           The parent, or ``None``.
		:raises ValueError: If ``None`` is assigned.
		:raises TypeError:  If the assigned parent isn't of type :class:`RiskManagement`.
		:raises TypeError:  If a parent is assigned to a :class:`RiskManagement`, which has no parent.
		:raises ValueError: If the element is already part of a risk register.
		:raises ValueError: If the risk register already contains an element of the same kind and ID.
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
			ex = ValueError(f"Element is already part of a risk register.")
			ex.add_note(f"Got element '{self!r}'.")
			raise ex

		parent._AddElement(self)
		self._parent = parent
		self._root =   parent._root
		for element in self.IterateElements():
			element._root = parent._root

	@readonly
	def Root(self) -> Nullable[RiskManagement]:
		"""
		Read-only property to access the risk register's root (:attr:`_root`).

		The root is maintained by :attr:`Parent`: assigning a parent sets it for this element and every element below it.

		:returns: The root, or ``None`` while the element isn't part of a risk register.
		"""
		return self._root

	@abstractmethod
	def IterateElements(self) -> Generator[Base, None, None]:
		"""
		Iterate every element below this one.

		:returns: A generator of the elements below this one.
		"""


@export
class RiskManagement(Base):
	"""
	The risk register: every risk by its ID, the register's version and its optional name.

	It is its own root, and has no parent. An element joins it by naming it as its parent, in the element's constructor
	or by :attr:`~Base.Parent`.
	"""

	_version: SemanticVersion  #: The version of the risk register.
	_name:    Nullable[str]    #: The name of the risk register, if given.
	_risks:   dict[str, Risk]  #: The risks, by ID.

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

		self._root =    self
		self._version = version
		self._name =    name
		self._risks =   {}

	@Base.Parent.setter
	def Parent(self, parent: None) -> None:
		ex = TypeError(f"A '{getFullyQualifiedName(self)}' has no parent.")
		ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
		raise ex

	def _AddElement(self, element: Risk) -> None:
		"""
		Add a risk, which names the risk register as its parent.

		:param element:     The risk.
		:raises ValueError: If the risk register already contains a risk of the same ID.
		"""
		if element._id in self._risks:
			raise ValueError(f"Risk '{element._id}' already exists in the risk register.")

		self._risks[element._id] = element

	def IterateElements(self) -> Generator[Base, None, None]:
		"""
		Iterate the risks of the risk register.

		:returns: A generator of every element below the risk register.
		"""
		yield from self._risks.values()

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

	def __repr__(self) -> str:
		"""
		Return a representation of the risk register for debugging.

		A register of version 1.0.0 with 3 risks reads ``<RiskManagement 1.0.0: 3 risks>``.

		:returns: The register's version and its number of risks.
		"""
		return f"<RiskManagement {self._version}: {len(self._risks)} risks>"


@export
class BaseWithID(Base):
	"""
	Base-class of the elements a risk register holds by ID: an ID and a description.
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

	def IterateElements(self) -> Generator[Base, None, None]:
		"""
		Iterate the elements below this one, which are none.

		:returns: An empty generator.
		"""
		yield from ()


# A class with a property named like a class - ``Probability``, ``Impact`` - can't name that class in the annotation of
# a field: the class body's namespace, where annotations are evaluated, binds the name to the property.
_Probability = Probability
_Impact =      Impact


@export
class Risk(BaseWithID):
	"""
	A risk: its title and description, the probability it occurs, its impact and its state.
	"""

	_title:       str           #: The risk's title.
	_probability: _Probability  #: The probability the risk occurs.
	_impact:      _Impact       #: The impact of the risk, if it occurs.
	_state:       RiskState     #: The state of the risk in its life cycle.

	def __init__(
		self,
		identifier: str,
		title: str,
		description: str,
		probability: Probability,
		impact: Impact,
		state: RiskState = RiskState.Open,
		keyValuePairs: Nullable[Mapping[str, Any]] = None,
		*,
		parent: Nullable[RiskManagement] = None
	) -> None:
		"""
		Initializes a risk, and adds it to its risk register.

		:param identifier:    The risk's ID, unique among the risks of a risk register.
		:param title:         The risk's title.
		:param description:   The risk's description.
		:param probability:   The probability the risk occurs.
		:param impact:        The impact of the risk, if it occurs.
		:param state:         Optional, the state of the risk. Default: ``RiskState.Open``.
		:param keyValuePairs: Optional, the key-value pairs. Default: ``None``.
		:param parent:        Optional, the risk register containing the risk. Default: ``None``.
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
		:raises ValueError:   If parameter ``title`` is ``None``.
		:raises TypeError:    If parameter ``title`` isn't of type :class:`str`.
		:raises ValueError:   If parameter ``title`` is empty.
		:raises ValueError:   If parameter ``probability`` is ``None``.
		:raises TypeError:    If parameter ``probability`` isn't of type :class:`Probability`.
		:raises ValueError:   If parameter ``impact`` is ``None``.
		:raises TypeError:    If parameter ``impact`` isn't of type :class:`Impact`.
		:raises ValueError:   If parameter ``state`` is ``None``.
		:raises TypeError:    If parameter ``state`` isn't of type :class:`RiskState`.
		:raises ValueError:   If the risk register already contains a risk of this ID.
		"""
		super().__init__(identifier, description, keyValuePairs, parent=parent)

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

		self._title =       title
		self._probability = probability
		self._impact =      impact
		self._state =       state

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

	def __repr__(self) -> str:
		"""
		Return a representation of the risk for debugging.

		An open risk ``R1`` of medium probability and high impact reads ``<Risk R1: open, probability medium,
		impact high>``.

		:returns: The risk's ID, state, probability and impact.
		"""
		return f"<Risk {self._id}: {self._state}, probability {self._probability}, impact {self._impact}>"
