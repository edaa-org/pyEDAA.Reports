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
"""Unit tests of the risk management model: enumerations, risks, implications, mitigations and the risk register."""
from pyEDAA.Reports.RiskManagement import Impact, Implication, Mitigation, Probability, Risk, RiskManagement, RiskState
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
		riskManagement = RiskManagement(VERSION, keyValuePairs={"project": "pyEDAA"})

		self.assertIs(VERSION, riskManagement.Version)
		self.assertIsNone(riskManagement.Name)
		self.assertIsNone(riskManagement.Parent)
		self.assertIs(riskManagement, riskManagement.Root)
		self.assertEqual({}, riskManagement.Risks)
		self.assertEqual({}, riskManagement.Implications)
		self.assertEqual({}, riskManagement.Mitigations)
		self.assertEqual("pyEDAA", riskManagement["project"])
		self.assertEqual("<RiskManagement 1.0.0: 0 risks, 0 implications, 0 mitigations>", repr(riskManagement))

	def test_Version(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = RiskManagement(None)
		self.assertEqual("Parameter 'version' is None.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = RiskManagement("1.0.0")
		self.assertEqual("Parameter 'version' is not of type 'SemanticVersion'.", str(context.exception))
		self.assertEqual(["Got type 'str'."], context.exception.__notes__)

	def test_Name(self) -> None:
		riskManagement = RiskManagement(VERSION, "pyEDAA.Reports")
		self.assertEqual("pyEDAA.Reports", riskManagement.Name)

		with self.assertRaises(TypeError) as context:
			_ = RiskManagement(VERSION, 1)
		self.assertEqual("Parameter 'name' is not of type 'str'.", str(context.exception))
		self.assertEqual(["Got type 'int'."], context.exception.__notes__)

		with self.assertRaises(ValueError) as context:
			_ = RiskManagement(VERSION, "")
		self.assertEqual("Parameter 'name' is empty.", str(context.exception))

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
		self.assertEqual({}, risk.Implications)
		self.assertEqual({}, risk.Mitigations)
		self.assertEqual({}, risk.SecondOrderImplications)
		self.assertEqual(0, len(risk))
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

	def test_Implication(self) -> None:
		followUp =    Implication("I2", "The product launch is delayed.")
		mitigation =  Mitigation("M1", "Order a second shuttle run.")
		implication = Implication("I1", "The tape-out is delayed.", [followUp], [mitigation], {"weeks": 3})

		self.assertEqual("I1", implication.ID)
		self.assertEqual("The tape-out is delayed.", implication.Description)
		self.assertEqual({"I2": followUp}, implication.Implications)
		self.assertEqual({"M1": mitigation}, implication.Mitigations)
		self.assertEqual(3, implication["weeks"])
		self.assertEqual("<Implication I1: 1 implications, 1 mitigations>", repr(implication))

	def test_Mitigation(self) -> None:
		sideEffect = Implication("I1", "The budget rises.")
		mitigation = Mitigation("M1", "Order a second shuttle run.", [sideEffect])

		self.assertEqual("M1", mitigation.ID)
		self.assertEqual("Order a second shuttle run.", mitigation.Description)
		self.assertEqual({"I1": sideEffect}, mitigation.Implications)
		self.assertEqual("<Mitigation M1: 1 implications>", repr(mitigation))

	def test_References_ParameterChecks(self) -> None:
		implication = Implication("I1", "The tape-out is delayed.")
		mitigation =  Mitigation("M1", "Order a second shuttle run.")

		for implications, mitigations, exception, message in (
			(1,                          None,                     TypeError,  "Parameter 'implications' is not iterable."),
			(None,                       1,                        TypeError,  "Parameter 'mitigations' is not iterable."),
			(
				implication, None,
				TypeError, "Parameter 'implications' is a single element, not an iterable of elements."
			),
			(
				None, mitigation,
				TypeError, "Parameter 'mitigations' is a single element, not an iterable of elements."
			),
			(
				[implication, implication], None,
				ValueError, "Parameter 'implications' contains implication 'I1' twice."
			),
			(
				None, [mitigation, mitigation],
				ValueError, "Parameter 'mitigations' contains mitigation 'M1' twice."
			),
			(
				[mitigation], None,
				TypeError, "Parameter 'implications' contains an element not of type 'Implication'."
			),
			(
				None, [implication],
				TypeError, "Parameter 'mitigations' contains an element not of type 'Mitigation'."
			),
		):
			with self.subTest(message=message):
				with self.assertRaises(exception) as context:
					_ = Implication("I2", "The product launch is delayed.", implications, mitigations)
				self.assertEqual(message, str(context.exception))

	def test_AddReferences(self) -> None:
		implication = Implication("I1", "The tape-out is delayed.")
		mitigation =  Mitigation("M1", "Order a second shuttle run.")
		risk =        Risk("R1", "Late silicon", "The foundry delays the wafers.", Probability.Medium, Impact.High)

		risk.AddImplication(implication)
		risk.AddMitigation(mitigation)
		self.assertEqual({"I1": implication}, risk.Implications)
		self.assertEqual({"M1": mitigation}, risk.Mitigations)

		for method, value, exception, message in (
			(risk.AddImplication, None,        ValueError, "Parameter 'implication' is None."),
			(risk.AddImplication, mitigation,  TypeError,  "Parameter 'implication' is not of type 'Implication'."),
			(risk.AddImplication, implication, ValueError, "Element already has implication 'I1'."),
			(risk.AddMitigation,  None,        ValueError, "Parameter 'mitigation' is None."),
			(risk.AddMitigation,  implication, TypeError,  "Parameter 'mitigation' is not of type 'Mitigation'."),
			(risk.AddMitigation,  mitigation,  ValueError, "Element already has mitigation 'M1'."),
		):
			with self.subTest(message=message):
				with self.assertRaises(exception) as context:
					method(value)
				self.assertEqual(message, str(context.exception))


class Register(Testcase):
	def test_Register(self) -> None:
		"""An implication and a mitigation are shared by two risks; the implications form a chain."""
		register = RiskManagement(VERSION)
		budget =   Implication("I3", "The budget rises.", parent=register)
		shuttle =  Mitigation("M1", "Order a second shuttle run.", [budget], parent=register)
		launch =   Implication("I2", "The product launch is delayed.", parent=register)
		tapeOut =  Implication("I1", "The tape-out is delayed.", [launch], [shuttle], parent=register)
		foundry =  Risk("R1", "Late silicon", "The foundry is late.", Probability.Medium, Impact.High, parent=register)
		tools =    Risk("R2", "Tool license", "A license expires.", Probability.Low, Impact.Medium, parent=register)
		foundry.AddImplication(tapeOut)
		foundry.AddMitigation(shuttle)
		tools.AddImplication(tapeOut)

		self.assertIs(register, foundry.Parent)
		self.assertIs(register, foundry.Root)
		self.assertIs(register, budget.Root)
		self.assertEqual({"R1": foundry, "R2": tools}, register.Risks)
		self.assertEqual({"I3": budget, "I2": launch, "I1": tapeOut}, register.Implications)
		self.assertEqual({"M1": shuttle}, register.Mitigations)
		self.assertIs(foundry.Implications["I1"], tools.Implications["I1"])
		self.assertEqual({"I2": launch, "I3": budget}, foundry.SecondOrderImplications)
		self.assertEqual({"I2": launch}, tools.SecondOrderImplications)
		self.assertEqual({"I3": budget}, foundry.Mitigations["M1"].Implications)
		self.assertEqual([foundry, tools], list(register.IterateRisks()))
		self.assertEqual([budget, launch, tapeOut], list(register.IterateImplications()))
		self.assertEqual([shuttle], list(register.IterateMitigations()))
		self.assertEqual("<RiskManagement 1.0.0: 2 risks, 3 implications, 1 mitigations>", repr(register))

	def test_Iterate(self) -> None:
		register = RiskManagement(VERSION)
		budget =   Implication("I1", "The budget rises.", parent=register)
		launch =   Implication("I2", "The product launch is delayed.", [budget], parent=register)
		shuttle =  Mitigation("M1", "Order a second shuttle run.", [budget], parent=register)
		staff =    Mitigation("M2", "Hire a contractor.", parent=register)
		foundry =  Risk("R1", "Late silicon", "The foundry is late.", Probability.High, Impact.High, parent=register)
		tools =    Risk("R2", "Tool license", "A license expires.", Probability.Low, Impact.Low, parent=register)
		tools.State = RiskState.Closed

		self.assertEqual([foundry, tools], list(register.IterateRisks()))
		self.assertEqual([tools], list(register.IterateRisks(lambda risk: risk.State is RiskState.Closed)))
		self.assertEqual([budget, launch], list(register.IterateImplications()))
		self.assertEqual([launch], list(register.IterateImplications(lambda item: len(item.Implications) > 0)))
		self.assertEqual([shuttle, staff], list(register.IterateMitigations()))
		self.assertEqual([shuttle], list(register.IterateMitigations(lambda item: "I1" in item.Implications)))

	def test_Duplicate(self) -> None:
		register = RiskManagement(VERSION)
		Risk("R1", "Late silicon", "The foundry is late.", Probability.High, Impact.High, parent=register)
		Implication("I1", "The tape-out is delayed.", parent=register)
		Mitigation("M1", "Order a second shuttle run.", parent=register)

		with self.assertRaises(ValueError) as context:
			_ = Risk("R1", "Tool license", "A license expires.", Probability.Low, Impact.Low, parent=register)
		self.assertEqual("Risk 'R1' already exists in the risk register.", str(context.exception))

		with self.assertRaises(ValueError) as context:
			_ = Implication("I1", "The budget rises.", parent=register)
		self.assertEqual("Implication 'I1' already exists in the risk register.", str(context.exception))

		with self.assertRaises(ValueError) as context:
			_ = Mitigation("M1", "Hire a contractor.", parent=register)
		self.assertEqual("Mitigation 'M1' already exists in the risk register.", str(context.exception))

		self.assertEqual("Late silicon", register.Risks["R1"].Title)
		self.assertEqual("The tape-out is delayed.", register.Implications["I1"].Description)
		self.assertEqual("Order a second shuttle run.", register.Mitigations["M1"].Description)

	def test_ForeignReferences(self) -> None:
		"""An element of a risk register references only implications and mitigations of the same register."""
		register =    RiskManagement(VERSION)
		implication = Implication("I1", "The tape-out is delayed.")
		mitigation =  Mitigation("M1", "Order a second shuttle run.", parent=RiskManagement(VERSION))

		with self.assertRaises(ValueError) as context:
			_ = Implication("I2", "The launch is delayed.", [implication], parent=register)
		self.assertEqual(
			"Parameter 'implications' contains an implication outside the element's risk register.",
			str(context.exception)
		)
		self.assertEqual(
			["Got implication 'I1'.", "Add the implication to the risk register first."],
			context.exception.__notes__
		)

		with self.assertRaises(ValueError) as context:
			_ = Implication("I2", "The launch is delayed.", mitigations=[mitigation], parent=register)
		self.assertEqual(
			"Parameter 'mitigations' contains a mitigation outside the element's risk register.",
			str(context.exception)
		)

		risk = Risk("R1", "Late silicon", "The foundry is late.", Probability.High, Impact.High, parent=register)
		with self.assertRaises(ValueError) as context:
			risk.AddImplication(implication)
		self.assertEqual("Parameter 'implication' is outside the element's risk register.", str(context.exception))

		with self.assertRaises(ValueError) as context:
			risk.AddMitigation(mitigation)
		self.assertEqual("Parameter 'mitigation' is outside the element's risk register.", str(context.exception))

		self.assertEqual({}, register.Implications)
		self.assertEqual({}, risk.Implications)
		self.assertEqual({}, risk.Mitigations)

	def test_Parent(self) -> None:
		"""Elements built without a register join it by assigning the parent; referenced elements join first."""
		register =    RiskManagement(VERSION)
		mitigation =  Mitigation("M1", "Order a second shuttle run.")
		implication = Implication("I1", "The tape-out is delayed.", mitigations=[mitigation])
		risk =        Risk("R1", "Late silicon", "The foundry is late.", Probability.High, Impact.High)
		risk.AddImplication(implication)

		with self.assertRaises(ValueError) as context:
			risk.Parent = register
		self.assertEqual("Risk 'R1' references an implication outside the risk register.", str(context.exception))
		self.assertEqual(
			["Got implication 'I1'.", "Add the implication to the risk register first."],
			context.exception.__notes__
		)

		with self.assertRaises(ValueError) as context:
			implication.Parent = register
		self.assertEqual("Implication 'I1' references a mitigation outside the risk register.", str(context.exception))
		self.assertIsNone(risk.Parent)
		self.assertIsNone(implication.Root)

		mitigation.Parent =  register
		implication.Parent = register
		risk.Parent =        register

		self.assertIs(register, risk.Parent)
		self.assertIs(register, risk.Root)
		self.assertEqual({"R1": risk}, register.Risks)
		self.assertEqual({"I1": implication}, register.Implications)
		self.assertEqual({"M1": mitigation}, register.Mitigations)

		for parent, exception, message in (
			(None,        ValueError, "Parameter 'parent' is None."),
			(implication, TypeError,  "Parameter 'parent' is not of type 'RiskManagement'."),
			(register,    ValueError, "Element is already part of a risk register."),
		):
			with self.subTest(message=message):
				with self.assertRaises(exception) as context:
					risk.Parent = parent
				self.assertEqual(message, str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = Mitigation("M2", "Hire a contractor.", parent=risk)
		self.assertEqual("Parameter 'parent' is not of type 'RiskManagement'.", str(context.exception))
		self.assertEqual(["Got type 'pyEDAA.Reports.RiskManagement.Risk'."], context.exception.__notes__)

		other = Risk("R1", "Tool license", "A license expires.", Probability.Low, Impact.Low)
		with self.assertRaises(ValueError) as context:
			other.Parent = register
		self.assertEqual("Risk 'R1' already exists in the risk register.", str(context.exception))
		self.assertIsNone(other.Parent)
