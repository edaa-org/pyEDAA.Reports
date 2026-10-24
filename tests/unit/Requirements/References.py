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
"""Unit tests of the requirements model: the persons, personas, labels, documents and layers an item refers to."""
from pyTooling.Versioning        import SemanticVersion
from pyTooling.Testing           import Testcase

from pyEDAA.Reports              import Person
from pyEDAA.Reports.Requirements import Document, DuplicatePersonError, ItemState, Label, Layer, \
                                        NotInSameSpecificationError, Obligation, Persona, Requirement, \
                                        RequirementKind, RequirementSpecification


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


VERSION =    SemanticVersion(1, 2, 0)    #: Version of the specifications under test.
FUNCTIONAL = RequirementKind.Functional  #: Kind of the requirements under test.


class References(Testcase):
	def test_None(self) -> None:
		requirement = Requirement("REQ-1", "Supply voltage", FUNCTIONAL)

		self.assertIsNone(requirement.Layer)
		for dictionary in (
			requirement.Authors,
			requirement.Owners,
			requirement.Personas,
			requirement.Labels,
			requirement.Attachments
		):
			self.assertEqual({}, dictionary)

	def test_References(self) -> None:
		"""A requirement refers to persons, personas, labels, documents and a layer of its specification."""
		specification = RequirementSpecification(VERSION, "Board")
		alice =         Person("alice", "Alice", "alice@example.com")
		bob =           Person("bob", "Bob")
		reviewer =      Persona("reviewer", "Reviewer", parent=specification)
		asic =          Label("asic", "ASIC variant", parent=specification)
		datasheet =     Document("ds", "Regulator datasheet", parent=specification)
		electrical =    Layer("el", "Electrical", parent=specification)
		for person in (alice, bob):
			specification.AddPerson(person)

		requirement = Requirement(
			"REQ-1",
			"Supply voltage",
			RequirementKind.Environmental,
			obligation=Obligation.Recommended,
			description="The board runs from 12 V.",
			state=ItemState.Final,
			layer=electrical,
			authors=(alice, bob),
			owners=[bob],
			personas=[reviewer],
			labels=[asic],
			attachments=[datasheet],
			keyValuePairs={"effort": 3},
			parent=specification
		)

		self.assertIs(Obligation.Recommended, requirement.Obligation)
		self.assertEqual("The board runs from 12 V.", requirement.Description)
		self.assertIs(ItemState.Final, requirement.State)
		self.assertIs(electrical, requirement.Layer)
		self.assertEqual(["alice", "bob"], list(requirement.Authors))
		self.assertEqual({"bob": bob}, requirement.Owners)
		self.assertEqual({"reviewer": reviewer}, requirement.Personas)
		self.assertEqual({"asic": asic}, requirement.Labels)
		self.assertEqual({"ds": datasheet}, requirement.Attachments)
		self.assertEqual(3, requirement["effort"])
		self.assertIs(specification, requirement.Root)
		self.assertEqual({"REQ-1": requirement}, specification.Requirements)
		self.assertEqual([requirement], list(electrical.IterateRequirements()))
		self.assertEqual([], list(Layer("sw", "Software").IterateRequirements()))


class ParameterChecks(Testcase):
	def test_References(self) -> None:
		specification = RequirementSpecification(VERSION, "Board")
		other =         RequirementSpecification(VERSION, "System")
		alice =         Person("alice", "Alice")
		bob =           Person("bob", "Bob")
		reviewer =      Persona("reviewer", "Reviewer", parent=specification)
		foreign =       Persona("tester", "Tester", parent=other)
		specification.AddPerson(alice)
		other.AddPerson(bob)
		for keywordArguments, exception, message, notes in (
			({"layer": reviewer},                  TypeError,
				"Parameter 'layer' is not of type 'Layer'.", ["Got type 'pyEDAA.Reports.Requirements.Persona'."]),
			({"layer": Layer("el", "El")},         NotInSameSpecificationError,
				"Parameter 'layer' isn't part of the item's specification.", ["Got layer 'el'."]),
			({"labels": 1},                        TypeError,
				"Parameter 'labels' is not iterable.", ["Got type 'int'."]),
			({"authors": alice},                   TypeError,
				"Parameter 'authors' is a single element, not an iterable of elements.", ["Got type 'pyEDAA.Reports.Person'."]),
			({"personas": reviewer},               TypeError,
				"Parameter 'personas' is a single element, not an iterable of elements.",
				["Got type 'pyEDAA.Reports.Requirements.Persona'."]),
			({"owners": ["alice"]},                TypeError,
				"Parameter 'owners' contains an element not of type 'Person'.", ["Got type 'str'."]),
			({"authors": [reviewer]},              TypeError,
				"Parameter 'authors' contains an element not of type 'Person'.",
				["Got type 'pyEDAA.Reports.Requirements.Persona'."]),
			({"personas": [alice]},                TypeError,
				"Parameter 'personas' contains an element not of type 'Persona'.", ["Got type 'pyEDAA.Reports.Person'."]),
			({"labels": [reviewer]},               TypeError,
				"Parameter 'labels' contains an element not of type 'Label'.",
				["Got type 'pyEDAA.Reports.Requirements.Persona'."]),
			({"attachments": [reviewer]},          TypeError,
				"Parameter 'attachments' contains an element not of type 'Document'.",
				["Got type 'pyEDAA.Reports.Requirements.Persona'."]),
			({"authors": [alice, bob]},            NotInSameSpecificationError,
				"Parameter 'authors' contains an element not part of the item's specification.", ["Got person 'bob'."]),
			({"owners": [Person("alice", "Alice")]}, NotInSameSpecificationError,
				"Parameter 'owners' contains an element not part of the item's specification.", ["Got person 'alice'."]),
			({"personas": [foreign]},              NotInSameSpecificationError,
				"Parameter 'personas' contains an element not part of the item's specification.",
				["Got persona 'tester'."]),
			({"owners": [alice, alice]},           DuplicatePersonError,
				"Parameter 'owners' contains an element twice.", ["Got person 'alice'."]),
		):
			with self.subTest(message=message):
				with self.assertRaises(exception) as context:
					_ = Requirement("REQ-1", "Title", FUNCTIONAL, parent=specification, **keywordArguments)

				self.assertEqual(message, str(context.exception))
				self.assertEqual(notes, context.exception.__notes__)

		self.assertEqual({}, specification.Requirements)

	def test_Standalone(self) -> None:
		"""A requirement without a specification can't refer to anything."""
		specification = RequirementSpecification(VERSION, "Board")
		alice =         Person("alice", "Alice")
		specification.AddPerson(alice)

		with self.assertRaises(NotInSameSpecificationError) as context:
			_ = Requirement("REQ-1", "Title", FUNCTIONAL, authors=[alice])

		self.assertEqual(
			"Parameter 'authors' contains an element not part of the item's specification.",
			str(context.exception)
		)
