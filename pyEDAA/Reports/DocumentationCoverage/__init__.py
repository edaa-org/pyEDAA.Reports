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

* The **physical** hierarchy - :class:`~pyEDAA.Reports.DocumentationCoverage.Files.DocumentationReport`,
  :class:`~pyEDAA.Reports.DocumentationCoverage.Files.Directory` and
  :class:`~pyEDAA.Reports.DocumentationCoverage.Files.File` - is built from the source files a reader analyzed. A file
  counts the items declared in it.
* The **logical** hierarchy holds the documentable items of a language -
  :class:`~pyEDAA.Reports.DocumentationCoverage.Items.Item` -, each with its kind, its documentation state, its source
  file and lines, and the items it contains.

An item's :class:`ItemKind` names the language construct, e.g. a class, a method or a VHDL entity. Each kind belongs to
an :class:`ItemCategory` shared by all languages - containers, types, callables, fields, variables, parameters -, so
the counters can be broken down the same way for every language.

An item's :class:`CoverageState` says, whether it is documented, and whether it is expected to be. The counters
(:class:`CoverageCounters`) of an item, a file, a directory or the whole analysis are computed from these states by
``Aggregate()``.

.. seealso::

   :mod:`pyEDAA.Reports.DocumentationCoverage.Files`
      |rarr| The physical hierarchy: the analysis' root, directories and source files.
   :mod:`pyEDAA.Reports.DocumentationCoverage.Items`
      |rarr| The logical hierarchy: the documentable items.
   :mod:`pyEDAA.Reports.DocumentationCoverage.Python`
      |rarr| The reader of Python source files.
   :mod:`pyEDAA.Reports.DocumentationCoverage.DocStrCoverage`
      |rarr| The converter of docstr_coverage's analysis.
"""
from __future__                                   import annotations

from enum                                         import Flag
from typing                                       import TYPE_CHECKING, ClassVar, Generator, Optional as Nullable

from pyTooling.Common                             import getFullyQualifiedName, StringEnum
from pyTooling.Decorators                         import export, readonly
from pyTooling.MetaClasses                        import ExtendedType, abstractmethod
from pyTooling.Warning                            import CriticalWarning

from pyEDAA.Reports                               import ReportException

if TYPE_CHECKING:  # pragma: no cover
	from pyEDAA.Reports.DocumentationCoverage.Files import DocumentationReport
	from pyEDAA.Reports.DocumentationCoverage.Items import Item


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
		:raises TypeError:        If a parent is assigned to a
		                          :class:`~pyEDAA.Reports.DocumentationCoverage.Files.DocumentationReport`, which has no
		                          parent.
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
		self._root =   parent._root
		for element in self.IterateElements():
			element._root = parent._root

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

	@abstractmethod
	def IterateElements(self) -> Generator[Base, None, None]:
		"""
		Iterate every element below this one, depth-first.

		:returns: A generator of the elements below this one.
		"""

	@abstractmethod
	def Aggregate(self) -> None:
		"""
		Compute the counters.
		"""
