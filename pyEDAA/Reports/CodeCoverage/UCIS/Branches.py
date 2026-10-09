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
The branch coverage of the UCIS XML interchange format: an instance's ``<branchCoverage>``, its branching statements
and their branches.
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


__all__ = ["BranchStatementParentType"]

# A class with a property named like a class - ``Bin`` - can't name that class in the annotation of a field: the class
# body's namespace, where annotations are evaluated, binds the name to the property.
_Bin = Bin

BranchStatementParentType = TypeVar("BranchStatementParentType", bound="BranchCoverage | Branch")
"""A type variable for the parent of a :class:`BranchStatement`: a :class:`BranchCoverage` or a :class:`Branch`."""


@export
class BranchCoverage(MetricCoverage):
	"""
	A ``<branchCoverage>`` of an instance: its branching statements.
	"""

	_statements: list[BranchStatement[BranchCoverage]]  #: The branching statements.

	def __init__(
		self,
		metricMode: Nullable[str] = None,
		weight: int = 1,
		userAttributes: Nullable[Iterable[UserAttribute]] = None,
		*,
		parent: Nullable[InstanceCoverage] = None
	) -> None:
		"""
		Initialize the branch coverage, and append it to the branch coverages of its instance.

		Its branching statements are added by creating them with this coverage as their parent.

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

		if parent is not None:
			parent._branchCoverages.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[InstanceCoverage] = None) -> Self:
		"""
		Parse a branch coverage and its branching statements from its ``<branchCoverage>`` element.

		:param element:            The ``<branchCoverage>`` element.
		:param parent:             Optional, the instance the coverage belongs to. Default: ``None``.
		:returns:                  The branch coverage.
		:raises CodeCoverageError: If a user-defined attribute's value isn't of the type the attribute states.
		"""
		branchCoverage = cls(
			element.attrib.get("metricMode"),
			int(element.attrib.get("weight", "1")),
			cls._ParseUserAttributes(element),
			parent=parent
		)

		for statementElement in element.iterfind("{*}statement"):
			BranchStatement.Parse(statementElement, parent=branchCoverage)

		return branchCoverage

	def IterateStatements(self) -> Generator[BranchStatement, None, None]:
		"""
		Iterate the branching statements, each followed by the branching statements nested in its branches.

		:returns: A generator of the branching statements.
		"""
		for statement in self._statements:
			yield statement
			yield from statement.IterateStatements()

	@readonly
	def Statements(self) -> list[BranchStatement[BranchCoverage]]:
		"""
		Read-only property to access the branching statements (:attr:`_statements`).

		:returns: The branching statements, which aren't nested in a branch, in the order the report lists them.
		"""
		return self._statements


@export
class BranchStatement(Base, ObjectAttributesMixin, Generic[BranchStatementParentType]):
	"""
	A branching statement - a ``<statement>`` of a branch coverage, or a ``<nestedBranch>`` of a branch -: where it is,
	its kind, its expression and its branches.
	"""

	_parent:           Nullable[BranchStatementParentType]  #: The branch coverage or branch the statement belongs to.
	_id:               StatementID                          #: Where the branching statement is.
	_statementType:    str                                  #: Kind of the branching statement, e.g. ``if``.
	_branchExpression: Nullable[str]                        #: The expression the statement branches on.
	_branches:         list[Branch]                         #: The branches.

	def __init__(
		self,
		statementID: StatementID,
		statementType: str,
		branchExpression: Nullable[str] = None,
		alias: Nullable[str] = None,
		excluded: bool = False,
		excludedReason: Nullable[str] = None,
		weight: int = 1,
		userAttributes: Nullable[Iterable[UserAttribute]] = None,
		*,
		parent: Nullable[BranchStatementParentType] = None
	) -> None:
		"""
		Initialize the branching statement, and append it to the branching statements of its parent.

		Its branches are added by creating them with this statement as their parent.

		:param statementID:      Where the branching statement is.
		:param statementType:    Kind of the branching statement, e.g. ``if`` or ``case``.
		:param branchExpression: Optional, the expression the statement branches on, e.g. ``(x)``. Default: ``None``.
		:param alias:            Optional, an alias of the statement's name. Default: ``None``.
		:param excluded:         Optional, whether the statement is excluded from the coverage. Default: ``False``.
		:param excludedReason:   Optional, why the statement is excluded. Default: ``None``.
		:param weight:           Optional, weight of the statement in computing the coverage. Default: ``1``.
		:param userAttributes:   Optional, the user-defined attributes. Default: ``None``.
		:param parent:           Optional, the branch coverage or branch the statement belongs to. Default: ``None``.
		:raises TypeError:       If parameter ``userAttributes`` isn't iterable.
		:raises TypeError:       If parameter ``userAttributes`` contains an element not of type
		                         :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Elements.UserAttribute`.
		:raises TypeError:       If parameter ``alias`` isn't of type :class:`str`.
		:raises ValueError:      If parameter ``excluded`` is ``None``.
		:raises TypeError:       If parameter ``excluded`` isn't of type :class:`bool`.
		:raises TypeError:       If parameter ``excludedReason`` isn't of type :class:`str`.
		:raises ValueError:      If parameter ``weight`` is ``None``.
		:raises TypeError:       If parameter ``weight`` isn't of type :class:`int`.
		:raises ValueError:      If parameter ``weight`` is negative.
		:raises ValueError:      If parameter ``statementID`` is ``None``.
		:raises TypeError:       If parameter ``statementID`` isn't of type
		                         :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Elements.StatementID`.
		:raises ValueError:      If parameter ``statementType`` is ``None``.
		:raises TypeError:       If parameter ``statementType`` isn't of type :class:`str`.
		:raises TypeError:       If parameter ``branchExpression`` isn't of type :class:`str`.
		:raises TypeError:       If parameter ``parent`` isn't of type :class:`BranchCoverage` or :class:`Branch`.
		"""
		super().__init__(userAttributes)
		ObjectAttributesMixin.__init__(self, alias, excluded, excludedReason, weight)

		if statementID is None:
			raise ValueError(f"Parameter 'statementID' is None.")
		elif not isinstance(statementID, StatementID):
			ex = TypeError(f"Parameter 'statementID' is not of type 'StatementID'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(statementID)}'.")
			raise ex

		if statementType is None:
			raise ValueError(f"Parameter 'statementType' is None.")
		elif not isinstance(statementType, str):
			ex = TypeError(f"Parameter 'statementType' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(statementType)}'.")
			raise ex

		if branchExpression is not None and not isinstance(branchExpression, str):
			ex = TypeError(f"Parameter 'branchExpression' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(branchExpression)}'.")
			raise ex

		if parent is not None and not isinstance(parent, (BranchCoverage, Branch)):
			ex = TypeError(f"Parameter 'parent' is not of type 'BranchCoverage' or 'Branch'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =           parent
		self._id =               statementID
		self._statementType =    statementType
		self._branchExpression = branchExpression
		self._branches =         []

		if parent is not None:
			parent._statements.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[BranchStatementParentType] = None) -> Self:
		"""
		Parse a branching statement and its branches from its ``<statement>`` or ``<nestedBranch>`` element.

		:param element:            The ``<statement>`` or ``<nestedBranch>`` element.
		:param parent:             Optional, the branch coverage or branch the statement belongs to. Default: ``None``.
		:returns:                  The branching statement.
		:raises CodeCoverageError: If a user-defined attribute's value isn't of the type the attribute states.
		"""
		statement = cls(
			StatementID.Parse(element.find("{*}id")),
			element.attrib["statementType"],
			element.attrib.get("branchExpr"),
			element.attrib.get("alias"),
			cls._ParseBoolean(element.attrib.get("excluded", "false")),
			element.attrib.get("excludedReason"),
			int(element.attrib.get("weight", "1")),
			cls._ParseUserAttributes(element),
			parent=parent
		)

		for branchElement in element.iterfind("{*}branch"):
			Branch.Parse(branchElement, parent=statement)

		return statement

	def IterateStatements(self) -> Generator[BranchStatement[Branch], None, None]:
		"""
		Iterate the branching statements nested in this statement's branches, each followed by those nested in it.

		:returns: A generator of the branching statements.
		"""
		for branch in self._branches:
			for statement in branch._statements:
				yield statement
				yield from statement.IterateStatements()

	@readonly
	def Parent(self) -> Nullable[BranchStatementParentType]:
		"""
		Read-only property to access the branch coverage or branch the statement belongs to (:attr:`_parent`).

		:returns: The :class:`BranchCoverage` or :class:`Branch`; ``None``, if the statement belongs to none.
		"""
		return self._parent

	@readonly
	def ID(self) -> StatementID:
		"""
		Read-only property to access where the branching statement is (:attr:`_id`).

		:returns: The source statement identifier.
		"""
		return self._id

	@readonly
	def StatementType(self) -> str:
		"""
		Read-only property to access the kind of the branching statement (:attr:`_statementType`).

		:returns: The kind, e.g. ``if`` or ``case``.
		"""
		return self._statementType

	@readonly
	def BranchExpression(self) -> Nullable[str]:
		"""
		Read-only property to access the expression the statement branches on (:attr:`_branchExpression`).

		:returns: The expression; ``None``, if the report states none.
		"""
		return self._branchExpression

	@readonly
	def Branches(self) -> list[Branch]:
		"""
		Read-only property to access the branches (:attr:`_branches`).

		:returns: The branches, in the order the report lists them.
		"""
		return self._branches


@export
class Branch(Base):
	"""
	A ``<branch>`` of a branching statement: where it is, its bin - how often it was taken - and the branching
	statements nested in it.
	"""

	_parent:     Nullable[BranchStatement]               #: The branching statement the branch belongs to.
	_id:         StatementID                             #: Where the branch is.
	_bin:        _Bin                                    #: How often the branch was taken.
	_statements: list[BranchStatement[Branch]]           #: The branching statements nested in the branch.

	def __init__(
		self,
		branchID: StatementID,
		coverBin: Bin,
		userAttributes: Nullable[Iterable[UserAttribute]] = None,
		*,
		parent: Nullable[BranchStatement] = None
	) -> None:
		"""
		Initialize the branch, become its bin's parent, and append it to the branches of its branching statement.

		The branching statements nested in it are added by creating them with this branch as their parent.

		:param branchID:       Where the branch is.
		:param coverBin:       How often the branch was taken.
		:param userAttributes: Optional, the user-defined attributes. Default: ``None``.
		:param parent:         Optional, the branching statement the branch belongs to. Default: ``None``.
		:raises TypeError:     If parameter ``userAttributes`` isn't iterable.
		:raises TypeError:     If parameter ``userAttributes`` contains an element not of type
		                       :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Elements.UserAttribute`.
		:raises ValueError:    If parameter ``branchID`` is ``None``.
		:raises TypeError:     If parameter ``branchID`` isn't of type
		                       :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Elements.StatementID`.
		:raises ValueError:    If parameter ``coverBin`` is ``None``.
		:raises TypeError:     If parameter ``coverBin`` isn't of type :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Bins.Bin`.
		:raises TypeError:     If parameter ``parent`` isn't of type :class:`BranchStatement`.
		"""
		super().__init__(userAttributes)

		if branchID is None:
			raise ValueError(f"Parameter 'branchID' is None.")
		elif not isinstance(branchID, StatementID):
			ex = TypeError(f"Parameter 'branchID' is not of type 'StatementID'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(branchID)}'.")
			raise ex

		if coverBin is None:
			raise ValueError(f"Parameter 'coverBin' is None.")
		elif not isinstance(coverBin, Bin):
			ex = TypeError(f"Parameter 'coverBin' is not of type 'Bin'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(coverBin)}'.")
			raise ex

		if parent is not None and not isinstance(parent, BranchStatement):
			ex = TypeError(f"Parameter 'parent' is not of type 'BranchStatement'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =     parent
		self._id =         branchID
		self._bin =        coverBin
		self._statements = []
		coverBin._parent = self

		if parent is not None:
			parent._branches.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[BranchStatement] = None) -> Self:
		"""
		Parse a branch, its bin and the branching statements nested in it from its ``<branch>`` element.

		:param element:            The ``<branch>`` element.
		:param parent:             Optional, the branching statement the branch belongs to. Default: ``None``.
		:returns:                  The branch.
		:raises CodeCoverageError: If a user-defined attribute's value isn't of the type the attribute states.
		"""
		branch = cls(
			StatementID.Parse(element.find("{*}id")),
			Bin.Parse(element.find("{*}branchBin")),
			cls._ParseUserAttributes(element),
			parent=parent
		)

		for statementElement in element.iterfind("{*}nestedBranch"):
			BranchStatement.Parse(statementElement, parent=branch)

		return branch

	@readonly
	def Parent(self) -> Nullable[BranchStatement]:
		"""
		Read-only property to access the branching statement the branch belongs to (:attr:`_parent`).

		:returns: The branching statement; ``None``, if the branch belongs to none.
		"""
		return self._parent

	@readonly
	def ID(self) -> StatementID:
		"""
		Read-only property to access where the branch is (:attr:`_id`).

		:returns: The source statement identifier.
		"""
		return self._id

	@readonly
	def Bin(self) -> Bin:
		"""
		Read-only property to access the branch's bin (:attr:`_bin`).

		:returns: The bin, stating how often the branch was taken.
		"""
		return self._bin

	@readonly
	def Statements(self) -> list[BranchStatement[Branch]]:
		"""
		Read-only property to access the branching statements nested in the branch (:attr:`_statements`).

		:returns: The branching statements, in the order the report lists them.
		"""
		return self._statements
