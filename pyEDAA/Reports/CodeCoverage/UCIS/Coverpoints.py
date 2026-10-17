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
The coverpoints of the covergroup coverage of the UCIS XML interchange format: their bins, and the value ranges or
sequences a bin counts.
"""
from __future__                                     import annotations

from typing                                         import TYPE_CHECKING, Iterable, Optional as Nullable, Self

from lxml.etree                                     import _Element
from pyTooling.Common                               import getFullyQualifiedName
from pyTooling.Decorators                           import export, readonly
from pyTooling.MetaClasses                          import ExtendedType, abstractclass

from pyEDAA.Reports.CodeCoverage.UCIS.Bins          import BinContents
from pyEDAA.Reports.CodeCoverage.UCIS.CoverOptions  import CoverpointOptions
from pyEDAA.Reports.CodeCoverage.UCIS.Elements      import Base, UserAttribute

if TYPE_CHECKING:
	from pyEDAA.Reports.CodeCoverage.UCIS.Covergroups import CovergroupInstance


@export
@abstractclass
class BinBase(Base):
	"""
	Base-class of the bins of a coverpoint or a cross: the bin's kind, alias, and - as some tools write them - name and
	key.
	"""

	_binType: str            #: Kind of the bin, e.g. ``default``, ``ignore`` or ``illegal``.
	_alias:   Nullable[str]  #: An alias of the bin's name.
	_name:    Nullable[str]  #: Name of the bin.
	_key:     Nullable[str]  #: UCIS key of the bin.

	def __init__(
		self,
		binType: str,
		alias: Nullable[str] = None,
		name: Nullable[str] = None,
		key: Nullable[str] = None,
		userAttributes: Nullable[Iterable[UserAttribute]] = None
	) -> None:
		"""
		Initialize the bin's kind, alias, name and key.

		:param binType:        Kind of the bin, e.g. ``default``, ``ignore`` or ``illegal``.
		:param alias:          Optional, an alias of the bin's name. Default: ``None``.
		:param name:           Optional, name of the bin; the standard's schema has none, pyucis writes it. Default:
		                       ``None``.
		:param key:            Optional, UCIS key of the bin; the standard's schema has none, pyucis writes it. Default:
		                       ``None``.
		:param userAttributes: Optional, the user-defined attributes. Default: ``None``.
		:raises TypeError:     If parameter ``userAttributes`` isn't iterable.
		:raises TypeError:     If parameter ``userAttributes`` contains an element not of type
		                       :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Elements.UserAttribute`.
		:raises ValueError:    If parameter ``binType`` is ``None``.
		:raises TypeError:     If parameter ``binType`` isn't of type :class:`str`.
		:raises TypeError:     If parameter ``alias``, ``name`` or ``key`` isn't of type :class:`str`.
		"""
		super().__init__(userAttributes)

		if binType is None:
			raise ValueError(f"Parameter 'binType' is None.")
		elif not isinstance(binType, str):
			ex = TypeError(f"Parameter 'binType' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(binType)}'.")
			raise ex

		for parameterName, value in (
			("alias", alias),
			("name",  name),
			("key",   key)
		):
			if value is not None and not isinstance(value, str):
				ex = TypeError(f"Parameter '{parameterName}' is not of type 'str'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
				raise ex

		self._binType = binType
		self._alias =   alias
		self._name =    name
		self._key =     key

	@readonly
	def BinType(self) -> str:
		"""
		Read-only property to access the kind of the bin (:attr:`_binType`).

		:returns: The kind, as stated, e.g. ``default``, ``ignore`` or ``illegal``.
		"""
		return self._binType

	@readonly
	def Alias(self) -> Nullable[str]:
		"""
		Read-only property to access the alias of the bin's name (:attr:`_alias`).

		:returns: The alias; ``None``, if the report states none.
		"""
		return self._alias

	@readonly
	def Name(self) -> Nullable[str]:
		"""
		Read-only property to access the name of the bin (:attr:`_name`).

		:returns: The name; ``None``, if the report states none.
		"""
		return self._name

	@readonly
	def Key(self) -> Nullable[str]:
		"""
		Read-only property to access the UCIS key of the bin (:attr:`_key`).

		:returns: The key; ``None``, if the report states none.
		"""
		return self._key


@export
class ValueRange(metaclass=ExtendedType, slots=True):
	"""
	A ``<range>`` of a coverpoint's bin: a range of values, and how often the coverpoint's expression had one of them.
	"""

	_parent:   Nullable[CoverpointBin]  #: The coverpoint bin the range belongs to.
	_from:     int                      #: The range's lowest value.
	_to:       int                      #: The range's highest value.
	_contents: BinContents              #: How often the expression had a value of the range.

	def __init__(self, fromValue: int, toValue: int, contents: BinContents) -> None:
		"""
		Initialize the range of values.

		The coverpoint bin owning the range takes it as a parameter and becomes its parent.

		:param fromValue:   The range's lowest value.
		:param toValue:     The range's highest value; the lowest one again for a single value.
		:param contents:    How often the expression had a value of the range.
		:raises ValueError: If parameter ``fromValue`` or ``toValue`` is ``None``.
		:raises TypeError:  If parameter ``fromValue`` or ``toValue`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``contents`` is ``None``.
		:raises TypeError:  If parameter ``contents`` isn't of type
		                    :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Bins.BinContents`.
		"""
		for parameterName, value in (
			("fromValue", fromValue),
			("toValue",   toValue)
		):
			if value is None:
				raise ValueError(f"Parameter '{parameterName}' is None.")
			elif not isinstance(value, int) or isinstance(value, bool):
				ex = TypeError(f"Parameter '{parameterName}' is not of type 'int'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
				raise ex

		if contents is None:
			raise ValueError(f"Parameter 'contents' is None.")
		elif not isinstance(contents, BinContents):
			ex = TypeError(f"Parameter 'contents' is not of type 'BinContents'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(contents)}'.")
			raise ex

		self._parent =   None
		self._from =     fromValue
		self._to =       toValue
		self._contents = contents

	@classmethod
	def Parse(cls, element: _Element) -> Self:
		"""
		Parse a range of values from its ``<range>`` element.

		:param element: The ``<range>`` element.
		:returns:       The range.
		"""
		return cls(
			int(element.attrib["from"]),
			int(element.attrib["to"]),
			BinContents.Parse(element.find("{*}contents"))
		)

	@readonly
	def Parent(self) -> Nullable[CoverpointBin]:
		"""
		Read-only property to access the coverpoint bin the range belongs to (:attr:`_parent`).

		:returns: The coverpoint bin; ``None``, if the range belongs to none.
		"""
		return self._parent

	@readonly
	def From(self) -> int:
		"""
		Read-only property to access the range's lowest value (:attr:`_from`).

		:returns: The value.
		"""
		return self._from

	@readonly
	def To(self) -> int:
		"""
		Read-only property to access the range's highest value (:attr:`_to`).

		:returns: The value.
		"""
		return self._to

	@readonly
	def Contents(self) -> BinContents:
		"""
		Read-only property to access how often the expression had a value of the range (:attr:`_contents`).

		:returns: The contents: the count and the tests.
		"""
		return self._contents


@export
class ValueSequence(metaclass=ExtendedType, slots=True):
	"""
	A ``<sequence>`` of a coverpoint's bin: a sequence of values, and how often the coverpoint's expression had them one
	after the other.
	"""

	_parent:   Nullable[CoverpointBin]  #: The coverpoint bin the sequence belongs to.
	_values:   list[int]                #: The values, from the first one.
	_contents: BinContents              #: How often the expression had the values one after the other.

	def __init__(self, values: Iterable[int], contents: BinContents) -> None:
		"""
		Initialize the sequence of values.

		The coverpoint bin owning the sequence takes it as a parameter and becomes its parent.

		:param values:      The values, from the first one.
		:param contents:    How often the expression had the values one after the other.
		:raises ValueError: If parameter ``contents`` is ``None``.
		:raises TypeError:  If parameter ``contents`` isn't of type
		                    :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Bins.BinContents`.
		:raises ValueError: If parameter ``values`` is ``None``.
		:raises TypeError:  If parameter ``values`` isn't iterable.
		:raises TypeError:  If parameter ``values`` contains an element not of type :class:`int`.
		:raises ValueError: If parameter ``values`` is empty.
		"""
		if contents is None:
			raise ValueError(f"Parameter 'contents' is None.")
		elif not isinstance(contents, BinContents):
			ex = TypeError(f"Parameter 'contents' is not of type 'BinContents'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(contents)}'.")
			raise ex

		self._parent =   None
		self._values =   []
		self._contents = contents

		if values is None:
			raise ValueError(f"Parameter 'values' is None.")
		elif not isinstance(values, Iterable):
			ex = TypeError(f"Parameter 'values' is not iterable.")
			ex.add_note(f"Got type '{getFullyQualifiedName(values)}'.")
			raise ex

		for value in values:
			if not isinstance(value, int) or isinstance(value, bool):
				ex = TypeError(f"Parameter 'values' contains an element not of type 'int'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
				raise ex

			self._values.append(value)

		if len(self._values) == 0:
			raise ValueError(f"Parameter 'values' is empty.")

	@classmethod
	def Parse(cls, element: _Element) -> Self:
		"""
		Parse a sequence of values from its ``<sequence>`` element.

		:param element: The ``<sequence>`` element.
		:returns:       The sequence.
		"""
		return cls(
			[int(valueElement.text) for valueElement in element.iterfind("{*}seqValue")],
			BinContents.Parse(element.find("{*}contents"))
		)

	@readonly
	def Parent(self) -> Nullable[CoverpointBin]:
		"""
		Read-only property to access the coverpoint bin the sequence belongs to (:attr:`_parent`).

		:returns: The coverpoint bin; ``None``, if the sequence belongs to none.
		"""
		return self._parent

	@readonly
	def Values(self) -> list[int]:
		"""
		Read-only property to access the values (:attr:`_values`).

		:returns: The values, from the first one.
		"""
		return self._values

	@readonly
	def Contents(self) -> BinContents:
		"""
		Read-only property to access how often the expression had the values one after the other (:attr:`_contents`).

		:returns: The contents: the count and the tests.
		"""
		return self._contents


@export
class CoverpointBin(BinBase):
	"""
	A ``<coverpointBin>`` of a coverpoint: its kind, and the ranges or sequences of values it counts.
	"""

	_parent:    Nullable[Coverpoint]  #: The coverpoint the bin belongs to.
	_ranges:    list[ValueRange]      #: The ranges of values the bin counts.
	_sequences: list[ValueSequence]   #: The sequences of values the bin counts.

	def __init__(
		self,
		binType: str,
		ranges: Nullable[Iterable[ValueRange]] = None,
		sequences: Nullable[Iterable[ValueSequence]] = None,
		alias: Nullable[str] = None,
		name: Nullable[str] = None,
		key: Nullable[str] = None,
		userAttributes: Nullable[Iterable[UserAttribute]] = None,
		*,
		parent: Nullable[Coverpoint] = None
	) -> None:
		"""
		Initialize the coverpoint bin, become its ranges' and sequences' parent, and append it to the bins of its
		coverpoint.

		:param binType:        Kind of the bin, e.g. ``default``, ``ignore`` or ``illegal``.
		:param ranges:         Optional, the ranges of values the bin counts. Default: ``None``.
		:param sequences:      Optional, the sequences of values the bin counts. Default: ``None``.
		:param alias:          Optional, an alias of the bin's name. Default: ``None``.
		:param name:           Optional, name of the bin, as pyucis writes it. Default: ``None``.
		:param key:            Optional, UCIS key of the bin, as pyucis writes it. Default: ``None``.
		:param userAttributes: Optional, the user-defined attributes. Default: ``None``.
		:param parent:         Optional, the coverpoint the bin belongs to. Default: ``None``.
		:raises TypeError:     If parameter ``userAttributes`` isn't iterable.
		:raises TypeError:     If parameter ``userAttributes`` contains an element not of type
		                       :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Elements.UserAttribute`.
		:raises ValueError:    If parameter ``binType`` is ``None``.
		:raises TypeError:     If parameter ``binType`` isn't of type :class:`str`.
		:raises TypeError:     If parameter ``alias``, ``name`` or ``key`` isn't of type :class:`str`.
		:raises TypeError:     If parameter ``parent`` isn't of type :class:`Coverpoint`.
		:raises TypeError:     If parameter ``ranges`` isn't iterable.
		:raises TypeError:     If parameter ``ranges`` contains an element not of type :class:`ValueRange`.
		:raises TypeError:     If parameter ``sequences`` isn't iterable.
		:raises TypeError:     If parameter ``sequences`` contains an element not of type :class:`ValueSequence`.
		"""
		super().__init__(binType, alias, name, key, userAttributes)

		if parent is not None and not isinstance(parent, Coverpoint):
			ex = TypeError(f"Parameter 'parent' is not of type 'Coverpoint'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =    parent
		self._ranges =    []
		self._sequences = []

		if ranges is not None:
			if not isinstance(ranges, Iterable):
				ex = TypeError(f"Parameter 'ranges' is not iterable.")
				ex.add_note(f"Got type '{getFullyQualifiedName(ranges)}'.")
				raise ex

			for valueRange in ranges:
				if not isinstance(valueRange, ValueRange):
					ex = TypeError(f"Parameter 'ranges' contains an element not of type 'ValueRange'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(valueRange)}'.")
					raise ex

				valueRange._parent = self
				self._ranges.append(valueRange)

		if sequences is not None:
			if not isinstance(sequences, Iterable):
				ex = TypeError(f"Parameter 'sequences' is not iterable.")
				ex.add_note(f"Got type '{getFullyQualifiedName(sequences)}'.")
				raise ex

			for valueSequence in sequences:
				if not isinstance(valueSequence, ValueSequence):
					ex = TypeError(f"Parameter 'sequences' contains an element not of type 'ValueSequence'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(valueSequence)}'.")
					raise ex

				valueSequence._parent = self
				self._sequences.append(valueSequence)

		if parent is not None:
			parent._bins.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[Coverpoint] = None) -> Self:
		"""
		Parse a coverpoint bin, its ranges and sequences from its ``<coverpointBin>`` element.

		:param element:            The ``<coverpointBin>`` element.
		:param parent:             Optional, the coverpoint the bin belongs to. Default: ``None``.
		:returns:                  The coverpoint bin.
		:raises CodeCoverageError: If a user-defined attribute's value isn't of the type the attribute states.
		"""
		return cls(
			element.attrib["type"],
			[ValueRange.Parse(rangeElement) for rangeElement in element.iterfind("{*}range")],
			[ValueSequence.Parse(sequenceElement) for sequenceElement in element.iterfind("{*}sequence")],
			element.attrib.get("alias"),
			element.attrib.get("name"),
			element.attrib.get("key"),
			cls._ParseUserAttributes(element),
			parent=parent
		)

	@readonly
	def Parent(self) -> Nullable[Coverpoint]:
		"""
		Read-only property to access the coverpoint the bin belongs to (:attr:`_parent`).

		:returns: The coverpoint; ``None``, if the bin belongs to none.
		"""
		return self._parent

	@readonly
	def Ranges(self) -> list[ValueRange]:
		"""
		Read-only property to access the ranges of values the bin counts (:attr:`_ranges`).

		:returns: The ranges, in the order the report lists them; empty for a bin of sequences.
		"""
		return self._ranges

	@readonly
	def Sequences(self) -> list[ValueSequence]:
		"""
		Read-only property to access the sequences of values the bin counts (:attr:`_sequences`).

		:returns: The sequences, in the order the report lists them; empty for a bin of ranges.
		"""
		return self._sequences


@export
class Coverpoint(Base):
	"""
	A ``<coverpoint>`` of a covergroup instance: its expression, options and bins.
	"""

	_parent:     Nullable[CovergroupInstance]  #: The covergroup instance the coverpoint belongs to.
	_name:       str                           #: Name of the coverpoint.
	_key:        str                           #: UCIS key of the coverpoint.
	_options:    CoverpointOptions             #: The options of the coverpoint.
	_alias:      Nullable[str]                 #: An alias of the coverpoint's name.
	_expression: Nullable[str]                 #: The expression the coverpoint samples.
	_bins:       list[CoverpointBin]           #: The bins.

	def __init__(
		self,
		name: str,
		key: str,
		options: CoverpointOptions,
		alias: Nullable[str] = None,
		expression: Nullable[str] = None,
		userAttributes: Nullable[Iterable[UserAttribute]] = None,
		*,
		parent: Nullable[CovergroupInstance] = None
	) -> None:
		"""
		Initialize the coverpoint, and append it to the coverpoints of its covergroup instance.

		Its bins are added by creating them with this coverpoint as their parent.

		:param name:           Name of the coverpoint, e.g. ``cvpt_a``.
		:param key:            UCIS key of the coverpoint.
		:param options:        The options of the coverpoint.
		:param alias:          Optional, an alias of the coverpoint's name. Default: ``None``.
		:param expression:     Optional, the expression the coverpoint samples, e.g. ``a``. Default: ``None``.
		:param userAttributes: Optional, the user-defined attributes. Default: ``None``.
		:param parent:         Optional, the covergroup instance the coverpoint belongs to. Default: ``None``.
		:raises TypeError:     If parameter ``userAttributes`` isn't iterable.
		:raises TypeError:     If parameter ``userAttributes`` contains an element not of type
		                       :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Elements.UserAttribute`.
		:raises ValueError:    If parameter ``name`` or ``key`` is ``None``.
		:raises TypeError:     If parameter ``name`` or ``key`` isn't of type :class:`str`.
		:raises ValueError:    If parameter ``options`` is ``None``.
		:raises TypeError:     If parameter ``options`` isn't of type
		                       :class:`~pyEDAA.Reports.CodeCoverage.UCIS.CoverOptions.CoverpointOptions`.
		:raises TypeError:     If parameter ``alias`` or ``expression`` isn't of type :class:`str`.
		:raises TypeError:     If parameter ``parent`` isn't of type
		                       :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Covergroups.CovergroupInstance`.
		"""
		from pyEDAA.Reports.CodeCoverage.UCIS.Covergroups import CovergroupInstance

		super().__init__(userAttributes)

		for parameterName, value in (
			("name", name),
			("key",  key)
		):
			if value is None:
				raise ValueError(f"Parameter '{parameterName}' is None.")
			elif not isinstance(value, str):
				ex = TypeError(f"Parameter '{parameterName}' is not of type 'str'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
				raise ex

		if options is None:
			raise ValueError(f"Parameter 'options' is None.")
		elif not isinstance(options, CoverpointOptions):
			ex = TypeError(f"Parameter 'options' is not of type 'CoverpointOptions'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(options)}'.")
			raise ex

		for parameterName, value in (
			("alias",      alias),
			("expression", expression)
		):
			if value is not None and not isinstance(value, str):
				ex = TypeError(f"Parameter '{parameterName}' is not of type 'str'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
				raise ex

		if parent is not None and not isinstance(parent, CovergroupInstance):
			ex = TypeError(f"Parameter 'parent' is not of type 'CovergroupInstance'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =     parent
		self._name =       name
		self._key =        key
		self._options =    options
		self._alias =      alias
		self._expression = expression
		self._bins =       []

		if parent is not None:
			parent._coverpoints.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[CovergroupInstance] = None) -> Self:
		"""
		Parse a coverpoint, its options and bins from its ``<coverpoint>`` element.

		:param element:            The ``<coverpoint>`` element.
		:param parent:             Optional, the covergroup instance the coverpoint belongs to. Default: ``None``.
		:returns:                  The coverpoint.
		:raises CodeCoverageError: If a user-defined attribute's value isn't of the type the attribute states.
		"""
		coverpoint = cls(
			element.attrib["name"],
			element.attrib["key"],
			CoverpointOptions.Parse(element.find("{*}options")),
			element.attrib.get("alias"),
			element.attrib.get("exprString"),
			cls._ParseUserAttributes(element),
			parent=parent
		)

		for binElement in element.iterfind("{*}coverpointBin"):
			CoverpointBin.Parse(binElement, parent=coverpoint)

		return coverpoint

	@readonly
	def Parent(self) -> Nullable[CovergroupInstance]:
		"""
		Read-only property to access the covergroup instance the coverpoint belongs to (:attr:`_parent`).

		:returns: The covergroup instance; ``None``, if the coverpoint belongs to none.
		"""
		return self._parent

	@readonly
	def Name(self) -> str:
		"""
		Read-only property to access the name of the coverpoint (:attr:`_name`).

		:returns: The name, as declared.
		"""
		return self._name

	@readonly
	def Key(self) -> str:
		"""
		Read-only property to access the UCIS key of the coverpoint (:attr:`_key`).

		:returns: The key, as stated.
		"""
		return self._key

	@readonly
	def Options(self) -> CoverpointOptions:
		"""
		Read-only property to access the options of the coverpoint (:attr:`_options`).

		:returns: The options.
		"""
		return self._options

	@readonly
	def Alias(self) -> Nullable[str]:
		"""
		Read-only property to access the alias of the coverpoint's name (:attr:`_alias`).

		:returns: The alias; ``None``, if the report states none.
		"""
		return self._alias

	@readonly
	def Expression(self) -> Nullable[str]:
		"""
		Read-only property to access the expression the coverpoint samples (:attr:`_expression`).

		:returns: The expression, e.g. ``a``; ``None``, if the report states none.
		"""
		return self._expression

	@readonly
	def Bins(self) -> list[CoverpointBin]:
		"""
		Read-only property to access the bins (:attr:`_bins`).

		:returns: The bins, in the order the report lists them.
		"""
		return self._bins
