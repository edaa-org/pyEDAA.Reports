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
The statement and block coverage of the UCIS XML interchange format: an instance's ``<blockCoverage>``, its statements,
blocks and processes.
"""
from __future__                                   import annotations

from typing                                       import TYPE_CHECKING, Generator, Generic, Iterable
from typing                                       import Optional as Nullable, Self, TypeVar

from lxml.etree                                   import _Element
from pyTooling.Common                             import getFullyQualifiedName
from pyTooling.Decorators                         import export, readonly

from pyEDAA.Reports.CodeCoverage.UCIS.Bins        import Bin
from pyEDAA.Reports.CodeCoverage.UCIS.Elements    import Base, MetricCoverage, ObjectAttributesMixin, StatementID
from pyEDAA.Reports.CodeCoverage.UCIS.Elements    import UserAttribute

if TYPE_CHECKING:
	from pyEDAA.Reports.CodeCoverage.UCIS.Instances import InstanceCoverage


__all__ = ["BlockParentType"]

# A class with a property named like a class - ``Bin`` - can't name that class in the annotation of a field: the class
# body's namespace, where annotations are evaluated, binds the name to the property.
_Bin = Bin

BlockParentType = TypeVar("BlockParentType", bound="BlockCoverage | Process | Block")
"""A type variable for the parent of a :class:`Block`: a :class:`BlockCoverage`, a :class:`Process` or a
:class:`Block`."""


@export
class BlockCoverage(MetricCoverage):
	"""
	A ``<blockCoverage>`` of an instance: its statements, its blocks or its processes with their blocks.

	The format states one of the three.
	"""

	_statements: list[Statement]                #: The statements.
	_blocks:     list[Block[BlockCoverage]]     #: The blocks.
	_processes:  list[Process]                  #: The processes.

	def __init__(
		self,
		metricMode: Nullable[str] = None,
		weight: int = 1,
		userAttributes: Nullable[Iterable[UserAttribute]] = None,
		*,
		parent: Nullable[InstanceCoverage] = None
	) -> None:
		"""
		Initialize the block coverage, and append it to the block coverages of its instance.

		Its statements, blocks and processes are added by creating them with this coverage as their parent.

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

		self._statements = []
		self._blocks =     []
		self._processes =  []

		if parent is not None:
			parent._blockCoverages.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[InstanceCoverage] = None) -> Self:
		"""
		Parse a block coverage, its statements, blocks and processes from its ``<blockCoverage>`` element.

		:param element:            The ``<blockCoverage>`` element.
		:param parent:             Optional, the instance the coverage belongs to. Default: ``None``.
		:returns:                  The block coverage.
		:raises CodeCoverageError: If a user-defined attribute's value isn't of the type the attribute states.
		"""
		blockCoverage = cls(
			element.attrib.get("metricMode"),
			int(element.attrib.get("weight", "1")),
			cls._ParseUserAttributes(element),
			parent=parent
		)

		for statementElement in element.iterfind("{*}statement"):
			Statement.Parse(statementElement, parent=blockCoverage)

		for blockElement in element.iterfind("{*}block"):
			Block.Parse(blockElement, parent=blockCoverage)

		for processElement in element.iterfind("{*}process"):
			Process.Parse(processElement, parent=blockCoverage)

		return blockCoverage

	def IterateBlocks(self) -> Generator[Block, None, None]:
		"""
		Iterate the blocks: those of the coverage and those of its processes, each followed by the blocks nested in it.

		:returns: A generator of the blocks.
		"""
		for block in self._blocks:
			yield block
			yield from block.IterateBlocks()

		for process in self._processes:
			for block in process._blocks:
				yield block
				yield from block.IterateBlocks()

	@readonly
	def Statements(self) -> list[Statement]:
		"""
		Read-only property to access the statements (:attr:`_statements`).

		:returns: The statements, in the order the report lists them.
		"""
		return self._statements

	@readonly
	def Blocks(self) -> list[Block[BlockCoverage]]:
		"""
		Read-only property to access the blocks, which belong to no process (:attr:`_blocks`).

		:returns: The blocks, in the order the report lists them.
		"""
		return self._blocks

	@readonly
	def Processes(self) -> list[Process]:
		"""
		Read-only property to access the processes (:attr:`_processes`).

		:returns: The processes, in the order the report lists them.
		"""
		return self._processes


