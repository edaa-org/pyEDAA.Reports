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
Abstract data model of requirements management.

A :class:`RequirementSpecification` is the root: it registers the persons, personas, labels, documents and layers its
requirements refer to, and every requirement by its ID.

A :class:`Requirement` has a title, a description, a creation time, a state, a kind and an obligation. A requirement
contains child requirements, which refine it.
"""
from __future__            import annotations

from datetime              import datetime
from typing                import Any, Callable, ClassVar, Generator, Mapping, Optional as Nullable, Self

from pyTooling.Common      import getFullyQualifiedName, StringEnum
from pyTooling.Decorators  import export, readonly
from pyTooling.MetaClasses import ExtendedType, abstractmethod
from pyTooling.Versioning  import SemanticVersion

from pyEDAA.Reports        import KeyValuePairsMixin, Person


@export
class ItemState(StringEnum):
	"""
	The state of an item in its life cycle.

	An item is open from :attr:`Placeholder` over :attr:`Draft`, :attr:`InReview`, :attr:`Final` and :attr:`Implemented`
	to :attr:`Verified`. It ends :attr:`Closed` after its verification, or :attr:`Rejected` or :attr:`Obsolete` at any
	time.
	"""

	Placeholder = "placeholder"  #: Reserved, e.g. an ID and a title, but not yet written.
	Draft =       "draft"        #: Written, but not yet reviewed.
	InReview =    "in-review"    #: Under review by its stakeholders.
	Final =       "final"        #: Reviewed and agreed by its stakeholders; it binds the design.
	Implemented = "implemented"  #: Implemented, but not yet verified.
	Verified =    "verified"     #: Implemented and verified; open for a regression.
	Closed =      "closed"       #: Verified and released, e.g. in a baseline; it changes no more.
	Rejected =    "rejected"     #: Not accepted by its stakeholders.
	Obsolete =    "obsolete"     #: No longer valid, e.g. replaced by another one, split or merged.


@export
class RequirementKind(StringEnum):
	"""
	The kind of a requirement: what it constrains.

	The kinds follow the requirement types of ISO/IEC/IEEE 29148, with safety and security as kinds of their own, as
	functional safety and security standards treat them separately.
	"""

	Functional =    "functional"     #: A function the system performs, e.g. a register map or a protocol's behavior.
	Performance =   "performance"    #: How well a function is performed, e.g. a clock frequency, latency or throughput.
	Quality =       "quality"        #: A quality attribute, e.g. reliability, maintainability or usability.
	Safety =        "safety"         #: A measure against hazards, e.g. a safety mechanism of ISO 26262 or IEC 61508.
	Security =      "security"       #: A measure against threats, e.g. encrypted bitstreams or secure boot.
	Interface =     "interface"      #: An interface to another system, e.g. a pin-out, a bus or a signal level.
	Environmental = "environmental"  #: An operating condition, e.g. a temperature range, vibration or EMC.
	Constraint =    "constraint"     #: A design or implementation constraint, e.g. an FPGA family or a language.
	Regulatory =    "regulatory"     #: A standard, law or certification the system complies with.
	Other =         "other"          #: Any other requirement.


@export
class Obligation(StringEnum):
	"""
	The obligation of a requirement: whether it must, should or may be met.

	The levels are those of the keywords of ISO/IEC/IEEE 29148 (*shall*, *should*, *may*) and of RFC 2119 (*MUST*,
	*SHOULD*, *MAY*). A negated requirement (*shall not*) has the obligation of its positive keyword; the negation is part
	of its text.
	"""

	Mandatory =   "mandatory"    #: Binding: the requirement must be met (*shall*, *must*).
	Recommended = "recommended"  #: A goal: the requirement should be met, deviations are justified (*should*).
	Optional =    "optional"     #: A permission: the requirement may be met (*may*).


# A class with a property named like a class - ``Obligation`` - can't name that class in the annotation of a field: the
# class body's namespace, where annotations are evaluated, binds the name to the property.
_Obligation = Obligation


@export
class Base(KeyValuePairsMixin, metaclass=ExtendedType, slots=True):
	"""
	Base-class of every element of the requirements model: key-value pairs, a reference to the element containing it, and
	a reference to the specification it is part of.
	"""

	_PARENT_TYPE: ClassVar[tuple[type, ...]]          #: The types a parent may have; set by each class with a parent.

	_parent:      Nullable[Base]                      #: The element containing this one, or ``None``.
	_root:        Nullable[RequirementSpecification]  #: The specification, or ``None`` while the element isn't in one.

	def __init__(self, *, keyValuePairs: Nullable[Mapping[str, Any]] = None, parent: Nullable[Base] = None) -> None:
		"""
		Initializes an element with its key-value pairs, its parent, and the parent's specification.

		The parent doesn't list the element yet: the class setting the field the parent stores it by - an ID - adds it with
		``parent._AddElement(self)``.

		:param keyValuePairs: Optional, the key-value pairs. Default: ``None``.
		:param parent:        Optional, the element containing this one. Default: ``None``.
		:raises TypeError:    If parameter ``keyValuePairs`` isn't a mapping.
		:raises TypeError:    If parameter ``keyValuePairs`` contains a key not of type :class:`str`.
		:raises ValueError:   If parameter ``keyValuePairs`` contains an empty key.
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

		Assigning a parent to an element without one adds the element to it, and sets the parent's specification as the
		specification of this element and of every element below it.

		:returns:           The parent, or ``None``.
		:raises ValueError: If ``None`` is assigned.
		:raises TypeError:  If the assigned parent isn't of a type this class declares in :attr:`_PARENT_TYPE`.
		:raises TypeError:  If a parent is assigned to a :class:`RequirementSpecification`, which has no parent.
		:raises ValueError: If the element already has a parent.
		:raises ValueError: If the assigned parent's specification already contains an element of an ID of this element or
		                    of an element below it.
		"""
		return self._parent

	@Parent.setter
	def Parent(self, parent: Base) -> None:
		if parent is None:
			raise ValueError(f"Parameter 'parent' is None.")
		elif not isinstance(parent, self._PARENT_TYPE):
			typeNames = " or ".join(f"'{parentType.__name__}'" for parentType in self._PARENT_TYPE)
			ex = TypeError(f"Parameter 'parent' is not of type {typeNames}.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		if self._parent is not None:
			raise ValueError(f"{self.__class__.__name__} already has a parent.")

		parent._AddElement(self)
		self._parent = parent
		self._root =   parent._root
		for element in self.IterateElements():
			element._root = parent._root

	@readonly
	def Root(self) -> Nullable[RequirementSpecification]:
		"""
		Read-only property to access the specification this element is part of (:attr:`_root`).

		The specification is maintained by :attr:`Parent`: assigning a parent sets it for this element and every element
		below it.

		:returns: The specification, or ``None`` while the element isn't part of one.
		"""
		return self._root

	@abstractmethod
	def IterateElements(self) -> Generator[Base, None, None]:
		"""
		Iterate every element below this one, depth-first.

		:returns: A generator of the elements below this one.
		"""


@export
class BaseWithID(Base):
	"""
	Base-class of the elements of the requirements model, which have an ID and a description.

	The ID is unique among the elements of the same class in a specification.
	"""

	_id:          str  #: The element's ID.
	_description: str  #: The element's description, or ``""``.

	def __init__(
		self,
		identifier: str,
		*,
		description: str = "",
		keyValuePairs: Nullable[Mapping[str, Any]] = None,
		parent: Nullable[Base] = None
	) -> None:
		"""
		Initializes an element with its ID, its description, its key-value pairs and its parent.

		:param identifier:    The element's ID.
		:param description:   Optional, the element's description. Default: ``""``.
		:param keyValuePairs: Optional, the key-value pairs. Default: ``None``.
		:param parent:        Optional, the element containing this one. Default: ``None``.
		:raises TypeError:    If parameter ``keyValuePairs`` isn't a mapping.
		:raises TypeError:    If parameter ``keyValuePairs`` contains a key not of type :class:`str`.
		:raises ValueError:   If parameter ``keyValuePairs`` contains an empty key.
		:raises TypeError:    If parameter ``parent`` isn't of a type this class declares in :attr:`_PARENT_TYPE`.
		:raises ValueError:   If parameter ``identifier`` is ``None``.
		:raises TypeError:    If parameter ``identifier`` isn't of type :class:`str`.
		:raises ValueError:   If parameter ``identifier`` is empty.
		:raises ValueError:   If parameter ``description`` is ``None``.
		:raises TypeError:    If parameter ``description`` isn't of type :class:`str`.
		"""
		super().__init__(keyValuePairs=keyValuePairs, parent=parent)

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

		:returns: The description, or ``""``.
		"""
		return self._description


