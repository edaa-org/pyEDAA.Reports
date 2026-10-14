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
The states and transitions of finite state machines in a scope of QuestaSim's coverage report XML.

A report lists them with details only (``vcover report -details -code f``). Unlike the other coverage items, a state and
a transition name no file number: their file is the scope's, if the scope has a single file.
"""
from __future__                                     import annotations

from pathlib                                        import Path
from typing                                         import TYPE_CHECKING, Optional as Nullable, Self

from lxml.etree                                     import _Element
from pyTooling.Common                               import getFullyQualifiedName
from pyTooling.Decorators                           import export, readonly
from pyTooling.MetaClasses                          import ExtendedType

from pyEDAA.Reports.CodeCoverage                    import CodeCoverageError

if TYPE_CHECKING:
	from pyEDAA.Reports.CodeCoverage.QuestaSim.Scopes import Scope


@export
class FSMState(metaclass=ExtendedType, slots=True):
	"""
	A ``<state>`` of a scope: a state of a finite state machine, and how often it was entered.
	"""

	_parent:     Nullable[Scope]  #: The scope the state belongs to.
	_name:       str              #: Name of the state.
	_file:       Nullable[Path]   #: Path of the source file, if known.
	_lineNumber: int              #: Line number of the state, counted from 1.
	_hits:       int              #: How often the state was entered.

	def __init__(
		self,
		name: str,
		file: Nullable[Path],
		lineNumber: int,
		hits: int,
		*,
		parent: Nullable[Scope] = None
	) -> None:
		"""
		Initialize the state, and append it to the states of its scope.

		:param name:        Name of the state.
		:param file:        Path of the source file, as the report states it; ``None``, if unknown.
		:param lineNumber:  Line number of the state, counted from 1.
		:param hits:        How often the state was entered.
		:param parent:      Optional, the scope the state belongs to. Default: ``None``.
		:raises ValueError: If parameter ``name`` is ``None``.
		:raises TypeError:  If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError: If parameter ``name`` is empty.
		:raises TypeError:  If parameter ``file`` isn't of type :class:`~pathlib.Path`.
		:raises ValueError: If parameter ``lineNumber`` is ``None``.
		:raises TypeError:  If parameter ``lineNumber`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``lineNumber`` is less than 1.
		:raises ValueError: If parameter ``hits`` is ``None``.
		:raises TypeError:  If parameter ``hits`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``hits`` is negative.
		:raises TypeError:  If parameter ``parent`` isn't of type
		                    :class:`~pyEDAA.Reports.CodeCoverage.QuestaSim.Scopes.Scope`.
		"""
		from pyEDAA.Reports.CodeCoverage.QuestaSim.Scopes import Scope

		if name is None:
			raise ValueError(f"Parameter 'name' is None.")
		elif not isinstance(name, str):
			ex = TypeError(f"Parameter 'name' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(name)}'.")
			raise ex
		elif name == "":
			raise ValueError(f"Parameter 'name' is empty.")

		if file is not None and not isinstance(file, Path):
			ex = TypeError(f"Parameter 'file' is not of type 'Path'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(file)}'.")
			raise ex

		if lineNumber is None:
			raise ValueError(f"Parameter 'lineNumber' is None.")
		elif not isinstance(lineNumber, int):
			ex = TypeError(f"Parameter 'lineNumber' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(lineNumber)}'.")
			raise ex
		elif lineNumber < 1:
			ex = ValueError(f"Parameter 'lineNumber' is less than 1.")
			ex.add_note(f"Got value '{lineNumber}'.")
			raise ex

		if hits is None:
			raise ValueError(f"Parameter 'hits' is None.")
		elif not isinstance(hits, int):
			ex = TypeError(f"Parameter 'hits' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(hits)}'.")
			raise ex
		elif hits < 0:
			ex = ValueError(f"Parameter 'hits' is negative.")
			ex.add_note(f"Got value '{hits}'.")
			raise ex

		if parent is not None and not isinstance(parent, Scope):
			ex = TypeError(f"Parameter 'parent' is not of type 'Scope'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =     parent
		self._name =       name
		self._file =       file
		self._lineNumber = lineNumber
		self._hits =       hits

		if parent is not None:
			parent._states.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Scope) -> Self:
		"""
		Parse a state from its ``<state>`` element.

		A ``<state>`` names no file number: its file is the scope's, if the scope has a single file.

		:param element: The ``<state>`` element.
		:param parent:  The scope the state belongs to.
		:returns:       The state.
		"""
		file = next(iter(parent._files.values())) if len(parent._files) == 1 else None
		return cls(
			element.attrib["state"], file, int(element.attrib["ln"]), int(element.attrib["hits"]), parent=parent
		)

	@readonly
	def Parent(self) -> Nullable[Scope]:
		"""
		Read-only property to access the scope the state belongs to (:attr:`_parent`).

		:returns: The scope; ``None`` if the state belongs to no scope.
		"""
		return self._parent

	@readonly
	def Name(self) -> str:
		"""
		Read-only property to access the name of the state (:attr:`_name`).

		:returns: The state's name, as the enumeration of the state machine names it.
		"""
		return self._name

	@readonly
	def File(self) -> Nullable[Path]:
		"""
		Read-only property to access the path of the source file (:attr:`_file`).

		:returns: The path, as the report states it; ``None``, if the scope has several files.
		"""
		return self._file

	@readonly
	def LineNumber(self) -> int:
		"""
		Read-only property to access the line number of the state (:attr:`_lineNumber`).

		:returns: The line number, counted from 1.
		"""
		return self._lineNumber

	@readonly
	def Hits(self) -> int:
		"""
		Read-only property to access how often the state was entered (:attr:`_hits`).

		:returns: The count.
		"""
		return self._hits


@export
class FSMTransition(metaclass=ExtendedType, slots=True):
	"""
	A ``<trans>`` of a scope: a transition of a finite state machine from one state to another, and how often it was
	taken.
	"""

	_parent:     Nullable[Scope]  #: The scope the transition belongs to.
	_identifier: int              #: Number of the transition in its state machine, counted from 0.
	_fromState:  str              #: Name of the state the transition leaves.
	_toState:    str              #: Name of the state the transition enters.
	_file:       Nullable[Path]   #: Path of the source file, if known.
	_lineNumber: int              #: Line number of the transition, counted from 1.
	_hits:       int              #: How often the transition was taken.

	def __init__(
		self,
		identifier: int,
		fromState: str,
		toState: str,
		file: Nullable[Path],
		lineNumber: int,
		hits: int,
		*,
		parent: Nullable[Scope] = None
	) -> None:
		"""
		Initialize the transition, and append it to the transitions of its scope.

		:param identifier:  Number of the transition in its state machine, counted from 0.
		:param fromState:   Name of the state the transition leaves.
		:param toState:     Name of the state the transition enters.
		:param file:        Path of the source file, as the report states it; ``None``, if unknown.
		:param lineNumber:  Line number of the transition, counted from 1.
		:param hits:        How often the transition was taken.
		:param parent:      Optional, the scope the transition belongs to. Default: ``None``.
		:raises ValueError: If parameter ``identifier`` is ``None``.
		:raises TypeError:  If parameter ``identifier`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``identifier`` is negative.
		:raises ValueError: If parameter ``fromState`` is ``None``.
		:raises TypeError:  If parameter ``fromState`` isn't of type :class:`str`.
		:raises ValueError: If parameter ``fromState`` is empty.
		:raises ValueError: If parameter ``toState`` is ``None``.
		:raises TypeError:  If parameter ``toState`` isn't of type :class:`str`.
		:raises ValueError: If parameter ``toState`` is empty.
		:raises TypeError:  If parameter ``file`` isn't of type :class:`~pathlib.Path`.
		:raises ValueError: If parameter ``lineNumber`` is ``None``.
		:raises TypeError:  If parameter ``lineNumber`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``lineNumber`` is less than 1.
		:raises ValueError: If parameter ``hits`` is ``None``.
		:raises TypeError:  If parameter ``hits`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``hits`` is negative.
		:raises TypeError:  If parameter ``parent`` isn't of type
		                    :class:`~pyEDAA.Reports.CodeCoverage.QuestaSim.Scopes.Scope`.
		"""
		from pyEDAA.Reports.CodeCoverage.QuestaSim.Scopes import Scope

		if identifier is None:
			raise ValueError(f"Parameter 'identifier' is None.")
		elif not isinstance(identifier, int):
			ex = TypeError(f"Parameter 'identifier' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(identifier)}'.")
			raise ex
		elif identifier < 0:
			ex = ValueError(f"Parameter 'identifier' is negative.")
			ex.add_note(f"Got value '{identifier}'.")
			raise ex

		if fromState is None:
			raise ValueError(f"Parameter 'fromState' is None.")
		elif not isinstance(fromState, str):
			ex = TypeError(f"Parameter 'fromState' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(fromState)}'.")
			raise ex
		elif fromState == "":
			raise ValueError(f"Parameter 'fromState' is empty.")

		if toState is None:
			raise ValueError(f"Parameter 'toState' is None.")
		elif not isinstance(toState, str):
			ex = TypeError(f"Parameter 'toState' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(toState)}'.")
			raise ex
		elif toState == "":
			raise ValueError(f"Parameter 'toState' is empty.")

		if file is not None and not isinstance(file, Path):
			ex = TypeError(f"Parameter 'file' is not of type 'Path'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(file)}'.")
			raise ex

		if lineNumber is None:
			raise ValueError(f"Parameter 'lineNumber' is None.")
		elif not isinstance(lineNumber, int):
			ex = TypeError(f"Parameter 'lineNumber' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(lineNumber)}'.")
			raise ex
		elif lineNumber < 1:
			ex = ValueError(f"Parameter 'lineNumber' is less than 1.")
			ex.add_note(f"Got value '{lineNumber}'.")
			raise ex

		if hits is None:
			raise ValueError(f"Parameter 'hits' is None.")
		elif not isinstance(hits, int):
			ex = TypeError(f"Parameter 'hits' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(hits)}'.")
			raise ex
		elif hits < 0:
			ex = ValueError(f"Parameter 'hits' is negative.")
			ex.add_note(f"Got value '{hits}'.")
			raise ex

		if parent is not None and not isinstance(parent, Scope):
			ex = TypeError(f"Parameter 'parent' is not of type 'Scope'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =     parent
		self._identifier = identifier
		self._fromState =  fromState
		self._toState =    toState
		self._file =       file
		self._lineNumber = lineNumber
		self._hits =       hits

		if parent is not None:
			parent._transitions.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Scope) -> Self:
		"""
		Parse a transition from its ``<trans>`` element, whose attribute ``state`` names both states.

		A ``<trans>`` names no file number: its file is the scope's, if the scope has a single file.

		:param element:            The ``<trans>`` element.
		:param parent:             The scope the transition belongs to.
		:returns:                  The transition.
		:raises CodeCoverageError: If attribute ``state`` doesn't name two states separated by ``->``. |br|
		                           Questa writes it as ``<state> -> <state>``.
		"""
		fromState, separator, toState = element.attrib["state"].partition(" -> ")
		if separator == "" or fromState == "" or toState == "":
			ex = CodeCoverageError(f"'<trans>' in line {element.sourceline} doesn't name the states it connects.")
			ex.add_note(f"Got state='{element.attrib['state']}'.")
			ex.add_note(f"Questa writes it as '<state> -> <state>'.")
			raise ex

		file = next(iter(parent._files.values())) if len(parent._files) == 1 else None
		return cls(
			int(element.attrib["tid"]),
			fromState,
			toState,
			file,
			int(element.attrib["ln"]),
			int(element.attrib["hits"]),
			parent=parent
		)

	@readonly
	def Parent(self) -> Nullable[Scope]:
		"""
		Read-only property to access the scope the transition belongs to (:attr:`_parent`).

		:returns: The scope; ``None`` if the transition belongs to no scope.
		"""
		return self._parent

	@readonly
	def Identifier(self) -> int:
		"""
		Read-only property to access the number of the transition in its state machine (:attr:`_identifier`).

		:returns: The number, counted from 0.
		"""
		return self._identifier

	@readonly
	def FromState(self) -> str:
		"""
		Read-only property to access the name of the state the transition leaves (:attr:`_fromState`).

		:returns: The state's name.
		"""
		return self._fromState

	@readonly
	def ToState(self) -> str:
		"""
		Read-only property to access the name of the state the transition enters (:attr:`_toState`).

		:returns: The state's name.
		"""
		return self._toState

	@readonly
	def File(self) -> Nullable[Path]:
		"""
		Read-only property to access the path of the source file (:attr:`_file`).

		:returns: The path, as the report states it; ``None``, if the scope has several files.
		"""
		return self._file

	@readonly
	def LineNumber(self) -> int:
		"""
		Read-only property to access the line number of the transition (:attr:`_lineNumber`).

		:returns: The line number, counted from 1.
		"""
		return self._lineNumber

	@readonly
	def Hits(self) -> int:
		"""
		Read-only property to access how often the transition was taken (:attr:`_hits`).

		:returns: The count.
		"""
		return self._hits
