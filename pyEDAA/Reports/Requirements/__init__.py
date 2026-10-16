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
items refer to, and every requirement and specification item by its ID.

A :class:`Requirement` has a title, a description, a creation time, a state, a kind and an obligation. It names its
authors and owners (:class:`~pyEDAA.Reports.Person`), the personas it is about (:class:`Persona`), its labels
(:class:`Label`), the documents attached to it (:class:`Document`), and the layer it belongs to (:class:`Layer`) - all
registered in the same specification. A requirement contains child requirements, which refine it.

A :class:`SpecificationItem` mirrors a requirement: it states how the system meets requirements. Specification items and
requirements are in an N:M relation.

An item's :class:`Link` states a relationship to another item, e.g. to its counterpart in another layer.
"""
from __future__            import annotations

from datetime              import datetime
from typing                import Any, Callable, ClassVar, Generator, Iterable, Mapping, Optional as Nullable, Self

from pyTooling.Common      import getFullyQualifiedName, StringEnum
from pyTooling.Decorators  import export, readonly
from pyTooling.MetaClasses import ExtendedType
from pyTooling.Versioning  import SemanticVersion

from pyEDAA.Reports        import KeyValuePairsMixin, Person, ReportException


@export
class RequirementsError(ReportException):
	"""Base-exception of the requirements model."""


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

		:returns:                  The parent, or ``None``.
		:raises ValueError:        If ``None`` is assigned.
		:raises TypeError:         If the assigned parent isn't of a type this class declares in :attr:`_PARENT_TYPE`.
		:raises TypeError:         If a parent is assigned to a :class:`RequirementSpecification`, which has no parent.
		:raises RequirementsError: If the element already has a parent.
		:raises RequirementsError: If the assigned parent's specification already contains an element of an ID of this
		                           element or of an element below it.
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
			raise RequirementsError(f"{self.__class__.__name__} already has a parent.")

		parent._AddElement(self)
		self._parent = parent
		self._root =   parent._root

	@readonly
	def Root(self) -> Nullable[RequirementSpecification]:
		"""
		Read-only property to access the specification this element is part of (:attr:`_root`).

		The specification is maintained by :attr:`Parent`: assigning a parent sets it for this element and every element
		below it.

		:returns: The specification, or ``None`` while the element isn't part of one.
		"""
		return self._root


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
	The root of the requirements model: the requirements and specification items of a system, and the personas, labels,
	documents and layers they refer to.

	It registers every requirement and every specification item by its ID - also a child item -, and is its own
	specification.

	Persons have no parent: the specification registers the persons its items refer to by their user IDs, and a person may
	be registered in several specifications.
	"""

	_name:               Nullable[str]                 #: The specification's name, or ``None``.
	_version:            SemanticVersion               #: The version of the specification.
	_persons:            dict[str, Person]             #: The persons, by user ID.
	_personas:           dict[str, Persona]            #: The personas, by ID.
	_labels:             dict[str, Label]              #: The labels, by ID.
	_documents:          dict[str, Document]           #: The documents, by ID.
	_layers:             dict[str, Layer]              #: The layers, by ID.
	_requirements:       dict[str, Requirement]        #: Every requirement, by ID, in the order they were added.
	_specificationItems: dict[str, SpecificationItem]  #: Every specification item, by ID, in the order they were added.

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

		self._root =               self
		self._name =               name
		self._version =            version
		self._persons =            {}
		self._personas =           {}
		self._labels =             {}
		self._documents =          {}
		self._layers =             {}
		self._requirements =       {}
		self._specificationItems = {}

	@Base.Parent.setter
	def Parent(self, parent: None) -> None:
		ex = TypeError(f"A '{getFullyQualifiedName(self)}' has no parent.")
		ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
		raise ex

	def _AddElement(self, element: BaseWithID) -> None:
		"""
		Register a persona, label, document, layer, top-level requirement or top-level specification item, which names the
		specification as its parent.

		:param element:            The element.
		:raises RequirementsError: If the specification already contains an element of the same class and ID, or an item
		                           below a requirement or specification item has the ID of a registered one.
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
			raise RequirementsError(f"{element.__class__.__name__} '{element._id}' already exists in the specification.")

		elements[element._id] = element

	def _AddItems(self, item: BaseItem) -> None:
		"""
		Register an item and every item below it by their IDs, and set the specification as their specification.

		Either all of them are registered, or none.

		:param item:               The item joining the specification.
		:raises RequirementsError: If an ID of these items is registered already, or used twice by them.
		"""
		items =   self._requirements if isinstance(item, Requirement) else self._specificationItems
		ids =     set()
		subtree = (item, *item.IterateDescendants())
		for element in subtree:
			if element._id in items or element._id in ids:
				raise RequirementsError(f"{element.__class__.__name__} '{element._id}' already exists in the specification.")

			ids.add(element._id)

		for element in subtree:
			element._root =     self
			items[element._id] = element

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

	def IteratePersons(self, predicate: Nullable[Callable[[Person], bool]] = None) -> Generator[Person, None, None]:
		"""
		Iterate all or selected persons.

		If parameter ``predicate`` is not None, the given filter function is used to skip persons in the generator.

		:param predicate: Optional, filter function accepting a person and returning a boolean. Default: ``None``.
		:returns:         A generator of the persons, in the order they were added.
		"""
		if predicate is None:
			yield from self._persons.values()
		else:
			for person in self._persons.values():
				if predicate(person):
					yield person

	def AddPerson(self, person: Person) -> None:
		"""
		Register a person, whom the specification's items can refer to.

		E.g. an author or an owner of requirements. A person has no parent: the same person may be registered in several
		specifications.

		:param person:             The person.
		:raises ValueError:        If parameter ``person`` is ``None``.
		:raises TypeError:         If parameter ``person`` isn't of type :class:`~pyEDAA.Reports.Person`.
		:raises RequirementsError: If the specification already contains a person of this user ID.
		"""
		if person is None:
			raise ValueError(f"Parameter 'person' is None.")
		elif not isinstance(person, Person):
			ex = TypeError(f"Parameter 'person' is not of type 'Person'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(person)}'.")
			raise ex
		elif person._userID in self._persons:
			raise RequirementsError(f"Person '{person._userID}' already exists in the specification.")

		self._persons[person._userID] = person

	@readonly
	def Personas(self) -> dict[str, Persona]:
		"""
		Read-only property to access the personas (:attr:`_personas`).

		:returns: The personas, by ID.
		"""
		return self._personas

	def IteratePersonas(self, predicate: Nullable[Callable[[Persona], bool]] = None) -> Generator[Persona, None, None]:
		"""
		Iterate all or selected personas.

		If parameter ``predicate`` is not None, the given filter function is used to skip personas in the generator.

		:param predicate: Optional, filter function accepting a persona and returning a boolean. Default: ``None``.
		:returns:         A generator of the personas, in the order they were added.
		"""
		if predicate is None:
			yield from self._personas.values()
		else:
			for persona in self._personas.values():
				if predicate(persona):
					yield persona

	@readonly
	def Labels(self) -> dict[str, Label]:
		"""
		Read-only property to access the labels (:attr:`_labels`).

		:returns: The labels, by ID.
		"""
		return self._labels

	def IterateLabels(self, predicate: Nullable[Callable[[Label], bool]] = None) -> Generator[Label, None, None]:
		"""
		Iterate all or selected labels.

		If parameter ``predicate`` is not None, the given filter function is used to skip labels in the generator.

		:param predicate: Optional, filter function accepting a label and returning a boolean. Default: ``None``.
		:returns:         A generator of the labels, in the order they were added.
		"""
		if predicate is None:
			yield from self._labels.values()
		else:
			for label in self._labels.values():
				if predicate(label):
					yield label

	@readonly
	def Documents(self) -> dict[str, Document]:
		"""
		Read-only property to access the documents (:attr:`_documents`).

		:returns: The documents, by ID.
		"""
		return self._documents

	def IterateDocuments(self, predicate: Nullable[Callable[[Document], bool]] = None) -> Generator[Document, None, None]:
		"""
		Iterate all or selected documents.

		If parameter ``predicate`` is not None, the given filter function is used to skip documents in the generator.

		:param predicate: Optional, filter function accepting a document and returning a boolean. Default: ``None``.
		:returns:         A generator of the documents, in the order they were added.
		"""
		if predicate is None:
			yield from self._documents.values()
		else:
			for document in self._documents.values():
				if predicate(document):
					yield document

	@readonly
	def Layers(self) -> dict[str, Layer]:
		"""
		Read-only property to access the layers (:attr:`_layers`).

		:returns: The layers, by ID.
		"""
		return self._layers

	def IterateLayers(self, predicate: Nullable[Callable[[Layer], bool]] = None) -> Generator[Layer, None, None]:
		"""
		Iterate all or selected layers.

		If parameter ``predicate`` is not None, the given filter function is used to skip layers in the generator.

		:param predicate: Optional, filter function accepting a layer and returning a boolean. Default: ``None``.
		:returns:         A generator of the layers, in the order they were added.
		"""
		if predicate is None:
			yield from self._layers.values()
		else:
			for layer in self._layers.values():
				if predicate(layer):
					yield layer

	@readonly
	def Requirements(self) -> dict[str, Requirement]:
		"""
		Read-only property to access every requirement (:attr:`_requirements`), also the child requirements.

		:returns: The requirements, by ID, in the order they were added.
		"""
		return self._requirements

	@readonly
	def SpecificationItems(self) -> dict[str, SpecificationItem]:
		"""
		Read-only property to access every specification item (:attr:`_specificationItems`), also the child items.

		:returns: The specification items, by ID, in the order they were added.
		"""
		return self._specificationItems

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

	def IterateSpecificationItems(
		self,
		predicate: Nullable[Callable[[SpecificationItem], bool]] = None
	) -> Generator[SpecificationItem, None, None]:
		"""
		Iterate all or selected specification items, also the child items, in the order they were added.

		If parameter ``predicate`` is not None, the given filter function is used to skip items in the generator.

		:param predicate: Optional, filter function accepting a specification item and returning a boolean. Default:
		                  ``None``.
		:returns:         A generator of the specification items.
		"""
		if predicate is None:
			yield from self._specificationItems.values()
		else:
			for specification in self._specificationItems.values():
				if predicate(specification):
					yield specification


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

		:param identifier:         The element's ID.
		:param name:               The element's name.
		:param description:        Optional, the element's description. Default: ``""``.
		:param keyValuePairs:      Optional, the key-value pairs. Default: ``None``.
		:param parent:             Optional, the specification. Default: ``None``.
		:raises TypeError:         If parameter ``keyValuePairs`` isn't a mapping.
		:raises TypeError:         If parameter ``keyValuePairs`` contains a key not of type :class:`str`.
		:raises ValueError:        If parameter ``keyValuePairs`` contains an empty key.
		:raises TypeError:         If parameter ``parent`` isn't of type :class:`RequirementSpecification`.
		:raises ValueError:        If parameter ``identifier`` is ``None``.
		:raises TypeError:         If parameter ``identifier`` isn't of type :class:`str`.
		:raises ValueError:        If parameter ``identifier`` is empty.
		:raises ValueError:        If parameter ``description`` is ``None``.
		:raises TypeError:         If parameter ``description`` isn't of type :class:`str`.
		:raises ValueError:        If parameter ``name`` is ``None``.
		:raises TypeError:         If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError:        If parameter ``name`` is empty.
		:raises RequirementsError: If the specification already contains an element of this class and ID.
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
	firmware, and this one in the software; links of kind :attr:`LinkKind.CounterpartOf` or :attr:`LinkKind.DerivesFrom`
	state it.
	"""

	def IterateRequirements(
		self,
		predicate: Nullable[Callable[[Requirement], bool]] = None
	) -> Generator[Requirement, None, None]:
		"""
		Iterate all or selected requirements of this layer, in the order the specification registered them.

		If parameter ``predicate`` is not None, the given filter function is used to skip requirements in the generator.

		:param predicate: Optional, filter function accepting a requirement and returning a boolean. Default: ``None``.
		:returns:         A generator of the layer's requirements; an empty one, while the layer isn't part of a
		                  specification.
		"""
		if self._root is None:
			return

		if predicate is None:
			for requirement in self._root._requirements.values():
				if requirement._layer is self:
					yield requirement
		else:
			for requirement in self._root._requirements.values():
				if requirement._layer is self and predicate(requirement):
					yield requirement

	def IterateSpecificationItems(
		self,
		predicate: Nullable[Callable[[SpecificationItem], bool]] = None
	) -> Generator[SpecificationItem, None, None]:
		"""
		Iterate all or selected specification items of this layer, in the order the specification registered them.

		If parameter ``predicate`` is not None, the given filter function is used to skip items in the generator.

		:param predicate: Optional, filter function accepting a specification item and returning a boolean. Default:
		                  ``None``.
		:returns:         A generator of the layer's specification items; an empty one, while the layer isn't part of a
		                  specification.
		"""
		if self._root is None:
			return

		if predicate is None:
			for specification in self._root._specificationItems.values():
				if specification._layer is self:
					yield specification
		else:
			for specification in self._root._specificationItems.values():
				if specification._layer is self and predicate(specification):
					yield specification


