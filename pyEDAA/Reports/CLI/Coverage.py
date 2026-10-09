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
The CLI command ``coverage``: read a code coverage report of any supported format, convert it to the common model of
:mod:`pyEDAA.Reports.CodeCoverage`, show its figures, and write it as Cobertura XML.
"""
from __future__ import annotations

from argparse import Namespace
from pathlib  import Path
from typing   import Dict, Type

from pyTooling.Attributes.ArgParse            import CommandHandler
from pyTooling.Attributes.ArgParse.ValuedFlag import LongValuedFlag
from pyTooling.Decorators                     import export
from pyTooling.MetaClasses                    import ExtendedType

from pyEDAA.Reports.CodeCoverage                                 import CodeCoverageError, CoverageSummary
from pyEDAA.Reports.CodeCoverage                                 import Document as cc_Document
from pyEDAA.Reports.CodeCoverage.Cobertura                       import Document as CoberturaDocument
from pyEDAA.Reports.CodeCoverage.Cobertura.CoveragePyCobertura   import Document as CoveragePyCoberturaDocument
from pyEDAA.Reports.CodeCoverage.CoveragePy                      import Document as CoveragePyDocument
from pyEDAA.Reports.CodeCoverage.Gcov                            import Document as GcovDocument
from pyEDAA.Reports.CodeCoverage.GHDL                            import Document as GHDLDocument
from pyEDAA.Reports.CodeCoverage.LCOV                            import Document as LCOVDocument


#: The formats ``--input`` reads, by their lower-case name on the command line.
INPUT_FORMATS: Dict[str, Type[cc_Document]] = {
	"any-cobertura":        CoberturaDocument,
	"coveragepy-cobertura": CoveragePyCoberturaDocument,
	"coveragepy-json":      CoveragePyDocument,
	"gcov-json":            GcovDocument,
	"ghdl-json":            GHDLDocument,
	"lcov":                 LCOVDocument
}


@export
class CoverageHandlers(metaclass=ExtendedType, mixin=True):
	"""A mixin-class adding the CLI command ``coverage``."""

	@CommandHandler(
		"coverage",
		help="Transform code coverage reports.",
		description="Read a code coverage report and convert it to Cobertura XML."
	)
	@LongValuedFlag(
		"--input", dest="input", metaName="Format:File", optional=True,
		help="Code coverage report to read, e.g. 'Gcov-JSON:main.gcov.json.gz'."
	)
	@LongValuedFlag(
		"--output", dest="output", metaName="Format:File", optional=True,
		help="Code coverage report to write, e.g. 'Cobertura:coverage.xml'."
	)
	def HandleCoverage(self, args: Namespace) -> None:
		"""Handle program calls with command ``coverage``."""
		self._PrintHeadline()

		if args.input is None:
			self.WriteError(f"Option '--input=<Format>:<File>' is missing.")
			self.Exit(3)

		try:
			summary = self._ReadCoverage(args.input)
		except CodeCoverageError as ex:
			self.WriteFatal(str(ex), immediateExit=False)
			for note in getattr(ex, "__notes__", []):
				self.WriteNormal(f"           {note}")
			self.Exit(1)

		lines =    f"{summary.CoveredLines} of {summary.TotalLines}"
		branches = f"{summary.CoveredBranches} of {summary.TotalBranches}"
		self.WriteNormal(f"Lines:    {lines} covered ({summary.LineCoverage:.1%})")
		if summary.TotalBranches > 0:
			self.WriteNormal(f"Branches: {branches} covered ({summary.BranchCoverage:.1%})")

		for file in summary.IterateFiles():
			lines = f"{file.CoveredLines} of {file.TotalLines}"
			self.WriteVerbose(f"  {file.Path.as_posix()}: {lines} lines ({file.LineCoverage:.1%})")

		if args.output is not None:
			self._WriteCoverage(summary, args.output)

		self.ExitOnPreviousErrors()

	def _ReadCoverage(self, task: str) -> CoverageSummary:
		"""
		Read a code coverage report and convert it to the common model.

		:param task:               The option's value: ``<Format>:<File>``, e.g. ``Gcov-JSON:main.gcov.json.gz``.
		:returns:                  The report's summary in the common model.
		:raises CodeCoverageError: If the value isn't ``<Format>:<File>``.
		:raises CodeCoverageError: If the format isn't supported. |br|
		                           The exception notes the supported formats.
		:raises CodeCoverageError: If the report can't be read.
		"""
		if ":" not in task:
			raise CodeCoverageError(f"Syntax error in '--input={task}': expected '<Format>:<File>'.")

		formatName, fileName = task.split(":", maxsplit=1)
		if (documentClass := INPUT_FORMATS.get(formatName.lower())) is None:
			ex = CodeCoverageError(f"Unsupported code coverage format for input: '{formatName}'.")
			ex.add_note(f"Supported formats: {', '.join(INPUT_FORMATS)} (case-insensitive).")
			raise ex

		self.WriteNormal(f"Reading code coverage report '{fileName}' ({formatName}) ...")
		document = documentClass(Path(fileName), analyzeAndConvert=True)
		return document.ToCoverageSummary()

	def _WriteCoverage(self, summary: CoverageSummary, task: str) -> None:
		"""
		Write the common model as a code coverage report.

		:param summary: The summary to write.
		:param task:    The option's value: ``<Format>:<File>``, e.g. ``Cobertura:coverage.xml``.
		"""
		if ":" not in task:
			self.WriteError(f"Syntax error in '--output={task}': expected '<Format>:<File>'.")
			return

		formatName, fileName = task.split(":", maxsplit=1)
		if formatName.lower() != "cobertura":
			self.WriteError(f"Unsupported code coverage format for output: '{formatName}'. Supported format: cobertura.")
			return

		self.WriteNormal(f"Writing Cobertura XML report '{fileName}' ...")
		try:
			CoberturaDocument.FromCoverageSummary(Path(fileName), summary).Write(overwrite=True, regenerate=True)
		except CodeCoverageError as ex:
			self.WriteError(str(ex))
