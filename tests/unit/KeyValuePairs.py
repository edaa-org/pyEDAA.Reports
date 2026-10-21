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
"""Unit tests of :class:`~pyTooling.DataModel.KeyValuePairsMixin` in an element of a data model."""
from pyTooling.DataModel   import KeyValuePairsMixin
from pyTooling.MetaClasses import ExtendedType
from pyTooling.Testing     import Testcase


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


class Element(KeyValuePairsMixin, metaclass=ExtendedType, slots=True):
	"""An element of a data model with key-value pairs."""


class KeyValuePairs(Testcase):
	def test_Empty(self) -> None:
		element = Element()

		self.assertEqual(0, len(element))
		self.assertEqual([], list(element))
		self.assertNotIn("owner", element)

	def test_DictionarySyntax(self) -> None:
		element = Element({"owner": "Paebbels"})

		self.assertEqual(1, len(element))
		self.assertEqual("Paebbels", element["owner"])
		element["owner"] = "EDA²"
		element["effort"] = 3
		self.assertEqual({"owner": "EDA²", "effort": 3}, {key: element[key] for key in element})
		self.assertEqual(["owner", "effort"], list(element))
		self.assertIn("effort", element)

		del element["owner"]
		self.assertNotIn("owner", element)
		with self.assertRaises(KeyError):
			_ = element["owner"]

		with self.assertRaises(KeyError):
			del element["owner"]

	def test_ParameterChecks(self) -> None:
		with self.assertRaises(TypeError) as context:
			_ = Element([("owner", 1)])

		self.assertEqual("Parameter 'keyValuePairs' is not a mapping ('dict', ...).", str(context.exception))
		self.assertEqual(["Got type 'list'."], context.exception.__notes__)
