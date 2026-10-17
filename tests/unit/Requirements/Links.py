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
from pyEDAA.Reports.Requirements import DuplicateLinkError, Link, LinkKind, NotInSameSpecification, Requirement
from pyEDAA.Reports.Requirements import RequirementSpecification, SpecificationItem
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
			requirements["FW-1"],
			requirements["EL-1"],
			LinkKind.CounterpartOf,
			keyValuePairs={"pin": "IRQ0"}
		)
		software = Link(requirements["SW-1"], requirements["FW-1"], LinkKind.CounterpartOf)
		derived =  Link(requirements["SW-1"], requirements["EL-1"], LinkKind.DerivesFrom)

		self.assertIs(requirements["FW-1"], firmware.Source)
		self.assertIs(requirements["EL-1"], firmware.Destination)
		self.assertIs(LinkKind.CounterpartOf, firmware.Kind)
		self.assertFalse(hasattr(firmware, "Parent"))
		self.assertEqual("IRQ0", firmware["pin"])
		self.assertEqual([software, derived], requirements["SW-1"].OutboundLinks)
		self.assertEqual([firmware, derived], requirements["EL-1"].InboundLinks)
		self.assertEqual([software], requirements["FW-1"].InboundLinks)

	def test_LinkTo(self) -> None:
		"""'LinkTo()' creates an outbound link with everything a link's constructor takes."""
		specification = BuildSpecification()
		requirements =  specification.Requirements
		firmware =      requirements["FW-1"]
		link =          firmware.LinkTo(requirements["EL-1"], LinkKind.CounterpartOf, keyValuePairs={"pin": "IRQ0"})

		self.assertIs(requirements["FW-1"], link.Source)
		self.assertIs(requirements["EL-1"], link.Destination)
		self.assertIs(LinkKind.CounterpartOf, link.Kind)
		self.assertEqual("IRQ0", link["pin"])
		self.assertEqual([link], requirements["FW-1"].OutboundLinks)
		self.assertEqual([link], requirements["EL-1"].InboundLinks)

	def test_LinkFrom(self) -> None:
		"""'LinkFrom()' creates an inbound link: the given item is the link's source."""
		specification = BuildSpecification()
		requirements =  specification.Requirements
		link =          requirements["EL-1"].LinkFrom(requirements["FW-1"], LinkKind.DerivesFrom)

		self.assertIs(requirements["FW-1"], link.Source)
		self.assertIs(requirements["EL-1"], link.Destination)
		self.assertEqual([link], requirements["FW-1"].OutboundLinks)
		self.assertEqual([link], requirements["EL-1"].InboundLinks)

		with self.assertRaises(DuplicateLinkError):
			requirements["EL-1"].LinkFrom(requirements["FW-1"], LinkKind.DerivesFrom)

	def test_LinkFrom_ParameterChecks(self) -> None:
		specification = BuildSpecification()
		requirements =  specification.Requirements
		other =         Requirement("OT-1", "Other", FUNCTIONAL, parent=RequirementSpecification(VERSION))
		for source, exception, message in (
			(None,                 ValueError,             "Parameter 'source' is None."),
			("FW-1",               TypeError,              "Parameter 'source' is not of type 'BaseItem'."),
			(requirements["EL-1"], ValueError,             "Parameter 'destination' is the source."),
			(other,                NotInSameSpecification,
				"Parameter 'destination' isn't part of the source's specification."),
		):
			with self.subTest(message=message):
				with self.assertRaises(exception) as context:
					requirements["EL-1"].LinkFrom(source, LinkKind.RelatesTo)

				self.assertEqual(message, str(context.exception))

	def test_Predicate(self) -> None:
		specification = BuildSpecification()
		requirements =  specification.Requirements
		design =        SpecificationItem("DES-1", "Interrupt controller", parent=specification)
		Link(requirements["SW-1"], requirements["FW-1"], LinkKind.CounterpartOf)
		Link(requirements["SW-1"], requirements["EL-1"], LinkKind.DependsOn)
		Link(design, requirements["SW-1"], LinkKind.RelatesTo)

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
		Link(requirements["FW-1"], requirements["EL-1"], LinkKind.CounterpartOf)
		Link(requirements["FW-1"], requirements["EL-1"], LinkKind.DependsOn)

		with self.assertRaises(DuplicateLinkError) as context:
			Link(requirements["FW-1"], requirements["EL-1"], LinkKind.CounterpartOf)

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
		alone =         Requirement("REQ-2", "Title", FUNCTIONAL)
		for source, destination, kind, exception, message in (
			(None,       electrical, LinkKind.RelatesTo, ValueError,             "Parameter 'source' is None."),
			(system,     electrical, LinkKind.RelatesTo, TypeError,
				"Parameter 'source' is not of type 'BaseItem'."),
			(alone,      electrical, LinkKind.RelatesTo, NotInSameSpecification,
				"Parameter 'source' isn't part of a specification."),
			(firmware,   None,       LinkKind.RelatesTo, ValueError,             "Parameter 'destination' is None."),
			(firmware,   "EL-1",     LinkKind.RelatesTo, TypeError,
				"Parameter 'destination' is not of type 'BaseItem'."),
			(firmware,   firmware,   LinkKind.RelatesTo, ValueError,             "Parameter 'destination' is the source."),
			(firmware,   other,      LinkKind.RelatesTo, NotInSameSpecification,
				"Parameter 'destination' isn't part of the source's specification."),
			(firmware,   electrical, None,               ValueError,             "Parameter 'kind' is None."),
			(firmware,   electrical, "relates-to",       TypeError,
				"Parameter 'kind' is not of type 'LinkKind'."),
		):
			with self.subTest(message=message):
				with self.assertRaises(exception) as context:
					_ = Link(source, destination, kind)

				self.assertEqual(message, str(context.exception))

		self.assertEqual([], requirements["FW-1"].OutboundLinks)
