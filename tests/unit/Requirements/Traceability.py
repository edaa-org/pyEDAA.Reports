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
"""Unit tests of the requirements model: following links transitively."""
from pyEDAA.Reports.Requirements import Link, LinkKind, RequirementSpecification
from pyTooling.Testing           import Testcase

from .                           import BuildSpecification


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


def BuildChain() -> RequirementSpecification:
	"""
	Build the shared specification with links: ``SW-1`` is the counterpart of ``FW-1``, which is the counterpart of
	``EL-1``, and ``SW-1`` depends on ``EL-1.1``.

	:returns: The specification.
	"""
	specification = BuildSpecification()
	requirements =  specification.Requirements
	Link(requirements["SW-1"], requirements["FW-1"], LinkKind.CounterpartOf)
	Link(requirements["SW-1"], requirements["EL-1.1"], LinkKind.DependsOn)
	Link(requirements["FW-1"], requirements["EL-1"], LinkKind.CounterpartOf)

	return specification


def IsCounterpart(link: Link) -> bool:
	"""
	Select counterpart links.

	:param link: The link.
	:returns:    ``True``, if the link states a counterpart.
	"""
	return link.Kind is LinkKind.CounterpartOf


class Trace(Testcase):
	def test_IterateTrace(self) -> None:
		"""A software requirement traces through the firmware to the electrical layer."""
		requirements = BuildChain().Requirements

		self.assertEqual(["FW-1", "EL-1", "EL-1.1"], [item.ID for item in requirements["SW-1"].IterateTrace()])
		self.assertEqual(["FW-1", "EL-1"], [item.ID for item in requirements["SW-1"].IterateTrace(IsCounterpart)])
		self.assertEqual([], list(requirements["EL-1"].IterateTrace()))

	def test_IterateInboundTrace(self) -> None:
		"""An electrical requirement has its counterparts in the firmware and the software."""
		requirements = BuildChain().Requirements

		self.assertEqual(["FW-1", "SW-1"], [item.ID for item in requirements["EL-1"].IterateInboundTrace(IsCounterpart)])
		self.assertEqual(["SW-1"], [item.ID for item in requirements["EL-1.1"].IterateInboundTrace()])
		self.assertEqual([], list(requirements["SW-1"].IterateInboundTrace()))

	def test_Cycle(self) -> None:
		"""Each item is reached once, even in a cycle of links, and the start item is never reached."""
		specification = BuildChain()
		requirements =  specification.Requirements
		Link(requirements["EL-1"], requirements["SW-1"], LinkKind.ConflictsWith)

		self.assertEqual(["FW-1", "EL-1", "EL-1.1"], [item.ID for item in requirements["SW-1"].IterateTrace()])
		self.assertEqual(["EL-1", "FW-1"], [item.ID for item in requirements["SW-1"].IterateInboundTrace()])
