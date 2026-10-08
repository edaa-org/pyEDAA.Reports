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
  :class:`SourceFile`, :class:`Class`, :class:`Function`, :class:`Method` -, each spanning its file from a first to a
  last :class:`Line`, so both hierarchies count the same lines.

A :class:`Line` and a :class:`Branch` carry a :class:`LineCoverageStatus` and - if the report says - a count: how
often the line ran, or the branch was taken. :meth:`CoverageSummary.Aggregate` computes the counters of every file,
directory and unit.

The report formats have models of their own, which convert to this one:

.. seealso::

   :mod:`pyEDAA.Reports.CodeCoverage.Cobertura`
      |rarr| The Cobertura XML format, as written e.g. by coverage.py (``coverage xml``) or gcovr (``--cobertura``).
   :mod:`pyEDAA.Reports.CodeCoverage.CoveragePy`
      |rarr| coverage.py's JSON format (``coverage json``).
   :mod:`pyEDAA.Reports.CodeCoverage.GHDL`
      |rarr| GHDL's JSON coverage file (``ghdl -r --coverage``).
   :mod:`pyEDAA.Reports.CodeCoverage.Gcov`
      |rarr| GCC's gcov JSON format (``gcov --json-format``).
   :mod:`pyEDAA.Reports.CodeCoverage.LCOV`
      |rarr| lcov's tracefile format, as written e.g. by lcov (``lcov --capture``) or llvm-cov (``llvm-cov export``).
   :mod:`pyEDAA.Reports.CodeCoverage.JaCoCo`
      |rarr| JaCoCo's XML format, as written e.g. by Gradle's task ``jacocoTestReport``.
   :mod:`pyEDAA.Reports.CodeCoverage.LLVM`
      |rarr| LLVM's JSON code coverage export (``llvm-cov export``), e.g. of Clang's source-based code coverage.
