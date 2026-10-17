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
The elements of the UCIS XML interchange format, which the coverage kinds share: the user-defined attributes, the
attributes of an object, the source statement identifiers, and the base-class of an instance's coverage of a kind.
"""
from __future__                                   import annotations

from typing                                       import TYPE_CHECKING, Iterable, Optional as Nullable, Self

from lxml.etree                                   import _Element
from pyTooling.Common                             import getFullyQualifiedName, StringEnum
from pyTooling.Decorators                         import export, readonly
from pyTooling.MetaClasses                        import ExtendedType, abstractclass

from pyEDAA.Reports.CodeCoverage                  import CodeCoverageError

if TYPE_CHECKING:
	from pyEDAA.Reports.CodeCoverage.UCIS.Instances import InstanceCoverage


@export
class UserAttributeType(StringEnum):
	"""
	Type of a user-defined attribute's value, as a ``<userAttr>``'s ``type`` states.
	"""

	Integer =   "int"     #: A 32-bit integer.
	Integer64 = "int64"   #: A 64-bit integer.
	Float =     "float"   #: A single precision floating point number.
	Double =    "double"  #: A double precision floating point number.
	String =    "str"     #: A string.
	Bits =      "bits"    #: A bit string, e.g. ``01101100``, its length stated by ``len``.


@export
class UserAttribute(metaclass=ExtendedType, slots=True):
	"""
	A ``<userAttr>`` of an element: a key, the type of its value, the value and - for a bit string - its length.

	It is a value, as a path is: it names no parent.
	"""

	_key:    str                           #: Key of the attribute.
	_type:   UserAttributeType             #: Type of the attribute's value.
	_value:  Nullable[int | float | str]   #: The value, of the type :attr:`_type` names.
	_length: Nullable[int]                 #: Length of a bit string.

	def __init__(
		self,
		key: str,
		attributeType: UserAttributeType,
		value: Nullable[int | float | str] = None,
		length: Nullable[int] = None
	) -> None:
		"""
		Initialize the user-defined attribute.

		:param key:           Key of the attribute, e.g. ``optimization_level``.
		:param attributeType: Type of the attribute's value.
		:param value:         Optional, the value: :class:`int` for ``int`` and ``int64``, :class:`float` for ``float`` and
		                      ``double``, :class:`str` for ``str`` and ``bits``; ``None``, if the report states none.
		                      Default: ``None``.
		:param length:        Optional, length of a bit string. Default: ``None``.
		:raises ValueError:   If parameter ``key`` is ``None``.
		:raises TypeError:    If parameter ``key`` isn't of type :class:`str`.
		:raises ValueError:   If parameter ``attributeType`` is ``None``.
		:raises TypeError:    If parameter ``attributeType`` isn't of type :class:`UserAttributeType`.
		:raises TypeError:    If parameter ``value`` isn't of the type parameter ``attributeType`` names.
		:raises TypeError:    If parameter ``length`` isn't of type :class:`int`.
		"""
		if key is None:
			raise ValueError(f"Parameter 'key' is None.")
		elif not isinstance(key, str):
			ex = TypeError(f"Parameter 'key' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(key)}'.")
			raise ex

		if attributeType is None:
			raise ValueError(f"Parameter 'attributeType' is None.")
		elif not isinstance(attributeType, UserAttributeType):
			ex = TypeError(f"Parameter 'attributeType' is not of type 'UserAttributeType'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(attributeType)}'.")
			raise ex

		if attributeType in (UserAttributeType.Integer, UserAttributeType.Integer64):
			valueType = int
		elif attributeType in (UserAttributeType.Float, UserAttributeType.Double):
			valueType = float
		else:
			valueType = str

		if value is not None and (not isinstance(value, valueType) or isinstance(value, bool)):
			ex = TypeError(f"Parameter 'value' is not of type '{valueType.__name__}'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(value)}' for attribute type '{attributeType}'.")
			raise ex

		if length is not None and not isinstance(length, int):
			ex = TypeError(f"Parameter 'length' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(length)}'.")
			raise ex

		self._key =    key
		self._type =   attributeType
		self._value =  value
		self._length = length

	@classmethod
	def Parse(cls, element: _Element) -> Self:
		"""
		Parse a user-defined attribute from its ``<userAttr>`` element.

		The value is the element's text, surrounding whitespace removed; an empty text is no value.

		:param element:            The ``<userAttr>`` element.
		:returns:                  The user-defined attribute.
		:raises CodeCoverageError: If the value isn't of the type the attribute states.
		"""
		key =           element.attrib["key"]
		attributeType = UserAttributeType(element.attrib["type"])
		text =          "" if element.text is None else element.text.strip()
		length =        element.attrib.get("len")

		value: Nullable[int | float | str] = None
		if text != "":
			try:
				if attributeType in (UserAttributeType.Integer, UserAttributeType.Integer64):
					value = int(text)
				elif attributeType in (UserAttributeType.Float, UserAttributeType.Double):
					value = float(text)
				else:
					value = text
			except ValueError as cause:
				ex = CodeCoverageError(f"UCIS user attribute '{key}' states a value not of type '{attributeType}'.")
				ex.add_note(f"Got value '{text}'.")
				raise ex from cause

		return cls(key, attributeType, value, None if length is None else int(length))

	@readonly
	def Key(self) -> str:
		"""
		Read-only property to access the key of the attribute (:attr:`_key`).

		:returns: The key.
		"""
		return self._key

	@readonly
	def Type(self) -> UserAttributeType:
		"""
		Read-only property to access the type of the attribute's value (:attr:`_type`).

		:returns: The type.
		"""
		return self._type

	@readonly
	def Value(self) -> Nullable[int | float | str]:
		"""
		Read-only property to access the value (:attr:`_value`).

		:returns: The value, of the type :attr:`Type` names; ``None``, if the report states none.
		"""
		return self._value

	@readonly
	def Length(self) -> Nullable[int]:
		"""
		Read-only property to access the length of a bit string (:attr:`_length`).

		:returns: The length; ``None``, if the report states none.
		"""
		return self._length


@export
@abstractclass
class Base(metaclass=ExtendedType, slots=True):
	"""
	Base-class of the elements stating user-defined attributes.
	"""

	_userAttributes: list[UserAttribute]  #: The user-defined attributes.

	def __init__(self, userAttributes: Nullable[Iterable[UserAttribute]] = None) -> None:
		"""
		Initialize the user-defined attributes.

		:param userAttributes: Optional, the user-defined attributes. Default: ``None``.
		:raises TypeError:     If parameter ``userAttributes`` isn't iterable.
		:raises TypeError:     If parameter ``userAttributes`` contains an element not of type :class:`UserAttribute`.
		"""
		self._userAttributes = []

		if userAttributes is not None:
			if not isinstance(userAttributes, Iterable):
				ex = TypeError(f"Parameter 'userAttributes' is not iterable.")
				ex.add_note(f"Got type '{getFullyQualifiedName(userAttributes)}'.")
				raise ex

			for userAttribute in userAttributes:
				if not isinstance(userAttribute, UserAttribute):
					ex = TypeError(f"Parameter 'userAttributes' contains an element not of type 'UserAttribute'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(userAttribute)}'.")
					raise ex

				self._userAttributes.append(userAttribute)

	@staticmethod
	def _ParseUserAttributes(element: _Element) -> list[UserAttribute]:
		"""
		Parse the user-defined attributes of an element, its ``<userAttr>`` elements.

		:param element:            The element.
		:returns:                  The user-defined attributes, in the order the report lists them.
		:raises CodeCoverageError: If a value isn't of the type its attribute states.
		"""
		return [UserAttribute.Parse(attributeElement) for attributeElement in element.iterfind("{*}userAttr")]

	@staticmethod
	def _ParseBoolean(value: str) -> bool:
		"""
		Parse an attribute's value of XML Schema type ``boolean``.

		:param value: The value: ``true``, ``1``, ``false`` or ``0``.
		:returns:     The boolean.
		"""
		return value in ("true", "1")

	@readonly
	def UserAttributes(self) -> list[UserAttribute]:
		"""
		Read-only property to access the user-defined attributes (:attr:`_userAttributes`).

		:returns: The user-defined attributes, in the order the report lists them.
		"""
		return self._userAttributes


@export
class ObjectAttributesMixin(metaclass=ExtendedType, mixin=True):
	"""
	A mixin-class adding the attributes of an object: its alias, whether it is excluded and why, and its weight.
	"""

	_alias:          Nullable[str]  #: An alias of the object's name.
	_isExcluded:     bool           #: Whether the object is excluded from the coverage.
	_excludedReason: Nullable[str]  #: Why the object is excluded.
	_weight:         int            #: Weight of the object in computing the coverage.

	def __init__(
		self,
		alias: Nullable[str] = None,
		excluded: bool = False,
		excludedReason: Nullable[str] = None,
		weight: int = 1
	) -> None:
		"""
		Initialize the attributes of the object.

		:param alias:          Optional, an alias of the object's name. Default: ``None``.
		:param excluded:       Optional, whether the object is excluded from the coverage. Default: ``False``.
		:param excludedReason: Optional, why the object is excluded. Default: ``None``.
		:param weight:         Optional, weight of the object in computing the coverage. Default: ``1``.
		:raises TypeError:     If parameter ``alias`` isn't of type :class:`str`.
		:raises ValueError:    If parameter ``excluded`` is ``None``.
		:raises TypeError:     If parameter ``excluded`` isn't of type :class:`bool`.
		:raises TypeError:     If parameter ``excludedReason`` isn't of type :class:`str`.
		:raises ValueError:    If parameter ``weight`` is ``None``.
		:raises TypeError:     If parameter ``weight`` isn't of type :class:`int`.
		:raises ValueError:    If parameter ``weight`` is negative.
		"""
		if alias is not None and not isinstance(alias, str):
			ex = TypeError(f"Parameter 'alias' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(alias)}'.")
			raise ex

		if excluded is None:
			raise ValueError(f"Parameter 'excluded' is None.")
		elif not isinstance(excluded, bool):
			ex = TypeError(f"Parameter 'excluded' is not of type 'bool'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(excluded)}'.")
			raise ex

		if excludedReason is not None and not isinstance(excludedReason, str):
			ex = TypeError(f"Parameter 'excludedReason' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(excludedReason)}'.")
			raise ex

		if weight is None:
			raise ValueError(f"Parameter 'weight' is None.")
		elif not isinstance(weight, int) or isinstance(weight, bool):
			ex = TypeError(f"Parameter 'weight' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(weight)}'.")
			raise ex
		elif weight < 0:
			ex = ValueError(f"Parameter 'weight' is negative.")
			ex.add_note(f"Got value '{weight}'.")
			raise ex

		self._alias =          alias
		self._isExcluded =     excluded
		self._excludedReason = excludedReason
		self._weight =         weight

	@readonly
	def Alias(self) -> Nullable[str]:
		"""
		Read-only property to access the alias of the object's name (:attr:`_alias`).

		:returns: The alias; ``None``, if the report states none.
		"""
		return self._alias

	@readonly
	def IsExcluded(self) -> bool:
		"""
		Read-only property to access whether the object is excluded from the coverage (:attr:`_isExcluded`).

		:returns: ``True``, if excluded.
		"""
		return self._isExcluded

	@readonly
	def ExcludedReason(self) -> Nullable[str]:
		"""
		Read-only property to access why the object is excluded (:attr:`_excludedReason`).

		:returns: The reason; ``None``, if the report states none.
		"""
		return self._excludedReason

	@readonly
	def Weight(self) -> int:
		"""
		Read-only property to access the weight of the object in computing the coverage (:attr:`_weight`).

		:returns: The weight; ``1``, if the report states none.
		"""
		return self._weight


@export
class StatementID(metaclass=ExtendedType, slots=True):
	"""
	A source statement identifier: the source file, the line and the index of the statement in the line.

	It is stated e.g. by an ``<id>`` element. It is a value, as a path is: it names no parent.
	"""

	_fileID:      int  #: ID of the source file.
	_lineNumber:  int  #: Line number, counted from 1.
	_inlineCount: int  #: Index of the statement in its line, counted from 1.

	def __init__(self, fileID: int, lineNumber: int, inlineCount: int) -> None:
		"""
		Initialize the source statement identifier.

		:param fileID:      ID of the source file.
		:param lineNumber:  Line number, counted from 1.
		:param inlineCount: Index of the statement in its line, counted from 1.
		:raises ValueError: If parameter ``fileID`` is ``None``.
		:raises TypeError:  If parameter ``fileID`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``fileID`` is less than 1.
		:raises ValueError: If parameter ``lineNumber`` is ``None``.
		:raises TypeError:  If parameter ``lineNumber`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``lineNumber`` is less than 1.
		:raises ValueError: If parameter ``inlineCount`` is ``None``.
		:raises TypeError:  If parameter ``inlineCount`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``inlineCount`` is less than 1.
		"""
		for name, value in (
			("fileID",      fileID),
			("lineNumber",  lineNumber),
			("inlineCount", inlineCount)
		):
			if value is None:
				raise ValueError(f"Parameter '{name}' is None.")
			elif not isinstance(value, int) or isinstance(value, bool):
				ex = TypeError(f"Parameter '{name}' is not of type 'int'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
				raise ex
			elif value < 1:
				ex = ValueError(f"Parameter '{name}' is less than 1.")
				ex.add_note(f"Got value '{value}'.")
				raise ex

		self._fileID =      fileID
		self._lineNumber =  lineNumber
		self._inlineCount = inlineCount

	@classmethod
	def Parse(cls, element: _Element) -> Self:
		"""
		Parse a source statement identifier from its element.

		The element is e.g. an ``<id>``.

		:param element: The identifier's element.
		:returns:       The source statement identifier.
		"""
		return cls(int(element.attrib["file"]), int(element.attrib["line"]), int(element.attrib["inlineCount"]))

	@readonly
	def FileID(self) -> int:
		"""
		Read-only property to access the ID of the source file (:attr:`_fileID`).

		:returns: The ID, as the report's source file states it.
		"""
		return self._fileID

	@readonly
	def LineNumber(self) -> int:
		"""
		Read-only property to access the line number (:attr:`_lineNumber`).

		:returns: The line number, counted from 1.
		"""
		return self._lineNumber

	@readonly
	def InlineCount(self) -> int:
		"""
		Read-only property to access the index of the statement in its line (:attr:`_inlineCount`).

		:returns: The index, counted from 1.
		"""
		return self._inlineCount

	def __repr__(self) -> str:
		"""
		Return a representation of the identifier for debugging.

		The first statement in line 12 of file 1 reads ``<StatementID 1:12:1>``.

		:returns: The file ID, the line number and the index in the line.
		"""
		return f"<StatementID {self._fileID}:{self._lineNumber}:{self._inlineCount}>"


@export
@abstractclass
class MetricCoverage(Base):
	"""
	Base-class of the coverage of one kind of an instance: its metric mode and weight.

	A ``<blockCoverage>`` is such a coverage. An instance states a kind's coverage once per metric mode.
	"""

	_parent:     Nullable[InstanceCoverage]  #: The instance the coverage belongs to.
	_metricMode: Nullable[str]               #: The mode in which the coverage was measured.
	_weight:     int                         #: Weight of the mode in computing the coverage.

	def __init__(
		self,
		metricMode: Nullable[str] = None,
		weight: int = 1,
		userAttributes: Nullable[Iterable[UserAttribute]] = None,
		*,
		parent: Nullable[InstanceCoverage] = None
	) -> None:
		"""
		Initialize the metric mode, the weight and the parent of the coverage.

		A derived class adds the coverage to its instance.

		:param metricMode:     Optional, the mode in which the coverage was measured, e.g. ``UCIS:BITWISE_FLAT``.
		                       Default: ``None``.
		:param weight:         Optional, weight of the mode in computing the coverage. Default: ``1``.
		:param userAttributes: Optional, the user-defined attributes. Default: ``None``.
		:param parent:         Optional, the instance the coverage belongs to. Default: ``None``.
		:raises TypeError:     If parameter ``userAttributes`` isn't iterable.
		:raises TypeError:     If parameter ``userAttributes`` contains an element not of type :class:`UserAttribute`.
		:raises TypeError:     If parameter ``metricMode`` isn't of type :class:`str`.
		:raises ValueError:    If parameter ``weight`` is ``None``.
		:raises TypeError:     If parameter ``weight`` isn't of type :class:`int`.
		:raises ValueError:    If parameter ``weight`` is negative.
		:raises TypeError:     If parameter ``parent`` isn't of type
		                       :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Instances.InstanceCoverage`.
		"""
		from pyEDAA.Reports.CodeCoverage.UCIS.Instances import InstanceCoverage

		super().__init__(userAttributes)

		if metricMode is not None and not isinstance(metricMode, str):
			ex = TypeError(f"Parameter 'metricMode' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(metricMode)}'.")
			raise ex

		if weight is None:
			raise ValueError(f"Parameter 'weight' is None.")
		elif not isinstance(weight, int) or isinstance(weight, bool):
			ex = TypeError(f"Parameter 'weight' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(weight)}'.")
			raise ex
		elif weight < 0:
			ex = ValueError(f"Parameter 'weight' is negative.")
			ex.add_note(f"Got value '{weight}'.")
			raise ex

		if parent is not None and not isinstance(parent, InstanceCoverage):
			ex = TypeError(f"Parameter 'parent' is not of type 'InstanceCoverage'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =     parent
		self._metricMode = metricMode
		self._weight =     weight

	@readonly
	def Parent(self) -> Nullable[InstanceCoverage]:
		"""
		Read-only property to access the instance the coverage belongs to (:attr:`_parent`).

		:returns: The instance; ``None``, if the coverage belongs to none.
		"""
		return self._parent

	@readonly
	def MetricMode(self) -> Nullable[str]:
		"""
		Read-only property to access the mode in which the coverage was measured (:attr:`_metricMode`).

		:returns: The mode; ``None``, if the report states none.
		"""
		return self._metricMode

	@readonly
	def Weight(self) -> int:
		"""
		Read-only property to access the weight of the mode in computing the coverage (:attr:`_weight`).

		:returns: The weight; ``1``, if the report states none.
		"""
		return self._weight
