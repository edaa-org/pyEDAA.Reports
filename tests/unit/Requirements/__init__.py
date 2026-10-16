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
"""Unit tests of the requirements model, and a specification of three layers they share."""
from datetime                    import datetime, timezone

from pyEDAA.Reports.Requirements import Layer, Requirement, RequirementKind, RequirementSpecification
from pyTooling.Versioning        import SemanticVersion


VERSION =    SemanticVersion(1, 2, 0)                          #: Version of the shared specification.
CREATED =    datetime(2026, 3, 1, 9, 30, tzinfo=timezone.utc)  #: Creation time of the shared specification's items.
FUNCTIONAL = RequirementKind.Functional                        #: Kind of the shared specification's requirements.


def BuildSpecification() -> RequirementSpecification:
	"""
	Build a specification of three layers, a requirement in each, and the electrical requirement's child ``EL-1.1``.

	:returns: The specification.
	"""
	specification = RequirementSpecification(VERSION, "Board")
	for layerID, layerName, requirementID in (
		("el", "Electrical",    "EL-1"),
		("fw", "FPGA firmware", "FW-1"),
		("sw", "Software",      "SW-1"),
	):
		layer = Layer(layerID, layerName, parent=specification)
		Requirement(requirementID, f"{layerName} interrupt", FUNCTIONAL, created=CREATED, layer=layer, parent=specification)

	Requirement("EL-1.1", "Interrupt level", FUNCTIONAL, created=CREATED, parent=specification.Requirements["EL-1"])

	return specification
