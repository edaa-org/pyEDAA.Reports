from __future__ import annotations

from argparse import Namespace
from pathlib  import Path
from typing   import Dict, List, Tuple, Type, TypeVar

from lxml.etree                               import XMLSyntaxError
from pyTooling.Attributes.ArgParse            import CommandHandler, splitFormat
from pyTooling.Attributes.ArgParse.ValuedFlag import LongValuedFlag
from pyTooling.Common                         import StringEnum
from pyTooling.Decorators                     import export
from pyTooling.MetaClasses                    import ExtendedType

from pyEDAA.Reports.Unittesting                       import UnittestError, TestsuiteKind, TestsuiteSummary, Testsuite
from pyEDAA.Reports.Unittesting                       import Testcase, MergedTestsuiteSummary
from pyEDAA.Reports.Unittesting.JUnit                 import Document as AnyJUnitDocument, JUnitReaderMode
from pyEDAA.Reports.Unittesting.JUnit.AntJUnit4       import Document as AntJUnitDocument
from pyEDAA.Reports.Unittesting.JUnit.Catch2JUnit     import Document as Catch2JUnitDocument
from pyEDAA.Reports.Unittesting.JUnit.CTestJUnit      import Document as CTestJUnitDocument
from pyEDAA.Reports.Unittesting.JUnit.GoJUnitReport   import Document as GoJUnitReportDocument
from pyEDAA.Reports.Unittesting.JUnit.GoogleTestJUnit import Document as GoogleTestJUnitDocument
from pyEDAA.Reports.Unittesting.JUnit.NextestJUnit    import Document as NextestJUnitDocument
from pyEDAA.Reports.Unittesting.JUnit.PyTestJUnit     import Document as PyTestJUnitDocument
from pyEDAA.Reports.Unittesting.JUnit.TestLoggerJUnit import Document as TestLoggerJUnitDocument


__all__ = ["INPUT_FORMATS", "OUTPUT_FORMATS"]


@export
class InputFormat(StringEnum):
	"""The unit test report formats ``--input`` and ``--merge`` read, by their name on the command line."""

	AntJUnit =           "Ant-JUnit"            #: JUnit XML as Ant's JUnit 4 task writes it.
	AnyJUnit =           "Any-JUnit"            #: JUnit XML of any tool, read leniently.
	Catch2JUnit =        "Catch2-JUnit"         #: JUnit XML as Catch2 writes it.
	CTestJUnit =         "CTest-JUnit"          #: JUnit XML as CTest writes it.
	GoJUnitReportJUnit = "GoJUnitReport-JUnit"  #: JUnit XML as go-junit-report writes it.
	GoogleTestJUnit =    "gtest-JUnit"          #: JUnit XML as GoogleTest writes it.
	NextestJUnit =       "nextest-JUnit"        #: JUnit XML as cargo-nextest writes it.
	PyTestJUnit =        "pyTest-JUnit"         #: JUnit XML as pytest writes it.
	TestLoggerJUnit =    "TestLogger-JUnit"     #: JUnit XML as the .NET test logger JunitXml.TestLogger writes it.


@export
class OutputFormat(StringEnum):
	"""The unit test report formats ``--output`` writes, by their name on the command line."""

	AntJUnit =           "Ant-JUnit"            #: JUnit XML as Ant's JUnit 4 task writes it.
	Catch2JUnit =        "Catch2-JUnit"         #: JUnit XML as Catch2 writes it.
	CTestJUnit =         "CTest-JUnit"          #: JUnit XML as CTest writes it.
	GoJUnitReportJUnit = "GoJUnitReport-JUnit"  #: JUnit XML as go-junit-report writes it.
	GoogleTestJUnit =    "gtest-JUnit"          #: JUnit XML as GoogleTest writes it.
	NextestJUnit =       "nextest-JUnit"        #: JUnit XML as cargo-nextest writes it.
	PyTestJUnit =        "pyTest-JUnit"         #: JUnit XML as pytest writes it.
	TestLoggerJUnit =    "TestLogger-JUnit"     #: JUnit XML as the .NET test logger JunitXml.TestLogger writes it.


#: The document class reading each input format.
INPUT_FORMATS: Dict[InputFormat, Type[AnyJUnitDocument]] = {
	InputFormat.AntJUnit:           AntJUnitDocument,
	InputFormat.AnyJUnit:           AnyJUnitDocument,
	InputFormat.Catch2JUnit:        Catch2JUnitDocument,
	InputFormat.CTestJUnit:         CTestJUnitDocument,
	InputFormat.GoJUnitReportJUnit: GoJUnitReportDocument,
	InputFormat.GoogleTestJUnit:    GoogleTestJUnitDocument,
	InputFormat.NextestJUnit:       NextestJUnitDocument,
	InputFormat.PyTestJUnit:        PyTestJUnitDocument,
	InputFormat.TestLoggerJUnit:    TestLoggerJUnitDocument
}

