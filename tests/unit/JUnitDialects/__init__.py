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
"""
Behaviour that only shows up *between* JUnit dialects: reading each dialect's own output, writing it back, and
converting one dialect into another.

The reference outputs in :file:`tests/data/JUnit` are the ground truth. They were produced by the frameworks
themselves, and the XML schemas in :file:`pyEDAA/Reports/Resources` were reverse-engineered from them - so a schema
that rejects a reference file is wrong about the format, and a report this package writes that its own reader
rejects is wrong about the format too.
"""
from pathlib import Path
from typing  import Dict, List, Tuple, Type

from pyTooling.Decorators import export, readonly
from pyTooling.MetaClasses import ExtendedType
from xmlschema             import XMLSchema

from pyEDAA.Reports.Unittesting                      import TestsuiteSummary
from pyEDAA.Reports.Unittesting.JUnit                import Document as AnyJUnitDocument
from pyEDAA.Reports.Unittesting.JUnit.AntJUnit4      import Document as AntJUnitDocument
from pyEDAA.Reports.Unittesting.JUnit.CTestJUnit     import Document as CTestJUnitDocument
from pyEDAA.Reports.Unittesting.JUnit.GoogleTestJUnit import Document as GoogleTestJUnitDocument
from pyEDAA.Reports.Unittesting.JUnit.PyTestJUnit    import Document as PyTestJUnitDocument


DATA_DIRECTORY = Path("tests/data/JUnit")
SCHEMA_DIRECTORY = Path("pyEDAA/Reports/Resources")
OUTPUT_DIRECTORY = Path("tests/output/JUnitDialects")


@export
class Dialect(metaclass=ExtendedType, slots=True):
	"""One JUnit dialect: the document class implementing it, its schema, and the reference outputs it must read."""

	_name:           str
	_documentClass:  Type
	_schemaName:     str
	_referenceFiles: List[Path]

	def __init__(self, name: str, documentClass: Type, schemaName: str, referenceFiles: List[Path]) -> None:
		"""
		Initialize the description of a dialect.

		:param name:           Name of the dialect, as the command line spells it.
		:param documentClass:  The ``Document`` class implementing the dialect.
		:param schemaName:     Base name of the dialect's XML schema in :file:`pyEDAA/Reports/Resources`.
		:param referenceFiles: Reports the framework itself produced, which the dialect has to read.
		"""
		self._name = name
		self._documentClass = documentClass
		self._schemaName = schemaName
		self._referenceFiles = referenceFiles

	@readonly
	def Name(self) -> str:
		"""
		Read-only property to access the name of the dialect, as the command line spells it (:attr:`_name`).

		:returns: The dialect's name.
		"""
		return self._name

	@readonly
	def DocumentClass(self) -> Type:
		"""
		Read-only property to access the document class implementing this dialect (:attr:`_documentClass`).

		:returns: The ``Document`` class of the dialect.
		"""
		return self._documentClass

	@readonly
	def SchemaFile(self) -> Path:
		"""
		Read-only property to return the path of the dialect's XML schema, derived from :attr:`_schemaName`.

		:returns: Path of the ``.xsd`` file.
		"""
		return SCHEMA_DIRECTORY / f"{self._schemaName}.xsd"

	@readonly
	def ReferenceFiles(self) -> List[Path]:
		"""
		Read-only property to access the reference outputs produced by the framework itself (:attr:`_referenceFiles`).

		:returns: List of reference report paths.
		"""
		return self._referenceFiles

	def Schema(self) -> XMLSchema:
		"""
		Load the dialect's XML schema.

		:returns: The compiled schema.
		"""
		return XMLSchema(str(self.SchemaFile))

	def __str__(self) -> str:
		return self._name


DIALECTS: Dict[str, Dialect] = {
	dialect.Name: dialect for dialect in (
		Dialect(
			"Ant-JUnit4", AntJUnitDocument, "Ant-JUnit4",
			sorted((DATA_DIRECTORY / "pyEDAA.Reports/Java-Ant-JUnit4").glob("*.xml"))
		),
		Dialect(
			"CTest-JUnit", CTestJUnitDocument, "CTest-JUnit",
			[DATA_DIRECTORY / "pyEDAA.Reports/Cpp-GoogleTest/ctest.xml"]
		),
		Dialect(
			"GoogleTest-JUnit", GoogleTestJUnitDocument, "GoogleTest-JUnit",
			[DATA_DIRECTORY / "pyEDAA.Reports/Cpp-GoogleTest/gtest.xml"]
		),
		Dialect(
			"pyTest-JUnit", PyTestJUnitDocument, "PyTest-JUnit",
			[
				DATA_DIRECTORY / "pyEDAA.Reports/Python-pytest/TestReportSummary.xml",
				DATA_DIRECTORY / "pyAttributes/pytest.pyAttributes.xml",
				DATA_DIRECTORY / "pyVersioning/unittests.xml",
			]
		),
		Dialect(
			"Any-JUnit", AnyJUnitDocument, "Any-JUnit",
			[DATA_DIRECTORY / "OsvvmLibraries/OSVVMLibraries_RunAllTests.xml"]
		),
	)
}

#: Reports rooted at ``<testsuite>`` rather than ``<testsuites>``. ``Any-JUnit`` should accept them and does not,
#: which is why they are named here instead of sitting in its reference list.
TESTSUITE_ROOTED_FILES: List[Path] = sorted((DATA_DIRECTORY / "VUnit").glob("*.xml"))


def readReference(dialect: Dialect, referenceFile: Path) -> TestsuiteSummary:
	"""
	Read a reference report with its own dialect and convert it to the unified data model.

	:param dialect:       The dialect the file was produced in.
	:param referenceFile: The reference report to read.
	:returns:             The report as a test suite summary of the unified data model.
	"""
	document = dialect.DocumentClass(referenceFile, analyzeAndConvert=True)
	summary = document.ToTestsuiteSummary()
	# The metrics a writer emits are computed here, exactly as the command line does before writing.
	summary.Aggregate()

	return summary


def writeAs(dialect: Dialect, summary: TestsuiteSummary, outputFile: Path) -> Path:
	"""
	Write a test suite summary in the given dialect.

	:param dialect:    The dialect to write.
	:param summary:    The test suite summary to write.
	:param outputFile: Where to write it.
	:returns:          The path written to, so a caller can chain the validation onto it.
	"""
	outputFile.parent.mkdir(parents=True, exist_ok=True)
	dialect.DocumentClass.FromTestsuiteSummary(outputFile, summary).Write(regenerate=True, overwrite=True)

	return outputFile


def countTestcases(summary: TestsuiteSummary) -> int:
	"""
	Count the test cases in a test suite summary, at any depth.

	:param summary: The test suite summary to count in.
	:returns:       Number of test cases.
	"""
	return len(list(summary.IterateTestcases()))


def collectTestcaseNames(summary: TestsuiteSummary) -> Tuple[str, ...]:
	"""
	Collect the names of all test cases in a test suite summary, sorted, so two reports can be compared.

	:param summary: The test suite summary to collect from.
	:returns:       Tuple of sorted test case names.
	"""
	return tuple(sorted(testcase._name for testcase in summary.IterateTestcases()))
