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
The scopes of QuestaSim's coverage report XML: instances, design units and source files, with their coverage statistics
and their coverage items.

Which kind of scope a report lists, its mode decides
(:class:`~pyEDAA.Reports.CodeCoverage.QuestaSim.Elements.ReportMode`). With details (``vcover report -details``), a
scope names its source files in a source table and lists its coverage items
(:mod:`~pyEDAA.Reports.CodeCoverage.QuestaSim.Details`, :mod:`~pyEDAA.Reports.CodeCoverage.QuestaSim.StateMachines`):
statements, ``if`` and ``case`` statements with their branches, and the states and transitions of finite state machines.
"""
from __future__                                          import annotations

from pathlib                                             import Path
from typing                                              import TYPE_CHECKING, Mapping, Optional as Nullable, Self

from lxml.etree                                          import _Element
from pyTooling.Common                                    import getFullyQualifiedName
from pyTooling.Decorators                                import export, readonly

from pyEDAA.Reports.CodeCoverage                         import CodeCoverageError
from pyEDAA.Reports.CodeCoverage.QuestaSim.Details       import CaseStatement, IfStatement, Statement
from pyEDAA.Reports.CodeCoverage.QuestaSim.StateMachines import FSMState, FSMTransition
from pyEDAA.Reports.CodeCoverage.QuestaSim.Elements      import StatisticsMixin

if TYPE_CHECKING:
	from pyEDAA.Reports.CodeCoverage.QuestaSim             import Report


# A class with a property named like a class - ``Path`` - can't name that class in the annotation of a field: the class
# body's namespace, where annotations are evaluated, binds the name to the property.
_Path = Path

@export
class Scope(StatisticsMixin, slots=True):
	"""
	Base-class of the scopes: an instance, a design unit or a source file, with its coverage statistics, its source files
	and its statements.
	"""

	_parent:         Nullable[Report]     #: The report the scope belongs to.
	_files:          dict[int, Path]      #: The source files, by the number the report gives them.
	_statements:     list[Statement]      #: The statements.
	_ifStatements:   list[IfStatement]    #: The ``if`` statements.
	_caseStatements: list[CaseStatement]  #: The ``case`` statements.
	_states:         list[FSMState]       #: The states of finite state machines.
	_transitions:    list[FSMTransition]  #: The transitions of finite state machines.

	def __init__(self, files: Nullable[Mapping[int, Path]] = None, *, parent: Nullable[Report] = None) -> None:
		"""
		Initialize the scope, and append it to the scopes of its report.

		Its coverage statistics and coverage items are added by creating them with this scope as their parent.

		:param files:       Optional, the source files, by the number the report gives them. Default: ``None``.
		:param parent:      Optional, the report the scope belongs to; the scope is appended to its scopes. Default:
		                    ``None``.
		:raises TypeError:  If parameter ``files`` isn't a mapping.
		:raises TypeError:  If parameter ``files`` contains a key not of type :class:`int`.
		:raises ValueError: If parameter ``files`` contains a negative key.
		:raises TypeError:  If parameter ``files`` contains a value not of type :class:`~pathlib.Path`.
		:raises TypeError:  If parameter ``parent`` isn't of type
		                    :class:`~pyEDAA.Reports.CodeCoverage.QuestaSim.Report`.
		"""
		from pyEDAA.Reports.CodeCoverage.QuestaSim import Report

		super().__init__()

		self._files = {}
		if files is not None:
			if not isinstance(files, Mapping):
				ex = TypeError(f"Parameter 'files' is not a mapping.")
				ex.add_note(f"Got type '{getFullyQualifiedName(files)}'.")
				raise ex

			for fileNumber, path in files.items():
				if not isinstance(fileNumber, int):
					ex = TypeError(f"Parameter 'files' contains a key not of type 'int'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(fileNumber)}'.")
					raise ex
				elif fileNumber < 0:
					ex = ValueError(f"Parameter 'files' contains a negative key.")
					ex.add_note(f"Got value '{fileNumber}'.")
					raise ex
				elif not isinstance(path, Path):
					ex = TypeError(f"Parameter 'files' contains a value not of type 'Path'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(path)}'.")
					raise ex

				self._files[fileNumber] = path

		if parent is not None and not isinstance(parent, Report):
			ex = TypeError(f"Parameter 'parent' is not of type 'Report'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =         parent
		self._statements =     []
		self._ifStatements =   []
		self._caseStatements = []
		self._states =         []
		self._transitions =    []

		if parent is not None:
			parent._scopes.append(self)

	@staticmethod
	def _ParseSourceTable(element: _Element) -> dict[int, Path]:
		"""
		Parse the source files of a scope's ``<sourceTable>``.

		:param element: The scope's element.
		:returns:       The source files, by their number; none, if the scope has no source table.
		"""
		return {
			int(fileMap.attrib["fn"]): Path(fileMap.attrib["path"]) for fileMap in element.iterfind("sourceTable/fileMap")
		}

	def _ParseItems(self, element: _Element) -> None:
		"""
		Parse the coverage statistics and the coverage items of the scope from its element.

		:param element:            The scope's element.
		:raises CodeCoverageError: If a coverage statistics element states more hit items than items.
		:raises CodeCoverageError: If the scope states a kind of coverage statistics twice.
		:raises CodeCoverageError: If a coverage item names an unknown file number, or none in a scope of several files.
		:raises CodeCoverageError: If an ``if`` or ``case`` statement states other figures than its branches have.
		:raises CodeCoverageError: If a transition's name doesn't name its two states.
		"""
		self._ParseStatistics(element)
		for child in element:
			if child.tag == "stmt":
				Statement.Parse(child, parent=self)
			elif child.tag == "if":
				IfStatement.Parse(child, parent=self)
			elif child.tag == "case":
				CaseStatement.Parse(child, parent=self)
			elif child.tag == "state":
				FSMState.Parse(child, parent=self)
			elif child.tag == "trans":
				FSMTransition.Parse(child, parent=self)

	def _ResolveFile(self, element: _Element) -> Path:
		"""
		Return the source file a coverage item's element names by its file number.

		An element without file number is in the scope's file: the path of a ``<fileData>``, or the only file of the source
		table.

		:param element:            The coverage item's element, e.g. a ``<stmt>``.
		:returns:                  The source file's path, as the report states it.
		:raises CodeCoverageError: If the file number isn't in the scope's source table.
		:raises CodeCoverageError: If the element names no file number, and the scope has no single file.
		"""
		if (fileNumber := element.attrib.get("fn")) is not None:
			if (file := self._files.get(int(fileNumber))) is None:
				ex = CodeCoverageError(
					f"'<{element.tag}>' in line {element.sourceline} names file number '{fileNumber}', which is unknown."
				)
				ex.add_note(f"Known file numbers: {', '.join(str(number) for number in self._files) or 'none'}.")
				raise ex

			return file
		elif isinstance(self, FileData):
			return self._path
		elif len(self._files) == 1:
			return next(iter(self._files.values()))

		ex = CodeCoverageError(f"'<{element.tag}>' in line {element.sourceline} names no file number.")
		ex.add_note(f"Its scope names {len(self._files)} files.")
		raise ex

	@readonly
	def Parent(self) -> Nullable[Report]:
		"""
		Read-only property to access the report the scope belongs to (:attr:`_parent`).

		:returns: The report; ``None`` if the scope belongs to none.
		"""
		return self._parent

	@readonly
	def Files(self) -> dict[int, Path]:
		"""
		Read-only property to access the source files (:attr:`_files`).

		:returns: The source files, by the number the report gives them; none, if the report has no details.
		"""
		return self._files

	@readonly
	def Statements(self) -> list[Statement]:
		"""
		Read-only property to access the statements (:attr:`_statements`).

		:returns: The statements, in the order the report lists them; none, if the report has no details.
		"""
		return self._statements

	@readonly
	def IfStatements(self) -> list[IfStatement]:
		"""
		Read-only property to access the ``if`` statements (:attr:`_ifStatements`).

		:returns: The ``if`` statements, in the order the report lists them; none, if the report has no details.
		"""
		return self._ifStatements

	@readonly
	def CaseStatements(self) -> list[CaseStatement]:
		"""
		Read-only property to access the ``case`` statements (:attr:`_caseStatements`).

		:returns: The ``case`` statements, in the order the report lists them; none, if the report has no details.
		"""
		return self._caseStatements

	@readonly
	def States(self) -> list[FSMState]:
		"""
		Read-only property to access the states of finite state machines (:attr:`_states`).

		:returns: The states, in the order the report lists them; none, if the report has no details.
		"""
		return self._states

	@readonly
	def Transitions(self) -> list[FSMTransition]:
		"""
		Read-only property to access the transitions of finite state machines (:attr:`_transitions`).

		:returns: The transitions, in the order the report lists them; none, if the report has no details.
		"""
		return self._transitions


@export
class InstanceData(Scope):
	"""
	An ``<instanceData>``: an instance of a design unit, or a package.
	"""

	_path:          str            #: Hierarchical path of the instance.
	_designUnit:    str            #: Name of the design unit.
	_secondaryUnit: Nullable[str]  #: Name of the secondary unit (the architecture), if the design unit has one.

	def __init__(
		self,
		path: str,
		designUnit: str,
		secondaryUnit: Nullable[str] = None,
		files: Nullable[Mapping[int, Path]] = None,
		*,
		parent: Nullable[Report] = None
	) -> None:
		"""
		Initialize the instance, and append it to the scopes of its report.

		:param path:          Hierarchical path of the instance, separated by ``/``.
		:param designUnit:    Name of the design unit.
		:param secondaryUnit: Optional, name of the secondary unit (the architecture). Default: ``None``.
		:param files:         Optional, the source files, by the number the report gives them. Default: ``None``.
		:param parent:        Optional, the report the instance belongs to. Default: ``None``.
		:raises TypeError:    If parameter ``files`` isn't a mapping.
		:raises TypeError:    If parameter ``files`` contains a key not of type :class:`int`.
		:raises ValueError:   If parameter ``files`` contains a negative key.
		:raises TypeError:    If parameter ``files`` contains a value not of type :class:`~pathlib.Path`.
		:raises TypeError:    If parameter ``parent`` isn't of type
		                      :class:`~pyEDAA.Reports.CodeCoverage.QuestaSim.Report`.
		:raises ValueError:   If parameter ``path`` is ``None``.
		:raises TypeError:    If parameter ``path`` isn't of type :class:`str`.
		:raises ValueError:   If parameter ``path`` is empty.
		:raises ValueError:   If parameter ``designUnit`` is ``None``.
		:raises TypeError:    If parameter ``designUnit`` isn't of type :class:`str`.
		:raises ValueError:   If parameter ``designUnit`` is empty.
		:raises TypeError:    If parameter ``secondaryUnit`` isn't of type :class:`str`.
		:raises ValueError:   If parameter ``secondaryUnit`` is empty.
		"""
		super().__init__(files, parent=parent)

		if path is None:
			raise ValueError(f"Parameter 'path' is None.")
		elif not isinstance(path, str):
			ex = TypeError(f"Parameter 'path' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(path)}'.")
			raise ex
		elif path == "":
			raise ValueError(f"Parameter 'path' is empty.")

		if designUnit is None:
			raise ValueError(f"Parameter 'designUnit' is None.")
		elif not isinstance(designUnit, str):
			ex = TypeError(f"Parameter 'designUnit' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(designUnit)}'.")
			raise ex
		elif designUnit == "":
			raise ValueError(f"Parameter 'designUnit' is empty.")

		if secondaryUnit is not None:
			if not isinstance(secondaryUnit, str):
				ex = TypeError(f"Parameter 'secondaryUnit' is not of type 'str'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(secondaryUnit)}'.")
				raise ex
			elif secondaryUnit == "":
				raise ValueError(f"Parameter 'secondaryUnit' is empty.")

		self._path =          path
		self._designUnit =    designUnit
		self._secondaryUnit = secondaryUnit

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[Report] = None) -> Self:
		"""
		Parse an instance, its source files, coverage statistics and statements from its ``<instanceData>`` element.

		:param element:            The ``<instanceData>`` element.
		:param parent:             Optional, the report the instance belongs to. Default: ``None``.
		:returns:                  The instance.
		:raises CodeCoverageError: If a coverage statistics element states more hit items than items.
		:raises CodeCoverageError: If the instance states a kind of coverage statistics twice.
		:raises CodeCoverageError: If a coverage item names an unknown file number, or none in an instance of several
		                           files.
		"""
		instance = cls(
			element.attrib["path"],
			element.attrib["du"],
			element.attrib.get("sec"),
			cls._ParseSourceTable(element),
			parent=parent
		)
		instance._ParseItems(element)
		return instance

	@readonly
	def Path(self) -> str:
		"""
		Read-only property to access the hierarchical path of the instance (:attr:`_path`).

		:returns: The path, separated by ``/``.
		"""
		return self._path

	@readonly
	def DesignUnit(self) -> str:
		"""
		Read-only property to access the name of the design unit (:attr:`_designUnit`).

		:returns: The design unit's name, as Questa writes it: in lower case for VHDL.
		"""
		return self._designUnit

	@readonly
	def SecondaryUnit(self) -> Nullable[str]:
		"""
		Read-only property to access the name of the secondary unit (:attr:`_secondaryUnit`).

		:returns: The architecture's name, or ``None`` - e.g. for a package.
		"""
		return self._secondaryUnit


@export
class DesignUnitData(Scope):
	"""
	A ``<DuData>``: a design unit, its instances' coverage combined.
	"""

	_designUnit:    str            #: Name of the design unit.
	_secondaryUnit: Nullable[str]  #: Name of the secondary unit (the architecture), if the design unit has one.

	def __init__(
		self,
		designUnit: str,
		secondaryUnit: Nullable[str] = None,
		files: Nullable[Mapping[int, Path]] = None,
		*,
		parent: Nullable[Report] = None
	) -> None:
		"""
		Initialize the design unit, and append it to the scopes of its report.

		:param designUnit:    Name of the design unit.
		:param secondaryUnit: Optional, name of the secondary unit (the architecture). Default: ``None``.
		:param files:         Optional, the source files, by the number the report gives them. Default: ``None``.
		:param parent:        Optional, the report the design unit belongs to. Default: ``None``.
		:raises TypeError:    If parameter ``files`` isn't a mapping.
		:raises TypeError:    If parameter ``files`` contains a key not of type :class:`int`.
		:raises ValueError:   If parameter ``files`` contains a negative key.
		:raises TypeError:    If parameter ``files`` contains a value not of type :class:`~pathlib.Path`.
		:raises TypeError:    If parameter ``parent`` isn't of type
		                      :class:`~pyEDAA.Reports.CodeCoverage.QuestaSim.Report`.
		:raises ValueError:   If parameter ``designUnit`` is ``None``.
		:raises TypeError:    If parameter ``designUnit`` isn't of type :class:`str`.
		:raises ValueError:   If parameter ``designUnit`` is empty.
		:raises TypeError:    If parameter ``secondaryUnit`` isn't of type :class:`str`.
		:raises ValueError:   If parameter ``secondaryUnit`` is empty.
		"""
		super().__init__(files, parent=parent)

		if designUnit is None:
			raise ValueError(f"Parameter 'designUnit' is None.")
		elif not isinstance(designUnit, str):
			ex = TypeError(f"Parameter 'designUnit' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(designUnit)}'.")
			raise ex
		elif designUnit == "":
			raise ValueError(f"Parameter 'designUnit' is empty.")

		if secondaryUnit is not None:
			if not isinstance(secondaryUnit, str):
				ex = TypeError(f"Parameter 'secondaryUnit' is not of type 'str'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(secondaryUnit)}'.")
				raise ex
			elif secondaryUnit == "":
				raise ValueError(f"Parameter 'secondaryUnit' is empty.")

		self._designUnit =    designUnit
		self._secondaryUnit = secondaryUnit

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[Report] = None) -> Self:
		"""
		Parse a design unit, its source files, coverage statistics and statements from its ``<DuData>`` element.

		:param element:            The ``<DuData>`` element.
		:param parent:             Optional, the report the design unit belongs to. Default: ``None``.
		:returns:                  The design unit.
		:raises CodeCoverageError: If a coverage statistics element states more hit items than items.
		:raises CodeCoverageError: If the design unit states a kind of coverage statistics twice.
		:raises CodeCoverageError: If a coverage item names an unknown file number, or none in a design unit of several
		                           files.
		"""
		designUnit = cls(element.attrib["du"], element.attrib.get("sec"), cls._ParseSourceTable(element), parent=parent)
		designUnit._ParseItems(element)
		return designUnit

	@readonly
	def DesignUnit(self) -> str:
		"""
		Read-only property to access the name of the design unit (:attr:`_designUnit`).

		:returns: The design unit's name, as Questa writes it: in lower case for VHDL.
		"""
		return self._designUnit

	@readonly
	def SecondaryUnit(self) -> Nullable[str]:
		"""
		Read-only property to access the name of the secondary unit (:attr:`_secondaryUnit`).

		:returns: The architecture's name, or ``None`` - e.g. for a package.
		"""
		return self._secondaryUnit


@export
class FileData(Scope):
	"""
	A ``<fileData>``: a source file.
	"""

	_path: _Path  #: Path of the source file, as the report states it.

	def __init__(
		self,
		path: Path,
		files: Nullable[Mapping[int, Path]] = None,
		*,
		parent: Nullable[Report] = None
	) -> None:
		"""
		Initialize the source file, and append it to the scopes of its report.

		:param path:        Path of the source file, as the report states it.
		:param files:       Optional, the source files, by the number the report gives them. Default: ``None``.
		:param parent:      Optional, the report the source file belongs to. Default: ``None``.
		:raises TypeError:  If parameter ``files`` isn't a mapping.
		:raises TypeError:  If parameter ``files`` contains a key not of type :class:`int`.
		:raises ValueError: If parameter ``files`` contains a negative key.
		:raises TypeError:  If parameter ``files`` contains a value not of type :class:`~pathlib.Path`.
		:raises TypeError:  If parameter ``parent`` isn't of type
		                    :class:`~pyEDAA.Reports.CodeCoverage.QuestaSim.Report`.
		:raises ValueError: If parameter ``path`` is ``None``.
		:raises TypeError:  If parameter ``path`` isn't of type :class:`~pathlib.Path`.
		"""
		super().__init__(files, parent=parent)

		if path is None:
			raise ValueError(f"Parameter 'path' is None.")
		elif not isinstance(path, Path):
			ex = TypeError(f"Parameter 'path' is not of type 'Path'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(path)}'.")
			raise ex

		self._path = path

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[Report] = None) -> Self:
		"""
		Parse a source file, its coverage statistics and statements from its ``<fileData>`` element.

		:param element:            The ``<fileData>`` element.
		:param parent:             Optional, the report the source file belongs to. Default: ``None``.
		:returns:                  The source file.
		:raises CodeCoverageError: If a coverage statistics element states more hit items than items.
		:raises CodeCoverageError: If the source file states a kind of coverage statistics twice.
		:raises CodeCoverageError: If a coverage item names an unknown file number.
		"""
		fileData = cls(Path(element.attrib["path"]), cls._ParseSourceTable(element), parent=parent)
		fileData._ParseItems(element)
		return fileData

	@readonly
	def Path(self) -> _Path:
		"""
		Read-only property to access the path of the source file (:attr:`_path`).

		:returns: The path, as the report states it.
		"""
		return self._path
