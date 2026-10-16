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
"""Unit tests of the requirements model: the specification, and its personas, labels, documents and layers."""
from pyEDAA.Reports.Requirements import Document, Label, Layer, Persona, RequirementSpecification
from pyTooling.Versioning        import SemanticVersion
from pyTooling.Testing           import Testcase


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


VERSION = SemanticVersion(1, 2, 0)  #: Version of the specifications under test.


class Root(Testcase):
	def test_Empty(self) -> None:
		specification = RequirementSpecification("Board", VERSION)

		self.assertEqual("Board", specification.Name)
		self.assertIs(VERSION, specification.Version)
		self.assertIsNone(specification.Parent)
		self.assertIs(specification, specification.Root)
		self.assertEqual({}, specification.Personas)
		self.assertEqual({}, specification.Labels)
		self.assertEqual({}, specification.Documents)
		self.assertEqual({}, specification.Layers)
		self.assertEqual([], list(specification.IterateElements()))
		self.assertEqual(0, len(specification))

	def test_KeyValuePairs(self) -> None:
		specification =           RequirementSpecification("Board", VERSION, keyValuePairs={"customer": "EDA²"})
		specification["status"] = "draft"

		self.assertEqual(2, len(specification))
		self.assertEqual("EDA²", specification["customer"])
		self.assertIn("status", specification)

	def test_Parent(self) -> None:
		"""A specification is the root: it has no parent."""
		specification = RequirementSpecification("Board", VERSION)

		with self.assertRaises(TypeError) as context:
			specification.Parent = RequirementSpecification("System", VERSION)

		self.assertEqual("A 'pyEDAA.Reports.Requirements.RequirementSpecification' has no parent.", str(context.exception))

	def test_ParameterChecks(self) -> None:
		for name, version, exception, message in (
			(None,    VERSION, ValueError, "Parameter 'name' is None."),
			(1,       VERSION, TypeError,  "Parameter 'name' is not of type 'str'."),
			("",      VERSION, ValueError, "Parameter 'name' is empty."),
			("Board", None,    ValueError, "Parameter 'version' is None."),
			("Board", "1.2.0", TypeError,  "Parameter 'version' is not of type 'SemanticVersion'."),
		):
			with self.subTest(message=message):
				with self.assertRaises(exception) as context:
					_ = RequirementSpecification(name, version)

				self.assertEqual(message, str(context.exception))


class Registries(Testcase):
	def test_Elements(self) -> None:
		"""Personas, labels, documents and layers are registered in their specification by ID."""
		specification = RequirementSpecification("Board", VERSION)
		for elementClass, dictionary in (
			(Persona,  specification.Personas),
			(Label,    specification.Labels),
			(Document, specification.Documents),
			(Layer,    specification.Layers),
		):
			with self.subTest(elementClass=elementClass.__name__):
				element = elementClass("id", "Name", description="Text", keyValuePairs={"key": 1}, parent=specification)

				self.assertEqual("id", element.ID)
				self.assertEqual("Name", element.Name)
				self.assertEqual("Text", element.Description)
				self.assertEqual(1, element["key"])
				self.assertIs(specification, element.Parent)
				self.assertIs(specification, element.Root)
				self.assertEqual({"id": element}, dictionary)
				self.assertEqual([], list(element.IterateElements()))

		self.assertEqual(4, len(list(specification.IterateElements())))

	def test_Standalone(self) -> None:
		persona = Persona("alice", "Alice")

		self.assertIsNone(persona.Parent)
		self.assertIsNone(persona.Root)
		self.assertEqual("", persona.Description)

	def test_Parent(self) -> None:
		"""An element without a parent is registered, when the parent is assigned."""
		specification = RequirementSpecification("Board", VERSION)
		label =         Label("asic", "ASIC variant")
		label.Parent =  specification

		self.assertIs(specification, label.Parent)
		self.assertIs(specification, label.Root)
		self.assertIs(label, specification.Labels["asic"])

	def test_Parent_Twice(self) -> None:
		specification = RequirementSpecification("Board", VERSION)
		label =         Label("asic", "ASIC variant", parent=specification)

		with self.assertRaises(ValueError) as context:
			label.Parent = RequirementSpecification("System", VERSION)

		self.assertEqual("Label already has a parent.", str(context.exception))

	def test_Duplicate(self) -> None:
		"""An ID is unique per class: a duplicate is rejected, the same ID of another class is not."""
		specification = RequirementSpecification("Board", VERSION)
		Persona("fw", "Firmware engineer", parent=specification)
		Layer("fw", "FPGA firmware", parent=specification)

		with self.assertRaises(ValueError) as context:
			Persona("fw", "Firmware architect", parent=specification)

		self.assertEqual("Persona 'fw' already exists in specification 'Board'.", str(context.exception))
		self.assertEqual("Firmware engineer", specification.Personas["fw"].Name)

		Document("manual", "Board manual", parent=specification)
		document = Document("manual", "Firmware manual")
		with self.assertRaises(ValueError) as context:
			document.Parent = specification

		self.assertEqual("Document 'manual' already exists in specification 'Board'.", str(context.exception))
		self.assertIsNone(document.Parent)
		self.assertIsNone(document.Root)

	def test_ParameterChecks(self) -> None:
		for identifier, name, description, exception, message in (
			(None,    "Alice", "",   ValueError, "Parameter 'identifier' is None."),
			(1,       "Alice", "",   TypeError,  "Parameter 'identifier' is not of type 'str'."),
			("",      "Alice", "",   ValueError, "Parameter 'identifier' is empty."),
			("alice", None,    "",   ValueError, "Parameter 'name' is None."),
			("alice", 1,       "",   TypeError,  "Parameter 'name' is not of type 'str'."),
			("alice", "",      "",   ValueError, "Parameter 'name' is empty."),
			("alice", "Alice", None, ValueError, "Parameter 'description' is None."),
			("alice", "Alice", 1,    TypeError,  "Parameter 'description' is not of type 'str'."),
		):
			with self.subTest(message=message):
				with self.assertRaises(exception) as context:
					_ = Persona(identifier, name, description=description)

				self.assertEqual(message, str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = Persona("alice", "Alice", parent=Persona("bob", "Bob"))

		self.assertEqual("Parameter 'parent' is not of type 'RequirementSpecification'.", str(context.exception))
		self.assertEqual(["Got type 'pyEDAA.Reports.Requirements.Persona'."], context.exception.__notes__)

		persona = Persona("alice", "Alice")
		with self.assertRaises(ValueError) as context:
			persona.Parent = None

		self.assertEqual("Parameter 'parent' is None.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			persona.Parent = Persona("bob", "Bob")

		self.assertEqual("Parameter 'parent' is not of type 'RequirementSpecification'.", str(context.exception))