#: The document class writing each output format.
OUTPUT_FORMATS: Dict[OutputFormat, Type[AnyJUnitDocument]] = {
	OutputFormat.AntJUnit:           AntJUnitDocument,
	OutputFormat.Catch2JUnit:        Catch2JUnitDocument,
	OutputFormat.CTestJUnit:         CTestJUnitDocument,
	OutputFormat.GoJUnitReportJUnit: GoJUnitReportDocument,
	OutputFormat.GoogleTestJUnit:    GoogleTestJUnitDocument,
	OutputFormat.NextestJUnit:       NextestJUnitDocument,
	OutputFormat.PyTestJUnit:        PyTestJUnitDocument,
	OutputFormat.TestLoggerJUnit:    TestLoggerJUnitDocument
}

Format = TypeVar("Format", InputFormat, OutputFormat)


class UnittestingHandlers(metaclass=ExtendedType, mixin=True):
	@CommandHandler("unittest", help="Transform unit testing results.", description="Merge and/or transform unit testing results.")
	@LongValuedFlag("--name", dest="name", metaName='Name', optional=True, help="Top-level unit testing summary name.")
	@LongValuedFlag("--input", dest="input", metaName='format:JUnit File', optional=True, help="Unit testing summary file (XML).")
	@LongValuedFlag("--merge", dest="merge", metaName='format:JUnit File', optional=True, help="Unit testing summary file (XML).")
	@LongValuedFlag("--pytest", dest="pytest", metaName='cleanup;cleanup', optional=True, help="Remove pytest overhead.")
	@LongValuedFlag("--render", dest="render", metaName='format', optional=True, help="Render unit testing results to <format>.")
	@LongValuedFlag("--output", dest="output", metaName='format:JUnit File', optional=True, help="Processed unit testing summary file (XML).")
	def HandleUnittest(self, args: Namespace) -> None:
		"""Handle program calls with command ``unittest``."""
		self._PrintHeadline()

		returnCode = 0
		if (args.input is None) and (args.merge is None):
			self.WriteError(f"Either option '--input=<Format>:<JUnitFilePattern>' or '--merge=<Format>:<JUnitFilePattern>' is missing.")
			returnCode = 3

		if returnCode != 0:
			self.Exit(returnCode)

		testsuiteSummaryName = args.name if args.name is not None else "TestsuiteSummary"
		merged = MergedTestsuiteSummary(testsuiteSummaryName)

		if args.input is not None:
			self.WriteNormal(f"Reading unit test input file ...")
			openTask = args.input
			try:
				document = self._open(openTask)
			except UnittestError as ex:
				self.WriteFatal(str(ex), immediateExit=False)
				for note in getattr(ex, "__notes__", ()):
					self.WriteErrorNote(note)

				if (innerEx := ex.__cause__) is not None and isinstance(innerEx, XMLSyntaxError):
					for note in getattr(innerEx, "__notes__", ()):
						self.WriteErrorNote(note)

				self.Exit(1)

			merged.Merge(document.ToTestsuiteSummary())

		if args.merge is not None:
			mergeTasks: Tuple[str, ...] = (args.merge, )
			for mergeTask in mergeTasks:
				self._merge(merged, mergeTask)

		self.WriteNormal(f"Aggregating unit test metrics ...")
		merged.Aggregate()

		self.WriteNormal(f"Flattening data structures to a single dimension ...")
		result = merged.ToTestsuiteSummary()

		if args.pytest is not None:
			self._processPyTest(result, args.pytest)

		if args.render is not None and self.Verbose:
			self.WriteVerbose("*" * self.Width)

			if args.render == "tree":
				tree = result.ToTree()
				self.WriteVerbose(tree.Render(), appendLinebreak=False)

			self.WriteVerbose("*" * self.Width)

		if args.output is not None:
			outputs = (args.output, )
			for output in outputs:
				self._output(result, output)

		self.ExitOnPreviousErrors()

	def _SplitTask(self, task: str, formats: Type[Format], direction: str) -> Tuple[Format, str]:
		"""
		Split an option's value ``<Format>:<FilePattern>`` into the format and the file pattern.

		The value is split at its first ``:`` only, so the file pattern may contain colons, like a Windows drive letter.

		:param task:           The option's value, e.g. ``pyTest-JUnit:report/unit/*.xml``.
		:param formats:        The formats the option accepts.
		:param direction:      ``input`` or ``output``, for the error message.
		:returns:              The format and the file pattern.
		:raises UnittestError: If the value names no format, or one the option doesn't accept. |br|
		                       The exception notes the supported formats.
		"""
		try:
			fileFormat, globPattern = splitFormat(task, formats)
		except ValueError as ex:
			error = UnittestError(f"Unsupported unit testing report format for {direction}: '{task}'.")
			error.add_note(f"Supported formats: {', '.join(formats)}.")
			raise error from ex

		return fileFormat, str(globPattern)

	@staticmethod
	def _FindFiles(globPattern: str) -> Tuple[Path, ...]:
		"""
		Find the files matching a file pattern, relative to the current directory or absolute.

		:param globPattern: The file pattern, e.g. ``report/unit/*.xml``.
		:returns:           The matching files.
		"""
		pattern = Path(globPattern)
		directory = Path(pattern.anchor) if pattern.is_absolute() else Path.cwd()
		return tuple(directory.glob(str(pattern.relative_to(pattern.anchor))))

	def _open(self, task: str) -> AnyJUnitDocument:
		inputFormat, globPattern = self._SplitTask(task, InputFormat, "input")
		foundFiles = self._FindFiles(globPattern)
		if (length := len(foundFiles)) != 1:
			ex = UnittestError(f"Found {length} files for pattern '{globPattern}'.")
			raise ex from FileNotFoundError(str(Path.cwd() / globPattern))

		file = foundFiles[0]
		self.WriteVerbose(f"  Reading {file}")
		return INPUT_FORMATS[inputFormat](file, analyzeAndConvert=True)

	def _merge(self, testsuiteSummary: MergedTestsuiteSummary, task: str) -> None:
		try:
			inputFormat, globPattern = self._SplitTask(task, InputFormat, "input")
		except UnittestError as ex:
			self.WriteError(str(ex))
			for note in getattr(ex, "__notes__", ()):
				self.WriteErrorNote(note)

			return

		foundFiles = self._FindFiles(globPattern)
		if len(foundFiles) == 0:
			self.WriteWarning(f"Found no matching files for pattern '{Path.cwd() / globPattern}'")
			return

		self._mergeJUnit(testsuiteSummary, INPUT_FORMATS[inputFormat], foundFiles, inputFormat)

	def _mergeJUnit(
		self,
		testsuiteSummary: MergedTestsuiteSummary,
		documentClass: Type[AnyJUnitDocument],
		foundFiles: Tuple[Path, ...],
		dialect: str
	) -> None:
		self.WriteNormal(f"Reading {len(foundFiles)} {dialect} unit test summary files ...")

		junitDocuments: List[documentClass] = []
		for file in foundFiles:
			self.WriteVerbose(f"  Reading {file}")
			try:
				junitDocuments.append(documentClass(file, analyzeAndConvert=True, readerMode=JUnitReaderMode.DecoupleTestsuiteHierarchyAndTestcaseClassName))
			except UnittestError as ex:
				self.WriteError(str(ex))
				for note in getattr(ex, "__notes__", ()):
					self.WriteErrorNote(note)

		if len(junitDocuments) == 0:
			self.WriteCritical(f"None of the {dialect} files were successfully read.")
			return

		self.WriteNormal(f"Merging unit test summary files into a single data model ...")
		for summary in junitDocuments:
			self.WriteVerbose(f"  merging {summary.Path}")
			testsuiteSummary.Merge(summary.ToTestsuiteSummary())

	def _processPyTest(self, testsuiteSummary: TestsuiteSummary, cleanups: str) -> None:
		self.WriteNormal(f"Simplifying unit testing reports created by pytest ...")

		for cleanup in cleanups.split(";"):
			parts = cleanup.split(":")
			if (l := len(parts)) == 1:
				if cleanup.lower() == "rewrite-dunder-init":
					self._processPyTest_RewiteDunderInit(testsuiteSummary)
				else:
					self.WriteError(f"Unsupported cleanup action for pytest: '{cleanup}'")
			elif l >= 2:
				command = parts[0].lower()
				if command == "reduce-depth":
					for path in parts[1:]:
						self._processPyTest_ReduceDepth(testsuiteSummary, path)
				elif command == "split":
					for path in parts[1:]:
						self._processPyTest_SplitTestsuite(testsuiteSummary, path)
				else:
					self.WriteError(f"Unsupported cleanup action for pytest: '{parts[0]}'")
			else:
				self.WriteError(f"Syntax error: '{cleanup}'")

	def _processPyTest_RewiteDunderInit(self, testsuiteSummary: TestsuiteSummary) -> None:
		self.WriteVerbose(f"  Rewriting '__init__' in classnames to actual Python package names")

		def processTestsuite(suite: Testsuite) -> None:
			testsuites: Tuple[Testsuite, ...] = tuple(ts for ts in suite.Testsuites.values())
			for testsuite in testsuites:                # type: Testsuite
				if testsuite.Name != "__init__":
					processTestsuite(testsuite)
					continue

				for ts in testsuite.Testsuites.values():  # type: Testsuite
					ts._parent = None
					suite.AddTestsuite(ts)

				for tc in testsuite.Testcases.values():   # type: Testcase
					tc._parent = None
					suite.AddTestcase(tc)

				del suite._testsuites["__init__"]

		processTestsuite(testsuiteSummary)

	def _processPyTest_ReduceDepth(self, testsuiteSummary: TestsuiteSummary, path: str) -> None:
		self.WriteVerbose(f"  Reducing path depth of testsuite '{path}'")
		cleanups = []
		suite = testsuiteSummary
		message = f"    Walking: {suite._name}"
		for element in path.split("."):
			if element in suite._testsuites:
				suite = suite._testsuites[element]
				message += f" -> {suite._name}"
			else:
				self.WriteDebug(f"    Skipping: {path}")
				suite = None
				break

		if suite is None:
			return

		self.WriteDebug(message)
		cleanups.append(suite)

		self.WriteDebug(f"    Moving testsuites ...")
		for ts in suite._testsuites.values():
			self.WriteDebug(f"      {ts._name} -> {testsuiteSummary._name}")
			ts._parent = None
			ts._kind = TestsuiteKind.Logical
			testsuiteSummary.AddTestsuite(ts)

		self.WriteDebug(f"    Deleting empty testsuites ...")
		for clean in cleanups:
			suite = clean
			while suite is not testsuiteSummary:
				name = suite._name
				suite = suite._parent
				if name in suite._testsuites:
					self.WriteDebug(f"      delete '{name}'")
					del suite._testsuites[name]
				else:
					self.WriteDebug(f"      skipping '{name}'")
					break

	def _processPyTest_SplitTestsuite(self, testsuiteSummary: TestsuiteSummary, path: str) -> None:
		self.WriteVerbose(f"  Splitting testsuite '{path}'")
		if path not in testsuiteSummary.Testsuites:
			self.WriteError(f"Path '{path}' not found")
			return

		cleanups = []
		parentTestsuite = testsuiteSummary
		workingTestsuite = parentTestsuite.Testsuites[path]
		for testsuite in workingTestsuite.Testsuites.values():
			self.WriteDebug(f"    Moving {testsuite.Name} to {parentTestsuite.Name}")

			testsuiteName = testsuite._name
			parentTestsuite.Testsuites[testsuiteName] = testsuite
			testsuite._parent = parentTestsuite

			cleanups.append(testsuiteName)

		for cleanup in cleanups:
			del workingTestsuite.Testsuites[cleanup]

		if len(workingTestsuite.Testsuites) == 0 and len(workingTestsuite.Testcases) == 0:
			self.WriteVerbose(f"  Removing empty testsuite '{path}'")
			del parentTestsuite.Testsuites[path]

	def _output(self, testsuiteSummary: TestsuiteSummary, task: str):
		try:
			outputFormat, fileName = self._SplitTask(task, OutputFormat, "output")
		except UnittestError as ex:
			self.WriteError(str(ex))
			for note in getattr(ex, "__notes__", ()):
				self.WriteErrorNote(note)

			return

		self._outputJUnit(testsuiteSummary, OUTPUT_FORMATS[outputFormat], Path(fileName), outputFormat)

	def _outputJUnit(
		self,
		testsuiteSummary: TestsuiteSummary,
		documentClass: Type[AnyJUnitDocument],
		file: Path,
		dialect: str
	) -> None:
		self.WriteNormal(f"Writing merged unit test summaries to file ...")
		self.WriteVerbose(f"  Common Data Model -> OUT ({dialect}): {file}")

		junitDocument = documentClass.FromTestsuiteSummary(file, testsuiteSummary)
		try:
			junitDocument.Write(regenerate=True, overwrite=True)
		except UnittestError as ex:
			self.WriteError(str(ex))
			if ex.__cause__ is not None:
				self.WriteError(f"  {ex.__cause__}")

			return

		self.WriteNormal(f"Output written to '{file}' in {dialect} format.")