"""
from __future__            import annotations

from collections.abc       import Iterable
from datetime              import timedelta
from enum                  import Enum
from pathlib               import Path
from typing                import ClassVar, Generator, Optional as Nullable

from pyTooling.Common      import getFullyQualifiedName
from pyTooling.Decorators  import export, readonly
from pyTooling.MetaClasses import ExtendedType, abstractclass, abstractmethod

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

	_PARENT_TYPE: ClassVar[tuple[type, ...]]  #: The types a parent may have; assigned by each class having a parent.

	_parent: Nullable[Base]             #: The element containing this one, or ``None``.
	_root:   Nullable[CoverageSummary]  #: The report's root, or ``None`` while the element isn't part of a report.

	def __init__(self, *, parent: Nullable[Base] = None) -> None:
		"""
		Initialize an element with its parent and the parent's root.

		The parent doesn't list the element yet: the class setting the field the parent stores it by - a name, a line
		number - adds it with ``parent._AddElement(self)``.

		:param parent:     Optional, the element containing this one. Default: ``None``.
		:raises TypeError: If parameter ``parent`` isn't of a type this class declares in :attr:`_PARENT_TYPE`.
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
			self._parent = parent
			self._root =   parent._root

	@property
	def Parent(self) -> Nullable[Base]:
		"""
		Property to access the element containing this one (:attr:`_parent`).

		Assigning a parent adds this element to it, and sets the parent's root as the root of this element and of every
		element below it.

		:returns:                  The parent, or ``None``.
		:raises ValueError:        If ``None`` is assigned.
		:raises TypeError:         If the assigned parent isn't of a type this class declares in :attr:`_PARENT_TYPE`.
		:raises TypeError:         If a parent is assigned to a :class:`CoverageSummary`, which has no parent.
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
		self._root =   parent._root
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

	@abstractmethod
	def IterateElements(self) -> Generator[Base, None, None]:
		"""
		Iterate every element below this one, depth-first.

		:returns: A generator of the elements below this one.
		"""


@export
class BaseWithStatus(Base):
	"""
	Base-class of the elements with a coverage state and a count: lines, branches and units.
	"""

	_status:        LineCoverageStatus  #: The coverage state.
	_coverageCount: Nullable[int]       #: How often it ran, was taken or was called, if the report says.

	def __init__(self, status: LineCoverageStatus, coverageCount: Nullable[int], *, parent: Nullable[Base]) -> None:
		"""
		Initialize the parent, the coverage state and the count.

		A count of ``0`` is uncovered, a positive count covered.

		:param status:        The coverage state.
		:param coverageCount: How often the line ran, the branch was taken or the unit was called; ``None``, if the report
		                      doesn't say.
		:param parent:        The element containing this one, or ``None``.
		:raises TypeError:    If parameter ``parent`` isn't of a type the class declares in :attr:`_PARENT_TYPE`.
		:raises ValueError:   If parameter ``status`` is ``None``.
		:raises TypeError:    If parameter ``status`` isn't of type :class:`LineCoverageStatus`.
		:raises TypeError:    If parameter ``coverageCount`` isn't of type :class:`int`.
		:raises ValueError:   If parameter ``coverageCount`` is negative.
		:raises ValueError:   If parameter ``coverageCount`` contradicts parameter ``status``.
		"""
		super().__init__(parent=parent)

		if status is None:
			raise ValueError(f"Parameter 'status' is None.")
		elif not isinstance(status, LineCoverageStatus):
			ex = TypeError(f"Parameter 'status' is not of type 'LineCoverageStatus'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(status)}'.")
			raise ex

		if coverageCount is not None:
			if not isinstance(coverageCount, int):
				ex = TypeError(f"Parameter 'coverageCount' is not of type 'int'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(coverageCount)}'.")
				raise ex
			elif coverageCount < 0:
				ex = ValueError(f"Parameter 'coverageCount' is negative.")
				ex.add_note(f"Got value '{coverageCount}'.")
				raise ex
			elif (coverageCount == 0 and status in (LineCoverageStatus.Covered, LineCoverageStatus.PartiallyCovered)) or \
					(coverageCount > 0 and status is LineCoverageStatus.Uncovered):
				ex = ValueError(f"Parameter 'coverageCount' contradicts parameter 'status'.")
				ex.add_note(f"Got count '{coverageCount}' for status '{status.name}'.")
				raise ex

		self._status =        status
		self._coverageCount = coverageCount

	@readonly
	def Status(self) -> LineCoverageStatus:
		"""
		Read-only property to access the coverage state (:attr:`_status`).

		:returns: The coverage state; :attr:`LineCoverageStatus.Unknown`, if the report doesn't say.
		"""
		return self._status

	@readonly
	def CoverageCount(self) -> Nullable[int]:
		"""
		Read-only property to access how often it ran, was taken or was called (:attr:`_coverageCount`).

		:returns: The count, or ``None`` if the report doesn't say.
		"""
		return self._coverageCount


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

		A line's covered branches are those its :meth:`Line.Aggregate` computed.

		:param lines: The lines.
		"""
		self._ResetCounters()
		for line in lines:
			if line._status is LineCoverageStatus.Excluded:
				self._excludedLines += 1
				continue

			self._totalLines += 1
			self._totalBranches += len(line._branches)
			self._coveredBranches += line._coveredBranches
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

	def __init__(self, name: str, *, parent: Nullable[Directory]) -> None:
		"""
		Initialize the parent, the name and the counters.

		:param name:        Name of the directory or file.
		:param parent:      The directory containing this one, or ``None``.
		:raises TypeError:  If parameter ``parent`` isn't of type :class:`Directory`.
		:raises ValueError: If parameter ``name`` is ``None``.
		:raises TypeError:  If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError: If parameter ``name`` is empty.
		"""
		super().__init__(parent=parent)
		CoverageCountersMixin.__init__(self)

		if name is None:
			raise ValueError(f"Parameter 'name' is None.")
		elif not isinstance(name, str):
			ex = TypeError(f"Parameter 'name' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(name)}'.")
			raise ex
		elif name == "":
			raise ValueError(f"Parameter 'name' is empty.")

		self._name = name

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
		Read-only property to return the path below the root: the names of the parent directories and the own name, e.g.
		``src/Counter.vhdl``.

		:returns: The path; the name, if there is no parent.
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

	_PARENT_TYPE: ClassVar[tuple[type, ...]]  #: A directory is in a directory; assigned below the class.

	_directories: dict[str, Directory]  #: The directories in this directory, by name.
	_files:       dict[str, File]       #: The source files in this directory, by name.

	def __init__(self, name: str, *, parent: Nullable[Directory] = None) -> None:
		"""
		Initialize a directory, and add it to its parent directory.

		:param name:               Name of the directory.
		:param parent:             Optional, the directory containing this one. Default: ``None``.
		:raises TypeError:         If parameter ``parent`` isn't of type :class:`Directory`.
		:raises ValueError:        If parameter ``name`` is ``None``.
		:raises TypeError:         If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError:        If parameter ``name`` is empty.
		:raises CodeCoverageError: If the parent directory already contains a file or directory of this name.
		"""
		super().__init__(name, parent=parent)

		self._directories = {}
		self._files =       {}

		if parent is not None:
			parent._AddElement(self)

	def _AddElement(self, element: Directory | File) -> None:
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

		parts = [part for part in path.parts if part not in ("", ".", path.anchor)]
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
		Return a representation of the directory for debugging, e.g. ``<Directory src: 3 files, 75.0%>``.

		:returns: The directory's path, its number of files and its line coverage.
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

	_sourceDirectories: list[Path]       #: The directories the report names as where the sources were, if any.
	_units:             dict[str, Unit]  #: The top-level units, by name.

	def __init__(self, name: str, *, sourceDirectories: Nullable[Iterable[Path]] = None) -> None:
		"""
		Initialize the root of a code coverage report.

		:param name:              Name of the report, e.g. of the project measured.
		:param sourceDirectories: Optional, the directories the report names as where the sources were. Default: none.
		:raises ValueError:       If parameter ``name`` is ``None``.
		:raises TypeError:        If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError:       If parameter ``name`` is empty.
		:raises TypeError:        If parameter ``sourceDirectories`` isn't iterable.
		:raises TypeError:        If parameter ``sourceDirectories`` contains an element not of type :class:`~pathlib.Path`.
		"""
		super().__init__(name)

		self._root =              self
		self._sourceDirectories = []
		self._units =             {}

		if sourceDirectories is not None:
			if not isinstance(sourceDirectories, Iterable):
				ex = TypeError(f"Parameter 'sourceDirectories' is not iterable.")
				ex.add_note(f"Got type '{getFullyQualifiedName(sourceDirectories)}'.")
				raise ex

			for sourceDirectory in sourceDirectories:
				if not isinstance(sourceDirectory, Path):
					ex = TypeError(f"Parameter 'sourceDirectories' contains an element not of type 'Path'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(sourceDirectory)}'.")
					raise ex

				self._sourceDirectories.append(sourceDirectory)

	@Base.Parent.setter
	def Parent(self, parent: None) -> None:
		ex = TypeError(f"A '{getFullyQualifiedName(self)}' has no parent.")
		ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
		raise ex

	def _AddElement(self, element: Directory | File | Unit) -> None:
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
		Iterate the elements of the physical hierarchy, then those of the logical hierarchy.

		:returns: A generator of every element below the report's root.
		"""
		yield from super().IterateElements()
		for unit in self._units.values():
			yield unit
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

	The lines are a list indexed by line number: index 0 is unused, and a line the report doesn't list - a comment, a
	declaration - is ``None``. Lines are iterated in order, and looked up without hashing.
	"""

	_PARENT_TYPE: ClassVar[tuple[type, ...]] = (Directory, )  #: A file is in a directory.

	_lines:          list[Nullable[Line]]  #: The executable lines by line number; ``None`` at index 0 and for gaps.
	_lastLineNumber: int                   #: The last line number the report lists; ``0``, if it lists none.
	_units:          list[Unit]            #: The units naming this file, in the order they were added.

	def __init__(self, name: str, *, lines: Nullable[Iterable[Line]] = None, parent: Nullable[Directory] = None) -> None:
		"""
		Initialize a source file, and add it to its directory.

		:param name:               Name of the file.
		:param lines:              Optional, the executable lines. Default: ``None``.
		:param parent:             Optional, the directory containing the file. Default: ``None``.
		:raises TypeError:         If parameter ``parent`` isn't of type :class:`Directory`.
		:raises ValueError:        If parameter ``name`` is ``None``.
		:raises TypeError:         If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError:        If parameter ``name`` is empty.
		:raises CodeCoverageError: If the directory already contains a file or directory of this name.
		:raises TypeError:         If parameter ``lines`` isn't iterable.
		:raises TypeError:         If parameter ``lines`` contains an element not of type :class:`Line`.
		:raises CodeCoverageError: If two lines have the same number.
		"""
		super().__init__(name, parent=parent)

		self._units = []

		if parent is not None:
			parent._AddElement(self)

		if lines is None:
			self._lines =          [None]
			self._lastLineNumber = 0
		elif not isinstance(lines, Iterable):
			ex = TypeError(f"Parameter 'lines' is not iterable.")
			ex.add_note(f"Got type '{getFullyQualifiedName(lines)}'.")
			raise ex
		else:
			# check the lines and find the last line number, then allocate the list once at its final size
			lineList = []
			lastLineNumber = 0
			for line in lines:
				if not isinstance(line, Line):
					ex = TypeError(f"Parameter 'lines' contains an element not of type 'Line'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(line)}'.")
					raise ex

				lineList.append(line)
				if line._lineNumber > lastLineNumber:
					lastLineNumber = line._lineNumber

			fileLines = [None] * (lastLineNumber + 1)
			for line in lineList:
				lineNumber = line._lineNumber
				if fileLines[lineNumber] is not None:
					raise CodeCoverageError(f"Line {lineNumber} of file '{self.Path.as_posix()}' is added twice.")

				fileLines[lineNumber] = line
				line._parent = self
				line._root =   self._root
				for branch in line._branches:
					branch._root = self._root

			self._lines =          fileLines
			self._lastLineNumber = lastLineNumber

	def _AddElement(self, line: Line) -> None:
		"""
		Add a line, which names this file as its parent.

		:param line:               The line.
		:raises CodeCoverageError: If the file already has a line of this number.
		"""
		lineNumber = line._lineNumber
		if (gap := lineNumber - len(self._lines)) >= 0:
			if gap > 0:
				self._lines.extend([None] * gap)

			self._lines.append(line)
		elif self._lines[lineNumber] is None:
			self._lines[lineNumber] = line
		else:
			raise CodeCoverageError(f"Line {lineNumber} of file '{self.Path.as_posix()}' is added twice.")

		if lineNumber > self._lastLineNumber:
			self._lastLineNumber = lineNumber

	def IterateElements(self) -> Generator[Base, None, None]:
		"""
		Iterate the lines of this file, each followed by its branches.

		:returns: A generator of the elements below this file.
		"""
		for line in self.IterateLines():
			yield line
			yield from line.IterateElements()

	@readonly
	def Lines(self) -> list[Nullable[Line]]:
		"""
		Read-only property to access the executable lines (:attr:`_lines`).

		The list ends at the last line the report lists. To iterate only the listed lines, use :meth:`IterateLines`.

		:returns: The lines, indexed by line number; ``None`` for index 0 and for a line the report doesn't list.
		"""
		return self._lines

	@readonly
	def LastLineNumber(self) -> int:
		"""
		Read-only property to access the number of the last line the report lists (:attr:`_lastLineNumber`).

		:returns: The line number; ``0``, if the report lists no line.
		"""
		return self._lastLineNumber

	def GetLine(self, lineNumber: int) -> Nullable[Line]:
		"""
		Return the line of a line number.

		:param lineNumber:  The line number, counted from 1.
		:returns:           The line, or ``None`` if the report doesn't list it.
		:raises ValueError: If parameter ``lineNumber`` is ``None``.
		:raises TypeError:  If parameter ``lineNumber`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``lineNumber`` is less than 1.
		:raises ValueError: If parameter ``lineNumber`` is beyond the last line the report lists (:attr:`LastLineNumber`).
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
		elif lineNumber > self._lastLineNumber:
			ex = ValueError(f"Parameter 'lineNumber' is beyond the last line of file '{self.Path.as_posix()}'.")
			ex.add_note(f"Got value '{lineNumber}' for {self._lastLineNumber} lines.")
			raise ex from IndexError(f"Index {lineNumber} is out of range 1..{self._lastLineNumber}.")

		return self._lines[lineNumber]

	@readonly
	def Units(self) -> list[Unit]:
		"""
		Read-only property to access the units naming this file (:attr:`_units`), e.g. a module, its classes and functions.

		:returns: The units.
		"""
		return self._units

	def IterateLines(
		self,
		startLine: Nullable[Line] = None,
		endLine: Nullable[Line] = None
	) -> Generator[Line, None, None]:
		"""
		Iterate the executable lines of this file from a first to a last line, both included, by line number.

		:param startLine:   Optional, the first line. Default: ``None``, the file's first line.
		:param endLine:     Optional, the last line. Default: ``None``, the file's last line.
		:returns:           A generator of the lines.
		:raises TypeError:  If parameter ``startLine`` isn't of type :class:`Line`.
		:raises ValueError: If parameter ``startLine`` isn't a line of this file.
		:raises TypeError:  If parameter ``endLine`` isn't of type :class:`Line`.
		:raises ValueError: If parameter ``endLine`` isn't a line of this file.
		"""
		if startLine is None:
			first = 1
		elif not isinstance(startLine, Line):
			ex = TypeError(f"Parameter 'startLine' is not of type 'Line'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(startLine)}'.")
			raise ex
		elif startLine._parent is not self:
			raise ValueError(f"Parameter 'startLine' is not a line of file '{self.Path.as_posix()}'.")
		else:
			first = startLine._lineNumber

		if endLine is None:
			last = self._lastLineNumber
		elif not isinstance(endLine, Line):
			ex = TypeError(f"Parameter 'endLine' is not of type 'Line'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(endLine)}'.")
			raise ex
		elif endLine._parent is not self:
			raise ValueError(f"Parameter 'endLine' is not a line of file '{self.Path.as_posix()}'.")
		else:
			last = endLine._lineNumber

		for lineNumber in range(first, last + 1):
			if (line := self._lines[lineNumber]) is not None:
				yield line

	def Aggregate(self) -> None:
		"""
		Aggregate the file's lines, then compute the counters from them.
		"""
		lines = list(self.IterateLines())
		for line in lines:
			line.Aggregate()

		self._CountLines(lines)

	def __repr__(self) -> str:
		"""
		Return a representation of the file for debugging, e.g. ``<File src/Counter.vhdl: 80.0%>``.

		:returns: The file's path and line coverage.
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

	_lineNumber:      int           #: Line number, counted from 1.
	_branches:        list[Branch]  #: The branches starting at this line.
	_coveredBranches: int           #: Number of branches, which were taken; zero until :meth:`Aggregate` computed it.

	def __init__(
		self,
		lineNumber: int,
		status: LineCoverageStatus,
		coverageCount: Nullable[int] = None,
		branches: Nullable[Iterable[Branch]] = None,
		*,
		parent: Nullable[File] = None
	) -> None:
		"""
		Initialize a line's coverage, and add it to its file.

		:param lineNumber:         Line number, counted from 1.
		:param status:             Coverage state of the line.
		:param coverageCount:      Optional, how often the line ran, if the report says. Default: ``None``.
		:param branches:           Optional, the branches starting at this line. Default: ``None``.
		:param parent:             Optional, the file the line is in. Default: ``None``.
		:raises TypeError:         If parameter ``parent`` isn't of type :class:`File`.
		:raises ValueError:        If parameter ``status`` is ``None``.
		:raises TypeError:         If parameter ``status`` isn't of type :class:`LineCoverageStatus`.
		:raises TypeError:         If parameter ``coverageCount`` isn't of type :class:`int`.
		:raises ValueError:        If parameter ``coverageCount`` is negative.
		:raises ValueError:        If parameter ``coverageCount`` contradicts parameter ``status``.
		:raises ValueError:        If parameter ``lineNumber`` is ``None``.
		:raises TypeError:         If parameter ``lineNumber`` isn't of type :class:`int`.
		:raises ValueError:        If parameter ``lineNumber`` is less than 1.
		:raises CodeCoverageError: If the file already has a line of this number.
		:raises TypeError:         If parameter ``branches`` isn't iterable.
		:raises TypeError:         If parameter ``branches`` contains an element not of type :class:`Branch`.
		"""
		super().__init__(status, coverageCount, parent=parent)

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

		self._lineNumber =      lineNumber
		self._branches =        []
		self._coveredBranches = 0

		if parent is not None:
			parent._AddElement(self)

		if branches is not None:
			if not isinstance(branches, Iterable):
				ex = TypeError(f"Parameter 'branches' is not iterable.")
				ex.add_note(f"Got type '{getFullyQualifiedName(branches)}'.")
				raise ex

			for branch in branches:
				if not isinstance(branch, Branch):
					ex = TypeError(f"Parameter 'branches' contains an element not of type 'Branch'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(branch)}'.")
					raise ex

				branch._parent = self
				branch._root =   self._root
				self._branches.append(branch)

	def _AddElement(self, branch: Branch) -> None:
		"""
		Add a branch, which names this line as its parent.

		:param branch: The branch.
		"""
		self._branches.append(branch)

	def IterateElements(self) -> Generator[Base, None, None]:
		"""
		Iterate the branches of this line.

		:returns: A generator of the branches.
		"""
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
		Read-only property to access the number of this line's branches, which were taken (:attr:`_coveredBranches`).

		:returns: The number of branches with state :attr:`LineCoverageStatus.Covered`; zero until :meth:`Aggregate`
		          computed it.
		"""
		return self._coveredBranches

	def Aggregate(self) -> None:
		"""
		Compute the number of this line's branches, which were taken.
		"""
		self._coveredBranches = sum(1 for branch in self._branches if branch._status is LineCoverageStatus.Covered)

	def __repr__(self) -> str:
		"""
		Return a representation of the line's coverage for debugging, e.g. ``<Line 12: PartiallyCovered (1/2 branches)>``.

		:returns: The line number, the state and the branches.
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
		coverageCount: Nullable[int] = None,
		target: Nullable[Line] = None,
		*,
		parent: Nullable[Line] = None
	) -> None:
		"""
		Initialize a branch, and add it to its line.

		:param status:        Whether the branch was taken.
		:param coverageCount: Optional, how often the branch was taken, if the report says. Default: ``None``.
		:param target:        Optional, the line the branch goes to, if the report says; ``None`` for an exit of a function.
		                      Default: ``None``.
		:param parent:        Optional, the line the branch starts at. Default: ``None``.
		:raises TypeError:    If parameter ``parent`` isn't of type :class:`Line`.
		:raises ValueError:   If parameter ``status`` is ``None``.
		:raises TypeError:    If parameter ``status`` isn't of type :class:`LineCoverageStatus`.
		:raises TypeError:    If parameter ``coverageCount`` isn't of type :class:`int`.
		:raises ValueError:   If parameter ``coverageCount`` is negative.
		:raises ValueError:   If parameter ``coverageCount`` contradicts parameter ``status``.
		:raises TypeError:    If parameter ``target`` isn't of type :class:`Line`.
		"""
		super().__init__(status, coverageCount, parent=parent)

		if target is not None and not isinstance(target, Line):
			ex = TypeError(f"Parameter 'target' is not of type 'Line'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(target)}'.")
			raise ex

		self._target = target

		if parent is not None:
			parent._AddElement(self)

	def IterateElements(self) -> Generator[Base, None, None]:
		"""
		Iterate the elements below this branch: none, a branch is a leaf.

		:returns: An empty generator.
		"""
		yield from ()

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
	units it contains, and the lines it spans.

	Its parent is the :class:`Unit` containing it, or the report's :class:`CoverageSummary`. A unit spans the lines of
	its file from its first to its last line - a language construct wraps the constructs nested in it -, so the
	physical and the logical hierarchy count the same lines. A unit without lines, e.g. a package of several files,
	counts the lines of the units it contains, each line once.
	"""

	_PARENT_TYPE: ClassVar[tuple[type, ...]]  #: A unit is in a unit or the report's root; assigned below the class.

	_name:      str              #: Name of the unit.
	_units:     dict[str, Unit]  #: The units this one contains, by name.
	_file:      Nullable[File]   #: The source file the unit is in, if the report says.
	_startLine: Nullable[Line]   #: The unit's first line, if the report says.
	_endLine:   Nullable[Line]   #: The unit's last line, if the report says.

	def __init__(
		self,
		name: str,
		*,
		file: Nullable[File] = None,
		startLine: Nullable[Line] = None,
		endLine: Nullable[Line] = None,
		status: LineCoverageStatus = LineCoverageStatus.Unknown,
		coverageCount: Nullable[int] = None,
		parent: Nullable[Unit | CoverageSummary] = None
	) -> None:
		"""
		Initialize a unit, and add it to its file and to the unit or report containing it.

		:param name:               Name of the unit.
		:param file:               Optional, the source file the unit is in. Default: ``None``.
		:param startLine:          Optional, the unit's first line. Default: ``None``.
		:param endLine:            Optional, the unit's last line. Default: ``None``.
		:param status:             Optional, whether the unit was called. Default: :attr:`LineCoverageStatus.Unknown`.
		:param coverageCount:      Optional, how often the unit was called. Default: ``None``.
		:param parent:             Optional, the unit or report containing this unit. Default: ``None``.
		:raises TypeError:         If parameter ``parent`` isn't of type :class:`Unit` or :class:`CoverageSummary`.
		:raises ValueError:        If parameter ``status`` is ``None``.
		:raises TypeError:         If parameter ``status`` isn't of type :class:`LineCoverageStatus`.
		:raises TypeError:         If parameter ``coverageCount`` isn't of type :class:`int`.
		:raises ValueError:        If parameter ``coverageCount`` is negative.
		:raises ValueError:        If parameter ``coverageCount`` contradicts parameter ``status``.
		:raises ValueError:        If parameter ``name`` is ``None``.
		:raises TypeError:         If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError:        If parameter ``name`` is empty.
		:raises TypeError:         If parameter ``file`` isn't of type :class:`File`.
		:raises TypeError:         If parameter ``startLine`` isn't of type :class:`Line`.
		:raises ValueError:        If parameter ``startLine`` isn't a line of parameter ``file``.
		:raises TypeError:         If parameter ``endLine`` isn't of type :class:`Line`.
		:raises ValueError:        If parameter ``endLine`` isn't a line of parameter ``file``.
		:raises ValueError:        If parameter ``endLine`` is before parameter ``startLine``.
		:raises CodeCoverageError: If the parent already contains a unit of this name.
		"""
		super().__init__(status, coverageCount, parent=parent)
		CoverageCountersMixin.__init__(self)

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

		if startLine is not None:
			if not isinstance(startLine, Line):
				ex = TypeError(f"Parameter 'startLine' is not of type 'Line'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(startLine)}'.")
				raise ex
			elif startLine._parent is not file:
				raise ValueError(f"Parameter 'startLine' is not a line of parameter 'file'.")

		if endLine is not None:
			if not isinstance(endLine, Line):
				ex = TypeError(f"Parameter 'endLine' is not of type 'Line'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(endLine)}'.")
				raise ex
			elif endLine._parent is not file:
				raise ValueError(f"Parameter 'endLine' is not a line of parameter 'file'.")
			elif startLine is not None and endLine._lineNumber < startLine._lineNumber:
				ex = ValueError(f"Parameter 'endLine' is before parameter 'startLine'.")
				ex.add_note(f"Got lines {startLine._lineNumber} to {endLine._lineNumber}.")
				raise ex

		self._name =      name
		self._units =     {}
		self._file =      file
		self._startLine = startLine
		self._endLine =   endLine

		if parent is not None:
			parent._AddElement(self)

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
		Iterate the units this unit contains, each followed by the units below it.

		:returns: A generator of the units below this one.
		"""
		for unit in self._units.values():
			yield unit
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
		Read-only property to return the names of the units from the top down to this one, joined by ``.``, e.g.
		``myPackage.Shapes.Circle.Area``.

		:returns: The qualified name.
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

	def IterateLines(self) -> Generator[Line, None, None]:
		"""
		Iterate the executable lines of this unit's file from its first to its last line, both included.

		:returns: A generator of the lines; nothing, if the unit has no file, or no first or last line.
		"""
		if self._file is not None and self._startLine is not None and self._endLine is not None:
			yield from self._file.IterateLines(self._startLine, self._endLine)

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
		Aggregate the units this one contains, then compute the counters from the lines this unit spans.

		A unit without first and last line counts the lines the units below it span, each line once. The lines are
		aggregated by their files - :meth:`CoverageSummary.Aggregate` does that first.
		"""
		for unit in self._units.values():
			unit.Aggregate()

		if self._startLine is not None and self._endLine is not None:
			self._CountLines(self.IterateLines())
		else:
			lines: dict[int, Line] = {}
			for unit in self.IterateUnits():
				lines.update((id(line), line) for line in unit.IterateLines())

			self._CountLines(lines.values())

	def __repr__(self) -> str:
		"""
		Return a representation of the unit for debugging, e.g. ``<Function Shapes.Circle.Area: 100.0%>``.

		:returns: The unit's kind, qualified name and line coverage.
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
@abstractclass
class Document(metaclass=ExtendedType, slots=True):
	"""
	A code coverage report file, which is read in two steps: analyzed, then converted.

	A format's document derives from this class and mixes in the root of the format's model.
	"""

	_path:               Path   #: Path to the report file.
	_analysisDuration:   float  #: Duration of :meth:`Analyze` in seconds, or ``-1.0`` before it ran.
	_conversionDuration: float  #: Duration of :meth:`Convert` in seconds, or ``-1.0`` before it ran.

	def __init__(self, reportFile: Path) -> None:
		"""
		Initialize the report file.

		:param reportFile: Path to the report file.
		"""
		self._path = reportFile

		self._analysisDuration =   -1.0
		self._conversionDuration = -1.0

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
