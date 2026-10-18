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

from pyEDAA.Reports.Requirements import AlreadyInSpecificationError, DuplicateDocumentError, DuplicateLabelError
from pyEDAA.Reports.Requirements import DuplicateLayerError, DuplicateLinkError, DuplicatePersonaError
from pyEDAA.Reports.Requirements import DuplicatePersonError, DuplicateRequirementError, DuplicateSpecificationItemError
from pyEDAA.Reports.Requirements import ItemState, Label, NotInSameSpecificationError, Obligation, Requirement
from pyEDAA.Reports.Requirements import RequirementKind
from pyEDAA.Reports.Requirements import RequirementSpecification, RequirementsError
from pyTooling.Exceptions        import AlreadyInHierarchyError, DuplicateElementError, NotInSameHierarchyError
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
		requirement = Requirement("REQ-1", "Supply voltage", RequirementKind.Environmental, created=CREATED)

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

	def test_Created(self) -> None:
		"""Without a creation time, a requirement is created now; a time without a time zone is a local time."""
		before =  datetime.now()
		current = Requirement("REQ-1", "Supply voltage", FUNCTIONAL)
		after =   datetime.now()
		local =   Requirement("REQ-2", "Supply current", FUNCTIONAL, "Below 2 A.", datetime(2026, 3, 1, 9, 30))

		self.assertTrue(before <= current.Created <= after)
		self.assertEqual(datetime(2026, 3, 1, 9, 30), local.Created)
		self.assertEqual("Below 2 A.", local.Description)

	def test_State(self) -> None:
		requirement =       Requirement("REQ-1", "Supply voltage", FUNCTIONAL)
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
		a =             Requirement("A", "Power", FUNCTIONAL, parent=specification)
		a1 =            Requirement("A.1", "Rails", FUNCTIONAL, parent=a)
		Requirement("A.1.1", "Core rail", RequirementKind.Performance, parent=a1)
		Requirement("A.2", "Sequencing", FUNCTIONAL, parent=a)
		Requirement("B", "Housing", RequirementKind.Constraint, parent=specification)

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
		c =             Requirement("C", "Cooling", FUNCTIONAL)
		c1 =            Requirement("C.1", "Fan", FUNCTIONAL, parent=c)
		Requirement("C.1.1", "Fan control", FUNCTIONAL, parent=c1)
		c.Parent = specification.Requirements["B"]

		self.assertEqual(["A", "A.1", "A.1.1", "A.2", "B", "C", "C.1", "C.1.1"], list(specification.Requirements))
		self.assertTrue(all(item.Root is specification for item in specification.IterateRequirements()))
		self.assertEqual(["C"], list(specification.Requirements["B"].Children))

	def test_Duplicate(self) -> None:
		specification = self._Specification()

		with self.assertRaises(DuplicateRequirementError) as context:
			Requirement("A.1.1", "Core rail", FUNCTIONAL, parent=specification.Requirements["B"])

		self.assertEqual("Requirement 'A.1.1' already exists in the specification.", str(context.exception))
		self.assertEqual({}, specification.Requirements["B"].Children)

		c = Requirement("C", "Cooling", FUNCTIONAL)
		Requirement("A.2", "Fan", FUNCTIONAL, parent=c)
		with self.assertRaises(DuplicateRequirementError) as context:
			c.Parent = specification

		self.assertEqual("Requirement 'A.2' already exists in the specification.", str(context.exception))
		self.assertNotIn("C", specification.Requirements)
		self.assertIsNone(c.Parent)

		with self.assertRaises(DuplicateRequirementError) as context:
			Requirement("A.2", "Pump", FUNCTIONAL, parent=c)

		self.assertEqual("Requirement 'C' already has a child 'A.2'.", str(context.exception))

	def test_Duplicate_Subtree(self) -> None:
		"""A subtree using an ID twice is rejected as a whole."""
		specification = self._Specification()
		c =             Requirement("C", "Cooling", FUNCTIONAL)
		Requirement("C.1", "Fan", FUNCTIONAL, parent=Requirement("C.0", "Air", FUNCTIONAL, parent=c))
		Requirement("C.1", "Fan", FUNCTIONAL, parent=c)

		with self.assertRaises(DuplicateRequirementError) as context:
			c.Parent = specification

		self.assertEqual("Requirement 'C.1' already exists in the specification.", str(context.exception))
		self.assertNotIn("C", specification.Requirements)
		self.assertNotIn("C.0", specification.Requirements)

	def test_Parent_Twice(self) -> None:
		specification = self._Specification()

		with self.assertRaises(AlreadyInSpecificationError) as context:
			specification.Requirements["A.2"].Parent = specification.Requirements["B"]

		self.assertEqual("Requirement already has a parent.", str(context.exception))

	def test_DuplicateErrors(self) -> None:
		"""Every duplicate error is a 'DuplicateElementError' and a 'RequirementsError'."""
		for exception in (
			DuplicatePersonaError, DuplicateLabelError, DuplicateDocumentError, DuplicateLayerError, DuplicatePersonError,
			DuplicateRequirementError, DuplicateSpecificationItemError, DuplicateLinkError
		):
			with self.subTest(exception=exception.__name__):
				self.assertTrue(issubclass(exception, DuplicateElementError))
				self.assertTrue(issubclass(exception, RequirementsError))

	def test_HierarchyErrors(self) -> None:
		"""The hierarchy errors derive from the common bases and from 'RequirementsError'."""
		self.assertTrue(issubclass(AlreadyInSpecificationError, AlreadyInHierarchyError))
		self.assertTrue(issubclass(AlreadyInSpecificationError, RequirementsError))
		self.assertTrue(issubclass(NotInSameSpecificationError, NotInSameHierarchyError))
		self.assertTrue(issubclass(NotInSameSpecificationError, RequirementsError))


class ParameterChecks(Testcase):
	def test_Requirement(self) -> None:
		for arguments, exception, message in (
			((None, "Title", FUNCTIONAL),           ValueError, "Parameter 'identifier' is None."),
			(("REQ-1", None, FUNCTIONAL),           ValueError, "Parameter 'title' is None."),
			(("REQ-1", 1, FUNCTIONAL),              TypeError,  "Parameter 'title' is not of type 'str'."),
			(("REQ-1", "", FUNCTIONAL),             ValueError, "Parameter 'title' is empty."),
			(("REQ-1", "Title", FUNCTIONAL, None),  ValueError, "Parameter 'description' is None."),
			(("REQ-1", "Title", FUNCTIONAL, "", 1), TypeError,  "Parameter 'created' is not of type 'datetime'."),
			(("REQ-1", "Title", None),              ValueError, "Parameter 'kind' is None."),
			(("REQ-1", "Title", "func"),            TypeError,  "Parameter 'kind' is not of type 'RequirementKind'."),
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
					_ = Requirement("REQ-1", "Title", FUNCTIONAL, **keywordArguments)

				self.assertEqual(message, str(context.exception))
