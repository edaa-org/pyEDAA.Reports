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
coverage.py's dialect of the Cobertura XML code coverage format: read strictly, and converted to the common model.

coverage.py writes the dialect with ``coverage xml``. A report is validated against :file:`CoveragePy-Cobertura.xsd`,
reverse-engineered from coverage.py 7.x, which accepts what coverage.py writes and nothing else. The format's model is
the one of :mod:`pyEDAA.Reports.CodeCoverage.Cobertura`; a :class:`Line` also keeps the targets of its branches never
taken, which coverage.py adds as ``missing-branches``.

:meth:`Document.ToCoverageSummary` converts the model to the common model of :mod:`pyEDAA.Reports.CodeCoverage`:

* A class' ``filename`` is a file's path, relative to the ``<source>`` directory; coverage.py writes a class per file.
* A line's ``hits`` - ``0`` or ``1`` - says whether it ran: a line, which ran, is covered - partially covered, if one of
  its branches wasn't taken -, otherwise uncovered. The format has no counts.
* A branching line's ``condition-coverage`` - e.g. ``50% (1/2)`` - states its taken and all branches. A branch never
  taken names its target line - none for an exit of a function, which coverage.py states as ``exit`` -, a taken one
  doesn't.
* A file's directories become packages, the file a module spanning the whole file. The format names no classes or
  functions of the language.
* The format has no excluded lines.

.. rubric:: Example

.. code-block:: Python

   from pathlib import Path
   from pyEDAA.Reports.CodeCoverage.Cobertura.CoveragePyCobertura import Document

   report = Document(Path("coverage.xml"), analyzeAndConvert=True)
   summary = report.ToCoverageSummary()
   for unit in summary.IterateUnits():
     print(f"{unit.QualifiedName}: {unit.LineCoverage:.1%}")
"""
from __future__                            import annotations

from collections.abc                       import Iterable
from pathlib                               import Path
from typing                                import Optional as Nullable

from lxml.etree                            import _Element
from pyTooling.Decorators                  import export, readonly

from pyEDAA.Reports.CodeCoverage           import Branch as cc_Branch, CoverageSummary, Line as cc_Line
from pyEDAA.Reports.CodeCoverage           import LineCoverageStatus, Module as cc_Module, Package as cc_Package
from pyEDAA.Reports.CodeCoverage           import Unit as cc_Unit
from pyEDAA.Reports.CodeCoverage.Cobertura import CONDITION_COVERAGE, Document as cob_Document, Line as cob_Line


__all__ = ["READ_SCHEMA"]

READ_SCHEMA = "CoveragePy-Cobertura.xsd"  #: The XML schema a report is validated against when read: strict.


@export
class Line(cob_Line):
	"""
	A ``<line>`` as coverage.py writes it: whether it ran, and the targets of its branches never taken.
	"""

	_missingBranches: list[Nullable[int]]  #: Target lines of the branches never taken; ``None`` for a function's exit.

	def __init__(
		self,
		number: int,
		hits: int,
		branch: bool = False,
		conditionCoverage: Nullable[tuple[int, int]] = None,
		missingBranches: Nullable[Iterable[Nullable[int]]] = None
	) -> None:
		"""
		Initialize a line.

		:param number:            Line number.
		:param hits:              Whether the line ran: ``1`` or ``0``.
		:param branch:            Optional, whether the line branches. Default: ``False``.
		:param conditionCoverage: Optional, taken and all branches. Default: ``None``.
		:param missingBranches:   Optional, target lines of the branches never taken; ``None`` for an exit of a function.
		                          Default: none.
		"""
		super().__init__(number, hits, branch, conditionCoverage)

		self._missingBranches = [] if missingBranches is None else list(missingBranches)

	@readonly
	def MissingBranches(self) -> list[Nullable[int]]:
		"""
		Read-only property to access the target lines of the branches never taken (:attr:`_missingBranches`).

		:returns: The target lines, ``None`` for an exit of a function; empty, if the line took all its branches.
		"""
		return self._missingBranches


@export
class Document(cob_Document):
	"""
	A Cobertura XML code coverage report as coverage.py writes it: read strictly, and converted to the common model.
	"""

	def Analyze(self) -> None:
		"""
		Parse the XML file and validate it against the strict XML schema :data:`READ_SCHEMA`.

		:raises CodeCoverageError: If the file doesn't exist.
		:raises CodeCoverageError: If the file isn't well-formed XML.
		:raises CodeCoverageError: If the root element isn't ``<coverage>``.
		:raises CodeCoverageError: If the XML schema can't be located or parsed.
		:raises CodeCoverageError: If the file isn't valid according to the XML schema.
		"""
		self._Analyze(READ_SCHEMA)

	@staticmethod
	def _ConvertLine(lineElement: _Element) -> Line:
		"""
		Convert a ``<line>`` element and the targets of its branches never taken.

		:param lineElement: The ``<line>`` element.
		:returns:           The line.
		"""
		conditionCoverage = None
		if (match := CONDITION_COVERAGE.search(lineElement.attrib.get("condition-coverage", ""))) is not None:
			conditionCoverage = (int(match[1]), int(match[2]))

		missingBranches: list[Nullable[int]] = []
		if (targets := lineElement.attrib.get("missing-branches")) is not None:
			missingBranches.extend(None if target == "exit" else int(target) for target in targets.split(","))

		return Line(
			int(lineElement.attrib["number"]), int(lineElement.attrib["hits"]), "branch" in lineElement.attrib,
			conditionCoverage, missingBranches
		)

	def ToCoverageSummary(self) -> CoverageSummary:
		"""
		Convert the format's model to the common model, and aggregate it.

		A line, which ran, is covered - partially covered, if one of its branches wasn't taken -, otherwise uncovered; the
		format has no counts. A branch never taken names its target line, a taken one doesn't. A file's directories
		become packages, the file a module spanning the whole file.

		:returns:                  The report's root of the common model, named after the report file.
		:raises CodeCoverageError: If a file's path runs through another file.
		:raises CodeCoverageError: If two classes name the same file.
		"""
		summary = CoverageSummary(self._path.stem, sourceDirectories=[Path(source) for source in self._sources])

		for package in self._packages:
			for klass in package._classes:
				file = summary.GetOrAddFile(klass._filename)
				for line in klass._lines.values():
					covered, total = (0, 0) if line._conditionCoverage is None else line._conditionCoverage
					if line._hits == 0:
						status = LineCoverageStatus.Uncovered
					elif covered < total:
						status = LineCoverageStatus.PartiallyCovered
					else:
						status = LineCoverageStatus.Covered

					cc_Line(line._number, status, parent=file)

				lines =          file._lines
				lastLineNumber = file._lastLineNumber
				for line in klass._lines.values():
					source = lines[line._number]
					for _ in range(0 if line._conditionCoverage is None else line._conditionCoverage[0]):
						cc_Branch(LineCoverageStatus.Covered, parent=source)

					for target in line._missingBranches:
						cc_Branch(
							LineCoverageStatus.Uncovered,
							target=lines[target] if target is not None and target <= lastLineNumber else None,
							parent=source
						)

				path = Path(klass._filename)
				parent: cc_Unit | CoverageSummary = summary
				for part in path.parent.parts:
					parent = parent._units[part] if part in parent._units else cc_Package(part, parent=parent)

				cc_Module(
					path.stem,
					file=file,
					startLine=next(file.IterateLines(), None),
					endLine=lines[lastLineNumber] if lastLineNumber > 0 else None,
					parent=parent
				)

		summary.Aggregate()
		return summary
