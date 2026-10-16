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
JaCoCo's XML code coverage format: a model of the format, read from a report and converted to the common model.

JaCoCo - the Java code coverage library - writes its XML report with ``jacococli.jar report --xml``, Maven's goals
``report`` and ``report-aggregate``, Ant's task ``report`` or Gradle's task ``jacocoTestReport``. A report names its
DTD by a public identifier, e.g. ``-//JACOCO//DTD Report 1.1//EN``, whose version (:class:`FormatVersion`) chooses the
XML schema a report is validated against: :file:`JaCoCo-1.1.xsd`, a translation of JaCoCo's DTD ``report.dtd``. The
format's model keeps what the report states: a :class:`Document` holds :class:`SessionInfo` elements, :class:`Group`
elements - nested -, and :class:`Package` elements; a package holds :class:`Class` elements with their :class:`Method`
elements, and :class:`SourceFile` elements with their :class:`Line` elements. Every element but a line and a session
states its :class:`Counter` elements. Each element's constructor takes typed values, so the model can be built by hand:
an element below the report names its parent with the keyword parameter ``parent`` and is added to it. Its class method
``Parse`` reads the element's XML element.

:meth:`Document.ToCoverageSummary` converts the model to the common model of :mod:`pyEDAA.Reports.CodeCoverage`:

* A source file's path is its package's name in VM notation - e.g. ``my/pack`` - and its name, relative to a source
  directory, which the report doesn't name.
* A line ran, if it has a covered instruction - partially covered, if it has a missed branch. Its missed and covered
  branches become as many branches. The format has no counts, no branch targets and no excluded lines.
* The packages, classes and methods become units of the logical hierarchy; a package's name is split at ``/`` into
  nested packages. A method spans its first line and the next lines of its file, as many as its ``LINE`` counter
  counts; a class spans its methods. The groups have no counterpart.

.. rubric:: Example

.. code-block:: Python

   from pathlib import Path
   from pyEDAA.Reports.CodeCoverage.JaCoCo import Document

   report = Document(Path("jacocoTestReport.xml"), analyzeAndConvert=True)
   summary = report.ToCoverageSummary()
   for unit in summary.IterateUnits():
     print(f"{unit.QualifiedName}: {unit.LineCoverage:.1%}")
"""
from __future__                  import annotations

from datetime                    import datetime, timedelta, timezone
from io                          import BytesIO
from itertools                   import islice
from pathlib                     import Path
from re                          import compile as re_compile
from typing                      import Generator, Generic, Optional as Nullable, Self, TypeVar

from lxml.etree                  import XMLParser, XMLSchema, XMLSchemaParseError, XMLSyntaxError
from lxml.etree                  import _Element, _ElementTree, parse
from pyTooling.Common            import getFullyQualifiedName, getResourceFile, StringEnum
from pyTooling.Decorators        import export, readonly
from pyTooling.Exceptions        import ToolingException
from pyTooling.MetaClasses       import ExtendedType, abstractclass
from pyTooling.Stopwatch         import Stopwatch

from pyEDAA.Reports              import Resources
from pyEDAA.Reports.CodeCoverage import Branch as cc_Branch, Class as cc_Class, CodeCoverageError
from pyEDAA.Reports.CodeCoverage import CoverageSummary, Document as cc_Document, Line as cc_Line
from pyEDAA.Reports.CodeCoverage import LineCoverageStatus, Method as cc_Method, Package as cc_Package
from pyEDAA.Reports.CodeCoverage import Unit as cc_Unit


__all__ = ["PUBLIC_IDENTIFIER", "SCHEMAS"]

#: Pattern of the DTD's public identifier a report states, capturing the version, e.g. ``1.1``.
PUBLIC_IDENTIFIER = re_compile(r"-//JACOCO//DTD Report (\S+)//EN")

ParentType = TypeVar("ParentType", bound="Report | Group")
"""A type variable for the parent of a :class:`Group` or :class:`Package`: a :class:`Report` or a :class:`Group`."""


@export
class FormatVersion(StringEnum):
	"""
	Version of the JaCoCo XML format: the version of the DTD, whose public identifier a report states.
	"""

	Version1_1 = "1.1"  #: Format 1.1, public identifier ``-//JACOCO//DTD Report 1.1//EN``.


# A class with a property named like a class - ``FormatVersion`` - can't name that class in the annotation of a field:
# the class body's namespace, where annotations are evaluated, binds the name to the property.
_FormatVersion = FormatVersion

SCHEMAS: dict[FormatVersion, str] = {
	FormatVersion.Version1_1: "JaCoCo-1.1.xsd"
}  #: Per format version, the XML schema a report of that version is validated against.


@export
class CounterType(StringEnum):
	"""
	Kind of items a ``<counter>`` counts, as its ``type`` states.
	"""

	Instruction = "INSTRUCTION"  #: Java bytecode instructions.
	Branch =      "BRANCH"       #: Branches of ``if`` and ``switch`` statements.
	Line =        "LINE"         #: Source lines with at least one instruction.
	Complexity =  "COMPLEXITY"   #: Cyclomatic complexity: paths, which in linear combination generate all paths.
	Method =      "METHOD"       #: Methods - also constructors and static initializers - with at least one instruction.
	Class =       "CLASS"        #: Classes with at least one method.


@export
class CountersMixin(metaclass=ExtendedType, mixin=True):
	"""
	A mixin-class adding the counters an element states: per kind of items, how many were missed and covered.
	"""

	_counters: dict[CounterType, Counter]  #: The counters, by kind.

	def __init__(self) -> None:
		"""
		Initialize the counters to none.

		A counter is added by creating it with the element as its parent.
		"""
		self._counters = {}

	@readonly
	def Counters(self) -> dict[CounterType, Counter]:
		"""
		Read-only property to access the counters (:attr:`_counters`).

		:returns: The counters, by kind; a kind without items has no counter.
		"""
		return self._counters


@export
@abstractclass
class Base(metaclass=ExtendedType, slots=True):
	"""
	Base-class of the named elements below the report.

	Packages and classes are named elements.
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
			raise ValueError(f"Parameter 'name' is None.")
		elif not isinstance(name, str):
			ex = TypeError(f"Parameter 'name' is not of type 'str'.")
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
class Counter(metaclass=ExtendedType, slots=True):
	"""
	A ``<counter>`` of an element: how many items of a kind were missed and covered.
	"""

	_parent:       Nullable[CountersMixin]  #: The element the counter belongs to.
	_type:         CounterType              #: Kind of items the counter counts.
	_missedCount:  int                      #: Number of missed items.
	_coveredCount: int                      #: Number of covered items.

	def __init__(
		self,
		counterType:  CounterType,
		missedCount:  int,
		coveredCount: int,
		*,
		parent:       Nullable[CountersMixin] = None
	) -> None:
		"""
		Initialize the counter, and add it to the counters of its element.

		:param counterType:  Kind of items the counter counts.
		:param missedCount:  Number of missed items.
		:param coveredCount: Number of covered items.
		:param parent:       Optional, the element the counter belongs to; the counter is added to its counters by
		                     :attr:`Type`. Default: ``None``.
		:raises ValueError:  If parameter ``counterType`` is ``None``.
		:raises TypeError:   If parameter ``counterType`` isn't of type :class:`CounterType`.
		:raises ValueError:  If parameter ``missedCount`` is ``None``.
		:raises TypeError:   If parameter ``missedCount`` isn't of type :class:`int`.
		:raises ValueError:  If parameter ``missedCount`` is negative.
		:raises ValueError:  If parameter ``coveredCount`` is ``None``.
		:raises TypeError:   If parameter ``coveredCount`` isn't of type :class:`int`.
		:raises ValueError:  If parameter ``coveredCount`` is negative.
		:raises TypeError:   If parameter ``parent`` isn't of type :class:`CountersMixin`.
		"""
		if counterType is None:
			raise ValueError(f"Parameter 'counterType' is None.")
		elif not isinstance(counterType, CounterType):
			ex = TypeError(f"Parameter 'counterType' is not of type 'CounterType'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(counterType)}'.")
			raise ex

		if missedCount is None:
			raise ValueError(f"Parameter 'missedCount' is None.")
		elif not isinstance(missedCount, int):
			ex = TypeError(f"Parameter 'missedCount' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(missedCount)}'.")
			raise ex
		elif missedCount < 0:
			ex = ValueError(f"Parameter 'missedCount' is negative.")
			ex.add_note(f"Got value '{missedCount}'.")
			raise ex

		if coveredCount is None:
			raise ValueError(f"Parameter 'coveredCount' is None.")
		elif not isinstance(coveredCount, int):
			ex = TypeError(f"Parameter 'coveredCount' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(coveredCount)}'.")
			raise ex
		elif coveredCount < 0:
			ex = ValueError(f"Parameter 'coveredCount' is negative.")
			ex.add_note(f"Got value '{coveredCount}'.")
			raise ex

		if parent is not None and not isinstance(parent, CountersMixin):
			ex = TypeError(f"Parameter 'parent' is not of type 'CountersMixin'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =       parent
		self._type =         counterType
		self._missedCount =  missedCount
		self._coveredCount = coveredCount

		if parent is not None:
			parent._counters[self._type] = self

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[CountersMixin] = None) -> Self:
		"""
		Parse a counter from its ``<counter>`` element.

		:param element: The ``<counter>`` element.
		:param parent:  Optional, the element the counter belongs to. Default: ``None``.
		:returns:       The counter.
		"""
		return cls(
			CounterType(element.attrib["type"]),
			int(element.attrib["missed"]),
			int(element.attrib["covered"]),
			parent=parent
		)

	@readonly
	def Parent(self) -> Nullable[CountersMixin]:
		"""
		Read-only property to access the element the counter belongs to (:attr:`_parent`).

		:returns: The element; ``None`` if the counter belongs to no element.
		"""
		return self._parent

	@readonly
	def Type(self) -> CounterType:
		"""
		Read-only property to access the kind of items the counter counts (:attr:`_type`).

		:returns: The kind of items.
		"""
		return self._type

	@readonly
	def MissedCount(self) -> int:
		"""
		Read-only property to access the number of missed items (:attr:`_missedCount`).

		:returns: The number of missed items.
		"""
		return self._missedCount

	@readonly
	def CoveredCount(self) -> int:
		"""
		Read-only property to access the number of covered items (:attr:`_coveredCount`).

		:returns: The number of covered items.
		"""
		return self._coveredCount


