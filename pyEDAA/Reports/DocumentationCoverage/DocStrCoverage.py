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
# Copyright 2024-2026 Electronic Design Automation Abstraction (EDA²)                                                  #
# Copyright 2023-2023 Patrick Lehmann - Bötzingen, Germany                                                             #
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
Converter of `docstr_coverage <https://github.com/HunterMcGushion/docstr_coverage>`__'s analysis to the documentation
coverage model.

docstr_coverage counts modules, classes and functions only - no fields or variables -, and reports each by an
identifier of its own and its parent's name, without its kind or line. So the converter rebuilds the hierarchy from
these identifiers, and every item but a module or package is of kind
:attr:`~pyEDAA.Reports.DocumentationCoverage.ItemKind.Other`.

.. seealso::

   :mod:`pyEDAA.Reports.DocumentationCoverage.Python`
      |rarr| The reader of Python source files, which counts fields and variables too.
"""
from __future__                           import annotations

from datetime                             import timedelta
from pathlib                              import Path
from typing                               import Optional as Nullable

from docstr_coverage                      import analyze, ResultCollection
from docstr_coverage.result_collection    import ExpectedDocstring
from pyTooling.Common                     import getFullyQualifiedName
from pyTooling.Decorators                 import export, readonly
from pyTooling.MetaClasses                import ExtendedType
from pyTooling.Stopwatch                  import Stopwatch

from pyEDAA.Reports.DocumentationCoverage import CoverageState, DocCoverageError, DocumentationReport, Item, ItemKind


@export
class DocStrCoverageError(DocCoverageError):
	"""An analysis by docstr_coverage can't be run or converted."""


