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
"""
Various report abstract data models and report format converters.
"""
__author__ =    "Patrick Lehmann"
__email__ =     "Paebbels@gmail.com"
__copyright__ = "2021-2025, Electronic Design Automation Abstraction (EDA²)"
__license__ =   "Apache License, Version 2.0"
__version__ =   "0.16.0"
__keywords__ =  ["Reports", "Abstract Model", "Data Model", "Unit Testing", "Testcase", "Testsuite", "OSVVM", "YAML", "XML"]

from enum                 import Enum
from sys                  import version_info
from typing               import List

from pyTooling.Decorators import export


@export
class ReportException(Exception):
	# WORKAROUND: for Python <3.11
	# Implementing a dummy method for Python versions before
	if version_info < (3, 11):  # pragma: no cover
		__notes__: List[str]

		def add_note(self, message: str) -> None:
			try:
				self.__notes__.append(message)
			except AttributeError:
				self.__notes__ = [message]


@export
class Severity(Enum):
	Unknown = 0
	Debug = 5
	Verbose = 10
	Normal = 20
	Info = 25
	Warning = 50
	CriticalWarning = 55
	Error = 60
	Fatal = 70
