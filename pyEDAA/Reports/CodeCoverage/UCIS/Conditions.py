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
The condition and expression coverage of the UCIS XML interchange format: an instance's ``<conditionCoverage>`` and its
expressions, nested by their sub-expressions.
"""
from __future__                                   import annotations

from typing                                       import TYPE_CHECKING, Generic, Iterable, Optional as Nullable, Self
from typing                                       import TypeVar

from lxml.etree                                   import _Element
from pyTooling.Common                             import getFullyQualifiedName
from pyTooling.Decorators                         import export, readonly

from pyEDAA.Reports.CodeCoverage.UCIS.Bins        import Bin
from pyEDAA.Reports.CodeCoverage.UCIS.Elements    import Base, MetricCoverage, ObjectAttributesMixin, StatementID
from pyEDAA.Reports.CodeCoverage.UCIS.Elements    import UserAttribute

if TYPE_CHECKING:
	from pyEDAA.Reports.CodeCoverage.UCIS.Instances import InstanceCoverage


__all__ = ["ExpressionParentType"]

ExpressionParentType = TypeVar("ExpressionParentType", bound="ConditionCoverage | Expression")
"""A type variable for the parent of an :class:`Expression`: a :class:`ConditionCoverage` or an :class:`Expression`."""


@export
class ConditionCoverage(MetricCoverage):
	"""
	A ``<conditionCoverage>`` of an instance: its top-level expressions, of conditions or assignments.
	"""

	_expressions: list[Expression[ConditionCoverage]]  #: The top-level expressions.

	def __init__(
		self,
		metricMode: Nullable[str] = None,
		weight: int = 1,
		userAttributes: Nullable[Iterable[UserAttribute]] = None,
		*,
		parent: Nullable[InstanceCoverage] = None
	) -> None:
		"""
		Initialize the condition coverage, and append it to the condition coverages of its instance.

		Its expressions are added by creating them with this coverage as their parent.

		:param metricMode:     Optional, the mode in which the coverage was measured, e.g. ``UCIS:BITWISE_FLAT``.
		                       Default: ``None``.
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

		self._expressions = []

		if parent is not None:
			parent._conditionCoverages.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[InstanceCoverage] = None) -> Self:
		"""
		Parse a condition coverage and its expressions from its ``<conditionCoverage>`` element.

		:param element:            The ``<conditionCoverage>`` element.
		:param parent:             Optional, the instance the coverage belongs to. Default: ``None``.
		:returns:                  The condition coverage.
		:raises CodeCoverageError: If a user-defined attribute's value isn't of the type the attribute states.
		"""
		conditionCoverage = cls(
			element.attrib.get("metricMode"),
			int(element.attrib.get("weight", "1")),
			cls._ParseUserAttributes(element),
			parent=parent
		)

		for expressionElement in element.iterfind("{*}expr"):
			Expression.Parse(expressionElement, parent=conditionCoverage)

		return conditionCoverage

	@readonly
	def Expressions(self) -> list[Expression[ConditionCoverage]]:
		"""
		Read-only property to access the top-level expressions (:attr:`_expressions`).

		:returns: The expressions, in the order the report lists them.
		"""
		return self._expressions