@export
class SessionInfo(metaclass=ExtendedType, slots=True):
	"""
	A ``<sessioninfo>`` of the report: a session, which contributed execution data - its ID, its start and its dump.
	"""

	_parent:    Nullable[Report]  #: The report the session belongs to.
	_sessionID: str               #: ID of the session.
	_start:     datetime          #: Time the session started.
	_dump:      datetime          #: Time the session's execution data was dumped.

	def __init__(self, sessionID: str, start: datetime, dump: datetime, *, parent: Nullable[Report] = None) -> None:
		"""
		Initialize the session, and append it to the sessions of its report.

		:param sessionID:   ID of the session, e.g. the host's name and a random number.
		:param start:       Time the session started.
		:param dump:        Time the session's execution data was dumped.
		:param parent:      Optional, the report the session belongs to; the session is appended to its sessions.
		                    Default: ``None``.
		:raises ValueError: If parameter ``sessionID`` is ``None``.
		:raises TypeError:  If parameter ``sessionID`` isn't of type :class:`str`.
		:raises ValueError: If parameter ``start`` is ``None``.
		:raises TypeError:  If parameter ``start`` isn't of type :class:`~datetime.datetime`.
		:raises ValueError: If parameter ``dump`` is ``None``.
		:raises TypeError:  If parameter ``dump`` isn't of type :class:`~datetime.datetime`.
		:raises TypeError:  If parameter ``parent`` isn't of type :class:`~pyEDAA.Reports.CodeCoverage.JaCoCo.Report`.
		"""
		if sessionID is None:
			raise ValueError(f"Parameter 'sessionID' is None.")
		elif not isinstance(sessionID, str):
			ex = TypeError(f"Parameter 'sessionID' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(sessionID)}'.")
			raise ex

		if start is None:
			raise ValueError(f"Parameter 'start' is None.")
		elif not isinstance(start, datetime):
			ex = TypeError(f"Parameter 'start' is not of type 'datetime'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(start)}'.")
			raise ex

		if dump is None:
			raise ValueError(f"Parameter 'dump' is None.")
		elif not isinstance(dump, datetime):
			ex = TypeError(f"Parameter 'dump' is not of type 'datetime'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(dump)}'.")
			raise ex

		if parent is not None and not isinstance(parent, Report):
			ex = TypeError(f"Parameter 'parent' is not of type 'Report'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =    parent
		self._sessionID = sessionID
		self._start =     start
		self._dump =      dump

		if parent is not None:
			parent._sessionInfos.append(self)

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[Report] = None) -> Self:
		"""
		Parse a session from its ``<sessioninfo>`` element.

		The times are stated in milliseconds since the epoch.

		:param element: The ``<sessioninfo>`` element.
		:param parent:  Optional, the report the session belongs to. Default: ``None``.
		:returns:       The session.
		"""
		epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
		return cls(
			element.attrib["id"],
			epoch + timedelta(milliseconds=int(element.attrib["start"])),
			epoch + timedelta(milliseconds=int(element.attrib["dump"])),
			parent=parent
		)

	@readonly
	def Parent(self) -> Nullable[Report]:
		"""
		Read-only property to access the report the session belongs to (:attr:`_parent`).

		:returns: The report; ``None`` if the session belongs to no report.
		"""
		return self._parent

	@readonly
	def SessionID(self) -> str:
		"""
		Read-only property to access the ID of the session (:attr:`_sessionID`).

		JaCoCo's agent names a session by the host's name and a random number, e.g. ``dffa20ef8728-f9da5560``.

		:returns: The ID.
		"""
		return self._sessionID

	@readonly
	def Start(self) -> datetime:
		"""
		Read-only property to access the time the session started (:attr:`_start`).

		:returns: The time, with time zone UTC, if read from a report.
		"""
		return self._start

	@readonly
	def Dump(self) -> datetime:
		"""
		Read-only property to access the time the session's execution data was dumped (:attr:`_dump`).

		:returns: The time, with time zone UTC, if read from a report.
		"""
		return self._dump


