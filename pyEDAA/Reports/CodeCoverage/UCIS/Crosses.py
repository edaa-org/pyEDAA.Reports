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
The crosses of the covergroup coverage of the UCIS XML interchange format: their options and bins, each a combination
of the crossed coverpoints' bins.
"""
from __future__                                     import annotations

from typing                                         import TYPE_CHECKING, Iterable, Optional as Nullable, Self

from lxml.etree                                     import _Element
from pyTooling.Common                               import getFullyQualifiedName
from pyTooling.Decorators                           import export, readonly

from pyEDAA.Reports.CodeCoverage.UCIS.Bins          import BinContents
from pyEDAA.Reports.CodeCoverage.UCIS.CoverOptions  import CrossOptions
from pyEDAA.Reports.CodeCoverage.UCIS.Coverpoints   import BinBase
from pyEDAA.Reports.CodeCoverage.UCIS.Elements      import Base, UserAttribute

if TYPE_CHECKING:
	from pyEDAA.Reports.CodeCoverage.UCIS.Covergroups import CovergroupInstance


@export
class Cross(Base):
	"""
	A ``<cross>`` of a covergroup instance: the expressions - coverpoints - it crosses, its options and bins.
	"""

	_parent:      Nullable[CovergroupInstance]  #: The covergroup instance the cross belongs to.
	_name:        str                           #: Name of the cross.
	_key:         str                           #: UCIS key of the cross.
	_options:     CrossOptions                  #: The options of the cross.
	_alias:       Nullable[str]                 #: An alias of the cross' name.
	_expressions: list[str]                     #: The crossed expressions, e.g. coverpoints' names.
	_bins:        list[CrossBin]                #: The bins.

	def __init__(
		self,
		name: str,
		key: str,
		options: CrossOptions,
		expressions: Nullable[Iterable[str]] = None,
		alias: Nullable[str] = None,
		userAttributes: Nullable[Iterable[UserAttribute]] = None,
		*,
		parent: Nullable[CovergroupInstance] = None
	) -> None:
		"""
		Initialize the cross, and append it to the crosses of its covergroup instance.

		Its bins are added by creating them with this cross as their parent.

		:param name:           Name of the cross, e.g. ``xab``.
		:param key:            UCIS key of the cross.
		:param options:        The options of the cross.
		:param expressions:    Optional, the crossed expressions, e.g. ``["cvpt_a", "cvpt_b"]``. Default: ``None``.
		:param alias:          Optional, an alias of the cross' name. Default: ``None``.
		:param userAttributes: Optional, the user-defined attributes. Default: ``None``.
		:param parent:         Optional, the covergroup instance the cross belongs to. Default: ``None``.
		:raises TypeError:     If parameter ``userAttributes`` isn't iterable.
		:raises TypeError:     If parameter ``userAttributes`` contains an element not of type
		                       :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Elements.UserAttribute`.
		:raises ValueError:    If parameter ``name`` or ``key`` is ``None``.
		:raises TypeError:     If parameter ``name`` or ``key`` isn't of type :class:`str`.
		:raises ValueError:    If parameter ``options`` is ``None``.
		:raises TypeError:     If parameter ``options`` isn't of type
		                       :class:`~pyEDAA.Reports.CodeCoverage.UCIS.CoverOptions.CrossOptions`.
		:raises TypeError:     If parameter ``alias`` isn't of type :class:`str`.
		:raises TypeError:     If parameter ``parent`` isn't of type
		                       :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Covergroups.CovergroupInstance`.
		:raises TypeError:     If parameter ``expressions`` isn't iterable.
		:raises TypeError:     If parameter ``expressions`` contains an element not of type :class:`str`.
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
		elif not isinstance(options, CrossOptions):
			ex = TypeError(f"Parameter 'options' is not of type 'CrossOptions'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(options)}'.")
			raise ex

		if alias is not None and not isinstance(alias, str):
			ex = TypeError(f"Parameter 'alias' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(alias)}'.")
			raise ex

		if parent is not None and not isinstance(parent, CovergroupInstance):
			ex = TypeError(f"Parameter 'parent' is not of type 'CovergroupInstance'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =      parent
		self._name =        name
		self._key =         key
		self._options =     options
		self._alias =       alias
		self._expressions = []
		self._bins =        []

		if expressions is not None:
			if not isinstance(expressions, Iterable):
				ex = TypeError(f"Parameter 'expressions' is not iterable.")
				ex.add_note(f"Got type '{getFullyQualifiedName(expressions)}'.")
				raise ex

			for expression in expressions:
				if not isinstance(expression, str):
					ex = TypeError(f"Parameter 'expressions' contains an element not of type 'str'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(expression)}'.")
					raise ex

				self._expressions.append(expression)

		if parent is not None:
			parent._crosses.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[CovergroupInstance] = None) -> Self:
		"""
		Parse a cross, its options and bins from its ``<cross>`` element.

		:param element:            The ``<cross>`` element.
		:param parent:             Optional, the covergroup instance the cross belongs to. Default: ``None``.
		:returns:                  The cross.
		:raises CodeCoverageError: If a user-defined attribute's value isn't of the type the attribute states.
		"""
		cross = cls(
			element.attrib["name"],
			element.attrib["key"],
			CrossOptions.Parse(element.find("{*}options")),
			[(expressionElement.text or "").strip() for expressionElement in element.iterfind("{*}crossExpr")],
			element.attrib.get("alias"),
			cls._ParseUserAttributes(element),
			parent=parent
		)

		for binElement in element.iterfind("{*}crossBin"):
			CrossBin.Parse(binElement, parent=cross)

		return cross

	@readonly
	def Parent(self) -> Nullable[CovergroupInstance]:
		"""
		Read-only property to access the covergroup instance the cross belongs to (:attr:`_parent`).

		:returns: The covergroup instance; ``None``, if the cross belongs to none.
		"""
		return self._parent

	@readonly
	def Name(self) -> str:
		"""
		Read-only property to access the name of the cross (:attr:`_name`).

		:returns: The name, as declared.
		"""
		return self._name

	@readonly
	def Key(self) -> str:
		"""
		Read-only property to access the UCIS key of the cross (:attr:`_key`).

		:returns: The key, as stated.
		"""
		return self._key

	@readonly
	def Options(self) -> CrossOptions:
		"""
		Read-only property to access the options of the cross (:attr:`_options`).

		:returns: The options.
		"""
		return self._options

	@readonly
	def Alias(self) -> Nullable[str]:
		"""
		Read-only property to access the alias of the cross' name (:attr:`_alias`).

		:returns: The alias; ``None``, if the report states none.
		"""
		return self._alias

	@readonly
	def Expressions(self) -> list[str]:
		"""
		Read-only property to access the crossed expressions (:attr:`_expressions`).

		:returns: The expressions, e.g. coverpoints' names, in the order the report lists them.
		"""
		return self._expressions

	@readonly
	def Bins(self) -> list[CrossBin]:
		"""
		Read-only property to access the bins (:attr:`_bins`).

		:returns: The bins, in the order the report lists them.
		"""
		return self._bins


