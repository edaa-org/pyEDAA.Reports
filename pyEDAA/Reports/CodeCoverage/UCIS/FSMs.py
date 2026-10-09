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
The FSM coverage of the UCIS XML interchange format: an instance's ``<fsmCoverage>``, its finite state machines, their
states and transitions.
"""
from __future__                                   import annotations

from typing                                       import TYPE_CHECKING, Iterable, Optional as Nullable, Self

from lxml.etree                                   import _Element
from pyTooling.Common                             import getFullyQualifiedName
from pyTooling.Decorators                         import export, readonly

from pyEDAA.Reports.CodeCoverage.UCIS.Bins        import Bin
from pyEDAA.Reports.CodeCoverage.UCIS.Elements    import Base, MetricCoverage, ObjectAttributesMixin, UserAttribute

if TYPE_CHECKING:
	from pyEDAA.Reports.CodeCoverage.UCIS.Instances import InstanceCoverage


# A class with a property named like a class - ``Bin`` - can't name that class in the annotation of a field: the class
# body's namespace, where annotations are evaluated, binds the name to the property.
_Bin = Bin


@export
class FSMCoverage(MetricCoverage):
	"""
	An ``<fsmCoverage>`` of an instance: its finite state machines.
	"""

	_fsms: list[FSM]  #: The finite state machines.

	def __init__(
		self,
		metricMode: Nullable[str] = None,
		weight: int = 1,
		userAttributes: Nullable[Iterable[UserAttribute]] = None,
		*,
		parent: Nullable[InstanceCoverage] = None
	) -> None:
		"""
		Initialize the FSM coverage, and append it to the FSM coverages of its instance.

		Its finite state machines are added by creating them with this coverage as their parent.

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

		self._fsms = []

		if parent is not None:
			parent._fsmCoverages.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[InstanceCoverage] = None) -> Self:
		"""
		Parse an FSM coverage and its finite state machines from its ``<fsmCoverage>`` element.

		:param element:            The ``<fsmCoverage>`` element.
		:param parent:             Optional, the instance the coverage belongs to. Default: ``None``.
		:returns:                  The FSM coverage.
		:raises CodeCoverageError: If a user-defined attribute's value isn't of the type the attribute states.
		"""
		fsmCoverage = cls(
			element.attrib.get("metricMode"),
			int(element.attrib.get("weight", "1")),
			cls._ParseUserAttributes(element),
			parent=parent
		)

		for fsmElement in element.iterfind("{*}fsm"):
			FSM.Parse(fsmElement, parent=fsmCoverage)

		return fsmCoverage

	@readonly
	def FSMs(self) -> list[FSM]:
		"""
		Read-only property to access the finite state machines (:attr:`_fsms`).

		:returns: The finite state machines, in the order the report lists them.
		"""
		return self._fsms


