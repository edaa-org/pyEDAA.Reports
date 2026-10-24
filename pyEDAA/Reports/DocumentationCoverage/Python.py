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
:class:`~pyEDAA.Reports.DocumentationCoverage.DocumentationReport`. Each file is read once (:class:`SourceFile`): in its
declared encoding, into its lines, its syntax tree and its tokens. The tokens hold the comments, which document a field
or variable for Sphinx' autodoc, or excuse a missing doc-string for docstr_coverage.

.. rubric:: Items

* A package - a directory - and a module - a file - are items; a package's doc-string is its ``__init__.py``'s. A
  directory without ``__init__.py`` is a namespace package, which has nothing to document.
* Classes, functions, methods, constructors (``__init__``), destructors (``__del__``) and properties are items, wherever
  they are declared, also in a function's body.
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
  trailing underscore (``__all__``, ``_value_``), and an item of a protected or private name, if :class:`CountedItems`
  doesn't select these names.
* Excluded: an item, whose qualified name matches one of :attr:`Analyzer.ExcludePatterns`, and the items it contains;
  the fields or variables, if :class:`CountedItems` doesn't select them; a module, which can't be read or parsed
  (:exc:`~pyEDAA.Reports.DocumentationCoverage.SourceFileWarning`).
"""
from __future__                           import annotations

from ast                                  import AnnAssign, Assign, AST, AsyncFunctionDef, Attribute, Call, ClassDef
from ast                                  import Constant, Expr, FunctionDef, If, List, Module, Name, Starred, Subscript
from ast                                  import Try, Tuple, expr, get_docstring, parse, stmt
from datetime                             import timedelta
from enum                                 import Flag
from io                                   import StringIO
from pathlib                              import Path
from re                                   import Pattern, compile as re_compile
from re                                   import error as RegularExpressionError
from sys                                  import version_info
from tokenize                             import COMMENT, ENDMARKER, NAME, NEWLINE, NL, NUMBER, OP, STRING
from tokenize                             import TokenError, TokenInfo, generate_tokens, open as tokenize_open
from typing                               import ClassVar, Iterable, Optional as Nullable

from pyTooling.Common                     import getFullyQualifiedName
from pyTooling.Decorators                 import export, readonly
from pyTooling.MetaClasses                import ExtendedType
from pyTooling.Stopwatch                  import Stopwatch
from pyTooling.Warning                    import WarningCollector

from pyEDAA.Reports.DocumentationCoverage import CoverageState, DocCoverageError, DocumentationReport, Item, ItemKind
from pyEDAA.Reports.DocumentationCoverage import SourceFileWarning

if version_info >= (3, 12):  # pragma: no cover
	from ast                                import TypeAlias


# A class with a property named like a class - ``Path`` - can't name that class in the annotation of a field: the class
# body's namespace, where annotations are evaluated, binds the name to the property.
_Path = Path


@export
class SourceFile(metaclass=ExtendedType, slots=True):
	"""
	A Python source file, read once: its lines, its syntax tree, and its tokens, which hold the comments.
	"""

	_COMMENT:   ClassVar[Pattern[str]] = re_compile(r"^\s*#: ?(.*)\r?\n?$")                              #: ``#:`` line.
	_INHERITED: ClassVar[Pattern[str]] = re_compile(r"#\s*docstr-coverage\s*:\s*inherit(ed)?\s*")        #: Inherited.
	_EXCUSED:   ClassVar[Pattern[str]] = re_compile(r"#\s*docstr-coverage\s*:\s*excuse(d)?\s* `.*`\s*")  #: Excused.

	_path:            _Path                       #: Path to the source file.
	_lines:           list[str]                   #: The source's lines, without line endings.
	_tree:            Module                      #: The source's syntax tree.
	_tokens:          list[TokenInfo]             #: The source's tokens.
	_parsingDuration: Nullable[timedelta]         #: Duration of reading and parsing the file, if measured.
	_positions:       dict[tuple[int, int], int]  #: The index of the token starting at a line and column.
	_lineStarts:      dict[int, int]              #: The index of the first token starting in a line.
	_closings:        dict[int, int]              #: The index of the closing bracket of an opening bracket.

	def __init__(
		self,
		path: Path,
		lines: list[str],
		tree: Module,
		tokens: list[TokenInfo],
		*,
		parsingDuration: Nullable[timedelta] = None
	) -> None:
		"""
		Initializes a read source file, and indexes its tokens.

		:param path:            Path to the source file.
		:param lines:           The source's lines, without line endings.
		:param tree:            The source's syntax tree.
		:param tokens:          The source's tokens.
		:param parsingDuration: Optional, the duration of reading and parsing the file. Default: ``None``.
		:raises ValueError:     If parameter ``path`` is ``None``.
		:raises TypeError:      If parameter ``path`` isn't of type :class:`~pathlib.Path`.
		:raises ValueError:     If parameter ``lines`` is ``None``.
		:raises TypeError:      If parameter ``lines`` isn't of type :class:`list`.
		:raises ValueError:     If parameter ``tree`` is ``None``.
		:raises TypeError:      If parameter ``tree`` isn't of type :class:`ast.Module`.
		:raises ValueError:     If parameter ``tokens`` is ``None``.
		:raises TypeError:      If parameter ``tokens`` isn't of type :class:`list`.
		:raises TypeError:      If parameter ``parsingDuration`` isn't of type :class:`~datetime.timedelta`.
		"""
		for parameterName, value, expectedType in (
			("path",   path,   Path),
			("lines",  lines,  list),
			("tree",   tree,   Module),
			("tokens", tokens, list)
		):
			if value is None:
				raise ValueError(f"Parameter '{parameterName}' is None.")
			elif not isinstance(value, expectedType):
				ex = TypeError(f"Parameter '{parameterName}' is not of type '{expectedType.__name__}'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(value)}'.")
				raise ex

		if parsingDuration is not None and not isinstance(parsingDuration, timedelta):
			ex = TypeError("Parameter 'parsingDuration' is not of type 'timedelta'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(parsingDuration)}'.")
			raise ex

		self._path =            path
		self._lines =           lines
		self._tree =            tree
		self._tokens =          tokens
		self._parsingDuration = parsingDuration
		self._positions =       {}
		self._lineStarts =      {}
		self._closings =        {}

		openings: list[int] = []
		for index, token in enumerate(tokens):
			self._positions[token.start] = index
			self._lineStarts.setdefault(token.start[0], index)
			if token.type == OP:
				if token.string in ("(", "[", "{"):
					openings.append(index)
				elif token.string in (")", "]", "}") and len(openings) > 0:
					self._closings[openings.pop()] = index

	@classmethod
	def Read(cls, path: Path) -> SourceFile:
		"""
		Read a source file in its declared encoding, and parse it, measuring the duration of both.

		:param path:                The source file.
		:returns:                   The read source file.
		:raises ValueError:         If parameter ``path`` is ``None``.
		:raises TypeError:          If parameter ``path`` isn't of type :class:`~pathlib.Path`.
		:raises OSError:            If the file can't be read.
		:raises SyntaxError:        If the file declares an unknown encoding, or isn't valid Python.
		:raises UnicodeDecodeError: If the file isn't encoded as it declares.
		:raises ValueError:         If the source contains a null byte (Python 3.11).
		:raises TokenError:         If the source ends inside a statement.
		"""
		if path is None:
			raise ValueError("Parameter 'path' is None.")
		elif not isinstance(path, Path):
			ex = TypeError("Parameter 'path' is not of type 'Path'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(path)}'.")
			raise ex

		with Stopwatch() as stopwatch:
			with tokenize_open(path) as file:
				source = file.read()

			tree = parse(source, filename=str(path))
			tokens = list(generate_tokens(StringIO(source).readline))

		parsingDuration = stopwatch.Duration
		return cls(path, source.split("\n"), tree, tokens, parsingDuration=parsingDuration)

	@readonly
	def Path(self) -> Path:
		"""
		Read-only property to access the path to the source file (:attr:`_path`).

		:returns: The path.
		"""
		return self._path

	@readonly
	def Lines(self) -> list[str]:
		"""
		Read-only property to access the source's lines (:attr:`_lines`).

		:returns: The lines, without line endings.
		"""
		return self._lines

	@readonly
	def Tree(self) -> Module:
		"""
		Read-only property to access the source's syntax tree (:attr:`_tree`).

		:returns: The syntax tree.
		"""
		return self._tree

	@readonly
	def ParsingDuration(self) -> Nullable[timedelta]:
		"""
		Read-only property to access the duration of reading, tokenizing and parsing the file (:attr:`_parsingDuration`).

		:returns: The duration, or ``None`` if it wasn't measured.
		"""
		return self._parsingDuration

	def DocumentationState(self, node: Module | ClassDef | FunctionDef | AsyncFunctionDef) -> CoverageState:
		"""
		Return how a module, class or function is documented: by a non-empty doc-string, or excused by a comment.

		docstr_coverage's comment, which excuses a class or function, is the first comment above its declaration,
		skipping blank lines and the lines of decorators.

		:param node: The module, class or function.
		:returns:    The documentation state of the declaration.
		"""
		docString = get_docstring(node)
		if docString is not None and docString.strip() != "":
			return CoverageState.Documented | CoverageState.Covered
		elif isinstance(node, Module):
			return CoverageState.Undocumented

		index = self._lineStarts.get(node.lineno, 0) - 1
		while index >= 0:
			token = self._tokens[index]
			if token.type in (NL, NEWLINE) or (token.type == NAME and token.string == "class") or \
					token.line.strip().startswith("@"):
				index -= 1
			elif token.type != COMMENT:
				break
			elif self._INHERITED.match(token.string) is not None:
				return CoverageState.Inherited | CoverageState.Covered
			elif self._EXCUSED.match(token.string) is not None:
				return CoverageState.Excused | CoverageState.Covered
			else:
				break

		return CoverageState.Undocumented

	def HasDocumentationComment(self, statement: stmt) -> bool:
		"""
		Return whether an assignment is documented by a non-empty ``#:`` comment, where Sphinx' autodoc finds it.

		Like autodoc, the comment behind the statement is looked up first - a comment behind an opening bracket belongs to
		the value -, then the ``#:`` comment lines directly above the statement.

		:param statement: The assignment.
		:returns:         ``True``, if a comment documents the assignment.
		"""
		line = self._lines[statement.lineno - 1]
		column = len(line.encode("utf-8")[:statement.col_offset].decode("utf-8", errors="replace"))

		if (index := self._positions.get((statement.lineno, column), None)) is not None:
			token = self._tokens[index]
			while not (token.type == OP and token.string == "=") and token.type not in (NEWLINE, COMMENT, ENDMARKER):
				index += 1
				token = self._tokens[index]

			if token.type == OP and token.string == "=":
				index += 1
				token = self._tokens[index]
				while token.type in (OP, NAME, NUMBER, STRING) and not (token.type == OP and token.string == ";"):
					index = self._closings.get(index, index) + 1
					token = self._tokens[index]

			if token.type == COMMENT and (match := self._COMMENT.match(token.string)) is not None:
				return match[1].strip() != ""

		if line[:column].strip() != "":
			return False

		for lineIndex in range(statement.lineno - 2, -1, -1):
			if (match := self._COMMENT.match(self._lines[lineIndex])) is None:
				return False
			elif match[1].strip() != "":
				return True

		return False


@export
class CountedItems(Flag):
	"""
	The items an analysis counts, besides the packages, modules, classes and callables of a public name.

	A protected name has one leading underscore; a private name two, but not two trailing ones like a dunder name. An
	item of a name, which isn't selected, is ignored. Fields and variables, which aren't selected, are excluded.
	"""

	Fields =    1                                         #: The fields of a class.
	Variables = 2                                         #: The variables of a module.
	Protected = 4                                         #: Items of a protected name, e.g. ``_x``.
	Private =   8                                         #: Items of a private, name-mangled name, e.g. ``__x``.

	Default =   Fields | Variables | Protected | Private  #: All items.


# A class with a property named like a class - ``CountedItems`` - can't name that class in the annotation of a field:
# the class body's namespace, where annotations are evaluated, binds the name to the property.
_CountedItems = CountedItems


@export
class Analyzer(metaclass=ExtendedType, slots=True):
	"""
	Reads the documentation coverage of a Python package from its source files.

	A package's or module's lines are its file's, so their items name no lines.

	.. rubric:: Example

	.. code-block:: Python

	   from pathlib import Path
	   from pyEDAA.Reports.DocumentationCoverage.Python import Analyzer, CountedItems
	   from pyTooling.Warning import WarningCollector

	   with WarningCollector() as warnings:
	     counted = CountedItems.Fields | CountedItems.Variables
	     report = Analyzer("myPackage", Path("src/myPackage"), countedItems=counted).Analyze()

	   print(f"{report.Counters.Covered}/{report.Counters.Expected}: {report.Counters.Coverage:.1%}")
	"""

	_packageName:     str                 #: Name of the package.
	_directory:       Path                #: The package's directory.
	_countedItems:    _CountedItems       #: The items the analysis counts.
	_excludePatterns: list[Pattern[str]]  #: The patterns of qualified names, whose items are excluded.

	def __init__(
		self,
		packageName: str,
		directory: Path,
		*,
		countedItems: CountedItems = CountedItems.Default,
		excludePatterns: Nullable[Iterable[str]] = None
	) -> None:
		"""
		Initializes the analysis of a package.

		:param packageName:     Name of the package, which is the name of the top-level item, e.g. ``myPackage``.
		:param directory:       The package's directory.
		:param countedItems:    Optional, the items the analysis counts. Default: all of them.
		:param excludePatterns: Optional, regular expressions matching the whole qualified name of an item to exclude,
		                        e.g. ``myPackage\\.CLI``; the items it contains are excluded too. Default: none.
		:raises ValueError:     If parameter ``packageName`` is ``None``.
		:raises TypeError:      If parameter ``packageName`` isn't of type :class:`str`.
		:raises ValueError:     If parameter ``packageName`` is empty.
		:raises ValueError:     If parameter ``directory`` is ``None``.
		:raises TypeError:      If parameter ``directory`` isn't of type :class:`~pathlib.Path`.
		:raises ValueError:     If parameter ``countedItems`` is ``None``.
		:raises TypeError:      If parameter ``countedItems`` isn't of type :class:`CountedItems`.
		:raises TypeError:      If parameter ``excludePatterns`` isn't iterable.
		:raises TypeError:      If parameter ``excludePatterns`` contains an element not of type :class:`str`.
		:raises ValueError:     If parameter ``excludePatterns`` contains an invalid regular expression.
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

		if countedItems is None:
			raise ValueError("Parameter 'countedItems' is None.")
		elif not isinstance(countedItems, CountedItems):
			ex = TypeError("Parameter 'countedItems' is not of type 'CountedItems'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(countedItems)}'.")
			raise ex

		self._packageName =     packageName
		self._directory =       directory
		self._countedItems =    countedItems
		self._excludePatterns = excludePatternList = []

		if excludePatterns is not None:
			if not isinstance(excludePatterns, Iterable):
				ex = TypeError("Parameter 'excludePatterns' is not iterable.")
				ex.add_note(f"Got type '{getFullyQualifiedName(excludePatterns)}'.")
				raise ex

			for excludePattern in excludePatterns:
				if not isinstance(excludePattern, str):
					ex = TypeError("Parameter 'excludePatterns' contains an element not of type 'str'.")
					ex.add_note(f"Got type '{getFullyQualifiedName(excludePattern)}'.")
					raise ex

				try:
					excludePatternList.append(re_compile(excludePattern))
				except RegularExpressionError as cause:
					ex = ValueError("Parameter 'excludePatterns' contains an invalid regular expression.")
					ex.add_note(f"Got pattern '{excludePattern}'.")
					raise ex from cause

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
	def CountedItems(self) -> CountedItems:
		"""
		Read-only property to access the items the analysis counts (:attr:`_countedItems`).

		:returns: The counted items.
		"""
		return self._countedItems

	@readonly
	def ExcludePatterns(self) -> list[Pattern[str]]:
		"""
		Read-only property to access the patterns of qualified names, whose items are excluded (:attr:`_excludePatterns`).

		:returns: The compiled regular expressions.
		"""
		return self._excludePatterns

	def Analyze(self) -> DocumentationReport:
		"""
		Read every Python source file of the package into a documentation coverage report, and aggregate it.

		The report's :attr:`~pyEDAA.Reports.DocumentationCoverage.DocumentationReport.AnalysisDuration` is the
		duration of the analysis. A source file, which can't be read or parsed, is raised as a
		:exc:`~pyEDAA.Reports.DocumentationCoverage.SourceFileWarning` to the current
		:class:`~pyTooling.Warning.WarningCollector`; its module is excluded, and the analysis continues.

		:returns:                              The report; its top-level item is the package.
		:raises DocCoverageError:              If the package's directory doesn't exist.
		:raises UnhandledCriticalWarningError: If a source file can't be analyzed, and no warning
		                                       collector collects the warning. |br|
		                                       Add a with-statement using
		                                       :class:`~pyTooling.Warning.WarningCollector`.
		"""
		if not self._directory.is_dir():
			raise DocCoverageError(f"Package directory '{self._directory.as_posix()}' doesn't exist.")

		with Stopwatch() as stopwatch:
			report = DocumentationReport(Path(self._packageName))
			self._ReadPackage(self._directory, self._packageName, report, report)
			report.Aggregate()

		report._analysisDuration = stopwatch.Duration

		return report

	def _ReadPackage(
		self,
		directory: Path,
		name: str,
		parent: Item | DocumentationReport,
		report: DocumentationReport
	) -> None:
		"""
		Read a package's ``__init__.py``, its modules, then its sub-packages, each sorted by name.

		:param directory: The package's directory.
		:param name:      The package's name.
		:param parent:    The package containing this one, or the report.
		:param report:    The report.
		"""
		if (directory / "__init__.py").is_file():
			package = self._ReadModule(directory / "__init__.py", name, ItemKind.Package, parent, report)
		else:
			package = Item(name, ItemKind.Package, self._State(CoverageState.Empty, name, parent), parent=parent)

		paths = sorted(directory.iterdir(), key=Path.as_posix)
		for path in paths:
			if path.suffix == ".py" and path.name != "__init__.py" and path.is_file():
				self._ReadModule(path, path.stem, ItemKind.Module, package, report)

		for path in paths:
			if path.is_dir() and next(path.rglob("*.py"), None) is not None:
				self._ReadPackage(path, path.name, package, report)

	def _ReadModule(
		self,
		path: Path,
		name: str,
		kind: ItemKind,
		parent: Item | DocumentationReport,
		report: DocumentationReport
	) -> Item:
		"""
		Read a module, or a package's ``__init__.py``, and the items declared in it.

		:param path:                           The source file.
		:param name:                           The module's or package's name.
		:param kind:                           The kind of the module's item.
		:param parent:                         The package containing the module, or the report.
		:param report:                         The report.
		:returns:                              The module's or package's item.
		:raises UnhandledCriticalWarningError: If the source file can't be analyzed, and no warning
		                                       collector collects the warning.
		"""
		file = report.GetOrAddFile(path.relative_to(self._directory))
		try:
			sourceFile = SourceFile.Read(path)
		except (OSError, SyntaxError, TokenError, ValueError) as ex:
			WarningCollector.Raise(
				SourceFileWarning(f"Source file '{file.Path.as_posix()}' can't be analyzed.", file=file),
				ex
			)
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
		elif isMember and statement.name == "__del__":
			kind = ItemKind.Destructor
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
				excluded=(CountedItems.Fields if isField else CountedItems.Variables) not in self._countedItems
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
		parent: Item | DocumentationReport,
		*,
		ignored: bool = False,
		excluded: bool = False
	) -> CoverageState:
		"""
		Return an item's coverage state: how it is documented, and whether it is excluded or ignored.

		An item is excluded, if its qualified name, or the qualified name of an item containing it, matches an exclude
		pattern. It is ignored, if its name is protected or private, and :class:`CountedItems` doesn't select such names.

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
			for pattern in self._excludePatterns for length in range(1, len(names) + 1)
		):
			return documentation | CoverageState.Excluded
		elif ignored or (
			name.startswith("_") and not name.startswith("__") and CountedItems.Protected not in self._countedItems
		) or (
			name.startswith("__") and not name.endswith("__") and CountedItems.Private not in self._countedItems
		):
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
