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
#   Artur Porebski (Aldec Inc.)                                                                                        #
#   Michal Pacula  (Aldec Inc.)                                                                                        #
#                                                                                                                      #
# License:                                                                                                             #
# ==================================================================================================================== #
# Copyright 2021-2026 Electronic Design Automation Abstraction (EDA²)                                                  #
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
Aldec's UCDB XML code coverage format: a model of the format, read from a report and converted to the common model.

Aldec's simulators Riviera-PRO and Active-HDL keep code coverage in a coverage database (ACDB), which the tool
``acdb2xml`` exports as XML: ``acdb2xml -i aggregate.acdb -o ucdb.xml``. The XML names its namespace ``www.aldec.com``
and its root ``<ux:ucdb>``; it is a dump of the database's UCIS data model - scopes, coverage items (bins) and history
nodes -, not the XML interchange format of the UCIS standard. A report states no format version, only the tool's name
and version, e.g. ``Riviera-PRO 2022.04``; it is validated against :file:`Aldec-UCDB.xsd` (:data:`SCHEMA`),
reverse-engineered from reports of Riviera-PRO.

The format's model keeps what the report states: a :class:`Document` holds its attributes, :class:`HistoryNode`
elements - nested, a merge holds the tests it merged -, :class:`Scope` elements - nested, e.g. design units, their
instances, processes and branching statements - with their :class:`Bin` elements, and :class:`Command` elements. Each
element's constructor takes typed values, so the model can be built by hand: an element below the report names its
parent with the keyword parameter ``parent`` and is added to it. Its class method ``Parse`` reads the element's XML
element.

* The scopes are the design units and their instances; the bins are the coverage items - e.g. statements and
  branches - with their counts, and where they are in the sources (:class:`SourceLocation`).
* Every element may state attributes (:class:`AttributesMixin`); the named elements derive from :class:`Base`.
* The kinds of scopes (:class:`ScopeType`), bins (:class:`CoverType`) and source languages (:class:`Language`) are
  named as the UCIS standard names them in its C API, without the prefix ``UCIS_``, e.g. ``DU_MODULE`` for
  ``UCIS_DU_MODULE``.

:meth:`Document.ToCoverageSummary` converts the statement coverage to the common model of
:mod:`pyEDAA.Reports.CodeCoverage`:

