from __future__ import annotations

from argparse import Namespace
from pathlib  import Path
from typing   import ClassVar, List, Tuple, Type

from lxml.etree                               import XMLSyntaxError
from pyTooling.Decorators                     import readonly
from pyTooling.MetaClasses                    import ExtendedType
from pyTooling.Attributes.ArgParse            import CommandHandler
from pyTooling.Attributes.ArgParse.ValuedFlag import LongValuedFlag

from pyEDAA.Reports.Unittesting       import UnittestError, TestsuiteKind, TestsuiteSummary, Testsuite, Testcase
from pyEDAA.Reports.Unittesting       import Document, MergedTestsuiteSummary
from pyEDAA.Reports.Unittesting.JUnit import JUnitReaderMode, TestsuiteSummary as ju_TestsuiteSummary


class UnittestingHandlers(metaclass=ExtendedType, mixin=True):
	UNITTEST_INPUT_FORMATS:  ClassVar[Tuple[str, ...]] = (
		"Ant-JUnit", "Any-JUnit", "Catch2-JUnit", "CTest-JUnit", "GoJUnitReport-JUnit", "gtest-JUnit", "nextest-JUnit",
		"pyTest-JUnit", "TestLogger-JUnit"
	)  #: The formats ``--input`` and ``--merge`` read, by their name on the command line.
	UNITTEST_OUTPUT_FORMATS: ClassVar[Tuple[str, ...]] = (
		"Ant-JUnit", "Catch2-JUnit", "CTest-JUnit", "GoJUnitReport-JUnit", "gtest-JUnit", "nextest-JUnit", "pyTest-JUnit",
		"TestLogger-JUnit"
	)  #: The formats ``--output`` writes, by their name on the command line.

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

	def _SplitTask(self, task: str, formats: Tuple[str, ...]) -> Tuple[str, str, str]:
		"""
		Split an option's value ``<Dialect>-<Format>:<FilePattern>`` into dialect, format and file pattern.

		The value is split at its first ``:`` only, so the file pattern may contain colons, like a Windows drive letter.

		:param task:           The option's value, e.g. ``pyTest-JUnit:report/unit/*.xml``.
		:param formats:        The formats the option accepts, by their name on the command line.
		:returns:              The dialect and the format in lower case, and the file pattern.
		:raises UnittestError: If the value has no ``:`` or no file pattern. |br|
		                       The exception notes the supported formats.
		:raises UnittestError: If the format names no dialect (no ``-``). |br|
		                       The exception notes the supported formats.
		"""
		token, colon, globPattern = task.partition(":")
		if colon == "" or globPattern == "":
			ex = UnittestError(f"Syntax error: '{task}'")
			ex.add_note(f"Write '<Format>:<File>' with one of: {', '.join(formats)}.")
			raise ex

		dialect, minus, dataFormat = token.lower().partition("-")
		if minus == "":
			ex = UnittestError(f"Unsupported unit testing report format: '{token}'")
			ex.add_note(f"Supported formats: {', '.join(formats)}.")
			raise ex

		return dialect, dataFormat, globPattern

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

	def _open(self, task: str) -> ju_TestsuiteSummary:
		dialect, dataFormat, globPattern = self._SplitTask(task, self.UNITTEST_INPUT_FORMATS)
		foundFiles = self._FindFiles(globPattern)
		if (length := len(foundFiles)) != 1:
			ex = UnittestError(f"Found {length} files for pattern '{globPattern}'.")
			raise ex from FileNotFoundError(str(Path.cwd() / globPattern))

		file = foundFiles[0]

		if dataFormat == "junit":
			if dialect == "ant":
				from pyEDAA.Reports.Unittesting.JUnit.AntJUnit4 import Document

				documentClass = Document
			elif dialect == "any":
				from pyEDAA.Reports.Unittesting.JUnit import Document

				documentClass = Document
			elif dialect == "catch2":
				from pyEDAA.Reports.Unittesting.JUnit.Catch2JUnit import Document

				documentClass = Document
			elif dialect == "ctest":
				from pyEDAA.Reports.Unittesting.JUnit.CTestJUnit import Document

				documentClass = Document
			elif dialect == "gojunitreport":
				from pyEDAA.Reports.Unittesting.JUnit.GoJUnitReport import Document

				documentClass = Document
			elif dialect == "gtest":
				from pyEDAA.Reports.Unittesting.JUnit.GoogleTestJUnit import Document

				documentClass = Document
			elif dialect == "nextest":
				from pyEDAA.Reports.Unittesting.JUnit.NextestJUnit import Document

				documentClass = Document
			elif dialect == "pytest":
				from pyEDAA.Reports.Unittesting.JUnit.PyTestJUnit import Document

				documentClass = Document
			elif dialect == "testlogger":
				from pyEDAA.Reports.Unittesting.JUnit.TestLoggerJUnit import Document

				documentClass = Document
			else:
				raise UnittestError(f"Unsupported JUnit XML dialect for input: '{dataFormat}-{dialect}'")

			self.WriteVerbose(f"  Reading {file}")
			return documentClass(file, analyzeAndConvert=True)
		else:
			raise UnittestError(f"Unsupported unit testing report dataFormat for input: '{dataFormat}'")

	def _merge(self, testsuiteSummary: MergedTestsuiteSummary, task: str) -> None:
		try:
			dialect, dataFormat, globPattern = self._SplitTask(task, self.UNITTEST_INPUT_FORMATS)
		except UnittestError as ex:
			self.WriteError(str(ex))
			for note in getattr(ex, "__notes__", ()):
				self.WriteErrorNote(note)

			return

		foundFiles = self._FindFiles(globPattern)
		if len(foundFiles) == 0:
			self.WriteWarning(f"Found no matching files for pattern '{Path.cwd() / globPattern}'")
			return

		if dataFormat == "junit":
			if dialect == "ant":
				from pyEDAA.Reports.Unittesting.JUnit.AntJUnit4 import Document

				self._mergeJUnit(testsuiteSummary, Document, foundFiles, "Ant+JUnit4")
			elif dialect == "any":
				from pyEDAA.Reports.Unittesting.JUnit import Document

				self._mergeJUnit(testsuiteSummary, Document, foundFiles, "Any-JUnit")
			elif dialect == "catch2":
				from pyEDAA.Reports.Unittesting.JUnit.Catch2JUnit import Document

				self._mergeJUnit(testsuiteSummary, Document, foundFiles, "Catch2-JUnit")
			elif dialect == "ctest":
				from pyEDAA.Reports.Unittesting.JUnit.CTestJUnit import Document

				self._mergeJUnit(testsuiteSummary, Document, foundFiles, "CTest-JUnit")
			elif dialect == "gojunitreport":
				from pyEDAA.Reports.Unittesting.JUnit.GoJUnitReport import Document

				self._mergeJUnit(testsuiteSummary, Document, foundFiles, "GoJUnitReport-JUnit")
			elif dialect == "gtest":
				from pyEDAA.Reports.Unittesting.JUnit.GoogleTestJUnit import Document

				self._mergeJUnit(testsuiteSummary, Document, foundFiles, "GoogleTest-JUnit")
			elif dialect == "nextest":
				from pyEDAA.Reports.Unittesting.JUnit.NextestJUnit import Document

				self._mergeJUnit(testsuiteSummary, Document, foundFiles, "nextest-JUnit")
			elif dialect == "pytest":
				from pyEDAA.Reports.Unittesting.JUnit.PyTestJUnit import Document

				self._mergeJUnit(testsuiteSummary, Document, foundFiles, "pyTest-JUnit")
			elif dialect == "testlogger":
				from pyEDAA.Reports.Unittesting.JUnit.TestLoggerJUnit import Document

				self._mergeJUnit(testsuiteSummary, Document, foundFiles, "TestLogger-JUnit")
			else:
				self.WriteError(f"Unsupported JUnit XML dialect for merging: '{dataFormat}-{dialect}'")
		else:
			self.WriteError(f"Unsupported unit testing report dataFormat for merging: '{dataFormat}'")

	def _mergeJUnit(self, testsuiteSummary: MergedTestsuiteSummary, documentClass: Type[Document], foundFiles: Tuple[Path, ...], dialect: str) -> None:
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
			dialect, format, fileName = self._SplitTask(task, self.UNITTEST_OUTPUT_FORMATS)
		except UnittestError as ex:
			self.WriteError(str(ex))
			for note in getattr(ex, "__notes__", ()):
				self.WriteErrorNote(note)

			return

		outputFile = Path(fileName)
		if format == "junit":
			if dialect == "ant":
				from pyEDAA.Reports.Unittesting.JUnit.AntJUnit4 import Document

				self._outputJUnit(testsuiteSummary, Document, outputFile, "Ant+JUnit4")
			elif dialect == "catch2":
				from pyEDAA.Reports.Unittesting.JUnit.Catch2JUnit import Document

				self._outputJUnit(testsuiteSummary, Document, outputFile, "Catch2-JUnit")
			elif dialect == "ctest":
				from pyEDAA.Reports.Unittesting.JUnit.CTestJUnit import Document

				self._outputJUnit(testsuiteSummary, Document, outputFile, "CTest-JUnit")
			elif dialect == "gojunitreport":
				from pyEDAA.Reports.Unittesting.JUnit.GoJUnitReport import Document

				self._outputJUnit(testsuiteSummary, Document, outputFile, "GoJUnitReport-JUnit")
			elif dialect == "gtest":
				from pyEDAA.Reports.Unittesting.JUnit.GoogleTestJUnit import Document

				self._outputJUnit(testsuiteSummary, Document, outputFile, "GoogleTest-JUnit")
			elif dialect == "nextest":
				from pyEDAA.Reports.Unittesting.JUnit.NextestJUnit import Document

				self._outputJUnit(testsuiteSummary, Document, outputFile, "nextest-JUnit")
			elif dialect == "pytest":
				from pyEDAA.Reports.Unittesting.JUnit.PyTestJUnit import Document

				self._outputJUnit(testsuiteSummary, Document, outputFile, "pyTest-JUnit")
			elif dialect == "testlogger":
				from pyEDAA.Reports.Unittesting.JUnit.TestLoggerJUnit import Document

				self._outputJUnit(testsuiteSummary, Document, outputFile, "TestLogger-JUnit")
			else:
				self.WriteError(f"Unsupported JUnit XML dialect for writing: '{format}-{dialect}'")
		else:
			self.WriteError(f"Unsupported unit testing report format for writing: '{format}'")

	def _outputJUnit(self, testsuiteSummary: TestsuiteSummary, documentClass: Type[Document], file: Path, dialect: str):
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
