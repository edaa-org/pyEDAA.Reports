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
from pathlib import Path
from re      import compile as re_compile

from pyTooling.Decorators import export


@export
class Requirement:
	_package: str

	EXTRA_PATTERN = re_compile(r"""^\s*extra\s*==\s*(?P<quote>['"])(?P<key>\w+)(?P=quote)?$""")

	# python_version
	# platform_python_implementation
	# platform_system
	# python_full_version
	# sys_platform

	def __init__(self, rule: str) -> None:
		extraKey = None
		for rulePart in (part.strip() for part in rule.split(";")):
			match = self.EXTRA_PATTERN.match(rulePart)
			if match:
				extraKey = match["key"]
				continue



@export
class RequirementsFile:
	_path: Path

	def __init__(self, path: Path, parse: bool = False) -> None:
		self._path = path

		if parse:
			self.Parse()

	def Parse(self) -> None:
		with self._path.open("r", encoding="utf-8") as file:
			lines = file.readline()

		for line in lines:
			pass
