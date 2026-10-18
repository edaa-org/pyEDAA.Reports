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
"""Unit tests of the requirements model: rationale, verification methods and acceptance criteria."""
from pyTooling.Testing           import Testcase

from pyEDAA.Reports.Requirements import Requirement, RequirementSpecification, SpecificationItem, VerificationMethod

from .                           import FUNCTIONAL, VERSION


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


class Verification(Testcase):
	def test_Defaults(self) -> None:
		requirement = Requirement("REQ-1", "Interrupts", FUNCTIONAL)

		self.assertEqual("", requirement.Rationale)
		self.assertIs(VerificationMethod.Unknown, requirement.VerificationMethods)
		self.assertEqual([], requirement.AcceptanceCriteria)

	def test_Requirement(self) -> None:
		requirement = Requirement(
			"REQ-1",
			"Interrupt latency",
			FUNCTIONAL,
			rationale="The motor control loop runs at 20 kHz.",
			verificationMethods=VerificationMethod.Simulation | VerificationMethod.Test,
			acceptanceCriteria=("Latency below 1 µs in simulation.", "Latency below 1 µs on the test bench.")
		)

		self.assertEqual("The motor control loop runs at 20 kHz.", requirement.Rationale)
		self.assertIn(VerificationMethod.Test, requirement.VerificationMethods)
		self.assertNotIn(VerificationMethod.Formal, requirement.VerificationMethods)
		self.assertEqual(
			["Latency below 1 µs in simulation.", "Latency below 1 µs on the test bench."],
			requirement.AcceptanceCriteria
		)

	def test_SpecificationItem(self) -> None:
		"""A specification item states its rationale, too: why a design decision was taken."""
		specification = RequirementSpecification(VERSION, "Board")
		design =        SpecificationItem("DES-1", "Vectored interrupts", rationale="Fast.", parent=specification)

		self.assertEqual("Fast.", design.Rationale)

	def test_ParameterChecks(self) -> None:
		for keywordArguments, exception, message in (
			({"rationale": None},                ValueError,
				"Parameter 'rationale' is None."),
			({"rationale": 1},                   TypeError,
				"Parameter 'rationale' is not of type 'str'."),
			({"verificationMethods": None},      ValueError,
				"Parameter 'verificationMethods' is None."),
			({"verificationMethods": 8},         TypeError,
				"Parameter 'verificationMethods' is not of type 'VerificationMethod'."),
			({"acceptanceCriteria": 1},          TypeError,
				"Parameter 'acceptanceCriteria' is not iterable."),
			({"acceptanceCriteria": "Fast."},    TypeError,
				"Parameter 'acceptanceCriteria' is a single string, not an iterable of strings."),
			({"acceptanceCriteria": [1]},        TypeError,
				"Parameter 'acceptanceCriteria' contains an element not of type 'str'."),
			({"acceptanceCriteria": ["a", ""]},  ValueError,
				"Parameter 'acceptanceCriteria' contains an empty criterion."),
		):
			with self.subTest(message=message):
				with self.assertRaises(exception) as context:
					_ = Requirement("REQ-1", "Title", FUNCTIONAL, **keywordArguments)

				self.assertEqual(message, str(context.exception))