@export
class Method(Base, CountersMixin):
	"""
	A ``<method>`` of a class: its descriptor, its first line and its counters.
	"""

	_parent:     Nullable[Class]  #: The class the method belongs to.
	_descriptor: str              #: Descriptor of the method: the types of its parameters and result, in VM notation.
	_lineNumber: Nullable[int]    #: The method's first source line, if the report says.

	def __init__(
		self,
		name:       str,
		descriptor: str,
		lineNumber: Nullable[int] = None,
		*,
		parent:     Nullable[Class] = None
	) -> None:
		"""
		Initialize the method, and add it to the methods of its class.

		Its counters are added by creating them with this method as their parent.

		:param name:        Name of the method, e.g. ``absolute``; ``<init>`` for a constructor.
		:param descriptor:  Descriptor of the method, e.g. ``(I)I`` for a method taking and returning an ``int``.
		:param lineNumber:  Optional, the method's first source line. Default: ``None``.
		:param parent:      Optional, the class the method belongs to; the method is added to its methods by
		                    :attr:`Name` and :attr:`Descriptor`. Default: ``None``.
		:raises ValueError: If parameter ``name`` is ``None``.
		:raises TypeError:  If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError: If parameter ``name`` is empty.
		:raises ValueError: If parameter ``descriptor`` is ``None``.
		:raises TypeError:  If parameter ``descriptor`` isn't of type :class:`str`.
		:raises ValueError: If parameter ``descriptor`` is empty.
		:raises TypeError:  If parameter ``lineNumber`` isn't of type :class:`int`.
		:raises ValueError: If parameter ``lineNumber`` is less than 1.
		:raises TypeError:  If parameter ``parent`` isn't of type :class:`Class`.
		"""
		super().__init__(name)
		CountersMixin.__init__(self)

		if name == "":
			raise ValueError(f"Parameter 'name' is empty.")

		if descriptor is None:
			raise ValueError(f"Parameter 'descriptor' is None.")
		elif not isinstance(descriptor, str):
			ex = TypeError(f"Parameter 'descriptor' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(descriptor)}'.")
			raise ex
		elif descriptor == "":
			raise ValueError(f"Parameter 'descriptor' is empty.")

		if lineNumber is not None:
			if not isinstance(lineNumber, int):
				ex = TypeError(f"Parameter 'lineNumber' is not of type 'int'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(lineNumber)}'.")
				raise ex
			elif lineNumber < 1:
				ex = ValueError(f"Parameter 'lineNumber' is less than 1.")
				ex.add_note(f"Got value '{lineNumber}'.")
				raise ex

		if parent is not None and not isinstance(parent, Class):
			ex = TypeError(f"Parameter 'parent' is not of type 'Class'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =     parent
		self._descriptor = descriptor
		self._lineNumber = lineNumber

		if parent is not None:
			parent._methods[f"{self._name}{self._descriptor}"] = self

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[Class] = None) -> Self:
		"""
		Parse a method and its counters from its ``<method>`` element.

		:param element:            The ``<method>`` element.
		:param parent:             Optional, the class the method belongs to. Default: ``None``.
		:returns:                  The method.
		:raises CodeCoverageError: If the method states a counter twice.
		"""
		method = cls(
			element.attrib["name"],
			element.attrib["desc"],
			int(line) if (line := element.attrib.get("line")) is not None else None,
			parent=parent
		)

		for counterElement in element.iterfind("counter"):
			if (counterType := CounterType(counterElement.attrib["type"])) in method._counters:
				raise CodeCoverageError(
					f"JaCoCo method '{method._name}{method._descriptor}' states counter '{counterType}' twice."
				)

			Counter.Parse(counterElement, parent=method)

		return method

	@readonly
	def Parent(self) -> Nullable[Class]:
		"""
		Read-only property to access the class the method belongs to (:attr:`_parent`).

		:returns: The class; ``None`` if the method belongs to no class.
		"""
		return self._parent

	@readonly
	def Descriptor(self) -> str:
		"""
		Read-only property to access the descriptor of the method (:attr:`_descriptor`).

		The descriptor ``([Ljava/lang/String;)V`` is of a method taking a ``String[]`` and returning ``void``.

		:returns: The descriptor, in VM notation.
		"""
		return self._descriptor

	@readonly
	def LineNumber(self) -> Nullable[int]:
		"""
		Read-only property to access the method's first source line (:attr:`_lineNumber`).

		A method of a class compiled without debug information has none.

		:returns: The line number, or ``None`` if the report doesn't say.
		"""
		return self._lineNumber


