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
"""Unit tests of the requirements model: requirements, their hierarchy, and iterating them."""
from datetime                    import datetime, timedelta, timezone

from pyEDAA.Reports.Requirements import ItemState, Label, Obligation, Requirement, RequirementKind
from pyEDAA.Reports.Requirements import RequirementSpecification, RequirementsError
from pyTooling.Versioning        import SemanticVersion
from pyTooling.Testing           import Testcase


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


VERSION =    SemanticVersion(1, 2, 0)                                         #: Version of the specifications.
CREATED =    datetime(2026, 3, 1, 9, 30, tzinfo=timezone(timedelta(hours=1)))  #: Creation time of the requirements.
FUNCTIONAL = RequirementKind.Functional                                       #: Kind of most requirements.


class Enumerations(Testcase):
	def test_Parse(self) -> None:
		self.assertIs(ItemState.Placeholder, ItemState.Parse("placeholder"))
		self.assertIs(ItemState.InReview, ItemState.Parse("in-review"))
		self.assertIs(ItemState.Final, ItemState.Parse("final"))
		self.assertIs(ItemState.Closed, ItemState.Parse("closed"))
		self.assertIs(RequirementKind.Environmental, RequirementKind.Parse("environmental"))
		self.assertIs(Obligation.Recommended, Obligation.Parse("recommended"))

		with self.assertRaises(ValueError) as context:
			_ = Obligation.Parse("shall")

		self.assertEqual("'shall' is not a valid Obligation.", str(context.exception))


