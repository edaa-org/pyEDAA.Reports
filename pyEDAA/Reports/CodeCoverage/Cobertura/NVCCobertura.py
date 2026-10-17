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
NVC's dialect of the Cobertura XML code coverage format: read strictly, and converted to the common model.

NVC writes the dialect with ``nvc --cover-export --format=cobertura``. A report is validated against
:file:`NVC-Cobertura.xsd`, reverse-engineered from NVC 1.23, which accepts what NVC writes and nothing else. The
format's model is the one of :mod:`pyEDAA.Reports.CodeCoverage.Cobertura`; a :class:`Class` is a design unit and also
keeps its entity and architecture.

:meth:`Document.ToCoverageSummary` converts the model to the common model of :mod:`pyEDAA.Reports.CodeCoverage`:

* A class' ``filename`` is a file's path, relative to the directory named by ``--relative``. Classes of one file - e.g.
  the architectures of an entity with statements - are one file, their lines merged.
* A line's ``hits`` is its count: how often the statements starting in the line ran, added for all of them and all
  instances of the design unit. A line without a statement - e.g. an ``elsif`` - has hits ``0``.
* A branching line's ``condition-coverage`` - ``0 %``, ``50 %`` or ``100 %`` - states how many directions of its
  conditions - each ``<condition>`` a true and a false one - were taken. They become as many branches without count. A
  line, which ran or took a branch, is covered - partially covered, if one of its branches wasn't taken -, otherwise
  uncovered; a line without a statement, which took a branch, has no count.
* The package - a library - becomes a package, a class' entity a module in it, its architecture a module in the entity,
  spanning its file from the first to the last line it lists.
* The format has no excluded lines.

.. rubric:: Example

.. code-block:: Python

   from pathlib import Path
   from pyEDAA.Reports.CodeCoverage.Cobertura.NVCCobertura import Document

   report = Document(Path("coverage.xml"), analyzeAndConvert=True)
   summary = report.ToCoverageSummary()
   for unit in summary.IterateUnits():
     print(f"{unit.QualifiedName}: {unit.LineCoverage:.1%}")