@export
class Class(Base, CountersMixin):
	"""
	A ``<class>`` of a package: its source file, its methods and its counters.
	"""

	_parent:         Nullable[Package]  #: The package the class belongs to.
	_sourceFileName: Nullable[str]      #: Name of the class' source file, if the report says.
	_methods:        dict[str, Method]  #: The methods, by name and descriptor.

	def __init__(self, name: str, sourceFileName: Nullable[str] = None, *, parent: Nullable[Package] = None) -> None:
		"""
		Initialize the class, and add it to the classes of its package.

		Its methods and counters are added by creating them with this class as their parent.

		:param name:           Fully qualified name of the class in VM notation, e.g. ``my/pack/MyClass``.
		:param sourceFileName: Optional, name of the class' source file, e.g. ``MyClass.java``. Default: ``None``.
		:param parent:         Optional, the package the class belongs to; the class is added to its classes by
		                       :attr:`Name`. Default: ``None``.
		:raises ValueError:    If parameter ``name`` is ``None``.
		:raises TypeError:     If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError:    If parameter ``name`` is empty.
		:raises TypeError:     If parameter ``sourceFileName`` isn't of type :class:`str`.
		:raises TypeError:     If parameter ``parent`` isn't of type :class:`~pyEDAA.Reports.CodeCoverage.JaCoCo.Package`.
		"""
		super().__init__(name)
		CountersMixin.__init__(self)

		if name == "":
			raise ValueError(f"Parameter 'name' is empty.")

		if sourceFileName is not None and not isinstance(sourceFileName, str):
			ex = TypeError(f"Parameter 'sourceFileName' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(sourceFileName)}'.")
			raise ex

		if parent is not None and not isinstance(parent, Package):
			ex = TypeError(f"Parameter 'parent' is not of type 'Package'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =         parent
		self._sourceFileName = sourceFileName
		self._methods =        {}

		if parent is not None:
			parent._classes[self._name] = self

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[Package] = None) -> Self:
		"""
		Parse a class, its methods and counters from its ``<class>`` element.

		:param element:            The ``<class>`` element.
		:param parent:             Optional, the package the class belongs to. Default: ``None``.
		:returns:                  The class.
		:raises CodeCoverageError: If the class states a method twice.
		:raises CodeCoverageError: If the class states a counter twice.
		"""
		klass = cls(element.attrib["name"], element.attrib.get("sourcefilename"), parent=parent)

		for methodElement in element.iterfind("method"):
			if (key := f"{methodElement.attrib['name']}{methodElement.attrib['desc']}") in klass._methods:
				raise CodeCoverageError(f"JaCoCo class '{klass._name}' states method '{key}' twice.")

			Method.Parse(methodElement, parent=klass)

		for counterElement in element.iterfind("counter"):
			if (counterType := CounterType(counterElement.attrib["type"])) in klass._counters:
				raise CodeCoverageError(f"JaCoCo class '{klass._name}' states counter '{counterType}' twice.")

			Counter.Parse(counterElement, parent=klass)

		return klass

	@readonly
	def Parent(self) -> Nullable[Package]:
		"""
		Read-only property to access the package the class belongs to (:attr:`_parent`).

		:returns: The package; ``None`` if the class belongs to no package.
		"""
		return self._parent

	@readonly
	def SourceFileName(self) -> Nullable[str]:
		"""
		Read-only property to access the name of the class' source file (:attr:`_sourceFileName`).

		A class compiled without debug information names no source file.

		:returns: The name of a :class:`SourceFile` of the class' package, or ``None`` if the report doesn't say.
		"""
		return self._sourceFileName

	@readonly
	def Methods(self) -> dict[str, Method]:
		"""
		Read-only property to access the methods (:attr:`_methods`).

		A method is keyed by its name and descriptor, e.g. ``absolute(I)I``.

		:returns: The methods, by name and descriptor.
		"""
		return self._methods


