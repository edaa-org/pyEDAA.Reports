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
The command ``coverage``, driven through the command line: read a report of each format, show its figures, write
Cobertura XML.
"""
from pathlib   import Path
from typing    import ClassVar

from lxml.etree        import XMLSchema, parse
from pyTooling.Common  import getResourceFile
from pyTooling.Testing import ApplicationTestcase

from pyEDAA.Reports                        import Resources
from pyEDAA.Reports.CodeCoverage.Cobertura import STRICT_SCHEMA, Document as CoberturaDocument


OUTPUT_DIRECTORY = Path("tests/output/AppCoverage")
DATA_DIRECTORY =   Path("tests/data/CodeCoverage")


class CoverageCommand(ApplicationTestcase):
	"""Read each supported format, show the figures and write Cobertura XML."""

	_consoleScript:  ClassVar[str] = "pyedaa-reports"
	_runnableModule: ClassVar[str] = "pyEDAA.Reports.CLI"

	def test_Read(self) -> None:
		"""Each format shows the line figures of its fixture."""
		for formatName, file, expected in (
			("Any-Cobertura",        DATA_DIRECTORY / "Go-Test/cobertura.xml",      "Lines:    20 of 28 covered (71.4%)"),
			("CoveragePy-Cobertura", DATA_DIRECTORY / "Python/coverage.xml",        "Lines:    22 of 27 covered (81.5%)"),
			("CoveragePy-JSON",      DATA_DIRECTORY / "Python/coverage.json",       "Lines:    22 of 27 covered (81.5%)"),
			("Gcov-JSON",            DATA_DIRECTORY / "GCC/Main.gcov.json.gz",      "Lines:    26 of 27 covered (96.3%)"),
			("GHDL-JSON",            DATA_DIRECTORY / "VHDL/coverage-Count.json",   "Lines:    23 of 27 covered (85.2%)"),
			("JaCoCo-XML",           DATA_DIRECTORY / "Java/jacocoTestReport.xml",  "Lines:    6 of 8 covered (75.0%)"),
			("LCOV",                 DATA_DIRECTORY / "lcov/VHDL/GHDL.info",        "Lines:    9 of 11 covered (81.8%)"),
			("NVC-Cobertura",        DATA_DIRECTORY / "NVC/Count.xml",              "Lines:    24 of 32 covered (75.0%)")
		):
			with self.subTest(format=formatName):
				result = self.RunEntrypoint("coverage", f"--input={formatName}:{file}", timeout=60.0)

				self.assertExitCode(result)
				self.assertIn(expected, result.stdout)

	def test_ToCobertura(self) -> None:
		"""coverage.py's JSON report written as Cobertura XML: valid by the strict schema, the same figures read back."""
		OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
		outputFile = OUTPUT_DIRECTORY / "coveragepy.xml"
		outputFile.unlink(missing_ok=True)

		inputFile = DATA_DIRECTORY / "Python/coverage.json"
		result = self.RunEntrypoint(
			"coverage", f"--input=CoveragePy-JSON:{inputFile}", f"--output=Cobertura:{outputFile}", timeout=60.0
		)

		self.assertExitCode(result)
		strict = XMLSchema(parse(getResourceFile(Resources, STRICT_SCHEMA)))
		self.assertTrue(strict.validate(parse(outputFile)), msg=str(strict.error_log))

		summary = CoberturaDocument(outputFile, analyzeAndConvert=True).ToCoverageSummary()
		self.assertEqual((27, 22), (summary.TotalLines, summary.CoveredLines))
		self.assertEqual((10, 5), (summary.TotalBranches, summary.CoveredBranches))

	def test_JaCoCoToCobertura(self) -> None:
		"""Gradle's JaCoCo XML report written as Cobertura XML: valid by the strict schema, the same figures read back."""
		OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
		outputFile = OUTPUT_DIRECTORY / "jacoco.xml"
		outputFile.unlink(missing_ok=True)

		inputFile = DATA_DIRECTORY / "Java/jacocoTestReport.xml"
		result = self.RunEntrypoint(
			"coverage", f"--input=JaCoCo-XML:{inputFile}", f"--output=Cobertura:{outputFile}", timeout=60.0
		)

		self.assertExitCode(result)
		strict = XMLSchema(parse(getResourceFile(Resources, STRICT_SCHEMA)))
		self.assertTrue(strict.validate(parse(outputFile)), msg=str(strict.error_log))

		summary = CoberturaDocument(outputFile, analyzeAndConvert=True).ToCoverageSummary()
		self.assertEqual((8, 6), (summary.TotalLines, summary.CoveredLines))
		self.assertEqual((2, 1), (summary.TotalBranches, summary.CoveredBranches))

	def test_MissingInput(self) -> None:
		result = self.RunEntrypoint("coverage", timeout=60.0)

		self.assertExitCode(result, 3)
		self.assertIn("Option '--input=[<Format>:]<File>' is missing.", result.stdout)

	def test_UnsupportedInputFormat(self) -> None:
		result = self.RunEntrypoint("coverage", "--input=Foo:coverage.xml", timeout=60.0)

		self.assertExitCode(result, 1)
		self.assertIn("Unsupported code coverage format for input: 'Foo:coverage.xml'.", result.stdout)
		self.assertIn("Supported formats: Any-Cobertura, CoveragePy-Cobertura", result.stdout)
		self.assertIn("without format: Any-Cobertura.", result.stdout)

	def test_FormatNamesAreCaseSensitive(self) -> None:
		"""The formats are spelled as the documentation names them."""
		inputFile = DATA_DIRECTORY / "GCC/Main.gcov.json.gz"
		result = self.RunEntrypoint("coverage", f"--input=gcov-json:{inputFile}", timeout=60.0)

		self.assertExitCode(result, 1)
		self.assertIn("Unsupported code coverage format for input", result.stdout)

	def test_DefaultFormats(self) -> None:
		"""A file without format is read as Cobertura XML of any tool, and written as Cobertura XML."""
		OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
		outputFile = OUTPUT_DIRECTORY / "default.xml"
		outputFile.unlink(missing_ok=True)

		result = self.RunEntrypoint(
			"coverage", f"--input={DATA_DIRECTORY / 'Go-Test/cobertura.xml'}", f"--output={outputFile}", timeout=60.0
		)

		self.assertExitCode(result)
		self.assertIn("(Any-Cobertura)", result.stdout)
		self.assertIn("Lines:    20 of 28 covered (71.4%)", result.stdout)
		self.assertTrue(outputFile.exists())

	def test_MissingFile(self) -> None:
		result = self.RunEntrypoint("coverage", f"--input=Gcov-JSON:{OUTPUT_DIRECTORY / 'missing.json'}", timeout=60.0)

		self.assertExitCode(result, 1)
		self.assertIn("does not exist", result.stdout)

	def test_UnsupportedOutputFormat(self) -> None:
		result = self.RunEntrypoint(
			"coverage", f"--input=GHDL-JSON:{DATA_DIRECTORY / 'VHDL/coverage-Count.json'}", "--output=LCOV:coverage.info",
			timeout=60.0
		)

		self.assertNotEqual(0, result.returncode)
		self.assertIn("Unsupported code coverage format for output: 'LCOV:coverage.info'.", result.stdout)
		self.assertIn("Supported formats: Cobertura; without format: Cobertura.", result.stdout)
