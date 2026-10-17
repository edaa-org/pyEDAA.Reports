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
"""
Unit tests documenting what pyEDAA.Reports makes of the code coverage reports .NET tools write.

The reports in :file:`tests/data/CodeCoverage/CSharp-xUnit` are written by coverlet (Cobertura, lcov, OpenCover, JSON),
by Microsoft's code coverage collector (Cobertura) and by ReportGenerator (Cobertura and lcov, converted from coverlet's
Cobertura report) for the example :file:`examples/CSharp/xUnit`.
"""
from json                                  import loads
from pathlib                               import Path, PurePosixPath

from lxml.etree                            import XMLSchema, parse
from pyTooling.Common                      import getResourceFile

from pyEDAA.Reports                        import Resources
from pyEDAA.Reports.CodeCoverage           import Class, CodeCoverageError
from pyEDAA.Reports.CodeCoverage.Cobertura import READ_SCHEMA, STRICT_SCHEMA, Document
from pyTooling.Testing                     import Testcase


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


DATA = Path(__file__).parent.parent.parent / "data" / "CodeCoverage" / "CSharp-xUnit"  #: Directory of the reports.

#: Schema violation of a capitalized boolean ``True``.
BRANCH_TRUE =         "Element 'line', attribute 'branch': 'True' is not a valid value of the atomic type 'xs:boolean'."
#: Schema violation of a capitalized boolean ``False``.
BRANCH_FALSE =        BRANCH_TRUE.replace("'True'", "'False'")
#: Violation of ``coverage-04.dtd`` by attribute ``complexity`` on ``<method>``.
METHOD_COMPLEXITY =   "Element 'method', attribute 'complexity': The attribute 'complexity' is not allowed."
#: Violation of ``coverage-04.dtd`` by a missing attribute ``complexity`` on ``<coverage>``.
COVERAGE_COMPLEXITY = "Element 'coverage': The attribute 'complexity' is required but missing."


def _schemaErrors(schemaName: str, xmlFile: Path) -> set[str]:
	"""
	Validate a report against an XML schema of the package's resources.

	:param schemaName: File name of the XML schema.
	:param xmlFile:    The report to validate.
	:returns:          The messages of all violations, each once.
	"""
	schema = XMLSchema(parse(getResourceFile(Resources, schemaName)))
	schema.validate(parse(xmlFile))

	return {entry.message for entry in schema.error_log}


def _lcovRecords(tracefile: Path) -> dict[str, list[str]]:
	"""
	Split an lcov tracefile into its records.

	:param tracefile: The lcov tracefile.
	:returns:         The lines of each record between ``SF:`` and ``end_of_record``, by the source file's name.
	"""
	records = {}
	for line in tracefile.read_text().splitlines():
		if line.startswith("SF:"):
			records[Path(line[3:]).name] = record = []
		elif line != "end_of_record" and len(records) > 0:
			record.append(line)

	return records


