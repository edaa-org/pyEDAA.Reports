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
"""Unit tests of the requirements model: the history of an item."""
from datetime                    import datetime, timedelta, timezone

from pyTooling.Versioning        import SemanticVersion
from pyTooling.Testing           import Testcase

from pyEDAA.Reports              import Person
from pyEDAA.Reports.Requirements import EventKind, HistoryEvent, ItemState, Persona, Requirement, RequirementKind, \
                                        DuplicateRequirementError, NotInSameSpecificationError, \
                                        RequirementSpecification, RequirementsError


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


VERSION =    SemanticVersion(1, 2, 0)                          #: Version of the specifications under test.
CREATED =    datetime(2026, 3, 1, 9, 30, tzinfo=timezone.utc)  #: Creation time of the requirements.
DAY =        timedelta(days=1)                                 #: Time between two events.
FUNCTIONAL = RequirementKind.Functional                        #: Kind of the requirements under test.


class History(Testcase):
	def test_Split(self) -> None:
		"""A requirement is split into two, which replace it: the split names them."""
		specification = RequirementSpecification(VERSION, "Board")
		alice =         Person("alice", "Alice")
		original =      Requirement("REQ-1", "Interrupts", FUNCTIONAL, created=CREATED, parent=specification)
		specification.AddPerson(alice)
		opened = HistoryEvent(EventKind.Opened, CREATED, person=alice, parent=original)
		edge =   Requirement("REQ-2", "Edge interrupts", FUNCTIONAL, created=CREATED + 2 * DAY, parent=specification)
		level =  Requirement("REQ-3", "Level interrupts", FUNCTIONAL, created=CREATED + 2 * DAY, parent=specification)
		split =  HistoryEvent(
			EventKind.Split,
			CREATED + 2 * DAY,
			person=alice,
			involved=(edge, level),
			description="One requirement per trigger mode.",
			keyValuePairs={"review": "R-17"},
			parent=original
		)
		original.State = ItemState.Obsolete

		self.assertEqual([opened, split], original.History)
		self.assertIs(EventKind.Split, split.Kind)
		self.assertEqual(CREATED + 2 * DAY, split.Timestamp)
		self.assertIs(alice, split.Person)
		self.assertEqual([edge, level], split.Involved)
		self.assertEqual("One requirement per trigger mode.", split.Description)
		self.assertEqual("R-17", split["review"])
		self.assertIs(original, split.Parent)
		self.assertIs(specification, split.Root)
		self.assertEqual([], opened.Involved)
		self.assertEqual("", opened.Description)

	def test_Parent(self) -> None:
		"""An event without an item joins the item's history, when the item is assigned."""
		requirement =     Requirement("REQ-1", "Interrupts", FUNCTIONAL, created=CREATED)
		modified =        HistoryEvent(EventKind.Modified, CREATED + DAY)
		modified.Parent = requirement

		self.assertEqual([modified], requirement.History)
		self.assertIsNone(modified.Root)

		specification =      RequirementSpecification(VERSION, "Board")
		requirement.Parent = specification

		self.assertIs(specification, modified.Root)

	def test_LocalTime(self) -> None:
		"""A time without a time zone is a local time; the history orders it among times with a time zone."""
		requirement = Requirement("REQ-1", "Interrupts", FUNCTIONAL, created=CREATED)
		reviewed =    HistoryEvent(EventKind.Reviewed, datetime(2026, 3, 5, 9, 30), parent=requirement)

		self.assertEqual(datetime(2026, 3, 5, 9, 30), reviewed.Timestamp)

		with self.assertRaises(RequirementsError):
			HistoryEvent(EventKind.Approved, CREATED + DAY, parent=requirement)

	def test_Chronology(self) -> None:
		"""The history is in chronological order: an event can't be earlier than the creation or the last event."""
		requirement = Requirement("REQ-1", "Interrupts", FUNCTIONAL, created=CREATED)
		HistoryEvent(EventKind.Reviewed, CREATED + DAY, parent=requirement)
		HistoryEvent(EventKind.Approved, CREATED + DAY, parent=requirement)
		for timestamp, message in (
			(CREATED,       "Got '2026-03-01T09:30:00+00:00' after '2026-03-02T09:30:00+00:00'."),
			(CREATED - DAY, "Got '2026-02-28T09:30:00+00:00' after '2026-03-02T09:30:00+00:00'."),
		):
			with self.subTest(timestamp=timestamp):
				with self.assertRaises(RequirementsError) as context:
					HistoryEvent(EventKind.Modified, timestamp, parent=requirement)

				self.assertEqual(
					"History event is earlier than the item's creation or its last event.",
					str(context.exception)
				)
				self.assertEqual([message], context.exception.__notes__)
				self.assertIsInstance(context.exception.__cause__, ValueError)
				self.assertEqual(
					"Parameter 'timestamp' is earlier than '2026-03-02T09:30:00+00:00'.",
					str(context.exception.__cause__)
				)

		other = Requirement("REQ-2", "Title", FUNCTIONAL, created=CREATED)
		with self.assertRaises(RequirementsError):
			HistoryEvent(EventKind.Opened, CREATED - DAY, parent=other)

		self.assertEqual(2, len(requirement.History))

	def test_ParameterChecks(self) -> None:
		specification = RequirementSpecification(VERSION, "Board")
		requirement =   Requirement("REQ-1", "Interrupts", FUNCTIONAL, created=CREATED, parent=specification)
		other =         RequirementSpecification(VERSION, "System")
		foreign =       Requirement("REQ-9", "Title", FUNCTIONAL, created=CREATED, parent=other)
		for kind, timestamp, keywordArguments, exception, message in (
			(None,             CREATED, {},                                ValueError,
				"Parameter 'kind' is None."),
			("opened",         CREATED, {},                                TypeError,
				"Parameter 'kind' is not of type 'EventKind'."),
			(EventKind.Opened, None,    {},                                ValueError,
				"Parameter 'timestamp' is None."),
			(EventKind.Opened, "2026",  {},                                TypeError,
				"Parameter 'timestamp' is not of type 'datetime'."),
			(EventKind.Opened, CREATED, {"person": "alice"},               TypeError,
				"Parameter 'person' is not of type 'Person'."),
			(EventKind.Opened, CREATED, {"person": Persona("a", "A")},     TypeError,
				"Parameter 'person' is not of type 'Person'."),
			(EventKind.Opened, CREATED, {"person": Person("a", "A")},      NotInSameSpecificationError,
				"Parameter 'person' isn't part of the item's specification."),
			(EventKind.Merged, CREATED, {"involved": 1},                   TypeError,
				"Parameter 'involved' is not iterable."),
			(EventKind.Merged, CREATED, {"involved": requirement},         TypeError,
				"Parameter 'involved' is a single element, not an iterable of elements."),
			(EventKind.Merged, CREATED, {"involved": ["REQ-1"]},           TypeError,
				"Parameter 'involved' contains an element not of type 'BaseItem'."),
			(EventKind.Merged, CREATED, {"involved": [foreign]},           NotInSameSpecificationError,
				"Parameter 'involved' contains an item not part of the item's specification."),
			(EventKind.Merged, CREATED, {"involved": [requirement] * 2},   DuplicateRequirementError,
				"Parameter 'involved' contains an item twice."),
			(EventKind.Merged, CREATED, {"involved": []},                  ValueError,
				"Parameter 'involved' names no item for a 'Merged' event."),
			(EventKind.Split,  CREATED, {},                                ValueError,
				"Parameter 'involved' names no item for a 'Split' event."),
			(EventKind.Opened, CREATED, {"description": None},             ValueError,
				"Parameter 'description' is None."),
			(EventKind.Opened, CREATED, {"description": 1},                TypeError,
				"Parameter 'description' is not of type 'str'."),
			(EventKind.Opened, CREATED, {"parent": specification},         TypeError,
				"Parameter 'parent' is not of type 'BaseItem'."),
		):
			with self.subTest(message=message):
				with self.assertRaises(exception) as context:
					arguments = {"parent": requirement}
					arguments.update(keywordArguments)
					_ = HistoryEvent(kind, timestamp, **arguments)

				self.assertEqual(message, str(context.exception))

		self.assertEqual([], requirement.History)
