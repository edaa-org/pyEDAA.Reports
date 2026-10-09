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
"""Unit tests of JaCoCo's XML format: its model, its XML schema and the conversion to the common model."""
from datetime                                    import datetime, timezone
from pathlib                                     import Path
from tempfile                                    import TemporaryDirectory

from lxml.etree                                  import fromstring
from pyEDAA.Reports.CodeCoverage                 import Class as cc_Class, CodeCoverageError, LineCoverageStatus
from pyEDAA.Reports.CodeCoverage                 import Method as cc_Method, Package as cc_Package, Unit
from pyEDAA.Reports.CodeCoverage.Cobertura       import Document as CoberturaDocument
from pyEDAA.Reports.CodeCoverage.JaCoCo          import Document, FormatVersion, Group, Package, PUBLIC_IDENTIFIER
from pyEDAA.Reports.CodeCoverage.JaCoCo          import SCHEMAS
from pyEDAA.Reports.CodeCoverage.JaCoCo.Classes  import Class, Line, Method, SourceFile
from pyEDAA.Reports.CodeCoverage.JaCoCo.Elements import Counter, CounterType, SessionInfo
from pyTooling.Testing                           import Testcase


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


DATA =   Path(__file__).parent.parent.parent / "data" / "CodeCoverage" / "Java"  #: Directory of the JaCoCo reports.
GRADLE = DATA / "jacocoTestReport.xml"                                          #: Report of Gradle's 'jacoco' plugin.
CLI =    DATA / "JaCoCo" / "jacoco.xml"                                         #: Report of JaCoCo's CLI.
GROUPS = DATA / "JaCoCo" / "jacoco-groups.xml"                                  #: Report with nested groups.


def _write(directory: str, content: str) -> Path:
	"""
	Write a report file into a directory.

	:param directory: The directory.
	:param content:   The report's text.
	:returns:         The report file.
	"""
	xmlFile = Path(directory) / "jacoco.xml"
	xmlFile.write_text(content, encoding="utf-8")
	return xmlFile


def _units(xmlFile: Path) -> dict[str, Unit]:
	"""
	Read a report and convert it to the common model.

	:param xmlFile: The report file.
	:returns:       The units of the common model, by qualified name.
	"""
	summary = Document(xmlFile, analyzeAndConvert=True).ToCoverageSummary()
	return {unit.QualifiedName: unit for unit in summary.IterateUnits()}


