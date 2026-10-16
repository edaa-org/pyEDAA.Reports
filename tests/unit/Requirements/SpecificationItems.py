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
"""Unit tests of the requirements model: specification items, and their N:M relation to requirements."""
from pyEDAA.Reports.Requirements import Layer, Requirement, RequirementSpecification, RequirementsError
from pyEDAA.Reports.Requirements import SpecificationItem
from pyTooling.Testing           import Testcase

from .                           import BuildSpecification, FUNCTIONAL, VERSION


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


class SpecificationItems(Testcase):
	def test_SpecificationItem(self) -> None:
		specification = BuildSpecification()
		requirements =  specification.Requirements
		design =        SpecificationItem(
			"DES-1",
			"Interrupt controller",
			requirements=[requirements["FW-1"], requirements["SW-1"]],
			layer=specification.Layers["fw"],
			parent=specification
		)
		detail = SpecificationItem("DES-1.1", "Register map", parent=design)

		self.assertEqual({"DES-1": design, "DES-1.1": detail}, specification.SpecificationItems)
		self.assertEqual(["FW-1", "SW-1"], list(design.Requirements))
		self.assertEqual({"DES-1": design}, requirements["FW-1"].SpecificationItems)
		self.assertEqual({}, requirements["EL-1"].SpecificationItems)
		self.assertEqual([design], list(specification.Layers["fw"].IterateSpecificationItems()))
		self.assertEqual([requirements["FW-1"]], list(specification.Layers["fw"].IterateRequirements()))
		self.assertEqual([detail], list(specification.IterateSpecificationItems(lambda item: item.Parent is design)))
		self.assertEqual(["DES-1.1"], [item.ID for item in design.IterateDescendants()])
		self.assertEqual([design, detail], list(specification.IterateSpecificationItems()))
		self.assertEqual([], list(Layer("fw", "FPGA firmware").IterateSpecificationItems()))
		self.assertIsNone(SpecificationItem("DES-2", "Interrupt driver").Root)

	def test_AddRequirement(self) -> None:
		"""A requirement is specified by any number of specification items, and the other way round."""
		specification = BuildSpecification()
		requirements =  specification.Requirements
		hardware =      SpecificationItem("DES-1", "Interrupt controller", parent=specification)
		driver =        SpecificationItem("DES-2", "Interrupt driver", parent=specification)
		for item in (hardware, driver):
			item.AddRequirement(requirements["SW-1"])

		hardware.AddRequirement(requirements["FW-1"])

		self.assertEqual(["SW-1", "FW-1"], list(hardware.Requirements))
		self.assertEqual(["DES-1", "DES-2"], list(requirements["SW-1"].SpecificationItems))

		with self.assertRaises(RequirementsError) as context:
			hardware.AddRequirement(requirements["FW-1"])

		self.assertEqual("Specification item 'DES-1' specifies requirement 'FW-1' already.", str(context.exception))

	def test_Duplicate(self) -> None:
		"""Requirements and specification items have IDs of their own."""
		specification = BuildSpecification()
		SpecificationItem("EL-1", "Interrupt pin", parent=specification)

		with self.assertRaises(RequirementsError) as context:
			SpecificationItem("EL-1", "Interrupt pin", parent=specification)

		self.assertEqual("SpecificationItem 'EL-1' already exists in the specification.", str(context.exception))

	def test_ParameterChecks(self) -> None:
		specification = BuildSpecification()
		system =        RequirementSpecification(VERSION, "System")
		other =         Requirement("REQ-1", "Title", FUNCTIONAL, parent=system)
		for requirements, exception, message, notes in (
			(1,                                        TypeError,
				"Parameter 'requirements' is not iterable.", ["Got type 'int'."]),
			(specification.Requirements["EL-1"],       TypeError,
				"Parameter 'requirements' is a single element, not an iterable of elements.",
				["Got type 'pyEDAA.Reports.Requirements.Requirement'."]),
			(["EL-1"],                                 TypeError,
				"Parameter 'requirements' contains an element not of type 'Requirement'.", ["Got type 'str'."]),
			([other],                                  ValueError,
				"Parameter 'requirements' contains a requirement not part of the item's specification.",
				["Got requirement 'REQ-1'."]),
			([specification.Requirements["EL-1"]] * 2, ValueError,
				"Parameter 'requirements' contains a requirement twice.", ["Got requirement 'EL-1'."]),
		):
			with self.subTest(message=message):
				with self.assertRaises(exception) as context:
					_ = SpecificationItem("DES-1", "Title", requirements=requirements, parent=specification)

				self.assertEqual(message, str(context.exception))
				self.assertEqual(notes, context.exception.__notes__)

		self.assertEqual({}, specification.SpecificationItems)
		self.assertEqual({}, specification.Requirements["EL-1"].SpecificationItems)

		design = SpecificationItem("DES-1", "Title", parent=specification)
		for requirement, exception, message in (
			(None,   ValueError, "Parameter 'requirement' is None."),
			("EL-1", TypeError,  "Parameter 'requirement' is not of type 'Requirement'."),
			(other,  ValueError, "Parameter 'requirement' isn't part of the item's specification."),
		):
			with self.subTest(message=message):
				with self.assertRaises(exception) as context:
					design.AddRequirement(requirement)

				self.assertEqual(message, str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = SpecificationItem("DES-2", "Title", parent=specification.Requirements["EL-1"])

		self.assertEqual(
			"Parameter 'parent' is not of type 'SpecificationItem' or 'RequirementSpecification'.",
			str(context.exception)
		)