class CoverletCobertura(Testcase):
	"""coverlet's Cobertura report: no dialect reads it, because attribute ``branch`` is ``True`` or ``False``."""

	xmlFile = DATA / "coverlet" / "coverage.cobertura.xml"  #: coverlet's Cobertura report.

	def test_Schemas(self) -> None:
		"""Both schemas reject the capitalized booleans; the DTD also misses ``complexity`` on ``<coverage>``."""
		self.assertEqual({BRANCH_FALSE, BRANCH_TRUE}, _schemaErrors(READ_SCHEMA, self.xmlFile))
		self.assertEqual(
			{BRANCH_FALSE, BRANCH_TRUE, COVERAGE_COMPLEXITY, METHOD_COMPLEXITY},
			_schemaErrors(STRICT_SCHEMA, self.xmlFile)
		)

	def test_Read(self) -> None:
		with self.assertRaises(CodeCoverageError) as context:
			_ = Document(self.xmlFile, analyzeAndConvert=True)

		self.assertEqual(
			f"Validation error for '{self.xmlFile}' using XSD schema 'Any-Cobertura.xsd'.", str(context.exception)
		)
		self.assertIn(BRANCH_FALSE, context.exception.__notes__[0])

	def test_Report(self) -> None:
		"""File names relative to one ``<source>``, counts, ``/`` before a nested class, IL offsets as condition numbers."""
		root = parse(self.xmlFile).getroot()

		self.assertEqual("1.9", root.get("version"))
		self.assertEqual(1, len(root.findall("sources/source")))
		self.assertTrue(root.findtext("sources/source").endswith("/examples/CSharp/xUnit/src/MyLibrary/"))
		self.assertEqual(
			[
				("MyLibrary.Calculator",                  "Calculator.cs"),
				("MyLibrary.Counter",                     "Counter.cs"),
				("MyLibrary.Counter/<IncrementAsync>d__6", "Counter.cs"),
			],
			[(klass.get("name"), klass.get("filename")) for klass in root.iterfind("packages/package/classes/class")]
		)
		self.assertEqual({"0", "1", "2", "3", "4", "13"}, {line.get("hits") for line in root.iter("line")})

		line = root.find("packages/package/classes/class[@name='MyLibrary.Counter']/lines/line[@number='11']")
		self.assertEqual(
			{"number": "11", "hits": "1", "branch": "True", "condition-coverage": "50% (1/2)"}, dict(line.attrib)
		)
		self.assertEqual(
			[{"number": "12", "type": "jump", "coverage": "50%"}],
			[dict(condition.attrib) for condition in line.iterfind("conditions/condition")]
		)


class MicrosoftCobertura(Testcase):
	"""Microsoft's Cobertura report: no dialect reads it, because attribute ``branch`` is ``True`` or ``False``."""

	xmlFile = DATA / "Microsoft.CodeCoverage" / "coverage.cobertura.xml"  #: Microsoft's Cobertura report.

	def test_Schemas(self) -> None:
		self.assertEqual({BRANCH_FALSE, BRANCH_TRUE}, _schemaErrors(READ_SCHEMA, self.xmlFile))
		self.assertEqual({BRANCH_FALSE, BRANCH_TRUE, METHOD_COMPLEXITY}, _schemaErrors(STRICT_SCHEMA, self.xmlFile))

	def test_Read(self) -> None:
		with self.assertRaises(CodeCoverageError) as context:
			_ = Document(self.xmlFile, analyzeAndConvert=True)

		self.assertEqual(
			f"Validation error for '{self.xmlFile}' using XSD schema 'Any-Cobertura.xsd'.", str(context.exception)
		)
		self.assertIn(BRANCH_FALSE, context.exception.__notes__[0])

	def test_Report(self) -> None:
		"""No ``<sources>``, absolute file names, the test assembly, ``hits`` ``0`` or ``1``, nested classes after ``.``."""
		root = parse(self.xmlFile).getroot()

		self.assertIsNone(root.find("sources"))
		self.assertEqual(
			{"MyLibrary", "MyLibrary.Tests"}, {package.get("name") for package in root.iterfind("packages/package")}
		)
		self.assertTrue(all(PurePosixPath(klass.get("filename")).is_absolute() for klass in root.iter("class")))
		self.assertEqual(
			[
				"MyLibrary.Calculator",
				"MyLibrary.Calculator.<>c",
				"MyLibrary.Counter",
				"MyLibrary.Counter.<IncrementAsync>d__6",
			],
			sorted(klass.get("name") for klass in root.iterfind("packages/package[@name='MyLibrary']/classes/class"))
		)
		self.assertEqual({"0", "1"}, {line.get("hits") for line in root.iter("line")})
		self.assertEqual({"0"}, {condition.get("number") for condition in root.iter("condition")})
		self.assertEqual(
			"(int, int)", root.find(".//class[@name='MyLibrary.Calculator']/methods/method[@name='Add']").get("signature")
		)