@export
class RequirementSpecification(Base):
	"""
	The root of the requirements model: the requirements of a system, and the personas, labels, documents and layers they
	refer to.

	It registers every requirement by its ID - also a child requirement -, and is its own specification.

	Persons have no parent: the specification registers the persons its items refer to by their user IDs, and a person may
	be registered in several specifications.
	"""

	_name:         Nullable[str]           #: The specification's name, or ``None``.
	_version:      SemanticVersion         #: The version of the specification.
	_persons:      dict[str, Person]       #: The persons, by user ID.
	_personas:     dict[str, Persona]      #: The personas, by ID.
	_labels:       dict[str, Label]        #: The labels, by ID.
	_documents:    dict[str, Document]     #: The documents, by ID.
	_layers:       dict[str, Layer]        #: The layers, by ID.
	_requirements: dict[str, Requirement]  #: Every requirement, by ID, in the order they were added.

	def __init__(
		self,
		version: SemanticVersion,
		name: Nullable[str] = None,
		*,
		keyValuePairs: Nullable[Mapping[str, Any]] = None
	) -> None:
		"""
		Initializes an empty requirement specification.

		:param version:       The version of the specification.
		:param name:          Optional, the specification's name. Default: ``None``.
		:param keyValuePairs: Optional, the key-value pairs. Default: ``None``.
		:raises TypeError:    If parameter ``keyValuePairs`` isn't a mapping.
		:raises TypeError:    If parameter ``keyValuePairs`` contains a key not of type :class:`str`.
		:raises ValueError:   If parameter ``keyValuePairs`` contains an empty key.
		:raises ValueError:   If parameter ``version`` is ``None``.
		:raises TypeError:    If parameter ``version`` isn't of type :class:`~pyTooling.Versioning.SemanticVersion`.
		:raises TypeError:    If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError:   If parameter ``name`` is empty.
		"""
		super().__init__(keyValuePairs=keyValuePairs)

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
		self._name =         name
		self._version =      version
		self._persons =      {}
		self._personas =     {}
		self._labels =       {}
		self._documents =    {}
		self._layers =       {}
		self._requirements = {}

	@Base.Parent.setter
	def Parent(self, parent: None) -> None:
		ex = TypeError(f"A '{getFullyQualifiedName(self)}' has no parent.")
		ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
		raise ex

	def _AddElement(self, element: BaseWithID) -> None:
		"""
		Register a persona, label, document, layer or top-level requirement, which names the specification as its parent.

		:param element:     The element.
		:raises ValueError: If the specification already contains an element of the same class and ID, or a requirement
		                    below a requirement has the ID of a registered one.
		"""
		if isinstance(element, BaseItem):
			self._AddItems(element)
			return

		if isinstance(element, Persona):
			elements = self._personas
		elif isinstance(element, Label):
			elements = self._labels
		elif isinstance(element, Document):
			elements = self._documents
		else:
			elements = self._layers

		if element._id in elements:
			raise ValueError(f"{element.__class__.__name__} '{element._id}' already exists in the specification.")

		elements[element._id] = element

	def _AddItems(self, item: BaseItem) -> None:
		"""
		Register an item and every item below it by their IDs.

		Either all of them are registered, or none.

		:param item:        The item joining the specification.
		:raises ValueError: If an ID of these items is registered already, or used twice by them.
		"""
		items =   self._requirements
		ids =     set()
		subtree = (item, *item.IterateDescendants())
		for element in subtree:
			if element._id in items or element._id in ids:
				raise ValueError(f"{element.__class__.__name__} '{element._id}' already exists in the specification.")

			ids.add(element._id)

		for element in subtree:
			items[element._id] = element

	def IterateElements(self) -> Generator[Base, None, None]:
		"""
		Iterate the personas, labels, documents and layers, then the top-level requirements, each followed by the elements
		below it.

		:returns: A generator of every element below the specification.
		"""
		yield from (*self._personas.values(), *self._labels.values(), *self._documents.values(), *self._layers.values())
		for requirement in self._requirements.values():
			if requirement._parent is self:
				yield requirement
				yield from requirement.IterateElements()

	@readonly
	def Name(self) -> Nullable[str]:
		"""
		Read-only property to access the specification's name (:attr:`_name`).

		:returns: The name, or ``None``.
		"""
		return self._name

	@readonly
	def Version(self) -> SemanticVersion:
		"""
		Read-only property to access the version of the specification (:attr:`_version`).

		:returns: The version.
		"""
		return self._version

	@readonly
	def Persons(self) -> dict[str, Person]:
		"""
		Read-only property to access the persons (:attr:`_persons`).

		:returns: The persons, by user ID.
		"""
		return self._persons

	def AddPerson(self, person: Person) -> None:
		"""
		Register a person, whom the specification's items can refer to.

		E.g. an author or an owner of requirements. A person has no parent: the same person may be registered in several
		specifications.

		:param person:      The person.
		:raises ValueError: If parameter ``person`` is ``None``.
		:raises TypeError:  If parameter ``person`` isn't of type :class:`~pyEDAA.Reports.Person`.
		:raises ValueError: If the specification already contains a person of this user ID.
		"""
		if person is None:
			raise ValueError(f"Parameter 'person' is None.")
		elif not isinstance(person, Person):
			ex = TypeError(f"Parameter 'person' is not of type 'Person'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(person)}'.")
			raise ex
		elif person._userID in self._persons:
			raise ValueError(f"Person '{person._userID}' already exists in the specification.")

		self._persons[person._userID] = person

	@readonly
	def Personas(self) -> dict[str, Persona]:
		"""
		Read-only property to access the personas (:attr:`_personas`).

		:returns: The personas, by ID.
		"""
		return self._personas

	@readonly
	def Labels(self) -> dict[str, Label]:
		"""
		Read-only property to access the labels (:attr:`_labels`).

		:returns: The labels, by ID.
		"""
		return self._labels

	@readonly
	def Documents(self) -> dict[str, Document]:
		"""
		Read-only property to access the documents (:attr:`_documents`).

		:returns: The documents, by ID.
		"""
		return self._documents

	@readonly
	def Layers(self) -> dict[str, Layer]:
		"""
		Read-only property to access the layers (:attr:`_layers`).

		:returns: The layers, by ID.
		"""
		return self._layers

	@readonly
	def Requirements(self) -> dict[str, Requirement]:
		"""
		Read-only property to access every requirement (:attr:`_requirements`), also the child requirements.

		:returns: The requirements, by ID, in the order they were added.
		"""
		return self._requirements

	def IterateRequirements(
		self,
		predicate: Nullable[Callable[[Requirement], bool]] = None
	) -> Generator[Requirement, None, None]:
		"""
		Iterate all or selected requirements, also the child requirements, in the order they were added.

		If parameter ``predicate`` is not None, the given filter function is used to skip requirements in the generator.

		:param predicate: Optional, filter function accepting a requirement and returning a boolean. Default: ``None``.
		:returns:         A generator of the requirements.
		"""
		if predicate is None:
			yield from self._requirements.values()
		else:
			for requirement in self._requirements.values():
				if predicate(requirement):
					yield requirement


