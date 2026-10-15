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
Reader of Python source code for the documentation coverage model.

:class:`Analyzer` reads a package's directory - every ``*.py`` file below it - into a
:class:`~pyEDAA.Reports.DocumentationCoverage.Files.CoverageSummary`. Each file is read once
(:class:`~pyEDAA.Reports.DocumentationCoverage.Python.Source.SourceFile`): in its declared encoding, into its syntax
tree and its tokens, which hold the comments.

.. rubric:: Items

* A package - a directory - and a module - a file - are items; a package's doc-string is its ``__init__.py``'s. A
  directory without ``__init__.py`` is a namespace package, which has nothing to document.
* Classes, functions, methods, constructors (``__init__``) and properties are items, wherever they are declared, also in
  a function's body.
* A class' fields are the names its body assigns or annotates - class variables and enumeration members too -, and its
  ``type`` statements, also inside an ``if`` or ``try`` statement. A name assigned several times is one item.
* A module's variables are the same statements in the module's body, e.g. constants, type aliases and type variables.
* Imports, augmented assignments, assignments to an attribute (``self._x = ...``), names assigned in a function's body,
  and the fields of a class declared in a function's body are no items.

.. rubric:: Documentation

* A module, class or callable is documented by a non-empty doc-string. A comment of docstr_coverage directly above its
  declaration excuses a missing doc-string: ``# docstr-coverage: inherited`` and
  ``# docstr-coverage: excused `reason```.
* A field or variable is documented, where Sphinx' autodoc finds its documentation: a ``#:`` comment behind the
  statement - behind a closing bracket, not behind an opening one -, ``#:`` comment lines directly above it, or a string
  literal directly after it. The documentation must not be empty.

.. rubric:: Ignored and excluded items

* Ignored: a property's setter and deleter, an ``@overload`` stub, a field or variable named with a leading and a
  trailing underscore (``__all__``, ``_value_``), and - if :attr:`Options.SkipPrivate` - every private name.
* Excluded: an item, whose qualified name matches one of :attr:`Options.ExcludePatterns`, and the items it contains;
  the fields or variables, if not counted (:attr:`Options.CountFields`, :attr:`Options.CountVariables`); a module, which
  can't be read or parsed (:exc:`~pyEDAA.Reports.DocumentationCoverage.SourceFileWarning`).
