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
# Copyright 2021-2026 Electronic Design Automation Abstraction (EDA²)                                                  #
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
Unit tests of the Cobertura XML format: its model, its schemas, the conversion to the common model and from it, and
writing a report.
"""
from pathlib                               import Path
from tempfile                              import TemporaryDirectory

from lxml.etree                            import XMLSchema, parse
from pyTooling.Common                      import getResourceFile

from pyEDAA.Reports                        import Resources
from pyEDAA.Reports.CodeCoverage           import Branch, Class, CodeCoverageError, CoverageSummary, Function
from pyEDAA.Reports.CodeCoverage           import Line as cc_Line, LineCoverageStatus, Method, Module, Package
from pyEDAA.Reports.CodeCoverage.Cobertura import READ_SCHEMA, STRICT_SCHEMA, Document, Line
from pyTooling.Testing                     import Testcase


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


DATA = Path(__file__).parent.parent.parent / "data" / "CodeCoverage"  #: Directory of the reports and their sources.


def _write(directory: str, content: str) -> Path:
	"""
	Write a report file into a directory.

	:param directory: The directory.
	:param content:   The report's content.
	:returns:         The report file.
	"""
	xmlFile = Path(directory) / "coverage.xml"
	xmlFile.write_text(content, encoding="utf-8")
	return xmlFile


class FormatModel(Testcase):
	"""The format's model keeps what the report states: figures, packages, classes, methods, lines, conditions."""

	def test_VHDL(self) -> None:
		report = Document(DATA / "VHDL" / "Cobertura.xml", analyzeAndConvert=True)

		self.assertEqual("gcovr 8.4", report.Version)
		self.assertEqual("1791360000", report.Timestamp)
		self.assertEqual(
			(16, 12, 12, 8), (report.LinesValid, report.LinesCovered, report.BranchesValid, report.BranchesCovered)
		)
		self.assertEqual((0.75, 0.6667, 0.0), (report.LineRate, report.BranchRate, report.Complexity))
		self.assertEqual(["."], report.Sources)
		self.assertEqual(["src", "src.Utilities"], [package.Name for package in report.Packages])

		counter = report.Packages[0].Classes[0]
		self.assertEqual(
			("Counter_vhdl", "src/Counter.vhdl", 0.875, 0.75),
			(counter.Name, counter.Filename, counter.LineRate, counter.BranchRate)
		)
		line = counter.Lines[26]
		self.assertEqual((1024, True, (1, 2)), (line.Hits, line.Branch, line.ConditionCoverage))
		self.assertEqual(
			[(0, "jump", "50%")], [(condition.Number, condition.Type, condition.Coverage) for condition in line.Conditions]
		)
		self.assertGreaterEqual(report.AnalysisDuration.total_seconds(), 0.0)

	def test_Methods(self) -> None:
		with TemporaryDirectory() as directory:
			report = Document(_write(directory,
				'<coverage><packages><package name="p"><classes><class name="A" filename="A.java"><methods>'
				'<method name="run" signature="()V"><lines><line number="3" hits="1"/></lines></method>'
				'<method name="run" signature="(I)V"><lines><line number="5" hits="0"/></lines></method>'
				'</methods><lines><line number="3" hits="1"/><line number="5" hits="0"/></lines></class>'
				'</classes></package></packages></coverage>'
			), analyzeAndConvert=True)

		methods = report.Packages[0].Classes[0].Methods
		self.assertEqual(["run", "run(I)V"], list(methods))
		self.assertEqual("()V", methods["run"].Signature)
		self.assertEqual([5], list(methods["run(I)V"].Lines))


