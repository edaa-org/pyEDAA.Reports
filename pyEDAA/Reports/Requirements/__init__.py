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

A :class:`RequirementSpecification` is the root: it registers the personas (:class:`Persona`), labels (:class:`Label`),
documents (:class:`Document`) and layers (:class:`Layer`) of a system's requirements by their IDs, and the persons
(:class:`~pyEDAA.Reports.Person`) by their user IDs.
"""
from __future__            import annotations

from typing                import Any, ClassVar, Generator, Mapping, Optional as Nullable

from pyTooling.Common      import getFullyQualifiedName
from pyTooling.Decorators  import export, readonly
from pyTooling.MetaClasses import ExtendedType, abstractmethod
from pyTooling.Versioning  import SemanticVersion

from pyEDAA.Reports        import KeyValuePairsMixin, Person


@export
class Base(KeyValuePairsMixin, metaclass=ExtendedType, slots=True):
	"""
	Base-class of every element of the requirements model: key-value pairs, a reference to the element containing it, and
	a reference to the specification it is part of.
	"""

	_PARENT_TYPE: ClassVar[tuple[type, ...]]  #: The types a parent may have; assigned by each class having a parent.

	_parent: Nullable[Base]                      #: The element containing this one, or ``None``.
	_root:   Nullable[RequirementSpecification]  #: The specification, or ``None`` while the element isn't part of one.

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
	The root of the requirements model: the personas, labels, documents and layers of a system's requirements.

	It registers each of them by its ID, and is its own specification.

	Persons have no parent: the specification registers the persons its items refer to by their user IDs, and a person may
	be registered in several specifications.
	"""

	_name:      Nullable[str]        #: The specification's name, or ``None``.
	_version:   SemanticVersion      #: The version of the specification.
	_persons:   dict[str, Person]    #: The persons, by user ID.
	_personas:  dict[str, Persona]   #: The personas, by ID.
	_labels:    dict[str, Label]     #: The labels, by ID.
	_documents: dict[str, Document]  #: The documents, by ID.
	_layers:    dict[str, Layer]     #: The layers, by ID.

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

		self._root =      self
		self._name =      name
		self._version =   version
		self._persons =   {}
		self._personas =  {}
		self._labels =    {}
		self._documents = {}
		self._layers =    {}

	@Base.Parent.setter
	def Parent(self, parent: None) -> None:
		ex = TypeError(f"A '{getFullyQualifiedName(self)}' has no parent.")
		ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
		raise ex

	def _AddElement(self, element: BaseWithID) -> None:
		"""
		Register a persona, label, document or layer, which names the specification as its parent.

		:param element:     The element.
		:raises ValueError: If the specification already contains an element of the same class and ID.
		"""
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

	def IterateElements(self) -> Generator[Base, None, None]:
		"""
		Iterate the personas, labels, documents and layers.

		:returns: A generator of every element below the specification.
		"""
		yield from (*self._personas.values(), *self._labels.values(), *self._documents.values(), *self._layers.values())

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


@export
class BaseWithName(BaseWithID):
	"""
	Base-class of the elements a specification registers for its requirements to refer to: an ID, a name and a
	description.

	Its parent is the :class:`RequirementSpecification`.
	"""

	_PARENT_TYPE: ClassVar[tuple[type, ...]] = (RequirementSpecification, )  #: The element is in a specification.

	_name: str  #: The element's name.

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
