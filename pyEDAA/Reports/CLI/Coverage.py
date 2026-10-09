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

from pyTooling.Attributes.ArgParse            import CommandHandler, splitFormat
from pyTooling.Attributes.ArgParse.ValuedFlag import LongValuedFlag
from pyTooling.Common                         import StringEnum
from pyTooling.Decorators                     import export
from pyTooling.MetaClasses                    import ExtendedType

from pyEDAA.Reports.CodeCoverage                                 import CodeCoverageError, CoverageSummary
from pyEDAA.Reports.CodeCoverage                                 import Document as cc_Document
from pyEDAA.Reports.CodeCoverage.Cobertura                       import Document as CoberturaDocument
from pyEDAA.Reports.CodeCoverage.Cobertura.CoveragePyCobertura   import Document as CoveragePyCoberturaDocument
from pyEDAA.Reports.CodeCoverage.Cobertura.NVCCobertura          import Document as NVCCoberturaDocument
from pyEDAA.Reports.CodeCoverage.CoveragePy                      import Document as CoveragePyDocument
from pyEDAA.Reports.CodeCoverage.Gcov                            import Document as GcovDocument
from pyEDAA.Reports.CodeCoverage.GHDL                            import Document as GHDLDocument
from pyEDAA.Reports.CodeCoverage.JaCoCo                          import Document as JaCoCoDocument
from pyEDAA.Reports.CodeCoverage.LCOV                            import Document as LCOVDocument


__all__ = ["INPUT_FORMATS"]


@export
class InputFormat(StringEnum):
	"""The code coverage formats ``--input`` reads, by their name on the command line."""

	AnyCobertura =        "Any-Cobertura"         #: Cobertura XML of any tool, read leniently.
	CoveragePyCobertura = "CoveragePy-Cobertura"  #: Cobertura XML as coverage.py writes it.
	CoveragePyJSON =      "CoveragePy-JSON"       #: coverage.py's JSON report.
	GcovJSON =            "Gcov-JSON"             #: GCC's gcov JSON report.
	GHDLJSON =            "GHDL-JSON"             #: GHDL's coverage file.
	JaCoCoXML =           "JaCoCo-XML"            #: JaCoCo's XML report.
	LCOV =                "LCOV"                  #: lcov's tracefile.
	NVCCobertura =        "NVC-Cobertura"         #: Cobertura XML as NVC writes it.

	DEFAULT = AnyCobertura                        #: A file without format is read as Cobertura XML.


@export
class OutputFormat(StringEnum):
	"""The code coverage formats ``--output`` writes, by their name on the command line."""

	Cobertura = "Cobertura"  #: Cobertura XML, after Cobertura's DTD ``coverage-04.dtd``.

	DEFAULT = Cobertura      #: A file without format is written as Cobertura XML.


#: The document class reading each input format.
INPUT_FORMATS: Dict[InputFormat, Type[cc_Document]] = {
	InputFormat.AnyCobertura:        CoberturaDocument,
	InputFormat.CoveragePyCobertura: CoveragePyCoberturaDocument,
	InputFormat.CoveragePyJSON:      CoveragePyDocument,
	InputFormat.GcovJSON:            GcovDocument,
	InputFormat.GHDLJSON:            GHDLDocument,
	InputFormat.JaCoCoXML:           JaCoCoDocument,
	InputFormat.LCOV:                LCOVDocument,
	InputFormat.NVCCobertura:        NVCCoberturaDocument
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
		"--input", dest="input", metaName="[Format:]File", optional=True,
		help="Code coverage report to read, e.g. 'Gcov-JSON:main.gcov.json.gz'; without format: Any-Cobertura."
	)
	@LongValuedFlag(
		"--output", dest="output", metaName="[Format:]File", optional=True,
		help="Code coverage report to write, e.g. 'Cobertura:coverage.xml'; without format: Cobertura."
	)
	def HandleCoverage(self, args: Namespace) -> None:
		"""Handle program calls with command ``coverage``."""
		self._PrintHeadline()

		if args.input is None:
			self.WriteError(f"Option '--input=[<Format>:]<File>' is missing.")
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

		:param task:               The option's value: ``[<Format>:]<File>``, e.g. ``Gcov-JSON:main.gcov.json.gz``.
		:returns:                  The report's summary in the common model.
		:raises CodeCoverageError: If the format isn't supported. |br|
		                           The exception notes the supported formats.
		:raises CodeCoverageError: If the report can't be read.
		"""
		try:
			inputFormat, file = splitFormat(task, InputFormat)
		except ValueError as ex:
			error = CodeCoverageError(f"Unsupported code coverage format for input: '{task}'.")
			error.add_note(f"Supported formats: {', '.join(InputFormat)}; without format: {InputFormat.DEFAULT}.")
			raise error from ex

		self.WriteNormal(f"Reading code coverage report '{file}' ({inputFormat}) ...")
		document = INPUT_FORMATS[inputFormat](file, analyzeAndConvert=True)
		return document.ToCoverageSummary()

	def _WriteCoverage(self, summary: CoverageSummary, task: str) -> None:
		"""
		Write the common model as a code coverage report.

		:param summary: The summary to write.
		:param task:    The option's value: ``[<Format>:]<File>``, e.g. ``Cobertura:coverage.xml``.
		"""
		try:
			_, file = splitFormat(task, OutputFormat)
		except ValueError:
			self.WriteError(f"Unsupported code coverage format for output: '{task}'.")
			formats = ", ".join(OutputFormat)
			self.WriteNormal(f"           Supported formats: {formats}; without format: {OutputFormat.DEFAULT}.")
			return

		self.WriteNormal(f"Writing Cobertura XML report '{file}' ...")
		try:
			CoberturaDocument.FromCoverageSummary(file, summary).Write(overwrite=True, regenerate=True)
		except CodeCoverageError as ex:
			self.WriteError(str(ex))