@export
class Statement(Base, ObjectAttributesMixin):
	"""
	A ``<statement>`` of a block coverage: where the statement is, and its bin - how often it ran.
	"""

	_parent: Nullable[BlockCoverage]  #: The block coverage the statement belongs to.
	_id:     StatementID              #: Where the statement is.
	_bin:    _Bin                     #: How often the statement ran.

	def __init__(
		self,
		statementID: StatementID,
		coverBin: Bin,
		alias: Nullable[str] = None,
		excluded: bool = False,
		excludedReason: Nullable[str] = None,
		weight: int = 1,
		userAttributes: Nullable[Iterable[UserAttribute]] = None,
		*,
		parent: Nullable[BlockCoverage] = None
	) -> None:
		"""
		Initialize the statement, become its bin's parent, and append it to the statements of its block coverage.

		:param statementID:    Where the statement is.
		:param coverBin:       How often the statement ran.
		:param alias:          Optional, an alias of the statement's name. Default: ``None``.
		:param excluded:       Optional, whether the statement is excluded from the coverage. Default: ``False``.
		:param excludedReason: Optional, why the statement is excluded. Default: ``None``.
		:param weight:         Optional, weight of the statement in computing the coverage. Default: ``1``.
		:param userAttributes: Optional, the user-defined attributes. Default: ``None``.
		:param parent:         Optional, the block coverage the statement belongs to. Default: ``None``.
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
		:raises ValueError:    If parameter ``statementID`` is ``None``.
		:raises TypeError:     If parameter ``statementID`` isn't of type
		                       :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Elements.StatementID`.
		:raises ValueError:    If parameter ``coverBin`` is ``None``.
		:raises TypeError:     If parameter ``coverBin`` isn't of type :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Bins.Bin`.
		:raises TypeError:     If parameter ``parent`` isn't of type :class:`BlockCoverage`.
		"""
		super().__init__(userAttributes)
		ObjectAttributesMixin.__init__(self, alias, excluded, excludedReason, weight)

		if statementID is None:
			raise ValueError(f"Parameter 'statementID' is None.")
		elif not isinstance(statementID, StatementID):
			ex = TypeError(f"Parameter 'statementID' is not of type 'StatementID'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(statementID)}'.")
			raise ex

		if coverBin is None:
			raise ValueError(f"Parameter 'coverBin' is None.")
		elif not isinstance(coverBin, Bin):
			ex = TypeError(f"Parameter 'coverBin' is not of type 'Bin'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(coverBin)}'.")
			raise ex

		if parent is not None and not isinstance(parent, BlockCoverage):
			ex = TypeError(f"Parameter 'parent' is not of type 'BlockCoverage'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =   parent
		self._id =       statementID
		self._bin =      coverBin
		coverBin._parent = self

		if parent is not None:
			parent._statements.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[BlockCoverage] = None) -> Self:
		"""
		Parse a statement and its bin from its ``<statement>`` element.

		:param element:            The ``<statement>`` element.
		:param parent:             Optional, the block coverage the statement belongs to. Default: ``None``.
		:returns:                  The statement.
		:raises CodeCoverageError: If a user-defined attribute's value isn't of the type the attribute states.
		"""
		return cls(
			StatementID.Parse(element.find("{*}id")),
			Bin.Parse(element.find("{*}bin")),
			element.attrib.get("alias"),
			cls._ParseBoolean(element.attrib.get("excluded", "false")),
			element.attrib.get("excludedReason"),
			int(element.attrib.get("weight", "1")),
			cls._ParseUserAttributes(element),
			parent=parent
		)

	@readonly
	def Parent(self) -> Nullable[BlockCoverage]:
		"""
		Read-only property to access the block coverage the statement belongs to (:attr:`_parent`).

		:returns: The block coverage; ``None``, if the statement belongs to none.
		"""
		return self._parent

	@readonly
	def ID(self) -> StatementID:
		"""
		Read-only property to access where the statement is (:attr:`_id`).

		:returns: The source statement identifier.
		"""
		return self._id

	@readonly
	def Bin(self) -> Bin:
		"""
		Read-only property to access the statement's bin (:attr:`_bin`).

		:returns: The bin, stating how often the statement ran.
		"""
		return self._bin