"""
from __future__                                    import annotations

from pathlib                                       import Path
from typing                                        import Optional as Nullable

from lxml.etree                                    import _Element
from pyTooling.Common                              import getFullyQualifiedName
from pyTooling.Decorators                          import export, readonly

from pyEDAA.Reports.CodeCoverage                   import Branch as cc_Branch, CoverageSummary, File as cc_File
from pyEDAA.Reports.CodeCoverage                   import Line as cc_Line, LineCoverageStatus, Module as cc_Module
from pyEDAA.Reports.CodeCoverage                   import Package as cc_Package
from pyEDAA.Reports.CodeCoverage.Cobertura         import Document as cob_Document, _float
from pyEDAA.Reports.CodeCoverage.Cobertura.Records import Class as cob_Class, Condition, Line


__all__ = ["READ_SCHEMA"]

READ_SCHEMA = "NVC-Cobertura.xsd"  #: The XML schema a report is validated against when read: strict.


@export
class Class(cob_Class):
	"""
	A ``<class>`` as NVC writes it: a design unit, its entity and architecture.

	Entity ``COUNTER`` with architecture ``RTL`` is named ``COUNTER(RTL)``.
	"""

	_entity:       str  #: Name of the design unit's entity.
	_architecture: str  #: Name of the design unit's architecture.

	def __init__(
		self,
		entity: str,
		architecture: str,
		filename: str,
		lineRate: Nullable[float] = None,
		branchRate: Nullable[float] = None,
		complexity: Nullable[float] = None
	) -> None:
		"""
		Initialize a design unit.

		The class' name is the entity's, followed by the architecture's in parentheses, e.g. ``COUNTER(RTL)``.

		:param entity:       Name of the design unit's entity.
		:param architecture: Name of the design unit's architecture.
		:param filename:     Path of the design unit's source file, relative to the directory named by ``--relative``.
		:param lineRate:     Optional, line coverage, as the report states it. Default: ``None``.
		:param branchRate:   Optional, branch coverage, as the report states it. Default: ``None``.
		:param complexity:   Optional, complexity, as the report states it. Default: ``None``.
		:raises ValueError:  If parameter ``entity`` is ``None``.
		:raises TypeError:   If parameter ``entity`` isn't of type :class:`str`.
		:raises ValueError:  If parameter ``entity`` is empty.
		:raises ValueError:  If parameter ``architecture`` is ``None``.
		:raises TypeError:   If parameter ``architecture`` isn't of type :class:`str`.
		:raises ValueError:  If parameter ``architecture`` is empty.
		"""
		super().__init__(f"{entity}({architecture})", filename, lineRate, branchRate, complexity)

		if entity is None:
			raise ValueError(f"Parameter 'entity' is None.")
		elif not isinstance(entity, str):
			ex = TypeError(f"Parameter 'entity' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(entity)}'.")
			raise ex
		elif entity == "":
			raise ValueError(f"Parameter 'entity' is empty.")

		if architecture is None:
			raise ValueError(f"Parameter 'architecture' is None.")
		elif not isinstance(architecture, str):
			ex = TypeError(f"Parameter 'architecture' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(architecture)}'.")
			raise ex
		elif architecture == "":
			raise ValueError(f"Parameter 'architecture' is empty.")

		self._entity =       entity
		self._architecture = architecture

	@readonly
	def Entity(self) -> str:
		"""
		Read-only property to access the name of the design unit's entity (:attr:`_entity`).

		NVC writes it in upper case, e.g. ``COUNTER``.

		:returns: The entity's name.
		"""
		return self._entity

	@readonly
	def Architecture(self) -> str:
		"""
		Read-only property to access the name of the design unit's architecture (:attr:`_architecture`).

		NVC writes it in upper case, e.g. ``RTL``.

		:returns: The architecture's name.
		"""
		return self._architecture


@export
class Document(cob_Document):
	"""
	A Cobertura XML code coverage report as NVC writes it: read strictly, and converted to the common model.
	"""

	def Analyze(self) -> None:
		"""
		Parse the XML file and validate it against the strict XML schema :data:`READ_SCHEMA`.

		:raises CodeCoverageError: If the file doesn't exist.
		:raises CodeCoverageError: If the file can't be read.
		:raises CodeCoverageError: If the file isn't well-formed XML.
		:raises CodeCoverageError: If the root element isn't ``<coverage>``.
		:raises CodeCoverageError: If the XML schema can't be located or parsed.
		:raises CodeCoverageError: If the file isn't valid according to the XML schema.
		"""
		self._Analyze(READ_SCHEMA)

	@classmethod
	def _ConvertClass(cls, classElement: _Element) -> Class:
		"""
		Convert a ``<class>`` element - a design unit - and its lines.

		:param classElement: The ``<class>`` element.
		:returns:            The design unit.
		"""
		entity, _, architecture = classElement.attrib["name"].partition("(")
		klass = Class(
			entity, architecture[:-1], classElement.attrib["filename"], _float(classElement, "line-rate"),
			_float(classElement, "branch-rate"), _float(classElement, "complexity")
		)

		for lineElement in classElement.iterfind("lines/line"):  # type: _Element
			line = cls._ConvertLine(lineElement)
			klass._lines[line._number] = line

		return klass

	@staticmethod
	def _ConvertLine(lineElement: _Element) -> Line:
		"""
		Convert a ``<line>`` element and its conditions.

		The line's taken and all branches are figured from its ``condition-coverage`` and its conditions, each a true and
		a false direction.

		:param lineElement: The ``<line>`` element.
		:returns:           The line.
		"""
		conditions = [
			Condition(int(element.attrib["number"]), element.attrib["type"], element.attrib["coverage"])
			for element in lineElement.iterfind("conditions/condition")
		]

		conditionCoverage = None
		if (percentage := lineElement.attrib.get("condition-coverage")) is not None:
			total = 2 * len(conditions)
			conditionCoverage = (int(percentage.removesuffix(" %")) * total // 100, total)

		return Line(
			int(lineElement.attrib["number"]), int(lineElement.attrib["hits"]), lineElement.attrib["branch"] == "true",
			conditionCoverage, conditions
		)

	def ToCoverageSummary(self) -> CoverageSummary:
		"""
		Convert the format's model to the common model, and aggregate it.

		Several classes of one file are one file: a line listed by several of them has their hits added, and of its
		branches the higher number taken. A line, which ran or took a branch, is covered - partially covered, if one of
		its branches wasn't taken -, otherwise uncovered; a line without a statement, which took a branch, has no count.
		The package becomes a package, a class' entity a module in it, its architecture a module in the entity, spanning
		its file from its first to its last line.

		:returns:                  The report's root of the common model, named after the report file.
		:raises CodeCoverageError: If a file's path runs through another file.
		"""
		summary = CoverageSummary(self._path.stem, sourceDirectories=[Path(source) for source in self._sources])

		merged: dict[int, dict[int, tuple[int, int, int]]] = {}
		files: dict[int, cc_File] = {}
		for package in self._packages:
			for klass in package._classes:
				file = summary.GetOrAddFile(klass._filename)
				files[id(file)] = file
				lines = merged.setdefault(id(file), {})
				for line in klass._lines.values():
					covered, total = (0, 0) if line._conditionCoverage is None else line._conditionCoverage
					hits, oldCovered, oldTotal = lines.get(line._number, (0, 0, 0))
					lines[line._number] = (hits + line._hits, max(covered, oldCovered), max(total, oldTotal))

		for fileID, lines in merged.items():
			file = files[fileID]
			for number in sorted(lines):
				hits, covered, total = lines[number]
				branches = [cc_Branch(LineCoverageStatus.Covered) for _ in range(covered)]
				branches.extend(cc_Branch(LineCoverageStatus.Uncovered) for _ in range(total - covered))
				if hits == 0 and covered == 0:
					status = LineCoverageStatus.Uncovered
				elif covered < total:
					status = LineCoverageStatus.PartiallyCovered
				else:
					status = LineCoverageStatus.Covered

				cc_Line(number, status, None if hits == 0 and covered > 0 else hits, branches, parent=file)

		for package in self._packages:
			if (library := summary._units.get(package._name)) is None:
				library = cc_Package(package._name, parent=summary)

			for klass in package._classes:
				if (entity := library._units.get(klass._entity)) is None:
					entity = cc_Module(klass._entity, parent=library)

				if klass._architecture not in entity._units:
					file = summary.GetOrAddFile(klass._filename)
					numbers = list(klass._lines)
					cc_Module(
						klass._architecture,
						file=file,
						startLine=file._lines[min(numbers)] if len(numbers) > 0 else None,
						endLine=file._lines[max(numbers)] if len(numbers) > 0 else None,
						parent=entity
					)

		summary.Aggregate()
		return summary