class Conversion(Testcase):
	"""The conversion to the common model: files and lines, and packages, classes and methods as units."""

	def test_Python(self) -> None:
		"""coverage.py's report: the computed figures agree with the stated ones."""
		report = Document(DATA / "Python" / "coverage.xml", analyzeAndConvert=True)
		summary = report.ToCoverageSummary()

		self.assertEqual("coverage", summary.Name)
		self.assertEqual(["myPackage"], [str(directory) for directory in summary.SourceDirectories])
		self.assertEqual(
			["Shapes.py", "__init__.py", "Units/Length.py", "Units/__init__.py"],
			[file.Path.as_posix() for file in summary.IterateFiles()]
		)
		self.assertEqual(
			(report.LinesValid, report.LinesCovered, report.BranchesValid, report.BranchesCovered),
			(summary.TotalLines, summary.CoveredLines, summary.TotalBranches, summary.CoveredBranches)
		)

		shapes = summary.Files["Shapes.py"]
		self.assertIs(LineCoverageStatus.PartiallyCovered, shapes.Lines[7].Status)
		self.assertEqual(1, shapes.Lines[7].CoverageCount)
		self.assertEqual(
			[LineCoverageStatus.Covered, LineCoverageStatus.Uncovered], [branch.Status for branch in shapes.Lines[7].Branches]
		)
		self.assertIs(LineCoverageStatus.Uncovered, shapes.Lines[8].Status)

	def test_VHDL(self) -> None:
		"""gcovr's packages - directories joined by '.' - become nested packages holding the classes."""
		summary = Document(DATA / "VHDL" / "Cobertura.xml", analyzeAndConvert=True).ToCoverageSummary()

		self.assertEqual((16, 12, 12, 8, 2), (
			summary.TotalLines, summary.CoveredLines, summary.TotalBranches, summary.CoveredBranches, summary.PartialLines
		))
		self.assertEqual(
			["src", "src.Counter_vhdl", "src.Utilities", "src.Utilities.Functions_vhdl"],
			[unit.QualifiedName for unit in summary.IterateUnits()]
		)
		counter = summary.Units["src"].Units["Counter_vhdl"]
		self.assertIsInstance(summary.Units["src"], Package)
		self.assertIsInstance(counter, Class)
		self.assertIs(summary.Directories["src"].Files["Counter.vhdl"], counter.File)
		self.assertEqual((8, 7), (counter.TotalLines, counter.CoveredLines))
		self.assertEqual(2048, counter.File.Lines[25].CoverageCount)

	def test_MergedClasses(self) -> None:
		"""Two classes of one source file, as Java's nested classes, become one file; their lines are merged."""
		with TemporaryDirectory() as directory:
			summary = Document(_write(directory,
				'<coverage><packages><package name="p"><classes>'
				'<class name="A" filename="A.java"><methods><method name="run"><lines><line number="4" hits="0"/></lines>'
				'</method></methods><lines>'
				'<line number="3" hits="1" branch="true" condition-coverage="50% (1/2)"/><line number="4" hits="0"/>'
				'</lines></class>'
				'<class name="A$Inner" filename="A.java"><lines><line number="4" hits="2"/></lines></class>'
				'</classes></package></packages></coverage>'
			), analyzeAndConvert=True).ToCoverageSummary()

		file = summary.Files["A.java"]
		self.assertEqual([3, 4], [line.LineNumber for line in file.IterateLines()])
		self.assertEqual(2, file.Lines[4].CoverageCount)
		self.assertIs(LineCoverageStatus.Covered, file.Lines[4].Status)
		self.assertIs(LineCoverageStatus.PartiallyCovered, file.Lines[3].Status)

		method = summary.Units["p"].Units["A"].Units["run"]
		self.assertIsInstance(method, Method)
		self.assertEqual((file.Lines[4], file.Lines[4]), (method.StartLine, method.EndLine))
		klass = summary.Units["p"].Units["A"]
		self.assertEqual((file.Lines[3], file.Lines[4]), (klass.StartLine, klass.EndLine))
		self.assertEqual(["A", "A$Inner"], list(summary.Units["p"].Units))

	def test_RustLLVMCov(self) -> None:
		"""cargo-llvm-cov: a package per directory, a class per file, a method per instantiation with its first line."""
		report = Document(DATA / "Rust-Cargo" / "llvm-cov-cobertura.xml", analyzeAndConvert=True)
		klass = report.Packages[0].Classes[0]

		self.assertEqual(("src", "src.lib.rs", "src/lib.rs"), (report.Packages[0].Name, klass.Name, klass.Filename))
		# Known gap: of two '<method>'s with the same name and an empty signature, the second replaces the first.
		self.assertEqual(22, len(parse(DATA / "Rust-Cargo" / "llvm-cov-cobertura.xml").findall(".//method")))
		self.assertEqual(16, len(klass.Methods))
		tryDecrement = klass.Methods["<counter::Counter>::try_decrement"]
		self.assertEqual({42: 5}, {number: line.Hits for number, line in tryDecrement.Lines.items()})

		summary = report.ToCoverageSummary()
		file = summary.Directories["src"].Files["lib.rs"]
		self.assertEqual((69, 58, 0), (summary.TotalLines, summary.CoveredLines, summary.TotalBranches))
		self.assertEqual(11, file.Lines[42].CoverageCount)
		self.assertIs(LineCoverageStatus.Uncovered, file.Lines[52].Status)
		self.assertEqual(["src", "src.src.lib.rs"], [unit.QualifiedName for unit in summary.IterateUnits()][:2])

	def test_RustGrcov(self) -> None:
		"""grcov: a package per file, named by its path - split at '.', the file extension becomes a package."""
		summary = Document(DATA / "Rust-Cargo" / "grcov-cobertura.xml", analyzeAndConvert=True).ToCoverageSummary()
		file = summary.Directories["src"].Files["lib.rs"]

		self.assertEqual((69, 58, 0), (summary.TotalLines, summary.CoveredLines, summary.TotalBranches))
		self.assertEqual(11, file.Lines[42].CoverageCount)
		self.assertIs(LineCoverageStatus.Uncovered, file.Lines[52].Status)
		self.assertEqual(
			["src/lib", "src/lib.rs", "src/lib.rs.lib"], [unit.QualifiedName for unit in summary.IterateUnits()][:3]
		)


