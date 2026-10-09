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
The elements of JaCoCo's XML format below a package: its classes and their methods, its source files and their lines.
"""
from __future__                                  import annotations

from typing                                      import TYPE_CHECKING, Optional as Nullable, Self

from lxml.etree                                  import _Element
from pyTooling.Common                            import getFullyQualifiedName
from pyTooling.Decorators                        import export, readonly
from pyTooling.MetaClasses                       import ExtendedType

from pyEDAA.Reports.CodeCoverage                 import CodeCoverageError
from pyEDAA.Reports.CodeCoverage.JaCoCo.Elements import Base, Counter, CountersMixin, CounterType

if TYPE_CHECKING:
	from pyEDAA.Reports.CodeCoverage.JaCoCo        import Package


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

		from pyEDAA.Reports.CodeCoverage.JaCoCo import Package

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

		from pyEDAA.Reports.CodeCoverage.JaCoCo import Package

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
