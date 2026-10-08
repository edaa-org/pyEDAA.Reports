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
The records of a line of GCC's gcov JSON format: its branches, calls and conditions.
"""
from __future__            import annotations

from collections.abc       import Iterable
from typing                import Any, Optional as Nullable, Self

from pyTooling.Common      import getFullyQualifiedName
from pyTooling.Decorators  import export, readonly
from pyTooling.MetaClasses import ExtendedType


@export
class Branch(metaclass=ExtendedType, slots=True):
	"""
	A ``branch`` of a line: an edge from a basic block to another, and how often it was taken.
	"""

	_count:              int            #: Number of times the branch was taken.
	_throw:              bool           #: Whether the branch is taken by an exception.
	_fallthrough:        bool           #: Whether the branch falls through.
	_sourceBlockID:      Nullable[int]  #: ID of the basic block the branch starts at, in format 2.
	_destinationBlockID: Nullable[int]  #: ID of the basic block the branch leads to, in format 2.

	def __init__(
		self,
		count:              int,
		throw:              bool,
		fallthrough:        bool,
		sourceBlockID:      Nullable[int] = None,
		destinationBlockID: Nullable[int] = None
	) -> None:
		"""
		Initialize the branch.

		:param count:              Number of times the branch was taken.
		:param throw:              Whether the branch is taken by an exception.
		:param fallthrough:        Whether the branch falls through.
		:param sourceBlockID:      Optional, ID of the basic block the branch starts at. Default: ``None``.
		:param destinationBlockID: Optional, ID of the basic block the branch leads to. Default: ``None``.
		:raises ValueError:        If parameter ``count`` is ``None``.
		:raises TypeError:         If parameter ``count`` isn't of type :class:`int`.
		:raises ValueError:        If parameter ``count`` is negative.
		:raises ValueError:        If parameter ``throw`` is ``None``.
		:raises TypeError:         If parameter ``throw`` isn't of type :class:`bool`.
		:raises ValueError:        If parameter ``fallthrough`` is ``None``.
		:raises TypeError:         If parameter ``fallthrough`` isn't of type :class:`bool`.
		:raises TypeError:         If parameter ``sourceBlockID`` isn't of type :class:`int`.
		:raises ValueError:        If parameter ``sourceBlockID`` is negative.
		:raises TypeError:         If parameter ``destinationBlockID`` isn't of type :class:`int`.
		:raises ValueError:        If parameter ``destinationBlockID`` is negative.
		"""
		if count is None:
			raise ValueError(f"Parameter 'count' is None.")
		elif not isinstance(count, int):
			ex = TypeError(f"Parameter 'count' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(count)}'.")
			raise ex
		elif count < 0:
			ex = ValueError(f"Parameter 'count' is negative.")
			ex.add_note(f"Got value '{count}'.")
			raise ex

		if throw is None:
			raise ValueError(f"Parameter 'throw' is None.")
		elif not isinstance(throw, bool):
			ex = TypeError(f"Parameter 'throw' is not of type 'bool'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(throw)}'.")
			raise ex

		if fallthrough is None:
			raise ValueError(f"Parameter 'fallthrough' is None.")
		elif not isinstance(fallthrough, bool):
			ex = TypeError(f"Parameter 'fallthrough' is not of type 'bool'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(fallthrough)}'.")
			raise ex

		if sourceBlockID is not None:
			if not isinstance(sourceBlockID, int):
				ex = TypeError(f"Parameter 'sourceBlockID' is not of type 'int'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(sourceBlockID)}'.")
				raise ex
			elif sourceBlockID < 0:
				ex = ValueError(f"Parameter 'sourceBlockID' is negative.")
				ex.add_note(f"Got value '{sourceBlockID}'.")
				raise ex

		if destinationBlockID is not None:
			if not isinstance(destinationBlockID, int):
				ex = TypeError(f"Parameter 'destinationBlockID' is not of type 'int'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(destinationBlockID)}'.")
				raise ex
			elif destinationBlockID < 0:
				ex = ValueError(f"Parameter 'destinationBlockID' is negative.")
				ex.add_note(f"Got value '{destinationBlockID}'.")
				raise ex

		self._count =              count
		self._throw =              throw
		self._fallthrough =        fallthrough
		self._sourceBlockID =      sourceBlockID
		self._destinationBlockID = destinationBlockID

	@classmethod
	def Parse(cls, record: dict[str, Any]) -> Self:
		"""
		Parse a branch from its JSON object.

		:param record: The JSON object of the branch.
		:returns:      The branch.
		"""
		return cls(
			record["count"],
			record["throw"],
			record["fallthrough"],
			record.get("source_block_id"),
			record.get("destination_block_id")
		)

	@readonly
	def Count(self) -> int:
		"""
		Read-only property to access the number of times the branch was taken (:attr:`_count`).

		:returns: The count.
		"""
		return self._count

	@readonly
	def Throw(self) -> bool:
		"""
		Read-only property to access whether the branch is taken by an exception (:attr:`_throw`).

		:returns: ``True``, if the branch is exceptional.
		"""
		return self._throw

	@readonly
	def Fallthrough(self) -> bool:
		"""
		Read-only property to access whether the branch falls through (:attr:`_fallthrough`).

		:returns: ``True``, if the branch falls through.
		"""
		return self._fallthrough

	@readonly
	def SourceBlockID(self) -> Nullable[int]:
		"""
		Read-only property to access the ID of the basic block the branch starts at (:attr:`_sourceBlockID`).

		:returns: The block's ID, unique within its function; ``None`` in format 1.
		"""
		return self._sourceBlockID

	@readonly
	def DestinationBlockID(self) -> Nullable[int]:
		"""
		Read-only property to access the ID of the basic block the branch leads to (:attr:`_destinationBlockID`).

		:returns: The block's ID, unique within its function; ``None`` in format 1.
		"""
		return self._destinationBlockID


@export
class Call(metaclass=ExtendedType, slots=True):
	"""
	A ``call`` of a line - in format 2 -: from a basic block to the block continuing after the return.
	"""

	_sourceBlockID:      int  #: ID of the basic block the call is in.
	_destinationBlockID: int  #: ID of the basic block continuing after the return.
	_returned:           int  #: Number of times the call returned.

	def __init__(self, sourceBlockID: int, destinationBlockID: int, returned: int) -> None:
		"""
		Initialize the call.

		:param sourceBlockID:      ID of the basic block the call is in.
		:param destinationBlockID: ID of the basic block continuing after the return.
		:param returned:           Number of times the call returned.
		:raises ValueError:        If parameter ``sourceBlockID`` is ``None``.
		:raises TypeError:         If parameter ``sourceBlockID`` isn't of type :class:`int`.
		:raises ValueError:        If parameter ``sourceBlockID`` is negative.
		:raises ValueError:        If parameter ``destinationBlockID`` is ``None``.
		:raises TypeError:         If parameter ``destinationBlockID`` isn't of type :class:`int`.
		:raises ValueError:        If parameter ``destinationBlockID`` is negative.
		:raises ValueError:        If parameter ``returned`` is ``None``.
		:raises TypeError:         If parameter ``returned`` isn't of type :class:`int`.
		:raises ValueError:        If parameter ``returned`` is negative.
		"""
		if sourceBlockID is None:
			raise ValueError(f"Parameter 'sourceBlockID' is None.")
		elif not isinstance(sourceBlockID, int):
			ex = TypeError(f"Parameter 'sourceBlockID' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(sourceBlockID)}'.")
			raise ex
		elif sourceBlockID < 0:
			ex = ValueError(f"Parameter 'sourceBlockID' is negative.")
			ex.add_note(f"Got value '{sourceBlockID}'.")
			raise ex

		if destinationBlockID is None:
			raise ValueError(f"Parameter 'destinationBlockID' is None.")
		elif not isinstance(destinationBlockID, int):
			ex = TypeError(f"Parameter 'destinationBlockID' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(destinationBlockID)}'.")
			raise ex
		elif destinationBlockID < 0:
			ex = ValueError(f"Parameter 'destinationBlockID' is negative.")
			ex.add_note(f"Got value '{destinationBlockID}'.")
			raise ex

		if returned is None:
			raise ValueError(f"Parameter 'returned' is None.")
		elif not isinstance(returned, int):
			ex = TypeError(f"Parameter 'returned' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(returned)}'.")
			raise ex
		elif returned < 0:
			ex = ValueError(f"Parameter 'returned' is negative.")
			ex.add_note(f"Got value '{returned}'.")
			raise ex

		self._sourceBlockID =      sourceBlockID
		self._destinationBlockID = destinationBlockID
		self._returned =           returned

	@classmethod
	def Parse(cls, record: dict[str, Any]) -> Self:
		"""
		Parse a call from its JSON object.

		:param record: The JSON object of the call.
		:returns:      The call.
		"""
		return cls(record["source_block_id"], record["destination_block_id"], record["returned"])

	@readonly
	def SourceBlockID(self) -> int:
		"""
		Read-only property to access the ID of the basic block the call is in (:attr:`_sourceBlockID`).

		:returns: The block's ID, unique within its function.
		"""
		return self._sourceBlockID

	@readonly
	def DestinationBlockID(self) -> int:
		"""
		Read-only property to access the ID of the basic block continuing after the return (:attr:`_destinationBlockID`).

		:returns: The block's ID, unique within its function.
		"""
		return self._destinationBlockID

	@readonly
	def Returned(self) -> int:
		"""
		Read-only property to access the number of times the call returned (:attr:`_returned`).

		:returns: The count; how often the call was made is the line's count.
		"""
		return self._returned


@export
class Condition(metaclass=ExtendedType, slots=True):
	"""
	A ``condition`` of a line - in format 2, with ``gcc -fcondition-coverage`` -: the condition outcomes of a boolean
	expression (MC/DC).
	"""

	_count:           int        #: Number of condition outcomes: twice the number of terms.
	_covered:         int        #: Number of covered condition outcomes.
	_notCoveredTrue:  list[int]  #: The terms, by index, never seen as true.
	_notCoveredFalse: list[int]  #: The terms, by index, never seen as false.

	def __init__(
		self,
		count:           int,
		covered:         int,
		notCoveredTrue:  Nullable[Iterable[int]] = None,
		notCoveredFalse: Nullable[Iterable[int]] = None
	) -> None:
		"""
		Initialize the condition.

		:param count:           Number of condition outcomes: twice the number of terms.
		:param covered:         Number of covered condition outcomes.
		:param notCoveredTrue:  Optional, the terms, by index, never seen as true. Default: none.
		:param notCoveredFalse: Optional, the terms, by index, never seen as false. Default: none.
		:raises ValueError:     If parameter ``count`` is ``None``.
		:raises TypeError:      If parameter ``count`` isn't of type :class:`int`.
		:raises ValueError:     If parameter ``count`` is negative.
		:raises ValueError:     If parameter ``covered`` is ``None``.
		:raises TypeError:      If parameter ``covered`` isn't of type :class:`int`.
		:raises ValueError:     If parameter ``covered`` is negative.
		:raises TypeError:      If parameter ``notCoveredTrue`` isn't iterable.
		:raises TypeError:      If parameter ``notCoveredTrue`` contains an element not of type :class:`int`.
		:raises TypeError:      If parameter ``notCoveredFalse`` isn't iterable.
		:raises TypeError:      If parameter ``notCoveredFalse`` contains an element not of type :class:`int`.
		"""
		if count is None:
			raise ValueError(f"Parameter 'count' is None.")
		elif not isinstance(count, int):
			ex = TypeError(f"Parameter 'count' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(count)}'.")
			raise ex
		elif count < 0:
			ex = ValueError(f"Parameter 'count' is negative.")
			ex.add_note(f"Got value '{count}'.")
			raise ex

		if covered is None:
			raise ValueError(f"Parameter 'covered' is None.")
		elif not isinstance(covered, int):
			ex = TypeError(f"Parameter 'covered' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(covered)}'.")
			raise ex
		elif covered < 0:
			ex = ValueError(f"Parameter 'covered' is negative.")
			ex.add_note(f"Got value '{covered}'.")
			raise ex

		self._count =           count
		self._covered =         covered
		self._notCoveredTrue =  []
		self._notCoveredFalse = []

		if notCoveredTrue is not None:
			if not isinstance(notCoveredTrue, Iterable):
				ex = TypeError(f"Parameter 'notCoveredTrue' is not iterable.")
				ex.add_note(f"Got type '{getFullyQualifiedName(notCoveredTrue)}'.")
				raise ex

			for term in notCoveredTrue:
				if not isinstance(term, int):
					ex = TypeError(f"Parameter 'notCoveredTrue' contains an element not of type 'int'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(term)}'.")
					raise ex

				self._notCoveredTrue.append(term)

		if notCoveredFalse is not None:
			if not isinstance(notCoveredFalse, Iterable):
				ex = TypeError(f"Parameter 'notCoveredFalse' is not iterable.")
				ex.add_note(f"Got type '{getFullyQualifiedName(notCoveredFalse)}'.")
				raise ex

			for term in notCoveredFalse:
				if not isinstance(term, int):
					ex = TypeError(f"Parameter 'notCoveredFalse' contains an element not of type 'int'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(term)}'.")
					raise ex

				self._notCoveredFalse.append(term)

	@classmethod
	def Parse(cls, record: dict[str, Any]) -> Self:
		"""
		Parse a condition from its JSON object.

		:param record: The JSON object of the condition.
		:returns:      The condition.
		"""
		return cls(record["count"], record["covered"], record["not_covered_true"], record["not_covered_false"])

	@readonly
	def Count(self) -> int:
		"""
		Read-only property to access the number of condition outcomes (:attr:`_count`).

		:returns: The number of outcomes: twice the number of terms.
		"""
		return self._count

	@readonly
	def Covered(self) -> int:
		"""
		Read-only property to access the number of covered condition outcomes (:attr:`_covered`).

		:returns: The number of covered outcomes.
		"""
		return self._covered

	@readonly
	def NotCoveredTrue(self) -> list[int]:
		"""
		Read-only property to access the terms never seen as true (:attr:`_notCoveredTrue`).

		:returns: The terms' indices.
		"""
		return self._notCoveredTrue

	@readonly
	def NotCoveredFalse(self) -> list[int]:
		"""
		Read-only property to access the terms never seen as false (:attr:`_notCoveredFalse`).

		:returns: The terms' indices.
		"""
		return self._notCoveredFalse
