from argparse import Namespace
from pathlib  import Path
from typing   import List, Tuple, Type

from pyTooling.MetaClasses                    import ExtendedType
from pyTooling.Attributes.ArgParse            import CommandHandler
from pyTooling.Attributes.ArgParse.ValuedFlag import LongValuedFlag

from pyEDAA.Reports.Unittesting       import UnittestException, TestsuiteKind, TestsuiteSummary, Testsuite, Testcase
from pyEDAA.Reports.Unittesting       import Document, MergedTestsuiteSummary
from pyEDAA.Reports.Unittesting.JUnit import JUnitReaderMode, TestsuiteSummary as ju_TestsuiteSummary


class UnittestingHandlers(metaclass=ExtendedType, mixin=True):
	@CommandHandler("unittest", help="Transform unit testing results.", description="Merge and/or transform unit testing results.")
	@LongValuedFlag("--name", dest="name", metaName='Name', optional=True, help="Top-level unit testing summary name.")
	@LongValuedFlag("--input", dest="input", metaName='format:JUnit File', optional=True, help="Unit testing summary file (XML).")
	@LongValuedFlag("--merge", dest="merge", metaName='format:JUnit File', optional=True, help="Unit testing summary file (XML).")
	@LongValuedFlag("--pytest", dest="pytest", metaName='cleanup;cleanup', optional=True, help="Remove pytest overhead.")
	@LongValuedFlag("--render", dest="render", metaName='format', optional=True, help="Render unit testing results to <format>.")
	@LongValuedFlag("--output", dest="output", metaName='format:JUnit File', help="Processed unit testing summary file (XML).")
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
			except UnittestException as ex:
				self.WriteFatal(ex, immediateExit=False)
				for note in ex.__notes__:
					self.WriteNormal(f"           {note}")
				self.Exit()

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

	def _open(self, task: str) -> ju_TestsuiteSummary:
		parts = task.split(":")
		if (length := len(parts)) == 1:
			raise UnittestException(f"Syntax error: '{task}'")
		elif length == 2:
			dialect, dataFormat = (x.lower() for x in parts[0].split("-"))
			globPattern = parts[1]
			foundFiles = [f for f in Path.cwd().glob(globPattern)]
			if (length := len(foundFiles)) != 1:
				raise UnittestException(f"Found {length} files for pattern '{globPattern}'.") from FileNotFoundError(str(Path.cwd() / globPattern))

			file = foundFiles[0]

			if dataFormat == "junit":
				if dialect == "ant":
					from pyEDAA.Reports.Unittesting.JUnit.AntJUnit4 import Document

					documentClass = Document
				elif dialect == "any":
					from pyEDAA.Reports.Unittesting.JUnit import Document

					documentClass = Document
				elif dialect == "ctest":
					from pyEDAA.Reports.Unittesting.JUnit.CTestJUnit import Document

					documentClass = Document
				elif dialect == "gtest":
					from pyEDAA.Reports.Unittesting.JUnit.GoogleTestJUnit import Document

					documentClass = Document
				elif dialect == "pytest":
					from pyEDAA.Reports.Unittesting.JUnit.PyTestJUnit import Document

					documentClass = Document
				else:
					raise UnittestException(f"Unsupported JUnit XML dialect for input: '{dataFormat}-{dialect}'")

				self.WriteVerbose(f"  Reading {file}")
				return documentClass(file, parse=True)
			else:
				raise UnittestException(f"Unsupported unit testing report dataFormat for input: '{dataFormat}'")
		else:
			raise UnittestException(f"Syntax error: '{task}'")

	def _merge(self, testsuiteSummary: MergedTestsuiteSummary, task: str) -> None:
		parts = task.split(":")
		if (length := len(parts)) == 1:
			self.WriteError(f"Syntax error: '{task}'")
		elif length == 2:
			dialect, dataFormat = (x.lower() for x in parts[0].split("-"))
			globPattern = parts[1]

			foundFiles = tuple(f for f in Path.cwd().glob(globPattern))
			if len(foundFiles) == 0:
				self.WriteWarning(f"Found no matching files for pattern '{Path.cwd()}/{globPattern}'")
				return

			if dataFormat == "junit":
				if dialect == "ant":
					from pyEDAA.Reports.Unittesting.JUnit.AntJUnit4 import Document

					self._mergeJUnit(testsuiteSummary, Document, foundFiles, "Ant+JUnit4")
				elif dialect == "any":
					from pyEDAA.Reports.Unittesting.JUnit import Document

					self._mergeJUnit(testsuiteSummary, Document, foundFiles, "Any-JUnit")
				elif dialect == "ctest":
					from pyEDAA.Reports.Unittesting.JUnit.CTestJUnit import Document

					self._mergeJUnit(testsuiteSummary, Document, foundFiles, "CTest-JUnit")
				elif dialect == "gtest":
					from pyEDAA.Reports.Unittesting.JUnit.GoogleTestJUnit import Document

					self._mergeJUnit(testsuiteSummary, Document, foundFiles, "GoogleTest-JUnit")
				elif dialect == "pytest":
					from pyEDAA.Reports.Unittesting.JUnit.PyTestJUnit import Document

					self._mergeJUnit(testsuiteSummary, Document, foundFiles, "pyTest-JUnit")
				else:
					self.WriteError(f"Unsupported JUnit XML dialect for merging: '{dataFormat}-{dialect}'")
			else:
				self.WriteError(f"Unsupported unit testing report dataFormat for merging: '{dataFormat}'")
		else:
			self.WriteError(f"Syntax error: '{task}'")

	def _mergeJUnit(self, testsuiteSummary: MergedTestsuiteSummary, documentClass: Type[Document], foundFiles: Tuple[Path, ...], dialect: str) -> None:
		self.WriteNormal(f"Reading {len(foundFiles)} {dialect} unit test summary files ...")

		junitDocuments: List[documentClass] = []
		for file in foundFiles:
			self.WriteVerbose(f"  Reading {file}")
			try:
				junitDocuments.append(documentClass(file, analyzeAndConvert=True, readerMode=JUnitReaderMode.DecoupleTestsuiteHierarchyAndTestcaseClassName))
			except UnittestException as ex:
				self.WriteError(ex)

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
		parts = task.split(":")
		if (l := len(parts)) == 1:
			self.WriteError(f"Syntax error: '{task}'")
		elif l == 2:
			dialect, format = (x.lower() for x in parts[0].split("-"))
			outputFile = Path(parts[1])
			if format == "junit":
				if dialect == "ant":
					from pyEDAA.Reports.Unittesting.JUnit.AntJUnit4 import Document, UnittestException

					self._outputJUnit(testsuiteSummary, Document, outputFile, "Ant+JUnit4")
				elif dialect == "ctest":
					from pyEDAA.Reports.Unittesting.JUnit.CTestJUnit import Document, UnittestException

					self._outputJUnit(testsuiteSummary, Document, outputFile, "CTest-JUnit")
				elif dialect == "gtest":
					from pyEDAA.Reports.Unittesting.JUnit.GoogleTestJUnit import Document, UnittestException

					self._outputJUnit(testsuiteSummary, Document, outputFile, "GoogleTest-JUnit")
				elif dialect == "pytest":
					from pyEDAA.Reports.Unittesting.JUnit.PyTestJUnit import Document, UnittestException

					self._outputJUnit(testsuiteSummary, Document, outputFile, "pyTest-JUnit")
				else:
					self.WriteError(f"Unsupported JUnit XML dialect for writing: '{format}-{dialect}'")
			else:
				self.WriteError(f"Unsupported unit testing report format for writing: '{format}'")
		else:
			self.WriteError(f"Syntax error: '{task}'")

	def _outputJUnit(self, testsuiteSummary: TestsuiteSummary, documentClass: Type[Document], file: Path, dialect: str):
		self.WriteNormal(f"Writing merged unit test summaries to file ...")
		self.WriteVerbose(f"  Common Data Model -> OUT ({dialect}): {file}")

		junitDocument = documentClass.FromTestsuiteSummary(file, testsuiteSummary)
		try:
			junitDocument.Write(regenerate=True, overwrite=True)
		except UnittestException as ex:
			self.WriteError(str(ex))
			if ex.__cause__ is not None:
				self.WriteError(f"  {ex.__cause__}")

		self.WriteNormal(f"Output written to '{file}' in {dialect} format.")
