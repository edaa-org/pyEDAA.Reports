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
The covergroup coverage of the UCIS XML interchange format: an instance's ``<covergroupCoverage>``, its covergroup
instances with their coverpoints and crosses.
"""
from __future__                                    import annotations

from typing                                        import TYPE_CHECKING, Iterable, Mapping, Optional as Nullable, Self

from lxml.etree                                    import _Element
from pyTooling.Common                              import getFullyQualifiedName
from pyTooling.Decorators                          import export, readonly
from pyTooling.MetaClasses                         import ExtendedType

from pyEDAA.Reports.CodeCoverage.UCIS.CoverOptions import CovergroupOptions
from pyEDAA.Reports.CodeCoverage.UCIS.Coverpoints  import Coverpoint
from pyEDAA.Reports.CodeCoverage.UCIS.Crosses      import Cross
from pyEDAA.Reports.CodeCoverage.UCIS.Elements     import Base, MetricCoverage, StatementID, UserAttribute

if TYPE_CHECKING:
	from pyEDAA.Reports.CodeCoverage.UCIS.Instances  import InstanceCoverage


@export
class CovergroupCoverage(MetricCoverage):
	"""
	A ``<covergroupCoverage>`` of an instance: its covergroup instances.
	"""

	_instances: list[CovergroupInstance]  #: The covergroup instances.

	def __init__(
		self,
		metricMode: Nullable[str] = None,
		weight: int = 1,
		userAttributes: Nullable[Iterable[UserAttribute]] = None,
		*,
		parent: Nullable[InstanceCoverage] = None
	) -> None:
		"""
		Initialize the covergroup coverage, and append it to the covergroup coverages of its instance.

		Its covergroup instances are added by creating them with this coverage as their parent.

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

		self._instances = []

		if parent is not None:
			parent._covergroupCoverages.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[InstanceCoverage] = None) -> Self:
		"""
		Parse a covergroup coverage and its covergroup instances from its ``<covergroupCoverage>`` element.

		:param element:            The ``<covergroupCoverage>`` element.
		:param parent:             Optional, the instance the coverage belongs to. Default: ``None``.
		:returns:                  The covergroup coverage.
		:raises CodeCoverageError: If a user-defined attribute's value isn't of the type the attribute states.
		"""
		covergroupCoverage = cls(
			element.attrib.get("metricMode"),
			int(element.attrib.get("weight", "1")),
			cls._ParseUserAttributes(element),
			parent=parent
		)

		for instanceElement in element.iterfind("{*}cgInstance"):
			CovergroupInstance.Parse(instanceElement, parent=covergroupCoverage)

		return covergroupCoverage

	@readonly
	def Instances(self) -> list[CovergroupInstance]:
		"""
		Read-only property to access the covergroup instances (:attr:`_instances`).

		:returns: The covergroup instances, in the order the report lists them.
		"""
		return self._instances