@export
class Line(metaclass=ExtendedType, slots=True):
	"""
	A ``<line>`` of a source file: its missed and covered instructions and branches.
	"""

	_parent:                  Nullable[SourceFile]  #: The source file the line belongs to.
	_lineNumber:              int                   #: Line number, counted from 1.
	_missedInstructionCount:  Nullable[int]         #: Number of missed instructions, if the report says.
	_coveredInstructionCount: Nullable[int]         #: Number of covered instructions, if the report says.
	_missedBranchCount:       Nullable[int]         #: Number of missed branches, if the report says.
	_coveredBranchCount:      Nullable[int]         #: Number of covered branches, if the report says.

	def __init__(
		self,
		lineNumber:              int,
		missedInstructionCount:  Nullable[int] = None,
		coveredInstructionCount: Nullable[int] = None,
		missedBranchCount:       Nullable[int] = None,
		coveredBranchCount:      Nullable[int] = None,
		*,
		parent:                  Nullable[SourceFile] = None
	) -> None:
		"""
		Initialize the line, and add it to the lines of its source file.

		:param lineNumber:              Line number, counted from 1.
		:param missedInstructionCount:  Optional, number of missed instructions. Default: ``None``.
		:param coveredInstructionCount: Optional, number of covered instructions. Default: ``None``.
		:param missedBranchCount:       Optional, number of missed branches. Default: ``None``.
		:param coveredBranchCount:      Optional, number of covered branches. Default: ``None``.
		:param parent:                  Optional, the source file the line belongs to; the line is added to its lines by
		                                :attr:`LineNumber`. Default: ``None``.
		:raises ValueError:             If parameter ``lineNumber`` is ``None``.
		:raises TypeError:              If parameter ``lineNumber`` isn't of type :class:`int`.
		:raises ValueError:             If parameter ``lineNumber`` is less than 1.
		:raises TypeError:              If parameter ``missedInstructionCount`` isn't of type :class:`int`.
		:raises ValueError:             If parameter ``missedInstructionCount`` is negative.
		:raises TypeError:              If parameter ``coveredInstructionCount`` isn't of type :class:`int`.
		:raises ValueError:             If parameter ``coveredInstructionCount`` is negative.
		:raises TypeError:              If parameter ``missedBranchCount`` isn't of type :class:`int`.
		:raises ValueError:             If parameter ``missedBranchCount`` is negative.
		:raises TypeError:              If parameter ``coveredBranchCount`` isn't of type :class:`int`.
		:raises ValueError:             If parameter ``coveredBranchCount`` is negative.
		:raises TypeError:              If parameter ``parent`` isn't of type :class:`SourceFile`.
		"""
		if lineNumber is None:
			raise ValueError(f"Parameter 'lineNumber' is None.")
		elif not isinstance(lineNumber, int):
			ex = TypeError(f"Parameter 'lineNumber' is not of type 'int'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(lineNumber)}'.")
			raise ex
		elif lineNumber < 1:
			ex = ValueError(f"Parameter 'lineNumber' is less than 1.")
			ex.add_note(f"Got value '{lineNumber}'.")
			raise ex

		for name, count in (
			("missedInstructionCount",  missedInstructionCount),
			("coveredInstructionCount", coveredInstructionCount),
			("missedBranchCount",       missedBranchCount),
			("coveredBranchCount",      coveredBranchCount)
		):
			if count is not None:
				if not isinstance(count, int):
					ex = TypeError(f"Parameter '{name}' is not of type 'int'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(count)}'.")
					raise ex
				elif count < 0:
					ex = ValueError(f"Parameter '{name}' is negative.")
					ex.add_note(f"Got value '{count}'.")
					raise ex

		if parent is not None and not isinstance(parent, SourceFile):
			ex = TypeError(f"Parameter 'parent' is not of type 'SourceFile'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =                  parent
		self._lineNumber =              lineNumber
		self._missedInstructionCount =  missedInstructionCount
		self._coveredInstructionCount = coveredInstructionCount
		self._missedBranchCount =       missedBranchCount
		self._coveredBranchCount =      coveredBranchCount

		if parent is not None:
			parent._lines[self._lineNumber] = self

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[SourceFile] = None) -> Self:
		"""
		Parse a line from its ``<line>`` element.

		:param element: The ``<line>`` element.
		:param parent:  Optional, the source file the line belongs to. Default: ``None``.
		:returns:       The line.
		"""
		attributes = element.attrib
		return cls(
			int(attributes["nr"]),
			int(attributes["mi"]) if "mi" in attributes else None,
			int(attributes["ci"]) if "ci" in attributes else None,
			int(attributes["mb"]) if "mb" in attributes else None,
			int(attributes["cb"]) if "cb" in attributes else None,
			parent=parent
		)

	@readonly
	def Parent(self) -> Nullable[SourceFile]:
		"""
		Read-only property to access the source file the line belongs to (:attr:`_parent`).

		:returns: The source file; ``None`` if the line belongs to no source file.
		"""
		return self._parent

	@readonly
	def LineNumber(self) -> int:
		"""
		Read-only property to access the line number (:attr:`_lineNumber`).

		:returns: The line number, counted from 1.
		"""
		return self._lineNumber

	@readonly
	def MissedInstructionCount(self) -> Nullable[int]:
		"""
		Read-only property to access the number of missed instructions (:attr:`_missedInstructionCount`).

		:returns: The number, or ``None`` if the report doesn't say.
		"""
		return self._missedInstructionCount

	@readonly
	def CoveredInstructionCount(self) -> Nullable[int]:
		"""
		Read-only property to access the number of covered instructions (:attr:`_coveredInstructionCount`).

		:returns: The number, or ``None`` if the report doesn't say.
		"""
		return self._coveredInstructionCount

	@readonly
	def MissedBranchCount(self) -> Nullable[int]:
		"""
		Read-only property to access the number of missed branches (:attr:`_missedBranchCount`).

		:returns: The number, or ``None`` if the report doesn't say.
		"""
		return self._missedBranchCount

	@readonly
	def CoveredBranchCount(self) -> Nullable[int]:
		"""
		Read-only property to access the number of covered branches (:attr:`_coveredBranchCount`).

		:returns: The number, or ``None`` if the report doesn't say.
		"""
		return self._coveredBranchCount


@export
class SourceFile(Base, CountersMixin):
	"""
	A ``<sourcefile>`` of a package: its lines and its counters.
	"""

	_parent: Nullable[Package]  #: The package the source file belongs to.
	_lines:  dict[int, Line]    #: The lines with instructions, by number.

	def __init__(self, name: str, *, parent: Nullable[Package] = None) -> None:
		"""
		Initialize the source file, and add it to the source files of its package.

		Its lines and counters are added by creating them with this source file as their parent.

		:param name:        Name of the source file, without the package's directory, e.g. ``MyClass.java``.
		:param parent:      Optional, the package the source file belongs to; the source file is added to its source
		                    files by :attr:`Name`. Default: ``None``.
		:raises ValueError: If parameter ``name`` is ``None``.
		:raises TypeError:  If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError: If parameter ``name`` is empty.
		:raises TypeError:  If parameter ``parent`` isn't of type :class:`~pyEDAA.Reports.CodeCoverage.JaCoCo.Package`.
		"""
		super().__init__(name)
		CountersMixin.__init__(self)

		if name == "":
			raise ValueError(f"Parameter 'name' is empty.")

		if parent is not None and not isinstance(parent, Package):
			ex = TypeError(f"Parameter 'parent' is not of type 'Package'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent = parent
		self._lines =  {}

		if parent is not None:
			parent._sourceFiles[self._name] = self

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[Package] = None) -> Self:
		"""
		Parse a source file, its lines and counters from its ``<sourcefile>`` element.

		:param element:            The ``<sourcefile>`` element.
		:param parent:             Optional, the package the source file belongs to. Default: ``None``.
		:returns:                  The source file.
		:raises CodeCoverageError: If the source file states a line twice.
		:raises CodeCoverageError: If the source file states a counter twice.
		"""
		sourceFile = cls(element.attrib["name"], parent=parent)

		for lineElement in element.iterfind("line"):
			if (lineNumber := int(lineElement.attrib["nr"])) in sourceFile._lines:
				raise CodeCoverageError(f"JaCoCo source file '{sourceFile._name}' states line {lineNumber} twice.")

			Line.Parse(lineElement, parent=sourceFile)

		for counterElement in element.iterfind("counter"):
			if (counterType := CounterType(counterElement.attrib["type"])) in sourceFile._counters:
				raise CodeCoverageError(f"JaCoCo source file '{sourceFile._name}' states counter '{counterType}' twice.")

			Counter.Parse(counterElement, parent=sourceFile)

		return sourceFile

	@readonly
	def Parent(self) -> Nullable[Package]:
		"""
		Read-only property to access the package the source file belongs to (:attr:`_parent`).

		:returns: The package; ``None`` if the source file belongs to no package.
		"""
		return self._parent

	@readonly
	def Lines(self) -> dict[int, Line]:
		"""
		Read-only property to access the lines with instructions (:attr:`_lines`).

		:returns: The lines, by number.
		"""
		return self._lines