class ReportGeneratorCobertura(Testcase):
	"""ReportGenerator's Cobertura report, converted from coverlet's: the generic reader reads it."""

	xmlFile = DATA / "ReportGenerator" / "Cobertura.xml"  #: ReportGenerator's Cobertura report.

	def test_Schemas(self) -> None:
		"""Only the DTD rejects it, for ``complexity`` on ``<method>``."""
		self.assertEqual(set(), _schemaErrors(READ_SCHEMA, self.xmlFile))
		self.assertEqual({METHOD_COMPLEXITY}, _schemaErrors(STRICT_SCHEMA, self.xmlFile))

	def test_Report(self) -> None:
		"""Cobertura's DOCTYPE, version ``0``, no ``<conditions>``, an async method's state machine merged into it."""
		document = parse(self.xmlFile)
		root = document.getroot()

		self.assertEqual("http://cobertura.sourceforge.net/xml/coverage-04.dtd", document.docinfo.system_url)
		self.assertEqual("0", root.get("version"))
		self.assertEqual([], root.findall(".//conditions"))
		self.assertEqual(
			["MyLibrary.Calculator", "MyLibrary.Counter"],
			[klass.get("name") for klass in root.iterfind("packages/package/classes/class")]
		)
		self.assertIsNotNone(root.find(".//class[@name='MyLibrary.Counter']/methods/method[@name='IncrementAsync']"))

	def test_Read(self) -> None:
		"""An absolute file name is a path below the summary; a class unit's name repeats its package's."""
		report = Document(self.xmlFile, analyzeAndConvert=True)

		self.assertEqual(21, report.LinesCovered)
		self.assertEqual(24, report.LinesValid)

		summary = report.ToCoverageSummary()
		root = parse(self.xmlFile).getroot()

		self.assertEqual(
			[Path(klass.get("filename")).relative_to("/") for klass in root.iterfind("packages/package/classes/class")],
			[file.Path for file in summary.IterateFiles()]
		)
		self.assertEqual(
			["MyLibrary.MyLibrary.Calculator", "MyLibrary.MyLibrary.Counter"],
			[unit.QualifiedName for unit in summary.IterateUnits() if isinstance(unit, Class)]
		)
		self.assertEqual([1.0, 11 / 14], [file.LineCoverage for file in summary.IterateFiles()])


class CoverletLcov(Testcase):
	"""coverlet's lcov tracefile, in the format before lcov 2.2 (``FN``/``FNDA``)."""

	tracefile = DATA / "coverlet" / "coverage.info"  #: coverlet's lcov tracefile.

	def test_Functions(self) -> None:
		"""A function is named by its IL signature, commas included; ``FN`` states the line before its first line."""
		records = _lcovRecords(self.tracefile)

		self.assertFalse(self.tracefile.read_text().startswith("TN:"))
		self.assertEqual(
			[
				"FN:4,System.Int32 MyLibrary.Calculator::Add(System.Int32,System.Int32)",
				"FNDA:1,System.Int32 MyLibrary.Calculator::Add(System.Int32,System.Int32)",
				"DA:5,1",
			],
			records["Calculator.cs"][0:3]
		)

	def test_Branches(self) -> None:
		"""A branch's block is the IL offset of its instruction; ``taken`` counts."""
		records = _lcovRecords(self.tracefile)

		self.assertEqual(
			["BRDA:11,7,0,2", "BRDA:11,7,1,1"], [line for line in records["Calculator.cs"] if line.startswith("BRDA:")]
		)
		self.assertEqual(
			["BRDA:11,12,0,0", "BRDA:11,12,1,1", "BRDA:21,36,0,1", "BRDA:21,36,1,1"],
			[line for line in records["Counter.cs"] if line.startswith("BRDA:")]
		)

	def test_Lines(self) -> None:
		"""Lines follow their function; a state machine's lines follow the lines of the class, not in ascending order."""
		records = _lcovRecords(self.tracefile)

		self.assertEqual(
			[5, 7, 10, 11, 12, 13, 16, 17, 26, 20, 21, 22, 23, 24],
			[int(line[3:].split(",")[0]) for line in records["Counter.cs"] if line.startswith("DA:")]
		)
		self.assertIn("FN:19,System.Void MyLibrary.Counter/<IncrementAsync>d__6::MoveNext()", records["Counter.cs"])


