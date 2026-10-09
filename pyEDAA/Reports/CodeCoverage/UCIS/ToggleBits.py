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
The bits of the toggle coverage of the UCIS XML interchange format: a signal's ``<toggleBit>`` elements and their
transitions.
"""
from __future__                                 import annotations

from typing                                     import TYPE_CHECKING, Iterable, Optional as Nullable, Self

from lxml.etree                                 import _Element
from pyTooling.Common                           import getFullyQualifiedName
from pyTooling.Decorators                       import export, readonly
from pyTooling.MetaClasses                      import ExtendedType

from pyEDAA.Reports.CodeCoverage.UCIS.Bins      import Bin
from pyEDAA.Reports.CodeCoverage.UCIS.Elements  import Base, ObjectAttributesMixin, UserAttribute

if TYPE_CHECKING:
	from pyEDAA.Reports.CodeCoverage.UCIS.Toggles import ToggleObject


# A class with a property named like a class - ``Bin`` - can't name that class in the annotation of a field: the class
# body's namespace, where annotations are evaluated, binds the name to the property.
_Bin = Bin


@export
class ToggleBit(Base, ObjectAttributesMixin):
	"""
	A ``<toggleBit>`` of a toggle object: a bit of the signal, its indices and its transitions.
	"""

	_parent:  Nullable[ToggleObject]  #: The toggle object the bit belongs to.
	_name:    str                     #: Name of the bit, e.g. ``ff1[2]``.
	_key:     str                     #: UCIS key of the bit.
	_indices: list[int]               #: The indices of the bit, one per dimension.
	_toggles: list[Toggle]            #: The transitions of the bit.

	def __init__(
		self,
		name: str,
		key: str,
		indices: Nullable[Iterable[int]] = None,
		alias: Nullable[str] = None,
		excluded: bool = False,
		excludedReason: Nullable[str] = None,
		weight: int = 1,
		userAttributes: Nullable[Iterable[UserAttribute]] = None,
		*,
		parent: Nullable[ToggleObject] = None
	) -> None:
		"""
		Initialize the toggle bit, and append it to the bits of its toggle object.

		Its transitions are added by creating them with this bit as their parent.

		:param name:           Name of the bit, e.g. ``ff1[2]``.
		:param key:            UCIS key of the bit.
		:param indices:        Optional, the indices of the bit, one per dimension. Default: ``None``.
		:param alias:          Optional, an alias of the bit's name. Default: ``None``.
		:param excluded:       Optional, whether the bit is excluded from the coverage. Default: ``False``.
		:param excludedReason: Optional, why the bit is excluded. Default: ``None``.
		:param weight:         Optional, weight of the bit in computing the coverage. Default: ``1``.
		:param userAttributes: Optional, the user-defined attributes. Default: ``None``.
		:param parent:         Optional, the toggle object the bit belongs to. Default: ``None``.
		:raises TypeError:     If parameter ``userAttributes`` isn't iterable.
		:raises TypeError:     If parameter ``userAttributes`` contains an element not of type
		                       :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Elements.UserAttribute`.
		:raises TypeError:     If parameter ``alias`` isn't of type :class:`str`.
		:raises ValueError:    If parameter ``excluded`` is ``None``.
		:raises TypeError:     If parameter ``excluded`` isn't of type :class:`bool`.
		:raises TypeError:     If parameter ``excludedReason`` isn't of type :class:`str`.
		:raises ValueError:    If parameter ``weight`` is ``None``.
		:raises TypeError:     If parameter ``weight`` isn't of type :class:`int`.
		:raises ValueError:    If parameter ``weight`` is negative.
		:raises ValueError:    If parameter ``name`` or ``key`` is ``None``.
		:raises TypeError:     If parameter ``name`` or ``key`` isn't of type :class:`str`.
		:raises TypeError:     If parameter ``parent`` isn't of type
		                       :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Toggles.ToggleObject`.
		:raises TypeError:     If parameter ``indices`` isn't iterable.
		:raises TypeError:     If parameter ``indices`` contains an element not of type :class:`int`.
		:raises ValueError:    If parameter ``indices`` contains a negative index.
		"""
		from pyEDAA.Reports.CodeCoverage.UCIS.Toggles import ToggleObject

		super().__init__(userAttributes)
		ObjectAttributesMixin.__init__(self, alias, excluded, excludedReason, weight)

		for parameterName, value in (
			("name", name),
			("key",  key)
		):
			if value is None:
				raise ValueError(f"Parameter '{parameterName}' is None.")
			elif not isinstance(value, str):
				ex = TypeError(f"Parameter '{parameterName}' is not of type 'str'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
				raise ex

		if parent is not None and not isinstance(parent, ToggleObject):
			ex = TypeError(f"Parameter 'parent' is not of type 'ToggleObject'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =  parent
		self._name =    name
		self._key =     key
		self._indices = []
		self._toggles = []

		if indices is not None:
			if not isinstance(indices, Iterable):
				ex = TypeError(f"Parameter 'indices' is not iterable.")
				ex.add_note(f"Got type '{getFullyQualifiedName(indices)}'.")
				raise ex

			for index in indices:
				if not isinstance(index, int) or isinstance(index, bool):
					ex = TypeError(f"Parameter 'indices' contains an element not of type 'int'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(index)}'.")
					raise ex
				elif index < 0:
					ex = ValueError(f"Parameter 'indices' contains a negative index.")
					ex.add_note(f"Got value '{index}'.")
					raise ex

				self._indices.append(index)

		if parent is not None:
			parent._bits.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[ToggleObject] = None) -> Self:
		"""
		Parse a toggle bit and its transitions from its ``<toggleBit>`` element.

		:param element:            The ``<toggleBit>`` element.
		:param parent:             Optional, the toggle object the bit belongs to. Default: ``None``.
		:returns:                  The toggle bit.
		:raises CodeCoverageError: If a user-defined attribute's value isn't of the type the attribute states.
		"""
		toggleBit = cls(
			element.attrib["name"],
			element.attrib["key"],
			[int(indexElement.text) for indexElement in element.iterfind("{*}index")],
			element.attrib.get("alias"),
			cls._ParseBoolean(element.attrib.get("excluded", "false")),
			element.attrib.get("excludedReason"),
			int(element.attrib.get("weight", "1")),
			cls._ParseUserAttributes(element),
			parent=parent
		)

		for toggleElement in element.iterfind("{*}toggle"):
			Toggle.Parse(toggleElement, parent=toggleBit)

		return toggleBit

	@readonly
	def Parent(self) -> Nullable[ToggleObject]:
		"""
		Read-only property to access the toggle object the bit belongs to (:attr:`_parent`).

		:returns: The toggle object; ``None``, if the bit belongs to none.
		"""
		return self._parent

	@readonly
	def Name(self) -> str:
		"""
		Read-only property to access the name of the bit (:attr:`_name`).

		:returns: The name, e.g. ``ff1[2]``.
		"""
		return self._name

	@readonly
	def Key(self) -> str:
		"""
		Read-only property to access the UCIS key of the bit (:attr:`_key`).

		:returns: The key, as stated.
		"""
		return self._key

	@readonly
	def Indices(self) -> list[int]:
		"""
		Read-only property to access the indices of the bit (:attr:`_indices`).

		:returns: The indices, one per dimension; empty, if the report states none.
		"""
		return self._indices

	@readonly
	def Toggles(self) -> list[Toggle]:
		"""
		Read-only property to access the transitions of the bit (:attr:`_toggles`).

		:returns: The transitions, in the order the report lists them.
		"""
		return self._toggles


@export
class Toggle(metaclass=ExtendedType, slots=True):
	"""
	A ``<toggle>`` of a toggle bit: a transition from one value to another, and its bin - how often it happened.
	"""

	_parent: Nullable[ToggleBit]  #: The toggle bit the transition belongs to.
	_from:   str                  #: The value before the transition, e.g. ``0``.
	_to:     str                  #: The value after the transition, e.g. ``1``.
	_bin:    _Bin                 #: How often the transition happened.

	def __init__(self, fromValue: str, toValue: str, coverBin: Bin, *, parent: Nullable[ToggleBit] = None) -> None:
		"""
		Initialize the transition, become its bin's parent, and append it to the transitions of its toggle bit.

		:param fromValue:   The value before the transition, e.g. ``0``.
		:param toValue:     The value after the transition, e.g. ``1``.
		:param coverBin:    How often the transition happened.
		:param parent:      Optional, the toggle bit the transition belongs to. Default: ``None``.
		:raises ValueError: If parameter ``fromValue`` or ``toValue`` is ``None``.
		:raises TypeError:  If parameter ``fromValue`` or ``toValue`` isn't of type :class:`str`.
		:raises ValueError: If parameter ``coverBin`` is ``None``.
		:raises TypeError:  If parameter ``coverBin`` isn't of type :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Bins.Bin`.
		:raises TypeError:  If parameter ``parent`` isn't of type :class:`ToggleBit`.
		"""
		for parameterName, value in (
			("fromValue", fromValue),
			("toValue",   toValue)
		):
			if value is None:
				raise ValueError(f"Parameter '{parameterName}' is None.")
			elif not isinstance(value, str):
				ex = TypeError(f"Parameter '{parameterName}' is not of type 'str'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
				raise ex

		if coverBin is None:
			raise ValueError(f"Parameter 'coverBin' is None.")
		elif not isinstance(coverBin, Bin):
			ex = TypeError(f"Parameter 'coverBin' is not of type 'Bin'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(coverBin)}'.")
			raise ex

		if parent is not None and not isinstance(parent, ToggleBit):
			ex = TypeError(f"Parameter 'parent' is not of type 'ToggleBit'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =     parent
		self._from =       fromValue
		self._to =         toValue
		self._bin =        coverBin
		coverBin._parent = self

		if parent is not None:
			parent._toggles.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[ToggleBit] = None) -> Self:
		"""
		Parse a transition and its bin from its ``<toggle>`` element.

		:param element:            The ``<toggle>`` element.
		:param parent:             Optional, the toggle bit the transition belongs to. Default: ``None``.
		:returns:                  The transition.
		:raises CodeCoverageError: If a user-defined attribute's value isn't of the type the attribute states.
		"""
		return cls(element.attrib["from"], element.attrib["to"], Bin.Parse(element.find("{*}bin")), parent=parent)

	@readonly
	def Parent(self) -> Nullable[ToggleBit]:
		"""
		Read-only property to access the toggle bit the transition belongs to (:attr:`_parent`).

		:returns: The toggle bit; ``None``, if the transition belongs to none.
		"""
		return self._parent

	@readonly
	def From(self) -> str:
		"""
		Read-only property to access the value before the transition (:attr:`_from`).

		:returns: The value, as stated, e.g. ``0``.
		"""
		return self._from

	@readonly
	def To(self) -> str:
		"""
		Read-only property to access the value after the transition (:attr:`_to`).

		:returns: The value, as stated, e.g. ``1``.
		"""
		return self._to

	@readonly
	def Bin(self) -> Bin:
		"""
		Read-only property to access the transition's bin (:attr:`_bin`).

		:returns: The bin, stating how often the transition happened.
		"""
		return self._bin