@export
class Package(Base, CountersMixin, Generic[ParentType]):
	"""
	A ``<package>`` of the report or of a group: its classes and source files, and its counters.
	"""

	_parent:      Nullable[ParentType]   #: The report or group the package belongs to.
	_classes:     dict[str, Class]       #: The classes, by name.
	_sourceFiles: dict[str, SourceFile]  #: The source files, by name.

	def __init__(self, name: str, *, parent: Nullable[ParentType] = None) -> None:
		"""
		Initialize the package, and add it to the packages of its report or group.

		Its classes, source files and counters are added by creating them with this package as their parent.

		:param name:        Name of the package in VM notation, e.g. ``my/pack``; empty for the default package.
		:param parent:      Optional, the report or group the package belongs to; the package is added to its packages
		                    by :attr:`Name`. Default: ``None``.
		:raises ValueError: If parameter ``name`` is ``None``.
		:raises TypeError:  If parameter ``name`` isn't of type :class:`str`.
		:raises TypeError:  If parameter ``parent`` isn't of type :class:`Report` or :class:`Group`.
		"""
		super().__init__(name)
		CountersMixin.__init__(self)

		if parent is not None and not isinstance(parent, (Report, Group)):
			ex = TypeError(f"Parameter 'parent' is not of type 'Report' or 'Group'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =      parent
		self._classes =     {}
		self._sourceFiles = {}

		if parent is not None:
			parent._packages[self._name] = self

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[ParentType] = None) -> Self:
		"""
		Parse a package, its classes, source files and counters from its ``<package>`` element.

		:param element:            The ``<package>`` element.
		:param parent:             Optional, the report or group the package belongs to. Default: ``None``.
		:returns:                  The package.
		:raises CodeCoverageError: If the package states a class or source file twice.
		:raises CodeCoverageError: If the package states a counter twice.
		"""
		package = cls(element.attrib["name"], parent=parent)

		for classElement in element.iterfind("class"):
			if (name := classElement.attrib["name"]) in package._classes:
				raise CodeCoverageError(f"JaCoCo package '{package._name}' states class '{name}' twice.")

			Class.Parse(classElement, parent=package)

		for sourceFileElement in element.iterfind("sourcefile"):
			if (name := sourceFileElement.attrib["name"]) in package._sourceFiles:
				raise CodeCoverageError(f"JaCoCo package '{package._name}' states source file '{name}' twice.")

			SourceFile.Parse(sourceFileElement, parent=package)

		for counterElement in element.iterfind("counter"):
			if (counterType := CounterType(counterElement.attrib["type"])) in package._counters:
				raise CodeCoverageError(f"JaCoCo package '{package._name}' states counter '{counterType}' twice.")

			Counter.Parse(counterElement, parent=package)

		return package

	@readonly
	def Parent(self) -> Nullable[ParentType]:
		"""
		Read-only property to access the report or group the package belongs to (:attr:`_parent`).

		:returns: The :class:`Report` or :class:`Group`; ``None`` if the package belongs to none.
		"""
		return self._parent

	@readonly
	def Classes(self) -> dict[str, Class]:
		"""
		Read-only property to access the classes (:attr:`_classes`).

		A class is keyed by its name, e.g. ``my/pack/MyClass``, a nested class by its binary name, e.g.
		``my/pack/MyClass$Inner``.

		:returns: The classes, by name.
		"""
		return self._classes

	@readonly
	def SourceFiles(self) -> dict[str, SourceFile]:
		"""
		Read-only property to access the source files (:attr:`_sourceFiles`).

		A source file is keyed by its name, e.g. ``MyClass.java``.

		:returns: The source files, by name.
		"""
		return self._sourceFiles


@export
class Group(Base, CountersMixin, Generic[ParentType]):
	"""
	A ``<group>`` of the report or of a group: its groups or packages, and its counters.

	JaCoCo groups packages, e.g. by module, if Maven's goal ``report-aggregate`` or Ant's task ``report`` asks for it.
	"""

	_parent:   Nullable[ParentType]       #: The report or group the group belongs to.
	_groups:   dict[str, Group[Group]]    #: The groups, by name.
	_packages: dict[str, Package[Group]]  #: The packages, by name.

	def __init__(self, name: str, *, parent: Nullable[ParentType] = None) -> None:
		"""
		Initialize the group, and add it to the groups of its report or group.

		Its groups, packages and counters are added by creating them with this group as their parent.

		:param name:        Name of the group, e.g. of a module.
		:param parent:      Optional, the report or group the group belongs to; the group is added to its groups by
		                    :attr:`Name`. Default: ``None``.
		:raises ValueError: If parameter ``name`` is ``None``.
		:raises TypeError:  If parameter ``name`` isn't of type :class:`str`.
		:raises ValueError: If parameter ``name`` is empty.
		:raises TypeError:  If parameter ``parent`` isn't of type :class:`Report` or :class:`Group`.
		"""
		super().__init__(name)
		CountersMixin.__init__(self)

		if name == "":
			raise ValueError(f"Parameter 'name' is empty.")

		if parent is not None and not isinstance(parent, (Report, Group)):
			ex = TypeError(f"Parameter 'parent' is not of type 'Report' or 'Group'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parent)}'.")
			raise ex

		self._parent =   parent
		self._groups =   {}
		self._packages = {}

		if parent is not None:
			parent._groups[self._name] = self

	@classmethod
	def Parse(cls, element: _Element, *, parent: Nullable[ParentType] = None) -> Self:
		"""
		Parse a group, its groups, packages and counters from its ``<group>`` element.

		:param element:            The ``<group>`` element.
		:param parent:             Optional, the report or group the group belongs to. Default: ``None``.
		:returns:                  The group.
		:raises CodeCoverageError: If the group states a group or package twice.
		:raises CodeCoverageError: If the group states a counter twice.
		"""
		group = cls(element.attrib["name"], parent=parent)

		for groupElement in element.iterfind("group"):
			if (name := groupElement.attrib["name"]) in group._groups:
				raise CodeCoverageError(f"JaCoCo group '{group._name}' states group '{name}' twice.")

			Group.Parse(groupElement, parent=group)

		for packageElement in element.iterfind("package"):
			if (name := packageElement.attrib["name"]) in group._packages:
				raise CodeCoverageError(f"JaCoCo group '{group._name}' states package '{name}' twice.")

			Package.Parse(packageElement, parent=group)

		for counterElement in element.iterfind("counter"):
			if (counterType := CounterType(counterElement.attrib["type"])) in group._counters:
				raise CodeCoverageError(f"JaCoCo group '{group._name}' states counter '{counterType}' twice.")

			Counter.Parse(counterElement, parent=group)

		return group

	@readonly
	def Parent(self) -> Nullable[ParentType]:
		"""
		Read-only property to access the report or group the group belongs to (:attr:`_parent`).

		:returns: The :class:`Report` or :class:`Group`; ``None`` if the group belongs to none.
		"""
		return self._parent

	@readonly
	def Groups(self) -> dict[str, Group[Group]]:
		"""
		Read-only property to access the groups (:attr:`_groups`).

		:returns: The groups, by name.
		"""
		return self._groups

	@readonly
	def Packages(self) -> dict[str, Package[Group]]:
		"""
		Read-only property to access the packages (:attr:`_packages`).

		:returns: The packages, by name.
		"""
		return self._packages