@export
class CovergroupID(metaclass=ExtendedType, slots=True):
	"""
	A ``<cgId>`` of a covergroup instance: the covergroup's name, the module or package declaring it, and where the
	covergroup and the instance are declared.

	It is a value, as a path is: it names no parent.
	"""

	_name:             str          #: Name of the covergroup.
	_moduleName:       str          #: Name of the module or package declaring the covergroup.
	_instanceSourceID: StatementID  #: Where the covergroup instance is declared.
	_sourceID:         StatementID  #: Where the covergroup is declared.

	def __init__(self, name: str, moduleName: str, instanceSourceID: StatementID, sourceID: StatementID) -> None:
		"""
		Initialize the covergroup identifier.

		:param name:             Name of the covergroup, e.g. ``cg``.
		:param moduleName:       Name of the module or package declaring the covergroup.
		:param instanceSourceID: Where the covergroup instance is declared.
		:param sourceID:         Where the covergroup is declared.
		:raises ValueError:      If parameter ``name`` or ``moduleName`` is ``None``.
		:raises TypeError:       If parameter ``name`` or ``moduleName`` isn't of type :class:`str`.
		:raises ValueError:      If parameter ``instanceSourceID`` or ``sourceID`` is ``None``.
		:raises TypeError:       If parameter ``instanceSourceID`` or ``sourceID`` isn't of type
		                         :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Elements.StatementID`.
		"""
		for parameterName, value in (
			("name",       name),
			("moduleName", moduleName)
		):
			if value is None:
				raise ValueError(f"Parameter '{parameterName}' is None.")
			elif not isinstance(value, str):
				ex = TypeError(f"Parameter '{parameterName}' is not of type 'str'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
				raise ex

		for parameterName, value in (
			("instanceSourceID", instanceSourceID),
			("sourceID",         sourceID)
		):
			if value is None:
				raise ValueError(f"Parameter '{parameterName}' is None.")
			elif not isinstance(value, StatementID):
				ex = TypeError(f"Parameter '{parameterName}' is not of type 'StatementID'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
				raise ex

		self._name =             name
		self._moduleName =       moduleName
		self._instanceSourceID = instanceSourceID
		self._sourceID =         sourceID

	@classmethod
	def Parse(cls, element: _Element) -> Self:
		"""
		Parse a covergroup identifier from its ``<cgId>`` element.

		:param element: The ``<cgId>`` element.
		:returns:       The covergroup identifier.
		"""
		return cls(
			element.attrib["cgName"],
			element.attrib["moduleName"],
			StatementID.Parse(element.find("{*}cginstSourceId")),
			StatementID.Parse(element.find("{*}cgSourceId"))
		)

	@readonly
	def Name(self) -> str:
		"""
		Read-only property to access the name of the covergroup (:attr:`_name`).

		:returns: The name, as declared.
		"""
		return self._name

	@readonly
	def ModuleName(self) -> str:
		"""
		Read-only property to access the name of the module or package declaring the covergroup (:attr:`_moduleName`).

		:returns: The name, as stated.
		"""
		return self._moduleName

	@readonly
	def InstanceSourceID(self) -> StatementID:
		"""
		Read-only property to access where the covergroup instance is declared (:attr:`_instanceSourceID`).

		:returns: The source statement identifier.
		"""
		return self._instanceSourceID

	@readonly
	def SourceID(self) -> StatementID:
		"""
		Read-only property to access where the covergroup is declared (:attr:`_sourceID`).

		:returns: The source statement identifier.
		"""
		return self._sourceID


# A class with a property named like a class - ``CovergroupID`` - can't name that class in the annotation of a field:
# the class body's namespace, where annotations are evaluated, binds the name to the property.
_CovergroupID = CovergroupID


@export
class CovergroupInstance(Base):
	"""
	A ``<cgInstance>`` of a covergroup coverage: an instance of a covergroup - or the covergroup as a whole -, its
	options and parameters, its coverpoints and crosses.
	"""

	_parent:         Nullable[CovergroupCoverage]  #: The covergroup coverage the covergroup instance belongs to.
	_name:           str                           #: Name of the covergroup instance.
	_key:            str                           #: UCIS key of the covergroup instance.
	_options:        CovergroupOptions             #: The options of the covergroup instance.
	_covergroupID:   _CovergroupID                 #: The covergroup and where it and the instance are declared.
	_parameters:     dict[str, str]                #: The parameters of the covergroup instance, by name.
	_alias:          Nullable[str]                 #: An alias of the covergroup instance's name.
	_isExcluded:     bool                          #: Whether the covergroup instance is excluded from the coverage.
	_excludedReason: Nullable[str]                 #: Why the covergroup instance is excluded.
	_coverpoints:    list[Coverpoint]              #: The coverpoints.
	_crosses:        list[Cross]                   #: The crosses.

	def __init__(
		self,
		name: str,
		key: str,
		options: CovergroupOptions,
		covergroupID: CovergroupID,
		parameters: Nullable[Mapping[str, str]] = None,
		alias: Nullable[str] = None,
		excluded: bool = False,
		excludedReason: Nullable[str] = None,
		userAttributes: Nullable[Iterable[UserAttribute]] = None,
		*,
		parent: Nullable[CovergroupCoverage] = None
	) -> None:
		"""
		Initialize the covergroup instance, and append it to the covergroup instances of its covergroup coverage.

		Its coverpoints and crosses are added by creating them with this covergroup instance as their parent.

		:param name:           Name of the covergroup instance, e.g. ``top.cv``.
		:param key:            UCIS key of the covergroup instance.
		:param options:        The options of the covergroup instance.
		:param covergroupID:   The covergroup and where it and the instance are declared.
		:param parameters:     Optional, the parameters of the covergroup instance, by name. Default: ``None``.
		:param alias:          Optional, an alias of the covergroup instance's name. Default: ``None``.
		:param excluded:       Optional, whether the covergroup instance is excluded from the coverage. Default:
		                       ``False``.
		:param excludedReason: Optional, why the covergroup instance is excluded. Default: ``None``.
		:param userAttributes: Optional, the user-defined attributes. Default: ``None``.
		:param parent:         Optional, the covergroup coverage the covergroup instance belongs to. Default: ``None``.
		:raises TypeError:     If parameter ``userAttributes`` isn't iterable.
		:raises TypeError:     If parameter ``userAttributes`` contains an element not of type
		                       :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Elements.UserAttribute`.
		:raises ValueError:    If parameter ``name`` or ``key`` is ``None``.
		:raises TypeError:     If parameter ``name`` or ``key`` isn't of type :class:`str`.
		:raises ValueError:    If parameter ``options`` is ``None``.
		:raises TypeError:     If parameter ``options`` isn't of type
		                       :class:`~pyEDAA.Reports.CodeCoverage.UCIS.CoverOptions.CovergroupOptions`.
		:raises ValueError:    If parameter ``covergroupID`` is ``None``.
		:raises TypeError:     If parameter ``covergroupID`` isn't of type :class:`CovergroupID`.
		:raises TypeError:     If parameter ``alias`` or ``excludedReason`` isn't of type :class:`str`.
		:raises ValueError:    If parameter ``excluded`` is ``None``.
		:raises TypeError:     If parameter ``excluded`` isn't of type :class:`bool`.
		:raises TypeError:     If parameter ``parent`` isn't of type :class:`CovergroupCoverage`.
		:raises TypeError:     If parameter ``parameters`` isn't a mapping.
		:raises TypeError:     If parameter ``parameters`` contains a name or value not of type :class:`str`.
		"""
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
		elif not isinstance(options, CovergroupOptions):
			ex = TypeError(f"Parameter 'options' is not of type 'CovergroupOptions'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(options)}'.")
			raise ex

		if covergroupID is None:
			raise ValueError(f"Parameter 'covergroupID' is None.")
		elif not isinstance(covergroupID, CovergroupID):
			ex = TypeError(f"Parameter 'covergroupID' is not of type 'CovergroupID'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(covergroupID)}'.")
			raise ex

		for parameterName, value in (
			("alias",          alias),
			("excludedReason", excludedReason)
		):
			if value is not None and not isinstance(value, str):
				ex = TypeError(f"Parameter '{parameterName}' is not of type 'str'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
				raise ex

		if excluded is None:
			raise ValueError(f"Parameter 'excluded' is None.")
		elif not isinstance(excluded, bool):
			ex = TypeError(f"Parameter 'excluded' is not of type 'bool'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(excluded)}'.")
			raise ex

		if parent is not None and not isinstance(parent, CovergroupCoverage):
			ex = TypeError(f"Parameter 'parent' is not of type 'CovergroupCoverage'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =         parent
		self._name =           name
		self._key =            key
		self._options =        options
		self._covergroupID =   covergroupID
		self._parameters =     {}
		self._alias =          alias
		self._isExcluded =     excluded
		self._excludedReason = excludedReason
		self._coverpoints =    []
		self._crosses =        []

		if parameters is not None:
			if not isinstance(parameters, Mapping):
				ex = TypeError(f"Parameter 'parameters' is not a mapping.")
				ex.add_note(f"Got type '{getFullyQualifiedName(parameters)}'.")
				raise ex

			for parameterName, value in parameters.items():
				if not isinstance(parameterName, str) or not isinstance(value, str):
					ex = TypeError(f"Parameter 'parameters' contains a name or value not of type 'str'.")
					ex.add_note(f"Got types '{getFullyQualifiedName(parameterName)}' and '{getFullyQualifiedName(value)}'.")
					raise ex

				self._parameters[parameterName] = value

		if parent is not None:
			parent._instances.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[CovergroupCoverage] = None) -> Self:
		"""
		Parse a covergroup instance, its coverpoints and crosses from its ``<cgInstance>`` element.

		:param element:            The ``<cgInstance>`` element.
		:param parent:             Optional, the covergroup coverage the covergroup instance belongs to. Default: ``None``.
		:returns:                  The covergroup instance.
		:raises CodeCoverageError: If a user-defined attribute's value isn't of the type the attribute states.
		"""
		instance = cls(
			element.attrib["name"],
			element.attrib["key"],
			CovergroupOptions.Parse(element.find("{*}options")),
			CovergroupID.Parse(element.find("{*}cgId")),
			{
				parameterElement.findtext("{*}name"): parameterElement.findtext("{*}value")
				for parameterElement in element.iterfind("{*}cgParms")
			},
			element.attrib.get("alias"),
			cls._ParseBoolean(element.attrib.get("excluded", "false")),
			element.attrib.get("excludedReason"),
			cls._ParseUserAttributes(element),
			parent=parent
		)

		for coverpointElement in element.iterfind("{*}coverpoint"):
			Coverpoint.Parse(coverpointElement, parent=instance)

		for crossElement in element.iterfind("{*}cross"):
			Cross.Parse(crossElement, parent=instance)

		return instance

	@readonly
	def Parent(self) -> Nullable[CovergroupCoverage]:
		"""
		Read-only property to access the covergroup coverage the covergroup instance belongs to (:attr:`_parent`).

		:returns: The covergroup coverage; ``None``, if the covergroup instance belongs to none.
		"""
		return self._parent

	@readonly
	def Name(self) -> str:
		"""
		Read-only property to access the name of the covergroup instance (:attr:`_name`).

		:returns: The name, as stated.
		"""
		return self._name

	@readonly
	def Key(self) -> str:
		"""
		Read-only property to access the UCIS key of the covergroup instance (:attr:`_key`).

		:returns: The key, as stated.
		"""
		return self._key

	@readonly
	def Options(self) -> CovergroupOptions:
		"""
		Read-only property to access the options of the covergroup instance (:attr:`_options`).

		:returns: The options.
		"""
		return self._options

	@readonly
	def CovergroupID(self) -> CovergroupID:
		"""
		Read-only property to access the covergroup and where it and the instance are declared (:attr:`_covergroupID`).

		:returns: The covergroup identifier.
		"""
		return self._covergroupID

	@readonly
	def Parameters(self) -> dict[str, str]:
		"""
		Read-only property to access the parameters of the covergroup instance (:attr:`_parameters`).

		:returns: The parameters' values, by name.
		"""
		return self._parameters

	@readonly
	def Alias(self) -> Nullable[str]:
		"""
		Read-only property to access the alias of the covergroup instance's name (:attr:`_alias`).

		:returns: The alias; ``None``, if the report states none.
		"""
		return self._alias

	@readonly
	def IsExcluded(self) -> bool:
		"""
		Read-only property to access whether the covergroup instance is excluded from the coverage (:attr:`_isExcluded`).

		:returns: ``True``, if excluded.
		"""
		return self._isExcluded

	@readonly
	def ExcludedReason(self) -> Nullable[str]:
		"""
		Read-only property to access why the covergroup instance is excluded (:attr:`_excludedReason`).

		:returns: The reason; ``None``, if the report states none.
		"""
		return self._excludedReason

	@readonly
	def Coverpoints(self) -> list[Coverpoint]:
		"""
		Read-only property to access the coverpoints (:attr:`_coverpoints`).

		:returns: The coverpoints, in the order the report lists them.
		"""
		return self._coverpoints

	@readonly
	def Crosses(self) -> list[Cross]:
		"""
		Read-only property to access the crosses (:attr:`_crosses`).

		:returns: The crosses, in the order the report lists them.
		"""
		return self._crosses