class ReportGeneratorLcov(Testcase):
	"""ReportGenerator's lcov tracefile, converted from coverlet's Cobertura report."""

	tracefile = DATA / "ReportGenerator" / "lcov.info"  #: ReportGenerator's lcov tracefile.

	def test_Functions(self) -> None:
		"""A function is named by its method name and parameter types; ``FN`` states its first line."""
		records = _lcovRecords(self.tracefile)

		self.assertTrue(self.tracefile.read_text().startswith("TN:\n"))
		self.assertEqual("FN:5,Add(System.Int32,System.Int32)", records["Calculator.cs"][0])
		self.assertIn("FN:20,IncrementAsync()", records["Counter.cs"])

	def test_Branches(self) -> None:
		"""A branch's block is its line number, branches are numbered per file, ``taken`` is ``1`` or ``-``."""
		records = _lcovRecords(self.tracefile)

		self.assertEqual(
			["BRDA:11,11,0,1", "BRDA:11,11,1,1"], [line for line in records["Calculator.cs"] if line.startswith("BRDA:")]
		)
		self.assertEqual(
			["BRDA:11,11,2,1", "BRDA:11,11,3,-", "BRDA:21,21,4,1", "BRDA:21,21,5,1"],
			[line for line in records["Counter.cs"] if line.startswith("BRDA:")]
		)


class CoverletOpenCover(Testcase):
	"""coverlet's OpenCover report has no reader yet."""

	xmlFile = DATA / "coverlet" / "coverage.opencover.xml"  #: coverlet's OpenCover report.

	def test_Report(self) -> None:
		"""Root ``<CoverageSession>``, a summary per level, sequence and branch points per method."""
		root = parse(self.xmlFile).getroot()

		self.assertEqual("CoverageSession", root.tag)
		self.assertEqual(
			{"numSequencePoints": "24", "visitedSequencePoints": "21", "numBranchPoints": "6", "visitedBranchPoints": "5"},
			{name: value for name, value in root.find("Summary").attrib.items() if name.endswith("Points")}
		)
		self.assertEqual(["MyLibrary"], [module.findtext("ModuleName") for module in root.iterfind("Modules/Module")])
		self.assertEqual(
			["Calculator.cs", "Counter.cs"],
			[Path(file.get("fullPath")).name for file in root.iterfind("Modules/Module/Files/File")]
		)

		method = root.find(".//Method[Name='System.Void MyLibrary.Counter::Decrement()']")
		self.assertEqual(
			[("0", "12", "14"), ("1", "12", "26")],
			[
				(point.get("vc"), point.get("offset"), point.get("offsetend"))
				for point in method.iterfind("BranchPoints/BranchPoint")
			]
		)

	def test_Cobertura(self) -> None:
		"""The Cobertura reader rejects an OpenCover report by its root element."""
		with self.assertRaises(CodeCoverageError) as context:
			_ = Document(self.xmlFile, analyzeAndConvert=True)

		self.assertEqual(f"Root element of '{self.xmlFile}' is not '<coverage>'.", str(context.exception))
		self.assertEqual(["Got root element '<CoverageSession>'."], context.exception.__notes__)


class CoverletJSON(Testcase):
	"""coverlet's JSON report has no reader yet."""

	def test_Report(self) -> None:
		"""Assembly, file, class and method as nested keys; per method its lines' counts and its branches."""
		report = loads((DATA / "coverlet" / "coverage.json").read_text())

		self.assertEqual(["MyLibrary.dll"], list(report))
		files = {Path(path).name: classes for path, classes in report["MyLibrary.dll"].items()}
		self.assertEqual(["Calculator.cs", "Counter.cs"], list(files))
		self.assertEqual(["MyLibrary.Counter", "MyLibrary.Counter/<IncrementAsync>d__6"], list(files["Counter.cs"]))

		method = files["Counter.cs"]["MyLibrary.Counter"]["System.Void MyLibrary.Counter::Decrement()"]
		self.assertEqual({"10": 1, "11": 1, "12": 0, "13": 0, "16": 1, "17": 1}, method["Lines"])
		self.assertEqual(
			[
				{"Line": 11, "Offset": 12, "EndOffset": 14, "Path": 0, "Ordinal": 0, "Hits": 0},
				{"Line": 11, "Offset": 12, "EndOffset": 26, "Path": 1, "Ordinal": 1, "Hits": 1},
			],
			method["Branches"]
		)
