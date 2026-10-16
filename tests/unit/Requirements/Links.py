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
"""Unit tests of the requirements model: links between items."""
from pyEDAA.Reports.Requirements import Link, LinkKind, Requirement, RequirementSpecification, RequirementsError
from pyEDAA.Reports.Requirements import SpecificationItem
from pyTooling.Testing           import Testcase

from .                           import BuildSpecification, FUNCTIONAL, VERSION


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


class Links(Testcase):
	def test_Counterparts(self) -> None:
		"""An electrical requirement has its counterpart in the firmware, and this one in the software."""
		specification = BuildSpecification()
		requirements =  specification.Requirements
		firmware =      Link(
			requirements["EL-1"],
			LinkKind.CounterpartOf,
			keyValuePairs={"pin": "IRQ0"},
			parent=requirements["FW-1"]
		)
		software = Link(requirements["FW-1"], LinkKind.CounterpartOf, parent=requirements["SW-1"])
		derived =  Link(requirements["EL-1"], LinkKind.DerivesFrom, parent=requirements["SW-1"])

		self.assertIs(requirements["FW-1"], firmware.Source)
		self.assertIs(requirements["FW-1"], firmware.Parent)
		self.assertIs(requirements["EL-1"], firmware.Destination)
		self.assertIs(LinkKind.CounterpartOf, firmware.Kind)
		self.assertIs(specification, firmware.Root)
		self.assertEqual("IRQ0", firmware["pin"])
		self.assertEqual([software, derived], requirements["SW-1"].OutboundLinks)
		self.assertEqual([firmware, derived], requirements["EL-1"].InboundLinks)
		self.assertEqual([software], requirements["FW-1"].InboundLinks)

	def test_Predicate(self) -> None:
		specification = BuildSpecification()
		requirements =  specification.Requirements
		design =        SpecificationItem("DES-1", "Interrupt controller", parent=specification)
		Link(requirements["FW-1"], LinkKind.CounterpartOf, parent=requirements["SW-1"])
		Link(requirements["EL-1"], LinkKind.DependsOn, parent=requirements["SW-1"])
		Link(requirements["SW-1"], LinkKind.RelatesTo, parent=design)

		def isCounterpart(link: Link) -> bool:
			"""Nested function selecting counterpart links."""
			return link.Kind is LinkKind.CounterpartOf

		source = requirements["SW-1"]
		self.assertEqual(["FW-1"], [link.Destination.ID for link in source.IterateOutboundLinks(isCounterpart)])
		self.assertEqual(2, len(list(source.IterateOutboundLinks())))
		self.assertEqual(["DES-1"], [link.Source.ID for link in requirements["SW-1"].IterateInboundLinks()])
		self.assertEqual([], list(requirements["SW-1"].IterateInboundLinks(isCounterpart)))
		self.assertEqual(["SW-1"], [link.Source.ID for link in requirements["FW-1"].IterateInboundLinks(isCounterpart)])

	def test_Duplicate(self) -> None:
		"""A source has one link of a kind to a destination."""
		specification = BuildSpecification()
		requirements =  specification.Requirements
		Link(requirements["EL-1"], LinkKind.CounterpartOf, parent=requirements["FW-1"])
		Link(requirements["EL-1"], LinkKind.DependsOn, parent=requirements["FW-1"])

		with self.assertRaises(RequirementsError) as context:
			Link(requirements["EL-1"], LinkKind.CounterpartOf, parent=requirements["FW-1"])

		self.assertEqual("Requirement 'FW-1' has a 'counterpart-of' link already.", str(context.exception))
		self.assertEqual(["Got destination 'EL-1'."], context.exception.__notes__)
		self.assertEqual(2, len(requirements["EL-1"].InboundLinks))

	def test_ParameterChecks(self) -> None:
		specification = BuildSpecification()
		requirements =  specification.Requirements
		system =        RequirementSpecification(VERSION, "System")
		other =         Requirement("REQ-1", "Title", FUNCTIONAL, parent=system)
		electrical =    requirements["EL-1"]
		firmware =      requirements["FW-1"]
		for destination, kind, parent, exception, message in (
			(electrical, LinkKind.RelatesTo, None,          ValueError,
				"Parameter 'parent' is None."),
			(electrical, LinkKind.RelatesTo, specification, TypeError,
				"Parameter 'parent' is not of type 'BaseItem'."),
			(None,       LinkKind.RelatesTo, firmware,      ValueError,
				"Parameter 'destination' is None."),
			("EL-1",     LinkKind.RelatesTo, firmware,      TypeError,
				"Parameter 'destination' is not of type 'BaseItem'."),
			(firmware,   LinkKind.RelatesTo, firmware,      ValueError,
				"Parameter 'destination' is the link's source."),
			(other,      LinkKind.RelatesTo, firmware,      ValueError,
				"Parameter 'destination' isn't part of the source's specification."),
			(electrical, None,               firmware,      ValueError,
				"Parameter 'kind' is None."),
			(electrical, "relates-to",       firmware,      TypeError,
				"Parameter 'kind' is not of type 'LinkKind'."),
		):
			with self.subTest(message=message):
				with self.assertRaises(exception) as context:
					_ = Link(destination, kind, parent=parent)

				self.assertEqual(message, str(context.exception))

		self.assertEqual([], requirements["FW-1"].OutboundLinks)

		with self.assertRaises(ValueError) as context:
			_ = Link(requirements["EL-1"], LinkKind.RelatesTo, parent=Requirement("REQ-2", "Title", FUNCTIONAL))

		self.assertEqual("Parameter 'destination' isn't part of the source's specification.", str(context.exception))

		link = Link(requirements["EL-1"], LinkKind.RelatesTo, parent=requirements["FW-1"])
		with self.assertRaises(RequirementsError) as context:
			link.Parent = requirements["SW-1"]

		self.assertEqual("Link already has a parent.", str(context.exception))