@export
class BaseWithName(BaseWithID):
	"""
	Base-class of the elements a specification registers for its requirements to refer to: an ID, a name and a
	description.

	Its parent is the :class:`RequirementSpecification`.
	"""

	_PARENT_TYPE: ClassVar[tuple[type, ...]] = (RequirementSpecification, )  #: The element is in a specification.

	_name:        str                                                        #: The element's name.

	def __init__(
		self,
		identifier: str,
		name: str,
		*,
		description: str = "",
		keyValuePairs: Nullable[Mapping[str, Any]] = None,
		parent: Nullable[RequirementSpecification] = None
	) -> None:
		"""
		Initializes an element with its ID, name and description, and registers it in its specification.

		:param identifier:    The element's ID.
		:param name:          The element's name.
		:param description:   Optional, the element's description. Default: ``""``.
		:param keyValuePairs: Optional, the key-value pairs. Default: ``None``.
		:param parent:        Optional, the specification. Default: ``None``.
		:raises TypeError:    If parameter ``keyValuePairs`` isn't a mapping.
		:raises TypeError:    If parameter ``keyValuePairs`` contains a key not of type :class:`str`.
		:raises ValueError:   If parameter ``keyValuePairs`` contains an empty key.
		:raises TypeError:    If parameter ``parent`` isn't of type :class:`RequirementSpecification`.
		:raises ValueError:   If parameter ``identifier`` is ``None``.
		:raises TypeError:    If parameter ``identifier`` isn't of type :class:`str`.
		:raises ValueError:   If parameter ``identifier`` is empty.
		:raises ValueError:   If parameter ``description`` is ``None``.
		:raises TypeError:    If parameter ``description`` isn't of type :class:`str`.
		:raises ValueError:   If parameter ``name`` is ``None``.
		:raises TypeError:    If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError:   If parameter ``name`` is empty.
		:raises ValueError:   If the specification already contains an element of this class and ID.
		"""
		super().__init__(identifier, description=description, keyValuePairs=keyValuePairs, parent=parent)

		if name is None:
			raise ValueError(f"Parameter 'name' is None.")
		elif not isinstance(name, str):
			ex = TypeError(f"Parameter 'name' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(name)}'.")
			raise ex
		elif name == "":
			raise ValueError(f"Parameter 'name' is empty.")

		self._name = name

		if parent is not None:
			parent._AddElement(self)

	@readonly
	def Name(self) -> str:
		"""
		Read-only property to access the element's name (:attr:`_name`).

		:returns: The name.
		"""
		return self._name

	def IterateElements(self) -> Generator[Base, None, None]:
		"""
		Iterate the elements below this one, which are none.

		:returns: An empty generator.
		"""
		yield from ()