@export
class Report(CountersMixin, mixin=True):
	"""
	The root element ``<report>``: its name, the sessions, the groups or packages, and the counters.

	The root of the format's model: a session, a group, a package or a counter names it as its parent.
	"""

	_name:          Nullable[str]               #: Name of the report, e.g. of the project measured.
	_formatVersion: Nullable[_FormatVersion]    #: Version of the report format.
	_sessionInfos:  list[SessionInfo]           #: The sessions, which contributed execution data.
	_groups:        dict[str, Group[Report]]    #: The groups, by name.
	_packages:      dict[str, Package[Report]]  #: The packages, by name.

	def __init__(self) -> None:
		"""
		Initialize an empty report.
		"""
		CountersMixin.__init__(self)

		self._name =          None
		self._formatVersion = None
		self._sessionInfos =  []
		self._groups =        {}
		self._packages =      {}

	@readonly
	def Name(self) -> Nullable[str]:
		"""
		Read-only property to access the name of the report (:attr:`_name`).

		The name is chosen by the tool writing the report, e.g. the name of the project measured.

		:returns: The name; ``None`` before the report was converted.
		"""
		return self._name

	@readonly
	def FormatVersion(self) -> Nullable[FormatVersion]:
		"""
		Read-only property to access the version of the report format (:attr:`_formatVersion`).

		:returns: The format version; ``None`` before the report was analyzed.
		"""
		return self._formatVersion

	@readonly
	def SessionInfos(self) -> list[SessionInfo]:
		"""
		Read-only property to access the sessions, which contributed execution data (:attr:`_sessionInfos`).

		:returns: The sessions, in the order the report lists them.
		"""
		return self._sessionInfos

	@readonly
	def Groups(self) -> dict[str, Group[Report]]:
		"""
		Read-only property to access the groups (:attr:`_groups`).

		:returns: The groups, by name; empty, if the report has packages.
		"""
		return self._groups

	@readonly
	def Packages(self) -> dict[str, Package[Report]]:
		"""
		Read-only property to access the packages (:attr:`_packages`).

		:returns: The packages, by name; empty, if the report has groups.
		"""
		return self._packages


