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
The logical hierarchy of the documentation coverage model: the documentable items of a language.

An item - a package, a class, a method, a field, a VHDL entity, ... - has a kind, a coverage state, and contains other
items. It names the source file it is declared in and its first and last line, where the reader knows them.
"""
from __future__                                 import annotations

from typing                                     import ClassVar, Generator, Iterator, Optional as Nullable

from pyTooling.Common                           import getFullyQualifiedName
from pyTooling.Decorators                       import export, readonly

from pyEDAA.Reports.DocumentationCoverage       import Base, CoverageState, ItemCategory, ItemKind
from pyEDAA.Reports.DocumentationCoverage.Files import CoverageSummary, File


# A class with a property named like a class - ``File`` - can't name that class in the annotation of a field: the class
# body's namespace, where annotations are evaluated, binds the name to the property.
_File = File


@export
class Item(Base):
	"""
	A documentable item of a language, its coverage state, and the items it contains.

	Its parent is the :class:`Item` containing it, or the analysis'
	:class:`~pyEDAA.Reports.DocumentationCoverage.Files.CoverageSummary` for a top-level item. Items of one parent may
	share a name, e.g. a property's getter and setter.

	A container's own documentation - a module's or a class' doc-string - is the container's own coverage state; the
	items it contains have states of their own. So an item's counters count the item itself and every item below it.
	"""

	_PARENT_TYPE: ClassVar[tuple[type, ...]]  #: An item is in an item or the analysis' root; assigned below the class.

	_name:      str              #: Name of the item.
	_kind:      ItemKind         #: The language construct the item is.
	_status:    CoverageState    #: The item's own coverage state.
	_file:      Nullable[_File]  #: The source file the item is declared in, if the reader knows it.
	_startLine: Nullable[int]    #: The item's first line, if the reader knows it.
	_endLine:   Nullable[int]    #: The item's last line, if the reader knows it.
	_items:     list[Item]       #: The items this one contains, in the order they were added.

	def __init__(
		self,
		name: str,
		kind: ItemKind,
		status: CoverageState,
		*,
		file: Nullable[File] = None,
		startLine: Nullable[int] = None,
		endLine: Nullable[int] = None,
		parent: Nullable[Item | CoverageSummary] = None
	) -> None:
		"""
		Initializes an item, and adds it to its file and to the item or analysis containing it.

		:param name:        Name of the item.
		:param kind:        The language construct the item is.
		:param status:      The item's own coverage state.
		:param file:        Optional, the source file the item is declared in. Default: ``None``.
		:param startLine:   Optional, the item's first line. Default: ``None``.
		:param endLine:     Optional, the item's last line. Default: ``None``.
		:param parent:      Optional, the item or analysis containing this item. Default: ``None``.
		:raises TypeError:  If parameter ``parent`` isn't of type :class:`Item` or
		                    :class:`~pyEDAA.Reports.DocumentationCoverage.Files.CoverageSummary`.
		:raises ValueError: If parameter ``name`` is ``None``.
		:raises TypeError:  If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError: If parameter ``name`` is empty.
		:raises ValueError: If parameter ``kind`` is ``None``.
		:raises TypeError:  If parameter ``kind`` isn't of type :class:`~pyEDAA.Reports.DocumentationCoverage.ItemKind`.
		:raises ValueError: If parameter ``status`` is ``None``.
		:raises TypeError:  If parameter ``status`` isn't of type
		                    :class:`~pyEDAA.Reports.DocumentationCoverage.CoverageState`.
		:raises ValueError: If parameter ``status`` is ``CoverageState.Unknown``.
		:raises TypeError:  If parameter ``file`` isn't of type :class:`~pyEDAA.Reports.DocumentationCoverage.Files.File`.
		:raises TypeError:  If parameter ``startLine`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``startLine`` is less than 1.
		:raises TypeError:  If parameter ``endLine`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``endLine`` is before parameter ``startLine``, or less than 1.
		"""
		super().__init__(parent=parent)

		if name is None:
			raise ValueError(f"Parameter 'name' is None.")
		elif not isinstance(name, str):
			ex = TypeError(f"Parameter 'name' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(name)}'.")
			raise ex
		elif name == "":
			raise ValueError(f"Parameter 'name' is empty.")

		if kind is None:
			raise ValueError(f"Parameter 'kind' is None.")
		elif not isinstance(kind, ItemKind):
			ex = TypeError(f"Parameter 'kind' is not of type 'ItemKind'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(kind)}'.")
			raise ex

		if status is None:
			raise ValueError(f"Parameter 'status' is None.")
		elif not isinstance(status, CoverageState):
			ex = TypeError(f"Parameter 'status' is not of type 'CoverageState'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(status)}'.")
			raise ex
		elif status is CoverageState.Unknown:
			raise ValueError(f"Parameter 'status' is 'Unknown'.")

		if file is not None and not isinstance(file, File):
			ex = TypeError(f"Parameter 'file' is not of type 'File'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(file)}'.")
			raise ex

		if startLine is not None:
			if not isinstance(startLine, int):
				ex = TypeError(f"Parameter 'startLine' is not of type 'int'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(startLine)}'.")
				raise ex
			elif startLine < 1:
				ex = ValueError(f"Parameter 'startLine' is less than 1.")
				ex.add_note(f"Got value '{startLine}'.")
				raise ex

		if endLine is not None:
			if not isinstance(endLine, int):
				ex = TypeError(f"Parameter 'endLine' is not of type 'int'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(endLine)}'.")
				raise ex
			elif endLine < (1 if startLine is None else startLine):
				ex = ValueError(f"Parameter 'endLine' is before parameter 'startLine', or less than 1.")
				ex.add_note(f"Got lines {startLine} to {endLine}.")
				raise ex

		self._name =      name
		self._kind =      kind
		self._status =    status
		self._file =      file
		self._startLine = startLine
		self._endLine =   endLine
		self._items =     []

		if parent is not None:
			parent._AddElement(self)

		if file is not None:
			file._items.append(self)

	def _AddElement(self, item: Item) -> None:
		"""
		Add an item, which names this item as its parent.

		:param item: The item.
		"""
		self._items.append(item)

	def IterateElements(self) -> Generator[Base, None, None]:
		"""
		Iterate the items this item contains, each followed by the items below it.

		:returns: A generator of the items below this one.
		"""
		for item in self._items:
			yield item
			yield from item.IterateElements()

	@readonly
	def Name(self) -> str:
		"""
		Read-only property to access the item's name (:attr:`_name`).

		:returns: The name.
		"""
		return self._name

	@readonly
	def Kind(self) -> ItemKind:
		"""
		Read-only property to access the language construct the item is (:attr:`_kind`).

		:returns: The item's kind.
		"""
		return self._kind

	@readonly
	def Category(self) -> ItemCategory:
		"""
		Read-only property to return the category of the item's kind.

		:returns: The item's category.
		"""
		return self._kind.Category

	@readonly
	def Status(self) -> CoverageState:
		"""
		Read-only property to access the item's own coverage state (:attr:`_status`).

		:returns: The coverage state.
		"""
		return self._status

	@readonly
	def File(self) -> Nullable[File]:
		"""
		Read-only property to access the source file the item is declared in (:attr:`_file`).

		:returns: The file, or ``None`` if the reader doesn't know it.
		"""
		return self._file

	@readonly
	def StartLine(self) -> Nullable[int]:
		"""
		Read-only property to access the item's first line (:attr:`_startLine`).

		:returns: The line number, or ``None`` if the reader doesn't know it.
		"""
		return self._startLine

	@readonly
	def EndLine(self) -> Nullable[int]:
		"""
		Read-only property to access the item's last line (:attr:`_endLine`).

		:returns: The line number, or ``None`` if the reader doesn't know it.
		"""
		return self._endLine

	@readonly
	def Items(self) -> list[Item]:
		"""
		Read-only property to access the items this one contains (:attr:`_items`).

		:returns: The items, in the order they were added.
		"""
		return self._items

	@readonly
	def QualifiedName(self) -> str:
		"""
		Read-only property to return the names of the items from the top down to this one, joined by ``.``.

		A method ``Area`` of a class ``Circle`` in a module ``myPackage.Shapes`` has the qualified name
		``myPackage.Shapes.Circle.Area``.

		:returns: The qualified name.
		"""
		if isinstance(self._parent, Item):
			return f"{self._parent.QualifiedName}.{self._name}"

		return self._name

	def __len__(self) -> int:
		"""
		Return the number of items this one contains.

		:returns: The number of items.
		"""
		return len(self._items)

	def __iter__(self) -> Iterator[Item]:
		"""
		Iterate the items this one contains.

		:returns: An iterator of the items, in the order they were added.
		"""
		return iter(self._items)

	def __contains__(self, name: str) -> bool:
		"""
		Return whether this item contains an item of a name.

		:param name: The name.
		:returns:    ``True``, if an item of this name is contained.
		"""
		return any(item._name == name for item in self._items)

	def __getitem__(self, name: str) -> Item:
		"""
		Return the contained item of a name; the first one, if several share it.

		A property's getter is added before its setter, so it is the one returned.

		:param name:      The name.
		:returns:         The item.
		:raises KeyError: If no item of this name is contained.
		"""
		for item in self._items:
			if item._name == name:
				return item

		raise KeyError(f"Item '{self.QualifiedName}' contains no item '{name}'.")

	def Aggregate(self) -> None:
		"""
		Aggregate the items this one contains, then count this item's own coverage state and add their counters.
		"""
		self._ResetCounters()
		self._CountItem(self)
		for item in self._items:
			item.Aggregate()
			self._AddCounters(item)

	def __repr__(self) -> str:
		"""
		Return a representation of the item for debugging.

		A method ``Area`` of class ``Circle`` in module ``Shapes`` reads ``<Item method Shapes.Circle.Area: 100.0%>``.

		:returns: The item's kind, qualified name and documentation coverage.
		"""
		return f"<Item {self._kind} {self.QualifiedName}: {self._counters.Coverage:.1%}>"


Item._PARENT_TYPE = (Item, CoverageSummary)
