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
# Copyright 2021-2025 Electronic Design Automation Abstraction (EDA²)                                                  #
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
"""Abstraction of code documentation coverage data model."""
from enum                  import Flag
from typing                import Optional as Nullable

from pyTooling.Decorators  import export
from pyTooling.MetaClasses import ExtendedType

from pyEDAA.Reports        import ReportException


@export
class DocCoverageException(ReportException):
	pass


@export
class CoverageState(Flag):
	Unknown = 0
	Excluded = 1
	Ignored = 2
	Empty = 4
	Covered = 8

	Weak = 16
	Incomplete = 32
	Inherited = 64
	Detailed = 128

	Undocumented = 256
	Documented = 512

	Parameters = 1024
	ReturnValue = 2048
	Exceptions = 8192
	Types = 16384

# unrequiredButDocumented
# wrongly documented


@export
class Base(metaclass=ExtendedType, slots=True):
	_parent: Nullable["Base"]
	_name:   str
	_status: CoverageState

	def __init__(self, name: str, parent: Nullable["Base"] = None):
		if name is None:
			raise ValueError(f"Parameter 'name' must not be None.")

		self._parent = parent
		self._name = name
		self._status = CoverageState.Unknown

	@property
	def Parent(self) -> Nullable["Base"]:
		return self._parent

	@property
	def Name(self) -> str:
		return self._name

	@property
	def Status(self) -> CoverageState:
		return self._status


@export
class _Type(Base):
	pass


@export
class Class(_Type):
	pass


@export
class _Unit(Base):
	pass


@export
class Module(_Unit):
	pass


@export
class Package(_Unit):
	pass