class FormatModel(Testcase):
	"""The format's model keeps what the report states: sessions, groups, packages, classes, source files, counters."""

	def test_Report(self) -> None:
		report = Document(GRADLE, analyzeAndConvert=True)

		self.assertEqual(("Gradle-JUnit4", FormatVersion.Version1_1), (report.Name, report.FormatVersion))
		session, = report.SessionInfos
		self.assertEqual("dffa20ef8728-f9da5560", session.SessionID)
		self.assertEqual(datetime(2026, 10, 8, 10, 41, 51, 841000, tzinfo=timezone.utc), session.Start)
		self.assertEqual(datetime(2026, 10, 8, 10, 41, 52, 456000, tzinfo=timezone.utc), session.Dump)
		self.assertEqual(["my/pack"], list(report.Packages))
		self.assertEqual({}, report.Groups)
		self.assertEqual(
			{"INSTRUCTION": (9, 16), "BRANCH": (1, 1), "LINE": (2, 6), "COMPLEXITY": (3, 6), "METHOD": (2, 6),
			 "CLASS": (0, 2)},
			{counter.Type.value: (counter.MissedCount, counter.CoveredCount) for counter in report.Counters.values()}
		)

	def test_Classes(self) -> None:
		package = Document(GRADLE, analyzeAndConvert=True).Packages["my/pack"]

		self.assertEqual(["my/pack/MyClass", "my/pack/OtherClass"], list(package.Classes))
		self.assertEqual(["MyClass.java", "OtherClass.java"], sorted(package.SourceFiles))
		myClass = package.Classes["my/pack/MyClass"]
		self.assertEqual("MyClass.java", myClass.SourceFileName)
		self.assertEqual(
			["<init>()V", "returnTrue()Z", "returnFalse()Z", "absolute(I)I", "divide(II)I"], list(myClass.Methods)
		)

	def test_Method(self) -> None:
		myClass = Document(GRADLE, analyzeAndConvert=True).Packages["my/pack"].Classes["my/pack/MyClass"]
		absolute = myClass.Methods["absolute(I)I"]

		self.assertEqual(("absolute", "(I)I", 13), (absolute.Name, absolute.Descriptor, absolute.LineNumber))
		branches = absolute.Counters[CounterType.Branch]
		self.assertEqual((1, 1), (branches.MissedCount, branches.CoveredCount))

	def test_PartiallyCoveredLine(self) -> None:
		"""A line states missed and covered instructions (``mi``, ``ci``) and branches (``mb``, ``cb``), no count."""
		line = Document(GRADLE, analyzeAndConvert=True).Packages["my/pack"].SourceFiles["MyClass.java"].Lines[13]

		self.assertEqual((13, 3, 4, 1, 1), (
			line.LineNumber, line.MissedInstructionCount, line.CoveredInstructionCount, line.MissedBranchCount,
			line.CoveredBranchCount
		))

	def test_Groups(self) -> None:
		"""Groups nest; a group holds groups or packages."""
		report = Document(GROUPS, analyzeAndConvert=True)

		self.assertEqual(("JaCoCo-Groups", {}), (report.Name, report.Packages))
		self.assertEqual(["Library", "Application"], list(report.Groups))
		library = report.Groups["Library"]
		self.assertEqual((["Shapes", "Utilities"], {}), (list(library.Groups), library.Packages))
		self.assertEqual(["shapes"], list(library.Groups["Shapes"].Packages))
		classes = library.Counters[CounterType.Class]
		self.assertEqual((1, 3), (classes.MissedCount, classes.CoveredCount))

	def test_NoDebugInformation(self) -> None:
		"""A class compiled without debug information names no source file, its methods no line."""
		package = Document(CLI, analyzeAndConvert=True).Packages["util"]

		numbers = package.Classes["util/Numbers"]
		self.assertEqual((None, {}), (numbers.SourceFileName, package.SourceFiles))
		self.assertIsNone(numbers.Methods["clamp(III)I"].LineNumber)
		self.assertNotIn(CounterType.Line, numbers.Counters)

	def test_DefaultPackage(self) -> None:
		package = Document(CLI, analyzeAndConvert=True).Packages[""]

		self.assertEqual(["Main"], list(package.Classes))
		self.assertEqual(["Main.java"], list(package.SourceFiles))


