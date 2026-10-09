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
The instances of the UCIS XML interchange format, each with its coverage of each kind, and the source files the
report's statement identifiers name by their ID.
"""
from __future__                                import annotations

from pathlib                                   import Path
from typing                                    import TYPE_CHECKING, Iterable, Mapping, Optional as Nullable, Self

from lxml.etree                                import _Element
from pyTooling.Common                          import getFullyQualifiedName
from pyTooling.Decorators                      import export, readonly
from pyTooling.MetaClasses                     import ExtendedType

from pyEDAA.Reports.CodeCoverage.UCIS.Blocks   import BlockCoverage
from pyEDAA.Reports.CodeCoverage.UCIS.Branches import BranchCoverage
from pyEDAA.Reports.CodeCoverage.UCIS.Elements import Base, StatementID, UserAttribute

if TYPE_CHECKING:
	from pyEDAA.Reports.CodeCoverage.UCIS        import Report

# A class with a property named like a class - ``Path`` - can't name that class in the annotation of a field: the class
# body's namespace, where annotations are evaluated, binds the name to the property.
_Path = Path


@export
class SourceFile(metaclass=ExtendedType, slots=True):
	"""
	A ``<sourceFiles>`` of the report: a source file's path and the ID, by which statement identifiers name it.
	"""

	_parent:       Nullable[Report]  #: The report the source file belongs to.
	_path:         _Path             #: Path of the source file.
	_sourceFileID: int               #: ID of the source file.

	def __init__(self, path: Path, sourceFileID: int, *, parent: Nullable[Report] = None) -> None:
		"""
		Initialize the source file, and add it to the source files of its report.

		:param path:               Path of the source file, as the tool states it.
		:param sourceFileID:       ID of the source file, counted from 1.
		:param parent:             Optional, the report the source file belongs to; the source file is added to its source
		                           files. Default: ``None``.
		:raises ValueError:        If parameter ``path`` is ``None``.
		:raises TypeError:         If parameter ``path`` isn't of type :class:`~pathlib.Path`.
		:raises ValueError:        If parameter ``sourceFileID`` is ``None``.
		:raises TypeError:         If parameter ``sourceFileID`` isn't of type :class:`int`.
		:raises ValueError:        If parameter ``sourceFileID`` is less than 1.
		:raises TypeError:         If parameter ``parent`` isn't of type :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Report`.
		"""
		from pyEDAA.Reports.CodeCoverage.UCIS import Report

		if path is None:
			raise ValueError(f"Parameter 'path' is None.")
		elif not isinstance(path, Path):
			ex = TypeError(f"Parameter 'path' is not of type 'Path'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(path)}'.")
			raise ex

		if sourceFileID is None:
			raise ValueError(f"Parameter 'sourceFileID' is None.")
		elif not isinstance(sourceFileID, int) or isinstance(sourceFileID, bool):
			ex = TypeError(f"Parameter 'sourceFileID' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(sourceFileID)}'.")
			raise ex
		elif sourceFileID < 1:
			ex = ValueError(f"Parameter 'sourceFileID' is less than 1.")
			ex.add_note(f"Got value '{sourceFileID}'.")
			raise ex

		if parent is not None and not isinstance(parent, Report):
			ex = TypeError(f"Parameter 'parent' is not of type 'Report'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =       parent
		self._path =         path
		self._sourceFileID = sourceFileID

		if parent is not None:
			parent._sourceFiles[sourceFileID] = self

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[Report] = None) -> Self:
		"""
		Parse a source file from its ``<sourceFiles>`` element.

		:param element: The ``<sourceFiles>`` element.
		:param parent:  Optional, the report the source file belongs to. Default: ``None``.
		:returns:       The source file.
		"""
		return cls(Path(element.attrib["fileName"]), int(element.attrib["id"]), parent=parent)

	@readonly
	def Parent(self) -> Nullable[Report]:
		"""
		Read-only property to access the report the source file belongs to (:attr:`_parent`).

		:returns: The report; ``None``, if the source file belongs to none.
		"""
		return self._parent

	@readonly
	def Path(self) -> Path:
		"""
		Read-only property to access the path of the source file (:attr:`_path`).

		:returns: The path, as the tool states it: absolute, or relative to the directory it ran in.
		"""
		return self._path

	@readonly
	def SourceFileID(self) -> int:
		"""
		Read-only property to access the ID of the source file (:attr:`_sourceFileID`).

		:returns: The ID, by which statement identifiers name the file.
		"""
		return self._sourceFileID


@export
class InstanceCoverage(Base):
	"""
	An ``<instanceCoverages>`` of the report: an instance of a design unit, where it is instantiated, its parameters, and
	its coverage of each kind.

	An instance names the instance it is instantiated in by that instance's ID.
	"""

	_parent:           Nullable[Report]      #: The report the instance belongs to.
	_name:             str                   #: Name of the instance.
	_key:              str                   #: UCIS key of the instance.
	_id:               StatementID           #: Where the instance is instantiated.
	_instanceID:       Nullable[int]         #: ID of the instance.
	_alias:            Nullable[str]         #: An alias of the instance's name.
	_moduleName:       Nullable[str]         #: Name of the design unit the instance instantiates.
	_parentInstanceID: Nullable[int]         #: ID of the instance this one is instantiated in.
	_designParameters: dict[str, str]        #: The design parameters of the instance, by name.
	_blockCoverages:   list[BlockCoverage]   #: The statement and block coverage, per metric mode.
	_branchCoverages:  list[BranchCoverage]  #: The branch coverage, per metric mode.

	def __init__(
		self,
		name: str,
		key: str,
		statementID: StatementID,
		instanceID: Nullable[int] = None,
		alias: Nullable[str] = None,
		moduleName: Nullable[str] = None,
		parentInstanceID: Nullable[int] = None,
		designParameters: Nullable[Mapping[str, str]] = None,
		userAttributes: Nullable[Iterable[UserAttribute]] = None,
		*,
		parent: Nullable[Report] = None
	) -> None:
		"""
		Initialize the instance, and append it to the instances of its report.

		Its coverage of each kind is added by creating it with this instance as its parent.

		:param name:             Name of the instance, e.g. ``top.dut``.
		:param key:              UCIS key of the instance.
		:param statementID:      Where the instance is instantiated.
		:param instanceID:       Optional, ID of the instance. Default: ``None``.
		:param alias:            Optional, an alias of the instance's name. Default: ``None``.
		:param moduleName:       Optional, name of the design unit the instance instantiates. Default: ``None``.
		:param parentInstanceID: Optional, ID of the instance this one is instantiated in. Default: ``None``.
		:param designParameters: Optional, the design parameters of the instance, by name, e.g. ``{"WIDTH": "8"}``.
		                         Default: ``None``.
		:param userAttributes:   Optional, the user-defined attributes. Default: ``None``.
		:param parent:           Optional, the report the instance belongs to; the instance is appended to its instances.
		                         Default: ``None``.
		:raises TypeError:       If parameter ``userAttributes`` isn't iterable.
		:raises TypeError:       If parameter ``userAttributes`` contains an element not of type
		                         :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Elements.UserAttribute`.
		:raises ValueError:      If parameter ``name`` is ``None``.
		:raises TypeError:       If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError:      If parameter ``key`` is ``None``.
		:raises TypeError:       If parameter ``key`` isn't of type :class:`str`.
		:raises ValueError:      If parameter ``statementID`` is ``None``.
		:raises TypeError:       If parameter ``statementID`` isn't of type
		                         :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Elements.StatementID`.
		:raises TypeError:       If parameter ``instanceID`` isn't of type :class:`int`.
		:raises TypeError:       If parameter ``alias`` isn't of type :class:`str`.
		:raises TypeError:       If parameter ``moduleName`` isn't of type :class:`str`.
		:raises TypeError:       If parameter ``parentInstanceID`` isn't of type :class:`int`.
		:raises TypeError:       If parameter ``designParameters`` isn't a mapping.
		:raises TypeError:       If parameter ``designParameters`` contains a name or value not of type :class:`str`.
		:raises TypeError:       If parameter ``parent`` isn't of type :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Report`.
		"""
		from pyEDAA.Reports.CodeCoverage.UCIS import Report

		super().__init__(userAttributes)

		if name is None:
			raise ValueError(f"Parameter 'name' is None.")
		elif not isinstance(name, str):
			ex = TypeError(f"Parameter 'name' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(name)}'.")
			raise ex

		if key is None:
			raise ValueError(f"Parameter 'key' is None.")
		elif not isinstance(key, str):
			ex = TypeError(f"Parameter 'key' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(key)}'.")
			raise ex

		if statementID is None:
			raise ValueError(f"Parameter 'statementID' is None.")
		elif not isinstance(statementID, StatementID):
			ex = TypeError(f"Parameter 'statementID' is not of type 'StatementID'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(statementID)}'.")
			raise ex

		if instanceID is not None and (not isinstance(instanceID, int) or isinstance(instanceID, bool)):
			ex = TypeError(f"Parameter 'instanceID' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(instanceID)}'.")
			raise ex

		if alias is not None and not isinstance(alias, str):
			ex = TypeError(f"Parameter 'alias' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(alias)}'.")
			raise ex

		if moduleName is not None and not isinstance(moduleName, str):
			ex = TypeError(f"Parameter 'moduleName' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(moduleName)}'.")
			raise ex

		if parentInstanceID is not None and (not isinstance(parentInstanceID, int) or isinstance(parentInstanceID, bool)):
			ex = TypeError(f"Parameter 'parentInstanceID' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parentInstanceID)}'.")
			raise ex

		if parent is not None and not isinstance(parent, Report):
			ex = TypeError(f"Parameter 'parent' is not of type 'Report'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =           parent
		self._name =             name
		self._key =              key
		self._id =               statementID
		self._instanceID =       instanceID
		self._alias =            alias
		self._moduleName =       moduleName
		self._parentInstanceID = parentInstanceID
		self._designParameters = {}
		self._blockCoverages =   []
		self._branchCoverages =  []

		if designParameters is not None:
			if not isinstance(designParameters, Mapping):
				ex = TypeError(f"Parameter 'designParameters' is not a mapping.")
				ex.add_note(f"Got type '{getFullyQualifiedName(designParameters)}'.")
				raise ex

			for parameterName, value in designParameters.items():
				if not isinstance(parameterName, str) or not isinstance(value, str):
					ex = TypeError(f"Parameter 'designParameters' contains a name or value not of type 'str'.")
					ex.add_note(f"Got types '{getFullyQualifiedName(parameterName)}' and '{getFullyQualifiedName(value)}'.")
					raise ex

				self._designParameters[parameterName] = value

		if parent is not None:
			parent._instances.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[Report] = None) -> Self:
		"""
		Parse an instance and its coverage of each kind from its ``<instanceCoverages>`` element.

		:param element:            The ``<instanceCoverages>`` element.
		:param parent:             Optional, the report the instance belongs to. Default: ``None``.
		:returns:                  The instance.
		:raises CodeCoverageError: If a user-defined attribute's value isn't of the type the attribute states.
		"""
		attributes =       element.attrib
		instanceID =       attributes.get("instanceId")
		parentInstanceID = attributes.get("parentInstanceId")
		designParameters = {
			parameterElement.findtext("{*}name"): parameterElement.findtext("{*}value")
			for parameterElement in element.iterfind("{*}designParameter")
		}

		instance = cls(
			attributes["name"],
			attributes["key"],
			StatementID.Parse(element.find("{*}id")),
			None if instanceID is None else int(instanceID),
			attributes.get("alias"),
			attributes.get("moduleName"),
			None if parentInstanceID is None else int(parentInstanceID),
			designParameters,
			cls._ParseUserAttributes(element),
			parent=parent
		)

		for coverageElement in element.iterfind("{*}blockCoverage"):
			BlockCoverage.Parse(coverageElement, parent=instance)

		for coverageElement in element.iterfind("{*}branchCoverage"):
			BranchCoverage.Parse(coverageElement, parent=instance)

		return instance

	@readonly
	def Parent(self) -> Nullable[Report]:
		"""
		Read-only property to access the report the instance belongs to (:attr:`_parent`).

		:returns: The report; ``None``, if the instance belongs to none.
		"""
		return self._parent

	@readonly
	def Name(self) -> str:
		"""
		Read-only property to access the name of the instance (:attr:`_name`).

		:returns: The name, as stated.
		"""
		return self._name

	@readonly
	def Key(self) -> str:
		"""
		Read-only property to access the UCIS key of the instance (:attr:`_key`).

		:returns: The key, as stated.
		"""
		return self._key

	@readonly
	def ID(self) -> StatementID:
		"""
		Read-only property to access where the instance is instantiated (:attr:`_id`).

		:returns: The source statement identifier.
		"""
		return self._id

	@readonly
	def InstanceID(self) -> Nullable[int]:
		"""
		Read-only property to access the ID of the instance (:attr:`_instanceID`).

		:returns: The ID; ``None``, if the report states none.
		"""
		return self._instanceID

	@readonly
	def Alias(self) -> Nullable[str]:
		"""
		Read-only property to access the alias of the instance's name (:attr:`_alias`).

		:returns: The alias; ``None``, if the report states none.
		"""
		return self._alias

	@readonly
	def ModuleName(self) -> Nullable[str]:
		"""
		Read-only property to access the name of the design unit the instance instantiates (:attr:`_moduleName`).

		:returns: The design unit's name; ``None``, if the report states none.
		"""
		return self._moduleName

	@readonly
	def ParentInstanceID(self) -> Nullable[int]:
		"""
		Read-only property to access the ID of the instance this one is instantiated in (:attr:`_parentInstanceID`).

		:returns: The ID; ``None`` for a top-level instance, or if the report states none.
		"""
		return self._parentInstanceID

	@readonly
	def DesignParameters(self) -> dict[str, str]:
		"""
		Read-only property to access the design parameters of the instance (:attr:`_designParameters`).

		:returns: The parameters' values, by name.
		"""
		return self._designParameters

	@readonly
	def BlockCoverages(self) -> list[BlockCoverage]:
		"""
		Read-only property to access the statement and block coverage (:attr:`_blockCoverages`).

		:returns: The block coverages, one per metric mode, in the order the report lists them.
		"""
		return self._blockCoverages

	@readonly
	def BranchCoverages(self) -> list[BranchCoverage]:
		"""
		Read-only property to access the branch coverage (:attr:`_branchCoverages`).

		:returns: The branch coverages, one per metric mode, in the order the report lists them.
		"""
		return self._branchCoverages