@export
class Persona(BaseWithName):
	"""
	A persona: a role a user of the system acts in, like the role of a use case or a user story.

	E.g. an administrator, a reviewer or a quality inspector. A real person, e.g. an author, is a
	:class:`~pyEDAA.Reports.Person`.
	"""


@export
class Label(BaseWithName):
	"""
	A label to classify items across layers and kinds.

	E.g. a product variant, a release or a customer.
	"""


@export
class Document(BaseWithName):
	"""
	A document attached to items.

	E.g. a datasheet, a schematic or a standard.
	"""


@export
class Layer(BaseWithName):
	"""
	A layer of the system: the items of one engineering discipline.

	E.g. electrical, mechanical, FPGA firmware and software requirements are four layers. Each item belongs to at most one
	layer. A requirement of one layer has its counterparts in other layers, e.g. an electrical requirement in the FPGA
	firmware, and this one in the software.
	"""


@export
class BaseItem(BaseWithID):
	"""
	Base-class of the items of a specification - requirements -: a title, a creation time, a state, and its child items.

	A child item has the class of its parent; its ID is unique in the specification, too.
	"""

	_title:    str              #: The item's title.
	_created:  datetime         #: The time the item was created.
	_state:    ItemState        #: The item's state in its life cycle.
	_children: dict[str, Self]  #: The child items, by ID.

	def __init__(
		self,
		identifier: str,
		title: str,
		created: datetime,
		*,
		description: str = "",
		state: ItemState = ItemState.Draft,
		keyValuePairs: Nullable[Mapping[str, Any]] = None,
		parent: Nullable[BaseItem | RequirementSpecification] = None
	) -> None:
		"""
		Initializes an item with its title, creation time and state.

		:param identifier:    The item's ID.
		:param title:         The item's title.
		:param created:       The time the item was created, with a time zone.
		:param description:   Optional, the item's description. Default: ``""``.
		:param state:         Optional, the item's state. Default: :attr:`ItemState.Draft`.
		:param keyValuePairs: Optional, the key-value pairs. Default: ``None``.
		:param parent:        Optional, the parent item or the specification. Default: ``None``.
		:raises TypeError:    If parameter ``keyValuePairs`` isn't a mapping.
		:raises TypeError:    If parameter ``keyValuePairs`` contains a key not of type :class:`str`.
		:raises ValueError:   If parameter ``keyValuePairs`` contains an empty key.
		:raises TypeError:    If parameter ``parent`` isn't of a type this class declares in :attr:`_PARENT_TYPE`.
		:raises ValueError:   If parameter ``identifier`` is ``None``.
		:raises TypeError:    If parameter ``identifier`` isn't of type :class:`str`.
		:raises ValueError:   If parameter ``identifier`` is empty.
		:raises ValueError:   If parameter ``description`` is ``None``.
		:raises TypeError:    If parameter ``description`` isn't of type :class:`str`.
		:raises ValueError:   If parameter ``title`` is ``None``.
		:raises TypeError:    If parameter ``title`` isn't of type :class:`str`.
		:raises ValueError:   If parameter ``title`` is empty.
		:raises ValueError:   If parameter ``created`` is ``None``.
		:raises TypeError:    If parameter ``created`` isn't of type :class:`~datetime.datetime`.
		:raises ValueError:   If parameter ``created`` has no time zone.
		:raises ValueError:   If parameter ``state`` is ``None``.
		:raises TypeError:    If parameter ``state`` isn't of type :class:`ItemState`.
		"""
		super().__init__(identifier, description=description, keyValuePairs=keyValuePairs, parent=parent)

		if title is None:
			raise ValueError(f"Parameter 'title' is None.")
		elif not isinstance(title, str):
			ex = TypeError(f"Parameter 'title' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(title)}'.")
			raise ex
		elif title == "":
			raise ValueError(f"Parameter 'title' is empty.")

		if created is None:
			raise ValueError(f"Parameter 'created' is None.")
		elif not isinstance(created, datetime):
			ex = TypeError(f"Parameter 'created' is not of type 'datetime'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(created)}'.")
			raise ex
		elif created.utcoffset() is None:
			ex = ValueError(f"Parameter 'created' has no time zone.")
			ex.add_note(f"Got value '{created.isoformat()}'.")
			raise ex

		if state is None:
			raise ValueError(f"Parameter 'state' is None.")
		elif not isinstance(state, ItemState):
			ex = TypeError(f"Parameter 'state' is not of type 'ItemState'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(state)}'.")
			raise ex

		self._title =    title
		self._created =  created
		self._state =    state
		self._children = {}

	def _AddElement(self, element: Self) -> None:
		"""
		Add a child item, which names this item as its parent, and register it with every item below it in the
		specification.

		:param element:     The child item.
		:raises ValueError: If the specification already contains an item of an ID of the child or an item below it.
		:raises ValueError: If this item isn't part of a specification, and has a child of this ID already.
		"""
		if self._root is not None:
			self._root._AddItems(element)
		elif element._id in self._children:
			raise ValueError(f"{self.__class__.__name__} '{self._id}' already has a child '{element._id}'.")

		self._children[element._id] = element

	def IterateElements(self) -> Generator[Base, None, None]:
		"""
		Iterate the child items, each followed by the elements below it.

		:returns: A generator of the elements below this item.
		"""
		for child in self._children.values():
			yield child
			yield from child.IterateElements()

	@readonly
	def Title(self) -> str:
		"""
		Read-only property to access the item's title (:attr:`_title`).

		:returns: The title.
		"""
		return self._title

	@readonly
	def Created(self) -> datetime:
		"""
		Read-only property to access the time the item was created (:attr:`_created`).

		:returns: The time, with a time zone.
		"""
		return self._created

	@property
	def State(self) -> ItemState:
		"""
		Property to access the item's state in its life cycle (:attr:`_state`).

		:returns:           The state.
		:raises ValueError: If ``None`` is assigned.
		:raises TypeError:  If the assigned state isn't of type :class:`ItemState`.
		"""
		return self._state

	@State.setter
	def State(self, state: ItemState) -> None:
		if state is None:
			raise ValueError(f"Parameter 'state' is None.")
		elif not isinstance(state, ItemState):
			ex = TypeError(f"Parameter 'state' is not of type 'ItemState'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(state)}'.")
			raise ex

		self._state = state

	@readonly
	def Children(self) -> dict[str, Self]:
		"""
		Read-only property to access the child items (:attr:`_children`).

		:returns: The child items, by ID.
		"""
		return self._children

	def IterateChildren(self, predicate: Nullable[Callable[[Self], bool]] = None) -> Generator[Self, None, None]:
		"""
		Iterate all or selected child items.

		If parameter ``predicate`` is not None, the given filter function is used to skip items in the generator.

		:param predicate: Optional, filter function accepting an item and returning a boolean. Default: ``None``.
		:returns:         A generator of the child items.
		"""
		if predicate is None:
			yield from self._children.values()
		else:
			for child in self._children.values():
				if predicate(child):
					yield child

	def IterateDescendants(self, predicate: Nullable[Callable[[Self], bool]] = None) -> Generator[Self, None, None]:
		"""
		Iterate all or selected items below this one - its children, grandchildren, ... -, depth-first: each child
		followed by the items below it.

		If parameter ``predicate`` is not None, the given filter function is used to skip items in the generator. A skipped
		item's children are still iterated.

		:param predicate: Optional, filter function accepting an item and returning a boolean. Default: ``None``.
		:returns:         A generator of the items below this one.
		"""
		for child in self._children.values():
			if predicate is None or predicate(child):
				yield child

			yield from child.IterateDescendants(predicate)