class Construction(Testcase):
	"""The format's model is built by hand: each constructor takes typed values and checks them."""

	def test_Line(self) -> None:
		line = Line(13, 3, 4, 1, 1)

		self.assertEqual((13, 3, 4, 1, 1), (
			line.LineNumber, line.MissedInstructionCount, line.CoveredInstructionCount, line.MissedBranchCount,
			line.CoveredBranchCount
		))

	def test_Line_Defaults(self) -> None:
		"""The DTD declares the counts of a line optional."""
		line = Line(3)

		self.assertEqual((None, None, None, None, None), (
			line.MissedInstructionCount, line.CoveredInstructionCount, line.MissedBranchCount, line.CoveredBranchCount,
			line.Parent
		))

	def test_Method(self) -> None:
		method = Method("absolute", "(I)I", 13)

		self.assertEqual(("absolute", "(I)I", 13, None, {}),
		                 (method.Name, method.Descriptor, method.LineNumber, method.Parent, method.Counters))
		self.assertIsNone(Method("clamp", "(III)I").LineNumber)

	def test_Class(self) -> None:
		klass = Class("my/pack/MyClass", "MyClass.java")

		self.assertEqual(("my/pack/MyClass", "MyClass.java", {}, None),
		                 (klass.Name, klass.SourceFileName, klass.Methods, klass.Parent))
		self.assertIsNone(Class("util/Numbers").SourceFileName)

	def test_Package(self) -> None:
		"""The default package has an empty name."""
		package = Package("")

		self.assertEqual(("", {}, {}, None), (package.Name, package.Classes, package.SourceFiles, package.Parent))

	def test_SessionInfo(self) -> None:
		start = datetime(2026, 10, 8, 10, 41, 51, tzinfo=timezone.utc)
		session = SessionInfo("host-1234", start, start)

		self.assertEqual(("host-1234", start, start, None),
		                 (session.SessionID, session.Start, session.Dump, session.Parent))

	def test_Line_LineNumber(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = Line(None)
		self.assertEqual("Parameter 'lineNumber' is None.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = Line("1")
		self.assertEqual("Parameter 'lineNumber' is not of type 'int'.", str(context.exception))
		self.assertEqual(["Got type 'str'."], context.exception.__notes__)

		with self.assertRaises(ValueError) as context:
			_ = Line(0)
		self.assertEqual("Parameter 'lineNumber' is less than 1.", str(context.exception))
		self.assertEqual(["Got value '0'."], context.exception.__notes__)

	def test_Line_Counts(self) -> None:
		with self.assertRaises(TypeError) as context:
			_ = Line(1, coveredInstructionCount="4")
		self.assertEqual("Parameter 'coveredInstructionCount' is not of type 'int'.", str(context.exception))
		self.assertEqual(["Got type 'str'."], context.exception.__notes__)

		with self.assertRaises(ValueError) as context:
			_ = Line(1, missedBranchCount=-1)
		self.assertEqual("Parameter 'missedBranchCount' is negative.", str(context.exception))
		self.assertEqual(["Got value '-1'."], context.exception.__notes__)

	def test_Method_Descriptor(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = Method("absolute", None)
		self.assertEqual("Parameter 'descriptor' is None.", str(context.exception))

		with self.assertRaises(ValueError) as context:
			_ = Method("absolute", "")
		self.assertEqual("Parameter 'descriptor' is empty.", str(context.exception))

	def test_Method_LineNumber(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = Method("absolute", "(I)I", 0)
		self.assertEqual("Parameter 'lineNumber' is less than 1.", str(context.exception))
		self.assertEqual(["Got value '0'."], context.exception.__notes__)

	def test_Name(self) -> None:
		"""The name is checked by the base-class; only a package's name may be empty."""
		with self.assertRaises(ValueError) as context:
			_ = Class(None)
		self.assertEqual("Parameter 'name' is None.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = SourceFile(Path("MyClass.java"))
		self.assertEqual("Parameter 'name' is not of type 'str'.", str(context.exception))

		for elementClass in (Group, Class, SourceFile):
			with self.subTest(elementClass=elementClass.__name__):
				with self.assertRaises(ValueError) as context:
					_ = elementClass("")
				self.assertEqual("Parameter 'name' is empty.", str(context.exception))

	def test_Class_SourceFileName(self) -> None:
		with self.assertRaises(TypeError) as context:
			_ = Class("my/pack/MyClass", Path("MyClass.java"))
		self.assertEqual("Parameter 'sourceFileName' is not of type 'str'.", str(context.exception))

	def test_Counter_Type(self) -> None:
		with self.assertRaises(TypeError) as context:
			_ = Counter("LINE", 0, 1)
		self.assertEqual("Parameter 'counterType' is not of type 'CounterType'.", str(context.exception))
		self.assertEqual(["Got type 'str'."], context.exception.__notes__)

	def test_Counter_Counts(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = Counter(CounterType.Line, None, 1)
		self.assertEqual("Parameter 'missedCount' is None.", str(context.exception))

		with self.assertRaises(ValueError) as context:
			_ = Counter(CounterType.Line, 0, -1)
		self.assertEqual("Parameter 'coveredCount' is negative.", str(context.exception))
		self.assertEqual(["Got value '-1'."], context.exception.__notes__)

	def test_SessionInfo_Start(self) -> None:
		with self.assertRaises(TypeError) as context:
			_ = SessionInfo("host-1234", 1791456111841, datetime.now(timezone.utc))
		self.assertEqual("Parameter 'start' is not of type 'datetime'.", str(context.exception))
		self.assertEqual(["Got type 'int'."], context.exception.__notes__)


class ParentRelation(Testcase):
	"""Each element below the report names its parent and is added to it."""

	def test_Report(self) -> None:
		"""A session, a group, a package and a counter are added to the report."""
		document = Document(Path("jacoco.xml"))
		session = SessionInfo("host-1234", datetime.now(timezone.utc), datetime.now(timezone.utc), parent=document)
		group =   Group("Library", parent=document)
		package = Package("my/pack", parent=document)
		counter = Counter(CounterType.Class, 0, 1, parent=document)

		self.assertEqual([document] * 4, [session.Parent, group.Parent, package.Parent, counter.Parent])
		self.assertEqual(([session], {"Library": group}, {"my/pack": package}, {CounterType.Class: counter}),
		                 (document.SessionInfos, document.Groups, document.Packages, document.Counters))

	def test_Group(self) -> None:
		library = Group("Library")
		shapes =  Group("Shapes", parent=library)
		package = Package("shapes", parent=shapes)

		self.assertEqual((library, shapes), (shapes.Parent, package.Parent))
		self.assertEqual(({"Shapes": shapes}, {"shapes": package}), (library.Groups, shapes.Packages))

	def test_Package(self) -> None:
		package =    Package("my/pack")
		klass =      Class("my/pack/MyClass", "MyClass.java", parent=package)
		sourceFile = SourceFile("MyClass.java", parent=package)

		self.assertEqual((package, package), (klass.Parent, sourceFile.Parent))
		self.assertEqual(({"my/pack/MyClass": klass}, {"MyClass.java": sourceFile}), (package.Classes, package.SourceFiles))

	def test_Class(self) -> None:
		"""A method is added by name and descriptor: overloaded methods share a name."""
		klass = Class("my/pack/MyClass")
		methods = [Method("max", "(II)I", 3, parent=klass), Method("max", "(JJ)J", 7, parent=klass)]

		self.assertEqual([klass, klass], [method.Parent for method in methods])
		self.assertEqual({"max(II)I": methods[0], "max(JJ)J": methods[1]}, klass.Methods)

	def test_SourceFile(self) -> None:
		sourceFile = SourceFile("MyClass.java")
		line =       Line(13, 3, 4, 1, 1, parent=sourceFile)
		counter =    Counter(CounterType.Line, 0, 1, parent=sourceFile)

		self.assertEqual((sourceFile, sourceFile), (line.Parent, counter.Parent))
		self.assertEqual(({13: line}, {CounterType.Line: counter}), (sourceFile.Lines, sourceFile.Counters))

	def test_Document(self) -> None:
		"""Reading a report builds each relation."""
		report = Document(GROUPS, analyzeAndConvert=True)

		self.assertTrue(all(session.Parent is report for session in report.SessionInfos))
		self.assertTrue(all(counter.Parent is report for counter in report.Counters.values()))
		library = report.Groups["Library"]
		self.assertIs(report, library.Parent)
		self.assertIs(library, library.Groups["Shapes"].Parent)
		package = library.Groups["Shapes"].Packages["shapes"]
		self.assertIs(library.Groups["Shapes"], package.Parent)
		for klass in package.Classes.values():
			self.assertIs(package, klass.Parent)
			self.assertTrue(all(method.Parent is klass for method in klass.Methods.values()))

		for sourceFile in package.SourceFiles.values():
			self.assertIs(package, sourceFile.Parent)
			self.assertTrue(all(line.Parent is sourceFile for line in sourceFile.Lines.values()))

	def test_Parent(self) -> None:
		"""Each element checks the type of its parent; a line has no counters."""
		module = "pyEDAA.Reports.CodeCoverage.JaCoCo"
		now =    datetime.now(timezone.utc)
		for create, types, got in (
			(lambda: Group("Library", parent=Package("p")),            "'Report' or 'Group'", f"{module}.Package"),
			(lambda: Package("p", parent="Library"),                   "'Report' or 'Group'", "str"),
			(lambda: Class("p/A", parent=Group("Library")),            "'Package'",           f"{module}.Group"),
			(lambda: Method("m", "()V", parent=Package("p")),          "'Class'",             f"{module}.Package"),
			(lambda: SourceFile("A.java", parent=Class("p/A")),        "'Package'",           f"{module}.Classes.Class"),
			(lambda: Line(13, parent=Package("p")),                    "'SourceFile'",        f"{module}.Package"),
			(lambda: Counter(CounterType.Line, 0, 1, parent=Line(3)),  "'CountersMixin'",     f"{module}.Classes.Line"),
			(lambda: SessionInfo("host", now, now, parent=Group("G")), "'Report'",            f"{module}.Group")
		):
			with self.subTest(types=types, got=got):
				with self.assertRaises(TypeError) as context:
					_ = create()
				self.assertEqual(f"Parameter 'parent' is not of type {types}.", str(context.exception))
				self.assertEqual([f"Got type '{got}'."], context.exception.__notes__)

	def test_Duplicates(self) -> None:
		"""An element stating a child element twice is rejected before the second child is created."""
		for element, message in (
			("<sourcefile name='A.java'><line nr='3'/><line nr='3'/></sourcefile>",
			 "JaCoCo source file 'A.java' states line 3 twice."),
			("<class name='p/A'><method name='m' desc='()V'/><method name='m' desc='()V'/></class>",
			 "JaCoCo class 'p/A' states method 'm()V' twice."),
			("<method name='m' desc='()V'><counter type='LINE' missed='0' covered='1'/>"
			 "<counter type='LINE' missed='1' covered='0'/></method>",
			 "JaCoCo method 'm()V' states counter 'LINE' twice."),
			("<package name='p'><class name='p/A'/><class name='p/A'/></package>",
			 "JaCoCo package 'p' states class 'p/A' twice."),
			("<group name='G'><package name='p'/><package name='p'/></group>",
			 "JaCoCo group 'G' states package 'p' twice.")
		):
			xmlElement = fromstring(element)
			with self.subTest(element=xmlElement.tag):
				with self.assertRaises(CodeCoverageError) as context:
					_ = {"sourcefile": SourceFile, "class": Class, "method": Method, "package": Package, "group": Group}[
						xmlElement.tag
					].Parse(xmlElement)
				self.assertEqual(message, str(context.exception))


class Parsing(Testcase):
	"""Each class of the format's model parses its XML element."""

	def test_Line_Optional(self) -> None:
		"""A count the line doesn't state is ``None``."""
		line = Line.Parse(fromstring("<line nr='7' mb='0' cb='2'/>"))

		self.assertEqual((None, None, 0, 2), (
			line.MissedInstructionCount, line.CoveredInstructionCount, line.MissedBranchCount, line.CoveredBranchCount
		))

	def test_Method(self) -> None:
		method = Method.Parse(fromstring(
			"<method name='&lt;init&gt;' desc='()V' line='3'><counter type='METHOD' missed='0' covered='1'/></method>"
		))

		self.assertEqual(("<init>", "()V", 3), (method.Name, method.Descriptor, method.LineNumber))
		self.assertEqual([CounterType.Method], list(method.Counters))

	def test_Class(self) -> None:
		klass = Class.Parse(fromstring(
			"<class name='my/pack/MyClass$Inner' sourcefilename='MyClass.java'><method name='run' desc='()V'/></class>"
		))

		self.assertEqual(("my/pack/MyClass$Inner", "MyClass.java"), (klass.Name, klass.SourceFileName))
		self.assertIsNone(klass.Methods["run()V"].LineNumber)

	def test_Package(self) -> None:
		package = Package.Parse(fromstring(
			"<package name='p'><class name='p/A' sourcefilename='A.java'/><sourcefile name='A.java'/>"
			"<class name='p/B' sourcefilename='A.java'/></package>"
		))

		self.assertEqual((["p/A", "p/B"], ["A.java"]), (list(package.Classes), list(package.SourceFiles)))

	def test_SessionInfo(self) -> None:
		"""The times are milliseconds since the epoch."""
		session = SessionInfo.Parse(fromstring("<sessioninfo id='host-1234' start='1000' dump='2500'/>"))

		self.assertEqual("host-1234", session.SessionID)
		self.assertEqual(datetime(1970, 1, 1, 0, 0, 1, tzinfo=timezone.utc), session.Start)
		self.assertEqual(datetime(1970, 1, 1, 0, 0, 2, 500000, tzinfo=timezone.utc), session.Dump)


class Conversion(Testcase):
	"""The conversion to the common model: files, lines, branches, packages, classes and methods."""

	def test_Counts(self) -> None:
		"""The computed line counters agree with the report's ``LINE`` counter."""
		for path in (GRADLE, CLI, GROUPS):
			with self.subTest(report=path.name):
				report = Document(path, analyzeAndConvert=True)
				summary = report.ToCoverageSummary()

				lines = report.Counters[CounterType.Line]
				self.assertEqual((lines.MissedCount + lines.CoveredCount, lines.CoveredCount),
				                 (summary.TotalLines, summary.CoveredLines))

	def test_Counts_SourceFiles(self) -> None:
		"""The computed line counters agree with each source file's ``LINE`` counter."""
		report = Document(CLI, analyzeAndConvert=True)
		summary = report.ToCoverageSummary()

		for package in report.Packages.values():
			for sourceFile in package.SourceFiles.values():
				with self.subTest(sourceFile=sourceFile.Name):
					file = summary.GetOrAddFile(Path(package.Name) / sourceFile.Name)
					lines = sourceFile.Counters[CounterType.Line]
					self.assertEqual((lines.MissedCount + lines.CoveredCount, lines.CoveredCount),
					                 (file.TotalLines, file.CoveredLines))

	def test_Files(self) -> None:
		"""A source file's path is its package's name and its name; the default package adds no directory."""
		summary = Document(CLI, analyzeAndConvert=True).ToCoverageSummary()

		self.assertEqual(["Main.java", "shapes/Circle.java", "shapes/Shape.java"], [
			file.Path.as_posix() for file in summary.IterateFiles()
		])

	def test_Lines(self) -> None:
		"""A line ran, if it has a covered instruction; partially, if it has a missed branch. No counts, no targets."""
		circle = Document(CLI, analyzeAndConvert=True).ToCoverageSummary().Directories["shapes"].Files["Circle.java"]

		for number, status in ((8, LineCoverageStatus.Covered), (9, LineCoverageStatus.PartiallyCovered),
		                       (10, LineCoverageStatus.Uncovered)):
			with self.subTest(line=number):
				self.assertEqual((status, None), (circle.Lines[number].Status, circle.Lines[number].CoverageCount))

		self.assertIsNone(circle.Lines[11])
		branches = circle.Lines[9].Branches
		self.assertEqual([LineCoverageStatus.Covered, LineCoverageStatus.Uncovered], [branch.Status for branch in branches])
		self.assertEqual([None, None], [branch.Target for branch in branches])
		self.assertEqual((2, 1), (circle.TotalBranches, circle.CoveredBranches))

	def test_Line_Unknown(self) -> None:
		"""A line, which doesn't state its covered instructions, has an unknown state."""
		document = Document(Path("jacoco.xml"))
		sourceFile = SourceFile("A.java", parent=Package("p", parent=document))
		Line(3, missedBranchCount=1, coveredBranchCount=1, parent=sourceFile)
		document._name = "A"

		line = document.ToCoverageSummary().Directories["p"].Files["A.java"].Lines[3]
		self.assertEqual((LineCoverageStatus.Unknown, 2), (line.Status, len(line.Branches)))

	def test_Units(self) -> None:
		units = _units(CLI)

		self.assertEqual(["Main", "shapes", "util"], [name for name in units if "." not in name])
		for name, unitClass in (
			("shapes", cc_Package), ("shapes.Circle", cc_Class), ("shapes.Circle$Unit", cc_Class),
			("shapes.Circle.<init>(D)V", cc_Method), ("shapes.Circle.lambda$area$0(D)D", cc_Method), ("Main", cc_Class)
		):
			with self.subTest(name=name):
				self.assertIsInstance(units[name], unitClass)

	def test_Methods(self) -> None:
		"""A method spans its first line and the next lines of its file, as many as its ``LINE`` counter counts."""
		units = _units(CLI)

		for name, span, status in (
			("shapes.Circle.<init>(D)V",         (8, 13),  LineCoverageStatus.Covered),
			("shapes.Circle.area()D",            (17, 18), LineCoverageStatus.Covered),
			("shapes.Circle.lambda$area$0(D)D",  (17, 17), LineCoverageStatus.Covered),
			("Main.unused()V",                   (12, 13), LineCoverageStatus.Uncovered)
		):
			with self.subTest(name=name):
				method = units[name]
				self.assertEqual((span, status, None), (
					(method.StartLine.LineNumber, method.EndLine.LineNumber), method.Status, method.CoverageCount
				))

		init = units["shapes.Circle.<init>(D)V"]
		self.assertEqual((5, 4, 1), (init.TotalLines, init.CoveredLines, init.PartialLines))

	def test_Classes(self) -> None:
		"""A class spans its methods; its state is its ``CLASS`` counter's."""
		units = _units(CLI)

		circle = units["shapes.Circle"]
		self.assertEqual(((8, 18), LineCoverageStatus.Covered, 7), (
			(circle.StartLine.LineNumber, circle.EndLine.LineNumber), circle.Status, circle.TotalLines
		))
		self.assertIs(LineCoverageStatus.Uncovered, units["shapes.Circle$Unit"].Status)
		self.assertEqual("shapes/Circle.java", units["shapes.Circle$Unit"].File.Path.as_posix())

	def test_NoDebugInformation(self) -> None:
		"""A class without source file has no file and no lines; its state is still known."""
		units = _units(CLI)

		numbers = units["util.Numbers"]
		self.assertEqual((None, None, LineCoverageStatus.Covered, 0),
		                 (numbers.File, numbers.StartLine, numbers.Status, numbers.TotalLines))
		self.assertIs(LineCoverageStatus.Covered, units["util.Numbers.clamp(III)I"].Status)

	def test_Packages(self) -> None:
		"""A package's name is split at ``/`` into nested packages."""
		summary = Document(GRADLE, analyzeAndConvert=True).ToCoverageSummary()

		self.assertEqual(["my", "my.pack", "my.pack.MyClass"], [unit.QualifiedName for unit in summary.IterateUnits()][:3])
		self.assertEqual((8, 6), (summary.Units["my"].TotalLines, summary.Units["my"].CoveredLines))

	def test_Groups(self) -> None:
		"""The groups have no counterpart: a report with groups converts like the report without."""
		withGroups = Document(GROUPS, analyzeAndConvert=True).ToCoverageSummary()
		without =    Document(CLI, analyzeAndConvert=True).ToCoverageSummary()

		self.assertEqual([file.Path for file in without.IterateFiles()], [file.Path for file in withGroups.IterateFiles()])
		self.assertEqual([unit.QualifiedName for unit in without.IterateUnits()],
		                 [unit.QualifiedName for unit in withGroups.IterateUnits()])

	def test_Name(self) -> None:
		"""The common model's root is named after the report, or after the file, if the report's name is empty."""
		self.assertEqual("Gradle-JUnit4", Document(GRADLE, analyzeAndConvert=True).ToCoverageSummary().Name)

		with TemporaryDirectory() as directory:
			report = Document(
				_write(directory, GRADLE.read_text(encoding="utf-8").replace('name="Gradle-JUnit4"', 'name=""')),
				analyzeAndConvert=True
			)

		self.assertEqual("jacoco", report.ToCoverageSummary().Name)

	def test_SameSourceFile(self) -> None:
		"""Two packages of the same name - in two groups - stating a source file of the same name are rejected."""
		document = Document(Path("jacoco.xml"))
		document._name = "Twice"
		for groupName in ("A", "B"):
			sourceFile = SourceFile("A.java", parent=Package("p", parent=Group(groupName, parent=document)))
			Line(3, 0, 1, parent=sourceFile)

		with self.assertRaises(CodeCoverageError) as context:
			_ = document.ToCoverageSummary()
		self.assertEqual("Line 3 of file 'p/A.java' is added twice.", str(context.exception))


class Schema(Testcase):
	"""A report is validated against the XML schema of the format version its DTD's public identifier states."""

	def test_Schemas(self) -> None:
		self.assertEqual({FormatVersion.Version1_1: "JaCoCo-1.1.xsd"}, SCHEMAS)
		self.assertEqual("1.1", PUBLIC_IDENTIFIER.fullmatch("-//JACOCO//DTD Report 1.1//EN")[1])

	def test_FormatVersion(self) -> None:
		with TemporaryDirectory() as directory:
			xmlFile = _write(directory, GRADLE.read_text(encoding="utf-8").replace("DTD Report 1.1", "DTD Report 1.2"))

			with self.assertRaises(CodeCoverageError) as context:
				_ = Document(xmlFile, analyzeAndConvert=True)

		self.assertEqual(f"JaCoCo report file '{xmlFile}' states an unsupported format version.", str(context.exception))
		self.assertEqual(
			["Got public identifier '-//JACOCO//DTD Report 1.2//EN'.", "Supported format versions: 1.1."],
			context.exception.__notes__
		)

	def test_FormatVersion_Missing(self) -> None:
		"""A report without the DTD's public identifier - e.g. gcovr's - states no format version."""
		content = GRADLE.read_text(encoding="utf-8").replace(
			'<!DOCTYPE report PUBLIC "-//JACOCO//DTD Report 1.1//EN" "report.dtd">', ""
		)
		with TemporaryDirectory() as directory:
			with self.assertRaises(CodeCoverageError) as context:
				_ = Document(_write(directory, content), analyzeAndConvert=True)

		self.assertEqual(["Got no public identifier.", "Supported format versions: 1.1."], context.exception.__notes__)

	def test_GroupsAndPackages(self) -> None:
		"""The DTD allows groups or packages in a report, not both."""
		content = GRADLE.read_text(encoding="utf-8").replace("<package ", "<group name='Library'/><package ")
		with TemporaryDirectory() as directory:
			xmlFile = _write(directory, content)

			with self.assertRaises(CodeCoverageError) as context:
				_ = Document(xmlFile, analyzeAndConvert=True)

		self.assertEqual(f"Validation error for '{xmlFile}' using XSD schema 'JaCoCo-1.1.xsd'.", str(context.exception))

	def test_UnknownAttribute(self) -> None:
		content = GRADLE.read_text(encoding="utf-8").replace('<line nr="13"', '<line nr="13" hits="4"')
		with TemporaryDirectory() as directory:
			with self.assertRaises(CodeCoverageError) as context:
				_ = Document(_write(directory, content), analyzeAndConvert=True)

		self.assertEqual(1, len(context.exception.__notes__))
		self.assertIn("The attribute 'hits' is not allowed.", context.exception.__notes__[0])

	def test_CounterType(self) -> None:
		content = GRADLE.read_text(encoding="utf-8").replace('type="CLASS"', 'type="FILE"')
		with TemporaryDirectory() as directory:
			with self.assertRaises(CodeCoverageError) as context:
				_ = Document(_write(directory, content), analyzeAndConvert=True)

		self.assertIn("'FILE' is not an element of the set", context.exception.__notes__[0])

	def test_Root(self) -> None:
		"""The JaCoCo reader rejects a Cobertura report by its root element."""
		xmlFile = DATA.parent / "Python" / "coverage.xml"

		with self.assertRaises(CodeCoverageError) as context:
			_ = Document(xmlFile, analyzeAndConvert=True)

		self.assertEqual(f"Root element of '{xmlFile}' is not '<report>'.", str(context.exception))
		self.assertEqual(["Got root element '<coverage>'."], context.exception.__notes__)

	def test_Cobertura(self) -> None:
		"""The Cobertura reader rejects a JaCoCo report by its root element."""
		with self.assertRaises(CodeCoverageError) as context:
			_ = CoberturaDocument(GRADLE, analyzeAndConvert=True)

		self.assertEqual(f"Root element of '{GRADLE}' is not '<coverage>'.", str(context.exception))
		self.assertEqual(["Got root element '<report>'."], context.exception.__notes__)

	def test_FileNotFound(self) -> None:
		with self.assertRaises(CodeCoverageError) as context:
			_ = Document(DATA / "missing.xml", analyzeAndConvert=True)

		self.assertEqual(f"JaCoCo report file '{DATA / 'missing.xml'}' does not exist.", str(context.exception))

	def test_Unreadable(self) -> None:
		"""A directory can't be read as a file."""
		with self.assertRaises(CodeCoverageError) as context:
			_ = Document(DATA, analyzeAndConvert=True)

		self.assertEqual(f"Couldn't read JaCoCo report file '{DATA}'.", str(context.exception))
		self.assertIsInstance(context.exception.__cause__, OSError)

	def test_NotAnalyzed(self) -> None:
		with self.assertRaises(CodeCoverageError) as context:
			Document(GRADLE).Convert()

		self.assertEqual(
			f"JaCoCo report file '{GRADLE}' needs to be read and analyzed by an XML parser.", str(context.exception)
		)