"""
from __future__                                         import annotations

from ast                                                import AnnAssign, Assign, AST, AsyncFunctionDef, Attribute
from ast                                                import Call, ClassDef, Constant, Expr, FunctionDef, If, List
from ast                                                import Name, Starred, Subscript, Try, Tuple, expr, stmt
from pathlib                                            import Path
from re                                                 import Pattern, compile as re_compile
from re                                                 import error as RegularExpressionError
from sys                                                import version_info
from tokenize                                           import TokenError
from typing                                             import Iterable, Optional as Nullable

from pyTooling.Common                                   import getFullyQualifiedName
from pyTooling.Decorators                               import export, readonly
from pyTooling.MetaClasses                              import ExtendedType
from pyTooling.Warning                                  import WarningCollector

from pyEDAA.Reports.DocumentationCoverage               import CoverageState, DocCoverageError, ItemKind
from pyEDAA.Reports.DocumentationCoverage               import SourceFileWarning
from pyEDAA.Reports.DocumentationCoverage.Files         import CoverageSummary
from pyEDAA.Reports.DocumentationCoverage.Items         import Item
from pyEDAA.Reports.DocumentationCoverage.Python.Source import SourceFile

if version_info >= (3, 12):  # pragma: no cover
	from ast                                              import TypeAlias


@export
class Options(metaclass=ExtendedType, slots=True):
	"""
	The options of an analysis: which items are counted, and which are ignored or excluded.
	"""

	_countFields:     bool                #: Whether the fields of a class are counted.
	_countVariables:  bool                #: Whether the variables of a module are counted.
	_skipPrivate:     bool                #: Whether items of a private name are ignored.
	_excludePatterns: list[Pattern[str]]  #: The patterns of qualified names, whose items are excluded.

	def __init__(
		self,
		*,
		countFields: bool = True,
		countVariables: bool = True,
		skipPrivate: bool = False,
		excludePatterns: Nullable[Iterable[str]] = None
	) -> None:
		"""
		Initializes the options of an analysis.

		:param countFields:     Optional, whether a class' fields are counted, or excluded. Default: ``True``.
		:param countVariables:  Optional, whether a module's variables are counted, or excluded. Default: ``True``.
		:param skipPrivate:     Optional, whether items of a private name - a leading underscore, but not a dunder name -
		                        are ignored. Default: ``False``.
		:param excludePatterns: Optional, regular expressions matching the whole qualified name of an item to exclude,
		                        e.g. ``myPackage\\.CLI(\\..*)?``. Default: none.
		:raises ValueError:     If parameter ``countFields`` is ``None``.
		:raises TypeError:      If parameter ``countFields`` isn't of type :class:`bool`.
		:raises ValueError:     If parameter ``countVariables`` is ``None``.
		:raises TypeError:      If parameter ``countVariables`` isn't of type :class:`bool`.
		:raises ValueError:     If parameter ``skipPrivate`` is ``None``.
		:raises TypeError:      If parameter ``skipPrivate`` isn't of type :class:`bool`.
		:raises TypeError:      If parameter ``excludePatterns`` isn't iterable.
		:raises TypeError:      If parameter ``excludePatterns`` contains an element not of type :class:`str`.
		:raises ValueError:     If parameter ``excludePatterns`` contains an invalid regular expression.
		"""
		for parameterName, value in (
			("countFields",    countFields),
			("countVariables", countVariables),
			("skipPrivate",    skipPrivate)
		):
			if value is None:
				raise ValueError(f"Parameter '{parameterName}' is None.")
			elif not isinstance(value, bool):
				ex = TypeError(f"Parameter '{parameterName}' is not of type 'bool'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
				raise ex

		self._countFields =     countFields
		self._countVariables =  countVariables
		self._skipPrivate =     skipPrivate
		self._excludePatterns = []

		if excludePatterns is not None:
			if not isinstance(excludePatterns, Iterable):
				ex = TypeError(f"Parameter 'excludePatterns' is not iterable.")
				ex.add_note(f"Got type '{getFullyQualifiedName(excludePatterns)}'.")
				raise ex

			for excludePattern in excludePatterns:
				if not isinstance(excludePattern, str):
					ex = TypeError(f"Parameter 'excludePatterns' contains an element not of type 'str'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(excludePattern)}'.")
					raise ex

				try:
					self._excludePatterns.append(re_compile(excludePattern))
				except RegularExpressionError as cause:
					ex = ValueError(f"Parameter 'excludePatterns' contains an invalid regular expression.")
					ex.add_note(f"Got pattern '{excludePattern}'.")
					raise ex from cause

	@readonly
	def CountFields(self) -> bool:
		"""
		Read-only property to access whether the fields of a class are counted (:attr:`_countFields`).

		:returns: ``True``, if fields are counted; otherwise they are excluded.
		"""
		return self._countFields

	@readonly
	def CountVariables(self) -> bool:
		"""
		Read-only property to access whether the variables of a module are counted (:attr:`_countVariables`).

		:returns: ``True``, if variables are counted; otherwise they are excluded.
		"""
		return self._countVariables

	@readonly
	def SkipPrivate(self) -> bool:
		"""
		Read-only property to access whether items of a private name are ignored (:attr:`_skipPrivate`).

		:returns: ``True``, if private items are ignored.
		"""
		return self._skipPrivate

	@readonly
	def ExcludePatterns(self) -> list[Pattern[str]]:
		"""
		Read-only property to access the patterns of qualified names, whose items are excluded (:attr:`_excludePatterns`).

		:returns: The compiled regular expressions.
		"""
		return self._excludePatterns


@export
class Analyzer(metaclass=ExtendedType, slots=True):
	"""
	Reads the documentation coverage of a Python package from its source files.

	A package's or module's lines are its file's, so their items name no lines.

	.. rubric:: Example

	.. code-block:: Python

	   from pathlib import Path
	   from pyEDAA.Reports.DocumentationCoverage.Python import Analyzer, Options
	   from pyTooling.Warning import WarningCollector

	   with WarningCollector() as warnings:
	     summary = Analyzer("myPackage", Path("src/myPackage"), options=Options(skipPrivate=True)).Analyze()

	   print(f"{summary.Counters.Covered}/{summary.Counters.Expected}: {summary.Counters.Coverage:.1%}")
	"""

	_packageName: str      #: Name of the package.
	_directory:   Path     #: The package's directory.
	_options:     Options  #: The options of the analysis.

	def __init__(self, packageName: str, directory: Path, *, options: Nullable[Options] = None) -> None:
		"""
		Initializes the analysis of a package.

		:param packageName: Name of the package, which is the name of the top-level item, e.g. ``myPackage``.
		:param directory:   The package's directory.
		:param options:     Optional, the options of the analysis. Default: the defaults of :class:`Options`.
		:raises ValueError: If parameter ``packageName`` is ``None``.
		:raises TypeError:  If parameter ``packageName`` isn't of type :class:`str`.
		:raises ValueError: If parameter ``packageName`` is empty.
		:raises ValueError: If parameter ``directory`` is ``None``.
		:raises TypeError:  If parameter ``directory`` isn't of type :class:`~pathlib.Path`.
		:raises TypeError:  If parameter ``options`` isn't of type :class:`Options`.
		"""
		if packageName is None:
			raise ValueError(f"Parameter 'packageName' is None.")
		elif not isinstance(packageName, str):
			ex = TypeError(f"Parameter 'packageName' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(packageName)}'.")
			raise ex
		elif packageName == "":
			raise ValueError(f"Parameter 'packageName' is empty.")

		if directory is None:
			raise ValueError(f"Parameter 'directory' is None.")
		elif not isinstance(directory, Path):
			ex = TypeError(f"Parameter 'directory' is not of type 'Path'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(directory)}'.")
			raise ex

		if options is not None and not isinstance(options, Options):
			ex = TypeError(f"Parameter 'options' is not of type 'Options'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(options)}'.")
			raise ex

		self._packageName = packageName
		self._directory =   directory
		self._options =     Options() if options is None else options

	@readonly
	def PackageName(self) -> str:
		"""
		Read-only property to access the name of the package (:attr:`_packageName`).

		:returns: The package's name.
		"""
		return self._packageName

	@readonly
	def Directory(self) -> Path:
		"""
		Read-only property to access the package's directory (:attr:`_directory`).

		:returns: The directory.
		"""
		return self._directory

	@readonly
	def Options(self) -> Options:
		"""
		Read-only property to access the options of the analysis (:attr:`_options`).

		:returns: The options.
		"""
		return self._options

	def Analyze(self) -> CoverageSummary:
		"""
		Read every Python source file of the package into a documentation coverage model, and aggregate it.

		A source file, which can't be read or parsed, is raised as a
		:exc:`~pyEDAA.Reports.DocumentationCoverage.SourceFileWarning` to the current
		:class:`~pyTooling.Warning.WarningCollector`; its module is excluded, and the analysis continues.

		:returns:                              The analysis' root; its top-level item is the package.
		:raises DocCoverageError:              If the package's directory doesn't exist.
		:raises UnhandledCriticalWarningError: If a source file can't be analyzed, and no warning collector collects the
		                                       warning. |br|
		                                       Add a with-statement using :class:`~pyTooling.Warning.WarningCollector`.
		"""
		if not self._directory.is_dir():
			raise DocCoverageError(f"Package directory '{self._directory}' doesn't exist.")

		summary = CoverageSummary(self._packageName)
		self._ReadPackage(self._directory, self._packageName, summary, summary)
		summary.Aggregate()

		return summary

	def _ReadPackage(self, directory: Path, name: str, parent: Item | CoverageSummary, summary: CoverageSummary) -> None:
		"""
		Read a package's ``__init__.py``, its modules, then its sub-packages, each sorted by name.

		:param directory: The package's directory.
		:param name:      The package's name.
		:param parent:    The package containing this one, or the analysis' root.
		:param summary:   The analysis' root.
		"""
		if (directory / "__init__.py").is_file():
			package = self._ReadModule(directory / "__init__.py", name, ItemKind.Package, parent, summary)
		else:
			package = Item(name, ItemKind.Package, self._State(CoverageState.Empty, name, parent), parent=parent)

		paths = sorted(directory.iterdir())
		for path in paths:
			if path.suffix == ".py" and path.name != "__init__.py" and path.is_file():
				self._ReadModule(path, path.stem, ItemKind.Module, package, summary)

		for path in paths:
			if path.is_dir() and next(path.rglob("*.py"), None) is not None:
				self._ReadPackage(path, path.name, package, summary)

	def _ReadModule(
		self,
		path: Path,
		name: str,
		kind: ItemKind,
		parent: Item | CoverageSummary,
		summary: CoverageSummary
	) -> Item:
		"""
		Read a module, or a package's ``__init__.py``, and the items declared in it.

		:param path:                           The source file.
		:param name:                           The module's or package's name.
		:param kind:                           :attr:`~pyEDAA.Reports.DocumentationCoverage.ItemKind.Module` or
		                                       :attr:`~pyEDAA.Reports.DocumentationCoverage.ItemKind.Package`.
		:param parent:                         The package containing the module, or the analysis' root.
		:param summary:                        The analysis' root.
		:returns:                              The module's or package's item.
		:raises UnhandledCriticalWarningError: If the source file can't be analyzed, and no warning collector collects the
		                                       warning.
		"""
		file = summary.GetOrAddFile(path.relative_to(self._directory))
		try:
			sourceFile = SourceFile.Read(path)
		except (OSError, SyntaxError, TokenError, ValueError) as ex:
			WarningCollector.Raise(SourceFileWarning(f"Source file '{file.Path.as_posix()}' can't be analyzed."), ex)
			return Item(name, kind, CoverageState.Excluded, file=file, parent=parent)

		if len(sourceFile.Tree.body) == 0:
			documentation = CoverageState.Empty
		else:
			documentation = sourceFile.DocumentationState(sourceFile.Tree)

		module = Item(name, kind, self._State(documentation, name, parent), file=file, parent=parent)
		self._ReadBody(sourceFile, sourceFile.Tree.body, module, False)

		return module

	def _ReadBody(self, sourceFile: SourceFile, body: list[stmt], parent: Item, inFunction: bool) -> None:
		"""
		Read the items declared in a module's, class' or function's body, in the order of their first declaration.

		Classes and functions are read wherever they are declared. Fields and variables are read from a module's or class'
		body and the ``if`` and ``try`` statements in it, but not from a function's body or a class declared in it. An
		assignment to a field in the class' ``__init__`` documents the field, if commented.

		:param sourceFile: The source file.
		:param body:       The statements of the body.
		:param parent:     The module's, class' or function's item.
		:param inFunction: Whether the body is a function's, or is declared in a function's body.
		"""
		order:      list[stmt | str] = []
		first:      dict[str, stmt] =  {}
		documented: dict[str, bool] =  {}
		previous:   Nullable[AST] =    None

		def visit(statements: list[stmt], readAttributes: bool, selfName: str) -> None:
			"""
			Nested function for recursion.

			The statement before an expression is tracked as Sphinx' autodoc does: a string after an assignment documents
			it; the condition of an ``if`` statement is the statement before its first block.

			:param statements:     The statements of a block.
			:param readAttributes: Whether the block's fields or variables are read.
			:param selfName:       Empty for a module's or class' body. In the body of a class' ``__init__``: the name of
			                       its first parameter, whose attributes document the class' fields.
			"""
			nonlocal previous
			for statement in statements:
				if isinstance(statement, (ClassDef, FunctionDef, AsyncFunctionDef)):
					if selfName == "":
						order.append(statement)
				elif readAttributes and len(names := self._TargetNames(statement, False, selfName)) > 0:
					hasComment = sourceFile.HasDocumentationComment(statement)
					for name in names:
						if selfName == "" and name not in first:
							order.append(name)
							first[name] =      statement
							documented[name] = False

						if name in documented:
							documented[name] = documented[name] or hasComment
				elif isinstance(statement, Expr) and isinstance(statement.value, Constant) and \
						isinstance(statement.value.value, str) and statement.value.value.strip() != "":
					for name in self._TargetNames(previous, True, selfName):
						if name in documented:
							documented[name] = True
				elif isinstance(statement, If):
					previous = statement.test
					visit(statement.body, readAttributes, selfName)
					visit(statement.orelse, readAttributes, selfName)
				elif isinstance(statement, Try):
					visit(statement.body, readAttributes, selfName)
					visit(statement.orelse, readAttributes, selfName)
					for handler in statement.handlers:
						visit(handler.body, False, selfName)

					visit(statement.finalbody, False, selfName)
				else:
					for block in ("body", "orelse", "finalbody"):
						visit(getattr(statement, block, []), False, selfName)

					for clause in (*getattr(statement, "handlers", []), *getattr(statement, "cases", [])):
						visit(clause.body, False, selfName)

				previous = statement

		isContainer = parent._kind in (ItemKind.Package, ItemKind.Module, ItemKind.Class, ItemKind.Enumeration)
		visit(body, isContainer and not inFunction, "")

		if parent._kind in (ItemKind.Class, ItemKind.Enumeration) and not inFunction:
			for entry in [entry for entry in order if isinstance(entry, (FunctionDef, AsyncFunctionDef))]:
				if entry.name == "__init__" and len(parameters := (*entry.args.posonlyargs, *entry.args.args)) > 0:
					previous = entry
					visit(entry.body, True, parameters[0].arg)

		for entry in order:
			if isinstance(entry, ClassDef):
				self._ReadClass(sourceFile, entry, parent, inFunction)
			elif isinstance(entry, (FunctionDef, AsyncFunctionDef)):
				self._ReadFunction(sourceFile, entry, parent)
			else:
				self._ReadAttribute(entry, first[entry], documented[entry], parent)

	def _ReadClass(self, sourceFile: SourceFile, statement: ClassDef, parent: Item, inFunction: bool) -> None:
		"""
		Read a class, and the items declared in its body.

		A class deriving from a class named ``...Enum`` or ``...Flag`` is an enumeration.

		:param sourceFile: The source file.
		:param statement:  The class' declaration.
		:param parent:     The item containing the class.
		:param inFunction: Whether the class is declared in a function's body.
		"""
		if any(self._BaseName(base).endswith(("Enum", "Flag")) for base in statement.bases):
			kind = ItemKind.Enumeration
		else:
			kind = ItemKind.Class

		item = Item(
			statement.name,
			kind,
			self._State(sourceFile.DocumentationState(statement), statement.name, parent),
			file=parent._file,
			startLine=self._FirstLine(statement),
			endLine=statement.end_lineno,
			parent=parent
		)
		self._ReadBody(sourceFile, statement.body, item, inFunction)

	def _ReadFunction(self, sourceFile: SourceFile, statement: FunctionDef | AsyncFunctionDef, parent: Item) -> None:
		"""
		Read a function, method, constructor or property, and the classes and functions declared in its body.

		A property's setter and deleter and an ``@overload`` stub are ignored.

		:param sourceFile: The source file.
		:param statement:  The function's declaration.
		:param parent:     The item containing the function.
		"""
		decorators = {self._BaseName(decorator) for decorator in statement.decorator_list}
		isAccessor = any(
			isinstance(decorator, Attribute) and decorator.attr in ("setter", "deleter")
			for decorator in statement.decorator_list
		)
		isMember = parent._kind in (ItemKind.Class, ItemKind.Enumeration)

		if isAccessor or (isMember and not decorators.isdisjoint(("property", "readonly", "cached_property", "getter"))):
			kind = ItemKind.Property
		elif isMember and statement.name == "__init__":
			kind = ItemKind.Constructor
		elif isMember:
			kind = ItemKind.Method
		else:
			kind = ItemKind.Function

		item = Item(
			statement.name,
			kind,
			self._State(
				sourceFile.DocumentationState(statement),
				statement.name,
				parent,
				ignored=isAccessor or "overload" in decorators
			),
			file=parent._file,
			startLine=self._FirstLine(statement),
			endLine=statement.end_lineno,
			parent=parent
		)
		self._ReadBody(sourceFile, statement.body, item, True)

	def _ReadAttribute(self, name: str, statement: stmt, documented: bool, parent: Item) -> None:
		"""
		Read a field of a class or a variable of a module, declared first by a statement.

		A variable assigned a call of ``TypeVar``, ``ParamSpec`` or ``TypeVarTuple`` is a type variable, of ``NewType`` a
		type; a variable annotated ``Final`` or named in upper case is a constant.

		:param name:       The field's or variable's name.
		:param statement:  The first statement assigning or annotating the name.
		:param documented: Whether a statement assigning or annotating the name documents it.
		:param parent:     The class' or module's item.
		"""
		isField = parent._kind in (ItemKind.Class, ItemKind.Enumeration)
		annotationName = self._BaseName(statement.annotation) if isinstance(statement, AnnAssign) else ""
		callName = self._BaseName(statement.value.func) if isinstance(getattr(statement, "value", None), Call) else ""

		if (version_info >= (3, 12) and isinstance(statement, TypeAlias)) or annotationName == "TypeAlias":
			kind = ItemKind.TypeAlias
		elif isField and parent._kind is ItemKind.Enumeration and isinstance(statement, Assign):
			kind = ItemKind.EnumerationMember
		elif isField:
			kind = ItemKind.Field
		elif callName in ("TypeVar", "ParamSpec", "TypeVarTuple"):
			kind = ItemKind.TypeVariable
		elif callName == "NewType":
			kind = ItemKind.Type
		elif annotationName == "Final" or name.isupper():
			kind = ItemKind.Constant
		else:
			kind = ItemKind.Variable

		Item(
			name,
			kind,
			self._State(
				CoverageState.Documented | CoverageState.Covered if documented else CoverageState.Undocumented,
				name,
				parent,
				ignored=name.startswith("_") and name.endswith("_"),
				excluded=not (self._options._countFields if isField else self._options._countVariables)
			),
			file=parent._file,
			startLine=statement.lineno,
			endLine=statement.end_lineno,
			parent=parent
		)

	def _State(
		self,
		documentation: CoverageState,
		name: str,
		parent: Item | CoverageSummary,
		*,
		ignored: bool = False,
		excluded: bool = False
	) -> CoverageState:
		"""
		Return an item's coverage state: how it is documented, and whether it is excluded or ignored.

		An item is excluded, if its qualified name, or the qualified name of an item containing it, matches an exclude
		pattern. It is ignored, if it is private and private items are skipped.

		:param documentation: How the item is documented.
		:param name:          The item's name.
		:param parent:        The item's parent.
		:param ignored:       Optional, whether the reader's rules ignore the item. Default: ``False``.
		:param excluded:      Optional, whether the options exclude the item. Default: ``False``.
		:returns:             The coverage state.
		"""
		names = f"{parent.QualifiedName}.{name}".split(".") if isinstance(parent, Item) else name.split(".")
		if excluded or any(
			pattern.fullmatch(".".join(names[:length])) is not None
			for pattern in self._options._excludePatterns for length in range(1, len(names) + 1)
		):
			return documentation | CoverageState.Excluded
		elif ignored or (self._options._skipPrivate and name.startswith("_") and
				not (name.startswith("__") and name.endswith("__"))):
			return documentation | CoverageState.Ignored

		return documentation

	@staticmethod
	def _TargetNames(statement: Nullable[AST], firstTargetOnly: bool, selfName: str) -> list[str]:
		"""
		Return the names an assignment, an annotation or a ``type`` statement declares, as Sphinx' autodoc reads them.

		In a module's or class' body, a name target declares a name. In the body of a class' ``__init__``, an attribute
		of its first parameter - ``self._x`` - declares the attribute's name.

		:param statement:       The statement; any other statement or ``None`` declares no name.
		:param firstTargetOnly: Whether only the first target of a chained assignment counts.
		:param selfName:        Empty for a module's or class' body; the name of ``__init__``'s first parameter in its body.
		:returns:               The names; none, if a target declares no name, e.g. a subscript.
		"""
		if isinstance(statement, Assign):
			targets = statement.targets[:1] if firstTargetOnly else statement.targets
		elif isinstance(statement, AnnAssign):
			targets = [statement.target]
		elif version_info >= (3, 12) and isinstance(statement, TypeAlias):
			targets = [statement.name]
		else:
			return []

		def targetName(target: expr) -> str:
			"""
			Nested function returning the name a target - neither a tuple nor a list - declares.

			:param target: The target.
			:returns:      The name; empty, if the target declares none.
			"""
			if isinstance(target, Name) and (selfName == "" or target.id == selfName):
				return target.id
			elif isinstance(target, Attribute) and selfName != "" and isinstance(target.value, Name) and \
					target.value.id == selfName:
				return target.attr

			return ""

		names: list[str] = []
		for target in targets:
			if isinstance(target, (Tuple, List)):
				for element in target.elts:
					if (name := targetName(element.value if isinstance(element, Starred) else element)) != "":
						names.append(name)
			elif (name := targetName(target)) != "":
				names.append(name)
			else:
				return []

		return names

	@staticmethod
	def _BaseName(expression: expr) -> str:
		"""
		Return the name an expression is based on: of a name, an attribute, a subscripted or a called expression.

		``typing.ClassVar[int]`` is based on ``ClassVar``, ``functools.cached_property`` on ``cached_property``.

		:param expression: The expression.
		:returns:          The name; empty, if the expression isn't based on a name.
		"""
		if isinstance(expression, Name):
			return expression.id
		elif isinstance(expression, Attribute):
			return expression.attr
		elif isinstance(expression, Subscript):
			return Analyzer._BaseName(expression.value)
		elif isinstance(expression, Call):
			return Analyzer._BaseName(expression.func)

		return ""

	@staticmethod
	def _FirstLine(statement: ClassDef | FunctionDef | AsyncFunctionDef) -> int:
		"""
		Return a declaration's first line: its first decorator's, if it has decorators.

		:param statement: The declaration.
		:returns:         The line number.
		"""
		return statement.decorator_list[0].lineno if len(statement.decorator_list) > 0 else statement.lineno