@export
class CrossBin(BinBase):
	"""
	A ``<crossBin>`` of a cross: the indices of the crossed coverpoints' bins it combines, and how often the combination
	was hit.
	"""

	_parent:   Nullable[Cross]  #: The cross the bin belongs to.
	_indices:  list[int]        #: The indices of the crossed coverpoints' bins, one per coverpoint.
	_contents: BinContents      #: How often the combination was hit.

	def __init__(
		self,
		indices: Iterable[int],
		contents: BinContents,
		binType: str = "default",
		alias: Nullable[str] = None,
		name: Nullable[str] = None,
		key: Nullable[str] = None,
		userAttributes: Nullable[Iterable[UserAttribute]] = None,
		*,
		parent: Nullable[Cross] = None
	) -> None:
		"""
		Initialize the cross bin, and append it to the bins of its cross.

		:param indices:        The indices of the crossed coverpoints' bins, one per coverpoint.
		:param contents:       How often the combination was hit.
		:param binType:        Optional, kind of the bin, e.g. ``default``, ``ignore`` or ``illegal``. Default:
		                       ``"default"``.
		:param alias:          Optional, an alias of the bin's name. Default: ``None``.
		:param name:           Optional, name of the bin, as pyucis writes it. Default: ``None``.
		:param key:            Optional, UCIS key of the bin, as pyucis writes it. Default: ``None``.
		:param userAttributes: Optional, the user-defined attributes. Default: ``None``.
		:param parent:         Optional, the cross the bin belongs to. Default: ``None``.
		:raises TypeError:     If parameter ``userAttributes`` isn't iterable.
		:raises TypeError:     If parameter ``userAttributes`` contains an element not of type
		                       :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Elements.UserAttribute`.
		:raises ValueError:    If parameter ``binType`` is ``None``.
		:raises TypeError:     If parameter ``binType`` isn't of type :class:`str`.
		:raises TypeError:     If parameter ``alias``, ``name`` or ``key`` isn't of type :class:`str`.
		:raises ValueError:    If parameter ``contents`` is ``None``.
		:raises TypeError:     If parameter ``contents`` isn't of type
		                       :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Bins.BinContents`.
		:raises TypeError:     If parameter ``parent`` isn't of type :class:`Cross`.
		:raises ValueError:    If parameter ``indices`` is ``None``.
		:raises TypeError:     If parameter ``indices`` isn't iterable.
		:raises TypeError:     If parameter ``indices`` contains an element not of type :class:`int`.
		:raises ValueError:    If parameter ``indices`` is empty.
		"""
		super().__init__(binType, alias, name, key, userAttributes)

		if contents is None:
			raise ValueError(f"Parameter 'contents' is None.")
		elif not isinstance(contents, BinContents):
			ex = TypeError(f"Parameter 'contents' is not of type 'BinContents'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(contents)}'.")
			raise ex

		if parent is not None and not isinstance(parent, Cross):
			ex = TypeError(f"Parameter 'parent' is not of type 'Cross'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =   parent
		self._indices =  []
		self._contents = contents

		if indices is None:
			raise ValueError(f"Parameter 'indices' is None.")
		elif not isinstance(indices, Iterable):
			ex = TypeError(f"Parameter 'indices' is not iterable.")
			ex.add_note(f"Got type '{getFullyQualifiedName(indices)}'.")
			raise ex

		for index in indices:
			if not isinstance(index, int) or isinstance(index, bool):
				ex = TypeError(f"Parameter 'indices' contains an element not of type 'int'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(index)}'.")
				raise ex

			self._indices.append(index)

		if len(self._indices) == 0:
			raise ValueError(f"Parameter 'indices' is empty.")

		if parent is not None:
			parent._bins.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[Cross] = None) -> Self:
		"""
		Parse a cross bin from its ``<crossBin>`` element.

		:param element:            The ``<crossBin>`` element.
		:param parent:             Optional, the cross the bin belongs to. Default: ``None``.
		:returns:                  The cross bin.
		:raises CodeCoverageError: If a user-defined attribute's value isn't of the type the attribute states.
		"""
		return cls(
			[int(indexElement.text) for indexElement in element.iterfind("{*}index")],
			BinContents.Parse(element.find("{*}contents")),
			element.attrib.get("type", "default"),
			element.attrib.get("alias"),
			element.attrib.get("name"),
			element.attrib.get("key"),
			cls._ParseUserAttributes(element),
			parent=parent
		)

	@readonly
	def Parent(self) -> Nullable[Cross]:
		"""
		Read-only property to access the cross the bin belongs to (:attr:`_parent`).

		:returns: The cross; ``None``, if the bin belongs to none.
		"""
		return self._parent

	@readonly
	def Indices(self) -> list[int]:
		"""
		Read-only property to access the indices of the crossed coverpoints' bins (:attr:`_indices`).

		:returns: The indices, one per crossed coverpoint.
		"""
		return self._indices

	@readonly
	def Contents(self) -> BinContents:
		"""
		Read-only property to access how often the combination was hit (:attr:`_contents`).

		:returns: The contents: the count and the tests.
		"""
		return self._contents
