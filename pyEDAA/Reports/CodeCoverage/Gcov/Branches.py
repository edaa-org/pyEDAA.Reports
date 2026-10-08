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

from typing                import Any, Optional as Nullable

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

	def __init__(self, record: dict[str, Any]) -> None:
		"""
		Initialize the branch from its JSON object.

		:param record: The JSON object of the branch.
		"""
		self._count =              record["count"]
		self._throw =              record["throw"]
		self._fallthrough =        record["fallthrough"]
		self._sourceBlockID =      record.get("source_block_id")
		self._destinationBlockID = record.get("destination_block_id")

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

	def __init__(self, record: dict[str, Any]) -> None:
		"""
		Initialize the call from its JSON object.

		:param record: The JSON object of the call.
		"""
		self._sourceBlockID =      record["source_block_id"]
		self._destinationBlockID = record["destination_block_id"]
		self._returned =           record["returned"]

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

	def __init__(self, record: dict[str, Any]) -> None:
		"""
		Initialize the condition from its JSON object.

		:param record: The JSON object of the condition.
		"""
		self._count =           record["count"]
		self._covered =         record["covered"]
		self._notCoveredTrue =  record["not_covered_true"]
		self._notCoveredFalse = record["not_covered_false"]

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
