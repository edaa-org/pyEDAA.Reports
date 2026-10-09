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
The toggle coverage of the UCIS XML interchange format: an instance's ``<toggleCoverage>``, its metric modes, and its
signals - toggle objects - with their dimensions.
"""
from __future__                                   import annotations

from typing                                       import TYPE_CHECKING, Iterable, Optional as Nullable, Self

from lxml.etree                                   import _Element
from pyTooling.Common                             import getFullyQualifiedName
from pyTooling.Decorators                         import export, readonly
from pyTooling.MetaClasses                        import ExtendedType

from pyEDAA.Reports.CodeCoverage.UCIS.Elements    import Base, MetricCoverage, ObjectAttributesMixin, StatementID
from pyEDAA.Reports.CodeCoverage.UCIS.Elements    import UserAttribute
from pyEDAA.Reports.CodeCoverage.UCIS.ToggleBits  import ToggleBit

if TYPE_CHECKING:
	from pyEDAA.Reports.CodeCoverage.UCIS.Instances import InstanceCoverage


@export
class MetricMode(Base):
	"""
	A ``<metricMode>`` of a toggle coverage: a mode, in which the coverage was measured, and its user-defined attributes.
	"""

	_parent:     Nullable[ToggleCoverage]  #: The toggle coverage the metric mode belongs to.
	_metricMode: str                       #: Name of the mode, e.g. ``2STOGGLE``.

	def __init__(
		self,
		metricMode: str,
		userAttributes: Nullable[Iterable[UserAttribute]] = None,
		*,
		parent: Nullable[ToggleCoverage] = None
	) -> None:
		"""
		Initialize the metric mode, and append it to the metric modes of its toggle coverage.

		:param metricMode:     Name of the mode, e.g. ``2STOGGLE``.
		:param userAttributes: Optional, the user-defined attributes. Default: ``None``.
		:param parent:         Optional, the toggle coverage the metric mode belongs to. Default: ``None``.
		:raises TypeError:     If parameter ``userAttributes`` isn't iterable.
		:raises TypeError:     If parameter ``userAttributes`` contains an element not of type
		                       :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Elements.UserAttribute`.
		:raises ValueError:    If parameter ``metricMode`` is ``None``.
		:raises TypeError:     If parameter ``metricMode`` isn't of type :class:`str`.
		:raises TypeError:     If parameter ``parent`` isn't of type :class:`ToggleCoverage`.
		"""
		super().__init__(userAttributes)

		if metricMode is None:
			raise ValueError(f"Parameter 'metricMode' is None.")
		elif not isinstance(metricMode, str):
			ex = TypeError(f"Parameter 'metricMode' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(metricMode)}'.")
			raise ex

		if parent is not None and not isinstance(parent, ToggleCoverage):
			ex = TypeError(f"Parameter 'parent' is not of type 'ToggleCoverage'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =     parent
		self._metricMode = metricMode

		if parent is not None:
			parent._metricModes.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[ToggleCoverage] = None) -> Self:
		"""
		Parse a metric mode from its ``<metricMode>`` element.

		:param element:            The ``<metricMode>`` element.
		:param parent:             Optional, the toggle coverage the metric mode belongs to. Default: ``None``.
		:returns:                  The metric mode.
		:raises CodeCoverageError: If a user-defined attribute's value isn't of the type the attribute states.
		"""
		return cls(element.attrib["metricMode"], cls._ParseUserAttributes(element), parent=parent)

	@readonly
	def Parent(self) -> Nullable[ToggleCoverage]:
		"""
		Read-only property to access the toggle coverage the metric mode belongs to (:attr:`_parent`).

		:returns: The toggle coverage; ``None``, if the metric mode belongs to none.
		"""
		return self._parent

	@readonly
	def MetricMode(self) -> str:
		"""
		Read-only property to access the name of the mode (:attr:`_metricMode`).

		:returns: The name, e.g. ``2STOGGLE``.
		"""
		return self._metricMode


@export
class ToggleCoverage(MetricCoverage):
	"""
	A ``<toggleCoverage>`` of an instance: its toggle objects and its metric modes.
	"""

	_objects:     list[ToggleObject]  #: The toggle objects.
	_metricModes: list[MetricMode]    #: The metric modes.

	def __init__(
		self,
		metricMode: Nullable[str] = None,
		weight: int = 1,
		userAttributes: Nullable[Iterable[UserAttribute]] = None,
		*,
		parent: Nullable[InstanceCoverage] = None
	) -> None:
		"""
		Initialize the toggle coverage, and append it to the toggle coverages of its instance.

		Its toggle objects and metric modes are added by creating them with this coverage as their parent.

		:param metricMode:     Optional, the mode in which the coverage was measured. Default: ``None``.
		:param weight:         Optional, weight of the mode in computing the coverage. Default: ``1``.
		:param userAttributes: Optional, the user-defined attributes. Default: ``None``.
		:param parent:         Optional, the instance the coverage belongs to. Default: ``None``.
		:raises TypeError:     If parameter ``userAttributes`` isn't iterable.
		:raises TypeError:     If parameter ``userAttributes`` contains an element not of type
		                       :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Elements.UserAttribute`.
		:raises TypeError:     If parameter ``metricMode`` isn't of type :class:`str`.
		:raises ValueError:    If parameter ``weight`` is ``None``.
		:raises TypeError:     If parameter ``weight`` isn't of type :class:`int`.
		:raises ValueError:    If parameter ``weight`` is negative.
		:raises TypeError:     If parameter ``parent`` isn't of type
		                       :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Instances.InstanceCoverage`.
		"""
		super().__init__(metricMode, weight, userAttributes, parent=parent)

		self._objects =     []
		self._metricModes = []

		if parent is not None:
			parent._toggleCoverages.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[InstanceCoverage] = None) -> Self:
		"""
		Parse a toggle coverage, its toggle objects and metric modes from its ``<toggleCoverage>`` element.

		:param element:            The ``<toggleCoverage>`` element.
		:param parent:             Optional, the instance the coverage belongs to. Default: ``None``.
		:returns:                  The toggle coverage.
		:raises CodeCoverageError: If a user-defined attribute's value isn't of the type the attribute states.
		"""
		toggleCoverage = cls(
			element.attrib.get("metricMode"),
			int(element.attrib.get("weight", "1")),
			cls._ParseUserAttributes(element),
			parent=parent
		)

		for objectElement in element.iterfind("{*}toggleObject"):
			ToggleObject.Parse(objectElement, parent=toggleCoverage)

		for modeElement in element.iterfind("{*}metricMode"):
			MetricMode.Parse(modeElement, parent=toggleCoverage)

		return toggleCoverage

	@readonly
	def Objects(self) -> list[ToggleObject]:
		"""
		Read-only property to access the toggle objects (:attr:`_objects`).

		:returns: The toggle objects, in the order the report lists them.
		"""
		return self._objects

	@readonly
	def MetricModes(self) -> list[MetricMode]:
		"""
		Read-only property to access the metric modes (:attr:`_metricModes`).

		:returns: The metric modes, in the order the report lists them.
		"""
		return self._metricModes


@export
class Dimension(metaclass=ExtendedType, slots=True):
	"""
	A ``<dimension>`` of a toggle object: its left and right index, and whether the index descends.

	It is a value, as a path is: it names no parent.
	"""

	_left:   int   #: The left index.
	_right:  int   #: The right index.
	_downTo: bool  #: Whether the index descends from left to right.

	def __init__(self, left: int, right: int, downTo: bool) -> None:
		"""
		Initialize the dimension.

		:param left:        The left index.
		:param right:       The right index.
		:param downTo:      Whether the index descends from left to right, e.g. for ``[3:0]``.
		:raises ValueError: If parameter ``left`` or ``right`` is ``None``.
		:raises TypeError:  If parameter ``left`` or ``right`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``downTo`` is ``None``.
		:raises TypeError:  If parameter ``downTo`` isn't of type :class:`bool`.
		"""
		if left is None:
			raise ValueError(f"Parameter 'left' is None.")
		elif not isinstance(left, int) or isinstance(left, bool):
			ex = TypeError(f"Parameter 'left' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(left)}'.")
			raise ex

		if right is None:
			raise ValueError(f"Parameter 'right' is None.")
		elif not isinstance(right, int) or isinstance(right, bool):
			ex = TypeError(f"Parameter 'right' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(right)}'.")
			raise ex

		if downTo is None:
			raise ValueError(f"Parameter 'downTo' is None.")
		elif not isinstance(downTo, bool):
			ex = TypeError(f"Parameter 'downTo' is not of type 'bool'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(downTo)}'.")
			raise ex

		self._left =   left
		self._right =  right
		self._downTo = downTo

	@classmethod
	def Parse(cls, element: _Element) -> Self:
		"""
		Parse a dimension from its ``<dimension>`` element.

		:param element: The ``<dimension>`` element.
		:returns:       The dimension.
		"""
		return cls(
			int(element.attrib["left"]),
			int(element.attrib["right"]),
			Base._ParseBoolean(element.attrib["downto"])
		)

	@readonly
	def Left(self) -> int:
		"""
		Read-only property to access the left index (:attr:`_left`).

		:returns: The left index.
		"""
		return self._left

	@readonly
	def Right(self) -> int:
		"""
		Read-only property to access the right index (:attr:`_right`).

		:returns: The right index.
		"""
		return self._right

	@readonly
	def DownTo(self) -> bool:
		"""
		Read-only property to access whether the index descends from left to right (:attr:`_downTo`).

		:returns: ``True``, if the index descends.
		"""
		return self._downTo


@export
class ToggleObject(Base, ObjectAttributesMixin):
	"""
	A ``<toggleObject>`` of a toggle coverage: a signal, its type, dimensions and bits, and where it is declared.
	"""

	_parent:        Nullable[ToggleCoverage]  #: The toggle coverage the toggle object belongs to.
	_name:          str                       #: Name of the signal.
	_key:           str                       #: UCIS key of the toggle object.
	_id:            StatementID               #: Where the signal is declared.
	_type:          Nullable[str]             #: Declared type of the signal.
	_portDirection: Nullable[str]             #: Direction of the signal, if it is a port.
	_dimensions:    list[Dimension]           #: The dimensions of the signal.
	_bits:          list[ToggleBit]           #: The bits of the signal.

	def __init__(
		self,
		name: str,
		key: str,
		statementID: StatementID,
		objectType: Nullable[str] = None,
		portDirection: Nullable[str] = None,
		dimensions: Nullable[Iterable[Dimension]] = None,
		alias: Nullable[str] = None,
		excluded: bool = False,
		excludedReason: Nullable[str] = None,
		weight: int = 1,
		userAttributes: Nullable[Iterable[UserAttribute]] = None,
		*,
		parent: Nullable[ToggleCoverage] = None
	) -> None:
		"""
		Initialize the toggle object, and append it to the toggle objects of its toggle coverage.

		Its bits are added by creating them with this toggle object as their parent.

		:param name:           Name of the signal, e.g. ``ff1``.
		:param key:            UCIS key of the toggle object.
		:param statementID:    Where the signal is declared.
		:param objectType:     Optional, declared type of the signal, e.g. ``wire``. Default: ``None``.
		:param portDirection:  Optional, direction of the signal, if it is a port, e.g. ``input``. Default: ``None``.
		:param dimensions:     Optional, the dimensions of the signal. Default: ``None``.
		:param alias:          Optional, an alias of the signal's name. Default: ``None``.
		:param excluded:       Optional, whether the signal is excluded from the coverage. Default: ``False``.
		:param excludedReason: Optional, why the signal is excluded. Default: ``None``.
		:param weight:         Optional, weight of the signal in computing the coverage. Default: ``1``.
		:param userAttributes: Optional, the user-defined attributes. Default: ``None``.
		:param parent:         Optional, the toggle coverage the toggle object belongs to. Default: ``None``.
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
		:raises ValueError:    If parameter ``statementID`` is ``None``.
		:raises TypeError:     If parameter ``statementID`` isn't of type
		                       :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Elements.StatementID`.
		:raises TypeError:     If parameter ``objectType`` or ``portDirection`` isn't of type :class:`str`.
		:raises TypeError:     If parameter ``parent`` isn't of type :class:`ToggleCoverage`.
		:raises TypeError:     If parameter ``dimensions`` isn't iterable.
		:raises TypeError:     If parameter ``dimensions`` contains an element not of type :class:`Dimension`.
		"""
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

		if statementID is None:
			raise ValueError(f"Parameter 'statementID' is None.")
		elif not isinstance(statementID, StatementID):
			ex = TypeError(f"Parameter 'statementID' is not of type 'StatementID'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(statementID)}'.")
			raise ex

		for parameterName, value in (
			("objectType",    objectType),
			("portDirection", portDirection)
		):
			if value is not None and not isinstance(value, str):
				ex = TypeError(f"Parameter '{parameterName}' is not of type 'str'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
				raise ex

		if parent is not None and not isinstance(parent, ToggleCoverage):
			ex = TypeError(f"Parameter 'parent' is not of type 'ToggleCoverage'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =        parent
		self._name =          name
		self._key =           key
		self._id =            statementID
		self._type =          objectType
		self._portDirection = portDirection
		self._dimensions =    []
		self._bits =          []

		if dimensions is not None:
			if not isinstance(dimensions, Iterable):
				ex = TypeError(f"Parameter 'dimensions' is not iterable.")
				ex.add_note(f"Got type '{getFullyQualifiedName(dimensions)}'.")
				raise ex

			for dimension in dimensions:
				if not isinstance(dimension, Dimension):
					ex = TypeError(f"Parameter 'dimensions' contains an element not of type 'Dimension'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(dimension)}'.")
					raise ex

				self._dimensions.append(dimension)

		if parent is not None:
			parent._objects.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[ToggleCoverage] = None) -> Self:
		"""
		Parse a toggle object and its bits from its ``<toggleObject>`` element.

		:param element:            The ``<toggleObject>`` element.
		:param parent:             Optional, the toggle coverage the toggle object belongs to. Default: ``None``.
		:returns:                  The toggle object.
		:raises CodeCoverageError: If a user-defined attribute's value isn't of the type the attribute states.
		"""
		toggleObject = cls(
			element.attrib["name"],
			element.attrib["key"],
			StatementID.Parse(element.find("{*}id")),
			element.attrib.get("type"),
			element.attrib.get("portDirection"),
			[Dimension.Parse(dimensionElement) for dimensionElement in element.iterfind("{*}dimension")],
			element.attrib.get("alias"),
			cls._ParseBoolean(element.attrib.get("excluded", "false")),
			element.attrib.get("excludedReason"),
			int(element.attrib.get("weight", "1")),
			cls._ParseUserAttributes(element),
			parent=parent
		)

		for bitElement in element.iterfind("{*}toggleBit"):
			ToggleBit.Parse(bitElement, parent=toggleObject)

		return toggleObject

	@readonly
	def Parent(self) -> Nullable[ToggleCoverage]:
		"""
		Read-only property to access the toggle coverage the toggle object belongs to (:attr:`_parent`).

		:returns: The toggle coverage; ``None``, if the toggle object belongs to none.
		"""
		return self._parent

	@readonly
	def Name(self) -> str:
		"""
		Read-only property to access the name of the signal (:attr:`_name`).

		:returns: The name, as declared.
		"""
		return self._name

	@readonly
	def Key(self) -> str:
		"""
		Read-only property to access the UCIS key of the toggle object (:attr:`_key`).

		:returns: The key, as stated.
		"""
		return self._key

	@readonly
	def ID(self) -> StatementID:
		"""
		Read-only property to access where the signal is declared (:attr:`_id`).

		:returns: The source statement identifier.
		"""
		return self._id

	@readonly
	def Type(self) -> Nullable[str]:
		"""
		Read-only property to access the declared type of the signal (:attr:`_type`).

		:returns: The type, e.g. ``wire``; ``None``, if the report states none.
		"""
		return self._type

	@readonly
	def PortDirection(self) -> Nullable[str]:
		"""
		Read-only property to access the direction of the signal, if it is a port (:attr:`_portDirection`).

		:returns: The direction, e.g. ``input``; ``None``, if the report states none.
		"""
		return self._portDirection

	@readonly
	def Dimensions(self) -> list[Dimension]:
		"""
		Read-only property to access the dimensions of the signal (:attr:`_dimensions`).

		:returns: The dimensions, from the left one.
		"""
		return self._dimensions

	@readonly
	def Bits(self) -> list[ToggleBit]:
		"""
		Read-only property to access the bits of the signal (:attr:`_bits`).

		:returns: The bits, in the order the report lists them.
		"""
		return self._bits