class Instantiation(Testcase):
	def test_Requirement(self) -> None:
		requirement = Requirement("REQ-1", "Supply voltage", RequirementKind.Environmental, CREATED)

		self.assertEqual("REQ-1", requirement.ID)
		self.assertEqual("Supply voltage", requirement.Title)
		self.assertEqual("", requirement.Description)
		self.assertIs(RequirementKind.Environmental, requirement.Kind)
		self.assertIs(CREATED, requirement.Created)
		self.assertIs(Obligation.Mandatory, requirement.Obligation)
		self.assertIs(ItemState.Draft, requirement.State)
		self.assertIsNone(requirement.Parent)
		self.assertIsNone(requirement.Root)
		self.assertEqual({}, requirement.Children)
		self.assertEqual(0, len(requirement))

	def test_State(self) -> None:
		requirement =       Requirement("REQ-1", "Supply voltage", FUNCTIONAL, CREATED)
		requirement.State = ItemState.Verified

		self.assertIs(ItemState.Verified, requirement.State)

		with self.assertRaises(ValueError) as context:
			requirement.State = None

		self.assertEqual("Parameter 'state' is None.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			requirement.State = "verified"

		self.assertEqual("Parameter 'state' is not of type 'ItemState'.", str(context.exception))
		self.assertEqual(["Got type 'str'."], context.exception.__notes__)


class Hierarchy(Testcase):
	def _Specification(self) -> RequirementSpecification:
		"""
		Build a specification of two top-level requirements: ``A`` with children ``A.1`` (with ``A.1.1``) and ``A.2``, and
		``B``.
		"""
		specification = RequirementSpecification(VERSION, "Board")
		a =             Requirement("A", "Power", FUNCTIONAL, CREATED, parent=specification)
		a1 =            Requirement("A.1", "Rails", FUNCTIONAL, CREATED, parent=a)
		Requirement("A.1.1", "Core rail", RequirementKind.Performance, CREATED, parent=a1)
		Requirement("A.2", "Sequencing", FUNCTIONAL, CREATED, parent=a)
		Requirement("B", "Housing", RequirementKind.Constraint, CREATED, parent=specification)

		return specification

	def test_Children(self) -> None:
		specification = self._Specification()
		a =             specification.Requirements["A"]

		self.assertEqual(["A", "A.1", "A.1.1", "A.2", "B"], list(specification.Requirements))
		self.assertEqual(["A.1", "A.2"], list(a.Children))
		self.assertEqual(["A.1", "A.2"], [child.ID for child in a.IterateChildren()])
		self.assertIs(a, specification.Requirements["A.1"].Parent)
		self.assertIs(specification, a.Parent)
		self.assertIs(specification, specification.Requirements["A.1.1"].Root)

	def test_Descendants(self) -> None:
		"""Descendants are iterated depth-first: each child followed by the items below it."""
		specification = self._Specification()
		a =             specification.Requirements["A"]

		self.assertEqual(["A.1", "A.1.1", "A.2"], [item.ID for item in a.IterateDescendants()])
		self.assertEqual([], list(specification.Requirements["B"].IterateDescendants()))
		self.assertEqual(["A", "A.1", "A.1.1", "A.2", "B"], [item.ID for item in specification.IterateRequirements()])

	def test_Predicate(self) -> None:
		specification = self._Specification()
		a =             specification.Requirements["A"]

		def isFunctional(requirement: Requirement) -> bool:
			"""Nested function selecting functional requirements."""
			return requirement.Kind is FUNCTIONAL

		self.assertEqual(["A", "A.1", "A.2"], [item.ID for item in specification.IterateRequirements(isFunctional)])
		self.assertEqual(["A.1", "A.2"], [item.ID for item in a.IterateChildren(isFunctional)])
		self.assertEqual(["A.1.1"], [item.ID for item in a.IterateDescendants(lambda item: not isFunctional(item))])
		self.assertEqual(["A.1"], [item.ID for item in a.IterateChildren(lambda item: item.ID == "A.1")])

	def test_Parent(self) -> None:
		"""A subtree built without a specification joins it, when its top requirement gets a parent."""
		specification = self._Specification()
		c =             Requirement("C", "Cooling", FUNCTIONAL, CREATED)
		c1 =            Requirement("C.1", "Fan", FUNCTIONAL, CREATED, parent=c)
		Requirement("C.1.1", "Fan control", FUNCTIONAL, CREATED, parent=c1)
		c.Parent = specification.Requirements["B"]

		self.assertEqual(["A", "A.1", "A.1.1", "A.2", "B", "C", "C.1", "C.1.1"], list(specification.Requirements))
		self.assertTrue(all(item.Root is specification for item in specification.IterateRequirements()))
		self.assertEqual(["C"], list(specification.Requirements["B"].Children))

	def test_Duplicate(self) -> None:
		specification = self._Specification()

		with self.assertRaises(RequirementsError) as context:
			Requirement("A.1.1", "Core rail", FUNCTIONAL, CREATED, parent=specification.Requirements["B"])

		self.assertEqual("Requirement 'A.1.1' already exists in the specification.", str(context.exception))
		self.assertEqual({}, specification.Requirements["B"].Children)

		c = Requirement("C", "Cooling", FUNCTIONAL, CREATED)
		Requirement("A.2", "Fan", FUNCTIONAL, CREATED, parent=c)
		with self.assertRaises(RequirementsError) as context:
			c.Parent = specification

		self.assertEqual("Requirement 'A.2' already exists in the specification.", str(context.exception))
		self.assertNotIn("C", specification.Requirements)
		self.assertIsNone(c.Parent)

		with self.assertRaises(RequirementsError) as context:
			Requirement("A.2", "Pump", FUNCTIONAL, CREATED, parent=c)

		self.assertEqual("Requirement 'C' already has a child 'A.2'.", str(context.exception))

	def test_Duplicate_Subtree(self) -> None:
		"""A subtree using an ID twice is rejected as a whole."""
		specification = self._Specification()
		c =             Requirement("C", "Cooling", FUNCTIONAL, CREATED)
		Requirement("C.1", "Fan", FUNCTIONAL, CREATED, parent=Requirement("C.0", "Air", FUNCTIONAL, CREATED, parent=c))
		Requirement("C.1", "Fan", FUNCTIONAL, CREATED, parent=c)

		with self.assertRaises(RequirementsError) as context:
			c.Parent = specification

		self.assertEqual("Requirement 'C.1' already exists in the specification.", str(context.exception))
		self.assertNotIn("C", specification.Requirements)
		self.assertNotIn("C.0", specification.Requirements)

	def test_Parent_Twice(self) -> None:
		specification = self._Specification()

		with self.assertRaises(RequirementsError) as context:
			specification.Requirements["A.2"].Parent = specification.Requirements["B"]

		self.assertEqual("Requirement already has a parent.", str(context.exception))


class ParameterChecks(Testcase):
	def test_Requirement(self) -> None:
		naive = datetime(2026, 3, 1, 9, 30)
		for arguments, exception, message in (
			((None, "Title", FUNCTIONAL, CREATED),   ValueError, "Parameter 'identifier' is None."),
			(("REQ-1", None, FUNCTIONAL, CREATED),   ValueError, "Parameter 'title' is None."),
			(("REQ-1", 1, FUNCTIONAL, CREATED),      TypeError,  "Parameter 'title' is not of type 'str'."),
			(("REQ-1", "", FUNCTIONAL, CREATED),     ValueError, "Parameter 'title' is empty."),
			(("REQ-1", "Title", FUNCTIONAL, None),   ValueError, "Parameter 'created' is None."),
			(("REQ-1", "Title", FUNCTIONAL, "2026"), TypeError,  "Parameter 'created' is not of type 'datetime'."),
			(("REQ-1", "Title", FUNCTIONAL, naive),  ValueError, "Parameter 'created' has no time zone."),
			(("REQ-1", "Title", None, CREATED),      ValueError, "Parameter 'kind' is None."),
			(("REQ-1", "Title", "func", CREATED),    TypeError,  "Parameter 'kind' is not of type 'RequirementKind'."),
		):
			with self.subTest(message=message):
				with self.assertRaises(exception) as context:
					_ = Requirement(*arguments)

				self.assertEqual(message, str(context.exception))

		for keywordArguments, exception, message in (
			({"state": None},             ValueError, "Parameter 'state' is None."),
			({"state": "draft"},          TypeError,  "Parameter 'state' is not of type 'ItemState'."),
			({"obligation": None},        ValueError, "Parameter 'obligation' is None."),
			({"obligation": "may"},       TypeError,  "Parameter 'obligation' is not of type 'Obligation'."),
			({"parent": Label("a", "A")}, TypeError,
				"Parameter 'parent' is not of type 'Requirement' or 'RequirementSpecification'."),
		):
			with self.subTest(message=message):
				with self.assertRaises(exception) as context:
					_ = Requirement("REQ-1", "Title", FUNCTIONAL, CREATED, **keywordArguments)

				self.assertEqual(message, str(context.exception))