# A class with a property named like a class - ``Layer`` - can't name that class in the annotation of a field: the class
# body's namespace, where annotations are evaluated, binds the name to the property.
_Layer = Layer


@export
class BaseItem(BaseWithID):
	"""
	Base-class of the items of a specification - requirements and specification items -: a title, a creation time, a
	state, the layer, the persons, personas, labels and documents it refers to, its child items and its links.

	An item refers only to persons, personas, labels, documents and layers of its own specification, so it must be part of
	one to refer to any. A child item has the class of its parent; its ID is unique in the specification, too.
	"""

	_title:        str                  #: The item's title.
	_created:      datetime             #: The time the item was created.
	_state:        ItemState            #: The item's state in its life cycle.
	_layer:        Nullable[_Layer]     #: The layer the item belongs to, or ``None``.
	_authors:      dict[str, Person]    #: The authors of the item, by user ID.
	_owners:       dict[str, Person]    #: The owners of the item, by user ID.
	_personas:     dict[str, Persona]   #: The personas the item is about, by ID.
	_labels:       dict[str, Label]     #: The labels of the item, by ID.
	_attachments:  dict[str, Document]  #: The documents attached to the item, by ID.
	_children:     dict[str, Self]      #: The child items, by ID.
	_links:        list[Link]           #: The links from this item, in the order they were added.
	_inboundLinks: list[Link]           #: The links to this item, in the order they were added.

	def __init__(
		self,
		identifier: str,
		title: str,
		description: str = "",
		created: Nullable[datetime] = None,
		*,
		state: ItemState = ItemState.Draft,
		layer: Nullable[Layer] = None,
		authors: Nullable[Iterable[Person]] = None,
		owners: Nullable[Iterable[Person]] = None,
		personas: Nullable[Iterable[Persona]] = None,
		labels: Nullable[Iterable[Label]] = None,
		attachments: Nullable[Iterable[Document]] = None,
		keyValuePairs: Nullable[Mapping[str, Any]] = None,
		parent: Nullable[BaseItem | RequirementSpecification] = None
	) -> None:
		"""
		Initializes an item with its title, creation time, state, layer, and the persons, personas, labels and documents it
		refers to.

		:param identifier:    The item's ID.
		:param title:         The item's title.
		:param description:   Optional, the item's description. Default: ``""``.
		:param created:       Optional, the time the item was created; without a time zone, it is a local time. Default:
		                      ``None``, the current time.
		:param state:         Optional, the item's state. Default: :attr:`ItemState.Draft`.
		:param layer:         Optional, the layer the item belongs to. Default: ``None``.
		:param authors:       Optional, the authors of the item. Default: ``None``.
		:param owners:        Optional, the owners of the item. Default: ``None``.
		:param personas:      Optional, the personas the item is about. Default: ``None``.
		:param labels:        Optional, the labels of the item. Default: ``None``.
		:param attachments:   Optional, the documents attached to the item. Default: ``None``.
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
		:raises TypeError:    If parameter ``created`` isn't of type :class:`~datetime.datetime`.
		:raises ValueError:   If parameter ``state`` is ``None``.
		:raises TypeError:    If parameter ``state`` isn't of type :class:`ItemState`.
		:raises TypeError:    If parameter ``layer`` isn't of type :class:`Layer`.
		:raises ValueError:   If parameter ``layer`` isn't part of the item's specification.
		:raises TypeError:    If parameter ``authors``, ``owners``, ``personas``, ``labels`` or ``attachments`` isn't
		                      iterable, or is a single element.
		:raises TypeError:    If parameter ``authors`` or ``owners`` contains an element not of type
		                      :class:`~pyEDAA.Reports.Person`.
		:raises TypeError:    If parameter ``personas``, ``labels`` or ``attachments`` contains an element not of type
		                      :class:`Persona`, :class:`Label` or :class:`Document`.
		:raises ValueError:   If parameter ``authors``, ``owners``, ``personas``, ``labels`` or ``attachments`` contains an
		                      element, which isn't part of the item's specification.
		:raises ValueError:   If parameter ``authors``, ``owners``, ``personas``, ``labels`` or ``attachments`` contains an
		                      element twice.
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
			created = datetime.now()
		elif not isinstance(created, datetime):
			ex = TypeError(f"Parameter 'created' is not of type 'datetime'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(created)}'.")
			raise ex

		if state is None:
			raise ValueError(f"Parameter 'state' is None.")
		elif not isinstance(state, ItemState):
			ex = TypeError(f"Parameter 'state' is not of type 'ItemState'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(state)}'.")
			raise ex

		if layer is not None:
			if not isinstance(layer, Layer):
				ex = TypeError(f"Parameter 'layer' is not of type 'Layer'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(layer)}'.")
				raise ex
			elif self._root is None or layer._root is not self._root:
				ex = ValueError(f"Parameter 'layer' isn't part of the item's specification.")
				ex.add_note(f"Got layer '{layer._id}'.")
				raise ex

		self._title =        title
		self._created =      created
		self._state =        state
		self._layer =        layer
		self._authors =      {}
		self._owners =       {}
		self._personas =     {}
		self._labels =       {}
		self._attachments =  {}
		self._children =     {}
		self._links =        []
		self._inboundLinks = []

		for parameterName, references, referenceType, container in (
			("authors",     authors,     Person,   self._authors),
			("owners",      owners,      Person,   self._owners),
			("personas",    personas,    Persona,  self._personas),
			("labels",      labels,      Label,    self._labels),
			("attachments", attachments, Document, self._attachments),
		):
			if references is None:
				continue
			elif not isinstance(references, Iterable):
				ex = TypeError(f"Parameter '{parameterName}' is not iterable.")
				ex.add_note(f"Got type '{getFullyQualifiedName(references)}'.")
				raise ex
			elif isinstance(references, KeyValuePairsMixin):
				ex = TypeError(f"Parameter '{parameterName}' is a single element, not an iterable of elements.")
				ex.add_note(f"Got type '{getFullyQualifiedName(references)}'.")
				raise ex

			for reference in references:
				if not isinstance(reference, referenceType):
					ex = TypeError(f"Parameter '{parameterName}' contains an element not of type '{referenceType.__name__}'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(reference)}'.")
					raise ex

				if referenceType is Person:
					key =        reference._userID
					registered = self._root is not None and self._root._persons.get(key) is reference
				else:
					key =        reference._id
					registered = self._root is not None and reference._root is self._root

				if not registered:
					ex = ValueError(f"Parameter '{parameterName}' contains an element not part of the item's specification.")
					ex.add_note(f"Got {referenceType.__name__.lower()} '{key}'.")
					raise ex
				elif key in container:
					ex = ValueError(f"Parameter '{parameterName}' contains an element twice.")
					ex.add_note(f"Got {referenceType.__name__.lower()} '{key}'.")
					raise ex

				container[key] = reference

	def _AddElement(self, element: Self | Link) -> None:
		"""
		Add a child item or a link, which names this item as its parent.

		A child item is registered with every item below it in the specification. A link is added to its destination's
		inbound links, too.

		:param element:            The child item or link.
		:raises RequirementsError: If the specification already contains an item of an ID of the child or an item below it.
		:raises RequirementsError: If this item isn't part of a specification, and has a child of this ID already.
		:raises RequirementsError: If this item has a link of the same kind to the same destination already.
		"""
		if isinstance(element, Link):
			for link in self._links:
				if link._destination is element._destination and link._kind is element._kind:
					ex = RequirementsError(f"{self.__class__.__name__} '{self._id}' has a '{element._kind}' link already.")
					ex.add_note(f"Got destination '{element._destination._id}'.")
					raise ex

			self._links.append(element)
			element._destination._inboundLinks.append(element)
		else:
			if self._root is not None:
				self._root._AddItems(element)
			elif element._id in self._children:
				raise RequirementsError(f"{self.__class__.__name__} '{self._id}' already has a child '{element._id}'.")

			self._children[element._id] = element

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

		:returns: The time; without a time zone, it is a local time.
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
	def Layer(self) -> Nullable[Layer]:
		"""
		Read-only property to access the layer the item belongs to (:attr:`_layer`).

		:returns: The layer, or ``None``.
		"""
		return self._layer

	@readonly
	def Authors(self) -> dict[str, Person]:
		"""
		Read-only property to access the authors of the item (:attr:`_authors`).

		:returns: The authors, by user ID.
		"""
		return self._authors

	@readonly
	def Owners(self) -> dict[str, Person]:
		"""
		Read-only property to access the owners of the item (:attr:`_owners`).

		:returns: The owners, by user ID.
		"""
		return self._owners

	@readonly
	def Personas(self) -> dict[str, Persona]:
		"""
		Read-only property to access the personas the item is about (:attr:`_personas`).

		E.g. the role of a user story: "As a reviewer, I want ...".

		:returns: The personas, by ID.
		"""
		return self._personas

	@readonly
	def Labels(self) -> dict[str, Label]:
		"""
		Read-only property to access the labels of the item (:attr:`_labels`).

		:returns: The labels, by ID.
		"""
		return self._labels

	@readonly
	def Attachments(self) -> dict[str, Document]:
		"""
		Read-only property to access the documents attached to the item (:attr:`_attachments`).

		:returns: The documents, by ID.
		"""
		return self._attachments

	@readonly
	def Children(self) -> dict[str, Self]:
		"""
		Read-only property to access the child items (:attr:`_children`).

		:returns: The child items, by ID.
		"""
		return self._children

	@readonly
	def Links(self) -> list[Link]:
		"""
		Read-only property to access the links from this item (:attr:`_links`).

		:returns: The links, in the order they were added.
		"""
		return self._links

	@readonly
	def InboundLinks(self) -> list[Link]:
		"""
		Read-only property to access the links to this item (:attr:`_inboundLinks`).

		:returns: The links, in the order they were added.
		"""
		return self._inboundLinks

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
		if predicate is None:
			for child in self._children.values():
				yield child
				yield from child.IterateDescendants()
		else:
			for child in self._children.values():
				if predicate(child):
					yield child

				yield from child.IterateDescendants(predicate)

	def IterateLinks(self, predicate: Nullable[Callable[[Link], bool]] = None) -> Generator[Link, None, None]:
		"""
		Iterate all or selected links from this item.

		If parameter ``predicate`` is not None, the given filter function is used to skip links in the generator.

		:param predicate: Optional, filter function accepting a link and returning a boolean. Default: ``None``.
		:returns:         A generator of the links from this item.
		"""
		if predicate is None:
			yield from self._links
		else:
			for link in self._links:
				if predicate(link):
					yield link

	def IterateInboundLinks(self, predicate: Nullable[Callable[[Link], bool]] = None) -> Generator[Link, None, None]:
		"""
		Iterate all or selected links to this item.

		If parameter ``predicate`` is not None, the given filter function is used to skip links in the generator.

		:param predicate: Optional, filter function accepting a link and returning a boolean. Default: ``None``.
		:returns:         A generator of the links to this item.
		"""
		if predicate is None:
			yield from self._inboundLinks
		else:
			for link in self._inboundLinks:
				if predicate(link):
					yield link


@export
class Requirement(BaseItem):
	"""
	A requirement: a condition or capability the system must, should or may meet, its kind and its obligation.

	Its parent is the :class:`RequirementSpecification` for a top-level requirement, or the :class:`Requirement` it
	refines - a child requirement. The specification registers either by its ID.
	"""

	_PARENT_TYPE:        ClassVar[tuple[type, ...]]    #: In a requirement or the specification; assigned below.

	_kind:               RequirementKind               #: What the requirement constrains.
	_obligation:         _Obligation                   #: Whether the requirement must, should or may be met.
	_specificationItems: dict[str, SpecificationItem]  #: The specification items specifying this requirement, by ID.

	def __init__(
		self,
		identifier: str,
		title: str,
		kind: RequirementKind,
		description: str = "",
		created: Nullable[datetime] = None,
		*,
		obligation: Obligation = Obligation.Mandatory,
		state: ItemState = ItemState.Draft,
		layer: Nullable[Layer] = None,
		authors: Nullable[Iterable[Person]] = None,
		owners: Nullable[Iterable[Person]] = None,
		personas: Nullable[Iterable[Persona]] = None,
		labels: Nullable[Iterable[Label]] = None,
		attachments: Nullable[Iterable[Document]] = None,
		keyValuePairs: Nullable[Mapping[str, Any]] = None,
		parent: Nullable[Requirement | RequirementSpecification] = None
	) -> None:
		"""
		Initializes a requirement, adds it to its parent, and registers it in its specification.

		:param identifier:         The requirement's ID.
		:param title:              The requirement's title.
		:param kind:               What the requirement constrains.
		:param description:        Optional, the requirement's description. Default: ``""``.
		:param created:            Optional, the time the requirement was created; without a time zone, it is a local time.
		                           Default: ``None``, the current time.
		:param obligation:         Optional, whether the requirement must, should or may be met. Default:
		                           :attr:`Obligation.Mandatory`.
		:param state:              Optional, the requirement's state. Default: :attr:`ItemState.Draft`.
		:param layer:              Optional, the layer the requirement belongs to. Default: ``None``.
		:param authors:            Optional, the authors of the requirement. Default: ``None``.
		:param owners:             Optional, the owners of the requirement. Default: ``None``.
		:param personas:           Optional, the personas the requirement is about. Default: ``None``.
		:param labels:             Optional, the labels of the requirement. Default: ``None``.
		:param attachments:        Optional, the documents attached to the requirement. Default: ``None``.
		:param keyValuePairs:      Optional, the key-value pairs. Default: ``None``.
		:param parent:             Optional, the requirement this one refines, or the specification. Default: ``None``.
		:raises TypeError:         If parameter ``keyValuePairs`` isn't a mapping.
		:raises TypeError:         If parameter ``keyValuePairs`` contains a key not of type :class:`str`.
		:raises ValueError:        If parameter ``keyValuePairs`` contains an empty key.
		:raises TypeError:         If parameter ``parent`` isn't of type :class:`Requirement` or
		                           :class:`RequirementSpecification`.
		:raises ValueError:        If parameter ``identifier`` is ``None``.
		:raises TypeError:         If parameter ``identifier`` isn't of type :class:`str`.
		:raises ValueError:        If parameter ``identifier`` is empty.
		:raises ValueError:        If parameter ``description`` is ``None``.
		:raises TypeError:         If parameter ``description`` isn't of type :class:`str`.
		:raises ValueError:        If parameter ``title`` is ``None``.
		:raises TypeError:         If parameter ``title`` isn't of type :class:`str`.
		:raises ValueError:        If parameter ``title`` is empty.
		:raises TypeError:         If parameter ``created`` isn't of type :class:`~datetime.datetime`.
		:raises ValueError:        If parameter ``state`` is ``None``.
		:raises TypeError:         If parameter ``state`` isn't of type :class:`ItemState`.
		:raises TypeError:         If parameter ``layer`` isn't of type :class:`Layer`.
		:raises ValueError:        If parameter ``layer`` isn't part of the requirement's specification.
		:raises TypeError:         If parameter ``authors``, ``owners``, ``personas``, ``labels`` or ``attachments`` isn't
		                           iterable, or is a single element.
		:raises TypeError:         If parameter ``authors`` or ``owners`` contains an element not of type
		                           :class:`~pyEDAA.Reports.Person`.
		:raises TypeError:         If parameter ``personas``, ``labels`` or ``attachments`` contains an element not of type
		                           :class:`Persona`, :class:`Label` or :class:`Document`.
		:raises ValueError:        If parameter ``authors``, ``owners``, ``personas``, ``labels`` or ``attachments``
		                           contains an element, which isn't part of the requirement's specification.
		:raises ValueError:        If parameter ``authors``, ``owners``, ``personas``, ``labels`` or ``attachments``
		                           contains an element twice.
		:raises ValueError:        If parameter ``kind`` is ``None``.
		:raises TypeError:         If parameter ``kind`` isn't of type :class:`RequirementKind`.
		:raises ValueError:        If parameter ``obligation`` is ``None``.
		:raises TypeError:         If parameter ``obligation`` isn't of type :class:`Obligation`.
		:raises RequirementsError: If the specification already contains a requirement of this ID.
		"""
		super().__init__(
			identifier,
			title,
			description,
			created,
			state=state,
			layer=layer,
			authors=authors,
			owners=owners,
			personas=personas,
			labels=labels,
			attachments=attachments,
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

		self._kind =               kind
		self._obligation =         obligation
		self._specificationItems = {}

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

	@readonly
	def SpecificationItems(self) -> dict[str, SpecificationItem]:
		"""
		Read-only property to access the specification items specifying this requirement (:attr:`_specificationItems`).

		The relation is maintained by :meth:`SpecificationItem.AddRequirement`.

		:returns: The specification items, by ID.
		"""
		return self._specificationItems


Requirement._PARENT_TYPE = (Requirement, RequirementSpecification)


@export
class SpecificationItem(BaseItem):
	"""
	A specification item: how the system meets requirements.

	E.g. a design decision, an architecture or an interface description. It mirrors a requirement - with an ID, a title, a
	state, a layer, persons, personas, labels, documents, child items and links -, and specifies any number of
	requirements; a requirement is specified by any number of specification items.

	Its parent is the :class:`RequirementSpecification` for a top-level item, or the :class:`SpecificationItem` it
	details. The specification registers either by its ID.
	"""

	_PARENT_TYPE:  ClassVar[tuple[type, ...]]  #: An item is in an item or the specification; assigned below the class.

	_requirements: dict[str, Requirement]      #: The requirements this item specifies, by ID.

	def __init__(
		self,
		identifier: str,
		title: str,
		description: str = "",
		created: Nullable[datetime] = None,
		*,
		requirements: Nullable[Iterable[Requirement]] = None,
		state: ItemState = ItemState.Draft,
		layer: Nullable[Layer] = None,
		authors: Nullable[Iterable[Person]] = None,
		owners: Nullable[Iterable[Person]] = None,
		personas: Nullable[Iterable[Persona]] = None,
		labels: Nullable[Iterable[Label]] = None,
		attachments: Nullable[Iterable[Document]] = None,
		keyValuePairs: Nullable[Mapping[str, Any]] = None,
		parent: Nullable[SpecificationItem | RequirementSpecification] = None
	) -> None:
		"""
		Initializes a specification item, adds it to its parent, registers it in its specification, and relates it to the
		requirements it specifies.

		:param identifier:         The item's ID.
		:param title:              The item's title.
		:param description:        Optional, the item's description. Default: ``""``.
		:param created:            Optional, the time the item was created; without a time zone, it is a local time.
		                           Default: ``None``, the current time.
		:param requirements:       Optional, the requirements the item specifies. Default: ``None``.
		:param state:              Optional, the item's state. Default: :attr:`ItemState.Draft`.
		:param layer:              Optional, the layer the item belongs to. Default: ``None``.
		:param authors:            Optional, the authors of the item. Default: ``None``.
		:param owners:             Optional, the owners of the item. Default: ``None``.
		:param personas:           Optional, the personas the item is about. Default: ``None``.
		:param labels:             Optional, the labels of the item. Default: ``None``.
		:param attachments:        Optional, the documents attached to the item. Default: ``None``.
		:param keyValuePairs:      Optional, the key-value pairs. Default: ``None``.
		:param parent:             Optional, the specification item this one details, or the specification. Default:
		                           ``None``.
		:raises TypeError:         If parameter ``keyValuePairs`` isn't a mapping.
		:raises TypeError:         If parameter ``keyValuePairs`` contains a key not of type :class:`str`.
		:raises ValueError:        If parameter ``keyValuePairs`` contains an empty key.
		:raises TypeError:         If parameter ``parent`` isn't of type :class:`SpecificationItem` or
		                           :class:`RequirementSpecification`.
		:raises ValueError:        If parameter ``identifier`` is ``None``.
		:raises TypeError:         If parameter ``identifier`` isn't of type :class:`str`.
		:raises ValueError:        If parameter ``identifier`` is empty.
		:raises ValueError:        If parameter ``description`` is ``None``.
		:raises TypeError:         If parameter ``description`` isn't of type :class:`str`.
		:raises ValueError:        If parameter ``title`` is ``None``.
		:raises TypeError:         If parameter ``title`` isn't of type :class:`str`.
		:raises ValueError:        If parameter ``title`` is empty.
		:raises TypeError:         If parameter ``created`` isn't of type :class:`~datetime.datetime`.
		:raises ValueError:        If parameter ``state`` is ``None``.
		:raises TypeError:         If parameter ``state`` isn't of type :class:`ItemState`.
		:raises TypeError:         If parameter ``layer`` isn't of type :class:`Layer`.
		:raises ValueError:        If parameter ``layer`` isn't part of the item's specification.
		:raises TypeError:         If parameter ``authors``, ``owners``, ``personas``, ``labels`` or ``attachments`` isn't
		                           iterable, or is a single element.
		:raises TypeError:         If parameter ``authors`` or ``owners`` contains an element not of type
		                           :class:`~pyEDAA.Reports.Person`.
		:raises TypeError:         If parameter ``personas``, ``labels`` or ``attachments`` contains an element not of type
		                           :class:`Persona`, :class:`Label` or :class:`Document`.
		:raises ValueError:        If parameter ``authors``, ``owners``, ``personas``, ``labels`` or ``attachments``
		                           contains an element, which isn't part of the item's specification.
		:raises ValueError:        If parameter ``authors``, ``owners``, ``personas``, ``labels`` or ``attachments``
		                           contains an element twice.
		:raises TypeError:         If parameter ``requirements`` isn't iterable, or is a single element.
		:raises TypeError:         If parameter ``requirements`` contains an element not of type :class:`Requirement`.
		:raises ValueError:        If parameter ``requirements`` contains a requirement, which isn't part of the item's
		                           specification.
		:raises ValueError:        If parameter ``requirements`` contains a requirement twice.
		:raises RequirementsError: If the specification already contains a specification item of this ID.
		"""
		super().__init__(
			identifier,
			title,
			description,
			created,
			state=state,
			layer=layer,
			authors=authors,
			owners=owners,
			personas=personas,
			labels=labels,
			attachments=attachments,
			keyValuePairs=keyValuePairs,
			parent=parent
		)

		self._requirements = {}

		if requirements is not None:
			if not isinstance(requirements, Iterable):
				ex = TypeError(f"Parameter 'requirements' is not iterable.")
				ex.add_note(f"Got type '{getFullyQualifiedName(requirements)}'.")
				raise ex
			elif isinstance(requirements, KeyValuePairsMixin):
				ex = TypeError(f"Parameter 'requirements' is a single element, not an iterable of elements.")
				ex.add_note(f"Got type '{getFullyQualifiedName(requirements)}'.")
				raise ex

			for requirement in requirements:
				if not isinstance(requirement, Requirement):
					ex = TypeError(f"Parameter 'requirements' contains an element not of type 'Requirement'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(requirement)}'.")
					raise ex
				elif self._root is None or requirement._root is not self._root:
					ex = ValueError(f"Parameter 'requirements' contains a requirement not part of the item's specification.")
					ex.add_note(f"Got requirement '{requirement._id}'.")
					raise ex
				elif requirement._id in self._requirements:
					ex = ValueError(f"Parameter 'requirements' contains a requirement twice.")
					ex.add_note(f"Got requirement '{requirement._id}'.")
					raise ex

				self._requirements[requirement._id] = requirement

		if parent is not None:
			parent._AddElement(self)

		for requirement in self._requirements.values():
			requirement._specificationItems[identifier] = self

	@readonly
	def Requirements(self) -> dict[str, Requirement]:
		"""
		Read-only property to access the requirements this item specifies (:attr:`_requirements`).

		:returns: The requirements, by ID.
		"""
		return self._requirements

	def AddRequirement(self, requirement: Requirement) -> None:
		"""
		Relate this item to a requirement it specifies: the item lists the requirement, and the requirement lists the item.

		:param requirement:        The requirement.
		:raises ValueError:        If parameter ``requirement`` is ``None``.
		:raises TypeError:         If parameter ``requirement`` isn't of type :class:`Requirement`.
		:raises ValueError:        If parameter ``requirement`` isn't part of the item's specification.
		:raises RequirementsError: If the item specifies the requirement already.
		"""
		if requirement is None:
			raise ValueError(f"Parameter 'requirement' is None.")
		elif not isinstance(requirement, Requirement):
			ex = TypeError(f"Parameter 'requirement' is not of type 'Requirement'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(requirement)}'.")
			raise ex
		elif self._root is None or requirement._root is not self._root:
			ex = ValueError(f"Parameter 'requirement' isn't part of the item's specification.")
			ex.add_note(f"Got requirement '{requirement._id}'.")
			raise ex
		elif requirement._id in self._requirements:
			raise RequirementsError(f"Specification item '{self._id}' specifies requirement '{requirement._id}' already.")

		self._requirements[requirement._id] =       requirement
		requirement._specificationItems[self._id] = self


SpecificationItem._PARENT_TYPE = (SpecificationItem, RequirementSpecification)


@export
class LinkKind(StringEnum):
	"""
	The relationship a link states: the source item *<kind>* the destination item.

	A link connects items of the same or of different layers, e.g. an FPGA firmware requirement derived from an electrical
	one. Which specification item specifies which requirement, isn't a link, but the relation of
	:attr:`SpecificationItem.Requirements` and :attr:`Requirement.SpecificationItems`.
	"""

	Refines =       "refines"         #: The source states the destination in more detail, outside the item hierarchy.
	DerivesFrom =   "derives-from"    #: The source is derived from the destination, e.g. from a higher layer.
	CounterpartOf = "counterpart-of"  #: The source is the destination's counterpart in another layer.
	DependsOn =     "depends-on"      #: The source can only be met, if the destination is met.
	ConflictsWith = "conflicts-with"  #: The source and the destination can't both be met.
	Duplicates =    "duplicates"      #: The source states the same as the destination.
	Replaces =      "replaces"        #: The source replaces the destination, which is obsolete.
	RelatesTo =     "relates-to"      #: Any other relationship.


@export
class Link(Base):
	"""
	A link from an item - its source - to another item of the same specification - its destination -, and the
	relationship it states.

	Its parent is its source: the source lists it in :attr:`~BaseItem.Links`, the destination in
	:attr:`~BaseItem.InboundLinks`.
	"""

	_PARENT_TYPE: ClassVar[tuple[type, ...]] = (BaseItem, )  #: A link is in its source item.

	_destination: BaseItem                                   #: The item the link points to.
	_kind:        LinkKind                                   #: The relationship the link states.

	def __init__(
		self,
		destination: BaseItem,
		kind: LinkKind,
		*,
		keyValuePairs: Nullable[Mapping[str, Any]] = None,
		parent: BaseItem
	) -> None:
		"""
		Initializes a link, and adds it to its source and its destination.

		:param destination:        The item the link points to.
		:param kind:               The relationship the link states.
		:param keyValuePairs:      Optional, the key-value pairs. Default: ``None``.
		:param parent:             The item the link starts at: its source.
		:raises TypeError:         If parameter ``keyValuePairs`` isn't a mapping.
		:raises TypeError:         If parameter ``keyValuePairs`` contains a key not of type :class:`str`.
		:raises ValueError:        If parameter ``keyValuePairs`` contains an empty key.
		:raises ValueError:        If parameter ``parent`` is ``None``.
		:raises TypeError:         If parameter ``parent`` isn't of type :class:`BaseItem`.
		:raises ValueError:        If parameter ``destination`` is ``None``.
		:raises TypeError:         If parameter ``destination`` isn't of type :class:`BaseItem`.
		:raises ValueError:        If parameter ``destination`` is the link's source.
		:raises ValueError:        If parameter ``destination`` isn't part of the source's specification.
		:raises ValueError:        If parameter ``kind`` is ``None``.
		:raises TypeError:         If parameter ``kind`` isn't of type :class:`LinkKind`.
		:raises RequirementsError: If the source has a link of this kind to this destination already.
		"""
		super().__init__(keyValuePairs=keyValuePairs, parent=parent)

		if parent is None:
			raise ValueError(f"Parameter 'parent' is None.")

		if destination is None:
			raise ValueError(f"Parameter 'destination' is None.")
		elif not isinstance(destination, BaseItem):
			ex = TypeError(f"Parameter 'destination' is not of type 'BaseItem'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(destination)}'.")
			raise ex
		elif destination is parent:
			ex = ValueError(f"Parameter 'destination' is the link's source.")
			ex.add_note(f"Got item '{destination._id}'.")
			raise ex
		elif self._root is None or destination._root is not self._root:
			ex = ValueError(f"Parameter 'destination' isn't part of the source's specification.")
			ex.add_note(f"Got item '{destination._id}'.")
			raise ex

		if kind is None:
			raise ValueError(f"Parameter 'kind' is None.")
		elif not isinstance(kind, LinkKind):
			ex = TypeError(f"Parameter 'kind' is not of type 'LinkKind'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(kind)}'.")
			raise ex

		self._destination = destination
		self._kind =        kind

		parent._AddElement(self)

	@readonly
	def Source(self) -> BaseItem:
		"""
		Read-only property to access the item the link starts at: its parent (:attr:`_parent`).

		:returns: The source item.
		"""
		return self._parent

	@readonly
	def Destination(self) -> BaseItem:
		"""
		Read-only property to access the item the link points to (:attr:`_destination`).

		:returns: The destination item.
		"""
		return self._destination

	@readonly
	def Kind(self) -> LinkKind:
		"""
		Read-only property to access the relationship the link states (:attr:`_kind`).

		:returns: The link's kind.
		"""
		return self._kind
