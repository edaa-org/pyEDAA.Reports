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
Abstract data model of documentation coverage, the common model every language's reader fills.

The model has two hierarchies over the same documentable items:

* The **physical** hierarchy - :class:`DocumentationReport`, :class:`Directory` and :class:`File` - is built from the
  source files a reader analyzed. A file counts the items declared in it; a directory sums its directories and files.
* The **logical** hierarchy holds the documentable items of a language - :class:`Item` -, each with its kind, its
  documentation state, its source file and lines, and the items it contains. The report holds its top-level items too.

An item - a package, a class, a method, a field, a VHDL entity, ... - names the source file it is declared in and its
first and last line, where the reader knows them.

An item's :class:`ItemKind` names the language construct, e.g. a class, a method or a VHDL entity. Each kind belongs to
an :class:`ItemCategory` shared by all languages - containers, types, callables, fields, variables, parameters -, so
the counters can be broken down the same way for every language.

An item's :class:`CoverageState` says, whether it is documented, and whether it is expected to be. The counters
(:class:`CoverageCounters`) of an item, a file, a directory or the whole analysis are computed from these states by
``Aggregate()``.

.. seealso::

   :mod:`pyEDAA.Reports.DocumentationCoverage.Python`
      |rarr| The reader of Python source files.
   :mod:`pyEDAA.Reports.DocumentationCoverage.DocStrCoverage`
      |rarr| The converter of docstr_coverage's analysis.
