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
The coverage items of a scope in QuestaSim's coverage report XML: statements, and ``if`` and ``case`` statements with
their branches.

A report lists them with details only (``vcover report -details``): ``-code`` chooses the kinds, e.g. ``-code bcesf``
for branches, conditions, expressions, statements and finite state machines. A coverage item names its source file by
the number the scope's source table gives it, its line, and its index among the items of its kind in that line. The
states and transitions of finite state machines are in :mod:`~pyEDAA.Reports.CodeCoverage.QuestaSim.StateMachines`.
"""
from __future__                                     import annotations

from pathlib                                        import Path
from typing                                         import TYPE_CHECKING, Optional as Nullable, Self

from lxml.etree                                     import _Element
from pyTooling.Common                               import getFullyQualifiedName
from pyTooling.Decorators                           import export, readonly
from pyTooling.MetaClasses                          import ExtendedType

from pyEDAA.Reports.CodeCoverage                    import CodeCoverageError

if TYPE_CHECKING:
	from pyEDAA.Reports.CodeCoverage.QuestaSim.Scopes import Scope


@export
class SourceItem(metaclass=ExtendedType, slots=True):
	"""
	Base-class of the coverage items, which name where they are in the sources: a file, a line and an index in the line.
	"""

	_file:       Path  #: Path of the source file, as the report states it.
	_lineNumber: int   #: Line number, counted from 1.
	_index:      int   #: Index of the item among the items of its kind in its line, counted from 1.

	def __init__(self, file: Path, lineNumber: int, index: int) -> None:
		"""
		Initialize where the coverage item is in the sources.

		:param file:        Path of the source file, as the report states it.
		:param lineNumber:  Line number, counted from 1.
		:param index:       Index of the item among the items of its kind in its line, counted from 1.
		:raises ValueError: If parameter ``file`` is ``None``.
		:raises TypeError:  If parameter ``file`` isn't of type :class:`~pathlib.Path`.
		:raises ValueError: If parameter ``lineNumber`` is ``None``.
		:raises TypeError:  If parameter ``lineNumber`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``lineNumber`` is less than 1.
		:raises ValueError: If parameter ``index`` is ``None``.
		:raises TypeError:  If parameter ``index`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``index`` is less than 1.
		"""
		if file is None:
			raise ValueError(f"Parameter 'file' is None.")
		elif not isinstance(file, Path):
			ex = TypeError(f"Parameter 'file' is not of type 'Path'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(file)}'.")
			raise ex

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

		if index is None:
			raise ValueError(f"Parameter 'index' is None.")
		elif not isinstance(index, int):
			ex = TypeError(f"Parameter 'index' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(index)}'.")
			raise ex
		elif index < 1:
			ex = ValueError(f"Parameter 'index' is less than 1.")
			ex.add_note(f"Got value '{index}'.")
			raise ex

		self._file =       file
		self._lineNumber = lineNumber
		self._index =      index

	@readonly
	def File(self) -> Path:
		"""
		Read-only property to access the path of the source file (:attr:`_file`).

		:returns: The path, as the report states it.
		"""
		return self._file

	@readonly
	def LineNumber(self) -> int:
		"""
		Read-only property to access the line number (:attr:`_lineNumber`).

		:returns: The line number, counted from 1.
		"""
		return self._lineNumber

	@readonly
	def Index(self) -> int:
		"""
		Read-only property to access the index of the item among the items of its kind in its line (:attr:`_index`).

		:returns: The index, counted from 1.
		"""
		return self._index


@export
class Statement(SourceItem):
	"""
	A ``<stmt>`` of a scope: a statement, where it is in the sources, and how often it ran.
	"""

	_parent: Nullable[Scope]  #: The scope the statement belongs to.
	_hits:   int              #: How often the statement ran.

	def __init__(self, file: Path, lineNumber: int, index: int, hits: int, *, parent: Nullable[Scope] = None) -> None:
		"""
		Initialize the statement, and append it to the statements of its scope.

		:param file:        Path of the source file, as the report states it.
		:param lineNumber:  Line number, counted from 1.
		:param index:       Index of the statement in its line, counted from 1.
		:param hits:        How often the statement ran.
		:param parent:      Optional, the scope the statement belongs to; the statement is appended to its statements.
		                    Default: ``None``.
		:raises ValueError: If parameter ``file`` is ``None``.
		:raises TypeError:  If parameter ``file`` isn't of type :class:`~pathlib.Path`.
		:raises ValueError: If parameter ``lineNumber`` is ``None``.
		:raises TypeError:  If parameter ``lineNumber`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``lineNumber`` is less than 1.
		:raises ValueError: If parameter ``index`` is ``None``.
		:raises TypeError:  If parameter ``index`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``index`` is less than 1.
		:raises ValueError: If parameter ``hits`` is ``None``.
		:raises TypeError:  If parameter ``hits`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``hits`` is negative.
		:raises TypeError:  If parameter ``parent`` isn't of type
		                    :class:`~pyEDAA.Reports.CodeCoverage.QuestaSim.Scopes.Scope`.
		"""
		from pyEDAA.Reports.CodeCoverage.QuestaSim.Scopes import Scope

		super().__init__(file, lineNumber, index)

		if hits is None:
			raise ValueError(f"Parameter 'hits' is None.")
		elif not isinstance(hits, int):
			ex = TypeError(f"Parameter 'hits' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(hits)}'.")
			raise ex
		elif hits < 0:
			ex = ValueError(f"Parameter 'hits' is negative.")
			ex.add_note(f"Got value '{hits}'.")
			raise ex

		if parent is not None and not isinstance(parent, Scope):
			ex = TypeError(f"Parameter 'parent' is not of type 'Scope'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent = parent
		self._hits =   hits

		if parent is not None:
			parent._statements.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Scope) -> Self:
		"""
		Parse a statement from its ``<stmt>`` element; its file is the one its file number names in the scope's source
		table.

		:param element:            The ``<stmt>`` element.
		:param parent:             The scope the statement belongs to.
		:returns:                  The statement.
		:raises CodeCoverageError: If the statement's file number isn't in the scope's source table.
		:raises CodeCoverageError: If the statement states no file number and its scope has no single file.
		"""
		return cls(
			parent._ResolveFile(element),
			int(element.attrib["ln"]),
			int(element.attrib["st"]),
			int(element.attrib["hits"]),
			parent=parent
		)

	@readonly
	def Parent(self) -> Nullable[Scope]:
		"""
		Read-only property to access the scope the statement belongs to (:attr:`_parent`).

		:returns: The scope; ``None`` if the statement belongs to no scope.
		"""
		return self._parent

	@readonly
	def Hits(self) -> int:
		"""
		Read-only property to access how often the statement ran (:attr:`_hits`).

		:returns: The count.
		"""
		return self._hits


@export
class IfStatement(metaclass=ExtendedType, slots=True):
	"""
	An ``<if>`` of a scope: an ``if`` statement - with its ``elsif`` and ``else`` branches - and how often each branch was
	taken.

	Each branch is an ``<ielem>`` (:class:`IfBranch`). An ``if`` statement without ``else`` has an implicit branch, the
	*AllFalse* branch, taken whenever no condition was true; Questa lists it as the last ``<ielem>``, in the line of the
	``if``.
	"""

	_parent:   Nullable[Scope]  #: The scope the ``if`` statement belongs to.
	_hasElse:  bool             #: Whether the ``if`` statement has an ``else`` branch.
	_branches: list[IfBranch]   #: The branches, in the order of their conditions.

	def __init__(self, hasElse: bool, *, parent: Nullable[Scope] = None) -> None:
		"""
		Initialize the ``if`` statement, and append it to the ``if`` statements of its scope.

		Its branches are added by creating them with this ``if`` statement as their parent.

		:param hasElse:     Whether the ``if`` statement has an ``else`` branch; otherwise its last branch is the implicit
		                    *AllFalse* branch.
		:param parent:      Optional, the scope the ``if`` statement belongs to. Default: ``None``.
		:raises ValueError: If parameter ``hasElse`` is ``None``.
		:raises TypeError:  If parameter ``hasElse`` isn't of type :class:`bool`.
		:raises TypeError:  If parameter ``parent`` isn't of type
		                    :class:`~pyEDAA.Reports.CodeCoverage.QuestaSim.Scopes.Scope`.
		"""
		from pyEDAA.Reports.CodeCoverage.QuestaSim.Scopes import Scope

		if hasElse is None:
			raise ValueError(f"Parameter 'hasElse' is None.")
		elif not isinstance(hasElse, bool):
			ex = TypeError(f"Parameter 'hasElse' is not of type 'bool'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(hasElse)}'.")
			raise ex

		if parent is not None and not isinstance(parent, Scope):
			ex = TypeError(f"Parameter 'parent' is not of type 'Scope'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =   parent
		self._hasElse =  hasElse
		self._branches = []

		if parent is not None:
			parent._ifStatements.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Scope) -> Self:
		"""
		Parse an ``if`` statement and its branches from its ``<if>`` element.

		:param element:            The ``<if>`` element.
		:param parent:             The scope the ``if`` statement belongs to.
		:returns:                  The ``if`` statement.
		:raises CodeCoverageError: If a branch's file number isn't in the scope's source table, or it states none and the
		                           scope has no single file.
		:raises CodeCoverageError: If the ``if`` statement states other numbers of branches and taken branches than its
		                           branches have.
		"""
		ifStatement = cls(element.attrib["hasElse"] == "1", parent=parent)
		for branchElement in element.iterfind("ielem"):
			IfBranch.Parse(branchElement, parent=ifStatement)

		active, hits = int(element.attrib["active"]), int(element.attrib["hits"])
		if (active, hits) != (len(ifStatement._branches), ifStatement.TakenBranches):
			ex = CodeCoverageError(f"'<if>' in line {element.sourceline} states other figures than its branches have.")
			ex.add_note(f"Got '{hits}' of '{active}' branches taken, its branches have {ifStatement.TakenBranches} of "
			            f"{len(ifStatement._branches)}.")
			raise ex

		return ifStatement

	@readonly
	def Parent(self) -> Nullable[Scope]:
		"""
		Read-only property to access the scope the ``if`` statement belongs to (:attr:`_parent`).

		:returns: The scope; ``None`` if the ``if`` statement belongs to no scope.
		"""
		return self._parent

	@readonly
	def HasElse(self) -> bool:
		"""
		Read-only property to access whether the ``if`` statement has an ``else`` branch (:attr:`_hasElse`).

		:returns: ``True``, if it has an ``else`` branch; otherwise its last branch is the implicit *AllFalse* branch.
		"""
		return self._hasElse

	@readonly
	def Branches(self) -> list[IfBranch]:
		"""
		Read-only property to access the branches (:attr:`_branches`).

		:returns: The branches, in the order of their conditions; the ``else`` or *AllFalse* branch last.
		"""
		return self._branches

	@readonly
	def TakenBranches(self) -> int:
		"""
		Read-only property to return the number of branches, which were taken.

		:returns: The number of branches with a positive :attr:`IfBranch.TrueCount`.
		"""
		return sum(1 for branch in self._branches if branch._trueCount > 0)

	@readonly
	def EvaluationCount(self) -> int:
		"""
		Read-only property to return how often the ``if`` statement was evaluated.

		Each evaluation takes exactly one branch, so it is the sum of the branches' :attr:`IfBranch.TrueCount`.

		:returns: The number of evaluations.
		"""
		return sum(branch._trueCount for branch in self._branches)


@export
class IfBranch(SourceItem):
	"""
	An ``<ielem>`` of an ``if`` statement: a branch - ``if``, ``elsif``, ``else`` or the implicit *AllFalse* branch -, how
	often it was taken, and how often its condition was false.
	"""

	_parent:     Nullable[IfStatement]  #: The ``if`` statement the branch belongs to.
	_trueCount:  int                    #: How often the branch was taken.
	_falseCount: int                    #: How often the branch's condition was false: the evaluation went on.

	def __init__(
		self,
		file: Path,
		lineNumber: int,
		index: int,
		trueCount: int,
		falseCount: int,
		*,
		parent: Nullable[IfStatement] = None
	) -> None:
		"""
		Initialize the branch, and append it to the branches of its ``if`` statement.

		:param file:        Path of the source file, as the report states it.
		:param lineNumber:  Line number of the branch's condition, counted from 1.
		:param index:       Index of the ``if`` statement in its line, counted from 1.
		:param trueCount:   How often the branch was taken.
		:param falseCount:  How often the branch's condition was false; ``0`` for an ``else`` or *AllFalse* branch.
		:param parent:      Optional, the ``if`` statement the branch belongs to. Default: ``None``.
		:raises ValueError: If parameter ``file`` is ``None``.
		:raises TypeError:  If parameter ``file`` isn't of type :class:`~pathlib.Path`.
		:raises ValueError: If parameter ``lineNumber`` is ``None``.
		:raises TypeError:  If parameter ``lineNumber`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``lineNumber`` is less than 1.
		:raises ValueError: If parameter ``index`` is ``None``.
		:raises TypeError:  If parameter ``index`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``index`` is less than 1.
		:raises ValueError: If parameter ``trueCount`` is ``None``.
		:raises TypeError:  If parameter ``trueCount`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``trueCount`` is negative.
		:raises ValueError: If parameter ``falseCount`` is ``None``.
		:raises TypeError:  If parameter ``falseCount`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``falseCount`` is negative.
		:raises TypeError:  If parameter ``parent`` isn't of type :class:`IfStatement`.
		"""
		super().__init__(file, lineNumber, index)

		if trueCount is None:
			raise ValueError(f"Parameter 'trueCount' is None.")
		elif not isinstance(trueCount, int):
			ex = TypeError(f"Parameter 'trueCount' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(trueCount)}'.")
			raise ex
		elif trueCount < 0:
			ex = ValueError(f"Parameter 'trueCount' is negative.")
			ex.add_note(f"Got value '{trueCount}'.")
			raise ex

		if falseCount is None:
			raise ValueError(f"Parameter 'falseCount' is None.")
		elif not isinstance(falseCount, int):
			ex = TypeError(f"Parameter 'falseCount' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(falseCount)}'.")
			raise ex
		elif falseCount < 0:
			ex = ValueError(f"Parameter 'falseCount' is negative.")
			ex.add_note(f"Got value '{falseCount}'.")
			raise ex

		if parent is not None and not isinstance(parent, IfStatement):
			ex = TypeError(f"Parameter 'parent' is not of type 'IfStatement'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =     parent
		self._trueCount =  trueCount
		self._falseCount = falseCount

		if parent is not None:
			parent._branches.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: IfStatement) -> Self:
		"""
		Parse a branch from its ``<ielem>`` element.

		:param element:            The ``<ielem>`` element.
		:param parent:             The ``if`` statement the branch belongs to; it belongs to a scope.
		:returns:                  The branch.
		:raises CodeCoverageError: If the branch's file number isn't in the scope's source table, or it states none and
		                           the scope has no single file.
		"""
		return cls(
			parent._parent._ResolveFile(element),
			int(element.attrib["ln"]),
			int(element.attrib["st"]),
			int(element.attrib["true"]),
			int(element.attrib["false"]),
			parent=parent
		)

	@readonly
	def Parent(self) -> Nullable[IfStatement]:
		"""
		Read-only property to access the ``if`` statement the branch belongs to (:attr:`_parent`).

		:returns: The ``if`` statement; ``None`` if the branch belongs to none.
		"""
		return self._parent

	@readonly
	def TrueCount(self) -> int:
		"""
		Read-only property to access how often the branch was taken (:attr:`_trueCount`).

		:returns: The count.
		"""
		return self._trueCount

	@readonly
	def FalseCount(self) -> int:
		"""
		Read-only property to access how often the branch's condition was false (:attr:`_falseCount`).

		Then the evaluation went on to the next branch: the count is the sum of the next branches' true counts.

		:returns: The count; ``0`` for an ``else`` or *AllFalse* branch.
		"""
		return self._falseCount


@export
class CaseStatement(metaclass=ExtendedType, slots=True):
	"""
	A ``<case>`` of a scope: a ``case`` statement, and how often each of its branches was taken.

	Each case item is a branch (``<celem>``, :class:`CaseBranch`); the ``case`` statement's line isn't stated.
	"""

	_parent:   Nullable[Scope]   #: The scope the ``case`` statement belongs to.
	_branches: list[CaseBranch]  #: The branches, in the order of the case items.

	def __init__(self, *, parent: Nullable[Scope] = None) -> None:
		"""
		Initialize the ``case`` statement, and append it to the ``case`` statements of its scope.

		Its branches are added by creating them with this ``case`` statement as their parent.

		:param parent:     Optional, the scope the ``case`` statement belongs to. Default: ``None``.
		:raises TypeError: If parameter ``parent`` isn't of type
		                   :class:`~pyEDAA.Reports.CodeCoverage.QuestaSim.Scopes.Scope`.
		"""
		from pyEDAA.Reports.CodeCoverage.QuestaSim.Scopes import Scope

		if parent is not None and not isinstance(parent, Scope):
			ex = TypeError(f"Parameter 'parent' is not of type 'Scope'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =   parent
		self._branches = []

		if parent is not None:
			parent._caseStatements.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Scope) -> Self:
		"""
		Parse a ``case`` statement and its branches from its ``<case>`` element.

		:param element:            The ``<case>`` element.
		:param parent:             The scope the ``case`` statement belongs to.
		:returns:                  The ``case`` statement.
		:raises CodeCoverageError: If a branch's file number isn't in the scope's source table, or it states none and the
		                           scope has no single file.
		:raises CodeCoverageError: If the ``case`` statement states other numbers of branches and taken branches than its
		                           branches have.
		"""
		caseStatement = cls(parent=parent)
		for branchElement in element.iterfind("celem"):
			CaseBranch.Parse(branchElement, parent=caseStatement)

		active, hits = int(element.attrib["active"]), int(element.attrib["hits"])
		if (active, hits) != (len(caseStatement._branches), caseStatement.TakenBranches):
			ex = CodeCoverageError(f"'<case>' in line {element.sourceline} states other figures than its branches have.")
			ex.add_note(f"Got '{hits}' of '{active}' branches taken, its branches have {caseStatement.TakenBranches} of "
			            f"{len(caseStatement._branches)}.")
			raise ex

		return caseStatement

	@readonly
	def Parent(self) -> Nullable[Scope]:
		"""
		Read-only property to access the scope the ``case`` statement belongs to (:attr:`_parent`).

		:returns: The scope; ``None`` if the ``case`` statement belongs to no scope.
		"""
		return self._parent

	@readonly
	def Branches(self) -> list[CaseBranch]:
		"""
		Read-only property to access the branches (:attr:`_branches`).

		:returns: The branches, in the order of the case items.
		"""
		return self._branches

	@readonly
	def TakenBranches(self) -> int:
		"""
		Read-only property to return the number of branches, which were taken.

		:returns: The number of branches with a positive :attr:`CaseBranch.Hits`.
		"""
		return sum(1 for branch in self._branches if branch._hits > 0)

	@readonly
	def EvaluationCount(self) -> int:
		"""
		Read-only property to return how often the ``case`` statement was evaluated.

		Each evaluation takes exactly one branch, so it is the sum of the branches' :attr:`CaseBranch.Hits`.

		:returns: The number of evaluations.
		"""
		return sum(branch._hits for branch in self._branches)


@export
class CaseBranch(SourceItem):
	"""
	A ``<celem>`` of a ``case`` statement: a case item, and how often it was taken.
	"""

	_parent: Nullable[CaseStatement]  #: The ``case`` statement the branch belongs to.
	_hits:   int                      #: How often the branch was taken.

	def __init__(
		self,
		file: Path,
		lineNumber: int,
		index: int,
		hits: int,
		*,
		parent: Nullable[CaseStatement] = None
	) -> None:
		"""
		Initialize the branch, and append it to the branches of its ``case`` statement.

		:param file:        Path of the source file, as the report states it.
		:param lineNumber:  Line number of the case item, counted from 1.
		:param index:       Index of the case item in its line, counted from 1.
		:param hits:        How often the branch was taken.
		:param parent:      Optional, the ``case`` statement the branch belongs to. Default: ``None``.
		:raises ValueError: If parameter ``file`` is ``None``.
		:raises TypeError:  If parameter ``file`` isn't of type :class:`~pathlib.Path`.
		:raises ValueError: If parameter ``lineNumber`` is ``None``.
		:raises TypeError:  If parameter ``lineNumber`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``lineNumber`` is less than 1.
		:raises ValueError: If parameter ``index`` is ``None``.
		:raises TypeError:  If parameter ``index`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``index`` is less than 1.
		:raises ValueError: If parameter ``hits`` is ``None``.
		:raises TypeError:  If parameter ``hits`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``hits`` is negative.
		:raises TypeError:  If parameter ``parent`` isn't of type :class:`CaseStatement`.
		"""
		super().__init__(file, lineNumber, index)

		if hits is None:
			raise ValueError(f"Parameter 'hits' is None.")
		elif not isinstance(hits, int):
			ex = TypeError(f"Parameter 'hits' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(hits)}'.")
			raise ex
		elif hits < 0:
			ex = ValueError(f"Parameter 'hits' is negative.")
			ex.add_note(f"Got value '{hits}'.")
			raise ex

		if parent is not None and not isinstance(parent, CaseStatement):
			ex = TypeError(f"Parameter 'parent' is not of type 'CaseStatement'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent = parent
		self._hits =   hits

		if parent is not None:
			parent._branches.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: CaseStatement) -> Self:
		"""
		Parse a branch from its ``<celem>`` element.

		:param element:            The ``<celem>`` element.
		:param parent:             The ``case`` statement the branch belongs to; it belongs to a scope.
		:returns:                  The branch.
		:raises CodeCoverageError: If the branch's file number isn't in the scope's source table, or it states none and
		                           the scope has no single file.
		"""
		return cls(
			parent._parent._ResolveFile(element),
			int(element.attrib["ln"]),
			int(element.attrib["st"]),
			int(element.attrib["hits"]),
			parent=parent
		)

	@readonly
	def Parent(self) -> Nullable[CaseStatement]:
		"""
		Read-only property to access the ``case`` statement the branch belongs to (:attr:`_parent`).

		:returns: The ``case`` statement; ``None`` if the branch belongs to none.
		"""
		return self._parent

	@readonly
	def Hits(self) -> int:
		"""
		Read-only property to access how often the branch was taken (:attr:`_hits`).

		:returns: The count.
		"""
		return self._hits
