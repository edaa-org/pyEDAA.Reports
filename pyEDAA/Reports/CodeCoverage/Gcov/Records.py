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
The records of GCC's gcov JSON format below a file: its functions and lines.
"""
from __future__                       import annotations

from collections.abc                  import Iterable
from typing                           import TYPE_CHECKING, Any, Optional as Nullable, Self

from pyTooling.Common                 import getFullyQualifiedName
from pyTooling.Decorators             import export, readonly
from pyTooling.MetaClasses            import ExtendedType

if TYPE_CHECKING:
	from pyEDAA.Reports.CodeCoverage.Gcov import File


@export
class Line(metaclass=ExtendedType, slots=True):
	"""
	A ``line`` of a file: how often it ran, and its basic blocks.
	"""

	_parent:          Nullable[File]  #: The file the line belongs to.
	_lineNumber:      int             #: Line number, counted from 1.
	_functionName:    Nullable[str]   #: Mangled name of the function the line belongs to, if the report says.
	_count:           int             #: Number of times the line ran.
	_unexecutedBlock: bool            #: Whether a basic block, not only reached by exceptions, never ran.
	_blockIDs:        list[int]       #: IDs of the basic blocks ending on this line, in format 2.

	def __init__(
		self,
		lineNumber:      int,
		count:           int,
		unexecutedBlock: bool,
		functionName:    Nullable[str] = None,
		blockIDs:        Nullable[Iterable[int]] = None,
		*,
		parent:          Nullable[File] = None
	) -> None:
		"""
		Initialize the line, and add it to the lines of its file.

		:param lineNumber:      Line number, counted from 1.
		:param count:           Number of times the line ran.
		:param unexecutedBlock: Whether a basic block of the line, not only reached by exceptions, never ran.
		:param functionName:    Optional, mangled name of the function the line belongs to. Default: ``None``.
		:param blockIDs:        Optional, IDs of the basic blocks ending on this line. Default: none.
		:param parent:          Optional, the file the line belongs to; the line is appended to its lines.
		                        Default: ``None``.
		:raises ValueError:     If parameter ``lineNumber`` is ``None``.
		:raises TypeError:      If parameter ``lineNumber`` isn't of type :class:`int`.
		:raises ValueError:     If parameter ``lineNumber`` is less than 1.
		:raises ValueError:     If parameter ``count`` is ``None``.
		:raises TypeError:      If parameter ``count`` isn't of type :class:`int`.
		:raises ValueError:     If parameter ``count`` is negative.
		:raises ValueError:     If parameter ``unexecutedBlock`` is ``None``.
		:raises TypeError:      If parameter ``unexecutedBlock`` isn't of type :class:`bool`.
		:raises TypeError:      If parameter ``functionName`` isn't of type :class:`str`.
		:raises TypeError:      If parameter ``blockIDs`` isn't iterable.
		:raises TypeError:      If parameter ``blockIDs`` contains an element not of type :class:`int`.
		:raises TypeError:      If parameter ``parent`` isn't of type :class:`~pyEDAA.Reports.CodeCoverage.Gcov.File`.
		"""
		from pyEDAA.Reports.CodeCoverage.Gcov import File

		if lineNumber is None:
			raise ValueError(f"Parameter 'lineNumber' is None.")
		elif not isinstance(lineNumber, int):
			ex = TypeError(f"Parameter 'lineNumber' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(lineNumber)}'.")
			raise ex
		elif lineNumber < 1:
			ex = ValueError(f"Parameter 'lineNumber' is less than 1.")
			ex.add_note(f"Got value '{lineNumber}'.")
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

		if unexecutedBlock is None:
			raise ValueError(f"Parameter 'unexecutedBlock' is None.")
		elif not isinstance(unexecutedBlock, bool):
			ex = TypeError(f"Parameter 'unexecutedBlock' is not of type 'bool'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(unexecutedBlock)}'.")
			raise ex

		if functionName is not None and not isinstance(functionName, str):
			ex = TypeError(f"Parameter 'functionName' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(functionName)}'.")
			raise ex

		if parent is not None and not isinstance(parent, File):
			ex = TypeError(f"Parameter 'parent' is not of type 'File'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =          parent
		self._lineNumber =      lineNumber
		self._functionName =    functionName
		self._count =           count
		self._unexecutedBlock = unexecutedBlock
		self._blockIDs =        []

		if blockIDs is not None:
			if not isinstance(blockIDs, Iterable):
				ex = TypeError(f"Parameter 'blockIDs' is not iterable.")
				ex.add_note(f"Got type '{getFullyQualifiedName(blockIDs)}'.")
				raise ex

			for blockID in blockIDs:
				if not isinstance(blockID, int):
					ex = TypeError(f"Parameter 'blockIDs' contains an element not of type 'int'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(blockID)}'.")
					raise ex

				self._blockIDs.append(blockID)

		if parent is not None:
			parent._lines.append(self)

	@classmethod
	def Parse(cls, record: dict[str, Any], *, parent: Nullable[File] = None) -> Self:
		"""
		Parse a line from its JSON object.

		:param record: The JSON object of the line.
		:param parent: Optional, the file the line belongs to. Default: ``None``.
		:returns:      The line.
		"""
		return cls(
			record["line_number"],
			record["count"],
			record["unexecuted_block"],
			record.get("function_name"),
			record.get("block_ids"),
			parent=parent
		)

	@readonly
	def Parent(self) -> Nullable[File]:
		"""
		Read-only property to access the file the line belongs to (:attr:`_parent`).

		:returns: The file; ``None`` if the line belongs to no file.
		"""
		return self._parent

	@readonly
	def LineNumber(self) -> int:
		"""
		Read-only property to access the line number (:attr:`_lineNumber`).

		:returns: The line number, counted from 1.
		"""
		return self._lineNumber

	@readonly
	def FunctionName(self) -> Nullable[str]:
		"""
		Read-only property to access the mangled name of the function the line belongs to (:attr:`_functionName`).

		:returns: The function's name, or ``None`` for a line of inlined statements.
		"""
		return self._functionName

	@readonly
	def Count(self) -> int:
		"""
		Read-only property to access the number of times the line ran (:attr:`_count`).

		:returns: The count.
		"""
		return self._count

	@readonly
	def UnexecutedBlock(self) -> bool:
		"""
		Read-only property to access whether a basic block of the line never ran (:attr:`_unexecutedBlock`).

		A block only reached by exceptions doesn't count.

		:returns: ``True``, if not every statement of the line ran.
		"""
		return self._unexecutedBlock

	@readonly
	def BlockIDs(self) -> list[int]:
		"""
		Read-only property to access the IDs of the basic blocks ending on this line (:attr:`_blockIDs`).

		:returns: The blocks' IDs, unique within the function; empty in format 1.
		"""
		return self._blockIDs


@export
class Function(metaclass=ExtendedType, slots=True):
	"""
	A ``function`` of a file: its names, its position, its basic blocks and how often it ran.
	"""

	_parent:         Nullable[File]  #: The file the function belongs to.
	_name:           str             #: Name of the function, mangled.
	_demangledName:  str             #: Name of the function, demangled.
	_startLine:      int             #: The function's first line.
	_startColumn:    int             #: The function's first column.
	_endLine:        int             #: The function's last line.
	_endColumn:      int             #: The function's last column.
	_blocks:         int             #: Number of basic blocks.
	_blocksExecuted: int             #: Number of executed basic blocks.
	_executionCount: int             #: Number of times the function ran.

	def __init__(
		self,
		name:           str,
		demangledName:  str,
		startLine:      int,
		startColumn:    int,
		endLine:        int,
		endColumn:      int,
		blocks:         int,
		blocksExecuted: int,
		executionCount: int,
		*,
		parent:         Nullable[File] = None
	) -> None:
		"""
		Initialize the function, and add it to the functions of its file.

		:param name:           Name of the function, mangled.
		:param demangledName:  Name of the function, demangled.
		:param startLine:      The function's first line.
		:param startColumn:    The function's first column.
		:param endLine:        The function's last line.
		:param endColumn:      The function's last column.
		:param blocks:         Number of basic blocks.
		:param blocksExecuted: Number of executed basic blocks.
		:param executionCount: Number of times the function ran.
		:param parent:         Optional, the file the function belongs to; the function is added to its functions by
		                       :attr:`Name`. Default: ``None``.
		:raises ValueError:    If parameter ``name`` is ``None``.
		:raises TypeError:     If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError:    If parameter ``name`` is empty.
		:raises ValueError:    If parameter ``demangledName`` is ``None``.
		:raises TypeError:     If parameter ``demangledName`` isn't of type :class:`str`.
		:raises ValueError:    If parameter ``demangledName`` is empty.
		:raises ValueError:    If parameter ``startLine`` is ``None``.
		:raises TypeError:     If parameter ``startLine`` isn't of type :class:`int`.
		:raises ValueError:    If parameter ``startLine`` is negative.
		:raises ValueError:    If parameter ``startColumn`` is ``None``.
		:raises TypeError:     If parameter ``startColumn`` isn't of type :class:`int`.
		:raises ValueError:    If parameter ``startColumn`` is negative.
		:raises ValueError:    If parameter ``endLine`` is ``None``.
		:raises TypeError:     If parameter ``endLine`` isn't of type :class:`int`.
		:raises ValueError:    If parameter ``endLine`` is negative.
		:raises ValueError:    If parameter ``endColumn`` is ``None``.
		:raises TypeError:     If parameter ``endColumn`` isn't of type :class:`int`.
		:raises ValueError:    If parameter ``endColumn`` is negative.
		:raises ValueError:    If parameter ``blocks`` is ``None``.
		:raises TypeError:     If parameter ``blocks`` isn't of type :class:`int`.
		:raises ValueError:    If parameter ``blocks`` is negative.
		:raises ValueError:    If parameter ``blocksExecuted`` is ``None``.
		:raises TypeError:     If parameter ``blocksExecuted`` isn't of type :class:`int`.
		:raises ValueError:    If parameter ``blocksExecuted`` is negative.
		:raises ValueError:    If parameter ``executionCount`` is ``None``.
		:raises TypeError:     If parameter ``executionCount`` isn't of type :class:`int`.
		:raises ValueError:    If parameter ``executionCount`` is negative.
		:raises TypeError:     If parameter ``parent`` isn't of type :class:`~pyEDAA.Reports.CodeCoverage.Gcov.File`.
		"""
		from pyEDAA.Reports.CodeCoverage.Gcov import File

		if name is None:
			raise ValueError(f"Parameter 'name' is None.")
		elif not isinstance(name, str):
			ex = TypeError(f"Parameter 'name' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(name)}'.")
			raise ex
		elif name == "":
			raise ValueError(f"Parameter 'name' is empty.")

		if demangledName is None:
			raise ValueError(f"Parameter 'demangledName' is None.")
		elif not isinstance(demangledName, str):
			ex = TypeError(f"Parameter 'demangledName' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(demangledName)}'.")
			raise ex
		elif demangledName == "":
			raise ValueError(f"Parameter 'demangledName' is empty.")

		if startLine is None:
			raise ValueError(f"Parameter 'startLine' is None.")
		elif not isinstance(startLine, int):
			ex = TypeError(f"Parameter 'startLine' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(startLine)}'.")
			raise ex
		elif startLine < 0:
			ex = ValueError(f"Parameter 'startLine' is negative.")
			ex.add_note(f"Got value '{startLine}'.")
			raise ex

		if startColumn is None:
			raise ValueError(f"Parameter 'startColumn' is None.")
		elif not isinstance(startColumn, int):
			ex = TypeError(f"Parameter 'startColumn' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(startColumn)}'.")
			raise ex
		elif startColumn < 0:
			ex = ValueError(f"Parameter 'startColumn' is negative.")
			ex.add_note(f"Got value '{startColumn}'.")
			raise ex

		if endLine is None:
			raise ValueError(f"Parameter 'endLine' is None.")
		elif not isinstance(endLine, int):
			ex = TypeError(f"Parameter 'endLine' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(endLine)}'.")
			raise ex
		elif endLine < 0:
			ex = ValueError(f"Parameter 'endLine' is negative.")
			ex.add_note(f"Got value '{endLine}'.")
			raise ex

		if endColumn is None:
			raise ValueError(f"Parameter 'endColumn' is None.")
		elif not isinstance(endColumn, int):
			ex = TypeError(f"Parameter 'endColumn' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(endColumn)}'.")
			raise ex
		elif endColumn < 0:
			ex = ValueError(f"Parameter 'endColumn' is negative.")
			ex.add_note(f"Got value '{endColumn}'.")
			raise ex

		if blocks is None:
			raise ValueError(f"Parameter 'blocks' is None.")
		elif not isinstance(blocks, int):
			ex = TypeError(f"Parameter 'blocks' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(blocks)}'.")
			raise ex
		elif blocks < 0:
			ex = ValueError(f"Parameter 'blocks' is negative.")
			ex.add_note(f"Got value '{blocks}'.")
			raise ex

		if blocksExecuted is None:
			raise ValueError(f"Parameter 'blocksExecuted' is None.")
		elif not isinstance(blocksExecuted, int):
			ex = TypeError(f"Parameter 'blocksExecuted' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(blocksExecuted)}'.")
			raise ex
		elif blocksExecuted < 0:
			ex = ValueError(f"Parameter 'blocksExecuted' is negative.")
			ex.add_note(f"Got value '{blocksExecuted}'.")
			raise ex

		if executionCount is None:
			raise ValueError(f"Parameter 'executionCount' is None.")
		elif not isinstance(executionCount, int):
			ex = TypeError(f"Parameter 'executionCount' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(executionCount)}'.")
			raise ex
		elif executionCount < 0:
			ex = ValueError(f"Parameter 'executionCount' is negative.")
			ex.add_note(f"Got value '{executionCount}'.")
			raise ex

		if parent is not None and not isinstance(parent, File):
			ex = TypeError(f"Parameter 'parent' is not of type 'File'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =         parent
		self._name =           name
		self._demangledName =  demangledName
		self._startLine =      startLine
		self._startColumn =    startColumn
		self._endLine =        endLine
		self._endColumn =      endColumn
		self._blocks =         blocks
		self._blocksExecuted = blocksExecuted
		self._executionCount = executionCount

		if parent is not None:
			parent._functions[self._name] = self

	@classmethod
	def Parse(cls, record: dict[str, Any], *, parent: Nullable[File] = None) -> Self:
		"""
		Parse a function from its JSON object.

		:param record: The JSON object of the function.
		:param parent: Optional, the file the function belongs to. Default: ``None``.
		:returns:      The function.
		"""
		return cls(
			record["name"],
			record["demangled_name"],
			record["start_line"],
			record["start_column"],
			record["end_line"],
			record["end_column"],
			record["blocks"],
			record["blocks_executed"],
			record["execution_count"],
			parent=parent
		)

	@readonly
	def Parent(self) -> Nullable[File]:
		"""
		Read-only property to access the file the function belongs to (:attr:`_parent`).

		:returns: The file; ``None`` if the function belongs to no file.
		"""
		return self._parent

	@readonly
	def Name(self) -> str:
		"""
		Read-only property to access the mangled name of the function (:attr:`_name`).

		The method ``Containers::Stack::Pop()`` is mangled to ``_ZN10Containers5Stack3PopEv``, a C function keeps its name.

		:returns: The mangled name.
		"""
		return self._name

	@readonly
	def DemangledName(self) -> str:
		"""
		Read-only property to access the demangled name of the function (:attr:`_demangledName`).

		The demangled name of ``_ZN10Containers5Stack3PopEv`` is ``Containers::Stack::Pop()``.

		:returns: The demangled name.
		"""
		return self._demangledName

	@readonly
	def StartLine(self) -> int:
		"""
		Read-only property to access the function's first line (:attr:`_startLine`).

		:returns: The line number.
		"""
		return self._startLine

	@readonly
	def StartColumn(self) -> int:
		"""
		Read-only property to access the function's first column (:attr:`_startColumn`).

		:returns: The column number, counted from 1.
		"""
		return self._startColumn

	@readonly
	def EndLine(self) -> int:
		"""
		Read-only property to access the function's last line (:attr:`_endLine`).

		:returns: The line number.
		"""
		return self._endLine

	@readonly
	def EndColumn(self) -> int:
		"""
		Read-only property to access the function's last column (:attr:`_endColumn`).

		:returns: The column number, counted from 1.
		"""
		return self._endColumn

	@readonly
	def Blocks(self) -> int:
		"""
		Read-only property to access the number of basic blocks (:attr:`_blocks`).

		:returns: The number of blocks.
		"""
		return self._blocks

	@readonly
	def BlocksExecuted(self) -> int:
		"""
		Read-only property to access the number of executed basic blocks (:attr:`_blocksExecuted`).

		:returns: The number of executed blocks.
		"""
		return self._blocksExecuted

	@readonly
	def ExecutionCount(self) -> int:
		"""
		Read-only property to access the number of times the function ran (:attr:`_executionCount`).

		:returns: The count.
		"""
		return self._executionCount