@export
class FSM(Base, ObjectAttributesMixin):
	"""
	An ``<fsm>`` of an FSM coverage: a finite state machine, the signal holding its state, its states and transitions.
	"""

	_parent:      Nullable[FSMCoverage]  #: The FSM coverage the finite state machine belongs to.
	_name:        Nullable[str]          #: Name of the signal holding the state.
	_type:        Nullable[str]          #: Declared type of the signal holding the state.
	_width:       Nullable[int]          #: Bit width of the signal holding the state.
	_states:      list[FSMState]         #: The states.
	_transitions: list[FSMTransition]    #: The transitions.

	def __init__(
		self,
		name: Nullable[str] = None,
		objectType: Nullable[str] = None,
		width: Nullable[int] = None,
		alias: Nullable[str] = None,
		excluded: bool = False,
		excludedReason: Nullable[str] = None,
		weight: int = 1,
		userAttributes: Nullable[Iterable[UserAttribute]] = None,
		*,
		parent: Nullable[FSMCoverage] = None
	) -> None:
		"""
		Initialize the finite state machine, and append it to the finite state machines of its FSM coverage.

		Its states and transitions are added by creating them with this finite state machine as their parent.

		:param name:           Optional, name of the signal holding the state, e.g. ``ctrl``. Default: ``None``.
		:param objectType:     Optional, declared type of the signal holding the state, e.g. ``reg``. Default: ``None``.
		:param width:          Optional, bit width of the signal holding the state. Default: ``None``.
		:param alias:          Optional, an alias of the finite state machine's name. Default: ``None``.
		:param excluded:       Optional, whether the finite state machine is excluded from the coverage. Default:
		                       ``False``.
		:param excludedReason: Optional, why the finite state machine is excluded. Default: ``None``.
		:param weight:         Optional, weight of the finite state machine in computing the coverage. Default: ``1``.
		:param userAttributes: Optional, the user-defined attributes. Default: ``None``.
		:param parent:         Optional, the FSM coverage the finite state machine belongs to. Default: ``None``.
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
		:raises TypeError:     If parameter ``name`` or ``objectType`` isn't of type :class:`str`.
		:raises TypeError:     If parameter ``width`` isn't of type :class:`int`.
		:raises ValueError:    If parameter ``width`` is less than 1.
		:raises TypeError:     If parameter ``parent`` isn't of type :class:`FSMCoverage`.
		"""
		super().__init__(userAttributes)
		ObjectAttributesMixin.__init__(self, alias, excluded, excludedReason, weight)

		for parameterName, value in (
			("name",       name),
			("objectType", objectType)
		):
			if value is not None and not isinstance(value, str):
				ex = TypeError(f"Parameter '{parameterName}' is not of type 'str'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
				raise ex

		if width is not None:
			if not isinstance(width, int) or isinstance(width, bool):
				ex = TypeError(f"Parameter 'width' is not of type 'int'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(width)}'.")
				raise ex
			elif width < 1:
				ex = ValueError(f"Parameter 'width' is less than 1.")
				ex.add_note(f"Got value '{width}'.")
				raise ex

		if parent is not None and not isinstance(parent, FSMCoverage):
			ex = TypeError(f"Parameter 'parent' is not of type 'FSMCoverage'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =      parent
		self._name =        name
		self._type =        objectType
		self._width =       width
		self._states =      []
		self._transitions = []

		if parent is not None:
			parent._fsms.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[FSMCoverage] = None) -> Self:
		"""
		Parse a finite state machine, its states and transitions from its ``<fsm>`` element.

		:param element:            The ``<fsm>`` element.
		:param parent:             Optional, the FSM coverage the finite state machine belongs to. Default: ``None``.
		:returns:                  The finite state machine.
		:raises CodeCoverageError: If a user-defined attribute's value isn't of the type the attribute states.
		"""
		width = element.attrib.get("width")
		fsm = cls(
			element.attrib.get("name"),
			element.attrib.get("type"),
			None if width is None else int(width),
			element.attrib.get("alias"),
			cls._ParseBoolean(element.attrib.get("excluded", "false")),
			element.attrib.get("excludedReason"),
			int(element.attrib.get("weight", "1")),
			cls._ParseUserAttributes(element),
			parent=parent
		)

		for stateElement in element.iterfind("{*}state"):
			FSMState.Parse(stateElement, parent=fsm)

		for transitionElement in element.iterfind("{*}stateTransition"):
			FSMTransition.Parse(transitionElement, parent=fsm)

		return fsm

	@readonly
	def Parent(self) -> Nullable[FSMCoverage]:
		"""
		Read-only property to access the FSM coverage the finite state machine belongs to (:attr:`_parent`).

		:returns: The FSM coverage; ``None``, if the finite state machine belongs to none.
		"""
		return self._parent

	@readonly
	def Name(self) -> Nullable[str]:
		"""
		Read-only property to access the name of the signal holding the state (:attr:`_name`).

		:returns: The name, e.g. ``ctrl``; ``None``, if the report states none.
		"""
		return self._name

	@readonly
	def Type(self) -> Nullable[str]:
		"""
		Read-only property to access the declared type of the signal holding the state (:attr:`_type`).

		:returns: The type, e.g. ``reg``; ``None``, if the report states none.
		"""
		return self._type

	@readonly
	def Width(self) -> Nullable[int]:
		"""
		Read-only property to access the bit width of the signal holding the state (:attr:`_width`).

		:returns: The width; ``None``, if the report states none.
		"""
		return self._width

	@readonly
	def States(self) -> list[FSMState]:
		"""
		Read-only property to access the states (:attr:`_states`).

		:returns: The states, in the order the report lists them.
		"""
		return self._states

	@readonly
	def Transitions(self) -> list[FSMTransition]:
		"""
		Read-only property to access the transitions (:attr:`_transitions`).

		:returns: The transitions, in the order the report lists them.
		"""
		return self._transitions


@export
class FSMState(Base):
	"""
	A ``<state>`` of a finite state machine: its name, value and bin - how often the machine was in it.
	"""

	_parent: Nullable[FSM]  #: The finite state machine the state belongs to.
	_name:   Nullable[str]  #: Name of the state.
	_value:  Nullable[str]  #: Value representing the state.
	_bin:    _Bin           #: How often the machine was in the state.

	def __init__(
		self,
		coverBin: Bin,
		name: Nullable[str] = None,
		value: Nullable[str] = None,
		userAttributes: Nullable[Iterable[UserAttribute]] = None,
		*,
		parent: Nullable[FSM] = None
	) -> None:
		"""
		Initialize the state, become its bin's parent, and append it to the states of its finite state machine.

		:param coverBin:       How often the machine was in the state.
		:param name:           Optional, name of the state, e.g. ``IDLE``. Default: ``None``.
		:param value:          Optional, value representing the state, e.g. ``4``. Default: ``None``.
		:param userAttributes: Optional, the user-defined attributes. Default: ``None``.
		:param parent:         Optional, the finite state machine the state belongs to. Default: ``None``.
		:raises TypeError:     If parameter ``userAttributes`` isn't iterable.
		:raises TypeError:     If parameter ``userAttributes`` contains an element not of type
		                       :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Elements.UserAttribute`.
		:raises ValueError:    If parameter ``coverBin`` is ``None``.
		:raises TypeError:     If parameter ``coverBin`` isn't of type :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Bins.Bin`.
		:raises TypeError:     If parameter ``name`` or ``value`` isn't of type :class:`str`.
		:raises TypeError:     If parameter ``parent`` isn't of type :class:`FSM`.
		"""
		super().__init__(userAttributes)

		if coverBin is None:
			raise ValueError(f"Parameter 'coverBin' is None.")
		elif not isinstance(coverBin, Bin):
			ex = TypeError(f"Parameter 'coverBin' is not of type 'Bin'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(coverBin)}'.")
			raise ex

		for parameterName, parameterValue in (
			("name",  name),
			("value", value)
		):
			if parameterValue is not None and not isinstance(parameterValue, str):
				ex = TypeError(f"Parameter '{parameterName}' is not of type 'str'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(parameterValue)}'.")
				raise ex

		if parent is not None and not isinstance(parent, FSM):
			ex = TypeError(f"Parameter 'parent' is not of type 'FSM'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =     parent
		self._name =       name
		self._value =      value
		self._bin =        coverBin
		coverBin._parent = self

		if parent is not None:
			parent._states.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[FSM] = None) -> Self:
		"""
		Parse a state and its bin from its ``<state>`` element.

		:param element:            The ``<state>`` element.
		:param parent:             Optional, the finite state machine the state belongs to. Default: ``None``.
		:returns:                  The state.
		:raises CodeCoverageError: If a user-defined attribute's value isn't of the type the attribute states.
		"""
		return cls(
			Bin.Parse(element.find("{*}stateBin")),
			element.attrib.get("stateName"),
			element.attrib.get("stateValue"),
			cls._ParseUserAttributes(element),
			parent=parent
		)

	@readonly
	def Parent(self) -> Nullable[FSM]:
		"""
		Read-only property to access the finite state machine the state belongs to (:attr:`_parent`).

		:returns: The finite state machine; ``None``, if the state belongs to none.
		"""
		return self._parent

	@readonly
	def Name(self) -> Nullable[str]:
		"""
		Read-only property to access the name of the state (:attr:`_name`).

		:returns: The name, e.g. ``IDLE``; ``None``, if the report states none.
		"""
		return self._name

	@readonly
	def Value(self) -> Nullable[str]:
		"""
		Read-only property to access the value representing the state (:attr:`_value`).

		:returns: The value, as stated; ``None``, if the report states none.
		"""
		return self._value

	@readonly
	def Bin(self) -> Bin:
		"""
		Read-only property to access the state's bin (:attr:`_bin`).

		:returns: The bin, stating how often the machine was in the state.
		"""
		return self._bin


@export
class FSMTransition(Base):
	"""
	A ``<stateTransition>`` of a finite state machine: the states it passes, and its bin - how often it happened.
	"""

	_parent: Nullable[FSM]  #: The finite state machine the transition belongs to.
	_states: list[str]      #: The states the transition passes, from the first one.
	_bin:    _Bin           #: How often the transition happened.

	def __init__(
		self,
		states: Iterable[str],
		coverBin: Bin,
		userAttributes: Nullable[Iterable[UserAttribute]] = None,
		*,
		parent: Nullable[FSM] = None
	) -> None:
		"""
		Initialize the transition, become its bin's parent, and append it to the transitions of its finite state machine.

		:param states:         The states the transition passes, from the first one, e.g. ``["IDLE", "ACTIVE"]``.
		:param coverBin:       How often the transition happened.
		:param userAttributes: Optional, the user-defined attributes. Default: ``None``.
		:param parent:         Optional, the finite state machine the transition belongs to. Default: ``None``.
		:raises TypeError:     If parameter ``userAttributes`` isn't iterable.
		:raises TypeError:     If parameter ``userAttributes`` contains an element not of type
		                       :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Elements.UserAttribute`.
		:raises ValueError:    If parameter ``coverBin`` is ``None``.
		:raises TypeError:     If parameter ``coverBin`` isn't of type :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Bins.Bin`.
		:raises TypeError:     If parameter ``parent`` isn't of type :class:`FSM`.
		:raises ValueError:    If parameter ``states`` is ``None``.
		:raises TypeError:     If parameter ``states`` isn't iterable.
		:raises TypeError:     If parameter ``states`` contains an element not of type :class:`str`.
		:raises ValueError:    If parameter ``states`` has less than two states.
		"""
		super().__init__(userAttributes)

		if coverBin is None:
			raise ValueError(f"Parameter 'coverBin' is None.")
		elif not isinstance(coverBin, Bin):
			ex = TypeError(f"Parameter 'coverBin' is not of type 'Bin'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(coverBin)}'.")
			raise ex

		if parent is not None and not isinstance(parent, FSM):
			ex = TypeError(f"Parameter 'parent' is not of type 'FSM'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =     parent
		self._states =     []
		self._bin =        coverBin
		coverBin._parent = self

		if states is None:
			raise ValueError(f"Parameter 'states' is None.")
		elif not isinstance(states, Iterable):
			ex = TypeError(f"Parameter 'states' is not iterable.")
			ex.add_note(f"Got type '{getFullyQualifiedName(states)}'.")
			raise ex

		for state in states:
			if not isinstance(state, str):
				ex = TypeError(f"Parameter 'states' contains an element not of type 'str'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(state)}'.")
				raise ex

			self._states.append(state)

		if len(self._states) < 2:
			ex = ValueError(f"Parameter 'states' has less than two states.")
			ex.add_note(f"Got {len(self._states)} state(s).")
			raise ex

		if parent is not None:
			parent._transitions.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[FSM] = None) -> Self:
		"""
		Parse a transition and its bin from its ``<stateTransition>`` element.

		:param element:            The ``<stateTransition>`` element.
		:param parent:             Optional, the finite state machine the transition belongs to. Default: ``None``.
		:returns:                  The transition.
		:raises CodeCoverageError: If a user-defined attribute's value isn't of the type the attribute states.
		"""
		return cls(
			[stateElement.text or "" for stateElement in element.iterfind("{*}state")],
			Bin.Parse(element.find("{*}transitionBin")),
			cls._ParseUserAttributes(element),
			parent=parent
		)

	@readonly
	def Parent(self) -> Nullable[FSM]:
		"""
		Read-only property to access the finite state machine the transition belongs to (:attr:`_parent`).

		:returns: The finite state machine; ``None``, if the transition belongs to none.
		"""
		return self._parent

	@readonly
	def States(self) -> list[str]:
		"""
		Read-only property to access the states the transition passes (:attr:`_states`).

		:returns: The states, from the first one, as the report states them.
		"""
		return self._states

	@readonly
	def Bin(self) -> Bin:
		"""
		Read-only property to access the transition's bin (:attr:`_bin`).

		:returns: The bin, stating how often the transition happened.
		"""
		return self._bin