class Schemas(Testcase):
	"""The lenient schema reads what tools write; the strict one is the official DTD's translation."""

	def test_Strict(self) -> None:
		"""coverage.py's extra attribute 'missing-branches' violates the DTD; gcovr's report follows it."""
		strict = XMLSchema(parse(getResourceFile(Resources, STRICT_SCHEMA)))
		lenient = XMLSchema(parse(getResourceFile(Resources, READ_SCHEMA)))

		for report, valid in ((DATA / "Python" / "coverage.xml", False), (DATA / "VHDL" / "Cobertura.xml", True)):
			with self.subTest(report=report.parent.name):
				self.assertEqual(valid, strict.validate(parse(report)))
				self.assertTrue(lenient.validate(parse(report)))

	def test_Rust(self) -> None:
		"""cargo-llvm-cov and grcov state 'complexity' on a '<method>', which the DTD doesn't declare."""
		strict = XMLSchema(parse(getResourceFile(Resources, STRICT_SCHEMA)))
		lenient = XMLSchema(parse(getResourceFile(Resources, READ_SCHEMA)))

		for report in ("llvm-cov-cobertura.xml", "grcov-cobertura.xml"):
			with self.subTest(report=report):
				self.assertTrue(lenient.validate(parse(DATA / "Rust-Cargo" / report)))
				self.assertFalse(strict.validate(parse(DATA / "Rust-Cargo" / report)))
				self.assertEqual(
					{"Element 'method', attribute 'complexity': The attribute 'complexity' is not allowed."},
					{error.message for error in strict.error_log}
				)

	def test_RootElement(self) -> None:
		with TemporaryDirectory() as directory:
			xmlFile = _write(directory, "<testsuites/>")

			with self.assertRaises(CodeCoverageError) as context:
				_ = Document(xmlFile, analyzeAndConvert=True)

		self.assertEqual(f"Root element of '{xmlFile}' is not '<coverage>'.", str(context.exception))
		self.assertEqual(["Got root element '<testsuites>'."], context.exception.__notes__)

	def test_Invalid(self) -> None:
		"""A line without hits violates the lenient schema too."""
		with TemporaryDirectory() as directory:
			xmlFile = _write(directory,
				'<coverage><packages><package name="p"><classes><class filename="a.c"><lines>'
				'<line number="1"/></lines></class></classes></package></packages></coverage>'
			)

			with self.assertRaises(CodeCoverageError) as context:
				_ = Document(xmlFile, analyzeAndConvert=True)

		self.assertEqual(f"Validation error for '{xmlFile}' using XSD schema 'Any-Cobertura.xsd'.", str(context.exception))
		self.assertEqual(1, len(context.exception.__notes__))

	def test_Missing(self) -> None:
		with self.assertRaises(CodeCoverageError) as context:
			_ = Document(DATA / "missing.xml", analyzeAndConvert=True)

		self.assertEqual(f"Cobertura report file '{DATA / 'missing.xml'}' does not exist.", str(context.exception))

	def test_NotAnalyzed(self) -> None:
		with self.assertRaises(CodeCoverageError):
			Document(DATA / "VHDL" / "Cobertura.xml").Convert()


