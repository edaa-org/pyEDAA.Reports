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
The options of the covergroup coverage of the UCIS XML interchange format: the ``<options>`` of a covergroup instance,
a coverpoint or a cross, as SystemVerilog declares them.
"""
from __future__                                import annotations

from typing                                    import Self

from lxml.etree                                import _Element
from pyTooling.Common                          import getFullyQualifiedName
from pyTooling.Decorators                      import export, readonly
from pyTooling.MetaClasses                     import ExtendedType, abstractclass

from pyEDAA.Reports.CodeCoverage.UCIS.Elements import Base


@export
@abstractclass
class Options(metaclass=ExtendedType, slots=True):
	"""
	Base-class of the ``<options>`` of a covergroup instance, a coverpoint or a cross: the options SystemVerilog declares
	for all three.

	It is a value, as a path is: it names no parent.
	"""

	_weight:  int  #: Weight in computing the coverage.
	_goal:    int  #: Coverage goal, in percent.
	_comment: str  #: A comment.
	_atLeast: int  #: How often a bin must be hit to be covered.

	def __init__(self, weight: int = 1, goal: int = 100, comment: str = "", atLeast: int = 1) -> None:
		"""
		Initialize the options.

		:param weight:      Optional, weight in computing the coverage. Default: ``1``.
		:param goal:        Optional, coverage goal, in percent. Default: ``100``.
		:param comment:     Optional, a comment. Default: ``""``.
		:param atLeast:     Optional, how often a bin must be hit to be covered. Default: ``1``.
		:raises ValueError: If parameter ``weight``, ``goal`` or ``atLeast`` is ``None``.
		:raises TypeError:  If parameter ``weight``, ``goal`` or ``atLeast`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``weight``, ``goal`` or ``atLeast`` is negative.
		:raises ValueError: If parameter ``comment`` is ``None``.
		:raises TypeError:  If parameter ``comment`` isn't of type :class:`str`.
		"""
		for parameterName, value in (
			("weight",  weight),
			("goal",    goal),
			("atLeast", atLeast)
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

		if comment is None:
			raise ValueError(f"Parameter 'comment' is None.")
		elif not isinstance(comment, str):
			ex = TypeError(f"Parameter 'comment' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(comment)}'.")
			raise ex

		self._weight =  weight
		self._goal =    goal
		self._comment = comment
		self._atLeast = atLeast

	@readonly
	def Weight(self) -> int:
		"""
		Read-only property to access the weight in computing the coverage (:attr:`_weight`).

		:returns: The weight; ``1``, if the report states none.
		"""
		return self._weight

	@readonly
	def Goal(self) -> int:
		"""
		Read-only property to access the coverage goal (:attr:`_goal`).

		:returns: The goal, in percent; ``100``, if the report states none.
		"""
		return self._goal

	@readonly
	def Comment(self) -> str:
		"""
		Read-only property to access the comment (:attr:`_comment`).

		:returns: The comment; empty, if the report states none.
		"""
		return self._comment

	@readonly
	def AtLeast(self) -> int:
		"""
		Read-only property to access how often a bin must be hit to be covered (:attr:`_atLeast`).

		:returns: The count; ``1``, if the report states none.
		"""
		return self._atLeast


@export
class CoverpointOptions(Options):
	"""
	The ``<options>`` of a coverpoint.
	"""

	_detectOverlap: bool  #: Whether to warn about overlapping bins.
	_autoBinMax:    int   #: Maximum number of bins created automatically.

	def __init__(
		self,
		weight: int = 1,
		goal: int = 100,
		comment: str = "",
		atLeast: int = 1,
		detectOverlap: bool = False,
		autoBinMax: int = 64
	) -> None:
		"""
		Initialize the options of a coverpoint.

		:param weight:        Optional, weight in computing the coverage. Default: ``1``.
		:param goal:          Optional, coverage goal, in percent. Default: ``100``.
		:param comment:       Optional, a comment. Default: ``""``.
		:param atLeast:       Optional, how often a bin must be hit to be covered. Default: ``1``.
		:param detectOverlap: Optional, whether to warn about overlapping bins. Default: ``False``.
		:param autoBinMax:    Optional, maximum number of bins created automatically. Default: ``64``.
		:raises ValueError:   If parameter ``weight``, ``goal`` or ``atLeast`` is ``None``.
		:raises TypeError:    If parameter ``weight``, ``goal`` or ``atLeast`` isn't of type :class:`int`.
		:raises ValueError:   If parameter ``weight``, ``goal`` or ``atLeast`` is negative.
		:raises ValueError:   If parameter ``comment`` is ``None``.
		:raises TypeError:    If parameter ``comment`` isn't of type :class:`str`.
		:raises ValueError:   If parameter ``detectOverlap`` is ``None``.
		:raises TypeError:    If parameter ``detectOverlap`` isn't of type :class:`bool`.
		:raises ValueError:   If parameter ``autoBinMax`` is ``None``.
		:raises TypeError:    If parameter ``autoBinMax`` isn't of type :class:`int`.
		:raises ValueError:   If parameter ``autoBinMax`` is negative.
		"""
		super().__init__(weight, goal, comment, atLeast)

		if detectOverlap is None:
			raise ValueError(f"Parameter 'detectOverlap' is None.")
		elif not isinstance(detectOverlap, bool):
			ex = TypeError(f"Parameter 'detectOverlap' is not of type 'bool'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(detectOverlap)}'.")
			raise ex

		if autoBinMax is None:
			raise ValueError(f"Parameter 'autoBinMax' is None.")
		elif not isinstance(autoBinMax, int) or isinstance(autoBinMax, bool):
			ex = TypeError(f"Parameter 'autoBinMax' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(autoBinMax)}'.")
			raise ex
		elif autoBinMax < 0:
			ex = ValueError(f"Parameter 'autoBinMax' is negative.")
			ex.add_note(f"Got value '{autoBinMax}'.")
			raise ex

		self._detectOverlap = detectOverlap
		self._autoBinMax =    autoBinMax

	@classmethod
	def Parse(cls, element: _Element) -> Self:
		"""
		Parse the options of a coverpoint from its ``<options>`` element; an option it doesn't state has its default.

		:param element: The ``<options>`` element.
		:returns:       The options.
		"""
		attributes = element.attrib
		return cls(
			int(attributes.get("weight", "1")),
			int(attributes.get("goal", "100")),
			attributes.get("comment", ""),
			int(attributes.get("at_least", "1")),
			Base._ParseBoolean(attributes.get("detect_overlap", "false")),
			int(attributes.get("auto_bin_max", "64"))
		)

	@readonly
	def DetectOverlap(self) -> bool:
		"""
		Read-only property to access whether to warn about overlapping bins (:attr:`_detectOverlap`).

		:returns: ``True``, if overlapping bins are reported.
		"""
		return self._detectOverlap

	@readonly
	def AutoBinMax(self) -> int:
		"""
		Read-only property to access the maximum number of bins created automatically (:attr:`_autoBinMax`).

		:returns: The maximum; ``64``, if the report states none.
		"""
		return self._autoBinMax


@export
class CrossOptions(Options):
	"""
	The ``<options>`` of a cross.
	"""

	_crossNumPrintMissing: int  #: Number of uncovered cross bins to save and report.

	def __init__(
		self,
		weight: int = 1,
		goal: int = 100,
		comment: str = "",
		atLeast: int = 1,
		crossNumPrintMissing: int = 0
	) -> None:
		"""
		Initialize the options of a cross.

		:param weight:               Optional, weight in computing the coverage. Default: ``1``.
		:param goal:                 Optional, coverage goal, in percent. Default: ``100``.
		:param comment:              Optional, a comment. Default: ``""``.
		:param atLeast:              Optional, how often a bin must be hit to be covered. Default: ``1``.
		:param crossNumPrintMissing: Optional, number of uncovered cross bins to save and report. Default: ``0``.
		:raises ValueError:          If parameter ``weight``, ``goal`` or ``atLeast`` is ``None``.
		:raises TypeError:           If parameter ``weight``, ``goal`` or ``atLeast`` isn't of type :class:`int`.
		:raises ValueError:          If parameter ``weight``, ``goal`` or ``atLeast`` is negative.
		:raises ValueError:          If parameter ``comment`` is ``None``.
		:raises TypeError:           If parameter ``comment`` isn't of type :class:`str`.
		:raises ValueError:          If parameter ``crossNumPrintMissing`` is ``None``.
		:raises TypeError:           If parameter ``crossNumPrintMissing`` isn't of type :class:`int`.
		:raises ValueError:          If parameter ``crossNumPrintMissing`` is negative.
		"""
		super().__init__(weight, goal, comment, atLeast)

		if crossNumPrintMissing is None:
			raise ValueError(f"Parameter 'crossNumPrintMissing' is None.")
		elif not isinstance(crossNumPrintMissing, int) or isinstance(crossNumPrintMissing, bool):
			ex = TypeError(f"Parameter 'crossNumPrintMissing' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(crossNumPrintMissing)}'.")
			raise ex
		elif crossNumPrintMissing < 0:
			ex = ValueError(f"Parameter 'crossNumPrintMissing' is negative.")
			ex.add_note(f"Got value '{crossNumPrintMissing}'.")
			raise ex

		self._crossNumPrintMissing = crossNumPrintMissing

	@classmethod
	def Parse(cls, element: _Element) -> Self:
		"""
		Parse the options of a cross from its ``<options>`` element; an option it doesn't state has its default.

		:param element: The ``<options>`` element.
		:returns:       The options.
		"""
		attributes = element.attrib
		return cls(
			int(attributes.get("weight", "1")),
			int(attributes.get("goal", "100")),
			attributes.get("comment", ""),
			int(attributes.get("at_least", "1")),
			int(attributes.get("cross_num_print_missing", "0"))
		)

	@readonly
	def CrossNumPrintMissing(self) -> int:
		"""
		Read-only property to access the number of uncovered cross bins to save and report (:attr:`_crossNumPrintMissing`).

		:returns: The number; ``0``, if the report states none.
		"""
		return self._crossNumPrintMissing


@export
class CovergroupOptions(CoverpointOptions):
	"""
	The ``<options>`` of a covergroup instance.
	"""

	_crossNumPrintMissing: int   #: Number of uncovered cross bins to save and report.
	_perInstance:          bool  #: Whether the instance's coverage is kept on its own.
	_mergeInstances:       bool  #: Whether the covergroup's coverage merges its instances.

	def __init__(
		self,
		weight: int = 1,
		goal: int = 100,
		comment: str = "",
		atLeast: int = 1,
		detectOverlap: bool = False,
		autoBinMax: int = 64,
		crossNumPrintMissing: int = 0,
		perInstance: bool = False,
		mergeInstances: bool = False
	) -> None:
		"""
		Initialize the options of a covergroup instance.

		:param weight:               Optional, weight in computing the coverage. Default: ``1``.
		:param goal:                 Optional, coverage goal, in percent. Default: ``100``.
		:param comment:              Optional, a comment. Default: ``""``.
		:param atLeast:              Optional, how often a bin must be hit to be covered. Default: ``1``.
		:param detectOverlap:        Optional, whether to warn about overlapping bins. Default: ``False``.
		:param autoBinMax:           Optional, maximum number of bins created automatically. Default: ``64``.
		:param crossNumPrintMissing: Optional, number of uncovered cross bins to save and report. Default: ``0``.
		:param perInstance:          Optional, whether the instance's coverage is kept on its own. Default: ``False``.
		:param mergeInstances:       Optional, whether the covergroup's coverage merges its instances. Default:
		                             ``False``.
		:raises ValueError:          If parameter ``weight``, ``goal`` or ``atLeast`` is ``None``.
		:raises TypeError:           If parameter ``weight``, ``goal`` or ``atLeast`` isn't of type :class:`int`.
		:raises ValueError:          If parameter ``weight``, ``goal`` or ``atLeast`` is negative.
		:raises ValueError:          If parameter ``comment`` is ``None``.
		:raises TypeError:           If parameter ``comment`` isn't of type :class:`str`.
		:raises ValueError:          If parameter ``detectOverlap`` is ``None``.
		:raises TypeError:           If parameter ``detectOverlap`` isn't of type :class:`bool`.
		:raises ValueError:          If parameter ``autoBinMax`` is ``None``.
		:raises TypeError:           If parameter ``autoBinMax`` isn't of type :class:`int`.
		:raises ValueError:          If parameter ``autoBinMax`` is negative.
		:raises ValueError:          If parameter ``crossNumPrintMissing`` is ``None``.
		:raises TypeError:           If parameter ``crossNumPrintMissing`` isn't of type :class:`int`.
		:raises ValueError:          If parameter ``crossNumPrintMissing`` is negative.
		:raises ValueError:          If parameter ``perInstance`` or ``mergeInstances`` is ``None``.
		:raises TypeError:           If parameter ``perInstance`` or ``mergeInstances`` isn't of type :class:`bool`.
		"""
		super().__init__(weight, goal, comment, atLeast, detectOverlap, autoBinMax)

		if crossNumPrintMissing is None:
			raise ValueError(f"Parameter 'crossNumPrintMissing' is None.")
		elif not isinstance(crossNumPrintMissing, int) or isinstance(crossNumPrintMissing, bool):
			ex = TypeError(f"Parameter 'crossNumPrintMissing' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(crossNumPrintMissing)}'.")
			raise ex
		elif crossNumPrintMissing < 0:
			ex = ValueError(f"Parameter 'crossNumPrintMissing' is negative.")
			ex.add_note(f"Got value '{crossNumPrintMissing}'.")
			raise ex

		if perInstance is None:
			raise ValueError(f"Parameter 'perInstance' is None.")
		elif not isinstance(perInstance, bool):
			ex = TypeError(f"Parameter 'perInstance' is not of type 'bool'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(perInstance)}'.")
			raise ex

		if mergeInstances is None:
			raise ValueError(f"Parameter 'mergeInstances' is None.")
		elif not isinstance(mergeInstances, bool):
			ex = TypeError(f"Parameter 'mergeInstances' is not of type 'bool'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(mergeInstances)}'.")
			raise ex

		self._crossNumPrintMissing = crossNumPrintMissing
		self._perInstance =          perInstance
		self._mergeInstances =       mergeInstances

	@classmethod
	def Parse(cls, element: _Element) -> Self:
		"""
		Parse the options of a covergroup instance from its ``<options>`` element; an option it doesn't state has its
		default.

		:param element: The ``<options>`` element.
		:returns:       The options.
		"""
		attributes = element.attrib
		return cls(
			int(attributes.get("weight", "1")),
			int(attributes.get("goal", "100")),
			attributes.get("comment", ""),
			int(attributes.get("at_least", "1")),
			Base._ParseBoolean(attributes.get("detect_overlap", "false")),
			int(attributes.get("auto_bin_max", "64")),
			int(attributes.get("cross_num_print_missing", "0")),
			Base._ParseBoolean(attributes.get("per_instance", "false")),
			Base._ParseBoolean(attributes.get("merge_instances", "false"))
		)

	@readonly
	def CrossNumPrintMissing(self) -> int:
		"""
		Read-only property to access the number of uncovered cross bins to save and report (:attr:`_crossNumPrintMissing`).

		:returns: The number; ``0``, if the report states none.
		"""
		return self._crossNumPrintMissing

	@readonly
	def PerInstance(self) -> bool:
		"""
		Read-only property to access whether the instance's coverage is kept on its own (:attr:`_perInstance`).

		:returns: ``True``, if kept per instance.
		"""
		return self._perInstance

	@readonly
	def MergeInstances(self) -> bool:
		"""
		Read-only property to access whether the covergroup's coverage merges its instances (:attr:`_mergeInstances`).

		:returns: ``True``, if the instances are merged; otherwise, it is their weighted average.
		"""
		return self._mergeInstances
