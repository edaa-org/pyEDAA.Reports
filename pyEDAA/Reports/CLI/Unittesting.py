from argparse import Namespace
from pathlib import Path
from typing import List, Tuple

from pyTooling.Attributes.ArgParse import CommandHandler
from pyTooling.Attributes.ArgParse.ValuedFlag import LongValuedFlag
from pyTooling.MetaClasses import ExtendedType

from pyEDAA.Reports.Unittesting          import TestsuiteKind, TestsuiteSummary, MergedTestsuiteSummary


class UnittestingHandlers(metaclass=ExtendedType, mixin=True):
	@CommandHandler("unittest", help="Merge unit testing results.", description="Merge unit testing results.")
	@LongValuedFlag("--name", dest="name", metaName='Name', help="Top-level unit testing summary name.")
	@LongValuedFlag("--merge", dest="merge", metaName='format:JUnit File', help="Unit testing summary file (XML).")
	@LongValuedFlag("--pytest", dest="pytest", metaName='Package', help="Remove pytest overhead.")
	@LongValuedFlag("--render", dest="render", metaName='format', help="Render unit testing results to <format>.")
	@LongValuedFlag("--output", dest="output", metaName='format:JUnit File', help="Processed unit testing summary file (XML).")
	def HandleUnittest(self, args: Namespace) -> None:
		"""Handle program calls with command ``merge-unittest``."""
		self._PrintHeadline()

		returnCode = 0
		if args.merge is None:
			self.WriteError(f"Option '--merge=<Format>:<JUnitFilePattern>' is missing.")
			returnCode = 3

		if returnCode != 0:
			self.Exit(returnCode)

		testsuiteSummaryName = args.name if args.name is not None else "TestsuiteSummary"
		merged = MergedTestsuiteSummary(testsuiteSummaryName)

		mergeTasks: Tuple[str, ...] = (args.merge, )
		for mergeTask in mergeTasks:
			self._merge(merged, mergeTask)

		self.WriteNormal(f"Aggregating unit test metrics ...")
		merged.Aggregate()

		self.WriteNormal(f"Flattening data structures to a single dimension ...")
		result = merged.ToTestsuiteSummary()

		if args.pytest is not None:
			self._processingPyTest(result, args.pytest)

		if args.output is not None:
			outputs = (args.output, )
			for output in outputs:
				self._output(result, output)

		self.ExitOnPreviousErrors()

	def _merge(self, testsuiteSummary: MergedTestsuiteSummary, task: str) -> None:
		parts = task.split(":")
		if (l := len(parts)) == 1:
			self.WriteError(f"Syntax error: '{task}'")
		elif l == 2:
			dialect, format = (x.lower() for x in parts[0].split("-"))
			globPattern = parts[1]
			if format == "junit":
				if dialect == "ant":
					self._mergeAntJUnit(testsuiteSummary, globPattern)
				elif dialect == "ctest":
					self._mergeCTestJUnit(testsuiteSummary, globPattern)
				elif dialect == "gtest":
					self._mergeGoogleTestJUnit(testsuiteSummary, globPattern)
				elif dialect == "pytest":
					self._mergePyTestJUnit(testsuiteSummary, globPattern)
				else:
					self.WriteError(f"Unsupported JUnit XML dialect for merging: '{format}'")
			else:
				self.WriteError(f"Unsupported unit testing report format for merging: '{format}'")
		else:
			self.WriteError(f"Syntax error: '{task}'")

	def _mergeAntJUnit(self, testsuiteSummary: MergedTestsuiteSummary, globPattern: str) -> None:
		from pyEDAA.Reports.Unittesting.AntJUnit import Document, JUnitReaderMode

		foundFiles = [f for f in Path.cwd().glob(globPattern)]
		self.WriteNormal(f"Reading {len(foundFiles)} Ant-JUnit unit test summary files ...")

		junitDocuments: List[Document] = []
		for file in foundFiles:
			self.WriteVerbose(f"  reading {file}")
			junitDocuments.append(Document(file, parse=True, readerMode=JUnitReaderMode.DecoupleTestsuiteHierarchyAndTestcaseClassName))

		self.WriteNormal(f"Merging unit test summary files into a single data model ...")
		for summary in junitDocuments:
			self.WriteVerbose(f"  merging {summary.Path}")
			testsuiteSummary.Merge(summary.ToTestsuiteSummary())

	def _mergeCTestJUnit(self, testsuiteSummary: MergedTestsuiteSummary, globPattern: str) -> None:
		from pyEDAA.Reports.Unittesting.CTestJUnit import Document, JUnitReaderMode

		foundFiles = [f for f in Path.cwd().glob(globPattern)]
		self.WriteNormal(f"Reading {len(foundFiles)} CTest-JUnit unit test summary files ...")

		junitDocuments: List[Document] = []
		for file in foundFiles:
			self.WriteVerbose(f"  reading {file}")
			junitDocuments.append(Document(file, parse=True, readerMode=JUnitReaderMode.DecoupleTestsuiteHierarchyAndTestcaseClassName))

		self.WriteNormal(f"Merging unit test summary files into a single data model ...")
		for summary in junitDocuments:
			self.WriteVerbose(f"  merging {summary.Path}")
			testsuiteSummary.Merge(summary.ToTestsuiteSummary())

	def _mergeGoogleTestJUnit(self, testsuiteSummary: MergedTestsuiteSummary, globPattern: str) -> None:
		from pyEDAA.Reports.Unittesting.GoogleTestJUnit import Document, JUnitReaderMode

		foundFiles = [f for f in Path.cwd().glob(globPattern)]
		self.WriteNormal(f"Reading {len(foundFiles)} GoogleTest-JUnit unit test summary files ...")

		junitDocuments: List[Document] = []
		for file in foundFiles:
			self.WriteVerbose(f"  reading {file}")
			junitDocuments.append(Document(file, parse=True, readerMode=JUnitReaderMode.DecoupleTestsuiteHierarchyAndTestcaseClassName))

		self.WriteNormal(f"Merging unit test summary files into a single data model ...")
		for summary in junitDocuments:
			self.WriteVerbose(f"  merging {summary.Path}")
			testsuiteSummary.Merge(summary.ToTestsuiteSummary())

	def _mergePyTestJUnit(self, testsuiteSummary: MergedTestsuiteSummary, globPattern: str) -> None:
		from pyEDAA.Reports.Unittesting.PyTestJUnit import Document, JUnitReaderMode

		foundFiles = [f for f in Path.cwd().glob(globPattern)]
		if len(foundFiles) == 0:
			self.WriteWarning(f"Found no matching files for pattern '{Path.cwd()}/{globPattern}'")
			return

		self.WriteNormal(f"Reading {len(foundFiles)} pytest-JUnit unit test summary files ...")

		junitDocuments: List[Document] = []
		for file in foundFiles:
			self.WriteVerbose(f"  reading {file}")
			junitDocuments.append(Document(file, parse=True, readerMode=JUnitReaderMode.DecoupleTestsuiteHierarchyAndTestcaseClassName))

		self.WriteNormal(f"Merging unit test summary files into a single data model ...")
		for summary in junitDocuments:
			self.WriteVerbose(f"  merging {summary.Path}")
			testsuiteSummary.Merge(summary.ToTestsuiteSummary())

	def _processingPyTest(self, testsuiteSummary: TestsuiteSummary, paths: str) -> None:
		self.WriteNormal(f"Simplifying unit testing reports created by pytest ...")

		cleanups = []
		for path in paths.split(";"):
			suite = testsuiteSummary
			message = f"  Walking: {suite._name}"
			for element in path.split("."):
				if element in suite._testsuites:
					suite = suite._testsuites[element]
					message += f" -> {suite._name}"
				else:
					self.WriteVerbose(f"  Skipping: {path}")
					suite = None
					break

			if suite is None:
				continue

			self.WriteVerbose(message)
			cleanups.append(suite)

			self.WriteVerbose(f"  Moving testsuites ...")
			for ts in suite._testsuites.values():
				self.WriteDebug(f"    {ts._name} -> {testsuiteSummary._name}")
				ts._parent = None
				ts._kind = TestsuiteKind.Logical
				testsuiteSummary.AddTestsuite(ts)

		self.WriteVerbose(f"  Deleting empty testsuites ...")
		for clean in cleanups:
			suite = clean
			while suite is not testsuiteSummary:
				name = suite._name
				suite = suite._parent
				if name in suite._testsuites:
					self.WriteDebug(f"    delete '{name}'")
					del suite._testsuites[name]
				else:
					self.WriteDebug(f"    skipping '{name}'")
					break

	def _output(self, testsuiteSummary: TestsuiteSummary, task: str):
		parts = task.split(":")
		if (l := len(parts)) == 1:
			self.WriteError(f"Syntax error: '{task}'")
		elif l == 2:
			dialect, format = (x.lower() for x in parts[0].split("-"))
			outputFile = Path(parts[1])
			if format == "junit":
				if dialect == "ant":
					self._outputAntJUnit(testsuiteSummary, outputFile)
				# elif dialect == "ctest":
				# 	self._outputCTestJUnit(testsuiteSummary, outputFile)
				# elif dialect == "gtest":
				# 	self._outputGoogleTestJUnit(testsuiteSummary, outputFile)
				# elif dialect == "pytest":
				# 	self._outputPyTestJUnit(testsuiteSummary, outputFile)
				else:
					self.WriteError(f"Unsupported JUnit XML dialect for writing: '{format}'")
			else:
				self.WriteError(f"Unsupported unit testing report format for writing: '{format}'")
		else:
			self.WriteError(f"Syntax error: '{task}'")

	def _outputAntJUnit(self, testsuiteSummary: TestsuiteSummary, file: Path):
		from pyEDAA.Reports.Unittesting.AntJUnit import Document, UnittestException

		self.WriteNormal(f"Writing merged unit test summaries to file ...")
		self.WriteVerbose(f"  Common Data Model -> OUT (JUnit):      {file}")

		junitDocument = Document.FromTestsuiteSummary(file, testsuiteSummary)
		try:
			junitDocument.Write(regenerate=True, overwrite=True)
		except UnittestException as ex:
			self.WriteError(str(ex))
			if ex.__cause__ is not None:
				self.WriteError(f"  {ex.__cause__}")

		self.WriteNormal(f"Output written to '{file}' in Ant-JUnit format.")
