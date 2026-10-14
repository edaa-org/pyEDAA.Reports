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
The elements of Aldec's UCDB XML format beside the scopes and bins: the history nodes, the commands, the attributes
every element may state, the kinds of scopes and bins, and the base-class of the named elements.

The kinds of scopes, bins and source languages are named as the UCIS standard names them in its C API, without the
prefix ``UCIS_``, e.g. ``DU_MODULE`` for ``UCIS_DU_MODULE``.
"""
from __future__                                      import annotations

from enum                                            import IntEnum
from pathlib                                         import Path
from typing                                          import TYPE_CHECKING, Generic, Mapping, Optional as Nullable, Self
from typing                                          import TypeVar

from lxml.etree                                      import _Element
from pyTooling.Common                                import getFullyQualifiedName, StringEnum
from pyTooling.Decorators                            import export, readonly
from pyTooling.MetaClasses                           import ExtendedType, abstractclass

from pyEDAA.Reports.CodeCoverage                     import CodeCoverageError

if TYPE_CHECKING:
	from pyEDAA.Reports.CodeCoverage.AldecUCDB       import Report


__all__ = ["NAMESPACE", "NAMESPACES", "HistoryNodeParentType"]

NAMESPACE = "www.aldec.com"            #: The XML namespace of the format's elements.
NAMESPACES = {"ux": NAMESPACE}         #: The XML namespaces of the format by their prefix, for finding elements.

HistoryNodeParentType = TypeVar("HistoryNodeParentType", bound="Report | HistoryNode")
"""A type variable for the parent of a :class:`HistoryNode`: a :class:`~pyEDAA.Reports.CodeCoverage.AldecUCDB.Report`
or a :class:`HistoryNode`."""


@export
class ScopeType(StringEnum):
	"""
	Kind of a ``<ux:scope>``, as its ``type`` states: a design unit, an instance of one, or a scope of a coverage kind.
	"""

	Toggle =                 "TOGGLE"           #: Toggle coverage of a signal.
	Branch =                 "BRANCH"           #: Branch coverage of a branching statement.
	Expression =             "EXPR"             #: Expression coverage.
	Condition =              "COND"             #: Condition coverage.
	Instance =               "INSTANCE"         #: An instance of a design unit, e.g. of a Verilog module.
	Process =                "PROCESS"          #: A process, e.g. a Verilog ``always`` block.
	Block =                  "BLOCK"            #: A block, e.g. a VHDL ``block`` statement.
	Function =               "FUNCTION"         #: A function.
	ForkJoin =               "FORKJOIN"         #: A Verilog ``fork ... join`` block.
	Generate =               "GENERATE"         #: A generate block.
	Generic =                "GENERIC"          #: A scope of a generic kind.
	Class =                  "CLASS"            #: A SystemVerilog class.
	CoverGroup =             "COVERGROUP"       #: A SystemVerilog covergroup type.
	CoverInstance =          "COVERINSTANCE"    #: An instance of a SystemVerilog covergroup.
	CoverPoint =             "COVERPOINT"       #: A SystemVerilog coverpoint.
	Cross =                  "CROSS"            #: A SystemVerilog cross coverage.
	Cover =                  "COVER"            #: A cover directive.
	Assert =                 "ASSERT"           #: An assertion.
	Program =                "PROGRAM"          #: An instance of a SystemVerilog program.
	Package =                "PACKAGE"          #: An instance of a package.
	Task =                   "TASK"             #: A Verilog task.
	Interface =              "INTERFACE"        #: An instance of a SystemVerilog interface.
	FSM =                    "FSM"              #: A finite state machine.
	DesignUnitModule =       "DU_MODULE"        #: Design unit: a Verilog module.
	DesignUnitArchitecture = "DU_ARCH"          #: Design unit: a VHDL architecture.
	DesignUnitPackage =      "DU_PACKAGE"       #: Design unit: a package.
	DesignUnitProgram =      "DU_PROGRAM"       #: Design unit: a SystemVerilog program.
	DesignUnitInterface =    "DU_INTERFACE"     #: Design unit: a SystemVerilog interface.
	FSMStates =              "FSM_STATES"       #: The states of a finite state machine.
	FSMTransitions =         "FSM_TRANS"        #: The transitions of a finite state machine.
	CoverBlock =             "COVBLOCK"         #: A block of coverage items.
	CoverGroupBinScope =     "CVGBINSCOPE"      #: A scope of covergroup bins.
	IllegalBinScope =        "ILLEGALBINSCOPE"  #: A scope of illegal covergroup bins.
	IgnoreBinScope =         "IGNOREBINSCOPE"   #: A scope of ignored covergroup bins.


@export
class CoverType(StringEnum):
	"""
	Kind of a ``<ux:bin>``, as its ``type`` states.

	A kind Aldec's export has no name for is stated by its value in hexadecimal, as the UCIS C API defines it.
	"""

	CoverGroupBin = "CVGBIN"         #: A bin of a SystemVerilog covergroup.
	CoverBin =      "COVERBIN"       #: A cover directive's pass.
	AssertBin =     "ASSERTBIN"      #: An assertion's failure.
	StatementBin =  "STMTBIN"        #: A statement.
	BranchBin =     "BRANCHBIN"      #: A branch of a branching statement.
	ExpressionBin = "EXPRBIN"        #: A row of an expression's truth table.
	ConditionBin =  "CONDBIN"        #: A row of a condition's truth table.
	ToggleBin =     "TOGGLEBIN"      #: A transition of a signal's toggle coverage.
	PassBin =       "PASSBIN"        #: An assertion's pass.
	FSMBin =        "FSMBIN"         #: A state or transition of a finite state machine.
	UserBin =       "USERBIN"        #: A bin defined by the user.
	Count =         "COUNT"          #: A counter.
	FailBin =       "FAILBIN"        #: A cover directive's failure.
	VacuousBin =    "VACUOUSBIN"     #: An assertion's vacuous pass.
	DisabledBin =   "DISABLEDBIN"    #: An assertion's or cover directive's disabled attempt.
	AttemptBin =    "ATTEMPTBIN"     #: An assertion's or cover directive's attempt.
	ActiveBin =     "ACTIVEBIN"      #: An assertion's or cover directive's active thread.
	IgnoreBin =     "IGNOREBIN"      #: An ignored bin of a SystemVerilog covergroup.
	IllegalBin =    "ILLEGALBIN"     #: An illegal bin of a SystemVerilog covergroup.
	DefaultBin =    "DEFAULTBIN"     #: The default bin of a SystemVerilog covergroup.
	PeakActiveBin = "PEAKACTIVEBIN"  #: The peak number of an assertion's or cover directive's active threads.
	BlockBin =      "1000000"        #: A block of statements, stated by its value ``UCIS_BLOCKBIN``: ``0x1000000``.


@export
class Language(StringEnum):
	"""
	Language of the source of a ``<ux:scope>``, as its ``lang`` states.
	"""

	VHDL =               "VHDL"         #: VHDL.
	Verilog =            "VLOG"         #: Verilog.
	SystemVerilog =      "SV"           #: SystemVerilog.
	SystemC =            "SYSTEMC"      #: SystemC.
	PSLInVHDL =          "PSL_VHDL"     #: PSL embedded in VHDL.
	PSLInVerilog =       "PSL_VLOG"     #: PSL embedded in Verilog.
	PSLInSystemVerilog = "PSL_SV"       #: PSL embedded in SystemVerilog.
	PSLInSystemC =       "PSL_SYSTEMC"  #: PSL embedded in SystemC.
	E =                  "E"            #: The verification language *e*.
	Vera =               "VERA"         #: The verification language OpenVera.
	NoLanguage =         "NONE"         #: No source language.
	Other =              "OTHER"        #: Another source language.


@export
class HistoryNodeKind(IntEnum):
	"""
	Kind of a ``<ux:hnode>``, as its ``type`` states.
	"""

	Test =  1  #: A test: a simulation run, which wrote a coverage database.
	Merge = 2  #: A merge of coverage databases.


@export
class AttributesMixin(metaclass=ExtendedType, mixin=True):
	"""
	A mixin-class adding the attributes an element states: its ``<ux:attr>`` elements, each a key and a typed value.

	An attribute's type is its value's type: ``int`` is :class:`int`, ``double`` is :class:`float`, ``str`` is
	:class:`str`.
	"""

	_attributes: dict[str, int | float | str]  #: The attributes, by key.

	def __init__(self, attributes: Nullable[Mapping[str, int | float | str]] = None) -> None:
		"""
		Initialize the attributes.

		:param attributes:  Optional, the attributes by key, e.g. ``{"#SINDEX#": 1}``. Default: ``None``.
		:raises TypeError:  If parameter ``attributes`` isn't a mapping.
		:raises TypeError:  If parameter ``attributes`` contains a key not of type :class:`str`.
		:raises ValueError: If parameter ``attributes`` contains an empty key.
		:raises TypeError:  If parameter ``attributes`` contains a value not of type :class:`int`, :class:`float` or
		                    :class:`str`.
		"""
		self._attributes = {}

		if attributes is not None:
			if not isinstance(attributes, Mapping):
				ex = TypeError(f"Parameter 'attributes' is not a mapping.")
				ex.add_note(f"Got type '{getFullyQualifiedName(attributes)}'.")
				raise ex

			for key, value in attributes.items():
				if not isinstance(key, str):
					ex = TypeError(f"Parameter 'attributes' contains a key not of type 'str'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(key)}'.")
					raise ex
				elif key == "":
					raise ValueError(f"Parameter 'attributes' contains an empty key.")

				if not isinstance(value, (int, float, str)):
					ex = TypeError(f"Parameter 'attributes' contains a value not of type 'int', 'float' or 'str'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(value)}' for key '{key}'.")
					raise ex

				self._attributes[key] = value

	@staticmethod
	def _ParseAttributes(element: _Element) -> dict[str, int | float | str]:
		"""
		Parse the attributes an element states, from its ``<ux:attr>`` elements.

		:param element:            The element stating the attributes.
		:returns:                  The attributes by key, each value of the type the attribute states.
		:raises CodeCoverageError: If an attribute's value isn't of the type the attribute states.
		"""
		attributes: dict[str, int | float | str] = {}
		for attributeElement in element.iterfind("ux:attr", NAMESPACES):
			key =           attributeElement.attrib["key"]
			attributeType = attributeElement.attrib["type"]
			text =          attributeElement.text if attributeElement.text is not None else ""
			try:
				if attributeType == "int":
					attributes[key] = int(text)
				elif attributeType == "double":
					attributes[key] = float(text)
				else:
					attributes[key] = text
			except ValueError as cause:
				ex = CodeCoverageError(f"UCDB attribute '{key}' states a value not of type '{attributeType}'.")
				ex.add_note(f"Got value '{text}'.")
				raise ex from cause

		return attributes

	@readonly
	def Attributes(self) -> dict[str, int | float | str]:
		"""
		Read-only property to access the attributes (:attr:`_attributes`).

		:returns: The attributes by key, e.g. ``#SINDEX#`` - a statement's index in its line - or ``UCIS:tool``.
		"""
		return self._attributes


@export
@abstractclass
class Base(metaclass=ExtendedType, slots=True):
	"""
	Base-class of the named elements below the report.

	Scopes and bins are named elements.
	"""

	_name: str  #: Name of the element.

	def __init__(self, name: str) -> None:
		"""
		Initialize the name of the element.

		:param name:        Name of the element.
		:raises ValueError: If parameter ``name`` is ``None``.
		:raises TypeError:  If parameter ``name`` isn't of type :class:`str`.
		"""
		if name is None:
			raise ValueError(f"Parameter 'name' is None.")
		elif not isinstance(name, str):
			ex = TypeError(f"Parameter 'name' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(name)}'.")
			raise ex

		self._name = name

	@readonly
	def Name(self) -> str:
		"""
		Read-only property to access the name of the element (:attr:`_name`).

		:returns: The name.
		"""
		return self._name


@export
class HistoryNode(Base, AttributesMixin, Generic[HistoryNodeParentType]):
	"""
	A ``<ux:hnode>`` of the report or of a merge: a test or a merge of databases, its attributes and merged nodes.

	A test wrote a coverage database, a merge merged databases. The attributes state e.g. the tool, the date and the
	command line.
	"""

	_parent:       Nullable[HistoryNodeParentType]   #: The report or merge the history node belongs to.
	_physicalName: Path                              #: Path of the coverage database.
	_kind:         HistoryNodeKind                   #: Kind of the history node.
	_historyNodes: list[HistoryNode[HistoryNode]]    #: The history nodes merged by this one.

	def __init__(
		self,
		name: str,
		physicalName: Path,
		kind: HistoryNodeKind,
		attributes: Nullable[Mapping[str, int | float | str]] = None,
		*,
		parent: Nullable[HistoryNodeParentType] = None
	) -> None:
		"""
		Initialize the history node, and append it to the history nodes of its report or merge.

		The history nodes it merged are added by creating them with this history node as their parent.

		:param name:         Logical name of the history node, e.g. of the test.
		:param physicalName: Path of the coverage database, e.g. ``cov/aggregate/aggregate.acdb``.
		:param kind:         Kind of the history node.
		:param attributes:   Optional, the attributes by key, e.g. ``{"UCIS:tool": "Riviera-PRO"}``. Default: ``None``.
		:param parent:       Optional, the report or merge the history node belongs to; the history node is appended
		                     to its history nodes. Default: ``None``.
		:raises ValueError:  If parameter ``name`` is ``None``.
		:raises TypeError:   If parameter ``name`` isn't of type :class:`str`.
		:raises TypeError:   If parameter ``attributes`` isn't a mapping.
		:raises TypeError:   If parameter ``attributes`` contains a key not of type :class:`str`.
		:raises ValueError:  If parameter ``attributes`` contains an empty key.
		:raises TypeError:   If parameter ``attributes`` contains a value not of type :class:`int`, :class:`float` or
		                     :class:`str`.
		:raises ValueError:  If parameter ``name`` is empty.
		:raises ValueError:  If parameter ``physicalName`` is ``None``.
		:raises TypeError:   If parameter ``physicalName`` isn't of type :class:`~pathlib.Path`.
		:raises ValueError:  If parameter ``kind`` is ``None``.
		:raises TypeError:   If parameter ``kind`` isn't of type :class:`HistoryNodeKind`.
		:raises TypeError:   If parameter ``parent`` isn't of type :class:`~pyEDAA.Reports.CodeCoverage.AldecUCDB.Report`
		                     or :class:`HistoryNode`.
		"""
		from pyEDAA.Reports.CodeCoverage.AldecUCDB import Report

		super().__init__(name)
		AttributesMixin.__init__(self, attributes)

		if name == "":
			raise ValueError(f"Parameter 'name' is empty.")

		if physicalName is None:
			raise ValueError(f"Parameter 'physicalName' is None.")
		elif not isinstance(physicalName, Path):
			ex = TypeError(f"Parameter 'physicalName' is not of type 'Path'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(physicalName)}'.")
			raise ex

		if kind is None:
			raise ValueError(f"Parameter 'kind' is None.")
		elif not isinstance(kind, HistoryNodeKind):
			ex = TypeError(f"Parameter 'kind' is not of type 'HistoryNodeKind'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(kind)}'.")
			raise ex

		if parent is not None and not isinstance(parent, (Report, HistoryNode)):
			ex = TypeError(f"Parameter 'parent' is not of type 'Report' or 'HistoryNode'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =       parent
		self._physicalName = physicalName
		self._kind =         kind
		self._historyNodes = []

		if parent is not None:
			parent._historyNodes.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[HistoryNodeParentType] = None) -> Self:
		"""
		Parse a history node, its attributes and the history nodes it merged from its ``<ux:hnode>`` element.

		:param element:            The ``<ux:hnode>`` element.
		:param parent:             Optional, the report or merge the history node belongs to. Default: ``None``.
		:returns:                  The history node.
		:raises CodeCoverageError: If an attribute's value isn't of the type the attribute states.
		"""
		historyNode = cls(
			element.attrib["logical_name"],
			Path(element.attrib["physical_name"]),
			HistoryNodeKind(int(element.attrib["type"])),
			cls._ParseAttributes(element),
			parent=parent
		)

		for historyNodeElement in element.iterfind("ux:hnode", NAMESPACES):
			HistoryNode.Parse(historyNodeElement, parent=historyNode)

		return historyNode

	@readonly
	def Parent(self) -> Nullable[HistoryNodeParentType]:
		"""
		Read-only property to access the report or merge the history node belongs to (:attr:`_parent`).

		:returns: The :class:`~pyEDAA.Reports.CodeCoverage.AldecUCDB.Report` or :class:`HistoryNode`; ``None`` if the
		          history node belongs to none.
		"""
		return self._parent

	@readonly
	def PhysicalName(self) -> Path:
		"""
		Read-only property to access the path of the coverage database (:attr:`_physicalName`).

		:returns: The path, as the tool stated it, e.g. relative to the directory it ran in.
		"""
		return self._physicalName

	@readonly
	def Kind(self) -> HistoryNodeKind:
		"""
		Read-only property to access the kind of the history node (:attr:`_kind`).

		:returns: The kind: a test or a merge.
		"""
		return self._kind

	@readonly
	def HistoryNodes(self) -> list[HistoryNode[HistoryNode]]:
		"""
		Read-only property to access the history nodes merged by this one (:attr:`_historyNodes`).

		:returns: The history nodes, in the order the report lists them; empty for a test.
		"""
		return self._historyNodes


@export
class Command(metaclass=ExtendedType, slots=True):
	"""
	A ``<ux:command>`` of the report: a record of a command applied to the coverage database.

	An exclusion is such a command. Its fields are kept as stated, not interpreted.
	"""

	_parent: Nullable[Report]  #: The report the command belongs to.
	_type:   int               #: Kind of the command.
	_flags:  int               #: Flags of the command.
	_data:   str               #: Data of the command, e.g. a list of values separated by ``;``.
	_index:  int               #: Index of the command.

	def __init__(self, commandType: int, flags: int, data: str, index: int, *, parent: Nullable[Report] = None) -> None:
		"""
		Initialize the command, and append it to the commands of its report.

		:param commandType: Kind of the command.
		:param flags:       Flags of the command.
		:param data:        Data of the command.
		:param index:       Index of the command.
		:param parent:      Optional, the report the command belongs to; the command is appended to its commands.
		                    Default: ``None``.
		:raises ValueError: If parameter ``commandType`` is ``None``.
		:raises TypeError:  If parameter ``commandType`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``flags`` is ``None``.
		:raises TypeError:  If parameter ``flags`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``flags`` is negative.
		:raises ValueError: If parameter ``data`` is ``None``.
		:raises TypeError:  If parameter ``data`` isn't of type :class:`str`.
		:raises ValueError: If parameter ``index`` is ``None``.
		:raises TypeError:  If parameter ``index`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``index`` is negative.
		:raises TypeError:  If parameter ``parent`` isn't of type :class:`~pyEDAA.Reports.CodeCoverage.AldecUCDB.Report`.
		"""
		from pyEDAA.Reports.CodeCoverage.AldecUCDB import Report

		if commandType is None:
			raise ValueError(f"Parameter 'commandType' is None.")
		elif not isinstance(commandType, int):
			ex = TypeError(f"Parameter 'commandType' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(commandType)}'.")
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

		if data is None:
			raise ValueError(f"Parameter 'data' is None.")
		elif not isinstance(data, str):
			ex = TypeError(f"Parameter 'data' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(data)}'.")
			raise ex

		if index is None:
			raise ValueError(f"Parameter 'index' is None.")
		elif not isinstance(index, int):
			ex = TypeError(f"Parameter 'index' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(index)}'.")
			raise ex
		elif index < 0:
			ex = ValueError(f"Parameter 'index' is negative.")
			ex.add_note(f"Got value '{index}'.")
			raise ex

		if parent is not None and not isinstance(parent, Report):
			ex = TypeError(f"Parameter 'parent' is not of type 'Report'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent = parent
		self._type =   commandType
		self._flags =  flags
		self._data =   data
		self._index =  index

		if parent is not None:
			parent._commands.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[Report] = None) -> Self:
		"""
		Parse a command from its ``<ux:command>`` element.

		:param element: The ``<ux:command>`` element.
		:param parent:  Optional, the report the command belongs to. Default: ``None``.
		:returns:       The command.
		"""
		return cls(
			int(element.attrib["type"]),
			int(element.attrib["flags"]),
			element.attrib["data"],
			int(element.attrib["index"]),
			parent=parent
		)

	@readonly
	def Parent(self) -> Nullable[Report]:
		"""
		Read-only property to access the report the command belongs to (:attr:`_parent`).

		:returns: The report; ``None`` if the command belongs to no report.
		"""
		return self._parent

	@readonly
	def Type(self) -> int:
		"""
		Read-only property to access the kind of the command (:attr:`_type`).

		:returns: The kind, as stated.
		"""
		return self._type

	@readonly
	def Flags(self) -> int:
		"""
		Read-only property to access the flags of the command (:attr:`_flags`).

		:returns: The flags, as stated.
		"""
		return self._flags

	@readonly
	def Data(self) -> str:
		"""
		Read-only property to access the data of the command (:attr:`_data`).

		:returns: The data, as stated, e.g. ``3;1;10;dut.sv;63;/project;0;0;``.
		"""
		return self._data

	@readonly
	def Index(self) -> int:
		"""
		Read-only property to access the index of the command (:attr:`_index`).

		:returns: The index, as stated.
		"""
		return self._index