@export
class Expression(Base, ObjectAttributesMixin, Generic[ExpressionParentType]):
	"""
	An ``<expr>`` of a condition coverage - or a ``<hierarchicalExpr>`` of an expression -: the expression, where it is,
	its sub-expressions, the bins of the combinations of their values, and the expressions nested in it.
	"""

	_parent:         Nullable[ExpressionParentType]  #: The condition coverage or expression the expression belongs to.
	_name:           str                             #: UCIS name of the expression.
	_key:            str                             #: UCIS key of the expression.
	_text:           str                             #: The expression's text, e.g. ``(a&&b) || (c&&d)``.
	_index:          int                             #: Index of the expression in its parent expression.
	_width:          int                             #: Bit width of the expression.
	_id:             StatementID                     #: Where the expression is.
	_subExpressions: list[str]                       #: The sub-expressions, whose values the bins combine.
	_bins:           list[Bin]                       #: The bins of the combinations of the sub-expressions' values.
	_statementType:  Nullable[str]                   #: Kind of the statement containing the expression, e.g. ``if``.
	_expressions:    list[Expression[Expression]]    #: The expressions nested in this one.

	def __init__(
		self,
		name: str,
		key: str,
		text: str,
		index: int,
		width: int,
		statementID: StatementID,
		subExpressions: Iterable[str],
		bins: Iterable[Bin],
		statementType: Nullable[str] = None,
		alias: Nullable[str] = None,
		excluded: bool = False,
		excludedReason: Nullable[str] = None,
		weight: int = 1,
		userAttributes: Nullable[Iterable[UserAttribute]] = None,
		*,
		parent: Nullable[ExpressionParentType] = None
	) -> None:
		"""
		Initialize the expression, become its bins' parent, and append it to the expressions of its parent.

		The expressions nested in it are added by creating them with this expression as their parent.

		:param name:           UCIS name of the expression.
		:param key:            UCIS key of the expression.
		:param text:           The expression's text, e.g. ``(a&&b) || (c&&d)``.
		:param index:          Index of the expression in its parent expression; ``0`` for a top-level expression.
		:param width:          Bit width of the expression.
		:param statementID:    Where the expression is.
		:param subExpressions: The sub-expressions, whose values the bins combine, e.g. ``a`` and ``b``.
		:param bins:           The bins of the combinations of the sub-expressions' values.
		:param statementType:  Optional, kind of the statement containing the expression, e.g. ``if``. Default: ``None``.
		:param alias:          Optional, an alias of the expression's name. Default: ``None``.
		:param excluded:       Optional, whether the expression is excluded from the coverage. Default: ``False``.
		:param excludedReason: Optional, why the expression is excluded. Default: ``None``.
		:param weight:         Optional, weight of the expression in computing the coverage. Default: ``1``.
		:param userAttributes: Optional, the user-defined attributes. Default: ``None``.
		:param parent:         Optional, the condition coverage or expression the expression belongs to. Default: ``None``.
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
		:raises ValueError:    If parameter ``name``, ``key`` or ``text`` is ``None``.
		:raises TypeError:     If parameter ``name``, ``key`` or ``text`` isn't of type :class:`str`.
		:raises ValueError:    If parameter ``index`` or ``width`` is ``None``.
		:raises TypeError:     If parameter ``index`` or ``width`` isn't of type :class:`int`.
		:raises ValueError:    If parameter ``index`` or ``width`` is negative.
		:raises ValueError:    If parameter ``statementID`` is ``None``.
		:raises TypeError:     If parameter ``statementID`` isn't of type
		                       :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Elements.StatementID`.
		:raises TypeError:     If parameter ``statementType`` isn't of type :class:`str`.
		:raises TypeError:     If parameter ``parent`` isn't of type :class:`ConditionCoverage` or :class:`Expression`.
		:raises ValueError:    If parameter ``subExpressions`` is ``None``.
		:raises TypeError:     If parameter ``subExpressions`` isn't iterable.
		:raises TypeError:     If parameter ``subExpressions`` contains an element not of type :class:`str`.
		:raises ValueError:    If parameter ``bins`` is ``None``.
		:raises TypeError:     If parameter ``bins`` isn't iterable.
		:raises TypeError:     If parameter ``bins`` contains an element not of type
		                       :class:`~pyEDAA.Reports.CodeCoverage.UCIS.Bins.Bin`.
		"""
		super().__init__(userAttributes)
		ObjectAttributesMixin.__init__(self, alias, excluded, excludedReason, weight)

		for parameterName, value in (
			("name", name),
			("key",  key),
			("text", text)
		):
			if value is None:
				raise ValueError(f"Parameter '{parameterName}' is None.")
			elif not isinstance(value, str):
				ex = TypeError(f"Parameter '{parameterName}' is not of type 'str'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
				raise ex

		for parameterName, value in (
			("index", index),
			("width", width)
		):
			if value is None:
				raise ValueError(f"Parameter '{parameterName}' is None.")
			elif not isinstance(value, int) or isinstance(value, bool):
				ex = TypeError(f"Parameter '{parameterName}' is not of type 'int'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
				raise ex
			elif value < 0:
				ex = ValueError(f"Parameter '{parameterName}' is negative.")
				ex.add_note(f"Got value '{value}'.")
				raise ex

		if statementID is None:
			raise ValueError(f"Parameter 'statementID' is None.")
		elif not isinstance(statementID, StatementID):
			ex = TypeError(f"Parameter 'statementID' is not of type 'StatementID'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(statementID)}'.")
			raise ex

		if statementType is not None and not isinstance(statementType, str):
			ex = TypeError(f"Parameter 'statementType' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(statementType)}'.")
			raise ex

		if parent is not None and not isinstance(parent, (ConditionCoverage, Expression)):
			ex = TypeError(f"Parameter 'parent' is not of type 'ConditionCoverage' or 'Expression'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =         parent
		self._name =           name
		self._key =            key
		self._text =           text
		self._index =          index
		self._width =          width
		self._id =             statementID
		self._subExpressions = []
		self._bins =           []
		self._statementType =  statementType
		self._expressions =    []

		if subExpressions is None:
			raise ValueError(f"Parameter 'subExpressions' is None.")
		elif not isinstance(subExpressions, Iterable):
			ex = TypeError(f"Parameter 'subExpressions' is not iterable.")
			ex.add_note(f"Got type '{getFullyQualifiedName(subExpressions)}'.")
			raise ex

		for subExpression in subExpressions:
			if not isinstance(subExpression, str):
				ex = TypeError(f"Parameter 'subExpressions' contains an element not of type 'str'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(subExpression)}'.")
				raise ex

			self._subExpressions.append(subExpression)

		if bins is None:
			raise ValueError(f"Parameter 'bins' is None.")
		elif not isinstance(bins, Iterable):
			ex = TypeError(f"Parameter 'bins' is not iterable.")
			ex.add_note(f"Got type '{getFullyQualifiedName(bins)}'.")
			raise ex

		for coverBin in bins:
			if not isinstance(coverBin, Bin):
				ex = TypeError(f"Parameter 'bins' contains an element not of type 'Bin'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(coverBin)}'.")
				raise ex

			coverBin._parent = self
			self._bins.append(coverBin)

		if parent is not None:
			parent._expressions.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[ExpressionParentType] = None) -> Self:
		"""
		Parse an expression, its bins and the expressions nested in it from its ``<expr>`` or ``<hierarchicalExpr>``
		element.

		:param element:            The ``<expr>`` or ``<hierarchicalExpr>`` element.
		:param parent:             Optional, the condition coverage or expression the expression belongs to. Default:
		                           ``None``.
		:returns:                  The expression.
		:raises CodeCoverageError: If a user-defined attribute's value isn't of the type the attribute states.
		"""
		expression = cls(
			element.attrib["name"],
			element.attrib["key"],
			element.attrib["exprString"],
			int(element.attrib["index"]),
			int(element.attrib["width"]),
			StatementID.Parse(element.find("{*}id")),
			[subExpressionElement.text or "" for subExpressionElement in element.iterfind("{*}subExpr")],
			[Bin.Parse(binElement) for binElement in element.iterfind("{*}bin")],
			element.attrib.get("statementType"),
			element.attrib.get("alias"),
			cls._ParseBoolean(element.attrib.get("excluded", "false")),
			element.attrib.get("excludedReason"),
			int(element.attrib.get("weight", "1")),
			cls._ParseUserAttributes(element),
			parent=parent
		)

		for expressionElement in element.iterfind("{*}hierarchicalExpr"):
			Expression.Parse(expressionElement, parent=expression)

		return expression

	@readonly
	def Parent(self) -> Nullable[ExpressionParentType]:
		"""
		Read-only property to access the condition coverage or expression the expression belongs to (:attr:`_parent`).

		:returns: The :class:`ConditionCoverage` or :class:`Expression`; ``None``, if the expression belongs to none.
		"""
		return self._parent

	@readonly
	def Name(self) -> str:
		"""
		Read-only property to access the UCIS name of the expression (:attr:`_name`).

		:returns: The name, as stated.
		"""
		return self._name

	@readonly
	def Key(self) -> str:
		"""
		Read-only property to access the UCIS key of the expression (:attr:`_key`).

		:returns: The key, as stated.
		"""
		return self._key

	@readonly
	def Text(self) -> str:
		"""
		Read-only property to access the expression's text (:attr:`_text`).

		:returns: The text, e.g. ``(a&&b) || (c&&d)``.
		"""
		return self._text

	@readonly
	def Index(self) -> int:
		"""
		Read-only property to access the index of the expression in its parent expression (:attr:`_index`).

		:returns: The index; ``0`` for a top-level expression.
		"""
		return self._index

	@readonly
	def Width(self) -> int:
		"""
		Read-only property to access the bit width of the expression (:attr:`_width`).

		:returns: The width.
		"""
		return self._width

	@readonly
	def ID(self) -> StatementID:
		"""
		Read-only property to access where the expression is (:attr:`_id`).

		:returns: The source statement identifier.
		"""
		return self._id

	@readonly
	def SubExpressions(self) -> list[str]:
		"""
		Read-only property to access the sub-expressions, whose values the bins combine (:attr:`_subExpressions`).

		:returns: The sub-expressions, in the order the report lists them.
		"""
		return self._subExpressions

	@readonly
	def Bins(self) -> list[Bin]:
		"""
		Read-only property to access the bins of the combinations of the sub-expressions' values (:attr:`_bins`).

		:returns: The bins, in the order the report lists them.
		"""
		return self._bins

	@readonly
	def StatementType(self) -> Nullable[str]:
		"""
		Read-only property to access the kind of the statement containing the expression (:attr:`_statementType`).

		:returns: The kind, e.g. ``if``; ``None``, if the report states none.
		"""
		return self._statementType

	@readonly
	def Expressions(self) -> list[Expression[Expression]]:
		"""
		Read-only property to access the expressions nested in this one (:attr:`_expressions`).

		:returns: The expressions, in the order the report lists them.
		"""
		return self._expressions