@export
class DocStrCoverage(metaclass=ExtendedType, slots=True):
	"""
	Runs docstr_coverage's analysis on a package's directory, and converts it to the documentation coverage model.
	"""

	_packageName:        str                         #: Name of the package.
	_searchDirectory:    Path                        #: The directory searched for Python source files.
	_moduleFiles:        list[Path]                  #: The Python source files found.
	_coverageReport:     Nullable[ResultCollection]  #: docstr_coverage's analysis, or ``None`` before :meth:`Analyze`.
	_analysisDuration:   Nullable[timedelta]         #: Duration of :meth:`Analyze`, or ``None`` before it ran.
	_conversionDuration: Nullable[timedelta]         #: Duration of :meth:`Convert`, or ``None`` before it ran.

	def __init__(self, packageName: str, directory: Path) -> None:
		"""
		Initializes the analysis of a package's directory, and searches it for Python source files.

		:param packageName:          Name of the package, which is the name of the top-level item, e.g. ``myPackage``.
		:param directory:            The package's directory.
		:raises ValueError:          If parameter ``packageName`` is ``None``.
		:raises TypeError:           If parameter ``packageName`` isn't of type :class:`str`.
		:raises ValueError:          If parameter ``packageName`` is empty.
		:raises ValueError:          If parameter ``directory`` is ``None``.
		:raises TypeError:           If parameter ``directory`` isn't of type :class:`~pathlib.Path`.
		:raises DocStrCoverageError: If the directory doesn't exist.
		"""
		if packageName is None:
			raise ValueError("Parameter 'packageName' is None.")
		elif not isinstance(packageName, str):
			ex = TypeError("Parameter 'packageName' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(packageName)}'.")
			raise ex
		elif packageName == "":
			raise ValueError("Parameter 'packageName' is empty.")

		if directory is None:
			raise ValueError("Parameter 'directory' is None.")
		elif not isinstance(directory, Path):
			ex = TypeError("Parameter 'directory' is not of type 'Path'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(directory)}'.")
			raise ex
		elif not directory.exists():
			raise DocStrCoverageError(f"Package source directory '{directory.as_posix()}' does not exist.") \
				from FileNotFoundError(f"Directory '{directory.as_posix()}' does not exist.")

		self._packageName =        packageName
		self._searchDirectory =    directory
		self._moduleFiles =        list(directory.glob("**/*.py"))
		self._coverageReport =     None
		self._analysisDuration =   None
		self._conversionDuration = None

	@readonly
	def SearchDirectory(self) -> Path:
		"""
		Read-only property to access the directory searched for Python source files (:attr:`_searchDirectory`).

		:returns: Path to the search directory.
		"""
		return self._searchDirectory

	@readonly
	def PackageName(self) -> str:
		"""
		Read-only property to access the name of the analyzed package (:attr:`_packageName`).

		:returns: Name of the package.
		"""
		return self._packageName

	@readonly
	def ModuleFiles(self) -> list[Path]:
		"""
		Read-only property to access the Python source files found in the search directory (:attr:`_moduleFiles`).

		:returns: List of module file paths.
		"""
		return self._moduleFiles

	@readonly
	def CoverageReport(self) -> Nullable[ResultCollection]:
		"""
		Read-only property to access docstr_coverage's analysis (:attr:`_coverageReport`).

		:returns: The analyzer's result collection, or ``None`` before :meth:`Analyze` ran.
		"""
		return self._coverageReport

	@readonly
	def AnalysisDuration(self) -> Nullable[timedelta]:
		"""
		Read-only property to access the duration of docstr_coverage's analysis (:attr:`_analysisDuration`).

		:returns: The duration, or ``None`` before :meth:`Analyze` ran.
		"""
		return self._analysisDuration

	@readonly
	def ModelConversionDuration(self) -> Nullable[timedelta]:
		"""
		Read-only property to access the duration of :meth:`Convert`: building the documentation coverage report
		(:attr:`_conversionDuration`).

		:returns: The duration, or ``None`` before :meth:`Convert` ran.
		"""
		return self._conversionDuration

	def Analyze(self) -> ResultCollection:
		"""
		Run docstr_coverage's analysis on the Python source files found, and measure its duration.

		:returns: The analyzer's result collection.
		"""
		with Stopwatch() as stopwatch:
			self._coverageReport = analyze(self._moduleFiles, show_progress=False)

		# WORKAROUND: pyTooling <10.0.0rc4
		# self._analysisDuration = stopwatch.Duration
		self._analysisDuration = timedelta(microseconds=stopwatch.DurationInNanoseconds / 1000)
		return self._coverageReport

	def Convert(self) -> DocumentationReport:
		"""
		Convert docstr_coverage's analysis to a documentation coverage report, aggregate it, and measure the duration.

		The report's :attr:`~pyEDAA.Reports.DocumentationCoverage.DocumentationReport.AnalysisDuration` is the
		duration of docstr_coverage's analysis.

		A source file is a module, an ``__init__.py`` the package of its directory, and a directory without
		``__init__.py`` a package without anything to document. docstr_coverage's identifier of an item names its parent:
		the item is added to the innermost item of that name, which encloses the item reported before.

		:returns:                    The report; its top-level item is the package.
		:raises DocStrCoverageError: If :meth:`Analyze` didn't run.
		"""
		if self._coverageReport is None:
			raise DocStrCoverageError("docstr_coverage's analysis didn't run.")

		def state(expected: ExpectedDocstring) -> CoverageState:
			"""
			Nested function returning the coverage state of an expected doc-string.

			:param expected: docstr_coverage's expected doc-string.
			:returns:        The coverage state.
			"""
			if expected.has_docstring:
				documentation = CoverageState.Documented | CoverageState.Covered
			else:
				documentation = CoverageState.Undocumented

			return (documentation | CoverageState.Ignored) if expected.ignore_reason else documentation

		with Stopwatch() as stopwatch:
			report = DocumentationReport(Path(self._packageName))
			packages: dict[tuple[str, ...], Item] = {}

			fileResults = {
				Path(path).relative_to(self._searchDirectory): fileResult for path, fileResult in self._coverageReport.files()
			}
			for path in sorted(fileResults, key=lambda path: (path.parent.parts, path.name != "__init__.py", path.name)):
				directoryParts = path.parent.parts
				parent: Item | DocumentationReport = report
				for depth in range(len(directoryParts) + 1):
					if (package := packages.get(directoryParts[:depth], None)) is None:
						if depth == len(directoryParts) and path.name == "__init__.py":
							break

						packageName = directoryParts[depth - 1] if depth > 0 else self._packageName
						package = Item(packageName, ItemKind.Package, CoverageState.Empty, parent=parent)
						packages[directoryParts[:depth]] = package

					parent = package

				moduleState = CoverageState.Empty
				expectedDocstrings: list[ExpectedDocstring] = []
				for expected in fileResults[path].expected_docstrings():
					if expected.node_identifier == "module docstring":
						moduleState = state(expected)
					else:
						expectedDocstrings.append(expected)

				file = report.GetOrAddFile(path)
				if path.name != "__init__.py":
					module = Item(path.stem, ItemKind.Module, moduleState, file=file, parent=parent)
				else:
					packageName = directoryParts[-1] if len(directoryParts) > 0 else self._packageName
					module = Item(packageName, ItemKind.Package, moduleState, file=file, parent=parent)
					packages[directoryParts] = module

				enclosing: list[Item] = [module]
				for expected in expectedDocstrings:
					parentName, _, name = expected.node_identifier.rpartition(".")
					while len(enclosing) > 1 and (parentName == "" or enclosing[-1]._name != parentName):
						enclosing.pop()

					enclosing.append(Item(name, ItemKind.Other, state(expected), file=file, parent=enclosing[-1]))

			report.Aggregate()

		report._analysisDuration = self._analysisDuration
		# WORKAROUND: pyTooling <10.0.0rc4
		# self._conversionDuration = stopwatch.Duration
		self._conversionDuration = timedelta(microseconds=stopwatch.DurationInNanoseconds / 1000)

		return report
