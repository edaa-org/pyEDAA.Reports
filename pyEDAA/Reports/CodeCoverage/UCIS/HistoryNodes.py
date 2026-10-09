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
The history nodes of the UCIS XML interchange format: the tests, which measured the coverage, and the merges of their
coverage, with the tool, the date and how the test ran.
"""
from __future__                                import annotations

from datetime                                  import datetime
from decimal                                   import Decimal
from pathlib                                   import Path
from typing                                    import TYPE_CHECKING, Iterable, Optional as Nullable, Self

from lxml.etree                                import _Element
from pyTooling.Common                          import getFullyQualifiedName
from pyTooling.Decorators                      import export, readonly

from pyEDAA.Reports.CodeCoverage.UCIS.Elements import Base, UserAttribute

if TYPE_CHECKING:
	from pyEDAA.Reports.CodeCoverage.UCIS        import Report


@export
class HistoryNode(Base):
	"""
	A ``<historyNodes>`` of the report: a test, which measured coverage, or a merge of coverage, its tool, its date and -
	if the report says - how the test ran.

	A history node names the node it belongs to - e.g. the merge, which merged it - by the ID of that node.
	"""

	_parent:            Nullable[Report]     #: The report the history node belongs to.
	_historyNodeID:     int                  #: ID of the history node.
	_logicalName:       str                  #: Name of the history node, e.g. of the test.
	_testStatus:        bool                 #: Whether the test passed.
	_date:              datetime             #: When the test ran.
	_toolCategory:      str                  #: Kind of the tool, e.g. ``simulator``.
	_ucisVersion:       str                  #: Version of the UCIS, in which the tool measured the coverage.
	_vendorID:          str                  #: ID of the tool's vendor.
	_vendorTool:        str                  #: Name of the tool.
	_vendorToolVersion: str                  #: Version of the tool.
	_parentID:          Nullable[int]        #: ID of the history node this one belongs to.
	_physicalName:      Nullable[Path]       #: Path of the coverage database the history node wrote.
	_kind:              Nullable[str]        #: Kind of the history node, e.g. a test or a merge.
	_simulationTime:    Nullable[float]      #: How long the test ran, in simulated time.
	_timeUnit:          Nullable[str]        #: Unit of the simulated time.
	_runDirectory:      Nullable[Path]       #: The directory the test ran in.
	_cpuTime:           Nullable[float]      #: How long the test ran, in CPU time.
	_seed:              Nullable[str]        #: The seed of the test's random numbers.
	_command:           Nullable[str]        #: The command, which ran the test.
	_arguments:         Nullable[str]        #: The command line arguments of the test.
	_compulsory:        Nullable[str]        #: Whether the test must run.
	_userName:          Nullable[str]        #: Name of the user, who ran the test.
	_cost:              Nullable[Decimal]    #: Cost of the test.
	_sameTests:         Nullable[int]        #: ID of a test this one is equivalent to.
	_comment:           Nullable[str]        #: A comment.

	def __init__(
		self,
		historyNodeID: int,
		logicalName: str,
		testStatus: bool,
		date: datetime,
		toolCategory: str,
		ucisVersion: str,
		vendorID: str,
		vendorTool: str,
		vendorToolVersion: str,
		parentID: Nullable[int] = None,
		physicalName: Nullable[Path] = None,
		kind: Nullable[str] = None,
		simulationTime: Nullable[float] = None,
		timeUnit: Nullable[str] = None,
		runDirectory: Nullable[Path] = None,
		cpuTime: Nullable[float] = None,
		seed: Nullable[str] = None,
		command: Nullable[str] = None,
		arguments: Nullable[str] = None,
		compulsory: Nullable[str] = None,
		userName: Nullable[str] = None,
		cost: Nullable[Decimal] = None,
		sameTests: Nullable[int] = None,
		comment: Nullable[str] = None,
		userAttributes: Nullable[Iterable[UserAttribute]] = None,
		*,
		parent: Nullable[Report] = None
	) -> None:
		"""
		Initialize the history node, and add it to the history nodes of its report.

		:param historyNodeID:     ID of the history node.
		:param logicalName:       Name of the history node, e.g. of the test.
		:param testStatus:        Whether the test passed.
		:param date:              When the test ran.
		:param toolCategory:      Kind of the tool, e.g. ``simulator``.
		:param ucisVersion:       Version of the UCIS, in which the tool measured the coverage, e.g. ``1.0``.
		:param vendorID:          ID of the tool's vendor.
		:param vendorTool:        Name of the tool.
		:param vendorToolVersion: Version of the tool.
		:param parentID:          Optional, ID of the history node this one belongs to. Default: ``None``.
		:param physicalName:      Optional, path of the coverage database the history node wrote. Default: ``None``.
		:param kind:              Optional, kind of the history node, e.g. a test or a merge. Default: ``None``.
		:param simulationTime:    Optional, how long the test ran, in simulated time. Default: ``None``.
		:param timeUnit:          Optional, unit of the simulated time, e.g. ``ns``. Default: ``None``.
		:param runDirectory:      Optional, the directory the test ran in. Default: ``None``.
		:param cpuTime:           Optional, how long the test ran, in CPU time. Default: ``None``.
		:param seed:              Optional, the seed of the test's random numbers. Default: ``None``.
		:param command:           Optional, the command, which ran the test. Default: ``None``.
		:param arguments:         Optional, the command line arguments of the test. Default: ``None``.
		:param compulsory:        Optional, whether the test must run. Default: ``None``.
		:param userName:          Optional, name of the user, who ran the test. Default: ``None``.
		:param cost:              Optional, cost of the test. Default: ``None``.
		:param sameTests:         Optional, ID of a test this one is equivalent to. Default: ``None``.
		:param comment:           Optional, a comment. Default: ``None``.
		:param userAttributes:    Optional, the user-defined attributes. Default: ``None``.
		:param parent:            Optional, the report the history node belongs to; the history node is added to its
		                          history nodes. Default: ``None``.
		:raises TypeError:        If parameter ``userAttributes`` isn't iterable.
		:raises TypeError:        If parameter ``userAttributes`` contains an element not of type
		                          :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Elements.UserAttribute`.
		:raises ValueError:       If parameter ``historyNodeID`` is ``None``.
		:raises TypeError:        If parameter ``historyNodeID`` isn't of type :class:`int`.
		:raises ValueError:       If parameter ``historyNodeID`` is negative.
		:raises ValueError:       If parameter ``testStatus`` is ``None``.
		:raises TypeError:        If parameter ``testStatus`` isn't of type :class:`bool`.
		:raises ValueError:       If parameter ``date`` is ``None``.
		:raises TypeError:        If parameter ``date`` isn't of type :class:`~datetime.datetime`.
		:raises ValueError:       If parameter ``logicalName``, ``toolCategory``, ``ucisVersion``, ``vendorID``,
		                          ``vendorTool`` or ``vendorToolVersion`` is ``None``.
		:raises TypeError:        If parameter ``logicalName``, ``toolCategory``, ``ucisVersion``, ``vendorID``,
		                          ``vendorTool`` or ``vendorToolVersion`` isn't of type :class:`str`.
		:raises TypeError:        If parameter ``parentID`` isn't of type :class:`int`.
		:raises ValueError:       If parameter ``parentID`` is negative.
		:raises TypeError:        If parameter ``sameTests`` isn't of type :class:`int`.
		:raises ValueError:       If parameter ``sameTests`` is negative.
		:raises TypeError:        If parameter ``physicalName`` isn't of type :class:`~pathlib.Path`.
		:raises TypeError:        If parameter ``runDirectory`` isn't of type :class:`~pathlib.Path`.
		:raises TypeError:        If parameter ``simulationTime`` isn't of type :class:`float`.
		:raises TypeError:        If parameter ``cpuTime`` isn't of type :class:`float`.
		:raises TypeError:        If parameter ``kind``, ``timeUnit``, ``seed``, ``command``, ``arguments``,
		                          ``compulsory``, ``userName`` or ``comment`` isn't of type :class:`str`.
		:raises TypeError:        If parameter ``cost`` isn't of type :class:`~decimal.Decimal`.
		:raises TypeError:        If parameter ``parent`` isn't of type :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Report`.
		"""
		from pyEDAA.Reports.CodeCoverage.UCIS import Report

		super().__init__(userAttributes)

		if historyNodeID is None:
			raise ValueError(f"Parameter 'historyNodeID' is None.")
		elif not isinstance(historyNodeID, int) or isinstance(historyNodeID, bool):
			ex = TypeError(f"Parameter 'historyNodeID' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(historyNodeID)}'.")
			raise ex
		elif historyNodeID < 0:
			ex = ValueError(f"Parameter 'historyNodeID' is negative.")
			ex.add_note(f"Got value '{historyNodeID}'.")
			raise ex

		if testStatus is None:
			raise ValueError(f"Parameter 'testStatus' is None.")
		elif not isinstance(testStatus, bool):
			ex = TypeError(f"Parameter 'testStatus' is not of type 'bool'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(testStatus)}'.")
			raise ex

		if date is None:
			raise ValueError(f"Parameter 'date' is None.")
		elif not isinstance(date, datetime):
			ex = TypeError(f"Parameter 'date' is not of type 'datetime'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(date)}'.")
			raise ex

		for name, value in (
			("logicalName",       logicalName),
			("toolCategory",      toolCategory),
			("ucisVersion",       ucisVersion),
			("vendorID",          vendorID),
			("vendorTool",        vendorTool),
			("vendorToolVersion", vendorToolVersion)
		):
			if value is None:
				raise ValueError(f"Parameter '{name}' is None.")
			elif not isinstance(value, str):
				ex = TypeError(f"Parameter '{name}' is not of type 'str'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
				raise ex

		if parentID is not None:
			if not isinstance(parentID, int) or isinstance(parentID, bool):
				ex = TypeError(f"Parameter 'parentID' is not of type 'int'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(parentID)}'.")
				raise ex
			elif parentID < 0:
				ex = ValueError(f"Parameter 'parentID' is negative.")
				ex.add_note(f"Got value '{parentID}'.")
				raise ex

		if sameTests is not None:
			if not isinstance(sameTests, int) or isinstance(sameTests, bool):
				ex = TypeError(f"Parameter 'sameTests' is not of type 'int'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(sameTests)}'.")
				raise ex
			elif sameTests < 0:
				ex = ValueError(f"Parameter 'sameTests' is negative.")
				ex.add_note(f"Got value '{sameTests}'.")
				raise ex

		if physicalName is not None and not isinstance(physicalName, Path):
			ex = TypeError(f"Parameter 'physicalName' is not of type 'Path'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(physicalName)}'.")
			raise ex

		if runDirectory is not None and not isinstance(runDirectory, Path):
			ex = TypeError(f"Parameter 'runDirectory' is not of type 'Path'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(runDirectory)}'.")
			raise ex

		if simulationTime is not None and not isinstance(simulationTime, float):
			ex = TypeError(f"Parameter 'simulationTime' is not of type 'float'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(simulationTime)}'.")
			raise ex

		if cpuTime is not None and not isinstance(cpuTime, float):
			ex = TypeError(f"Parameter 'cpuTime' is not of type 'float'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(cpuTime)}'.")
			raise ex

		for name, value in (
			("kind",       kind),
			("timeUnit",   timeUnit),
			("seed",       seed),
			("command",    command),
			("arguments",  arguments),
			("compulsory", compulsory),
			("userName",   userName),
			("comment",    comment)
		):
			if value is not None and not isinstance(value, str):
				ex = TypeError(f"Parameter '{name}' is not of type 'str'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
				raise ex

		if cost is not None and not isinstance(cost, Decimal):
			ex = TypeError(f"Parameter 'cost' is not of type 'Decimal'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(cost)}'.")
			raise ex

		if parent is not None and not isinstance(parent, Report):
			ex = TypeError(f"Parameter 'parent' is not of type 'Report'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =            parent
		self._historyNodeID =     historyNodeID
		self._logicalName =       logicalName
		self._testStatus =        testStatus
		self._date =              date
		self._toolCategory =      toolCategory
		self._ucisVersion =       ucisVersion
		self._vendorID =          vendorID
		self._vendorTool =        vendorTool
		self._vendorToolVersion = vendorToolVersion
		self._parentID =          parentID
		self._physicalName =      physicalName
		self._kind =              kind
		self._simulationTime =    simulationTime
		self._timeUnit =          timeUnit
		self._runDirectory =      runDirectory
		self._cpuTime =           cpuTime
		self._seed =              seed
		self._command =           command
		self._arguments =         arguments
		self._compulsory =        compulsory
		self._userName =          userName
		self._cost =              cost
		self._sameTests =         sameTests
		self._comment =           comment

		if parent is not None:
			parent._historyNodes[historyNodeID] = self

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[Report] = None) -> Self:
		"""
		Parse a history node from its ``<historyNodes>`` element.

		:param element:            The ``<historyNodes>`` element.
		:param parent:             Optional, the report the history node belongs to. Default: ``None``.
		:returns:                  The history node.
		:raises CodeCoverageError: If a user-defined attribute's value isn't of the type the attribute states.
		"""
		attributes =     element.attrib
		parentID =       attributes.get("parentId")
		physicalName =   attributes.get("physicalName")
		simulationTime = attributes.get("simtime")
		runDirectory =   attributes.get("runCwd")
		cpuTime =        attributes.get("cpuTime")
		cost =           attributes.get("cost")
		sameTests =      attributes.get("sameTests")

		return cls(
			int(attributes["historyNodeId"]),
			attributes["logicalName"],
			cls._ParseBoolean(attributes["testStatus"]),
			datetime.fromisoformat(attributes["date"]),
			attributes["toolCategory"],
			attributes["ucisVersion"],
			attributes["vendorId"],
			attributes["vendorTool"],
			attributes["vendorToolVersion"],
			None if parentID is None else int(parentID),
			None if physicalName is None else Path(physicalName),
			attributes.get("kind"),
			None if simulationTime is None else float(simulationTime),
			attributes.get("timeunit"),
			None if runDirectory is None else Path(runDirectory),
			None if cpuTime is None else float(cpuTime),
			attributes.get("seed"),
			attributes.get("cmd"),
			attributes.get("args"),
			attributes.get("compulsory"),
			attributes.get("userName"),
			None if cost is None else Decimal(cost),
			None if sameTests is None else int(sameTests),
			attributes.get("comment"),
			cls._ParseUserAttributes(element),
			parent=parent
		)

	@readonly
	def Parent(self) -> Nullable[Report]:
		"""
		Read-only property to access the report the history node belongs to (:attr:`_parent`).

		:returns: The report; ``None``, if the history node belongs to none.
		"""
		return self._parent

	@readonly
	def HistoryNodeID(self) -> int:
		"""
		Read-only property to access the ID of the history node (:attr:`_historyNodeID`).

		:returns: The ID, by which bins name the tests, which covered them.
		"""
		return self._historyNodeID

	@readonly
	def LogicalName(self) -> str:
		"""
		Read-only property to access the name of the history node (:attr:`_logicalName`).

		:returns: The name, e.g. of the test.
		"""
		return self._logicalName

	@readonly
	def TestStatus(self) -> bool:
		"""
		Read-only property to access whether the test passed (:attr:`_testStatus`).

		:returns: ``True``, if the test passed.
		"""
		return self._testStatus

	@readonly
	def Date(self) -> datetime:
		"""
		Read-only property to access when the test ran (:attr:`_date`).

		:returns: The date and time.
		"""
		return self._date

	@readonly
	def ToolCategory(self) -> str:
		"""
		Read-only property to access the kind of the tool (:attr:`_toolCategory`).

		:returns: The kind, as stated.
		"""
		return self._toolCategory

	@readonly
	def UCISVersion(self) -> str:
		"""
		Read-only property to access the UCIS version, in which the tool measured the coverage (:attr:`_ucisVersion`).

		:returns: The version, as stated.
		"""
		return self._ucisVersion

	@readonly
	def VendorID(self) -> str:
		"""
		Read-only property to access the ID of the tool's vendor (:attr:`_vendorID`).

		:returns: The ID, as stated.
		"""
		return self._vendorID

	@readonly
	def VendorTool(self) -> str:
		"""
		Read-only property to access the name of the tool (:attr:`_vendorTool`).

		:returns: The name, as stated.
		"""
		return self._vendorTool

	@readonly
	def VendorToolVersion(self) -> str:
		"""
		Read-only property to access the version of the tool (:attr:`_vendorToolVersion`).

		:returns: The version, as stated.
		"""
		return self._vendorToolVersion

	@readonly
	def ParentID(self) -> Nullable[int]:
		"""
		Read-only property to access the ID of the history node this one belongs to (:attr:`_parentID`).

		:returns: The ID, e.g. of the merge, which merged this one; ``None``, if the report states none.
		"""
		return self._parentID

	@readonly
	def PhysicalName(self) -> Nullable[Path]:
		"""
		Read-only property to access the path of the coverage database the history node wrote (:attr:`_physicalName`).

		:returns: The path, as stated; ``None``, if the report states none.
		"""
		return self._physicalName

	@readonly
	def Kind(self) -> Nullable[str]:
		"""
		Read-only property to access the kind of the history node (:attr:`_kind`).

		:returns: The kind, as stated; ``None``, if the report states none.
		"""
		return self._kind

	@readonly
	def SimulationTime(self) -> Nullable[float]:
		"""
		Read-only property to access how long the test ran in simulated time (:attr:`_simulationTime`).

		:returns: The time, in :attr:`TimeUnit`; ``None``, if the report states none.
		"""
		return self._simulationTime

	@readonly
	def TimeUnit(self) -> Nullable[str]:
		"""
		Read-only property to access the unit of the simulated time (:attr:`_timeUnit`).

		:returns: The unit, e.g. ``ns``; ``None``, if the report states none.
		"""
		return self._timeUnit

	@readonly
	def RunDirectory(self) -> Nullable[Path]:
		"""
		Read-only property to access the directory the test ran in (:attr:`_runDirectory`).

		It is a path on the machine the coverage was measured on, so it may not exist where the report is read.

		:returns: The directory; ``None``, if the report states none.
		"""
		return self._runDirectory

	@readonly
	def CPUTime(self) -> Nullable[float]:
		"""
		Read-only property to access how long the test ran in CPU time (:attr:`_cpuTime`).

		:returns: The time; ``None``, if the report states none.
		"""
		return self._cpuTime

	@readonly
	def Seed(self) -> Nullable[str]:
		"""
		Read-only property to access the seed of the test's random numbers (:attr:`_seed`).

		:returns: The seed; ``None``, if the report states none.
		"""
		return self._seed

	@readonly
	def Command(self) -> Nullable[str]:
		"""
		Read-only property to access the command, which ran the test (:attr:`_command`).

		:returns: The command; ``None``, if the report states none.
		"""
		return self._command

	@readonly
	def Arguments(self) -> Nullable[str]:
		"""
		Read-only property to access the command line arguments of the test (:attr:`_arguments`).

		:returns: The arguments; ``None``, if the report states none.
		"""
		return self._arguments

	@readonly
	def Compulsory(self) -> Nullable[str]:
		"""
		Read-only property to access whether the test must run (:attr:`_compulsory`).

		:returns: The value, as stated; ``None``, if the report states none.
		"""
		return self._compulsory

	@readonly
	def UserName(self) -> Nullable[str]:
		"""
		Read-only property to access the name of the user, who ran the test (:attr:`_userName`).

		:returns: The name; ``None``, if the report states none.
		"""
		return self._userName

	@readonly
	def Cost(self) -> Nullable[Decimal]:
		"""
		Read-only property to access the cost of the test (:attr:`_cost`).

		:returns: The cost; ``None``, if the report states none.
		"""
		return self._cost

	@readonly
	def SameTests(self) -> Nullable[int]:
		"""
		Read-only property to access the ID of a test this one is equivalent to (:attr:`_sameTests`).

		:returns: The ID; ``None``, if the report states none.
		"""
		return self._sameTests

	@readonly
	def Comment(self) -> Nullable[str]:
		"""
		Read-only property to access the comment (:attr:`_comment`).

		:returns: The comment; ``None``, if the report states none.
		"""
		return self._comment
