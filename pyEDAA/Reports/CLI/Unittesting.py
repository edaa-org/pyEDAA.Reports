from argparse import Namespace
from pathlib import Path
from typing import List

from pyTooling.Attributes.ArgParse import CommandHandler
from pyTooling.Attributes.ArgParse.ValuedFlag import LongValuedFlag
from pyTooling.MetaClasses import ExtendedType

from pyEDAA.Reports.Unittesting       import Document, MergedTestsuiteSummary, TestsuiteKind
from pyEDAA.Reports.Unittesting.JUnit import Document, JUnitReaderMode, UnittestException


class UnittestingHandlers(metaclass=ExtendedType, mixin=True):
	@CommandHandler("merge-unittest", help="Merge unit testing results.", description="Merge unit testing results.")
	@LongValuedFlag("--junit", dest="junit", metaName='JUnitFile', help="Unit testing summary file (XML).")
	@LongValuedFlag("--pytest", dest="pytest", metaName='Package', help="Remove pytest overhead.")
	def HandleMergeUnittest(self, args: Namespace) -> None:
		"""Handle program calls with command ``merge-unittest``."""
		self._PrintHeadline()

		returnCode = 0
		if args.junit is None:
			self.WriteError(f"Option '--junit <JUnitFile' is missing.")
			returnCode = 3

		if returnCode != 0:
			self.Exit(returnCode)

		foundFiles = [f for f in Path.cwd().glob(args.junit)]
		self.WriteNormal(f"Reading {len(foundFiles)} unit test summary files ...")

		junitDocuments: List[Document] = []
		self.WriteVerbose(f"IN (JUnit)  -> Common Data Model:      {args.junit}")
		for file in foundFiles:
			self.WriteVerbose(f"  reading {file}")
			junitDocuments.append(Document(file, parse=True, readerMode=JUnitReaderMode.DecoupleTestsuiteHierarchyAndTestcaseClassName))

		self.WriteNormal(f"Merging unit test summary files to a single file ...")

		merged = MergedTestsuiteSummary("PlatformTesting")
		for summary in junitDocuments:
			self.WriteVerbose(f"  merging {summary.Path}")
			merged.Merge(summary.ToTestsuiteSummary())

		self.WriteNormal(f"Aggregating unit test metrics ...")
		merged.Aggregate()

		self.WriteNormal(f"Flattening data structures to a single dimension ...")
		result = merged.ToTestsuiteSummary()

		if args.pytest is not None:
			self.WriteNormal(f"Simplifying unit testing reports created by pytest ...")

			cleanups = []
			for path in args.pytest.split(";"):
				suite = result
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
					self.WriteDebug(f"    {ts._name} -> {result._name}")
					ts._parent = None
					ts._kind = TestsuiteKind.Logical
					result.AddTestsuite(ts)

			self.WriteVerbose(f"  Deleting empty testsuites ...")
			for clean in cleanups:
				suite = clean
				while suite is not result:
					name = suite._name
					suite = suite._parent
					if name in suite._testsuites:
						self.WriteDebug(f"    delete '{name}'")
						del suite._testsuites[name]
					else:
						self.WriteDebug(f"    skipping '{name}'")
						break

		self.WriteNormal(f"Writing merged unit test summaries to file ...")
		mergedFile = Path.cwd() / Path("Unittesting.xml")
		self.WriteVerbose(f"  Common Data Model -> OUT (JUnit):      {mergedFile}")
		junitDocument = Document.FromTestsuiteSummary(mergedFile, result)
		try:
			junitDocument.Write(regenerate=True, overwrite=True)
		except UnittestException as ex:
			self.WriteError(str(ex))
			if ex.__cause__ is not None:
				self.WriteError(f"  {ex.__cause__}")

		self.WriteNormal(f"Output written to '{mergedFile}'.")