* The statements are the statement bins (``STMTBIN``) of the instances: the bins of the scopes below each top-level
  scope, which isn't a design unit. A statement is identified by its file, its line and its index in the line
  (attribute ``#SINDEX#``); with ``mergeInstances``, the statements of all instances of a design unit are merged into
  one, which ran as often as in all instances together (:meth:`Report.IterateStatements`).
* A file's path is the one a statement bin's source location states, relative to the directory the tool ran in; these
  directories are the summary's source directories.
* A line ran as often as its least often run statement: it is covered, if all its statements ran. A line, whose
  statements are all excluded, is excluded; an excluded statement doesn't count for its line.
* The branches, the blocks and the other kinds of coverage aren't converted, and the format names no units.

.. rubric:: Example

.. code-block:: Python

   from pathlib import Path
   from pyEDAA.Reports.CodeCoverage.AldecUCDB import Document

   report = Document(Path("ucdb.xml"), analyzeAndConvert=True)
   summary = report.ToCoverageSummary(mergeInstances=True)
   for file in summary.IterateFiles():
     print(f"{file.Path}: {file.LineCoverage:.1%}")
"""
from __future__                  import annotations

from enum                        import IntEnum, IntFlag
from io                          import BytesIO
from pathlib                     import Path
from typing                      import Generator, Generic, Iterable, Mapping, Optional as Nullable, Self, TypeVar

from lxml.etree                  import XMLParser, XMLSchema, XMLSchemaParseError, XMLSyntaxError, _Element, \
                                        _ElementTree, parse
from pyTooling.Common            import getFullyQualifiedName, getResourceFile, StringEnum
from pyTooling.Decorators        import export, readonly
from pyTooling.Exceptions        import ToolingException
from pyTooling.MetaClasses       import ExtendedType, abstractclass
from pyTooling.Stopwatch         import Stopwatch
from pyTooling.Versioning        import CalendarVersion

from pyEDAA.Reports              import Resources
from pyEDAA.Reports.CodeCoverage import CodeCoverageError, CoverageSummary, Document as cc_Document, Line as cc_Line, \
                                        LineCoverageStatus


__all__ = ["SCHEMA", "NAMESPACE", "NAMESPACES", "HistoryNodeParentType", "ScopeParentType"]

SCHEMA = "Aldec-UCDB.xsd"  #: The XML schema a report is validated against.

NAMESPACE = "www.aldec.com"            #: The XML namespace of the format's elements.
NAMESPACES = {"ux": NAMESPACE}         #: The XML namespaces of the format by their prefix, for finding elements.

HistoryNodeParentType = TypeVar("HistoryNodeParentType", bound="Report | HistoryNode")
"""A type variable for the parent of a :class:`HistoryNode`: a :class:`Report`
or a :class:`HistoryNode`."""

ScopeParentType = TypeVar("ScopeParentType", bound="Report | Scope")
"""A type variable for the parent of a :class:`Scope`: a :class:`Report` or a
:class:`Scope`."""


@export
class ScopeType(StringEnum):
	"""
	Kind of a ``<ux:scope>``, as its ``type`` states: a design unit, an instance of one, or a scope of a coverage kind.
	"""

	Toggle =                 "TOGGLE"           #: Toggle coverage of a signal.
	Branch =                 "BRANCH"           #: Branch coverage of a branching statement.
	Expression =             "EXPR"             #: Expression coverage.
	Condition =              "COND"             #: Condition coverage.
	Instance =               "INSTANCE"         #: An instance of a design unit, e.g. of a Verilog module.
	Process =                "PROCESS"          #: A process, e.g. a Verilog ``always`` block.
	Block =                  "BLOCK"            #: A block, e.g. a VHDL ``block`` statement.
	Function =               "FUNCTION"         #: A function.
	ForkJoin =               "FORKJOIN"         #: A Verilog ``fork ... join`` block.
	Generate =               "GENERATE"         #: A generate block.
	Generic =                "GENERIC"          #: A scope of a generic kind.
	Class =                  "CLASS"            #: A SystemVerilog class.
	CoverGroup =             "COVERGROUP"       #: A SystemVerilog covergroup type.
	CoverInstance =          "COVERINSTANCE"    #: An instance of a SystemVerilog covergroup.
	CoverPoint =             "COVERPOINT"       #: A SystemVerilog coverpoint.
	Cross =                  "CROSS"            #: A SystemVerilog cross coverage.
	Cover =                  "COVER"            #: A cover directive.
	Assert =                 "ASSERT"           #: An assertion.
	Program =                "PROGRAM"          #: An instance of a SystemVerilog program.
	Package =                "PACKAGE"          #: An instance of a package.
	Task =                   "TASK"             #: A Verilog task.
	Interface =              "INTERFACE"        #: An instance of a SystemVerilog interface.
	FSM =                    "FSM"              #: A finite state machine.
	DesignUnitModule =       "DU_MODULE"        #: Design unit: a Verilog module.
	DesignUnitArchitecture = "DU_ARCH"          #: Design unit: a VHDL architecture.
	DesignUnitPackage =      "DU_PACKAGE"       #: Design unit: a package.
	DesignUnitProgram =      "DU_PROGRAM"       #: Design unit: a SystemVerilog program.
	DesignUnitInterface =    "DU_INTERFACE"     #: Design unit: a SystemVerilog interface.
	FSMStates =              "FSM_STATES"       #: The states of a finite state machine.
	FSMTransitions =         "FSM_TRANS"        #: The transitions of a finite state machine.
	CoverBlock =             "COVBLOCK"         #: A block of coverage items.
	CoverGroupBinScope =     "CVGBINSCOPE"      #: A scope of covergroup bins.
	IllegalBinScope =        "ILLEGALBINSCOPE"  #: A scope of illegal covergroup bins.
	IgnoreBinScope =         "IGNOREBINSCOPE"   #: A scope of ignored covergroup bins.


@export
class CoverType(StringEnum):
	"""
	Kind of a ``<ux:bin>``, as its ``type`` states.

	A kind Aldec's export has no name for is stated by its value in hexadecimal, as the UCIS C API defines it.
	"""

	CoverGroupBin = "CVGBIN"         #: A bin of a SystemVerilog covergroup.
	CoverBin =      "COVERBIN"       #: A cover directive's pass.
	AssertBin =     "ASSERTBIN"      #: An assertion's failure.
	StatementBin =  "STMTBIN"        #: A statement.
	BranchBin =     "BRANCHBIN"      #: A branch of a branching statement.
	ExpressionBin = "EXPRBIN"        #: A row of an expression's truth table.
	ConditionBin =  "CONDBIN"        #: A row of a condition's truth table.
	ToggleBin =     "TOGGLEBIN"      #: A transition of a signal's toggle coverage.
	PassBin =       "PASSBIN"        #: An assertion's pass.
	FSMBin =        "FSMBIN"         #: A state or transition of a finite state machine.
	UserBin =       "USERBIN"        #: A bin defined by the user.
	Count =         "COUNT"          #: A counter.
	FailBin =       "FAILBIN"        #: A cover directive's failure.
	VacuousBin =    "VACUOUSBIN"     #: An assertion's vacuous pass.
	DisabledBin =   "DISABLEDBIN"    #: An assertion's or cover directive's disabled attempt.
	AttemptBin =    "ATTEMPTBIN"     #: An assertion's or cover directive's attempt.
	ActiveBin =     "ACTIVEBIN"      #: An assertion's or cover directive's active thread.
	IgnoreBin =     "IGNOREBIN"      #: An ignored bin of a SystemVerilog covergroup.
	IllegalBin =    "ILLEGALBIN"     #: An illegal bin of a SystemVerilog covergroup.
	DefaultBin =    "DEFAULTBIN"     #: The default bin of a SystemVerilog covergroup.
	PeakActiveBin = "PEAKACTIVEBIN"  #: The peak number of an assertion's or cover directive's active threads.
	BlockBin =      "1000000"        #: A block of statements, stated by its value ``UCIS_BLOCKBIN``: ``0x1000000``.


@export
class Language(StringEnum):
	"""
	Language of the source of a ``<ux:scope>``, as its ``lang`` states.
	"""

	VHDL =               "VHDL"         #: VHDL.
	Verilog =            "VLOG"         #: Verilog.
	SystemVerilog =      "SV"           #: SystemVerilog.
	SystemC =            "SYSTEMC"      #: SystemC.
	PSLInVHDL =          "PSL_VHDL"     #: PSL embedded in VHDL.
	PSLInVerilog =       "PSL_VLOG"     #: PSL embedded in Verilog.
	PSLInSystemVerilog = "PSL_SV"       #: PSL embedded in SystemVerilog.
	PSLInSystemC =       "PSL_SYSTEMC"  #: PSL embedded in SystemC.
	E =                  "E"            #: The verification language *e*.
	Vera =               "VERA"         #: The verification language OpenVera.
	NoLanguage =         "NONE"         #: No source language.
	Other =              "OTHER"        #: Another source language.


# A class with a property named like a class - ``Language`` - can't name that class in the annotation of a field: the
# class body's namespace, where annotations are evaluated, binds the name to the property.
_Language = Language


@export
class HistoryNodeKind(IntEnum):
	"""
	Kind of a ``<ux:hnode>``, as its ``type`` states.
	"""

	Test =  1  #: A test: a simulation run, which wrote a coverage database.
	Merge = 2  #: A merge of coverage databases.


@export
class BinFlags(IntFlag):
	"""
	Flags of a ``<ux:bin>``, as its ``flags`` state in hexadecimal; a flag not named here is kept.
	"""

	Is32Bit =         0x00000001  #: The count is a 32-bit number.
	Is64Bit =         0x00000002  #: The count is a 64-bit number.
	IsVector =        0x00000004  #: The bin is a vector of counts.
	HasGoal =         0x00000008  #: The bin states a goal.
	HasWeight =       0x00000010  #: The bin states a weight.
	ExcludePragma =   0x00000020  #: Excluded by a pragma in the source.
	ExcludeFile =     0x00000040  #: Excluded by an exclusion file.
	ExcludeInstance = 0x00000080  #: Excluded in this instance.
	ExcludeAuto =     0x00000100  #: Excluded automatically by the tool.
	HasLimit =        0x00000400  #: The count saturates at a limit.
	HasCount =        0x00000800  #: The bin states a count.
	IsCovered =       0x00001000  #: The bin reached its goal.

	Excluded =        0x000001E0  #: Any of the exclusion flags.


@export
class AttributesMixin(metaclass=ExtendedType, mixin=True):
	"""
	A mixin-class adding the attributes an element states: its ``<ux:attr>`` elements, each a key and a typed value.

	An attribute's type is its value's type: ``int`` is :class:`int`, ``double`` is :class:`float`, ``str`` is
	:class:`str`.
	"""

	_attributes: dict[str, int | float | str]  #: The attributes, by key.

	def __init__(self, attributes: Nullable[Mapping[str, int | float | str]] = None) -> None:
		"""
		Initialize the attributes.

		:param attributes:  Optional, the attributes by key, e.g. ``{"#SINDEX#": 1}``. Default: ``None``.
		:raises TypeError:  If parameter ``attributes`` isn't a mapping.
		:raises TypeError:  If parameter ``attributes`` contains a key not of type :class:`str`.
		:raises ValueError: If parameter ``attributes`` contains an empty key.
		:raises TypeError:  If parameter ``attributes`` contains a value not of type :class:`int`, :class:`float` or
		                    :class:`str`.
		"""
		self._attributes = {}

		if attributes is not None:
			if not isinstance(attributes, Mapping):
				ex = TypeError("Parameter 'attributes' is not a mapping.")
				ex.add_note(f"Got type '{getFullyQualifiedName(attributes)}'.")
				raise ex

			for key, value in attributes.items():
				if not isinstance(key, str):
					ex = TypeError("Parameter 'attributes' contains a key not of type 'str'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(key)}'.")
					raise ex
				elif key == "":
					raise ValueError("Parameter 'attributes' contains an empty key.")

				if not isinstance(value, (int, float, str)):
					ex = TypeError("Parameter 'attributes' contains a value not of type 'int', 'float' or 'str'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(value)}' for key '{key}'.")
					raise ex

				self._attributes[key] = value

	@staticmethod
	def _ParseAttributes(element: _Element) -> dict[str, int | float | str]:
		"""
		Parse the attributes an element states, from its ``<ux:attr>`` elements.

		:param element:            The element stating the attributes.
		:returns:                  The attributes by key, each value of the type the attribute states.
		:raises CodeCoverageError: If an attribute's value isn't of the type the attribute states.
		"""
		attributes: dict[str, int | float | str] = {}
		for attributeElement in element.iterfind("ux:attr", NAMESPACES):
			key =           attributeElement.attrib["key"]
			attributeType = attributeElement.attrib["type"]
			text =          attributeElement.text if attributeElement.text is not None else ""
			try:
				if attributeType == "int":
					attributes[key] = int(text)
				elif attributeType == "double":
					attributes[key] = float(text)
				else:
					attributes[key] = text
			except ValueError as cause:
				ex = CodeCoverageError(f"UCDB attribute '{key}' states a value not of type '{attributeType}'.")
				ex.add_note(f"Got value '{text}'.")
				raise ex from cause

		return attributes

	@readonly
	def Attributes(self) -> dict[str, int | float | str]:
		"""
		Read-only property to access the attributes (:attr:`_attributes`).

		:returns: The attributes by key, e.g. ``#SINDEX#`` - a statement's index in its line - or ``UCIS:tool``.
		"""
		return self._attributes


@export
@abstractclass
class Base(metaclass=ExtendedType, slots=True):
	"""
	Base-class of the named elements below the report.

	Scopes and bins are named elements.
	"""

	_name: str  #: Name of the element.

	def __init__(self, name: str) -> None:
		"""
		Initialize the name of the element.

		:param name:        Name of the element.
		:raises ValueError: If parameter ``name`` is ``None``.
		:raises TypeError:  If parameter ``name`` isn't of type :class:`str`.
		"""
		if name is None:
			raise ValueError("Parameter 'name' is None.")
		elif not isinstance(name, str):
			ex = TypeError("Parameter 'name' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(name)}'.")
			raise ex

		self._name = name

	@readonly
	def Name(self) -> str:
		"""
		Read-only property to access the name of the element (:attr:`_name`).

		:returns: The name.
		"""
		return self._name


@export
class SourceLocation(metaclass=ExtendedType, slots=True):
	"""
	A ``<ux:src>`` of a scope or bin: the source file, the directory its name is relative to, the line and the token.

	It is a value, as a path is: it names no parent.
	"""

	_file:          Path  #: Path of the source file, relative to :attr:`_workDirectory`, if not absolute.
	_workDirectory: Path  #: The directory the tool ran in.
	_lineNumber:    int   #: Line number, counted from 1; ``0`` for a scope without a line.
	_token:         int   #: Number of the token in the line.

	def __init__(self, file: Path, workDirectory: Path, lineNumber: int, token: int) -> None:
		"""
		Initialize the source location.

		:param file:          Path of the source file, e.g. ``src/counter.sv``.
		:param workDirectory: The directory the tool ran in.
		:param lineNumber:    Line number, counted from 1; ``0`` for a scope without a line.
		:param token:         Number of the token in the line.
		:raises ValueError:   If parameter ``file`` is ``None``.
		:raises TypeError:    If parameter ``file`` isn't of type :class:`~pathlib.Path`.
		:raises ValueError:   If parameter ``workDirectory`` is ``None``.
		:raises TypeError:    If parameter ``workDirectory`` isn't of type :class:`~pathlib.Path`.
		:raises ValueError:   If parameter ``lineNumber`` is ``None``.
		:raises TypeError:    If parameter ``lineNumber`` isn't of type :class:`int`.
		:raises ValueError:   If parameter ``lineNumber`` is negative.
		:raises ValueError:   If parameter ``token`` is ``None``.
		:raises TypeError:    If parameter ``token`` isn't of type :class:`int`.
		:raises ValueError:   If parameter ``token`` is negative.
		"""
		if file is None:
			raise ValueError("Parameter 'file' is None.")
		elif not isinstance(file, Path):
			ex = TypeError("Parameter 'file' is not of type 'Path'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(file)}'.")
			raise ex

		if workDirectory is None:
			raise ValueError("Parameter 'workDirectory' is None.")
		elif not isinstance(workDirectory, Path):
			ex = TypeError("Parameter 'workDirectory' is not of type 'Path'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(workDirectory)}'.")
			raise ex

		if lineNumber is None:
			raise ValueError("Parameter 'lineNumber' is None.")
		elif not isinstance(lineNumber, int):
			ex = TypeError("Parameter 'lineNumber' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(lineNumber)}'.")
			raise ex
		elif lineNumber < 0:
			ex = ValueError("Parameter 'lineNumber' is negative.")
			ex.add_note(f"Got value '{lineNumber}'.")
			raise ex

		if token is None:
			raise ValueError("Parameter 'token' is None.")
		elif not isinstance(token, int):
			ex = TypeError("Parameter 'token' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(token)}'.")
			raise ex
		elif token < 0:
			ex = ValueError("Parameter 'token' is negative.")
			ex.add_note(f"Got value '{token}'.")
			raise ex

		self._file =          file
		self._workDirectory = workDirectory
		self._lineNumber =    lineNumber
		self._token =         token

	@classmethod
	def Parse(cls, element: _Element) -> Self:
		"""
		Parse a source location from its ``<ux:src>`` element.

		:param element: The ``<ux:src>`` element.
		:returns:       The source location.
		"""
		return cls(
			Path(element.attrib["file"]),
			Path(element.attrib["workdir"]),
			int(element.attrib["line"]),
			int(element.attrib["token"])
		)

	@readonly
	def File(self) -> Path:
		"""
		Read-only property to access the path of the source file (:attr:`_file`).

		:returns: The path, relative to :attr:`WorkDirectory`, if not absolute.
		"""
		return self._file

	@readonly
	def WorkDirectory(self) -> Path:
		"""
		Read-only property to access the directory the tool ran in (:attr:`_workDirectory`).

		It is a path on the machine the coverage was measured on, so it may not exist where the report is read.

		:returns: The directory.
		"""
		return self._workDirectory

	@readonly
	def LineNumber(self) -> int:
		"""
		Read-only property to access the line number (:attr:`_lineNumber`).

		:returns: The line number, counted from 1; ``0`` for a scope without a line.
		"""
		return self._lineNumber

	@readonly
	def Token(self) -> int:
		"""
		Read-only property to access the number of the token in the line (:attr:`_token`).

		:returns: The token's number.
		"""
		return self._token


@export
class Bin(Base, AttributesMixin):
	"""
	A ``<ux:bin>`` of a scope: a coverage item, how often it was hit, its flags, and where it is in the sources.

	Statements and branches are coverage items.
	"""

	_parent: Nullable[Scope]  #: The scope the bin belongs to.
	_type:   CoverType        #: Kind of the bin.
	_flags:  BinFlags         #: Flags of the bin, e.g. whether it is excluded.
	_count:  int              #: How often the coverage item was hit.
	_source: SourceLocation   #: Where the coverage item is in the sources.

	def __init__(
		self,
		name: str,
		coverType: CoverType,
		flags: BinFlags,
		count: int,
		source: SourceLocation,
		attributes: Nullable[Mapping[str, int | float | str]] = None,
		*,
		parent: Nullable[Scope] = None
	) -> None:
		"""
		Initialize the bin, and append it to the bins of its scope.

		:param name:        Name of the bin, e.g. ``true_branch``; empty for a statement.
		:param coverType:   Kind of the bin.
		:param flags:       Flags of the bin.
		:param count:       How often the coverage item was hit.
		:param source:      Where the coverage item is in the sources.
		:param attributes:  Optional, the attributes by key, e.g. ``{"#SINDEX#": 1}``. Default: ``None``.
		:param parent:      Optional, the scope the bin belongs to; the bin is appended to its bins. Default: ``None``.
		:raises ValueError: If parameter ``name`` is ``None``.
		:raises TypeError:  If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError: If parameter ``coverType`` is ``None``.
		:raises TypeError:  If parameter ``coverType`` isn't of type
		                    :class:`CoverType`.
		:raises ValueError: If parameter ``flags`` is ``None``.
		:raises TypeError:  If parameter ``flags`` isn't of type :class:`BinFlags`.
		:raises ValueError: If parameter ``count`` is ``None``.
		:raises TypeError:  If parameter ``count`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``count`` is negative.
		:raises ValueError: If parameter ``source`` is ``None``.
		:raises TypeError:  If parameter ``source`` isn't of type :class:`SourceLocation`.
		:raises TypeError:  If parameter ``attributes`` isn't a mapping.
		:raises TypeError:  If parameter ``attributes`` contains a key not of type :class:`str`.
		:raises ValueError: If parameter ``attributes`` contains an empty key.
		:raises TypeError:  If parameter ``attributes`` contains a value not of type :class:`int`, :class:`float` or
		                    :class:`str`.
		:raises TypeError:  If parameter ``parent`` isn't of type :class:`Scope`.
		"""
		super().__init__(name)
		AttributesMixin.__init__(self, attributes)

		if coverType is None:
			raise ValueError("Parameter 'coverType' is None.")
		elif not isinstance(coverType, CoverType):
			ex = TypeError("Parameter 'coverType' is not of type 'CoverType'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(coverType)}'.")
			raise ex

		if flags is None:
			raise ValueError("Parameter 'flags' is None.")
		elif not isinstance(flags, BinFlags):
			ex = TypeError("Parameter 'flags' is not of type 'BinFlags'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(flags)}'.")
			raise ex

		if count is None:
			raise ValueError("Parameter 'count' is None.")
		elif not isinstance(count, int):
			ex = TypeError("Parameter 'count' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(count)}'.")
			raise ex
		elif count < 0:
			ex = ValueError("Parameter 'count' is negative.")
			ex.add_note(f"Got value '{count}'.")
			raise ex

		if source is None:
			raise ValueError("Parameter 'source' is None.")
		elif not isinstance(source, SourceLocation):
			ex = TypeError("Parameter 'source' is not of type 'SourceLocation'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(source)}'.")
			raise ex

		if parent is not None and not isinstance(parent, Scope):
			ex = TypeError("Parameter 'parent' is not of type 'Scope'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent = parent
		self._type =   coverType
		self._flags =  flags
		self._count =  count
		self._source = source

		if parent is not None:
			parent._bins.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[Scope] = None) -> Self:
		"""
		Parse a bin, its count, source location and attributes from its ``<ux:bin>`` element.

		:param element:            The ``<ux:bin>`` element.
		:param parent:             Optional, the scope the bin belongs to. Default: ``None``.
		:returns:                  The bin.
		:raises CodeCoverageError: If an attribute's value isn't of the type the attribute states.
		"""
		return cls(
			element.attrib["name"],
			CoverType(element.attrib["type"]),
			BinFlags(int(element.attrib["flags"], 16)),
			int(element.find("ux:count", NAMESPACES).text),
			SourceLocation.Parse(element.find("ux:src", NAMESPACES)),
			cls._ParseAttributes(element),
			parent=parent
		)

	@readonly
	def Parent(self) -> Nullable[Scope]:
		"""
		Read-only property to access the scope the bin belongs to (:attr:`_parent`).

		:returns: The scope; ``None`` if the bin belongs to no scope.
		"""
		return self._parent

	@readonly
	def Type(self) -> CoverType:
		"""
		Read-only property to access the kind of the bin (:attr:`_type`).

		:returns: The kind, e.g. a statement.
		"""
		return self._type

	@readonly
	def Flags(self) -> BinFlags:
		"""
		Read-only property to access the flags of the bin (:attr:`_flags`).

		:returns: The flags.
		"""
		return self._flags

	@readonly
	def IsExcluded(self) -> bool:
		"""
		Read-only property to return whether the bin is excluded from the measurement.

		:returns: ``True``, if :attr:`Flags` has one of the exclusion flags (:attr:`BinFlags.Excluded`).
		"""
		return (self._flags & BinFlags.Excluded) != 0

	@readonly
	def Count(self) -> int:
		"""
		Read-only property to access how often the coverage item was hit (:attr:`_count`).

		:returns: The count, e.g. how often a statement ran.
		"""
		return self._count

	@readonly
	def Source(self) -> SourceLocation:
		"""
		Read-only property to access where the coverage item is in the sources (:attr:`_source`).

		:returns: The source location.
		"""
		return self._source


@export
class Scope(Base, AttributesMixin, Generic[ScopeParentType]):
	"""
	A ``<ux:scope>`` of the report or of a scope: its bins and the scopes below it.

	Design units, their instances, processes and branching statements are scopes.
	"""

	_parent:     Nullable[ScopeParentType]  #: The report or scope the scope belongs to.
	_type:       ScopeType                  #: Kind of the scope.
	_language:   _Language                  #: Language of the scope's source.
	_weight:     int                        #: Weight of the scope.
	_flags:      int                        #: Flags of the scope.
	_source:     SourceLocation             #: Where the scope is in the sources.
	_designUnit: Nullable[str]              #: Name of the design unit an instance instantiates.
	_scopes:     list[Scope[Scope]]         #: The scopes below this one.
	_bins:       list[Bin]                  #: The bins of this scope.

	def __init__(
		self,
		name: str,
		scopeType: ScopeType,
		language: _Language,
		weight: int,
		flags: int,
		source: SourceLocation,
		designUnit: Nullable[str] = None,
		attributes: Nullable[Mapping[str, int | float | str]] = None,
		*,
		parent: Nullable[ScopeParentType] = None
	) -> None:
		"""
		Initialize the scope, and append it to the scopes of its report or scope.

		Its scopes and bins are added by creating them with this scope as their parent.

		:param name:        Name of the scope, e.g. ``work.counter`` for a design unit or ``uut`` for an instance.
		:param scopeType:   Kind of the scope.
		:param language:    Language of the scope's source.
		:param weight:      Weight of the scope.
		:param flags:       Flags of the scope.
		:param source:      Where the scope is in the sources.
		:param designUnit:  Optional, name of the design unit an instance instantiates, e.g. ``work.counter``.
		                    Default: ``None``.
		:param attributes:  Optional, the attributes by key, e.g. ``{"#GOAL#": 100}``. Default: ``None``.
		:param parent:      Optional, the report or scope the scope belongs to; the scope is appended to its scopes.
		                    Default: ``None``.
		:raises ValueError: If parameter ``name`` is ``None``.
		:raises TypeError:  If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError: If parameter ``name`` is empty.
		:raises ValueError: If parameter ``scopeType`` is ``None``.
		:raises TypeError:  If parameter ``scopeType`` isn't of type
		                    :class:`ScopeType`.
		:raises ValueError: If parameter ``language`` is ``None``.
		:raises TypeError:  If parameter ``language`` isn't of type
		                    :class:`Language`.
		:raises ValueError: If parameter ``weight`` is ``None``.
		:raises TypeError:  If parameter ``weight`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``weight`` is negative.
		:raises ValueError: If parameter ``flags`` is ``None``.
		:raises TypeError:  If parameter ``flags`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``flags`` is negative.
		:raises ValueError: If parameter ``source`` is ``None``.
		:raises TypeError:  If parameter ``source`` isn't of type :class:`SourceLocation`.
		:raises TypeError:  If parameter ``designUnit`` isn't of type :class:`str`.
		:raises ValueError: If parameter ``designUnit`` is empty.
		:raises TypeError:  If parameter ``attributes`` isn't a mapping.
		:raises TypeError:  If parameter ``attributes`` contains a key not of type :class:`str`.
		:raises ValueError: If parameter ``attributes`` contains an empty key.
		:raises TypeError:  If parameter ``attributes`` contains a value not of type :class:`int`, :class:`float` or
		                    :class:`str`.
		:raises TypeError:  If parameter ``parent`` isn't of type :class:`Report`
		                    or :class:`Scope`.
		"""
		super().__init__(name)
		AttributesMixin.__init__(self, attributes)

		if name == "":
			raise ValueError("Parameter 'name' is empty.")

		if scopeType is None:
			raise ValueError("Parameter 'scopeType' is None.")
		elif not isinstance(scopeType, ScopeType):
			ex = TypeError("Parameter 'scopeType' is not of type 'ScopeType'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(scopeType)}'.")
			raise ex

		if language is None:
			raise ValueError("Parameter 'language' is None.")
		elif not isinstance(language, Language):
			ex = TypeError("Parameter 'language' is not of type 'Language'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(language)}'.")
			raise ex

		if weight is None:
			raise ValueError("Parameter 'weight' is None.")
		elif not isinstance(weight, int):
			ex = TypeError("Parameter 'weight' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(weight)}'.")
			raise ex
		elif weight < 0:
			ex = ValueError("Parameter 'weight' is negative.")
			ex.add_note(f"Got value '{weight}'.")
			raise ex

		if flags is None:
			raise ValueError("Parameter 'flags' is None.")
		elif not isinstance(flags, int):
			ex = TypeError("Parameter 'flags' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(flags)}'.")
			raise ex
		elif flags < 0:
			ex = ValueError("Parameter 'flags' is negative.")
			ex.add_note(f"Got value '{flags}'.")
			raise ex

		if source is None:
			raise ValueError("Parameter 'source' is None.")
		elif not isinstance(source, SourceLocation):
			ex = TypeError("Parameter 'source' is not of type 'SourceLocation'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(source)}'.")
			raise ex

		if designUnit is not None:
			if not isinstance(designUnit, str):
				ex = TypeError("Parameter 'designUnit' is not of type 'str'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(designUnit)}'.")
				raise ex
			elif designUnit == "":
				raise ValueError("Parameter 'designUnit' is empty.")

		if parent is not None and not isinstance(parent, (Report, Scope)):
			ex = TypeError("Parameter 'parent' is not of type 'Report' or 'Scope'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =     parent
		self._type =       scopeType
		self._language =   language
		self._weight =     weight
		self._flags =      flags
		self._source =     source
		self._designUnit = designUnit
		self._scopes =     []
		self._bins =       []

		if parent is not None:
			parent._scopes.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[ScopeParentType] = None) -> Self:
		"""
		Parse a scope, its attributes, bins and the scopes below it from its ``<ux:scope>`` element.

		:param element:            The ``<ux:scope>`` element.
		:param parent:             Optional, the report or scope the scope belongs to. Default: ``None``.
		:returns:                  The scope.
		:raises CodeCoverageError: If an attribute's value isn't of the type the attribute states.
		"""
		scope = cls(
			element.attrib["name"],
			ScopeType(element.attrib["type"]),
			Language(element.attrib["lang"]),
			int(element.attrib["weight"]),
			int(element.attrib["flags"], 16),
			SourceLocation.Parse(element.find("ux:src", NAMESPACES)),
			element.attrib.get("du"),
			cls._ParseAttributes(element),
			parent=parent
		)

		for binElement in element.iterfind("ux:bin", NAMESPACES):
			Bin.Parse(binElement, parent=scope)

		for scopeElement in element.iterfind("ux:scope", NAMESPACES):
			Scope.Parse(scopeElement, parent=scope)

		return scope

	def IterateBins(self) -> Generator[Bin, None, None]:
		"""
		Iterate the bins of this scope, then those of the scopes below it, depth-first.

		:returns: A generator of the bins.
		"""
		yield from self._bins
		for scope in self._scopes:
			yield from scope.IterateBins()

	@readonly
	def Parent(self) -> Nullable[ScopeParentType]:
		"""
		Read-only property to access the report or scope the scope belongs to (:attr:`_parent`).

		:returns: The :class:`Report` or :class:`Scope`; ``None`` if the scope
		          belongs to none.
		"""
		return self._parent

	@readonly
	def Type(self) -> ScopeType:
		"""
		Read-only property to access the kind of the scope (:attr:`_type`).

		:returns: The kind, e.g. a design unit or an instance.
		"""
		return self._type

	@readonly
	def Language(self) -> _Language:
		"""
		Read-only property to access the language of the scope's source (:attr:`_language`).

		:returns: The language.
		"""
		return self._language

	@readonly
	def Weight(self) -> int:
		"""
		Read-only property to access the weight of the scope (:attr:`_weight`).

		:returns: The weight.
		"""
		return self._weight

	@readonly
	def Flags(self) -> int:
		"""
		Read-only property to access the flags of the scope (:attr:`_flags`).

		:returns: The flags, as stated.
		"""
		return self._flags

	@readonly
	def Source(self) -> SourceLocation:
		"""
		Read-only property to access where the scope is in the sources (:attr:`_source`).

		:returns: The source location.
		"""
		return self._source

	@readonly
	def DesignUnit(self) -> Nullable[str]:
		"""
		Read-only property to access the name of the design unit an instance instantiates (:attr:`_designUnit`).

		:returns: The design unit's name, e.g. ``work.counter``; ``None`` for a scope, which isn't an instance.
		"""
		return self._designUnit

	@readonly
	def Scopes(self) -> list[Scope[Scope]]:
		"""
		Read-only property to access the scopes below this one (:attr:`_scopes`).

		:returns: The scopes, in the order the report lists them.
		"""
		return self._scopes

	@readonly
	def Bins(self) -> list[Bin]:
		"""
		Read-only property to access the bins of this scope (:attr:`_bins`).

		:returns: The bins, in the order the report lists them.
		"""
		return self._bins


@export
class HistoryNode(Base, AttributesMixin, Generic[HistoryNodeParentType]):
	"""
	A ``<ux:hnode>`` of the report or of a merge: a test or a merge of databases, its attributes and merged nodes.

	A test wrote a coverage database, a merge merged databases. The attributes state e.g. the tool, the date and the
	command line.
	"""

	_parent:       Nullable[HistoryNodeParentType]   #: The report or merge the history node belongs to.
	_physicalName: Path                              #: Path of the coverage database.
	_kind:         HistoryNodeKind                   #: Kind of the history node.
	_historyNodes: list[HistoryNode[HistoryNode]]    #: The history nodes merged by this one.

	def __init__(
		self,
		name: str,
		physicalName: Path,
		kind: HistoryNodeKind,
		attributes: Nullable[Mapping[str, int | float | str]] = None,
		*,
		parent: Nullable[HistoryNodeParentType] = None
	) -> None:
		"""
		Initialize the history node, and append it to the history nodes of its report or merge.

		The history nodes it merged are added by creating them with this history node as their parent.

		:param name:         Logical name of the history node, e.g. of the test.
		:param physicalName: Path of the coverage database, e.g. ``cov/aggregate/aggregate.acdb``.
		:param kind:         Kind of the history node.
		:param attributes:   Optional, the attributes by key, e.g. ``{"UCIS:tool": "Riviera-PRO"}``. Default: ``None``.
		:param parent:       Optional, the report or merge the history node belongs to; the history node is appended
		                     to its history nodes. Default: ``None``.
		:raises ValueError:  If parameter ``name`` is ``None``.
		:raises TypeError:   If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError:  If parameter ``name`` is empty.
		:raises ValueError:  If parameter ``physicalName`` is ``None``.
		:raises TypeError:   If parameter ``physicalName`` isn't of type :class:`~pathlib.Path`.
		:raises ValueError:  If parameter ``kind`` is ``None``.
		:raises TypeError:   If parameter ``kind`` isn't of type :class:`HistoryNodeKind`.
		:raises TypeError:   If parameter ``attributes`` isn't a mapping.
		:raises TypeError:   If parameter ``attributes`` contains a key not of type :class:`str`.
		:raises ValueError:  If parameter ``attributes`` contains an empty key.
		:raises TypeError:   If parameter ``attributes`` contains a value not of type :class:`int`, :class:`float` or
		                     :class:`str`.
		:raises TypeError:   If parameter ``parent`` isn't of type :class:`Report`
		                     or :class:`HistoryNode`.
		"""
		super().__init__(name)
		AttributesMixin.__init__(self, attributes)

		if name == "":
			raise ValueError("Parameter 'name' is empty.")

		if physicalName is None:
			raise ValueError("Parameter 'physicalName' is None.")
		elif not isinstance(physicalName, Path):
			ex = TypeError("Parameter 'physicalName' is not of type 'Path'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(physicalName)}'.")
			raise ex

		if kind is None:
			raise ValueError("Parameter 'kind' is None.")
		elif not isinstance(kind, HistoryNodeKind):
			ex = TypeError("Parameter 'kind' is not of type 'HistoryNodeKind'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(kind)}'.")
			raise ex

		if parent is not None and not isinstance(parent, (Report, HistoryNode)):
			ex = TypeError("Parameter 'parent' is not of type 'Report' or 'HistoryNode'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =       parent
		self._physicalName = physicalName
		self._kind =         kind
		self._historyNodes = []

		if parent is not None:
			parent._historyNodes.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[HistoryNodeParentType] = None) -> Self:
		"""
		Parse a history node, its attributes and the history nodes it merged from its ``<ux:hnode>`` element.

		:param element:            The ``<ux:hnode>`` element.
		:param parent:             Optional, the report or merge the history node belongs to. Default: ``None``.
		:returns:                  The history node.
		:raises CodeCoverageError: If an attribute's value isn't of the type the attribute states.
		"""
		historyNode = cls(
			element.attrib["logical_name"],
			Path(element.attrib["physical_name"]),
			HistoryNodeKind(int(element.attrib["type"])),
			cls._ParseAttributes(element),
			parent=parent
		)

		for historyNodeElement in element.iterfind("ux:hnode", NAMESPACES):
			HistoryNode.Parse(historyNodeElement, parent=historyNode)

		return historyNode

	@readonly
	def Parent(self) -> Nullable[HistoryNodeParentType]:
		"""
		Read-only property to access the report or merge the history node belongs to (:attr:`_parent`).

		:returns: The :class:`Report` or :class:`HistoryNode`; ``None`` if the
		          history node belongs to none.
		"""
		return self._parent

	@readonly
	def PhysicalName(self) -> Path:
		"""
		Read-only property to access the path of the coverage database (:attr:`_physicalName`).

		:returns: The path, as the tool stated it, e.g. relative to the directory it ran in.
		"""
		return self._physicalName

	@readonly
	def Kind(self) -> HistoryNodeKind:
		"""
		Read-only property to access the kind of the history node (:attr:`_kind`).

		:returns: The kind: a test or a merge.
		"""
		return self._kind

	@readonly
	def HistoryNodes(self) -> list[HistoryNode[HistoryNode]]:
		"""
		Read-only property to access the history nodes merged by this one (:attr:`_historyNodes`).

		:returns: The history nodes, in the order the report lists them; empty for a test.
		"""
		return self._historyNodes


@export
class Command(metaclass=ExtendedType, slots=True):
	"""
	A ``<ux:command>`` of the report: a record of a command applied to the coverage database.

	An exclusion is such a command. Its fields are kept as stated, not interpreted.
	"""

	_parent: Nullable[Report]  #: The report the command belongs to.
	_type:   int               #: Kind of the command.
	_flags:  int               #: Flags of the command.
	_data:   str               #: Data of the command, e.g. a list of values separated by ``;``.
	_index:  int               #: Index of the command.

	def __init__(self, commandType: int, flags: int, data: str, index: int, *, parent: Nullable[Report] = None) -> None:
		"""
		Initialize the command, and append it to the commands of its report.

		:param commandType: Kind of the command.
		:param flags:       Flags of the command.
		:param data:        Data of the command.
		:param index:       Index of the command.
		:param parent:      Optional, the report the command belongs to; the command is appended to its commands.
		                    Default: ``None``.
		:raises ValueError: If parameter ``commandType`` is ``None``.
		:raises TypeError:  If parameter ``commandType`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``flags`` is ``None``.
		:raises TypeError:  If parameter ``flags`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``flags`` is negative.
		:raises ValueError: If parameter ``data`` is ``None``.
		:raises TypeError:  If parameter ``data`` isn't of type :class:`str`.
		:raises ValueError: If parameter ``index`` is ``None``.
		:raises TypeError:  If parameter ``index`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``index`` is negative.
		:raises TypeError:  If parameter ``parent`` isn't of type :class:`Report`.
		"""
		if commandType is None:
			raise ValueError("Parameter 'commandType' is None.")
		elif not isinstance(commandType, int):
			ex = TypeError("Parameter 'commandType' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(commandType)}'.")
			raise ex

		if flags is None:
			raise ValueError("Parameter 'flags' is None.")
		elif not isinstance(flags, int):
			ex = TypeError("Parameter 'flags' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(flags)}'.")
			raise ex
		elif flags < 0:
			ex = ValueError("Parameter 'flags' is negative.")
			ex.add_note(f"Got value '{flags}'.")
			raise ex

		if data is None:
			raise ValueError("Parameter 'data' is None.")
		elif not isinstance(data, str):
			ex = TypeError("Parameter 'data' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(data)}'.")
			raise ex

		if index is None:
			raise ValueError("Parameter 'index' is None.")
		elif not isinstance(index, int):
			ex = TypeError("Parameter 'index' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(index)}'.")
			raise ex
		elif index < 0:
			ex = ValueError("Parameter 'index' is negative.")
			ex.add_note(f"Got value '{index}'.")
			raise ex

		if parent is not None and not isinstance(parent, Report):
			ex = TypeError("Parameter 'parent' is not of type 'Report'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent = parent
		self._type =   commandType
		self._flags =  flags
		self._data =   data
		self._index =  index

		if parent is not None:
			parent._commands.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[Report] = None) -> Self:
		"""
		Parse a command from its ``<ux:command>`` element.

		:param element: The ``<ux:command>`` element.
		:param parent:  Optional, the report the command belongs to. Default: ``None``.
		:returns:       The command.
		"""
		return cls(
			int(element.attrib["type"]),
			int(element.attrib["flags"]),
			element.attrib["data"],
			int(element.attrib["index"]),
			parent=parent
		)

	@readonly
	def Parent(self) -> Nullable[Report]:
		"""
		Read-only property to access the report the command belongs to (:attr:`_parent`).

		:returns: The report; ``None`` if the command belongs to no report.
		"""
		return self._parent

	@readonly
	def Type(self) -> int:
		"""
		Read-only property to access the kind of the command (:attr:`_type`).

		:returns: The kind, as stated.
		"""
		return self._type

	@readonly
	def Flags(self) -> int:
		"""
		Read-only property to access the flags of the command (:attr:`_flags`).

		:returns: The flags, as stated.
		"""
		return self._flags

	@readonly
	def Data(self) -> str:
		"""
		Read-only property to access the data of the command (:attr:`_data`).

		:returns: The data, as stated, e.g. ``3;1;10;dut.sv;63;/project;0;0;``.
		"""
		return self._data

	@readonly
	def Index(self) -> int:
		"""
		Read-only property to access the index of the command (:attr:`_index`).

		:returns: The index, as stated.
		"""
		return self._index


@export
class Statement(metaclass=ExtendedType, slots=True):
	"""
	A statement of a source line: its statement bins - of one instance, or merged, of all instances -, and how often it
	ran.

	A statement isn't an element of the format: :meth:`Report.IterateStatements` computes it from the bins.
	"""

	_file:       Path       #: Path of the source file.
	_lineNumber: int        #: Line number, counted from 1.
	_index:      int        #: Index of the statement in its line.
	_bins:       list[Bin]  #: The statement bins of the statement.
	_count:      int        #: How often the statement ran: the sum of its bins' counts, without the excluded ones.
	_isExcluded: bool       #: Whether all the statement's bins are excluded.

	def __init__(self, file: Path, lineNumber: int, index: int, bins: Iterable[Bin]) -> None:
		"""
		Initialize the statement, its count and whether it is excluded.

		:param file:        Path of the source file, as the bins' source locations state it.
		:param lineNumber:  Line number, counted from 1.
		:param index:       Index of the statement in its line, counted from 1.
		:param bins:        The statement bins of the statement: one, or of all instances, if merged.
		:raises ValueError: If parameter ``file`` is ``None``.
		:raises TypeError:  If parameter ``file`` isn't of type :class:`~pathlib.Path`.
		:raises ValueError: If parameter ``lineNumber`` is ``None``.
		:raises TypeError:  If parameter ``lineNumber`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``lineNumber`` is less than 1.
		:raises ValueError: If parameter ``index`` is ``None``.
		:raises TypeError:  If parameter ``index`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``index`` is negative.
		:raises ValueError: If parameter ``bins`` is ``None``.
		:raises TypeError:  If parameter ``bins`` isn't iterable.
		:raises TypeError:  If parameter ``bins`` contains an element not of type
		                    :class:`Bin`.
		:raises ValueError: If parameter ``bins`` is empty.
		"""
		if file is None:
			raise ValueError("Parameter 'file' is None.")
		elif not isinstance(file, Path):
			ex = TypeError("Parameter 'file' is not of type 'Path'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(file)}'.")
			raise ex

		if lineNumber is None:
			raise ValueError("Parameter 'lineNumber' is None.")
		elif not isinstance(lineNumber, int):
			ex = TypeError("Parameter 'lineNumber' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(lineNumber)}'.")
			raise ex
		elif lineNumber < 1:
			ex = ValueError("Parameter 'lineNumber' is less than 1.")
			ex.add_note(f"Got value '{lineNumber}'.")
			raise ex

		if index is None:
			raise ValueError("Parameter 'index' is None.")
		elif not isinstance(index, int):
			ex = TypeError("Parameter 'index' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(index)}'.")
			raise ex
		elif index < 0:
			ex = ValueError("Parameter 'index' is negative.")
			ex.add_note(f"Got value '{index}'.")
			raise ex

		if bins is None:
			raise ValueError("Parameter 'bins' is None.")
		elif not isinstance(bins, Iterable):
			ex = TypeError("Parameter 'bins' is not iterable.")
			ex.add_note(f"Got type '{getFullyQualifiedName(bins)}'.")
			raise ex

		self._file =       file
		self._lineNumber = lineNumber
		self._index =      index
		self._bins =       binList = []
		self._count =      0
		self._isExcluded = True

		for coverBin in bins:
			if not isinstance(coverBin, Bin):
				ex = TypeError("Parameter 'bins' contains an element not of type 'Bin'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(coverBin)}'.")
				raise ex

			binList.append(coverBin)
			if not coverBin.IsExcluded:
				self._count +=     coverBin._count
				self._isExcluded = False

		if len(self._bins) == 0:
			raise ValueError("Parameter 'bins' is empty.")

	@readonly
	def File(self) -> Path:
		"""
		Read-only property to access the path of the source file (:attr:`_file`).

		:returns: The path, as the bins' source locations state it.
		"""
		return self._file

	@readonly
	def LineNumber(self) -> int:
		"""
		Read-only property to access the line number (:attr:`_lineNumber`).

		:returns: The line number, counted from 1.
		"""
		return self._lineNumber

	@readonly
	def Index(self) -> int:
		"""
		Read-only property to access the index of the statement in its line (:attr:`_index`).

		:returns: The index, counted from 1.
		"""
		return self._index

	@readonly
	def Bins(self) -> list[Bin]:
		"""
		Read-only property to access the statement bins of the statement (:attr:`_bins`).

		:returns: The bins: one, or of all instances, if merged.
		"""
		return self._bins

	@readonly
	def Count(self) -> int:
		"""
		Read-only property to access how often the statement ran (:attr:`_count`).

		:returns: The sum of the counts of the bins, which aren't excluded.
		"""
		return self._count

	@readonly
	def IsExcluded(self) -> bool:
		"""
		Read-only property to access whether the statement is excluded from the measurement (:attr:`_isExcluded`).

		:returns: ``True``, if all its bins are excluded.
		"""
		return self._isExcluded


@export
class Report(AttributesMixin, mixin=True):
	"""
	The root element ``<ux:ucdb>``: the tool, which wrote it, its attributes, the history nodes, the scopes and the
	commands.

	The root of the format's model: a history node, a scope or a command names it as its parent.
	"""

	_tool:         Nullable[str]               #: Name of the tool, which wrote the report.
	_toolVersion:  Nullable[CalendarVersion]   #: Version of the tool, which wrote the report.
	_historyNodes: list[HistoryNode[Report]]   #: The history nodes.
	_scopes:       list[Scope[Report]]         #: The top-level scopes.
	_commands:     list[Command]               #: The commands.

	def __init__(self) -> None:
		"""
		Initialize an empty report.
		"""
		AttributesMixin.__init__(self)

		self._tool =         None
		self._toolVersion =  None
		self._historyNodes = []
		self._scopes =       []
		self._commands =     []

	@readonly
	def Tool(self) -> Nullable[str]:
		"""
		Read-only property to access the name of the tool, which wrote the report (:attr:`_tool`).

		:returns: The tool's name, e.g. ``Riviera-PRO``; ``None`` before the report was converted.
		"""
		return self._tool

	@readonly
	def ToolVersion(self) -> Nullable[CalendarVersion]:
		"""
		Read-only property to access the version of the tool, which wrote the report (:attr:`_toolVersion`).

		:returns: The tool's version, e.g. ``2022.04``; ``None`` before the report was converted.
		"""
		return self._toolVersion

	@readonly
	def HistoryNodes(self) -> list[HistoryNode[Report]]:
		"""
		Read-only property to access the history nodes (:attr:`_historyNodes`).

		:returns: The history nodes, in the order the report lists them: the tests, or the merge of the tests.
		"""
		return self._historyNodes

	@readonly
	def Scopes(self) -> list[Scope[Report]]:
		"""
		Read-only property to access the top-level scopes (:attr:`_scopes`).

		:returns: The scopes, in the order the report lists them: e.g. the design units and the top-level instances.
		"""
		return self._scopes

	@readonly
	def Commands(self) -> list[Command]:
		"""
		Read-only property to access the commands (:attr:`_commands`).

		:returns: The commands, in the order the report lists them.
		"""
		return self._commands

	def IterateStatements(self, mergeInstances: bool = False) -> Generator[Statement, None, None]:
		"""
		Iterate the statements: the statement bins of the instances.

		The statement bins are those of the scopes below each top-level scope, which isn't a design unit. A statement is
		identified by its file, its line and its index in the line - attribute ``#SINDEX#`` of its bin.

		:param mergeInstances:     Optional, if true, merge the bins of all instances, which identify the same statement,
		                           into one statement; otherwise each bin is a statement. Default: ``False``.
		:returns:                  A generator of the statements, in the order of their first bin.
		:raises ValueError:        If parameter ``mergeInstances`` is ``None``.
		:raises TypeError:         If parameter ``mergeInstances`` isn't of type :class:`bool`.
		:raises CodeCoverageError: If a statement bin states no statement index.
		"""
		if mergeInstances is None:
			raise ValueError("Parameter 'mergeInstances' is None.")
		elif not isinstance(mergeInstances, bool):
			ex = TypeError("Parameter 'mergeInstances' is not of type 'bool'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(mergeInstances)}'.")
			raise ex

		designUnits = (
			ScopeType.DesignUnitModule, ScopeType.DesignUnitArchitecture, ScopeType.DesignUnitPackage,
			ScopeType.DesignUnitProgram, ScopeType.DesignUnitInterface
		)
		mergedBins: dict[tuple[Path, int, int], list[Bin]] = {}
		for scope in self._scopes:
			if scope._type in designUnits:
				continue

			for coverBin in scope.IterateBins():
				if coverBin._type is not CoverType.StatementBin:
					continue

				source = coverBin._source
				if not isinstance(index := coverBin._attributes.get("#SINDEX#"), int):
					ex = CodeCoverageError(
						f"UCDB statement bin at '{source._file.as_posix()}:{source._lineNumber}' states no statement index."
					)
					ex.add_note("A statement bin states its index in the line by attribute '#SINDEX#' of type 'int'.")
					raise ex

				if mergeInstances:
					mergedBins.setdefault((source._file, source._lineNumber, index), []).append(coverBin)
				else:
					yield Statement(source._file, source._lineNumber, index, (coverBin, ))

		for (file, lineNumber, index), bins in mergedBins.items():
			yield Statement(file, lineNumber, index, bins)


@export
class Document(cc_Document, Report):
	"""
	An Aldec UCDB XML code coverage report: read into the format's model, and converted to the common model.
	"""

	_xmlDocument: Nullable[_ElementTree]  #: The parsed and validated XML document, after :meth:`Analyze`.

	def __init__(self, xmlReportFile: Path, analyzeAndConvert: bool = False) -> None:
		"""
		Initialize the report, and optionally read it.

		:param xmlReportFile:     Path to the UCDB XML file.
		:param analyzeAndConvert: Optional, if true, analyze the file and convert its content. Default: ``False``.
		"""
		super().__init__(xmlReportFile)
		Report.__init__(self)

		self._xmlDocument = None

		if analyzeAndConvert:
			self.Analyze()
			self.Convert()

	def Analyze(self) -> None:
		"""
		Parse the XML file, check its root element, and validate the file against the XML schema (:data:`SCHEMA`).

		:raises CodeCoverageError: If the file doesn't exist.
		:raises CodeCoverageError: If the file can't be read.
		:raises CodeCoverageError: If the file isn't well-formed XML.
		:raises CodeCoverageError: If the root element isn't ``<ux:ucdb>`` of namespace ``www.aldec.com``.
		:raises CodeCoverageError: If the XML schema can't be located or parsed.
		:raises CodeCoverageError: If the file isn't valid according to the XML schema.
		"""
		if not self._path.exists():
			raise CodeCoverageError(f"Aldec UCDB file '{self._path}' does not exist.") \
				from FileNotFoundError(f"File '{self._path}' not found.")

		with Stopwatch() as sw:
			try:
				content = self._path.read_bytes()
			except OSError as ex:
				raise CodeCoverageError(f"Couldn't read Aldec UCDB file '{self._path}'.") from ex

			try:
				xmlDocument = parse(BytesIO(content), XMLParser(ns_clean=True), base_url=str(self._path))
			except XMLSyntaxError as ex:
				raise CodeCoverageError(f"XML syntax error in Aldec UCDB file '{self._path}'.") from ex

			rootElement: _Element = xmlDocument.getroot()
			if rootElement.tag != f"{{{NAMESPACE}}}ucdb":
				ex = CodeCoverageError(f"Root element of '{self._path}' is not '<ux:ucdb>' of namespace '{NAMESPACE}'.")
				ex.add_note(f"Got root element '<{rootElement.tag}>'.")
				raise ex

			try:
				schemaResourceFile = getResourceFile(Resources, SCHEMA)
			except ToolingException as ex:
				raise CodeCoverageError(f"Couldn't locate XML Schema '{SCHEMA}' in package resources.") from ex

			try:
				xmlSchema = XMLSchema(parse(schemaResourceFile, XMLParser(ns_clean=True)))
			except (XMLSyntaxError, XMLSchemaParseError) as ex:
				raise CodeCoverageError(f"Error while parsing XML Schema '{SCHEMA}'.") from ex

			if not xmlSchema.validate(xmlDocument):
				ex = CodeCoverageError(f"Validation error for '{self._path}' using XSD schema '{SCHEMA}'.")
				for logEntry in xmlSchema.error_log:
					ex.add_note(str(logEntry))
				raise ex

			self._xmlDocument = xmlDocument

		self._analysisDuration = sw.Duration

	def Convert(self) -> None:
		"""
		Convert the parsed and validated XML document to the format's model.

		:raises CodeCoverageError: If the XML file was not analyzed before. |br|
		                           Call 'Document.Analyze()' or create the document using
		                           'Document(path, analyzeAndConvert=True)'.
		:raises CodeCoverageError: If an attribute's value isn't of the type the attribute states.
		"""
		if self._xmlDocument is None:
			ex = CodeCoverageError(f"Aldec UCDB file '{self._path}' needs to be read and analyzed by an XML parser.")
			ex.add_note("Call 'Document.Analyze()' or create the document using 'Document(path, analyzeAndConvert=True)'.")
			raise ex

		with Stopwatch() as sw:
			root: _Element = self._xmlDocument.getroot()
			tool, _, version = root.attrib["version"].rpartition(" ")
			self._tool =        tool
			self._toolVersion = CalendarVersion.Parse(version)
			self._attributes =  self._ParseAttributes(root)

			for historyNodeElement in root.iterfind("ux:hnode", NAMESPACES):
				HistoryNode.Parse(historyNodeElement, parent=self)

			for scopeElement in root.iterfind("ux:scope", NAMESPACES):
				Scope.Parse(scopeElement, parent=self)

			for commandElement in root.iterfind("ux:command", NAMESPACES):
				Command.Parse(commandElement, parent=self)

		self._conversionDuration = sw.Duration

	def ToCoverageSummary(self, mergeInstances: bool = False) -> CoverageSummary:
		"""
		Convert the statement coverage of the format's model to the common model, and aggregate it.

		A line ran as often as its least often run statement (:meth:`~Report.IterateStatements`): it is covered, if all its
		statements ran, otherwise uncovered. A line, whose statements are all excluded, is excluded.

		:param mergeInstances:     Optional, if true, merge the statements of all instances of a design unit. Default:
		                           ``False``.
		:returns:                  The report's root of the common model, named after the report file. Its source
		                           directories are the directories the tool ran in.
		:raises ValueError:        If parameter ``mergeInstances`` is ``None``.
		:raises TypeError:         If parameter ``mergeInstances`` isn't of type :class:`bool`.
		:raises CodeCoverageError: If a statement bin states no statement index.
		:raises CodeCoverageError: If a file's path runs through another file.
		"""
		statementsPerFile: dict[Path, dict[int, list[Statement]]] = {}
		sourceDirectories: dict[Path, None] = {}
		for statement in self.IterateStatements(mergeInstances):
			statementsPerFile.setdefault(statement._file, {}).setdefault(statement._lineNumber, []).append(statement)
			for coverBin in statement._bins:
				sourceDirectories[coverBin._source._workDirectory] = None

		summary = CoverageSummary(self._path.stem, sourceDirectories=sourceDirectories)
		for path, statementsPerLine in statementsPerFile.items():
			file = summary.GetOrAddFile(path)
			for lineNumber in sorted(statementsPerLine):
				counts = [statement._count for statement in statementsPerLine[lineNumber] if not statement._isExcluded]
				if len(counts) == 0:
					cc_Line(lineNumber, LineCoverageStatus.Excluded, parent=file)
				else:
					count = min(counts)
					status = LineCoverageStatus.Covered if count > 0 else LineCoverageStatus.Uncovered
					cc_Line(lineNumber, status, count, parent=file)

		summary.Aggregate()
		return summary
