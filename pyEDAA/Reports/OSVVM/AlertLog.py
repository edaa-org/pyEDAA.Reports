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
# Copyright 2021-2024 Electronic Design Automation Abstraction (EDA²)                                                  #
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
"""A data model for OSVVM's AlertLog YAML file format."""
from datetime import timedelta
from enum     import Enum, auto
from pathlib  import Path
from time     import perf_counter_ns
from typing   import Optional as Nullable, Dict, Iterator

from ruamel.yaml           import YAML
from pyTooling.Decorators  import readonly, export
from pyTooling.MetaClasses import ExtendedType
from pyTooling.Tree        import Node

from pyEDAA.Reports.OSVVM  import OSVVMException


@export
class AlertLogStatus(Enum):
	Unknown = auto()
	Passed = auto()
	Failed = auto()

	__MAPPINGS__ = {
		"passed": Passed,
		"failed": Failed
	}

	@classmethod
	def Parse(self, name: str) -> "AlertLogStatus":
		try:
			return self.__MAPPINGS__[name.lower()]
		except KeyError as ex:
			raise OSVVMException(f"Unknown AlertLog status '{name}'.") from ex

	def __bool__(self) -> bool:
		return self is self.Passed


@export
class Base(metaclass=ExtendedType, slots=True):
	pass


@export
class LoggingGroup(Base):
	_parent: "LoggingGroup"
	_name: str
	_children: Dict[str, "LoggingGroup"]
	_afirmations: int

	def __init__(self, name: str, afirmations: int = 0, parent: Nullable["LoggingGroup"] = None) -> None:
		self._parent = parent
		self._name = name
		self._children = {}
		self._afirmations = afirmations

	@readonly
	def Parent(self) -> Nullable["LoggingGroup"]:
		return self._parent

	@readonly
	def Name(self) -> str:
		return self._name

	@readonly
	def Affirmations(self) -> int:
		return self._afirmations

	def __iter__(self) -> Iterator["LoggingGroup"]:
		return self._chilren.values()

	def __getitem__(self, name: str) -> "LoggingGroup":
		return self._chilren[name]

	def ToTree(self) -> Node:
		node = Node(value=self._name, children=(child.ToTree() for child in self._children.values()))

		return node


@export
class Document(Base):
	_path: Path
	_yamlDocument: Nullable[YAML]

	_name: str
	_status: AlertLogStatus
	_children: Dict[str, LoggingGroup]

	_analysisDuration: float  #: TODO: replace by Timer; should be timedelta?
	_modelConversion:  float  #: TODO: replace by Timer; should be timedelta?

	def __init__(self, filename: Path, parse: bool = False) -> None:
		self._path = filename
		self._yamlDocument = None

		self._name = None
		self._status = AlertLogStatus.Unknown
		self._children = {}

		self._analysisDuration = -1.0
		self._modelConversion = -1.0

		if parse:
			self.Read()
			self.Parse()

	@property
	def Path(self) -> Path:
		return self._path

	@readonly
	def AnalysisDuration(self) -> timedelta:
		return timedelta(seconds=self._analysisDuration)

	@readonly
	def ModelConversionDuration(self) -> timedelta:
		return timedelta(seconds=self._modelConversion)

	def Read(self) -> None:
		if not self._path.exists():
			raise OSVVMException(f"OSVVM AlertLog YAML file '{self._path}' does not exist.") \
				from FileNotFoundError(f"File '{self._path}' not found.")

		startAnalysis = perf_counter_ns()
		try:
			yamlReader = YAML()
			self._yamlDocument = yamlReader.load(self._path)
		except Exception as ex:
			raise OSVVMException(f"Couldn't open '{self._path}'.") from ex

		endAnalysis = perf_counter_ns()
		self._analysisDuration = (endAnalysis - startAnalysis) / 1e9

	def Parse(self) -> None:
		if self._yamlDocument is None:
			ex = OSVVMException(f"OSVVM AlertLog YAML file '{self._path}' needs to be read and analyzed by a YAML parser.")
			ex.add_note(f"Call 'Document.Read()' or create document using 'Document(path, parse=True)'.")
			raise ex

		startConversion = perf_counter_ns()

		self._name = self._yamlDocument["Name"]
		self._status = AlertLogStatus.Parse(self._yamlDocument["Status"])
		for child in self._yamlDocument["Children"]:
			group  = self._ParseGroup(child, self)
			self._children[group._name] = group

		# self.Aggregate()
		endConversation = perf_counter_ns()
		self._modelConversion = (endConversation - startConversion) / 1e9

	def _ParseGroup(self, child, parent: Base) -> LoggingGroup:
		group = LoggingGroup(
			child["Name"],
			0,
			parent
		)
		for ch in child["Children"]:
			grp  = self._ParseGroup(ch, self)
			group._children[grp._name] = grp

		return group

	def ToTree(self) -> Node:
		root = Node(
			value=self._name,
			children=(child.ToTree() for child in self._children.values())
		)

		return root