@export
class Document(cc_Document, Report):
	"""
	A JaCoCo XML code coverage report: read into the format's model, and converted to the common model.
	"""

	_xmlDocument: Nullable[_ElementTree]  #: The parsed and validated XML document, after :meth:`Analyze`.

	def __init__(self, xmlReportFile: Path, analyzeAndConvert: bool = False) -> None:
		"""
		Initialize the report, and optionally read it.

		:param xmlReportFile:     Path to the JaCoCo XML file.
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
		Parse the XML file, read the format version from the DTD's public identifier, and validate the file against the
		XML schema of that version (:data:`SCHEMAS`).

		:raises CodeCoverageError: If the file doesn't exist.
		:raises CodeCoverageError: If the file can't be read.
		:raises CodeCoverageError: If the file isn't well-formed XML.
		:raises CodeCoverageError: If the root element isn't ``<report>``.
		:raises CodeCoverageError: If the file states no public identifier of a supported format version.
		:raises CodeCoverageError: If the XML schema can't be located or parsed.
		:raises CodeCoverageError: If the file isn't valid according to the XML schema.
		"""
		if not self._path.exists():
			raise CodeCoverageError(f"JaCoCo report file '{self._path}' does not exist.") \
				from FileNotFoundError(f"File '{self._path}' not found.")

		with Stopwatch() as sw:
			try:
				content = self._path.read_bytes()
			except OSError as ex:
				raise CodeCoverageError(f"Couldn't read JaCoCo report file '{self._path}'.") from ex

			try:
				xmlDocument = parse(BytesIO(content), XMLParser(ns_clean=True), base_url=str(self._path))
			except XMLSyntaxError as ex:
				raise CodeCoverageError(f"XML syntax error in JaCoCo report file '{self._path}'.") from ex

			rootElement: _Element = xmlDocument.getroot()
			if rootElement.tag != "report":
				ex = CodeCoverageError(f"Root element of '{self._path}' is not '<report>'.")
				ex.add_note(f"Got root element '<{rootElement.tag}>'.")
				raise ex

			publicID = xmlDocument.docinfo.public_id
			match = PUBLIC_IDENTIFIER.fullmatch(publicID) if publicID is not None else None
			if match is None or match[1] not in [member.value for member in FormatVersion]:
				ex = CodeCoverageError(f"JaCoCo report file '{self._path}' states an unsupported format version.")
				ex.add_note(f"Got public identifier '{publicID}'." if publicID is not None else "Got no public identifier.")
				ex.add_note(f"Supported format versions: {', '.join(member.value for member in FormatVersion)}.")
				raise ex

			formatVersion = FormatVersion(match[1])
			schemaFile = SCHEMAS[formatVersion]
			try:
				schemaResourceFile = getResourceFile(Resources, schemaFile)
			except ToolingException as ex:
				raise CodeCoverageError(f"Couldn't locate XML Schema '{schemaFile}' in package resources.") from ex

			try:
				xmlSchema = XMLSchema(parse(schemaResourceFile, XMLParser(ns_clean=True)))
			except (XMLSyntaxError, XMLSchemaParseError) as ex:
				raise CodeCoverageError(f"Error while parsing XML Schema '{schemaFile}'.") from ex

			if not xmlSchema.validate(xmlDocument):
				ex = CodeCoverageError(f"Validation error for '{self._path}' using XSD schema '{schemaFile}'.")
				for logEntry in xmlSchema.error_log:
					ex.add_note(str(logEntry))
				raise ex

			self._xmlDocument =   xmlDocument
			self._formatVersion = formatVersion

		self._analysisDuration = sw.Duration

	def Convert(self) -> None:
		"""
		Convert the parsed and validated XML document to the format's model.

		:raises CodeCoverageError: If the XML file was not analyzed before. |br|
		                           Call 'Document.Analyze()' or create the document using
		                           'Document(path, analyzeAndConvert=True)'.
		:raises CodeCoverageError: If an element states a child element twice.
		"""
		if self._xmlDocument is None:
			ex = CodeCoverageError(f"JaCoCo report file '{self._path}' needs to be read and analyzed by an XML parser.")
			ex.add_note(f"Call 'Document.Analyze()' or create the document using 'Document(path, analyzeAndConvert=True)'.")
			raise ex

		with Stopwatch() as sw:
			root: _Element = self._xmlDocument.getroot()
			self._name = root.attrib["name"]

			for sessionInfoElement in root.iterfind("sessioninfo"):
				SessionInfo.Parse(sessionInfoElement, parent=self)

			for groupElement in root.iterfind("group"):
				if (name := groupElement.attrib["name"]) in self._groups:
					raise CodeCoverageError(f"JaCoCo report '{self._name}' states group '{name}' twice.")

				Group.Parse(groupElement, parent=self)

			for packageElement in root.iterfind("package"):
				if (name := packageElement.attrib["name"]) in self._packages:
					raise CodeCoverageError(f"JaCoCo report '{self._name}' states package '{name}' twice.")

				Package.Parse(packageElement, parent=self)

			for counterElement in root.iterfind("counter"):
				if (counterType := CounterType(counterElement.attrib["type"])) in self._counters:
					raise CodeCoverageError(f"JaCoCo report '{self._name}' states counter '{counterType}' twice.")

				Counter.Parse(counterElement, parent=self)

		self._conversionDuration = sw.Duration

	def ToCoverageSummary(self) -> CoverageSummary:
		"""
		Convert the format's model to the common model, and aggregate it.

		The packages of all groups are converted. A source file's path is its package's name and its name. A line's
		missed and covered branches become as many branches. A method spans its first line and the next lines of its file,
		as many as its ``LINE`` counter counts; a class spans its methods.

		:returns:                  The report's root of the common model, named after the report - or, if the report's
		                           name is empty, after the report file.
		:raises CodeCoverageError: If two packages of the same name state a source file of the same name.
		:raises CodeCoverageError: If a file's path runs through another file.
		"""
		def iteratePackages(element: Report | Group) -> Generator[Package, None, None]:
			"""
			Nested function for recursion.

			:param element: The report or a group.
			:returns:       A generator of the packages of the element and of its groups.
			"""
			for group in element._groups.values():
				yield from iteratePackages(group)

			yield from element._packages.values()

		def getStatus(element: CountersMixin, counterType: CounterType) -> LineCoverageStatus:
			"""
			Nested function returning the coverage state of a class or method by its ``CLASS`` or ``METHOD`` counter.

			:param element:     The class or method.
			:param counterType: The counter's kind.
			:returns:           Covered, if the counter counts a covered item, otherwise uncovered; unknown, if the element
			                    has no such counter.
			"""
			if (counter := element._counters.get(counterType)) is None:
				return LineCoverageStatus.Unknown

			return LineCoverageStatus.Covered if counter._coveredCount > 0 else LineCoverageStatus.Uncovered

		summary = CoverageSummary(self._name if self._name is not None and self._name != "" else self._path.stem)

		for package in iteratePackages(self):
			for sourceFile in package._sourceFiles.values():
				file = summary.GetOrAddFile(Path(package._name) / sourceFile._name)
				for number in sorted(sourceFile._lines):
					line = sourceFile._lines[number]
					missedBranchCount =  line._missedBranchCount if line._missedBranchCount is not None else 0
					coveredBranchCount = line._coveredBranchCount if line._coveredBranchCount is not None else 0
					branches =           [cc_Branch(LineCoverageStatus.Covered) for _ in range(coveredBranchCount)]
					branches.extend(cc_Branch(LineCoverageStatus.Uncovered) for _ in range(missedBranchCount))
					if line._coveredInstructionCount is None:
						status = LineCoverageStatus.Unknown
					elif line._coveredInstructionCount == 0:
						status = LineCoverageStatus.Uncovered
					elif missedBranchCount > 0:
						status = LineCoverageStatus.PartiallyCovered
					else:
						status = LineCoverageStatus.Covered
					cc_Line(number, status, None, branches, parent=file)

		for package in iteratePackages(self):
			parent: cc_Unit | CoverageSummary = summary
			for part in (part for part in package._name.split("/") if part != ""):
				parent = parent._units[part] if part in parent._units else cc_Package(part, parent=parent)

			for klass in package._classes.values():
				file = None
				if klass._sourceFileName is not None and klass._sourceFileName in package._sourceFiles:
					file = summary.GetOrAddFile(Path(package._name) / klass._sourceFileName)

				# per method with a first line in the file: its first and last line
				spans: dict[str, tuple[cc_Line, cc_Line]] = {}
				for key, method in klass._methods.items():
					if (
						file is None or method._lineNumber is None or method._lineNumber > file._lastLineNumber or
						(startLine := file._lines[method._lineNumber]) is None
					):
						continue

					counter =    method._counters.get(CounterType.Line)
					lineCount =  counter._missedCount + counter._coveredCount if counter is not None else 1
					lines =      list(islice(file.IterateLines(startLine), max(lineCount, 1)))
					spans[key] = (startLine, lines[-1])

				if (classUnit := parent._units.get(name := klass._name.rpartition("/")[2])) is None:
					classUnit = cc_Class(
						name,
						file=file,
						startLine=min((span[0] for span in spans.values()), key=lambda line: line._lineNumber, default=None),
						endLine=max((span[1] for span in spans.values()), key=lambda line: line._lineNumber, default=None),
						status=getStatus(klass, CounterType.Class),
						parent=parent
					)

				for key, method in klass._methods.items():
					if key not in classUnit._units:
						cc_Method(
							key,
							file=file,
							startLine=spans[key][0] if key in spans else None,
							endLine=spans[key][1] if key in spans else None,
							status=getStatus(method, CounterType.Method),
							parent=classUnit
						)

		summary.Aggregate()
		return summary