@export
class Process(Base, ObjectAttributesMixin):
	"""
	A ``<process>`` of a block coverage: its kind and its blocks.
	"""

	_parent:      Nullable[BlockCoverage]  #: The block coverage the process belongs to.
	_processType: str                      #: Kind of the process, e.g. ``always``.
	_blocks:      list[Block[Process]]     #: The blocks of the process.

	def __init__(
		self,
		processType: str,
		alias: Nullable[str] = None,
		excluded: bool = False,
		excludedReason: Nullable[str] = None,
		weight: int = 1,
		userAttributes: Nullable[Iterable[UserAttribute]] = None,
		*,
		parent: Nullable[BlockCoverage] = None
	) -> None:
		"""
		Initialize the process, and append it to the processes of its block coverage.

		Its blocks are added by creating them with this process as their parent.

		:param processType:    Kind of the process, e.g. ``always`` or ``initial``.
		:param alias:          Optional, an alias of the process' name. Default: ``None``.
		:param excluded:       Optional, whether the process is excluded from the coverage. Default: ``False``.
		:param excludedReason: Optional, why the process is excluded. Default: ``None``.
		:param weight:         Optional, weight of the process in computing the coverage. Default: ``1``.
		:param userAttributes: Optional, the user-defined attributes. Default: ``None``.
		:param parent:         Optional, the block coverage the process belongs to. Default: ``None``.
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
		:raises ValueError:    If parameter ``processType`` is ``None``.
		:raises TypeError:     If parameter ``processType`` isn't of type :class:`str`.
		:raises TypeError:     If parameter ``parent`` isn't of type :class:`BlockCoverage`.
		"""
		super().__init__(userAttributes)
		ObjectAttributesMixin.__init__(self, alias, excluded, excludedReason, weight)

		if processType is None:
			raise ValueError(f"Parameter 'processType' is None.")
		elif not isinstance(processType, str):
			ex = TypeError(f"Parameter 'processType' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(processType)}'.")
			raise ex

		if parent is not None and not isinstance(parent, BlockCoverage):
			ex = TypeError(f"Parameter 'parent' is not of type 'BlockCoverage'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =      parent
		self._processType = processType
		self._blocks =      []

		if parent is not None:
			parent._processes.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[BlockCoverage] = None) -> Self:
		"""
		Parse a process and its blocks from its ``<process>`` element.

		:param element:            The ``<process>`` element.
		:param parent:             Optional, the block coverage the process belongs to. Default: ``None``.
		:returns:                  The process.
		:raises CodeCoverageError: If a user-defined attribute's value isn't of the type the attribute states.
		"""
		process = cls(
			element.attrib["processType"],
			element.attrib.get("alias"),
			cls._ParseBoolean(element.attrib.get("excluded", "false")),
			element.attrib.get("excludedReason"),
			int(element.attrib.get("weight", "1")),
			cls._ParseUserAttributes(element),
			parent=parent
		)

		for blockElement in element.iterfind("{*}block"):
			Block.Parse(blockElement, parent=process)

		return process

	@readonly
	def Parent(self) -> Nullable[BlockCoverage]:
		"""
		Read-only property to access the block coverage the process belongs to (:attr:`_parent`).

		:returns: The block coverage; ``None``, if the process belongs to none.
		"""
		return self._parent

	@readonly
	def ProcessType(self) -> str:
		"""
		Read-only property to access the kind of the process (:attr:`_processType`).

		:returns: The kind, e.g. ``always``.
		"""
		return self._processType

	@readonly
	def Blocks(self) -> list[Block[Process]]:
		"""
		Read-only property to access the blocks of the process (:attr:`_blocks`).

		:returns: The blocks, in the order the report lists them.
		"""
		return self._blocks


