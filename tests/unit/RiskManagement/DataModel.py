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
#
"""Unit tests of the risk management model: enumerations, risks and the risk register."""
from pyEDAA.Reports.RiskManagement import Impact, Probability, Risk, RiskManagement, RiskState
from pyTooling.Versioning          import SemanticVersion
from pyTooling.Testing             import Testcase


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


VERSION = SemanticVersion(1, 0, 0)  #: Version of the risk registers of the tests.


class Enumerations(Testcase):
	def test_Probability(self) -> None:
		self.assertIs(Probability.Occurred, Probability.Parse("occurred"))
		self.assertIsNone(Probability.Parse(None))
		self.assertEqual(["low", "medium", "high", "occurred"], [str(probability) for probability in Probability])

	def test_Impact(self) -> None:
		self.assertIs(Impact.Critical, Impact.Parse("critical"))
		self.assertEqual(["low", "medium", "high", "critical"], [str(impact) for impact in Impact])

	def test_RiskState(self) -> None:
		self.assertIs(RiskState.OnHold, RiskState.Parse("on-hold"))
		self.assertIs(RiskState.Open, RiskState.Parse(None))
		self.assertIs(RiskState.Open, RiskState.DEFAULT)
		self.assertEqual(["open", "on-hold", "closed", "solved"], [str(state) for state in RiskState])


