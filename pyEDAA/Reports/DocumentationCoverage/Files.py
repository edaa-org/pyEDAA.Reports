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
The physical hierarchy of the documentation coverage model: the report, its directories and source files.

A file counts the items declared in it; a directory sums its directories and files. The items themselves are in the
logical hierarchy (:mod:`~pyEDAA.Reports.DocumentationCoverage.Items`), which the report holds too.
"""
from __future__                                   import annotations

from datetime                                     import timedelta
from pathlib                                      import Path
from typing                                       import TYPE_CHECKING, ClassVar, Generator, Optional as Nullable

from pyTooling.Common                             import getFullyQualifiedName
from pyTooling.Decorators                         import export, readonly

from pyEDAA.Reports.DocumentationCoverage         import Base, DocCoverageError

if TYPE_CHECKING:  # pragma: no cover
	from pyEDAA.Reports.DocumentationCoverage.Items import Item


# A class with a property named like a class - ``Path`` - can't name that class in the annotation of a field: the class
# body's namespace, where annotations are evaluated, binds the name to the property.
_Path = Path


@export
class BaseWithPath(Base):
	"""
	Base-class of the physical hierarchy - directories and source files -: a name and a path below the report.

	Its parent is the :class:`Directory` containing it.
	"""

	_name: _Path  #: Name of the directory or file: a path of one component.

	def __init__(self, name: Path, *, parent: Nullable[Directory]) -> None:
		"""
		Initializes the parent, the name and the counters.

		:param name:        Name of the directory or file: a path of one component.
		:param parent:      The directory containing this one, or ``None``.
		:raises TypeError:  If parameter ``parent`` isn't of type :class:`Directory`.
		:raises ValueError: If parameter ``name`` is ``None``.
		:raises TypeError:  If parameter ``name`` isn't of type :class:`~pathlib.Path`.
		:raises ValueError: If parameter ``name`` is empty or ``.``.
		:raises ValueError: If parameter ``name`` has more than one component.
		"""
		super().__init__(parent=parent)

		if name is None:
			raise ValueError(f"Parameter 'name' is None.")
		elif not isinstance(name, Path):
			ex = TypeError(f"Parameter 'name' is not of type 'Path'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(name)}'.")
			raise ex
		elif name.name == "":
			ex = ValueError(f"Parameter 'name' is empty.")
			ex.add_note(f"Got path '{name}'.")
			raise ex
		elif len(name.parts) > 1:
			ex = ValueError(f"Parameter 'name' has more than one component.")
			ex.add_note(f"Got path '{name.as_posix()}'.")
			raise ex

		self._name = name

	@readonly
	def Name(self) -> Path:
		"""
		Read-only property to access the name of the directory or file (:attr:`_name`).

		:returns: The name: a path of one component.
		"""
		return self._name

	@readonly
	def Path(self) -> Path:
		"""
		Read-only property to return the path below the report: the names of the parent directories and the own name.

		A file ``Shapes.py`` in a directory ``myPackage`` has the path ``myPackage/Shapes.py``.

		:returns: The path; the name, if there is no parent.
		"""
		if self._parent is None:
			return self._name

		return self._parent.Path / self._name


@export
class Directory(BaseWithPath):
	"""
	A directory: its directories and source files, and their summed counters.
	"""

	_PARENT_TYPE: ClassVar[tuple[type, ...]]  #: A directory is in a directory; assigned below the class.

	_directories: dict[_Path, Directory]  #: The directories in this directory, by name.
	_files:       dict[_Path, File]       #: The source files in this directory, by name.

	def __init__(self, name: Path, *, parent: Nullable[Directory] = None) -> None:
		"""
		Initializes a directory, and adds it to its parent directory.

		:param name:              Name of the directory: a path of one component.
		:param parent:            Optional, the directory containing this one. Default: ``None``.
		:raises TypeError:        If parameter ``parent`` isn't of type :class:`Directory`.
		:raises ValueError:       If parameter ``name`` is ``None``.
		:raises TypeError:        If parameter ``name`` isn't of type :class:`~pathlib.Path`.
		:raises ValueError:       If parameter ``name`` is empty or ``.``.
		:raises ValueError:       If parameter ``name`` has more than one component.
		:raises DocCoverageError: If the parent directory already contains a file or directory of this name.
		"""
		super().__init__(name, parent=parent)

		self._directories = {}
		self._files =       {}

		if parent is not None:
			parent._AddElement(self)

	def _AddElement(self, element: Directory | File) -> None:
		"""
		Add a directory or file, which names this directory as its parent.

		:param element:           The directory or file.
		:raises DocCoverageError: If this directory already contains a file or directory of this name.
		"""
		if element._name in self._directories or element._name in self._files:
			raise DocCoverageError(f"Directory '{self.Path.as_posix()}' already contains '{element._name.as_posix()}'.")

		if isinstance(element, Directory):
			self._directories[element._name] = element
		else:
			self._files[element._name] = element

	def IterateElements(self) -> Generator[Base, None, None]:
		"""
		Iterate the directories and files in this directory, each followed by the elements below it.

		:returns: A generator of the elements below this directory.
		"""
		for child in (*self._directories.values(), *self._files.values()):
			yield child
			yield from child.IterateElements()

	@readonly
	def Directories(self) -> dict[Path, Directory]:
		"""
		Read-only property to access the directories in this directory (:attr:`_directories`).

		:returns: The directories, by name.
		"""
		return self._directories

	@readonly
	def Files(self) -> dict[Path, File]:
		"""
		Read-only property to access the source files in this directory (:attr:`_files`).

		:returns: The files, by name.
		"""
		return self._files

	@readonly
	def FileCount(self) -> int:
		"""
		Read-only property to return the number of source files in this directory and below.

		:returns: The number of files.
		"""
		return len(self._files) + sum(directory.FileCount for directory in self._directories.values())

	def GetOrAddFile(self, path: Path) -> File:
		"""
		Return the source file at a path below this directory, adding it and the directories on its way, if missing.

		:param path:              The file's path relative to this directory, e.g. ``myPackage/Shapes.py``.
		:returns:                 The file.
		:raises ValueError:       If parameter ``path`` is ``None``.
		:raises TypeError:        If parameter ``path`` isn't of type :class:`~pathlib.Path`.
		:raises ValueError:       If parameter ``path`` names no file.
		:raises DocCoverageError: If a part of the path is a file instead of a directory, or the file's name is a
		                          directory's.
		"""
		if path is None:
			raise ValueError(f"Parameter 'path' is None.")
		elif not isinstance(path, Path):
			ex = TypeError(f"Parameter 'path' is not of type 'Path'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(path)}'.")
			raise ex

		parts = [Path(part) for part in path.parts if part not in ("", ".", path.anchor)]
		if len(parts) == 0:
			ex = ValueError(f"Parameter 'path' names no file.")
			ex.add_note(f"Got path '{path}'.")
			raise ex

		directory = self
		for part in parts[:-1]:
			if part in directory._files:
				raise DocCoverageError(f"'{(directory.Path / part).as_posix()}' is a file, not a directory.")
			elif (subdirectory := directory._directories.get(part)) is None:
				subdirectory = Directory(part, parent=directory)
			directory = subdirectory

		if (file := directory._files.get(parts[-1])) is None:
			file = File(parts[-1], parent=directory)

		return file

	def IterateFiles(self) -> Generator[File, None, None]:
		"""
		Iterate the source files in this directory and below, sorted by name, a directory's files before its directories'.

		:returns: A generator of the files.
		"""
		for name in sorted(self._files):
			yield self._files[name]

		for name in sorted(self._directories):
			yield from self._directories[name].IterateFiles()

	def Aggregate(self) -> None:
		"""
		Aggregate the directories and files in this directory, then sum their counters.
		"""
		self._ResetCounters()
		for child in (*self._directories.values(), *self._files.values()):
			child.Aggregate()
			self._AddCounters(child)

	def __repr__(self) -> str:
		"""
		Return a representation of the directory for debugging.

		A directory ``myPackage`` of 3 files reads ``<Directory myPackage: 3 files, 75.0%>``.

		:returns: The directory's path, its number of files and its documentation coverage.
		"""
		return f"<Directory {self.Path.as_posix()}: {self.FileCount} files, {self._counters.Coverage:.1%}>"


Directory._PARENT_TYPE = (Directory, )


@export
class DocumentationReport(Directory):
	"""
	The report of a documentation coverage analysis: the directory the source files' paths are relative to, and the
	top-level items of the logical hierarchy.

	It is its own root. Its counters count every item of the logical hierarchy; its directories and files count only
	the items declared in a source file.
	"""

	_items:            list[Item]           #: The top-level items, in the order they were added.
	_analysisDuration: Nullable[timedelta]  #: Duration of the analysis, which produced the report, if measured.

	def __init__(self, name: Path) -> None:
		"""
		Initializes the report of a documentation coverage analysis.

		:param name:        Name of the report: a path of one component, e.g. the analyzed package's name.
		:raises ValueError: If parameter ``name`` is ``None``.
		:raises TypeError:  If parameter ``name`` isn't of type :class:`~pathlib.Path`.
		:raises ValueError: If parameter ``name`` is empty or ``.``.
		:raises ValueError: If parameter ``name`` has more than one component.
		"""
		super().__init__(name)

		self._root =             self
		self._items =            []
		self._analysisDuration = None

	@Base.Parent.setter
	def Parent(self, parent: None) -> None:
		ex = TypeError(f"A '{getFullyQualifiedName(self)}' has no parent.")
		ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
		raise ex

	def _AddElement(self, element: Directory | File | Item) -> None:
		"""
		Add a top-level item, a directory or a file, which names the report as its parent.

		:param element:           The item, directory or file.
		:raises DocCoverageError: If the report already contains a file or directory of this name.
		"""
		if isinstance(element, BaseWithPath):
			super()._AddElement(element)
		else:
			self._items.append(element)

	def IterateElements(self) -> Generator[Base, None, None]:
		"""
		Iterate the elements of the physical hierarchy, then those of the logical hierarchy.

		:returns: A generator of every element below the report.
		"""
		yield from super().IterateElements()
		for item in self._items:
			yield item
			yield from item.IterateElements()

	@readonly
	def Path(self) -> Path:
		"""
		Read-only property to return the path below the report, which is the report's own: ``.``.

		So the paths of the directories and files below are relative to the report, without its name.

		:returns: ``.``
		"""
		return Path(".")

	@readonly
	def Items(self) -> list[Item]:
		"""
		Read-only property to access the top-level items of the logical hierarchy (:attr:`_items`).

		:returns: The items, in the order they were added.
		"""
		return self._items

	@readonly
	def AnalysisDuration(self) -> Nullable[timedelta]:
		"""
		Read-only property to access the duration of the analysis, which produced the report (:attr:`_analysisDuration`).

		A reader measures it; a report built otherwise has none.

		:returns: The duration, or ``None`` if it wasn't measured.
		"""
		return self._analysisDuration

	def Aggregate(self) -> None:
		"""
		Aggregate the physical hierarchy - directories and files -, then the items of the logical hierarchy, which the
		report's counters sum.
		"""
		super().Aggregate()

		self._ResetCounters()
		for item in self._items:
			item.Aggregate()
			self._AddCounters(item)


@export
class File(BaseWithPath):
	"""
	A source file: the items declared in it, and their counters.

	The items are those of the logical hierarchy naming this file; the file counts each item's own state, not the items
	it contains, which name their file themselves.
	"""

	_PARENT_TYPE: ClassVar[tuple[type, ...]] = (Directory, )  #: A file is in a directory.

	_items: list[Item]  #: The items declared in this file, in the order they were added.

	def __init__(self, name: Path, *, parent: Nullable[Directory] = None) -> None:
		"""
		Initializes a source file, and adds it to its directory.

		:param name:              Name of the file: a path of one component.
		:param parent:            Optional, the directory containing the file. Default: ``None``.
		:raises TypeError:        If parameter ``parent`` isn't of type :class:`Directory`.
		:raises ValueError:       If parameter ``name`` is ``None``.
		:raises TypeError:        If parameter ``name`` isn't of type :class:`~pathlib.Path`.
		:raises ValueError:       If parameter ``name`` is empty or ``.``.
		:raises ValueError:       If parameter ``name`` has more than one component.
		:raises DocCoverageError: If the directory already contains a file or directory of this name.
		"""
		super().__init__(name, parent=parent)

		self._items = []

		if parent is not None:
			parent._AddElement(self)

	def IterateElements(self) -> Generator[Base, None, None]:
		"""
		Iterate the elements below this file, which are none: its items belong to the logical hierarchy.

		:returns: An empty generator.
		"""
		yield from ()

	@readonly
	def Items(self) -> list[Item]:
		"""
		Read-only property to access the items declared in this file (:attr:`_items`).

		:returns: The items, in the order they were added.
		"""
		return self._items

	def Aggregate(self) -> None:
		"""
		Count the own coverage state of each item declared in this file.
		"""
		self._ResetCounters()
		for item in self._items:
			self._CountItem(item)

	def __repr__(self) -> str:
		"""
		Return a representation of the file for debugging.

		A file ``Shapes.py`` of 4 items reads ``<File myPackage/Shapes.py: 4 items, 75.0%>``.

		:returns: The file's path, its number of items and its documentation coverage.
		"""
		return f"<File {self.Path.as_posix()}: {len(self._items)} items, {self._counters.Coverage:.1%}>"