@export
class Block(Base, ObjectAttributesMixin, Generic[BlockParentType]):
	"""
	A ``<block>`` - or a ``<hierarchicalBlock>`` nested in a block -: where it is, the statements it contains, its bin -
	how often it ran - and the blocks nested in it.
	"""

	_parent:        Nullable[BlockParentType]  #: The block coverage, process or block the block belongs to.
	_id:            StatementID                #: Where the block is.
	_bin:           _Bin                       #: How often the block ran.
	_statementIDs:  list[StatementID]          #: Where the statements of the block are.
	_parentProcess: Nullable[str]              #: Kind of the process the block is in, e.g. ``always``.
	_blocks:        list[Block[Block]]         #: The blocks nested in this one.

	def __init__(
		self,
		blockID: StatementID,
		coverBin: Bin,
		statementIDs: Nullable[Iterable[StatementID]] = None,
		parentProcess: Nullable[str] = None,
		alias: Nullable[str] = None,
		excluded: bool = False,
		excludedReason: Nullable[str] = None,
		weight: int = 1,
		userAttributes: Nullable[Iterable[UserAttribute]] = None,
		*,
		parent: Nullable[BlockParentType] = None
	) -> None:
		"""
		Initialize the block, become its bin's parent, and append it to the blocks of its parent.

		The blocks nested in it are added by creating them with this block as their parent.

		:param blockID:        Where the block is.
		:param coverBin:       How often the block ran.
		:param statementIDs:   Optional, where the statements of the block are. Default: ``None``.
		:param parentProcess:  Optional, kind of the process the block is in, e.g. ``always``. Default: ``None``.
		:param alias:          Optional, an alias of the block's name. Default: ``None``.
		:param excluded:       Optional, whether the block is excluded from the coverage. Default: ``False``.
		:param excludedReason: Optional, why the block is excluded. Default: ``None``.
		:param weight:         Optional, weight of the block in computing the coverage. Default: ``1``.
		:param userAttributes: Optional, the user-defined attributes. Default: ``None``.
		:param parent:         Optional, the block coverage, process or block the block belongs to. Default: ``None``.
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
		:raises ValueError:    If parameter ``blockID`` is ``None``.
		:raises TypeError:     If parameter ``blockID`` isn't of type
		                       :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Elements.StatementID`.
		:raises ValueError:    If parameter ``coverBin`` is ``None``.
		:raises TypeError:     If parameter ``coverBin`` isn't of type :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Bins.Bin`.
		:raises TypeError:     If parameter ``parentProcess`` isn't of type :class:`str`.
		:raises TypeError:     If parameter ``parent`` isn't of type :class:`BlockCoverage`, :class:`Process` or
		                       :class:`Block`.
		:raises TypeError:     If parameter ``statementIDs`` isn't iterable.
		:raises TypeError:     If parameter ``statementIDs`` contains an element not of type
		                       :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Elements.StatementID`.
		"""
		super().__init__(userAttributes)
		ObjectAttributesMixin.__init__(self, alias, excluded, excludedReason, weight)

		if blockID is None:
			raise ValueError(f"Parameter 'blockID' is None.")
		elif not isinstance(blockID, StatementID):
			ex = TypeError(f"Parameter 'blockID' is not of type 'StatementID'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(blockID)}'.")
			raise ex

		if coverBin is None:
			raise ValueError(f"Parameter 'coverBin' is None.")
		elif not isinstance(coverBin, Bin):
			ex = TypeError(f"Parameter 'coverBin' is not of type 'Bin'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(coverBin)}'.")
			raise ex

		if parentProcess is not None and not isinstance(parentProcess, str):
			ex = TypeError(f"Parameter 'parentProcess' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parentProcess)}'.")
			raise ex

		if parent is not None and not isinstance(parent, (BlockCoverage, Process, Block)):
			ex = TypeError(f"Parameter 'parent' is not of type 'BlockCoverage', 'Process' or 'Block'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =        parent
		self._id =            blockID
		self._bin =           coverBin
		self._statementIDs =  []
		self._parentProcess = parentProcess
		self._blocks =        []
		coverBin._parent =    self

		if statementIDs is not None:
			if not isinstance(statementIDs, Iterable):
				ex = TypeError(f"Parameter 'statementIDs' is not iterable.")
				ex.add_note(f"Got type '{getFullyQualifiedName(statementIDs)}'.")
				raise ex

			for statementID in statementIDs:
				if not isinstance(statementID, StatementID):
					ex = TypeError(f"Parameter 'statementIDs' contains an element not of type 'StatementID'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(statementID)}'.")
					raise ex

				self._statementIDs.append(statementID)

		if parent is not None:
			parent._blocks.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[BlockParentType] = None) -> Self:
		"""
		Parse a block, its bin and the blocks nested in it from its ``<block>`` or ``<hierarchicalBlock>`` element.

		:param element:            The ``<block>`` or ``<hierarchicalBlock>`` element.
		:param parent:             Optional, the block coverage, process or block the block belongs to. Default: ``None``.
		:returns:                  The block.
		:raises CodeCoverageError: If a user-defined attribute's value isn't of the type the attribute states.
		"""
		block = cls(
			StatementID.Parse(element.find("{*}blockId")),
			Bin.Parse(element.find("{*}blockBin")),
			[StatementID.Parse(idElement) for idElement in element.iterfind("{*}statementId")],
			element.attrib.get("parentProcess"),
			element.attrib.get("alias"),
			cls._ParseBoolean(element.attrib.get("excluded", "false")),
			element.attrib.get("excludedReason"),
			int(element.attrib.get("weight", "1")),
			cls._ParseUserAttributes(element),
			parent=parent
		)

		for blockElement in element.iterfind("{*}hierarchicalBlock"):
			Block.Parse(blockElement, parent=block)

		return block

	def IterateBlocks(self) -> Generator[Block[Block], None, None]:
		"""
		Iterate the blocks nested in this one, each followed by the blocks nested in it.

		:returns: A generator of the blocks.
		"""
		for block in self._blocks:
			yield block
			yield from block.IterateBlocks()

	@readonly
	def Parent(self) -> Nullable[BlockParentType]:
		"""
		Read-only property to access the block coverage, process or block the block belongs to (:attr:`_parent`).

		:returns: The :class:`BlockCoverage`, :class:`Process` or :class:`Block`; ``None``, if the block belongs to none.
		"""
		return self._parent

	@readonly
	def ID(self) -> StatementID:
		"""
		Read-only property to access where the block is (:attr:`_id`).

		:returns: The source statement identifier.
		"""
		return self._id

	@readonly
	def Bin(self) -> Bin:
		"""
		Read-only property to access the block's bin (:attr:`_bin`).

		:returns: The bin, stating how often the block ran.
		"""
		return self._bin

	@readonly
	def StatementIDs(self) -> list[StatementID]:
		"""
		Read-only property to access where the statements of the block are (:attr:`_statementIDs`).

		:returns: The source statement identifiers, in the order the report lists them.
		"""
		return self._statementIDs

	@readonly
	def ParentProcess(self) -> Nullable[str]:
		"""
		Read-only property to access the kind of the process the block is in (:attr:`_parentProcess`).

		:returns: The kind, e.g. ``always``; ``None``, if the report states none.
		"""
		return self._parentProcess

	@readonly
	def Blocks(self) -> list[Block[Block]]:
		"""
		Read-only property to access the blocks nested in this one (:attr:`_blocks`).

		:returns: The blocks, in the order the report lists them.
		"""
		return self._blocks