@export
class Requirement(BaseItem):
	"""
	A requirement: a condition or capability the system must, should or may meet, its kind and its obligation.

	Its parent is the :class:`RequirementSpecification` for a top-level requirement, or the :class:`Requirement` it
	refines - a child requirement. The specification registers either by its ID.
	"""

	_PARENT_TYPE: ClassVar[tuple[type, ...]]  #: In a requirement or the specification; assigned below.

	_kind:        RequirementKind             #: What the requirement constrains.
	_obligation:  _Obligation                 #: Whether the requirement must, should or may be met.

	def __init__(
		self,
		identifier: str,
		title: str,
		kind: RequirementKind,
		created: datetime,
		*,
		obligation: Obligation = Obligation.Mandatory,
		description: str = "",
		state: ItemState = ItemState.Draft,
		keyValuePairs: Nullable[Mapping[str, Any]] = None,
		parent: Nullable[Requirement | RequirementSpecification] = None
	) -> None:
		"""
		Initializes a requirement, adds it to its parent, and registers it in its specification.

		:param identifier:    The requirement's ID.
		:param title:         The requirement's title.
		:param kind:          What the requirement constrains.
		:param created:       The time the requirement was created, with a time zone.
		:param obligation:    Optional, whether the requirement must, should or may be met. Default:
		                      :attr:`Obligation.Mandatory`.
		:param description:   Optional, the requirement's description. Default: ``""``.
		:param state:         Optional, the requirement's state. Default: :attr:`ItemState.Draft`.
		:param keyValuePairs: Optional, the key-value pairs. Default: ``None``.
		:param parent:        Optional, the requirement this one refines, or the specification. Default: ``None``.
		:raises TypeError:    If parameter ``keyValuePairs`` isn't a mapping.
		:raises TypeError:    If parameter ``keyValuePairs`` contains a key not of type :class:`str`.
		:raises ValueError:   If parameter ``keyValuePairs`` contains an empty key.
		:raises TypeError:    If parameter ``parent`` isn't of type :class:`Requirement` or
		                      :class:`RequirementSpecification`.
		:raises ValueError:   If parameter ``identifier`` is ``None``.
		:raises TypeError:    If parameter ``identifier`` isn't of type :class:`str`.
		:raises ValueError:   If parameter ``identifier`` is empty.
		:raises ValueError:   If parameter ``description`` is ``None``.
		:raises TypeError:    If parameter ``description`` isn't of type :class:`str`.
		:raises ValueError:   If parameter ``title`` is ``None``.
		:raises TypeError:    If parameter ``title`` isn't of type :class:`str`.
		:raises ValueError:   If parameter ``title`` is empty.
		:raises ValueError:   If parameter ``created`` is ``None``.
		:raises TypeError:    If parameter ``created`` isn't of type :class:`~datetime.datetime`.
		:raises ValueError:   If parameter ``created`` has no time zone.
		:raises ValueError:   If parameter ``state`` is ``None``.
		:raises TypeError:    If parameter ``state`` isn't of type :class:`ItemState`.
		:raises ValueError:   If parameter ``kind`` is ``None``.
		:raises TypeError:    If parameter ``kind`` isn't of type :class:`RequirementKind`.
		:raises ValueError:   If parameter ``obligation`` is ``None``.
		:raises TypeError:    If parameter ``obligation`` isn't of type :class:`Obligation`.
		:raises ValueError:   If the specification already contains a requirement of this ID.
		"""
		super().__init__(
			identifier,
			title,
			created,
			description=description,
			state=state,
			keyValuePairs=keyValuePairs,
			parent=parent
		)

		if kind is None:
			raise ValueError(f"Parameter 'kind' is None.")
		elif not isinstance(kind, RequirementKind):
			ex = TypeError(f"Parameter 'kind' is not of type 'RequirementKind'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(kind)}'.")
			raise ex

		if obligation is None:
			raise ValueError(f"Parameter 'obligation' is None.")
		elif not isinstance(obligation, Obligation):
			ex = TypeError(f"Parameter 'obligation' is not of type 'Obligation'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(obligation)}'.")
			raise ex

		self._kind =       kind
		self._obligation = obligation

		if parent is not None:
			parent._AddElement(self)

	@readonly
	def Kind(self) -> RequirementKind:
		"""
		Read-only property to access what the requirement constrains (:attr:`_kind`).

		:returns: The requirement's kind.
		"""
		return self._kind

	@readonly
	def Obligation(self) -> Obligation:
		"""
		Read-only property to access whether the requirement must, should or may be met (:attr:`_obligation`).

		:returns: The requirement's obligation.
		"""
		return self._obligation


Requirement._PARENT_TYPE = (Requirement, RequirementSpecification)
