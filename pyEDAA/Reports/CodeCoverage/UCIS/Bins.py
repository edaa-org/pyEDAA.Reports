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
The bins of the UCIS XML interchange format: a coverage item's count - how often it was covered -, the tests, which
covered it, and its goal.
"""
from __future__                                import annotations

from typing                                    import Iterable, Optional as Nullable, Self

from lxml.etree                                import _Element
from pyTooling.Common                          import getFullyQualifiedName
from pyTooling.Decorators                      import export, readonly
from pyTooling.MetaClasses                     import ExtendedType

from pyEDAA.Reports.CodeCoverage.UCIS.Elements import Base, ObjectAttributesMixin, UserAttribute


@export
class BinContents(metaclass=ExtendedType, slots=True):
	"""
	A ``<contents>`` of a bin: how often its coverage item was covered, the tests, which covered it, and the components
	of its unique ID.

	It is a value, as a path is: it names no parent.
	"""

	_coverageCount:  int            #: How often the coverage item was covered.
	_historyNodeIDs: list[int]      #: The IDs of the history nodes, which covered the coverage item.
	_nameComponent:  Nullable[str]  #: The name component of the coverage item's unique ID.
	_typeComponent:  Nullable[str]  #: The type component of the coverage item's unique ID.

	def __init__(
		self,
		coverageCount: int,
		historyNodeIDs: Nullable[Iterable[int]] = None,
		nameComponent: Nullable[str] = None,
		typeComponent: Nullable[str] = None
	) -> None:
		"""
		Initialize the contents of a bin.

		:param coverageCount:  How often the coverage item was covered.
		:param historyNodeIDs: Optional, the IDs of the history nodes, which covered the coverage item. Default: ``None``.
		:param nameComponent:  Optional, the name component of the coverage item's unique ID. Default: ``None``.
		:param typeComponent:  Optional, the type component of the coverage item's unique ID, e.g. ``:5:`` for a
		                       statement. Default: ``None``.
		:raises ValueError:    If parameter ``coverageCount`` is ``None``.
		:raises TypeError:     If parameter ``coverageCount`` isn't of type :class:`int`.
		:raises ValueError:    If parameter ``coverageCount`` is negative.
		:raises TypeError:     If parameter ``historyNodeIDs`` isn't iterable.
		:raises TypeError:     If parameter ``historyNodeIDs`` contains an element not of type :class:`int`.
		:raises TypeError:     If parameter ``nameComponent`` isn't of type :class:`str`.
		:raises TypeError:     If parameter ``typeComponent`` isn't of type :class:`str`.
		"""
		if coverageCount is None:
			raise ValueError(f"Parameter 'coverageCount' is None.")
		elif not isinstance(coverageCount, int) or isinstance(coverageCount, bool):
			ex = TypeError(f"Parameter 'coverageCount' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(coverageCount)}'.")
			raise ex
		elif coverageCount < 0:
			ex = ValueError(f"Parameter 'coverageCount' is negative.")
			ex.add_note(f"Got value '{coverageCount}'.")
			raise ex

		if nameComponent is not None and not isinstance(nameComponent, str):
			ex = TypeError(f"Parameter 'nameComponent' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(nameComponent)}'.")
			raise ex

		if typeComponent is not None and not isinstance(typeComponent, str):
			ex = TypeError(f"Parameter 'typeComponent' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(typeComponent)}'.")
			raise ex

		self._coverageCount =  coverageCount
		self._historyNodeIDs = []
		self._nameComponent =  nameComponent
		self._typeComponent =  typeComponent

		if historyNodeIDs is not None:
			if not isinstance(historyNodeIDs, Iterable):
				ex = TypeError(f"Parameter 'historyNodeIDs' is not iterable.")
				ex.add_note(f"Got type '{getFullyQualifiedName(historyNodeIDs)}'.")
				raise ex

			for historyNodeID in historyNodeIDs:
				if not isinstance(historyNodeID, int) or isinstance(historyNodeID, bool):
					ex = TypeError(f"Parameter 'historyNodeIDs' contains an element not of type 'int'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(historyNodeID)}'.")
					raise ex

				self._historyNodeIDs.append(historyNodeID)

	@classmethod
	def Parse(cls, element: _Element) -> Self:
		"""
		Parse the contents of a bin from its ``<contents>`` element.

		:param element: The ``<contents>`` element.
		:returns:       The contents.
		"""
		return cls(
			int(element.attrib["coverageCount"]),
			[int(idElement.text) for idElement in element.iterfind("{*}historyNodeId")],
			element.attrib.get("nameComponent"),
			element.attrib.get("typeComponent")
		)

	@readonly
	def CoverageCount(self) -> int:
		"""
		Read-only property to access how often the coverage item was covered (:attr:`_coverageCount`).

		:returns: The count, e.g. how often a statement ran.
		"""
		return self._coverageCount

	@readonly
	def HistoryNodeIDs(self) -> list[int]:
		"""
		Read-only property to access the IDs of the history nodes, which covered the item (:attr:`_historyNodeIDs`).

		:returns: The IDs, in the order the report lists them.
		"""
		return self._historyNodeIDs

	@readonly
	def NameComponent(self) -> Nullable[str]:
		"""
		Read-only property to access the name component of the coverage item's unique ID (:attr:`_nameComponent`).

		:returns: The name component; ``None``, if the report states none.
		"""
		return self._nameComponent

	@readonly
	def TypeComponent(self) -> Nullable[str]:
		"""
		Read-only property to access the type component of the coverage item's unique ID (:attr:`_typeComponent`).

		:returns: The type component, e.g. ``:5:``; ``None``, if the report states none.
		"""
		return self._typeComponent


@export
class Bin(Base, ObjectAttributesMixin):
	"""
	A bin of a coverage item, e.g. a ``<bin>`` of a statement or a ``<branchBin>`` of a branch: its contents, its goal
	and its attributes.

	The element owning the bin takes it as a parameter and becomes its parent.
	"""

	_parent:            Nullable[Base]  #: The element owning the bin.
	_contents:          BinContents     #: How often the coverage item was covered, and by which tests.
	_coverageCountGoal: Nullable[int]   #: How often the coverage item must be covered.

	def __init__(
		self,
		contents: BinContents,
		coverageCountGoal: Nullable[int] = None,
		alias: Nullable[str] = None,
		excluded: bool = False,
		excludedReason: Nullable[str] = None,
		weight: int = 1,
		userAttributes: Nullable[Iterable[UserAttribute]] = None
	) -> None:
		"""
		Initialize the bin.

		:param contents:          How often the coverage item was covered, and by which tests.
		:param coverageCountGoal: Optional, how often the coverage item must be covered. Default: ``None``.
		:param alias:             Optional, an alias of the bin's name. Default: ``None``.
		:param excluded:          Optional, whether the bin is excluded from the coverage. Default: ``False``.
		:param excludedReason:    Optional, why the bin is excluded. Default: ``None``.
		:param weight:            Optional, weight of the bin in computing the coverage. Default: ``1``.
		:param userAttributes:    Optional, the user-defined attributes. Default: ``None``.
		:raises TypeError:        If parameter ``userAttributes`` isn't iterable.
		:raises TypeError:        If parameter ``userAttributes`` contains an element not of type
		                          :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Elements.UserAttribute`.
		:raises TypeError:        If parameter ``alias`` isn't of type :class:`str`.
		:raises ValueError:       If parameter ``excluded`` is ``None``.
		:raises TypeError:        If parameter ``excluded`` isn't of type :class:`bool`.
		:raises TypeError:        If parameter ``excludedReason`` isn't of type :class:`str`.
		:raises ValueError:       If parameter ``weight`` is ``None``.
		:raises TypeError:        If parameter ``weight`` isn't of type :class:`int`.
		:raises ValueError:       If parameter ``weight`` is negative.
		:raises ValueError:       If parameter ``contents`` is ``None``.
		:raises TypeError:        If parameter ``contents`` isn't of type :class:`BinContents`.
		:raises TypeError:        If parameter ``coverageCountGoal`` isn't of type :class:`int`.
		:raises ValueError:       If parameter ``coverageCountGoal`` is negative.
		"""
		super().__init__(userAttributes)
		ObjectAttributesMixin.__init__(self, alias, excluded, excludedReason, weight)

		if contents is None:
			raise ValueError(f"Parameter 'contents' is None.")
		elif not isinstance(contents, BinContents):
			ex = TypeError(f"Parameter 'contents' is not of type 'BinContents'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(contents)}'.")
			raise ex

		if coverageCountGoal is not None:
			if not isinstance(coverageCountGoal, int) or isinstance(coverageCountGoal, bool):
				ex = TypeError(f"Parameter 'coverageCountGoal' is not of type 'int'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(coverageCountGoal)}'.")
				raise ex
			elif coverageCountGoal < 0:
				ex = ValueError(f"Parameter 'coverageCountGoal' is negative.")
				ex.add_note(f"Got value '{coverageCountGoal}'.")
				raise ex

		self._parent =            None
		self._contents =          contents
		self._coverageCountGoal = coverageCountGoal

	@classmethod
	def Parse(cls, element: _Element) -> Self:
		"""
		Parse a bin, its contents and its user-defined attributes from its element, e.g. ``<bin>`` or ``<branchBin>``.

		:param element:            The bin's element.
		:returns:                  The bin.
		:raises CodeCoverageError: If a user-defined attribute's value isn't of the type the attribute states.
		"""
		goal = element.attrib.get("coverageCountGoal")
		return cls(
			BinContents.Parse(element.find("{*}contents")),
			None if goal is None else int(goal),
			element.attrib.get("alias"),
			cls._ParseBoolean(element.attrib.get("excluded", "false")),
			element.attrib.get("excludedReason"),
			int(element.attrib.get("weight", "1")),
			cls._ParseUserAttributes(element)
		)

	@readonly
	def Parent(self) -> Nullable[Base]:
		"""
		Read-only property to access the element owning the bin (:attr:`_parent`).

		:returns: The element, e.g. a :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Blocks.Statement`; ``None``, if the bin
		          belongs to none.
		"""
		return self._parent

	@readonly
	def Contents(self) -> BinContents:
		"""
		Read-only property to access the contents of the bin (:attr:`_contents`).

		:returns: How often the coverage item was covered, and by which tests.
		"""
		return self._contents

	@readonly
	def CoverageCountGoal(self) -> Nullable[int]:
		"""
		Read-only property to access how often the coverage item must be covered (:attr:`_coverageCountGoal`).

		:returns: The goal; ``None``, if the report states none.
		"""
		return self._coverageCountGoal
