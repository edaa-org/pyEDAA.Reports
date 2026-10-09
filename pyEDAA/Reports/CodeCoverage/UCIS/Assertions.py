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
The assertion coverage of the UCIS XML interchange format: an instance's ``<assertionCoverage>`` and its assertions -
e.g. ``assert``, ``assume`` or ``cover`` directives - with a bin per outcome.
"""
from __future__                                   import annotations

from typing                                       import TYPE_CHECKING, Iterable, Mapping, Optional as Nullable, Self

from lxml.etree                                   import _Element
from pyTooling.Common                             import getFullyQualifiedName, StringEnum
from pyTooling.Decorators                         import export, readonly

from pyEDAA.Reports.CodeCoverage.UCIS.Bins        import Bin
from pyEDAA.Reports.CodeCoverage.UCIS.Elements    import Base, MetricCoverage, ObjectAttributesMixin, UserAttribute

if TYPE_CHECKING:
	from pyEDAA.Reports.CodeCoverage.UCIS.Instances import InstanceCoverage


@export
class AssertionBinKind(StringEnum):
	"""
	Kind of an assertion's bin: the outcome it counts, named as the bin's element.
	"""

	Cover =      "coverBin"       #: The cover directive's sequence matched.
	Pass =       "passBin"        #: The assertion passed.
	Fail =       "failBin"        #: The assertion failed.
	Vacuous =    "vacuousBin"     #: The assertion passed vacuously.
	Disabled =   "disabledBin"    #: The assertion was disabled.
	Attempt =    "attemptBin"     #: The assertion was attempted.
	Active =     "activeBin"      #: The assertion's threads were active.
	PeakActive = "peakActiveBin"  #: The peak number of the assertion's active threads.


@export
class AssertionCoverage(MetricCoverage):
	"""
	An ``<assertionCoverage>`` of an instance: its assertions.
	"""

	_assertions: list[Assertion]  #: The assertions.

	def __init__(
		self,
		metricMode: Nullable[str] = None,
		weight: int = 1,
		userAttributes: Nullable[Iterable[UserAttribute]] = None,
		*,
		parent: Nullable[InstanceCoverage] = None
	) -> None:
		"""
		Initialize the assertion coverage, and append it to the assertion coverages of its instance.

		Its assertions are added by creating them with this coverage as their parent.

		:param metricMode:     Optional, the mode in which the coverage was measured. Default: ``None``.
		:param weight:         Optional, weight of the mode in computing the coverage. Default: ``1``.
		:param userAttributes: Optional, the user-defined attributes. Default: ``None``.
		:param parent:         Optional, the instance the coverage belongs to. Default: ``None``.
		:raises TypeError:     If parameter ``userAttributes`` isn't iterable.
		:raises TypeError:     If parameter ``userAttributes`` contains an element not of type
		                       :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Elements.UserAttribute`.
		:raises TypeError:     If parameter ``metricMode`` isn't of type :class:`str`.
		:raises ValueError:    If parameter ``weight`` is ``None``.
		:raises TypeError:     If parameter ``weight`` isn't of type :class:`int`.
		:raises ValueError:    If parameter ``weight`` is negative.
		:raises TypeError:     If parameter ``parent`` isn't of type
		                       :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Instances.InstanceCoverage`.
		"""
		super().__init__(metricMode, weight, userAttributes, parent=parent)

		self._assertions = []

		if parent is not None:
			parent._assertionCoverages.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[InstanceCoverage] = None) -> Self:
		"""
		Parse an assertion coverage and its assertions from its ``<assertionCoverage>`` element.

		:param element:            The ``<assertionCoverage>`` element.
		:param parent:             Optional, the instance the coverage belongs to. Default: ``None``.
		:returns:                  The assertion coverage.
		:raises CodeCoverageError: If a user-defined attribute's value isn't of the type the attribute states.
		"""
		assertionCoverage = cls(
			element.attrib.get("metricMode"),
			int(element.attrib.get("weight", "1")),
			cls._ParseUserAttributes(element),
			parent=parent
		)

		for assertionElement in element.iterfind("{*}assertion"):
			Assertion.Parse(assertionElement, parent=assertionCoverage)

		return assertionCoverage

	@readonly
	def Assertions(self) -> list[Assertion]:
		"""
		Read-only property to access the assertions (:attr:`_assertions`).

		:returns: The assertions, in the order the report lists them.
		"""
		return self._assertions


@export
class Assertion(Base, ObjectAttributesMixin):
	"""
	An ``<assertion>`` of an assertion coverage: its name, its kind and a bin per outcome the report counts.
	"""

	_parent:        Nullable[AssertionCoverage]  #: The assertion coverage the assertion belongs to.
	_name:          str                          #: Name of the assertion.
	_assertionKind: str                          #: Kind of the assertion, e.g. ``assert`` or ``cover``.
	_bins:          dict[AssertionBinKind, Bin]  #: The bins, by the outcome they count.

	def __init__(
		self,
		name: str,
		assertionKind: str,
		bins: Nullable[Mapping[AssertionBinKind, Bin]] = None,
		alias: Nullable[str] = None,
		excluded: bool = False,
		excludedReason: Nullable[str] = None,
		weight: int = 1,
		userAttributes: Nullable[Iterable[UserAttribute]] = None,
		*,
		parent: Nullable[AssertionCoverage] = None
	) -> None:
		"""
		Initialize the assertion, become its bins' parent, and append it to the assertions of its assertion coverage.

		:param name:           Name of the assertion, e.g. ``a1``.
		:param assertionKind:  Kind of the assertion, e.g. ``assert`` or ``cover``.
		:param bins:           Optional, the bins, by the outcome they count. Default: ``None``.
		:param alias:          Optional, an alias of the assertion's name. Default: ``None``.
		:param excluded:       Optional, whether the assertion is excluded from the coverage. Default: ``False``.
		:param excludedReason: Optional, why the assertion is excluded. Default: ``None``.
		:param weight:         Optional, weight of the assertion in computing the coverage. Default: ``1``.
		:param userAttributes: Optional, the user-defined attributes. Default: ``None``.
		:param parent:         Optional, the assertion coverage the assertion belongs to. Default: ``None``.
		:raises TypeError:     If parameter ``userAttributes`` isn't iterable.
		:raises TypeError:     If parameter ``userAttributes`` contains an element not of type
		                       :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Elements.UserAttribute`.
		:raises TypeError:     If parameter ``alias`` isn't of type :class:`str`.
		:raises ValueError:    If parameter ``excluded`` is ``None``.
		:raises TypeError:     If parameter ``excluded`` isn't of type :class:`bool`.
		:raises TypeError:     If parameter ``excludedReason`` isn't of type :class:`str`.
		:raises ValueError:    If parameter ``weight`` is ``None``.
		:raises TypeError:     If parameter ``weight`` isn't of type :class:`int`.
		:raises ValueError:    If parameter ``weight`` is negative.
		:raises ValueError:    If parameter ``name`` or ``assertionKind`` is ``None``.
		:raises TypeError:     If parameter ``name`` or ``assertionKind`` isn't of type :class:`str`.
		:raises TypeError:     If parameter ``parent`` isn't of type :class:`AssertionCoverage`.
		:raises TypeError:     If parameter ``bins`` isn't a mapping.
		:raises TypeError:     If parameter ``bins`` contains a key not of type :class:`AssertionBinKind`.
		:raises TypeError:     If parameter ``bins`` contains a value not of type
		                       :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Bins.Bin`.
		"""
		super().__init__(userAttributes)
		ObjectAttributesMixin.__init__(self, alias, excluded, excludedReason, weight)

		for parameterName, value in (
			("name",          name),
			("assertionKind", assertionKind)
		):
			if value is None:
				raise ValueError(f"Parameter '{parameterName}' is None.")
			elif not isinstance(value, str):
				ex = TypeError(f"Parameter '{parameterName}' is not of type 'str'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
				raise ex

		if parent is not None and not isinstance(parent, AssertionCoverage):
			ex = TypeError(f"Parameter 'parent' is not of type 'AssertionCoverage'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =        parent
		self._name =          name
		self._assertionKind = assertionKind
		self._bins =          {}

		if bins is not None:
			if not isinstance(bins, Mapping):
				ex = TypeError(f"Parameter 'bins' is not a mapping.")
				ex.add_note(f"Got type '{getFullyQualifiedName(bins)}'.")
				raise ex

			for binKind, coverBin in bins.items():
				if not isinstance(binKind, AssertionBinKind):
					ex = TypeError(f"Parameter 'bins' contains a key not of type 'AssertionBinKind'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(binKind)}'.")
					raise ex
				elif not isinstance(coverBin, Bin):
					ex = TypeError(f"Parameter 'bins' contains a value not of type 'Bin'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(coverBin)}' for key '{binKind}'.")
					raise ex

				coverBin._parent =    self
				self._bins[binKind] = coverBin

		if parent is not None:
			parent._assertions.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[AssertionCoverage] = None) -> Self:
		"""
		Parse an assertion and its bins from its ``<assertion>`` element.

		:param element:            The ``<assertion>`` element.
		:param parent:             Optional, the assertion coverage the assertion belongs to. Default: ``None``.
		:returns:                  The assertion.
		:raises CodeCoverageError: If a user-defined attribute's value isn't of the type the attribute states.
		"""
		bins = {
			binKind: Bin.Parse(binElement)
			for binKind in AssertionBinKind if (binElement := element.find(f"{{*}}{binKind}")) is not None
		}

		return cls(
			element.attrib["name"],
			element.attrib["assertionKind"],
			bins,
			element.attrib.get("alias"),
			cls._ParseBoolean(element.attrib.get("excluded", "false")),
			element.attrib.get("excludedReason"),
			int(element.attrib.get("weight", "1")),
			cls._ParseUserAttributes(element),
			parent=parent
		)

	@readonly
	def Parent(self) -> Nullable[AssertionCoverage]:
		"""
		Read-only property to access the assertion coverage the assertion belongs to (:attr:`_parent`).

		:returns: The assertion coverage; ``None``, if the assertion belongs to none.
		"""
		return self._parent

	@readonly
	def Name(self) -> str:
		"""
		Read-only property to access the name of the assertion (:attr:`_name`).

		:returns: The name, as declared.
		"""
		return self._name

	@readonly
	def AssertionKind(self) -> str:
		"""
		Read-only property to access the kind of the assertion (:attr:`_assertionKind`).

		:returns: The kind, as stated, e.g. ``assert`` or ``cover``.
		"""
		return self._assertionKind

	@readonly
	def Bins(self) -> dict[AssertionBinKind, Bin]:
		"""
		Read-only property to access the bins (:attr:`_bins`).

		:returns: The bins, by the outcome they count, in the order of :class:`AssertionBinKind`.
		"""
		return self._bins