class RiskManagementInstantiation(Testcase):
	def test_Empty(self) -> None:
		riskManagement = RiskManagement(VERSION, {"project": "pyEDAA"})

		self.assertIs(VERSION, riskManagement.Version)
		self.assertIsNone(riskManagement.Parent)
		self.assertIs(riskManagement, riskManagement.Root)
		self.assertEqual({}, riskManagement.Risks)
		self.assertEqual([], list(riskManagement.IterateElements()))
		self.assertEqual("pyEDAA", riskManagement["project"])
		self.assertEqual("<RiskManagement 1.0.0: 0 risks>", repr(riskManagement))

	def test_Version(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = RiskManagement(None)
		self.assertEqual("Parameter 'version' is None.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = RiskManagement("1.0.0")
		self.assertEqual("Parameter 'version' is not of type 'SemanticVersion'.", str(context.exception))
		self.assertEqual(["Got type 'str'."], context.exception.__notes__)

	def test_NoParent(self) -> None:
		riskManagement = RiskManagement(VERSION)

		with self.assertRaises(TypeError) as context:
			riskManagement.Parent = RiskManagement(VERSION)
		self.assertEqual("A 'pyEDAA.Reports.RiskManagement.RiskManagement' has no parent.", str(context.exception))


class ElementInstantiation(Testcase):
	def test_Risk(self) -> None:
		risk = Risk("R1", "Late silicon", "The foundry delays the wafers.", Probability.Medium, Impact.High)

		self.assertIsNone(risk.Parent)
		self.assertIsNone(risk.Root)
		self.assertEqual("R1", risk.ID)
		self.assertEqual("Late silicon", risk.Title)
		self.assertEqual("The foundry delays the wafers.", risk.Description)
		self.assertIs(Probability.Medium, risk.Probability)
		self.assertIs(Impact.High, risk.Impact)
		self.assertIs(RiskState.Open, risk.State)
		self.assertEqual(0, len(risk))
		self.assertEqual([], list(risk.IterateElements()))
		self.assertEqual("<Risk R1: open, probability medium, impact high>", repr(risk))

	def test_Risk_Assessment(self) -> None:
		"""Probability, impact and state are reassessed by assignment."""
		risk = Risk("R1", "Late silicon", "The foundry delays the wafers.", Probability.Low, Impact.Low)

		risk.Probability = Probability.Occurred
		risk.Impact =      Impact.Critical
		risk.State =       RiskState.Solved

		self.assertIs(Probability.Occurred, risk.Probability)
		self.assertIs(Impact.Critical, risk.Impact)
		self.assertIs(RiskState.Solved, risk.State)

		for name, value, exception, message in (
			("Probability", None,     ValueError, "Parameter 'value' is None."),
			("Probability", "high",   TypeError,  "Parameter 'value' is not of type 'Probability'."),
			("Impact",      None,     ValueError, "Parameter 'value' is None."),
			("Impact",      "high",   TypeError,  "Parameter 'value' is not of type 'Impact'."),
			("State",       None,     ValueError, "Parameter 'value' is None."),
			("State",       "closed", TypeError,  "Parameter 'value' is not of type 'RiskState'."),
		):
			with self.subTest(name=name, value=value):
				with self.assertRaises(exception) as context:
					setattr(risk, name, value)
				self.assertEqual(message, str(context.exception))

	def test_Risk_ParameterChecks(self) -> None:
		low =   Probability.Low
		minor = Impact.Low
		for arguments, exception, message in (
			((None, "T",  "D",  low,   minor),         ValueError, "Parameter 'identifier' is None."),
			((1,    "T",  "D",  low,   minor),         TypeError,  "Parameter 'identifier' is not of type 'str'."),
			(("",   "T",  "D",  low,   minor),         ValueError, "Parameter 'identifier' is empty."),
			(("R1", "T",  None, low,   minor),         ValueError, "Parameter 'description' is None."),
			(("R1", "T",  1,    low,   minor),         TypeError,  "Parameter 'description' is not of type 'str'."),
			(("R1", "T",  "",   low,   minor),         ValueError, "Parameter 'description' is empty."),
			(("R1", None, "D",  low,   minor),         ValueError, "Parameter 'title' is None."),
			(("R1", 1,    "D",  low,   minor),         TypeError,  "Parameter 'title' is not of type 'str'."),
			(("R1", "",   "D",  low,   minor),         ValueError, "Parameter 'title' is empty."),
			(("R1", "T",  "D",  None,  minor),         ValueError, "Parameter 'probability' is None."),
			(("R1", "T",  "D",  minor, minor),         TypeError,  "Parameter 'probability' is not of type 'Probability'."),
			(("R1", "T",  "D",  low,   None),          ValueError, "Parameter 'impact' is None."),
			(("R1", "T",  "D",  low,   "low"),         TypeError,  "Parameter 'impact' is not of type 'Impact'."),
			(("R1", "T",  "D",  low,   minor, None),   ValueError, "Parameter 'state' is None."),
			(("R1", "T",  "D",  low,   minor, "open"), TypeError,  "Parameter 'state' is not of type 'RiskState'."),
		):
			with self.subTest(message=message):
				with self.assertRaises(exception) as context:
					_ = Risk(*arguments)
				self.assertEqual(message, str(context.exception))

class Register(Testcase):
	def test_Register(self) -> None:
		register = RiskManagement(VERSION)
		foundry =  Risk("R1", "Late silicon", "The foundry is late.", Probability.Medium, Impact.High, parent=register)
		tools =    Risk("R2", "Tool license", "A license expires.", Probability.Low, Impact.Medium, parent=register)

		self.assertIs(register, foundry.Parent)
		self.assertIs(register, foundry.Root)
		self.assertEqual({"R1": foundry, "R2": tools}, register.Risks)
		self.assertEqual([foundry, tools], list(register.IterateElements()))
		self.assertEqual("<RiskManagement 1.0.0: 2 risks>", repr(register))

	def test_Iterate(self) -> None:
		register = RiskManagement(VERSION)
		foundry =  Risk("R1", "Late silicon", "The foundry is late.", Probability.High, Impact.High, parent=register)
		tools =    Risk("R2", "Tool license", "A license expires.", Probability.Low, Impact.Low, parent=register)
		tools.State = RiskState.Closed

		self.assertEqual([foundry, tools], list(register.IterateRisks()))
		self.assertEqual([tools], list(register.IterateRisks(lambda risk: risk.State is RiskState.Closed)))

	def test_Duplicate(self) -> None:
		register = RiskManagement(VERSION)
		Risk("R1", "Late silicon", "The foundry is late.", Probability.High, Impact.High, parent=register)

		with self.assertRaises(ValueError) as context:
			_ = Risk("R1", "Tool license", "A license expires.", Probability.Low, Impact.Low, parent=register)
		self.assertEqual("Risk 'R1' already exists in the risk register.", str(context.exception))
		self.assertEqual("Late silicon", register.Risks["R1"].Title)

	def test_Parent(self) -> None:
		"""A risk built without a register joins it by assigning the parent."""
		register = RiskManagement(VERSION)
		risk =     Risk("R1", "Late silicon", "The foundry is late.", Probability.High, Impact.High)
		risk.Parent = register

		self.assertIs(register, risk.Parent)
		self.assertIs(register, risk.Root)
		self.assertEqual({"R1": risk}, register.Risks)

		for parent, exception, message in (
			(None,     ValueError, "Parameter 'parent' is None."),
			(risk,     TypeError,  "Parameter 'parent' is not of type 'RiskManagement'."),
			(register, ValueError, "Element is already part of a risk register."),
		):
			with self.subTest(message=message):
				with self.assertRaises(exception) as context:
					risk.Parent = parent
				self.assertEqual(message, str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = Risk("R2", "Tool license", "A license expires.", Probability.Low, Impact.Low, parent=risk)
		self.assertEqual("Parameter 'parent' is not of type 'RiskManagement'.", str(context.exception))
		self.assertEqual(["Got type 'pyEDAA.Reports.RiskManagement.Risk'."], context.exception.__notes__)

		other = Risk("R1", "Tool license", "A license expires.", Probability.Low, Impact.Low)
		with self.assertRaises(ValueError) as context:
			other.Parent = register
		self.assertEqual("Risk 'R1' already exists in the risk register.", str(context.exception))
		self.assertIsNone(other.Parent)
