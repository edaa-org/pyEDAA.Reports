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
# Copyright 2021-2026 Electronic Design Automation Abstraction (EDA²)                                                  #
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
Abstract data model of code coverage, the common model every report format is converted to.

The model has two hierarchies over the same lines:

* The **physical** hierarchy - :class:`CoverageSummary`, :class:`Directory`, :class:`File` - is built from the file
  paths a report names. A file holds its executable lines; every format has them.
* The **logical** hierarchy holds the language units a report names - :class:`Package`, :class:`Module`,
  :class:`SourceFile`, :class:`Class`, :class:`Function`, :class:`Method` -, each with the file and the lines it
  covers. A unit's lines are the file's :class:`Line` objects, so both hierarchies count the same lines.

A :class:`Line` and a :class:`Branch` carry a :class:`LineCoverageStatus` and - if the report says - a count: how
often the line ran, or the branch was taken. :meth:`CoverageSummary.Aggregate` computes the counters of every file,
directory and unit.

The report formats have models of their own, which convert to this one:

.. seealso::

   :mod:`pyEDAA.Reports.CodeCoverage.Cobertura`
      |rarr| The Cobertura XML format, as written e.g. by coverage.py (``coverage xml``) or gcovr (``--cobertura``).
"""
from __future__            import annotations

from collections.abc       import Iterable
from datetime              import timedelta
from enum                  import Enum
from pathlib               import Path
from typing                import ClassVar, Generator, Optional as Nullable

from pyTooling.Common      import getFullyQualifiedName
from pyTooling.Decorators  import export, readonly
from pyTooling.MetaClasses import ExtendedType, abstractmethod

from pyEDAA.Reports        import ReportException


@export
class CodeCoverageError(ReportException):
	"""Base-exception of the code coverage data model and its report formats."""


@export
class LineCoverageStatus(Enum):
	"""The coverage state of a line, a branch or a unit, as a report states it."""

	Unknown =          0  #: The report doesn't say.
	Uncovered =        1  #: The line never ran, the branch was never taken, the unit was never called.
	PartiallyCovered = 2  #: The line ran, but not all of its branches were taken.
	Covered =          3  #: The line ran, the branch was taken, the unit was called.
	Excluded =         4  #: Excluded from the measurement, e.g. by a pragma comment.


@export
class Base(metaclass=ExtendedType, slots=True):
	"""
	Base-class of every element of the code coverage model: a reference to the element containing it, and to the report's
	root.
	"""

	_PARENT_TYPE: ClassVar[tuple[type, ...]] = ()  #: The types a parent may have.

	_parent: Nullable[Base]             #: The element containing this one, or ``None``.
	_root:   Nullable[CoverageSummary]  #: The report's root, or ``None`` while the element isn't part of a report.

	def __init__(self, parent: Nullable[Base] = None) -> None:
		"""
		Initialize an element, and add it to its parent.

		The element is added to its parent last, so a class deriving from this one sets its own fields - e.g. the name
		the parent stores it by - before it calls this initializer.

		:param parent:             Optional, the element containing this one. Default: ``None``.
		:raises TypeError:         If parameter ``parent`` isn't of a type this class declares in :attr:`_PARENT_TYPE`.
		:raises CodeCoverageError: If the parent already contains an element of this name or line number.
		"""
		if parent is None:
			self._parent = None
			self._root =   None
		elif not isinstance(parent, self._PARENT_TYPE):
			typeNames = " or ".join(f"'{parentType.__name__}'" for parentType in self._PARENT_TYPE)
			ex = TypeError(f"Parameter 'parent' is not of type {typeNames}.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex
		else:
			parent._AddElement(self)
			self._parent = parent
			for element in self.IterateElements():
				element._root = parent._root

	@property
	def Parent(self) -> Nullable[Base]:
		"""
		Property to access the element containing this one (:attr:`_parent`).

		Assigning a parent adds this element to it, and sets the parent's root as the root of this element and of every
		element below it.

		:returns:                  The parent, or ``None``.
		:raises ValueError:        If ``None`` is assigned.
		:raises TypeError:         If the assigned parent isn't of a type this class declares in :attr:`_PARENT_TYPE`.
		:raises CodeCoverageError: If the assigned parent already contains an element of this name or line number.
		"""
		return self._parent

	@Parent.setter
	def Parent(self, parent: Base) -> None:
		if parent is None:
			raise ValueError(f"Parameter 'parent' is None.")
		elif not isinstance(parent, self._PARENT_TYPE):
			typeNames = " or ".join(f"'{parentType.__name__}'" for parentType in self._PARENT_TYPE)
			ex = TypeError(f"Parameter 'parent' is not of type {typeNames}.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		parent._AddElement(self)
		self._parent = parent
		for element in self.IterateElements():
			element._root = parent._root

	@readonly
	def Root(self) -> Nullable[CoverageSummary]:
		"""
		Read-only property to access the report's root (:attr:`_root`).

		The root is maintained by :attr:`Parent`: assigning a parent sets it for this element and every element below it.

		:returns: The root, or ``None`` while the element isn't part of a report.
		"""
		return self._root

	def IterateElements(self) -> Generator[Base, None, None]:
		"""
		Iterate this element and every element below it, depth-first.

		:returns: A generator of the elements, this one first.
		"""
		yield self


@export
class BaseWithStatus(Base):
	"""
	Base-class of the elements with a coverage state and a count: lines, branches and units.
	"""

	_status: LineCoverageStatus  #: The coverage state.
	_count:  Nullable[int]       #: How often it ran, was taken or was called, if the report says.

	def __init__(self, status: LineCoverageStatus, count: Nullable[int], parent: Nullable[Base]) -> None:
		"""
		Initialize the coverage state and the count, and add the element to its parent.

		A count of ``0`` is uncovered, a positive count covered.

		:param status:             The coverage state.
		:param count:              How often the line ran, the branch was taken or the unit was called; ``None``, if the
		                           report doesn't say.
		:param parent:             The element containing this one, or ``None``.
		:raises ValueError:        If parameter ``status`` is ``None``.
		:raises TypeError:         If parameter ``status`` isn't of type :class:`LineCoverageStatus`.
		:raises TypeError:         If parameter ``count`` isn't of type :class:`int`.
		:raises ValueError:        If parameter ``count`` is negative.
		:raises ValueError:        If parameter ``count`` contradicts parameter ``status``.
		:raises TypeError:         If parameter ``parent`` isn't of a type the class declares in :attr:`_PARENT_TYPE`.
		:raises CodeCoverageError: If the parent already contains an element of this name or line number.
		"""
		if status is None:
			raise ValueError(f"Parameter 'status' is None.")
		elif not isinstance(status, LineCoverageStatus):
			ex = TypeError(f"Parameter 'status' is not of type 'LineCoverageStatus'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(status)}'.")
			raise ex

		if count is not None:
			if not isinstance(count, int):
				ex = TypeError(f"Parameter 'count' is not of type 'int'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(count)}'.")
				raise ex
			elif count < 0:
				ex = ValueError(f"Parameter 'count' is negative.")
				ex.add_note(f"Got value '{count}'.")
				raise ex
			elif (count == 0 and status in (LineCoverageStatus.Covered, LineCoverageStatus.PartiallyCovered)) or \
					(count > 0 and status is LineCoverageStatus.Uncovered):
				ex = ValueError(f"Parameter 'count' contradicts parameter 'status'.")
				ex.add_note(f"Got count '{count}' for status '{status.name}'.")
				raise ex

		self._status = status
		self._count =  count

		super().__init__(parent)

	@readonly
	def Status(self) -> LineCoverageStatus:
		"""
		Read-only property to access the coverage state (:attr:`_status`).

		:returns: The coverage state; :attr:`LineCoverageStatus.Unknown`, if the report doesn't say.
		"""
		return self._status

	@readonly
	def Count(self) -> Nullable[int]:
		"""
		Read-only property to access how often the line ran, the branch was taken or the unit was called (:attr:`_count`).

		:returns: The count, or ``None`` if the report doesn't say.
		"""
		return self._count


@export
class CoverageCountersMixin(metaclass=ExtendedType, mixin=True):
	"""
	A mixin-class adding the counters of lines and branches, computed from the lines of a file or a unit, or summed over
	a directory's children.

	The counters are zero until :meth:`BaseWithPath.Aggregate` - of a directory or a file - or :meth:`Unit.Aggregate`
	computed them.
	"""

	_totalLines:      int  #: Number of executable lines, without the excluded ones.
	_coveredLines:    int  #: Number of executable lines, which ran.
	_excludedLines:   int  #: Number of lines excluded from the measurement.
	_partialLines:    int  #: Number of lines, which ran without taking all their branches.
	_totalBranches:   int  #: Number of branches.
	_coveredBranches: int  #: Number of branches, which were taken.

	def __init__(self) -> None:
		"""
		Initialize the counters to zero.
		"""
		self._ResetCounters()

	def _ResetCounters(self) -> None:
		"""
		Set the counters to zero.
		"""
		self._totalLines =      0
		self._coveredLines =    0
		self._excludedLines =   0
		self._partialLines =    0
		self._totalBranches =   0
		self._coveredBranches = 0

	def _CountLines(self, lines: Iterable[Line]) -> None:
		"""
		Set the counters to the counts of lines.

		:param lines: The lines.
		"""
		self._ResetCounters()
		for line in lines:
			if line._status is LineCoverageStatus.Excluded:
				self._excludedLines += 1
				continue

			self._totalLines += 1
			self._totalBranches += len(line._branches)
			self._coveredBranches += line.CoveredBranches
			if line._status is LineCoverageStatus.Covered:
				self._coveredLines += 1
			elif line._status is LineCoverageStatus.PartiallyCovered:
				self._coveredLines += 1
				self._partialLines += 1

	@readonly
	def TotalLines(self) -> int:
		"""
		Read-only property to access the number of executable lines, without the excluded ones (:attr:`_totalLines`).

		:returns: The number of executable lines.
		"""
		return self._totalLines

	@readonly
	def CoveredLines(self) -> int:
		"""
		Read-only property to access the number of executable lines, which ran (:attr:`_coveredLines`).

		:returns: The number of covered lines, including the partially covered ones.
		"""
		return self._coveredLines

	@readonly
	def MissingLines(self) -> int:
		"""
		Read-only property to return the number of executable lines, which never ran.

		:returns: :attr:`TotalLines` minus :attr:`CoveredLines`.
		"""
		return self._totalLines - self._coveredLines

	@readonly
	def ExcludedLines(self) -> int:
		"""
		Read-only property to access the number of lines excluded from the measurement (:attr:`_excludedLines`).

		:returns: The number of excluded lines.
		"""
		return self._excludedLines

	@readonly
	def PartialLines(self) -> int:
		"""
		Read-only property to access the number of lines, which ran without taking all their branches
		(:attr:`_partialLines`).

		:returns: The number of partially covered lines.
		"""
		return self._partialLines

	@readonly
	def TotalBranches(self) -> int:
		"""
		Read-only property to access the number of branches (:attr:`_totalBranches`).

		:returns: The number of branches.
		"""
		return self._totalBranches

	@readonly
	def CoveredBranches(self) -> int:
		"""
		Read-only property to access the number of branches, which were taken (:attr:`_coveredBranches`).

		:returns: The number of covered branches.
		"""
		return self._coveredBranches

	@readonly
	def MissingBranches(self) -> int:
		"""
		Read-only property to return the number of branches, which were never taken.

		:returns: :attr:`TotalBranches` minus :attr:`CoveredBranches`.
		"""
		return self._totalBranches - self._coveredBranches

	@readonly
	def LineCoverage(self) -> float:
		"""
		Read-only property to return the line coverage: the ratio of covered to executable lines.

		:returns: The line coverage in range 0.0..1.0; ``1.0`` if there is no executable line.
		"""
		return 1.0 if self._totalLines == 0 else self._coveredLines / self._totalLines

	@readonly
	def BranchCoverage(self) -> float:
		"""
		Read-only property to return the branch coverage: the ratio of taken branches to all branches.

		:returns: The branch coverage in range 0.0..1.0; ``1.0`` if there is no branch.
		"""
		return 1.0 if self._totalBranches == 0 else self._coveredBranches / self._totalBranches

	@readonly
	def Coverage(self) -> float:
		"""
		Read-only property to return the combined coverage of lines and branches, as coverage.py computes it.

		:returns: Covered lines plus taken branches, divided by executable lines plus branches, in range 0.0..1.0;
		          ``1.0`` if there is neither.
		"""
		total = self._totalLines + self._totalBranches
		return 1.0 if total == 0 else (self._coveredLines + self._coveredBranches) / total

	def _AggregateCounters(self, other: CoverageCountersMixin) -> None:
		"""
		Add the counters of another directory, file or unit to this one's.

		:param other: The other directory, file or unit, aggregated.
		"""
		self._totalLines +=      other._totalLines
		self._coveredLines +=    other._coveredLines
		self._excludedLines +=   other._excludedLines
		self._partialLines +=    other._partialLines
		self._totalBranches +=   other._totalBranches
		self._coveredBranches += other._coveredBranches


@export
class BaseWithPath(Base, CoverageCountersMixin):
	"""
	Base-class of the physical hierarchy - directories and source files -: a name, a path below the report's root, and
	the counters.

	Its parent is the :class:`Directory` containing it.
	"""

	_name: str  #: Name of the directory or file.

	def __init__(self, name: str, parent: Nullable[Directory]) -> None:
		"""
		Initialize the name and the counters, and add the directory or file to its parent directory.

		:param name:               Name of the directory or file.
		:param parent:             The directory containing this one, or ``None``.
		:raises ValueError:        If parameter ``name`` is ``None``.
		:raises TypeError:         If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError:        If parameter ``name`` is empty.
		:raises TypeError:         If parameter ``parent`` isn't of type :class:`Directory`.
		:raises CodeCoverageError: If the parent directory already contains a file or directory of this name.
		"""
		if name is None:
			raise ValueError(f"Parameter 'name' is None.")
		elif not isinstance(name, str):
			ex = TypeError(f"Parameter 'name' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(name)}'.")
			raise ex
		elif name == "":
			raise ValueError(f"Parameter 'name' is empty.")

		self._name = name
		CoverageCountersMixin.__init__(self)

		super().__init__(parent)

	@readonly
	def Name(self) -> str:
		"""
		Read-only property to access the name of the directory or file (:attr:`_name`).

		:returns: The name.
		"""
		return self._name

	@readonly
	def Path(self) -> Path:
		"""
		Read-only property to return the path below the root: the names of the parent directories and the own name.

		:returns: The path, e.g. ``src/Counter.vhdl``; the name, if there is no parent.
		"""
		if self._parent is None:
			return Path(self._name)

		return self._parent.Path / self._name

	@abstractmethod
	def Aggregate(self) -> None:
		"""
		Compute the counters.
		"""


@export
class Directory(BaseWithPath):
	"""
	A directory: its directories and source files, and their summed counters.
	"""

	_PARENT_TYPE: ClassVar[tuple[type, ...]] = ()  #: A directory is in a directory; set below the class.

	_directories: dict[str, Directory]  #: The directories in this directory, by name.
	_files:       dict[str, File]       #: The source files in this directory, by name.

	def __init__(self, name: str, *, parent: Nullable[Directory] = None) -> None:
		"""
		Initialize a directory, and add it to its parent directory.

		:param name:               Name of the directory.
		:param parent:             Optional, the directory containing this one. Default: ``None``.
		:raises ValueError:        If parameter ``name`` is ``None``.
		:raises TypeError:         If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError:        If parameter ``name`` is empty.
		:raises TypeError:         If parameter ``parent`` isn't of type :class:`Directory`.
		:raises CodeCoverageError: If the parent directory already contains a file or directory of this name.
		"""
		self._directories = {}
		self._files =       {}

		super().__init__(name, parent)

	def _AddElement(self, element: BaseWithPath) -> None:
		"""
		Add a directory or file, which names this directory as its parent.

		:param element:            The directory or file.
		:raises CodeCoverageError: If this directory already contains a file or directory of this name.
		"""
		if element._name in self._directories or element._name in self._files:
			raise CodeCoverageError(f"Directory '{self.Path.as_posix()}' already contains '{element._name}'.")

		if isinstance(element, Directory):
			self._directories[element._name] = element
		else:
			self._files[element._name] = element  # type: ignore[assignment]

	def IterateElements(self) -> Generator[Base, None, None]:
		"""
		Iterate this directory, then the directories and files in it and the elements below them.

		:returns: A generator of the directory and the elements below it.
		"""
		yield self
		for child in (*self._directories.values(), *self._files.values()):
			yield from child.IterateElements()

	@readonly
	def Directories(self) -> dict[str, Directory]:
		"""
		Read-only property to access the directories in this directory (:attr:`_directories`).

		:returns: The directories, by name.
		"""
		return self._directories

	@readonly
	def Files(self) -> dict[str, File]:
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

	def GetOrAddFile(self, path: Path | str) -> File:
		"""
		Return the source file at a path below this directory, adding it and the directories on its way, if missing.

		A backslash in a string path separates directories too, as a report written on Windows has them.

		:param path:               The file's path relative to this directory, e.g. ``src/Counter.vhdl``.
		:returns:                  The file.
		:raises ValueError:        If parameter ``path`` is ``None``.
		:raises TypeError:         If parameter ``path`` isn't of type :class:`~pathlib.Path` or :class:`str`.
		:raises ValueError:        If parameter ``path`` names no file.
		:raises CodeCoverageError: If a part of the path is a file instead of a directory, or the file's name is a
		                           directory's.
		"""
		if path is None:
			raise ValueError(f"Parameter 'path' is None.")
		elif isinstance(path, str):
			path = Path(path.replace("\\", "/"))
		elif not isinstance(path, Path):
			ex = TypeError(f"Parameter 'path' is not of type 'Path' or 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(path)}'.")
			raise ex

		parts = [part for part in path.parts if part not in ("", ".", "/")]
		if len(parts) == 0:
			ex = ValueError(f"Parameter 'path' names no file.")
			ex.add_note(f"Got path '{path}'.")
			raise ex

		directory = self
		for part in parts[:-1]:
			if part in directory._files:
				raise CodeCoverageError(f"'{(directory.Path / part).as_posix()}' is a file, not a directory.")
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
			self._AggregateCounters(child)

	def __repr__(self) -> str:
		"""
		Return a representation of the directory for debugging.

		:returns: The directory's path, its number of files and its line coverage, e.g. ``<Directory src: 3 files, 75.0%>``.
		"""
		return f"<Directory {self.Path.as_posix()}: {self.FileCount} files, {self.LineCoverage:.1%}>"


Directory._PARENT_TYPE = (Directory, )


@export
class CoverageSummary(Directory):
	"""
	The root of a code coverage report: the directory the report's file paths are relative to, and the top-level units
	of the logical hierarchy.

	It is its own root.
	"""

	_PARENT_TYPE: ClassVar[tuple[type, ...]] = ()  #: The report's root has no parent.

	_sourceDirectories: list[Path]       #: The directories the report names as where the sources were, if any.
	_units:             dict[str, Unit]  #: The top-level units, by name.

	def __init__(self, name: str, *, sourceDirectories: Iterable[Path] = ()) -> None:
		"""
		Initialize the root of a code coverage report.

		:param name:              Name of the report, e.g. of the project measured.
		:param sourceDirectories: Optional, the directories the report names as where the sources were. Default: none.
		:raises ValueError:       If parameter ``name`` is ``None``.
		:raises TypeError:        If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError:       If parameter ``name`` is empty.
		:raises ValueError:       If parameter ``sourceDirectories`` is ``None``.
		:raises TypeError:        If parameter ``sourceDirectories`` isn't iterable.
		:raises TypeError:        If parameter ``sourceDirectories`` contains an element not of type :class:`~pathlib.Path`.
		"""
		if sourceDirectories is None:
			raise ValueError(f"Parameter 'sourceDirectories' is None.")
		elif not isinstance(sourceDirectories, Iterable):
			ex = TypeError(f"Parameter 'sourceDirectories' is not iterable.")
			ex.add_note(f"Got type '{getFullyQualifiedName(sourceDirectories)}'.")
			raise ex

		self._sourceDirectories = []
		for sourceDirectory in sourceDirectories:
			if not isinstance(sourceDirectory, Path):
				ex = TypeError(f"Parameter 'sourceDirectories' contains an element not of type 'Path'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(sourceDirectory)}'.")
				raise ex

			self._sourceDirectories.append(sourceDirectory)

		self._units = {}

		super().__init__(name)

		self._root = self

	def _AddElement(self, element: BaseWithPath | Unit) -> None:
		"""
		Add a top-level unit, directory or file, which names the report's root as its parent.

		:param element:            The unit, directory or file.
		:raises CodeCoverageError: If the root already contains a unit of this name.
		:raises CodeCoverageError: If the root already contains a file or directory of this name.
		"""
		if not isinstance(element, Unit):
			super()._AddElement(element)
		elif element._name in self._units:
			raise CodeCoverageError(f"Unit '{element._name}' is added twice to '{self._name}'.")
		else:
			self._units[element._name] = element

	def IterateElements(self) -> Generator[Base, None, None]:
		"""
		Iterate the report's root, the elements of the physical hierarchy, then those of the logical hierarchy.

		:returns: A generator of the root and every element below it.
		"""
		yield from super().IterateElements()
		for unit in self._units.values():
			yield from unit.IterateElements()

	@readonly
	def Path(self) -> Path:
		"""
		Read-only property to return the path below the root, which is the root's own: ``.``.

		So the paths of the directories and files below are relative to the root, without its name.

		:returns: ``.``
		"""
		return Path(".")

	@readonly
	def SourceDirectories(self) -> list[Path]:
		"""
		Read-only property to access the directories the report names as where the sources were
		(:attr:`_sourceDirectories`).

		They are the paths on the machine the coverage was measured on, so they may not exist where the report is read.

		:returns: The source directories; empty, if the report names none.
		"""
		return self._sourceDirectories

	@readonly
	def Units(self) -> dict[str, Unit]:
		"""
		Read-only property to access the top-level units of the logical hierarchy (:attr:`_units`).

		:returns: The units, by name.
		"""
		return self._units

	def IterateUnits(self) -> Generator[Unit, None, None]:
		"""
		Iterate the units of the logical hierarchy, a unit before its units, each level sorted by name.

		:returns: A generator of the units.
		"""
		for name in sorted(self._units):
			yield from self._units[name].IterateUnits()

	def Aggregate(self) -> None:
		"""
		Aggregate the physical hierarchy - directories and files -, then the units of the logical hierarchy.
		"""
		super().Aggregate()
		for unit in self._units.values():
			unit.Aggregate()


@export
class File(BaseWithPath):
	"""
	A source file: the coverage of its executable lines, and the units of the logical hierarchy it holds.
	"""

	_PARENT_TYPE: ClassVar[tuple[type, ...]] = (Directory, )  #: A file is in a directory.

	_lines: dict[int, Line]  #: The executable lines, by line number.
	_units: list[Unit]       #: The units naming this file, in the order they were added.

	def __init__(self, name: str, *, lines: Iterable[Line] = (), parent: Nullable[Directory] = None) -> None:
		"""
		Initialize a source file, and add it to its directory.

		:param name:               Name of the file.
		:param lines:              Optional, the executable lines. Default: no line.
		:param parent:             Optional, the directory containing the file. Default: ``None``.
		:raises ValueError:        If parameter ``name`` is ``None``.
		:raises TypeError:         If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError:        If parameter ``name`` is empty.
		:raises ValueError:        If parameter ``lines`` is ``None``.
		:raises TypeError:         If parameter ``lines`` isn't iterable.
		:raises TypeError:         If parameter ``lines`` contains an element not of type :class:`Line`.
		:raises TypeError:         If parameter ``parent`` isn't of type :class:`Directory`.
		:raises CodeCoverageError: If the directory already contains a file or directory of this name.
		:raises CodeCoverageError: If two lines have the same number.
		"""
		if lines is None:
			raise ValueError(f"Parameter 'lines' is None.")
		elif not isinstance(lines, Iterable):
			ex = TypeError(f"Parameter 'lines' is not iterable.")
			ex.add_note(f"Got type '{getFullyQualifiedName(lines)}'.")
			raise ex

		lineList = []
		for line in lines:
			if not isinstance(line, Line):
				ex = TypeError(f"Parameter 'lines' contains an element not of type 'Line'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(line)}'.")
				raise ex

			lineList.append(line)

		self._lines = {}
		self._units = []

		super().__init__(name, parent)

		for line in lineList:
			line.Parent = self

	def _AddElement(self, line: Line) -> None:
		"""
		Add a line, which names this file as its parent.

		:param line:               The line.
		:raises CodeCoverageError: If the file already has a line of this number.
		"""
		if line._lineNumber in self._lines:
			raise CodeCoverageError(f"Line {line._lineNumber} of file '{self.Path.as_posix()}' is added twice.")

		self._lines[line._lineNumber] = line

	def IterateElements(self) -> Generator[Base, None, None]:
		"""
		Iterate this file, then its lines and their branches.

		:returns: A generator of the file and the elements below it.
		"""
		yield self
		for line in self._lines.values():
			yield from line.IterateElements()

	@readonly
	def Lines(self) -> dict[int, Line]:
		"""
		Read-only property to access the executable lines (:attr:`_lines`).

		:returns: The lines, by line number.
		"""
		return self._lines

	@readonly
	def Units(self) -> list[Unit]:
		"""
		Read-only property to access the units naming this file (:attr:`_units`).

		:returns: The units, e.g. a module, its classes and functions.
		"""
		return self._units

	def Aggregate(self) -> None:
		"""
		Compute the counters from the file's lines.
		"""
		self._CountLines(self._lines.values())

	def __repr__(self) -> str:
		"""
		Return a representation of the file for debugging.

		:returns: The file's path and line coverage, e.g. ``<File src/Counter.vhdl: 80.0%>``.
		"""
		return f"<File {self.Path.as_posix()}: {self.LineCoverage:.1%}>"


@export
class Line(BaseWithStatus):
	"""
	The coverage of an executable line: its coverage state, how often it ran - if the report says -, and its branches.

	A report lists only executable lines; a line it doesn't list - a comment, a declaration - has no :class:`Line`. Its
	parent is the :class:`File` it is in.
	"""

	_PARENT_TYPE: ClassVar[tuple[type, ...]] = (File, )  #: A line is in a file.

	_lineNumber: int           #: Line number, counted from 1.
	_branches:   list[Branch]  #: The branches starting at this line.

	def __init__(
		self,
		lineNumber: int,
		status: LineCoverageStatus,
		count: Nullable[int] = None,
		branches: Iterable[Branch] = (),
		parent: Nullable[File] = None
	) -> None:
		"""
		Initialize a line's coverage, and add it to its file.

		:param lineNumber:         Line number, counted from 1.
		:param status:             Coverage state of the line.
		:param count:              Optional, how often the line ran, if the report says. Default: ``None``.
		:param branches:           Optional, the branches starting at this line. Default: none.
		:param parent:             Optional, the file the line is in. Default: ``None``.
		:raises ValueError:        If parameter ``lineNumber`` is ``None``.
		:raises TypeError:         If parameter ``lineNumber`` isn't of type :class:`int`.
		:raises ValueError:        If parameter ``lineNumber`` is less than 1.
		:raises ValueError:        If parameter ``branches`` is ``None``.
		:raises TypeError:         If parameter ``branches`` isn't iterable.
		:raises TypeError:         If parameter ``branches`` contains an element not of type :class:`Branch`.
		:raises ValueError:        If parameter ``status`` is ``None``.
		:raises TypeError:         If parameter ``status`` isn't of type :class:`LineCoverageStatus`.
		:raises TypeError:         If parameter ``count`` isn't of type :class:`int`.
		:raises ValueError:        If parameter ``count`` is negative.
		:raises ValueError:        If parameter ``count`` contradicts parameter ``status``.
		:raises TypeError:         If parameter ``parent`` isn't of type :class:`File`.
		:raises CodeCoverageError: If the file already has a line of this number.
		"""
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

		if branches is None:
			raise ValueError(f"Parameter 'branches' is None.")
		elif not isinstance(branches, Iterable):
			ex = TypeError(f"Parameter 'branches' is not iterable.")
			ex.add_note(f"Got type '{getFullyQualifiedName(branches)}'.")
			raise ex

		branchList = []
		for branch in branches:
			if not isinstance(branch, Branch):
				ex = TypeError(f"Parameter 'branches' contains an element not of type 'Branch'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(branch)}'.")
				raise ex

			branchList.append(branch)

		self._lineNumber = lineNumber
		self._branches =   []

		super().__init__(status, count, parent)

		for branch in branchList:
			branch.Parent = self

	def _AddElement(self, branch: Branch) -> None:
		"""
		Add a branch, which names this line as its parent.

		:param branch: The branch.
		"""
		self._branches.append(branch)

	def IterateElements(self) -> Generator[Base, None, None]:
		"""
		Iterate this line, then its branches.

		:returns: A generator of the line and its branches.
		"""
		yield self
		yield from self._branches

	@readonly
	def LineNumber(self) -> int:
		"""
		Read-only property to access the line number (:attr:`_lineNumber`).

		:returns: The line number, counted from 1.
		"""
		return self._lineNumber

	@readonly
	def Branches(self) -> list[Branch]:
		"""
		Read-only property to access the branches starting at this line (:attr:`_branches`).

		:returns: The branches; empty for a line, which doesn't branch.
		"""
		return self._branches

	@readonly
	def CoveredBranches(self) -> int:
		"""
		Read-only property to return the number of this line's branches, which were taken.

		:returns: The number of branches with state :attr:`LineCoverageStatus.Covered`.
		"""
		return sum(1 for branch in self._branches if branch._status is LineCoverageStatus.Covered)

	def __repr__(self) -> str:
		"""
		Return a representation of the line's coverage for debugging.

		:returns: The line number, the state and the branches, e.g. ``<Line 12: PartiallyCovered (1/2 branches)>``.
		"""
		branches = f" ({self.CoveredBranches}/{len(self._branches)} branches)" if len(self._branches) > 0 else ""
		return f"<Line {self._lineNumber}: {self._status.name}{branches}>"


@export
class Branch(BaseWithStatus):
	"""
	A branch of a line: whether it was taken, how often - if the report says -, and where it goes - if the report says.

	Its parent is the :class:`Line` it starts at.
	"""

	_PARENT_TYPE: ClassVar[tuple[type, ...]] = (Line, )  #: A branch starts at a line.

	_target: Nullable[Line]  #: The line the branch goes to, if the report says.

	def __init__(
		self,
		status: LineCoverageStatus,
		count: Nullable[int] = None,
		target: Nullable[Line] = None,
		parent: Nullable[Line] = None
	) -> None:
		"""
		Initialize a branch, and add it to its line.

		:param status:      Whether the branch was taken.
		:param count:       Optional, how often the branch was taken, if the report says. Default: ``None``.
		:param target:      Optional, the line the branch goes to, if the report says; ``None`` for an exit of a function.
		                    Default: ``None``.
		:param parent:      Optional, the line the branch starts at. Default: ``None``.
		:raises TypeError:  If parameter ``target`` isn't of type :class:`Line`.
		:raises ValueError: If parameter ``status`` is ``None``.
		:raises TypeError:  If parameter ``status`` isn't of type :class:`LineCoverageStatus`.
		:raises TypeError:  If parameter ``count`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``count`` is negative.
		:raises ValueError: If parameter ``count`` contradicts parameter ``status``.
		:raises TypeError:  If parameter ``parent`` isn't of type :class:`Line`.
		"""
		if target is not None and not isinstance(target, Line):
			ex = TypeError(f"Parameter 'target' is not of type 'Line'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(target)}'.")
			raise ex

		self._target = target

		super().__init__(status, count, parent)

	@readonly
	def Target(self) -> Nullable[Line]:
		"""
		Read-only property to access the line the branch goes to (:attr:`_target`).

		:returns: The line, or ``None`` if the report doesn't say or the branch exits the function.
		"""
		return self._target


@export
class Unit(BaseWithStatus, CoverageCountersMixin):
	"""
	Base-class of the logical hierarchy: a language unit - a package, a module, a class, a function, a method -, the
	units it contains, and the lines it covers.

	Its parent is the :class:`Unit` containing it, or the report's :class:`CoverageSummary`. A unit's lines are
	:class:`Line` objects of its file, so the physical and the logical hierarchy count the same lines. Its counters are
	computed from its own lines and those of the units it contains, each line counted once.
	"""

	_PARENT_TYPE: ClassVar[tuple[type, ...]] = ()  #: A unit is in a unit or the report's root; set below the class.

	_name:      str              #: Name of the unit.
	_units:     dict[str, Unit]  #: The units this one contains, by name.
	_file:      Nullable[File]   #: The source file the unit is in, if the report says.
	_startLine: Nullable[Line]   #: The unit's first line, if the report says.
	_endLine:   Nullable[Line]   #: The unit's last line, if the report says.
	_lines:     dict[int, Line]  #: The executable lines of the unit itself, by line number.

	def __init__(
		self,
		name: str,
		*,
		file: Nullable[File] = None,
		startLine: Nullable[Line] = None,
		endLine: Nullable[Line] = None,
		status: LineCoverageStatus = LineCoverageStatus.Unknown,
		count: Nullable[int] = None,
		parent: Nullable[Unit | CoverageSummary] = None
	) -> None:
		"""
		Initialize a unit, and add it to its file and to the unit or report containing it.

		:param name:               Name of the unit.
		:param file:               Optional, the source file the unit is in. Default: ``None``.
		:param startLine:          Optional, the unit's first line. Default: ``None``.
		:param endLine:            Optional, the unit's last line. Default: ``None``.
		:param status:             Optional, whether the unit was called. Default: :attr:`LineCoverageStatus.Unknown`.
		:param count:              Optional, how often the unit was called. Default: ``None``.
		:param parent:             Optional, the unit or report containing this unit. Default: ``None``.
		:raises ValueError:        If parameter ``name`` is ``None``.
		:raises TypeError:         If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError:        If parameter ``name`` is empty.
		:raises TypeError:         If parameter ``file`` isn't of type :class:`File`.
		:raises TypeError:         If parameter ``startLine`` isn't of type :class:`Line`.
		:raises TypeError:         If parameter ``endLine`` isn't of type :class:`Line`.
		:raises ValueError:        If parameter ``status`` is ``None``.
		:raises TypeError:         If parameter ``status`` isn't of type :class:`LineCoverageStatus`.
		:raises TypeError:         If parameter ``count`` isn't of type :class:`int`.
		:raises ValueError:        If parameter ``count`` is negative.
		:raises ValueError:        If parameter ``count`` contradicts parameter ``status``.
		:raises TypeError:         If parameter ``parent`` isn't of type :class:`Unit` or :class:`CoverageSummary`.
		:raises CodeCoverageError: If the parent already contains a unit of this name.
		"""
		if name is None:
			raise ValueError(f"Parameter 'name' is None.")
		elif not isinstance(name, str):
			ex = TypeError(f"Parameter 'name' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(name)}'.")
			raise ex
		elif name == "":
			raise ValueError(f"Parameter 'name' is empty.")

		if file is not None and not isinstance(file, File):
			ex = TypeError(f"Parameter 'file' is not of type 'File'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(file)}'.")
			raise ex

		if startLine is not None and not isinstance(startLine, Line):
			ex = TypeError(f"Parameter 'startLine' is not of type 'Line'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(startLine)}'.")
			raise ex

		if endLine is not None and not isinstance(endLine, Line):
			ex = TypeError(f"Parameter 'endLine' is not of type 'Line'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(endLine)}'.")
			raise ex

		self._name =      name
		self._units =     {}
		self._file =      file
		self._startLine = startLine
		self._endLine =   endLine
		self._lines =     {}
		CoverageCountersMixin.__init__(self)

		super().__init__(status, count, parent)

		if file is not None:
			file._units.append(self)

	def _AddElement(self, unit: Unit) -> None:
		"""
		Add a unit, which names this unit as its parent.

		:param unit:               The unit.
		:raises CodeCoverageError: If this unit already contains a unit of this name.
		"""
		if unit._name in self._units:
			raise CodeCoverageError(f"Unit '{unit._name}' is added twice to '{self._name}'.")

		self._units[unit._name] = unit

	def IterateElements(self) -> Generator[Base, None, None]:
		"""
		Iterate this unit, then the units it contains and the units below them.

		:returns: A generator of the unit and the units below it.
		"""
		yield self
		for unit in self._units.values():
			yield from unit.IterateElements()

	@readonly
	def Name(self) -> str:
		"""
		Read-only property to access the unit's name (:attr:`_name`).

		:returns: The name.
		"""
		return self._name

	@readonly
	def QualifiedName(self) -> str:
		"""
		Read-only property to return the names of the units from the top down to this one, joined by ``.``.

		:returns: The qualified name, e.g. ``myPackage.Shapes.Circle.Area``.
		"""
		if isinstance(self._parent, Unit):
			return f"{self._parent.QualifiedName}.{self._name}"

		return self._name

	@readonly
	def Units(self) -> dict[str, Unit]:
		"""
		Read-only property to access the units this one contains (:attr:`_units`).

		:returns: The units, by name.
		"""
		return self._units

	@readonly
	def File(self) -> Nullable[File]:
		"""
		Read-only property to access the source file the unit is in (:attr:`_file`).

		:returns: The file, or ``None`` if the report doesn't say.
		"""
		return self._file

	@readonly
	def StartLine(self) -> Nullable[Line]:
		"""
		Read-only property to access the unit's first line (:attr:`_startLine`).

		:returns: The line of the unit's file, or ``None`` if the report doesn't say.
		"""
		return self._startLine

	@readonly
	def EndLine(self) -> Nullable[Line]:
		"""
		Read-only property to access the unit's last line (:attr:`_endLine`).

		:returns: The line of the unit's file, or ``None`` if the report doesn't say.
		"""
		return self._endLine

	@readonly
	def Lines(self) -> dict[int, Line]:
		"""
		Read-only property to access the executable lines of the unit itself (:attr:`_lines`).

		:returns: The lines, by line number; the lines of the units it contains aren't included.
		"""
		return self._lines

	def AddLine(self, line: Line) -> None:
		"""
		Add a line of the unit's file to the unit; a line added twice is kept once.

		:param line:        The line.
		:raises ValueError: If parameter ``line`` is ``None``.
		:raises TypeError:  If parameter ``line`` isn't of type :class:`Line`.
		"""
		if line is None:
			raise ValueError(f"Parameter 'line' is None.")
		elif not isinstance(line, Line):
			ex = TypeError(f"Parameter 'line' is not of type 'Line'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(line)}'.")
			raise ex

		self._lines[line._lineNumber] = line

	def IterateUnits(self) -> Generator[Unit, None, None]:
		"""
		Iterate this unit, then the units it contains, each level sorted by name.

		:returns: A generator of the units.
		"""
		yield self
		for name in sorted(self._units):
			yield from self._units[name].IterateUnits()

	def Aggregate(self) -> None:
		"""
		Aggregate the units this one contains, then compute the counters from the lines of this unit and its units, each
		line counted once.
		"""
		for unit in self._units.values():
			unit.Aggregate()

		lines: dict[int, Line] = {}
		for unit in self.IterateUnits():
			lines.update((id(line), line) for line in unit._lines.values())

		self._CountLines(lines.values())

	def __repr__(self) -> str:
		"""
		Return a representation of the unit for debugging.

		:returns: The unit's kind, qualified name and line coverage, e.g. ``<Function Shapes.Circle.Area: 100.0%>``.
		"""
		return f"<{self.__class__.__name__} {self.QualifiedName}: {self.LineCoverage:.1%}>"


Unit._PARENT_TYPE = (Unit, CoverageSummary)


@export
class Package(Unit):
	"""A package: e.g. a Python package, a Java package, a VHDL library."""


@export
class Module(Unit):
	"""A module: e.g. a Python module, a VHDL package or entity."""


@export
class SourceFile(Unit):
	"""A source file as a unit, where the file is the language's unit: e.g. a C translation unit, a Bash or TCL script."""


@export
class Class(Unit):
	"""A class: e.g. a Python, Java or C++ class."""


@export
class Function(Unit):
	"""A function: e.g. a Python or C function, a VHDL function or procedure."""


@export
class Method(Unit):
	"""A method of a class."""


@export
class Document(metaclass=ExtendedType, mixin=True):
	"""
	A mixin-class representing a code coverage report file, which is read in two steps: analyzed, then converted.
	"""

	_path:               Path   #: Path to the report file.
	_analysisDuration:   float  #: Duration of :meth:`Analyze` in seconds, or ``-1.0`` before it ran.
	_conversionDuration: float  #: Duration of :meth:`Convert` in seconds, or ``-1.0`` before it ran.

	def __init__(self, reportFile: Path, analyzeAndConvert: bool = False) -> None:
		"""
		Initialize the report file, and optionally read it.

		:param reportFile:        Path to the report file.
		:param analyzeAndConvert: Optional, if true, analyze the file and convert its content. Default: ``False``.
		"""
		self._path = reportFile

		self._analysisDuration =   -1.0
		self._conversionDuration = -1.0

		if analyzeAndConvert:
			self.Analyze()
			self.Convert()

	@readonly
	def ReportFile(self) -> Path:
		"""
		Read-only property to access the path to the report file (:attr:`_path`).

		:returns: The report file's path.
		"""
		return self._path

	@readonly
	def AnalysisDuration(self) -> timedelta:
		"""
		Read-only property to return the duration of :meth:`Analyze`: reading, parsing and validating the file.

		:returns: The duration; negative, if the file wasn't analyzed yet.
		"""
		return timedelta(seconds=self._analysisDuration)

	@readonly
	def ModelConversionDuration(self) -> timedelta:
		"""
		Read-only property to return the duration of :meth:`Convert`: building the report format's model.

		:returns: The duration; negative, if the content wasn't converted yet.
		"""
		return timedelta(seconds=self._conversionDuration)

	@abstractmethod
	def Analyze(self) -> None:
		"""
		Read, parse and validate the report file.
		"""

	@abstractmethod
	def Convert(self) -> None:
		"""
		Convert the analyzed content to the report format's model.
		"""

	@abstractmethod
	def ToCoverageSummary(self) -> CoverageSummary:
		"""
		Convert the report format's model to the common code coverage model, and aggregate it.

		:returns: The report's root of the common model.
		"""