"""
from __future__            import annotations

from datetime              import timedelta
from enum                  import Flag
from pathlib               import Path
from typing                import Callable, ClassVar, Generator, Iterator, Optional as Nullable

from pyTooling.Common      import getFullyQualifiedName, StringEnum
from pyTooling.Decorators  import export, readonly
from pyTooling.MetaClasses import ExtendedType, abstractmethod
from pyTooling.Warning     import CriticalWarning

from pyEDAA.Reports        import ReportException


@export
class DocCoverageError(ReportException):
	"""Base-exception of the documentation coverage data model and its readers."""


@export
class SourceFileWarning(CriticalWarning):
	"""
	A source file can't be analyzed: it can't be read, decoded or parsed.

	The reader excludes the file's item from the analysis, and continues with the next file. The cause is the exception
	reading, decoding or parsing raised.

	.. important::

	   This warning is critical: it must be collected by a :class:`~pyTooling.Warning.WarningCollector` up the
	   call-hierarchy, otherwise :meth:`~pyTooling.Warning.WarningCollector.Raise` raises an
	   :exc:`~pyTooling.Warning.UnhandledCriticalWarningError`.
	"""


@export
class CoverageState(Flag):
	"""
	The documentation state of an item, as flags.

	:class:`CoverageCounters` counts an item by the first of these flags it has:

	* :attr:`Empty`: not counted.
	* :attr:`Excluded`: counted as excluded.
	* :attr:`Ignored`: counted as ignored.
	* :attr:`Covered`: counted as expected and covered.
	* None of them: counted as expected and uncovered.
	"""

	Unknown =      0      #: No state; an item can't have it.
	Excluded =     1      #: Excluded from the analysis, e.g. by a name pattern.
	Ignored =      2      #: Needs no documentation by the reader's rules, e.g. a property's setter.
	Empty =        4      #: Has nothing to document, e.g. an empty module; not counted.
	Covered =      8      #: Counts as documented.

	Weak =         16     #: Documented, but too briefly.
	Incomplete =   32     #: Documented, but not every part of it.
	Inherited =    64     #: Undocumented, but takes the documentation of what it overrides, as a comment states.
	Detailed =     128    #: Documented in detail.

	Undocumented = 256    #: Has no documentation.
	Documented =   512    #: Has documentation.

	Parameters =   1024   #: Its parameters are documented.
	ReturnValue =  2048   #: Its return value is documented.
	Exceptions =   8192   #: The exceptions it raises are documented.
	Types =        16384  #: Its types are documented.

	Excused =      32768  #: Undocumented, but a comment excuses the missing documentation.


@export
class ItemCategory(StringEnum):
	"""
	The category of a documentable item, shared by all languages.

	Each :class:`ItemKind` belongs to one category (:attr:`ItemKind.Category`), so the counters of every language break
	down the same way.
	"""

	Container = "container"  #: Contains other items, e.g. a package, a module, a namespace or a VHDL entity.
	Type =      "type"       #: Declares a type, e.g. a class, a struct, an enumeration or a type alias.
	Callable =  "callable"   #: Can be called, e.g. a function, a method, a procedure or a property.
	Field =     "field"      #: Data of a type, e.g. a class' field, a record's element or an enumeration's member.
	Variable =  "variable"   #: Data of a container, whose value can change, e.g. a module's variable or a VHDL signal.
	Constant =  "constant"   #: Data of a container, whose value can't change, e.g. a constant of C or VHDL.
	Generic =   "generic"    #: A compile-time parameter, e.g. a VHDL generic or a C++ template parameter.
	Parameter = "parameter"  #: A run-time parameter declared as an item of its own, e.g. a VHDL port.
	Other =     "other"      #: Belongs to no other category.

	DEFAULT =   Other        #: The category of an item, which belongs to no other category.


@export
class ItemKind(StringEnum):
	"""
	The kind of a documentable item: the language construct it is.

	Languages share a kind, where they share the construct, e.g. a package of Python, Java and Go. A construct only one
	language has, has a kind of its own, e.g. a VHDL entity. Each kind belongs to an :class:`ItemCategory`
	(:attr:`Category`).
	"""

	Library =           "library"             #: A library of design units, e.g. a VHDL library.
	Package =           "package"             #: A package, e.g. of Python, Java or Go, or a VHDL package.
	PackageBody =       "package-body"        #: The body of a VHDL package.
	Namespace =         "namespace"           #: A namespace, e.g. of C++ or TCL.
	Module =            "module"              #: A module, e.g. a Python module.
	SourceFile =        "source-file"         #: A source file, where the file is the language's unit, e.g. in C.
	Entity =            "entity"              #: A VHDL entity.
	Architecture =      "architecture"        #: A VHDL architecture.
	Configuration =     "configuration"       #: A VHDL configuration.
	Context =           "context"             #: A VHDL context.

	Class =             "class"               #: A class.
	Struct =            "struct"              #: A structure, e.g. of C, C++ or Go.
	Union =             "union"               #: A union of C or C++.
	Interface =         "interface"           #: An interface, e.g. of Java or Go.
	Enumeration =       "enumeration"         #: An enumeration.
	Record =            "record"              #: A record, e.g. of Java or a VHDL record type.
	Type =              "type"                #: Any other type declaration, e.g. a VHDL type or subtype.
	TypeAlias =         "type-alias"          #: A type alias, e.g. a C ``typedef`` or Python's ``type`` statement.
	TypeVariable =      "type-variable"       #: A type variable, e.g. Python's ``TypeVar``.
	Component =         "component"           #: A VHDL component declaration.

	Function =          "function"            #: A function.
	Method =            "method"              #: A method of a type.
	Constructor =       "constructor"         #: A type's constructor, e.g. Python's ``__init__``.
	Destructor =        "destructor"          #: A type's destructor, e.g. of C++, or Python's ``__del__``.
	Property =          "property"            #: A property: a method accessed like a field.
	Procedure =         "procedure"           #: A procedure, e.g. of VHDL or TCL.
	Macro =             "macro"               #: A preprocessor macro, e.g. of C.
	Process =           "process"             #: A VHDL process.

	Field =             "field"               #: A field of a type, e.g. a class' field or a record's element.
	EnumerationMember = "enumeration-member"  #: A member of an enumeration.

	Variable =          "variable"            #: A variable of a container, e.g. a module's variable.
	Signal =            "signal"              #: A VHDL signal.
	FileObject =        "file-object"         #: A file object, e.g. declared by a VHDL file declaration.
	Constant =          "constant"            #: A constant.

	Generic =           "generic"             #: A VHDL generic.
	TypeParameter =     "type-parameter"      #: A type parameter, e.g. of a C++ template or a Java generic class.
	Parameter =         "parameter"           #: A parameter declared as an item of its own, e.g. of a VHDL subprogram.
	Port =              "port"                #: A VHDL port.

	Alias =             "alias"               #: An alias, e.g. a VHDL alias declaration.
	Attribute =         "attribute"           #: A VHDL attribute declaration.
	Other =             "other"               #: Any other documentable item.

	DEFAULT =           Other                 #: The kind of an item, which is no other kind.

	__CATEGORIES: ClassVar[dict[str, ItemCategory]] = {
		Library:           ItemCategory.Container,
		Package:           ItemCategory.Container,
		PackageBody:       ItemCategory.Container,
		Namespace:         ItemCategory.Container,
		Module:            ItemCategory.Container,
		SourceFile:        ItemCategory.Container,
		Entity:            ItemCategory.Container,
		Architecture:      ItemCategory.Container,
		Configuration:     ItemCategory.Container,
		Context:           ItemCategory.Container,
		Class:             ItemCategory.Type,
		Struct:            ItemCategory.Type,
		Union:             ItemCategory.Type,
		Interface:         ItemCategory.Type,
		Enumeration:       ItemCategory.Type,
		Record:            ItemCategory.Type,
		Type:              ItemCategory.Type,
		TypeAlias:         ItemCategory.Type,
		TypeVariable:      ItemCategory.Type,
		Component:         ItemCategory.Type,
		Function:          ItemCategory.Callable,
		Method:            ItemCategory.Callable,
		Constructor:       ItemCategory.Callable,
		Destructor:        ItemCategory.Callable,
		Property:          ItemCategory.Callable,
		Procedure:         ItemCategory.Callable,
		Macro:             ItemCategory.Callable,
		Process:           ItemCategory.Callable,
		Field:             ItemCategory.Field,
		EnumerationMember: ItemCategory.Field,
		Variable:          ItemCategory.Variable,
		Signal:            ItemCategory.Variable,
		FileObject:        ItemCategory.Variable,
		Constant:          ItemCategory.Constant,
		Generic:           ItemCategory.Generic,
		TypeParameter:     ItemCategory.Generic,
		Parameter:         ItemCategory.Parameter,
		Port:              ItemCategory.Parameter,
		Alias:             ItemCategory.Other,
		Attribute:         ItemCategory.Other,
		Other:             ItemCategory.Other,
	}  #: The category of each kind, by the kind's value.

	@readonly
	def Category(self) -> ItemCategory:
		"""
		Read-only property to return the category this kind belongs to.

		:returns: The kind's category.
		"""
		return self.__CATEGORIES[self]


@export
class CoverageCounters(metaclass=ExtendedType, slots=True):
	"""
	The numbers of documentable items by their coverage state, and the coverage computed from them.

	* An item is *expected* to be documented, unless it is *ignored* or *excluded*; an item without anything to document
	  (:attr:`CoverageState.Empty`) isn't counted at all.
	* An expected item is either *covered* or *uncovered*.

	.. code-block:: text

	   total    = expected + ignored + excluded
	   expected = covered + uncovered
	   coverage = covered / expected
	"""

	_expected: int  #: Number of items expected to be documented.
	_covered:  int  #: Number of expected items, which count as documented.
	_ignored:  int  #: Number of items, which need no documentation by the reader's rules.
	_excluded: int  #: Number of items excluded from the analysis.

	def __init__(self) -> None:
		"""
		Initializes counters of zero items.
		"""
		self._expected = 0
		self._covered =  0
		self._ignored =  0
		self._excluded = 0

	@readonly
	def Total(self) -> int:
		"""
		Read-only property to return the number of counted items.

		:returns: The sum of expected, ignored and excluded items.
		"""
		return self._expected + self._ignored + self._excluded

	@readonly
	def Expected(self) -> int:
		"""
		Read-only property to access the number of items expected to be documented (:attr:`_expected`).

		:returns: The number of expected items.
		"""
		return self._expected

	@readonly
	def Covered(self) -> int:
		"""
		Read-only property to access the number of expected items, which count as documented (:attr:`_covered`).

		:returns: The number of covered items.
		"""
		return self._covered

	@readonly
	def Uncovered(self) -> int:
		"""
		Read-only property to return the number of expected items, which don't count as documented.

		:returns: :attr:`Expected` minus :attr:`Covered`.
		"""
		return self._expected - self._covered

	@readonly
	def Ignored(self) -> int:
		"""
		Read-only property to access the number of items, which need no documentation by the reader's rules
		(:attr:`_ignored`).

		:returns: The number of ignored items.
		"""
		return self._ignored

	@readonly
	def Excluded(self) -> int:
		"""
		Read-only property to access the number of items excluded from the analysis (:attr:`_excluded`).

		:returns: The number of excluded items.
		"""
		return self._excluded

	@readonly
	def Coverage(self) -> float:
		"""
		Read-only property to return the documentation coverage: the ratio of covered to expected items.

		:returns: The coverage in range 0.0..1.0; ``1.0`` if no item is expected.
		"""
		return 1.0 if self._expected == 0 else self._covered / self._expected

	def _Count(self, status: CoverageState) -> None:
		"""
		Count one item of a coverage state.

		:param status: The item's coverage state.
		"""
		if CoverageState.Empty in status:
			return
		elif CoverageState.Excluded in status:
			self._excluded += 1
		elif CoverageState.Ignored in status:
			self._ignored += 1
		else:
			self._expected += 1
			if CoverageState.Covered in status:
				self._covered += 1

	def _Add(self, other: CoverageCounters) -> None:
		"""
		Add the numbers of other counters to these.

		:param other: The other counters.
		"""
		self._expected += other._expected
		self._covered +=  other._covered
		self._ignored +=  other._ignored
		self._excluded += other._excluded

	def __repr__(self) -> str:
		"""
		Return a representation of the counters for debugging.

		Counters of 3 covered out of 4 expected items, 1 ignored item and no excluded item read
		``<CoverageCounters 3/4, ignored 1, excluded 0: 75.0%>``.

		:returns: The covered, expected, ignored and excluded items and the coverage.
		"""
		return (
			f"<CoverageCounters {self._covered}/{self._expected}, ignored {self._ignored}, excluded {self._excluded}: "
			f"{self.Coverage:.1%}>"
		)


@export
class Base(metaclass=ExtendedType, slots=True):
	"""
	Base-class of every element of the documentation coverage model: a reference to the element containing it and to
	the analysis' root, and the counters computed by :meth:`Aggregate`.
	"""

	_PARENT_TYPE: ClassVar[tuple[type, ...]]  #: The types a parent may have; assigned by each class having a parent.

	_parent:     Nullable[Base]                        #: The element containing this one, or ``None``.
	_root:       Nullable[DocumentationReport]         #: The report, or ``None`` while the element isn't part of one.
	_counters:   CoverageCounters                      #: The counters of the items this element counts.
	_categories: dict[ItemCategory, CoverageCounters]  #: The counters per category of the items.

	def __init__(self, *, parent: Nullable[Base] = None) -> None:
		"""
		Initializes an element with its parent, the parent's root, and counters of zero items.

		The parent doesn't list the element yet: the class setting the field the parent stores it by - a name - adds it
		with ``parent._AddElement(self)``.

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

		self._counters =   CoverageCounters()
		self._categories = {}

	@property
	def Parent(self) -> Nullable[Base]:
		"""
		Property to access the element containing this one (:attr:`_parent`).

		Assigning a parent adds this element to it, and sets the parent's root as the root of this element and of every
		element below it.

		:returns:                 The parent, or ``None``.
		:raises ValueError:       If ``None`` is assigned.
		:raises TypeError:        If the assigned parent isn't of a type this class declares in :attr:`_PARENT_TYPE`.
		:raises TypeError:        If a parent is assigned to a :class:`DocumentationReport`, which has no parent.
		:raises DocCoverageError: If the assigned parent is a directory, which already contains an element of this name.
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
		self._SetRoot(parent._root)

	@readonly
	def Root(self) -> Nullable[DocumentationReport]:
		"""
		Read-only property to access the analysis' root (:attr:`_root`).

		The root is maintained by :attr:`Parent`: assigning a parent sets it for this element and every element below it.

		:returns: The root, or ``None`` while the element isn't part of an analysis.
		"""
		return self._root

	@readonly
	def Counters(self) -> CoverageCounters:
		"""
		Read-only property to access the counters of the items this element counts (:attr:`_counters`).

		They are zero until :meth:`Aggregate` computed them.

		:returns: The counters.
		"""
		return self._counters

	@readonly
	def Categories(self) -> dict[ItemCategory, CoverageCounters]:
		"""
		Read-only property to access the counters per category of the items this element counts (:attr:`_categories`).

		A category without items has no entry. The counters are computed by :meth:`Aggregate`.

		:returns: The counters, by category.
		"""
		return self._categories

	def _ResetCounters(self) -> None:
		"""
		Set the counters to zero items.
		"""
		self._counters =   CoverageCounters()
		self._categories = {}

	def _CountItem(self, item: Item) -> None:
		"""
		Count an item's own coverage state, in the counters and in the counters of its category.

		:param item: The item.
		"""
		self._counters._Count(item._status)
		category = item._kind.Category
		if (counters := self._categories.get(category, None)) is None:
			counters = CoverageCounters()
			self._categories[category] = counters

		counters._Count(item._status)

	def _AddCounters(self, other: Base) -> None:
		"""
		Add the counters of another element to this one's.

		:param other: The other element, aggregated.
		"""
		self._counters._Add(other._counters)
		for category, otherCounters in other._categories.items():
			if (counters := self._categories.get(category, None)) is None:
				counters = CoverageCounters()
				self._categories[category] = counters

			counters._Add(otherCounters)

	def _SetRoot(self, root: Nullable[DocumentationReport]) -> None:
		"""
		Set the analysis' root of this element.

		A class containing elements overrides it, to set the root of those too.

		:param root: The root, or ``None`` while the element isn't part of an analysis.
		"""
		self._root = root

	@abstractmethod
	def Aggregate(self) -> None:
		"""
		Compute the counters.
		"""


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

	def _SetRoot(self, root: Nullable[DocumentationReport]) -> None:
		"""
		Set the analysis' root of this directory, and of the directories and files below it.

		:param root: The root, or ``None`` while the directory isn't part of an analysis.
		"""
		self._root = root
		for directory in self._directories.values():
			directory._SetRoot(root)

		for file in self._files.values():
			file._SetRoot(root)

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

		Names are compared case-sensitively on every platform.

		:returns: A generator of the files.
		"""
		for name in sorted(self._files, key=Path.as_posix):
			yield self._files[name]

		for name in sorted(self._directories, key=Path.as_posix):
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


