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
"""Unit tests of :class:`~pyEDAA.Reports.Person`."""
from pyTooling.Testing import Testcase

from pyEDAA.Reports    import Person


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


class Persons(Testcase):
	def test_Person(self) -> None:
		person = Person("paebbels", "Patrick Lehmann", "Paebbels@gmail.com", {"role": "maintainer"})

		self.assertEqual(("paebbels", "Patrick Lehmann", "Paebbels@gmail.com", "maintainer"), (
			person.UserID, person.Name, person.Email, person["role"]
		))
		self.assertEqual("<Person paebbels: Patrick Lehmann <Paebbels@gmail.com>>", repr(person))
		self.assertIsNone(Person("claude", "Claude Code").Email)
		self.assertEqual("<Person claude: Claude Code>", repr(Person("claude", "Claude Code")))

	def test_ParameterChecks(self) -> None:
		for arguments, exception, message in (
			((None, "Patrick Lehmann"),                ValueError, "Parameter 'userID' is None."),
			(("paebbels", 1),                          TypeError,  "Parameter 'name' is not of type 'str'."),
			(("", "Patrick Lehmann"),                  ValueError, "Parameter 'userID' is empty."),
			(("paebbels", "Patrick Lehmann", 1),       TypeError,  "Parameter 'email' is not of type 'str'."),
			(("paebbels", "Patrick Lehmann", "gmail"), ValueError, "Parameter 'email' isn't of the form 'local@domain'."),
			(("paebbels", "Patrick Lehmann", "@gmail.com"), ValueError,
			 "Parameter 'email' isn't of the form 'local@domain'."),
		):
			with self.subTest(message=message):
				with self.assertRaises(exception) as context:
					_ = Person(*arguments)

				self.assertEqual(message, str(context.exception))
