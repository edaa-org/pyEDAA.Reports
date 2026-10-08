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
"""Unit tests documenting the support status of JaCoCo's XML code coverage report."""
from pathlib                               import Path

from lxml.etree                            import parse

from pyEDAA.Reports.CodeCoverage           import CodeCoverageError
from pyEDAA.Reports.CodeCoverage.Cobertura import Document
from pyTooling.Testing                     import Testcase


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


DATA = Path(__file__).parent.parent.parent / "data" / "CodeCoverage" / "Java"  #: Directory of the JaCoCo reports.


class StatusQuo(Testcase):
	"""JaCoCo's XML report, as Gradle's ``jacoco`` plugin writes it, has no reader yet."""

	def test_Report(self) -> None:
		"""Root element ``<report>``, a package with classes and source files, a counter per kind and level."""
		root = parse(DATA / "jacocoTestReport.xml").getroot()

		self.assertEqual("report", root.tag)
		self.assertEqual("-//JACOCO//DTD Report 1.1//EN", root.getroottree().docinfo.public_id)
		self.assertEqual(["my/pack"], [package.get("name") for package in root.iterfind("package")])
		self.assertEqual(
			["my/pack/MyClass", "my/pack/OtherClass"], [cls.get("name") for cls in root.iterfind("package/class")]
		)
		self.assertEqual(
			["MyClass.java", "OtherClass.java"],
			sorted(sourceFile.get("name") for sourceFile in root.iterfind("package/sourcefile"))
		)
		self.assertEqual(
			{"INSTRUCTION": ("9", "16"), "BRANCH": ("1", "1"), "LINE": ("2", "6"), "COMPLEXITY": ("3", "6"),
			 "METHOD": ("2", "6"), "CLASS": ("0", "2")},
			{counter.get("type"): (counter.get("missed"), counter.get("covered")) for counter in root.findall("counter")}
		)

	def test_PartiallyCoveredLine(self) -> None:
		"""A line states missed and covered instructions (``mi``, ``ci``) and branches (``mb``, ``cb``), no count."""
		root = parse(DATA / "jacocoTestReport.xml").getroot()
		line = root.find("package/sourcefile[@name='MyClass.java']/line[@nr='13']")

		self.assertEqual({"nr": "13", "mi": "3", "ci": "4", "mb": "1", "cb": "1"}, dict(line.attrib))

	def test_Cobertura(self) -> None:
		"""The Cobertura reader rejects a JaCoCo report by its root element."""
		xmlFile = DATA / "jacocoTestReport.xml"

		with self.assertRaises(CodeCoverageError) as context:
			_ = Document(xmlFile, analyzeAndConvert=True)

		self.assertEqual(f"Root element of '{xmlFile}' is not '<coverage>'.", str(context.exception))
		self.assertEqual(["Got root element '<report>'."], context.exception.__notes__)