# A class with a property named like a class - ``File`` - can't name that class in the annotation of a field: the class
# body's namespace, where annotations are evaluated, binds the name to the property.
_File = File


@export
class Item(Base):
	"""
	A documentable item of a language, its coverage state, and the items it contains.

	Its parent is the :class:`Item` containing it, or the :class:`DocumentationReport` for a top-level item. Items of one
	parent may share a name, e.g. a property's getter and setter.

	A container's own documentation - a module's or a class' doc-string - is the container's own coverage state; the
	items it contains have states of their own. So an item's counters count the item itself and every item below it.
	"""

	_PARENT_TYPE: ClassVar[tuple[type, ...]]  #: An item is in an item or the report; assigned below the class.

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
		parent: Nullable[Item | DocumentationReport] = None
	) -> None:
		"""
		Initializes an item, and adds it to its file and to the item or report containing it.

		:param name:        Name of the item.
		:param kind:        The language construct the item is.
		:param status:      The item's own coverage state.
		:param file:        Optional, the source file the item is declared in. Default: ``None``.
		:param startLine:   Optional, the item's first line. Default: ``None``.
		:param endLine:     Optional, the item's last line. Default: ``None``.
		:param parent:      Optional, the item or report containing this item. Default: ``None``.
		:raises TypeError:  If parameter ``parent`` isn't of type :class:`Item` or :class:`DocumentationReport`.
		:raises ValueError: If parameter ``name`` is ``None``.
		:raises TypeError:  If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError: If parameter ``name`` is empty.
		:raises ValueError: If parameter ``kind`` is ``None``.
		:raises TypeError:  If parameter ``kind`` isn't of type :class:`ItemKind`.
		:raises ValueError: If parameter ``status`` is ``None``.
		:raises TypeError:  If parameter ``status`` isn't of type :class:`CoverageState`.
		:raises ValueError: If parameter ``status`` is ``CoverageState.Unknown``.
		:raises TypeError:  If parameter ``file`` isn't of type :class:`File`.
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

	def _SetRoot(self, root: Nullable[DocumentationReport]) -> None:
		"""
		Set the analysis' root of this item, and of the items below it.

		:param root: The root, or ``None`` while the item isn't part of an analysis.
		"""
		self._root = root
		for item in self._items:
			item._SetRoot(root)

	def IterateDescendants(self, predicate: Nullable[Callable[[Item], bool]] = None) -> Generator[Item, None, None]:
		"""
		Iterate all or selected items below this one - the items it contains, theirs, ... -, depth-first: each item
		followed by the items below it.

		If parameter ``predicate`` is not None, the given filter function is used to skip items in the generator. A skipped
		item's items are still iterated.

		:param predicate: Optional, filter function accepting an item and returning a boolean. Default: ``None``.
		:returns:         A generator of the items below this one.
		"""
		if predicate is None:
			for item in self._items:
				yield item
				yield from item.IterateDescendants()
		else:
			for item in self._items:
				if predicate(item):
					yield item

				yield from item.IterateDescendants(predicate)

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
		Read-only property to access the category of the item's kind (:attr:`_kind`).

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


Item._PARENT_TYPE = (Item, DocumentationReport)
