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
#
"""
The summaries of LLVM's code coverage export: the counters llvm-cov computed for a file or the whole report.

A summary's constructor takes typed values; its classmethod ``Parse`` reads the summary's JSON object.
"""
from __future__            import annotations

from typing                import Any, Optional as Nullable, Self

from pyTooling.Common      import getFullyQualifiedName
from pyTooling.Decorators  import export, readonly
from pyTooling.MetaClasses import ExtendedType


@export
class Counters(metaclass=ExtendedType, slots=True):
	"""
	The counters of one kind of a summary: how many there are, and how many are covered.

	A summary counts lines, functions, regions, branches and MC/DC conditions.
	"""

	_count:      int            #: Number of lines, functions, regions, branches or MC/DC conditions.
	_covered:    int            #: Number of the covered ones.
	_notCovered: Nullable[int]  #: Number of the uncovered ones, if stated.
	_percent:    float          #: The coverage in percent.

	def __init__(self, count: int, covered: int, percent: float, notCovered: Nullable[int] = None) -> None:
		"""
		Initialize counters.

		:param count:       Number of lines, functions, regions, branches or MC/DC conditions.
		:param covered:     Number of the covered ones.
		:param percent:     The coverage in percent.
		:param notCovered:  Optional, number of the uncovered ones. Default: ``None``.
		:raises ValueError: If parameter ``count`` or ``covered`` is ``None``.
		:raises TypeError:  If parameter ``count`` or ``covered`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``count`` or ``covered`` is negative.
		:raises TypeError:  If parameter ``notCovered`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``notCovered`` is negative.
		:raises ValueError: If parameter ``percent`` is ``None``.
		:raises TypeError:  If parameter ``percent`` isn't of type :class:`float` or :class:`int`.
		:raises ValueError: If parameter ``percent`` is out of range 0..100.
		"""
		for name, value in (("count", count), ("covered", covered)):
			if value is None:
				raise ValueError(f"Parameter '{name}' is None.")
			elif not isinstance(value, int):
				ex = TypeError(f"Parameter '{name}' is not of type 'int'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
				raise ex
			elif value < 0:
				ex = ValueError(f"Parameter '{name}' is negative.")
				ex.add_note(f"Got value '{value}'.")
				raise ex

		if notCovered is not None:
			if not isinstance(notCovered, int):
				ex = TypeError(f"Parameter 'notCovered' is not of type 'int'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(notCovered)}'.")
				raise ex
			elif notCovered < 0:
				ex = ValueError(f"Parameter 'notCovered' is negative.")
				ex.add_note(f"Got value '{notCovered}'.")
				raise ex

		if percent is None:
			raise ValueError(f"Parameter 'percent' is None.")
		elif not isinstance(percent, (float, int)):
			ex = TypeError(f"Parameter 'percent' is not of type 'float'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(percent)}'.")
			raise ex
		elif not 0 <= percent <= 100:
			ex = ValueError(f"Parameter 'percent' is out of range 0..100.")
			ex.add_note(f"Got value '{percent}'.")
			raise ex

		self._count =      count
		self._covered =    covered
		self._notCovered = notCovered
		self._percent =    percent

	@classmethod
	def Parse(cls, counters: dict[str, Any]) -> Self:
		"""
		Parse counters from their JSON object.

		:param counters: The JSON object of the counters.
		:returns:        The counters.
		"""
		return cls(counters["count"], counters["covered"], counters["percent"], counters.get("notcovered"))

	@readonly
	def Count(self) -> int:
		"""
		Read-only property to access the number of lines, functions, regions, branches or MC/DC conditions (:attr:`_count`).

		:returns: The number.
		"""
		return self._count

	@readonly
	def Covered(self) -> int:
		"""
		Read-only property to access the number of covered ones (:attr:`_covered`).

		:returns: The number.
		"""
		return self._covered

	@readonly
	def NotCovered(self) -> Nullable[int]:
		"""
		Read-only property to access the number of uncovered ones (:attr:`_notCovered`).

		:returns: The number, or ``None`` for lines, functions and instantiations, which don't state it.
		"""
		return self._notCovered

	@readonly
	def Percent(self) -> float:
		"""
		Read-only property to access the coverage (:attr:`_percent`).

		:returns: The coverage in percent.
		"""
		return self._percent


@export
class Summary(metaclass=ExtendedType, slots=True):
	"""
	A ``summary``: the counters llvm-cov computed for a file or the whole report.

	llvm-cov counts a file's lines, regions and branches per function, and merges a function's instantiations by taking
	the best one.
	"""

	_lines:          Counters            #: The counters of lines.
	_functions:      Counters            #: The counters of functions, a function's instantiations counted once.
	_instantiations: Counters            #: The counters of function instantiations.
	_regions:        Counters            #: The counters of code regions.
	_branches:       Nullable[Counters]  #: The counters of branch outcomes, if stated.
	_mcdc:           Nullable[Counters]  #: The counters of MC/DC conditions, if stated.

	def __init__(
		self,
		lines: Counters,
		functions: Counters,
		instantiations: Counters,
		regions: Counters,
		branches: Nullable[Counters] = None,
		mcdc: Nullable[Counters] = None
	) -> None:
		"""
		Initialize a summary.

		:param lines:          The counters of lines.
		:param functions:      The counters of functions, a function's instantiations counted once.
		:param instantiations: The counters of function instantiations.
		:param regions:        The counters of code regions.
		:param branches:       Optional, the counters of branch outcomes. Default: ``None``.
		:param mcdc:           Optional, the counters of MC/DC conditions. Default: ``None``.
		:raises ValueError:    If parameter ``lines``, ``functions``, ``instantiations`` or ``regions`` is ``None``.
		:raises TypeError:     If parameter ``lines``, ``functions``, ``instantiations``, ``regions``, ``branches`` or
		                       ``mcdc`` isn't of type :class:`Counters`.
		"""
		for name, counters in (
			("lines", lines), ("functions", functions), ("instantiations", instantiations), ("regions", regions)
		):
			if counters is None:
				raise ValueError(f"Parameter '{name}' is None.")
			elif not isinstance(counters, Counters):
				ex = TypeError(f"Parameter '{name}' is not of type 'Counters'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(counters)}'.")
				raise ex

		for name, counters in (("branches", branches), ("mcdc", mcdc)):
			if counters is not None and not isinstance(counters, Counters):
				ex = TypeError(f"Parameter '{name}' is not of type 'Counters'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(counters)}'.")
				raise ex

		self._lines =          lines
		self._functions =      functions
		self._instantiations = instantiations
		self._regions =        regions
		self._branches =       branches
		self._mcdc =           mcdc

	@classmethod
	def Parse(cls, summary: dict[str, Any]) -> Self:
		"""
		Parse a summary from its JSON object.

		:param summary: The JSON object ``summary`` or ``totals``.
		:returns:       The summary.
		"""
		return cls(
			Counters.Parse(summary["lines"]),
			Counters.Parse(summary["functions"]),
			Counters.Parse(summary["instantiations"]),
			Counters.Parse(summary["regions"]),
			Counters.Parse(summary["branches"]) if "branches" in summary else None,
			Counters.Parse(summary["mcdc"]) if "mcdc" in summary else None
		)

	@readonly
	def Lines(self) -> Counters:
		"""
		Read-only property to access the counters of lines (:attr:`_lines`).

		:returns: The counters.
		"""
		return self._lines

	@readonly
	def Functions(self) -> Counters:
		"""
		Read-only property to access the counters of functions, a function's instantiations counted once
		(:attr:`_functions`).

		:returns: The counters.
		"""
		return self._functions

	@readonly
	def Instantiations(self) -> Counters:
		"""
		Read-only property to access the counters of function instantiations (:attr:`_instantiations`).

		:returns: The counters.
		"""
		return self._instantiations

	@readonly
	def Regions(self) -> Counters:
		"""
		Read-only property to access the counters of code regions (:attr:`_regions`).

		:returns: The counters.
		"""
		return self._regions

	@readonly
	def Branches(self) -> Nullable[Counters]:
		"""
		Read-only property to access the counters of branch outcomes - two per branch region - (:attr:`_branches`).

		:returns: The counters, or ``None`` before LLVM 12.
		"""
		return self._branches

	@readonly
	def MCDC(self) -> Nullable[Counters]:
		"""
		Read-only property to access the counters of MC/DC conditions (:attr:`_mcdc`).

		:returns: The counters, or ``None`` before LLVM 18.
		"""
		return self._mcdc
