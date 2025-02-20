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
"""Package installer for 'Various report abstract data models and report format converters'."""
from pathlib             import Path

from setuptools          import setup
from pyTooling.Packaging import DescribePythonPackageHostedOnGitHub, DEFAULT_CLASSIFIERS

gitHubNamespace =        "pyEDAA"
packageName =            "pyEDAA.Reports"
packageDirectory =       packageName.replace(".", "/")
packageInformationFile = Path(f"{packageDirectory}/__init__.py")

setup(**DescribePythonPackageHostedOnGitHub(
	packageName=packageName,
	description="Various report abstract data models and report format converters.",
	gitHubNamespace=gitHubNamespace,
	unittestRequirementsFile=Path("tests/requirements.txt"),
	developmentStatus="pre-alpha",
	classifiers=list(DEFAULT_CLASSIFIERS) + [
		"Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)",
	],
	sourceFileWithVersion=packageInformationFile,
	dataFiles={
		packageName: [
			f"py.typed",
			f"Resources/*.xsd"
		]
	},
	consoleScripts={
		"pyedaa-reports": "pyEDAA.Reports.CLI:main"
	}
))
