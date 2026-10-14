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
#   Artur Porebski (Aldec Inc.)                                                                                        #
#   Michal Pacula  (Aldec Inc.)                                                                                        #
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
The scopes of Aldec's UCDB XML format and their bins.

The scopes are the design units and their instances; the bins are the coverage items - e.g. statements and branches -
with their counts, and where they are in the sources.
"""
from __future__                                      import annotations

from enum                                            import IntFlag
from pathlib                                         import Path
from typing                                          import TYPE_CHECKING, Generator, Generic, Mapping
from typing                                          import Optional as Nullable, Self, TypeVar

from lxml.etree                                      import _Element
from pyTooling.Common                                import getFullyQualifiedName
from pyTooling.Decorators                            import export, readonly
from pyTooling.MetaClasses                           import ExtendedType

from pyEDAA.Reports.CodeCoverage.AldecUCDB.Elements  import AttributesMixin, Base, CoverType, Language, NAMESPACES
from pyEDAA.Reports.CodeCoverage.AldecUCDB.Elements  import ScopeType

if TYPE_CHECKING:
	from pyEDAA.Reports.CodeCoverage.AldecUCDB       import Report


__all__ = ["ScopeParentType"]

# A class with a property named like a class - ``Language`` - can't name that class in the annotation of a field: the
# class body's namespace, where annotations are evaluated, binds the name to the property.
_Language = Language

ScopeParentType = TypeVar("ScopeParentType", bound="Report | Scope")
"""A type variable for the parent of a :class:`Scope`: a :class:`~pyEDAA.Reports.CodeCoverage.AldecUCDB.Report` or a
:class:`Scope`."""


@export
class BinFlags(IntFlag):
	"""
	Flags of a ``<ux:bin>``, as its ``flags`` state in hexadecimal; a flag not named here is kept.
	"""

	Is32Bit =         0x00000001  #: The count is a 32-bit number.
	Is64Bit =         0x00000002  #: The count is a 64-bit number.
	IsVector =        0x00000004  #: The bin is a vector of counts.
	HasGoal =         0x00000008  #: The bin states a goal.
	HasWeight =       0x00000010  #: The bin states a weight.
	ExcludePragma =   0x00000020  #: Excluded by a pragma in the source.
	ExcludeFile =     0x00000040  #: Excluded by an exclusion file.
	ExcludeInstance = 0x00000080  #: Excluded in this instance.
	ExcludeAuto =     0x00000100  #: Excluded automatically by the tool.
	HasLimit =        0x00000400  #: The count saturates at a limit.
	HasCount =        0x00000800  #: The bin states a count.
	IsCovered =       0x00001000  #: The bin reached its goal.

	Excluded =        0x000001E0  #: Any of the exclusion flags.


@export
class SourceLocation(metaclass=ExtendedType, slots=True):
	"""
	A ``<ux:src>`` of a scope or bin: the source file, the directory its name is relative to, the line and the token.

	It is a value, as a path is: it names no parent.
	"""

	_file:          Path  #: Path of the source file, relative to :attr:`_workDirectory`, if not absolute.
	_workDirectory: Path  #: The directory the tool ran in.
	_lineNumber:    int   #: Line number, counted from 1; ``0`` for a scope without a line.
	_token:         int   #: Number of the token in the line.

	def __init__(self, file: Path, workDirectory: Path, lineNumber: int, token: int) -> None:
		"""
		Initialize the source location.

		:param file:          Path of the source file, e.g. ``src/counter.sv``.
		:param workDirectory: The directory the tool ran in.
		:param lineNumber:    Line number, counted from 1; ``0`` for a scope without a line.
		:param token:         Number of the token in the line.
		:raises ValueError:   If parameter ``file`` is ``None``.
		:raises TypeError:    If parameter ``file`` isn't of type :class:`~pathlib.Path`.
		:raises ValueError:   If parameter ``workDirectory`` is ``None``.
		:raises TypeError:    If parameter ``workDirectory`` isn't of type :class:`~pathlib.Path`.
		:raises ValueError:   If parameter ``lineNumber`` is ``None``.
		:raises TypeError:    If parameter ``lineNumber`` isn't of type :class:`int`.
		:raises ValueError:   If parameter ``lineNumber`` is negative.
		:raises ValueError:   If parameter ``token`` is ``None``.
		:raises TypeError:    If parameter ``token`` isn't of type :class:`int`.
		:raises ValueError:   If parameter ``token`` is negative.
		"""
		if file is None:
			raise ValueError(f"Parameter 'file' is None.")
		elif not isinstance(file, Path):
			ex = TypeError(f"Parameter 'file' is not of type 'Path'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(file)}'.")
			raise ex

		if workDirectory is None:
			raise ValueError(f"Parameter 'workDirectory' is None.")
		elif not isinstance(workDirectory, Path):
			ex = TypeError(f"Parameter 'workDirectory' is not of type 'Path'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(workDirectory)}'.")
			raise ex

		if lineNumber is None:
			raise ValueError(f"Parameter 'lineNumber' is None.")
		elif not isinstance(lineNumber, int):
			ex = TypeError(f"Parameter 'lineNumber' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(lineNumber)}'.")
			raise ex
		elif lineNumber < 0:
			ex = ValueError(f"Parameter 'lineNumber' is negative.")
			ex.add_note(f"Got value '{lineNumber}'.")
			raise ex

		if token is None:
			raise ValueError(f"Parameter 'token' is None.")
		elif not isinstance(token, int):
			ex = TypeError(f"Parameter 'token' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(token)}'.")
			raise ex
		elif token < 0:
			ex = ValueError(f"Parameter 'token' is negative.")
			ex.add_note(f"Got value '{token}'.")
			raise ex

		self._file =          file
		self._workDirectory = workDirectory
		self._lineNumber =    lineNumber
		self._token =         token

	@classmethod
	def Parse(cls, element: _Element) -> Self:
		"""
		Parse a source location from its ``<ux:src>`` element.

		:param element: The ``<ux:src>`` element.
		:returns:       The source location.
		"""
		return cls(
			Path(element.attrib["file"]),
			Path(element.attrib["workdir"]),
			int(element.attrib["line"]),
			int(element.attrib["token"])
		)

	@readonly
	def File(self) -> Path:
		"""
		Read-only property to access the path of the source file (:attr:`_file`).

		:returns: The path, relative to :attr:`WorkDirectory`, if not absolute.
		"""
		return self._file

	@readonly
	def WorkDirectory(self) -> Path:
		"""
		Read-only property to access the directory the tool ran in (:attr:`_workDirectory`).

		It is a path on the machine the coverage was measured on, so it may not exist where the report is read.

		:returns: The directory.
		"""
		return self._workDirectory

	@readonly
	def LineNumber(self) -> int:
		"""
		Read-only property to access the line number (:attr:`_lineNumber`).

		:returns: The line number, counted from 1; ``0`` for a scope without a line.
		"""
		return self._lineNumber

	@readonly
	def Token(self) -> int:
		"""
		Read-only property to access the number of the token in the line (:attr:`_token`).

		:returns: The token's number.
		"""
		return self._token


@export
class Bin(Base, AttributesMixin):
	"""
	A ``<ux:bin>`` of a scope: a coverage item, how often it was hit, its flags, and where it is in the sources.

	Statements and branches are coverage items.
	"""

	_parent: Nullable[Scope]  #: The scope the bin belongs to.
	_type:   CoverType        #: Kind of the bin.
	_flags:  BinFlags         #: Flags of the bin, e.g. whether it is excluded.
	_count:  int              #: How often the coverage item was hit.
	_source: SourceLocation   #: Where the coverage item is in the sources.

	def __init__(
		self,
		name: str,
		coverType: CoverType,
		flags: BinFlags,
		count: int,
		source: SourceLocation,
		attributes: Nullable[Mapping[str, int | float | str]] = None,
		*,
		parent: Nullable[Scope] = None
	) -> None:
		"""
		Initialize the bin, and append it to the bins of its scope.

		:param name:        Name of the bin, e.g. ``true_branch``; empty for a statement.
		:param coverType:   Kind of the bin.
		:param flags:       Flags of the bin.
		:param count:       How often the coverage item was hit.
		:param source:      Where the coverage item is in the sources.
		:param attributes:  Optional, the attributes by key, e.g. ``{"#SINDEX#": 1}``. Default: ``None``.
		:param parent:      Optional, the scope the bin belongs to; the bin is appended to its bins. Default: ``None``.
		:raises ValueError: If parameter ``name`` is ``None``.
		:raises TypeError:  If parameter ``name`` isn't of type :class:`str`.
		:raises TypeError:  If parameter ``attributes`` isn't a mapping.
		:raises TypeError:  If parameter ``attributes`` contains a key not of type :class:`str`.
		:raises ValueError: If parameter ``attributes`` contains an empty key.
		:raises TypeError:  If parameter ``attributes`` contains a value not of type :class:`int`, :class:`float` or
		                    :class:`str`.
		:raises ValueError: If parameter ``coverType`` is ``None``.
		:raises TypeError:  If parameter ``coverType`` isn't of type
		                    :class:`~pyEDAA.Reports.CodeCoverage.AldecUCDB.Elements.CoverType`.
		:raises ValueError: If parameter ``flags`` is ``None``.
		:raises TypeError:  If parameter ``flags`` isn't of type :class:`BinFlags`.
		:raises ValueError: If parameter ``count`` is ``None``.
		:raises TypeError:  If parameter ``count`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``count`` is negative.
		:raises ValueError: If parameter ``source`` is ``None``.
		:raises TypeError:  If parameter ``source`` isn't of type :class:`SourceLocation`.
		:raises TypeError:  If parameter ``parent`` isn't of type :class:`Scope`.
		"""
		super().__init__(name)
		AttributesMixin.__init__(self, attributes)

		if coverType is None:
			raise ValueError(f"Parameter 'coverType' is None.")
		elif not isinstance(coverType, CoverType):
			ex = TypeError(f"Parameter 'coverType' is not of type 'CoverType'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(coverType)}'.")
			raise ex

		if flags is None:
			raise ValueError(f"Parameter 'flags' is None.")
		elif not isinstance(flags, BinFlags):
			ex = TypeError(f"Parameter 'flags' is not of type 'BinFlags'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(flags)}'.")
			raise ex

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

		if source is None:
			raise ValueError(f"Parameter 'source' is None.")
		elif not isinstance(source, SourceLocation):
			ex = TypeError(f"Parameter 'source' is not of type 'SourceLocation'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(source)}'.")
			raise ex

		if parent is not None and not isinstance(parent, Scope):
			ex = TypeError(f"Parameter 'parent' is not of type 'Scope'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent = parent
		self._type =   coverType
		self._flags =  flags
		self._count =  count
		self._source = source

		if parent is not None:
			parent._bins.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[Scope] = None) -> Self:
		"""
		Parse a bin, its count, source location and attributes from its ``<ux:bin>`` element.

		:param element:            The ``<ux:bin>`` element.
		:param parent:             Optional, the scope the bin belongs to. Default: ``None``.
		:returns:                  The bin.
		:raises CodeCoverageError: If an attribute's value isn't of the type the attribute states.
		"""
		return cls(
			element.attrib["name"],
			CoverType(element.attrib["type"]),
			BinFlags(int(element.attrib["flags"], 16)),
			int(element.find("ux:count", NAMESPACES).text),
			SourceLocation.Parse(element.find("ux:src", NAMESPACES)),
			cls._ParseAttributes(element),
			parent=parent
		)

	@readonly
	def Parent(self) -> Nullable[Scope]:
		"""
		Read-only property to access the scope the bin belongs to (:attr:`_parent`).

		:returns: The scope; ``None`` if the bin belongs to no scope.
		"""
		return self._parent

	@readonly
	def Type(self) -> CoverType:
		"""
		Read-only property to access the kind of the bin (:attr:`_type`).

		:returns: The kind, e.g. a statement.
		"""
		return self._type

	@readonly
	def Flags(self) -> BinFlags:
		"""
		Read-only property to access the flags of the bin (:attr:`_flags`).

		:returns: The flags.
		"""
		return self._flags

	@readonly
	def IsExcluded(self) -> bool:
		"""
		Read-only property to return whether the bin is excluded from the measurement.

		:returns: ``True``, if :attr:`Flags` has one of the exclusion flags (:attr:`BinFlags.Excluded`).
		"""
		return (self._flags & BinFlags.Excluded) != 0

	@readonly
	def Count(self) -> int:
		"""
		Read-only property to access how often the coverage item was hit (:attr:`_count`).

		:returns: The count, e.g. how often a statement ran.
		"""
		return self._count

	@readonly
	def Source(self) -> SourceLocation:
		"""
		Read-only property to access where the coverage item is in the sources (:attr:`_source`).

		:returns: The source location.
		"""
		return self._source


@export
class Scope(Base, AttributesMixin, Generic[ScopeParentType]):
	"""
	A ``<ux:scope>`` of the report or of a scope: its bins and the scopes below it.

	Design units, their instances, processes and branching statements are scopes.
	"""

	_parent:     Nullable[ScopeParentType]  #: The report or scope the scope belongs to.
	_type:       ScopeType                  #: Kind of the scope.
	_language:   _Language                  #: Language of the scope's source.
	_weight:     int                        #: Weight of the scope.
	_flags:      int                        #: Flags of the scope.
	_source:     SourceLocation             #: Where the scope is in the sources.
	_designUnit: Nullable[str]              #: Name of the design unit an instance instantiates.
	_scopes:     list[Scope[Scope]]         #: The scopes below this one.
	_bins:       list[Bin]                  #: The bins of this scope.

	def __init__(
		self,
		name: str,
		scopeType: ScopeType,
		language: _Language,
		weight: int,
		flags: int,
		source: SourceLocation,
		designUnit: Nullable[str] = None,
		attributes: Nullable[Mapping[str, int | float | str]] = None,
		*,
		parent: Nullable[ScopeParentType] = None
	) -> None:
		"""
		Initialize the scope, and append it to the scopes of its report or scope.

		Its scopes and bins are added by creating them with this scope as their parent.

		:param name:        Name of the scope, e.g. ``work.counter`` for a design unit or ``uut`` for an instance.
		:param scopeType:   Kind of the scope.
		:param language:    Language of the scope's source.
		:param weight:      Weight of the scope.
		:param flags:       Flags of the scope.
		:param source:      Where the scope is in the sources.
		:param designUnit:  Optional, name of the design unit an instance instantiates, e.g. ``work.counter``.
		                    Default: ``None``.
		:param attributes:  Optional, the attributes by key, e.g. ``{"#GOAL#": 100}``. Default: ``None``.
		:param parent:      Optional, the report or scope the scope belongs to; the scope is appended to its scopes.
		                    Default: ``None``.
		:raises ValueError: If parameter ``name`` is ``None``.
		:raises TypeError:  If parameter ``name`` isn't of type :class:`str`.
		:raises TypeError:  If parameter ``attributes`` isn't a mapping.
		:raises TypeError:  If parameter ``attributes`` contains a key not of type :class:`str`.
		:raises ValueError: If parameter ``attributes`` contains an empty key.
		:raises TypeError:  If parameter ``attributes`` contains a value not of type :class:`int`, :class:`float` or
		                    :class:`str`.
		:raises ValueError: If parameter ``name`` is empty.
		:raises ValueError: If parameter ``scopeType`` is ``None``.
		:raises TypeError:  If parameter ``scopeType`` isn't of type
		                    :class:`~pyEDAA.Reports.CodeCoverage.AldecUCDB.Elements.ScopeType`.
		:raises ValueError: If parameter ``language`` is ``None``.
		:raises TypeError:  If parameter ``language`` isn't of type
		                    :class:`~pyEDAA.Reports.CodeCoverage.AldecUCDB.Elements.Language`.
		:raises ValueError: If parameter ``weight`` is ``None``.
		:raises TypeError:  If parameter ``weight`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``weight`` is negative.
		:raises ValueError: If parameter ``flags`` is ``None``.
		:raises TypeError:  If parameter ``flags`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``flags`` is negative.
		:raises ValueError: If parameter ``source`` is ``None``.
		:raises TypeError:  If parameter ``source`` isn't of type :class:`SourceLocation`.
		:raises TypeError:  If parameter ``designUnit`` isn't of type :class:`str`.
		:raises ValueError: If parameter ``designUnit`` is empty.
		:raises TypeError:  If parameter ``parent`` isn't of type :class:`~pyEDAA.Reports.CodeCoverage.AldecUCDB.Report`
		                    or :class:`Scope`.
		"""
		from pyEDAA.Reports.CodeCoverage.AldecUCDB import Report

		super().__init__(name)
		AttributesMixin.__init__(self, attributes)

		if name == "":
			raise ValueError(f"Parameter 'name' is empty.")

		if scopeType is None:
			raise ValueError(f"Parameter 'scopeType' is None.")
		elif not isinstance(scopeType, ScopeType):
			ex = TypeError(f"Parameter 'scopeType' is not of type 'ScopeType'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(scopeType)}'.")
			raise ex

		if language is None:
			raise ValueError(f"Parameter 'language' is None.")
		elif not isinstance(language, Language):
			ex = TypeError(f"Parameter 'language' is not of type 'Language'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(language)}'.")
			raise ex

		if weight is None:
			raise ValueError(f"Parameter 'weight' is None.")
		elif not isinstance(weight, int):
			ex = TypeError(f"Parameter 'weight' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(weight)}'.")
			raise ex
		elif weight < 0:
			ex = ValueError(f"Parameter 'weight' is negative.")
			ex.add_note(f"Got value '{weight}'.")
			raise ex

		if flags is None:
			raise ValueError(f"Parameter 'flags' is None.")
		elif not isinstance(flags, int):
			ex = TypeError(f"Parameter 'flags' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(flags)}'.")
			raise ex
		elif flags < 0:
			ex = ValueError(f"Parameter 'flags' is negative.")
			ex.add_note(f"Got value '{flags}'.")
			raise ex

		if source is None:
			raise ValueError(f"Parameter 'source' is None.")
		elif not isinstance(source, SourceLocation):
			ex = TypeError(f"Parameter 'source' is not of type 'SourceLocation'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(source)}'.")
			raise ex

		if designUnit is not None:
			if not isinstance(designUnit, str):
				ex = TypeError(f"Parameter 'designUnit' is not of type 'str'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(designUnit)}'.")
				raise ex
			elif designUnit == "":
				raise ValueError(f"Parameter 'designUnit' is empty.")

		if parent is not None and not isinstance(parent, (Report, Scope)):
			ex = TypeError(f"Parameter 'parent' is not of type 'Report' or 'Scope'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =     parent
		self._type =       scopeType
		self._language =   language
		self._weight =     weight
		self._flags =      flags
		self._source =     source
		self._designUnit = designUnit
		self._scopes =     []
		self._bins =       []

		if parent is not None:
			parent._scopes.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[ScopeParentType] = None) -> Self:
		"""
		Parse a scope, its attributes, bins and the scopes below it from its ``<ux:scope>`` element.

		:param element:            The ``<ux:scope>`` element.
		:param parent:             Optional, the report or scope the scope belongs to. Default: ``None``.
		:returns:                  The scope.
		:raises CodeCoverageError: If an attribute's value isn't of the type the attribute states.
		"""
		scope = cls(
			element.attrib["name"],
			ScopeType(element.attrib["type"]),
			Language(element.attrib["lang"]),
			int(element.attrib["weight"]),
			int(element.attrib["flags"], 16),
			SourceLocation.Parse(element.find("ux:src", NAMESPACES)),
			element.attrib.get("du"),
			cls._ParseAttributes(element),
			parent=parent
		)

		for binElement in element.iterfind("ux:bin", NAMESPACES):
			Bin.Parse(binElement, parent=scope)

		for scopeElement in element.iterfind("ux:scope", NAMESPACES):
			Scope.Parse(scopeElement, parent=scope)

		return scope

	def IterateBins(self) -> Generator[Bin, None, None]:
		"""
		Iterate the bins of this scope, then those of the scopes below it, depth-first.

		:returns: A generator of the bins.
		"""
		yield from self._bins
		for scope in self._scopes:
			yield from scope.IterateBins()

	@readonly
	def Parent(self) -> Nullable[ScopeParentType]:
		"""
		Read-only property to access the report or scope the scope belongs to (:attr:`_parent`).

		:returns: The :class:`~pyEDAA.Reports.CodeCoverage.AldecUCDB.Report` or :class:`Scope`; ``None`` if the scope
		          belongs to none.
		"""
		return self._parent

	@readonly
	def Type(self) -> ScopeType:
		"""
		Read-only property to access the kind of the scope (:attr:`_type`).

		:returns: The kind, e.g. a design unit or an instance.
		"""
		return self._type

	@readonly
	def Language(self) -> _Language:
		"""
		Read-only property to access the language of the scope's source (:attr:`_language`).

		:returns: The language.
		"""
		return self._language

	@readonly
	def Weight(self) -> int:
		"""
		Read-only property to access the weight of the scope (:attr:`_weight`).

		:returns: The weight.
		"""
		return self._weight

	@readonly
	def Flags(self) -> int:
		"""
		Read-only property to access the flags of the scope (:attr:`_flags`).

		:returns: The flags, as stated.
		"""
		return self._flags

	@readonly
	def Source(self) -> SourceLocation:
		"""
		Read-only property to access where the scope is in the sources (:attr:`_source`).

		:returns: The source location.
		"""
		return self._source

	@readonly
	def DesignUnit(self) -> Nullable[str]:
		"""
		Read-only property to access the name of the design unit an instance instantiates (:attr:`_designUnit`).

		:returns: The design unit's name, e.g. ``work.counter``; ``None`` for a scope, which isn't an instance.
		"""
		return self._designUnit

	@readonly
	def Scopes(self) -> list[Scope[Scope]]:
		"""
		Read-only property to access the scopes below this one (:attr:`_scopes`).

		:returns: The scopes, in the order the report lists them.
		"""
		return self._scopes

	@readonly
	def Bins(self) -> list[Bin]:
		"""
		Read-only property to access the bins of this scope (:attr:`_bins`).

		:returns: The bins, in the order the report lists them.
		"""
		return self._bins