class Writer(Testcase):
	"""The conversion from the common model, and writing a report: every written report follows the strict schema."""

	_strictSchema: XMLSchema  #: The strict schema, parsed once.

	@classmethod
	def setUpClass(cls) -> None:
		cls._strictSchema = XMLSchema(parse(getResourceFile(Resources, STRICT_SCHEMA)))

	def _assertStrict(self, xmlFile: Path) -> None:
		"""
		Assert a written report is valid according to the strict schema.

		:param xmlFile: The report file.
		"""
		self.assertTrue(self._strictSchema.validate(parse(xmlFile)), str(self._strictSchema.error_log))

	def test_RoundTrip(self) -> None:
		"""A report read, converted to the common model and back, and written states the same figures and lines."""
		for report in (DATA / "Python" / "coverage.xml", DATA / "VHDL" / "Cobertura.xml"):
			with self.subTest(report=report.parent.name), TemporaryDirectory() as directory:
				original = Document(report, analyzeAndConvert=True)
				xmlFile = Path(directory) / "Cobertura.xml"
				Document.FromCoverageSummary(xmlFile, original.ToCoverageSummary()).Write(regenerate=True)

				self._assertStrict(xmlFile)
				written = Document(xmlFile, analyzeAndConvert=True)

				self.assertEqual(original.Sources, written.Sources)
				for name in ("LineRate", "BranchRate", "LinesValid", "LinesCovered", "BranchesValid", "BranchesCovered"):
					self.assertEqual(getattr(original, name), getattr(written, name), name)

				self.assertEqual(
					[(package.Name, package.LineRate, package.BranchRate) for package in original.Packages],
					[(package.Name, package.LineRate, package.BranchRate) for package in written.Packages]
				)
				for originalPackage, writtenPackage in zip(original.Packages, written.Packages):
					for originalClass, writtenClass in zip(originalPackage.Classes, writtenPackage.Classes, strict=True):
						self.assertEqual(
							(originalClass.Name, originalClass.Filename, originalClass.LineRate, originalClass.BranchRate),
							(writtenClass.Name, writtenClass.Filename, writtenClass.LineRate, writtenClass.BranchRate)
						)
						self.assertEqual(
							[(line.Number, line.Hits, line.ConditionCoverage) for line in originalClass.Lines.values()],
							[(line.Number, line.Hits, line.ConditionCoverage) for line in writtenClass.Lines.values()]
						)

				self.assertTrue(written.Version.startswith("pyEDAA.Reports "))

	def test_Regenerate(self) -> None:
		"""A report read and generated again follows the strict schema: coverage.py's extra attribute is left out."""
		with TemporaryDirectory() as directory:
			xmlFile = Path(directory) / "Cobertura.xml"
			original = Document(DATA / "Python" / "coverage.xml", analyzeAndConvert=True)
			original.Write(xmlFile, regenerate=True)

			self._assertStrict(xmlFile)
			written = Document(xmlFile, analyzeAndConvert=True)

		self.assertEqual((original.Version, original.Timestamp), (written.Version, written.Timestamp))
		self.assertEqual((27, 22, 10, 5), (
			written.LinesValid, written.LinesCovered, written.BranchesValid, written.BranchesCovered
		))

	def test_ComputedFigures(self) -> None:
		"""The figures and rates a report doesn't state are computed from the lines."""
		with TemporaryDirectory() as directory:
			report = Document(_write(directory,
				'<coverage><packages><package name="p"><classes><class name="A" filename="A.java"><methods>'
				'<method name="run"><lines><line number="3" hits="1" branch="true" condition-coverage="50% (1/2)"/></lines>'
				'</method></methods><lines><line number="3" hits="1" branch="true" condition-coverage="50% (1/2)"/>'
				'<line number="5" hits="0"/></lines></class></classes></package></packages></coverage>'
			), analyzeAndConvert=True)
			xmlFile = Path(directory) / "Cobertura.xml"
			report.Write(xmlFile, regenerate=True)

			self._assertStrict(xmlFile)
			root = parse(xmlFile).getroot()

		self.assertEqual(
			{"line-rate": "0.5", "branch-rate": "0.5", "lines-valid": "2", "lines-covered": "1", "branches-valid": "2",
			 "branches-covered": "1", "complexity": "0", "version": "", "timestamp": ""},
			dict(root.attrib)
		)
		method = root.find("packages/package/classes/class/methods/method")
		self.assertEqual(
			("1.0", "0.5", ""), (method.attrib["line-rate"], method.attrib["branch-rate"], method.attrib["signature"])
		)

	def test_FromCoverageSummary(self) -> None:
		"""
		Modules and classes become classes, listing the lines of their innermost unit; functions and methods become methods.
		"""
		summary = CoverageSummary("handmade")
		shapes = summary.GetOrAddFile("myPackage/Shapes.py")
		lines = {number: cc_Line(number, status, count, parent=shapes) for number, status, count in (
			(1, LineCoverageStatus.Covered,          None),
			(2, LineCoverageStatus.Excluded,         None),
			(3, LineCoverageStatus.Covered,          1),
			(4, LineCoverageStatus.PartiallyCovered, None),
			(5, LineCoverageStatus.Uncovered,        None),
			(6, LineCoverageStatus.Covered,          3),
			(8, LineCoverageStatus.Covered,          None),
			(9, LineCoverageStatus.Unknown,          None)
		)}
		Branch(LineCoverageStatus.Covered, parent=lines[4])
		Branch(LineCoverageStatus.Uncovered, parent=lines[4])

		package = Package("myPackage", parent=summary)
		module = Module("Shapes", file=shapes, startLine=lines[1], endLine=lines[9], parent=package)
		circle = Class("Circle", file=shapes, startLine=lines[3], endLine=lines[6], parent=module)
		Method("Area", file=shapes, startLine=lines[4], endLine=lines[5], parent=circle)
		Function("Distance", file=shapes, startLine=lines[8], endLine=lines[9], parent=module)

		top = summary.GetOrAddFile("top.py")
		topLines = [cc_Line(number, status, count, parent=top) for number, status, count in (
			(1, LineCoverageStatus.Covered,   1),
			(2, LineCoverageStatus.Covered,   2),
			(3, LineCoverageStatus.Uncovered, 0)
		)]
		Function("main", file=top, startLine=topLines[1], endLine=topLines[2], parent=summary)

		with TemporaryDirectory() as directory:
			xmlFile = Path(directory) / "Cobertura.xml"
			report = Document.FromCoverageSummary(xmlFile, summary)
			report.Write(regenerate=True)

			self._assertStrict(xmlFile)
			written = Document(xmlFile, analyzeAndConvert=True).ToCoverageSummary()

		self.assertEqual(
			(10, 7, 2, 1), (report.LinesValid, report.LinesCovered, report.BranchesValid, report.BranchesCovered)
		)
		self.assertEqual((0.7, 0.5), (report.LineRate, report.BranchRate))
		self.assertEqual([], report.Sources)
		self.assertEqual([".", "myPackage"], [package.Name for package in report.Packages])

		klass = report.Packages[0].Classes[0]
		self.assertEqual(("top.py", "top.py"), (klass.Name, klass.Filename))
		self.assertEqual([(1, 1), (2, 2), (3, 0)], [(line.Number, line.Hits) for line in klass.Lines.values()])
		self.assertEqual({"main": [2, 3]}, {name: list(method.Lines) for name, method in klass.Methods.items()})

		shapesClass, circleClass = report.Packages[1].Classes
		self.assertEqual(("Shapes", "myPackage/Shapes.py"), (shapesClass.Name, shapesClass.Filename))
		self.assertEqual([(1, 1), (8, 1), (9, 0)], [(line.Number, line.Hits) for line in shapesClass.Lines.values()])
		self.assertEqual({"Distance": [8, 9]}, {name: list(method.Lines) for name, method in shapesClass.Methods.items()})
		self.assertEqual("Shapes.Circle", circleClass.Name)
		self.assertEqual(
			[(3, 1, None), (4, 1, (1, 2)), (5, 0, None), (6, 3, None)],
			[(line.Number, line.Hits, line.ConditionCoverage) for line in circleClass.Lines.values()]
		)
		self.assertEqual((0.75, 0.5), (circleClass.LineRate, circleClass.BranchRate))
		area = circleClass.Methods["Area"]
		self.assertEqual(([4, 5], 0.5, 0.5, None), (list(area.Lines), area.LineRate, area.BranchRate, area.Signature))

		summary.Aggregate()
		for root, excluded in ((summary, 1), (written, 0)):
			self.assertEqual((10, 7, 2, 1, excluded), (
				root.TotalLines, root.CoveredLines, root.TotalBranches, root.CoveredBranches, root.ExcludedLines
			))
		self.assertEqual(
			["myPackage", "myPackage.Shapes", "myPackage.Shapes.Distance", "myPackage.Shapes.Circle",
			 "myPackage.Shapes.Circle.Area", "top.py", "top.py.main"],
			[unit.QualifiedName for unit in written.IterateUnits()]
		)

	def test_Line(self) -> None:
		"""A line without count has one hit, if it ran."""
		for status, count, hits in (
			(LineCoverageStatus.Covered,   None, 1),
			(LineCoverageStatus.Covered,   7,    7),
			(LineCoverageStatus.Uncovered, None, 0),
			(LineCoverageStatus.Unknown,   None, 0)
		):
			with self.subTest(status=status.name, count=count):
				line = Line.FromLine(cc_Line(4, status, count))
				self.assertEqual((4, hits, False, None), (line.Number, line.Hits, line.Branch, line.ConditionCoverage))

		with self.assertRaises(ValueError) as context:
			_ = Line.FromLine(None)
		self.assertEqual("Parameter 'line' is None.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = Line.FromLine(4)
		self.assertEqual("Parameter 'line' is not of type 'Line'.", str(context.exception))
		self.assertEqual(["Got type 'int'."], context.exception.__notes__)

	def test_FromCoverageSummary_Parameters(self) -> None:
		summary = CoverageSummary("empty")
		for xmlFile, coverageSummary, exceptionType, message in (
			(None,                  summary, ValueError, "Parameter 'xmlReportFile' is None."),
			("Cobertura.xml",       summary, TypeError,  "Parameter 'xmlReportFile' is not of type 'Path'."),
			(Path("Cobertura.xml"), None,    ValueError, "Parameter 'coverageSummary' is None."),
			(Path("Cobertura.xml"), "x",     TypeError,  "Parameter 'coverageSummary' is not of type 'CoverageSummary'.")
		):
			with self.subTest(message=message):
				with self.assertRaises(exceptionType) as context:
					_ = Document.FromCoverageSummary(xmlFile, coverageSummary)
				self.assertEqual(message, str(context.exception))

	def test_Empty(self) -> None:
		"""A report without files has no packages; its rates are 1.0."""
		with TemporaryDirectory() as directory:
			xmlFile = Path(directory) / "Cobertura.xml"
			Document.FromCoverageSummary(xmlFile, CoverageSummary("empty", sourceDirectories=[Path("src")])).Write(
				regenerate=True
			)

			self._assertStrict(xmlFile)
			written = Document(xmlFile, analyzeAndConvert=True)

		self.assertEqual((1.0, 1.0, 0, []), (written.LineRate, written.BranchRate, written.LinesValid, written.Packages))
		self.assertEqual(["src"], written.Sources)

	def test_Write_Errors(self) -> None:
		with TemporaryDirectory() as directory:
			xmlFile = Path(directory) / "Cobertura.xml"
			report = Document.FromCoverageSummary(xmlFile, CoverageSummary("empty"))

			with self.assertRaises(CodeCoverageError) as context:
				report.Write()
			self.assertEqual(
				f"XML document of Cobertura report file '{xmlFile}' needs to be generated first.", str(context.exception)
			)
			self.assertEqual(
				["Call 'Document.Generate()' or 'Document.Write(..., regenerate=True)'."], context.exception.__notes__
			)

			report.Generate()
			with self.assertRaises(CodeCoverageError) as context:
				report.Generate()
			self.assertEqual(
				f"XML document of Cobertura report file '{xmlFile}' is already populated.", str(context.exception)
			)

			report.Write()
			with self.assertRaises(CodeCoverageError) as context:
				report.Write()
			self.assertEqual(f"Cobertura report file '{xmlFile}' can not be overwritten.", str(context.exception))
			self.assertIsInstance(context.exception.__cause__, FileExistsError)

			report.Write(overwrite=True)

			with self.assertRaises(CodeCoverageError) as context:
				report.Write(Path(directory) / "missing" / "Cobertura.xml")
			self.assertIsInstance(context.exception.__cause__, OSError)

		for parameters, exceptionType, message in (
			({"path": "Cobertura.xml"}, TypeError,  "Parameter 'path' is not of type 'Path'."),
			({"overwrite": None},       ValueError, "Parameter 'overwrite' is None."),
			({"overwrite": 1},          TypeError,  "Parameter 'overwrite' is not of type 'bool'."),
			({"regenerate": None},      ValueError, "Parameter 'regenerate' is None."),
			({"regenerate": "yes"},     TypeError,  "Parameter 'regenerate' is not of type 'bool'.")
		):
			with self.subTest(message=message):
				with self.assertRaises(exceptionType) as context:
					report.Write(**parameters)
				self.assertEqual(message, str(context.exception))

		for overwrite, exceptionType, message in (
			(None, ValueError, "Parameter 'overwrite' is None."),
			(1,    TypeError,  "Parameter 'overwrite' is not of type 'bool'.")
		):
			with self.subTest(message=message):
				with self.assertRaises(exceptionType) as context:
					report.Generate(overwrite)
				self.assertEqual(message, str(context.exception))
