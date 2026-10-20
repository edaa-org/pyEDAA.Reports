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
"""Unit tests of the reader of Python source code for the documentation coverage model."""
from datetime                                    import timedelta
from pathlib                                     import Path
from sys                                         import version_info
from tempfile                                    import TemporaryDirectory
from textwrap                                    import dedent
from tokenize                                    import generate_tokens
from typing                                      import Iterable, Optional as Nullable
from unittest                                    import skipIf

from pyTooling.Warning                           import UnhandledCriticalWarningError, WarningCollector
from pyTooling.Testing                           import Testcase

from pyEDAA.Reports.DocumentationCoverage        import CoverageState, DocCoverageError, DocumentationReport
from pyEDAA.Reports.DocumentationCoverage        import Item, ItemKind, SourceFileWarning
from pyEDAA.Reports.DocumentationCoverage.Python import Analyzer, CountedItems, SourceFile


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


DOCUMENTED =   CoverageState.Documented | CoverageState.Covered                 #: State of a documented item.
UNDOCUMENTED = CoverageState.Undocumented                                       #: State of an undocumented item.
FIXTURE =      Path("tests/data/DocumentationCoverage/Attributes.py")           #: A source file to read.


def analyzePackage(
	files: dict[str, str],
	countedItems: CountedItems = CountedItems.Default,
	excludePatterns: Nullable[Iterable[str]] = None
) -> DocumentationReport:
	"""
	Write a package ``myPackage`` into a temporary directory and analyze it.

	:param files:           The source of each file, by its path in the package; the source is dedented.
	:param countedItems:    Optional, the items the analysis counts. Default: all of them.
	:param excludePatterns: Optional, the patterns of qualified names to exclude. Default: none.
	:returns:               The report.
	"""
	with TemporaryDirectory() as directory:
		for path, source in files.items():
			file = Path(directory) / path
			file.parent.mkdir(parents=True, exist_ok=True)
			file.write_text(dedent(source), encoding="utf-8")

		return Analyzer("myPackage", Path(directory), countedItems=countedItems, excludePatterns=excludePatterns).Analyze()


def analyzeModule(
	source: str,
	countedItems: CountedItems = CountedItems.Default,
	excludePatterns: Nullable[Iterable[str]] = None
) -> Item:
	"""
	Analyze a package ``myPackage`` of a module ``Module``.

	:param source:          The module's source; it is dedented.
	:param countedItems:    Optional, the items the analysis counts. Default: all of them.
	:param excludePatterns: Optional, the patterns of qualified names to exclude. Default: none.
	:returns:               The module's item.
	"""
	return analyzePackage({"Module.py": source}, countedItems, excludePatterns).Items[0]["Module"]


class Modules(Testcase):
	def test_Package(self) -> None:
		report = analyzePackage({
			"__init__.py":          '"""A package."""\n',
			"Shapes.py":            '"""A module."""\n',
			"Empty.py":             "# A comment only.\n",
			"Undocumented.py":      "import sys\n",
			"Units/__init__.py":    "",
			"Units/Length.py":      '"""A module of a sub-package."""\n',
			"Plugins/Loader.py":    '"""A module of a namespace package."""\n',
			"Resources/README.txt": "No Python file.\n",
		})
		package = report.Items[0]

		self.assertEqual(Path("myPackage"), report.Name)
		self.assertGreaterEqual(report.AnalysisDuration, timedelta(0))
		self.assertIs(timedelta, type(report.AnalysisDuration))
		self.assertEqual([package], report.Items)
		self.assertEqual(ItemKind.Package, package.Kind)
		self.assertEqual(DOCUMENTED, package.Status)
		self.assertEqual(["Empty", "Shapes", "Undocumented", "Plugins", "Units"], [item.Name for item in package])
		self.assertIs(ItemKind.Module, package["Shapes"].Kind)
		self.assertEqual(DOCUMENTED, package["Shapes"].Status)
		self.assertEqual(CoverageState.Empty, package["Empty"].Status)
		self.assertEqual(UNDOCUMENTED, package["Undocumented"].Status)
		self.assertEqual(CoverageState.Empty, package["Units"].Status)
		self.assertEqual(CoverageState.Empty, package["Plugins"].Status)
		self.assertIsNone(package["Plugins"].File)
		self.assertEqual("myPackage.Units.Length", package["Units"]["Length"].QualifiedName)
		self.assertEqual(Path("Units/Length.py"), package["Units"]["Length"].File.Path)
		self.assertIsNone(package["Shapes"].StartLine)

		self.assertEqual(7, report.FileCount)
		self.assertEqual(5, report.Counters.Expected)
		self.assertEqual(4, report.Counters.Covered)

	def test_Parameters(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = Analyzer("", Path("."))
		self.assertEqual("Parameter 'packageName' is empty.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = Analyzer("myPackage", ".")
		self.assertEqual("Parameter 'directory' is not of type 'Path'.", str(context.exception))

		with self.assertRaises(ValueError) as context:
			_ = Analyzer("myPackage", Path("."), countedItems=None)
		self.assertEqual("Parameter 'countedItems' is None.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = Analyzer("myPackage", Path("."), countedItems=1)
		self.assertEqual("Parameter 'countedItems' is not of type 'CountedItems'.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = Analyzer("myPackage", Path("."), excludePatterns=1)
		self.assertEqual("Parameter 'excludePatterns' is not iterable.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = Analyzer("myPackage", Path("."), excludePatterns=[1])
		self.assertEqual("Parameter 'excludePatterns' contains an element not of type 'str'.", str(context.exception))

		with self.assertRaises(ValueError) as context:
			_ = Analyzer("myPackage", Path("."), excludePatterns=["myPackage.("])
		self.assertEqual("Parameter 'excludePatterns' contains an invalid regular expression.", str(context.exception))

		analyzer = Analyzer("myPackage", Path("src"))
		self.assertEqual("myPackage", analyzer.PackageName)
		self.assertEqual(Path("src"), analyzer.Directory)
		self.assertIs(CountedItems.Default, analyzer.CountedItems)
		self.assertEqual([], analyzer.ExcludePatterns)

	def test_MissingDirectory(self) -> None:
		with self.assertRaises(DocCoverageError) as context:
			_ = Analyzer("myPackage", Path("tests/packages/missing")).Analyze()
		self.assertEqual("Package directory 'tests/packages/missing' doesn't exist.", str(context.exception))


class Callables(Testcase):
	def test_Kinds(self) -> None:
		module = analyzeModule('''\
			"""A module."""
			from enum   import Enum
			from typing import overload

			def Function() -> None:
				"""A function."""
				def Nested() -> None:
					pass

				class Local:
					def Method(self) -> None:
						"""A method of a class in a function."""

			async def Coroutine() -> None:
				pass

			class Color(Enum):
				"""An enumeration."""

			class Shape:
				"""A class."""

				def __init__(self) -> None:
					pass

				@property
				def Name(self) -> str:
					"""A getter."""

				@Name.setter
				def Name(self, value: str) -> None:
					pass

				@Name.deleter
				def Name(self) -> None:
					pass

				@readonly
				def Size(self) -> int:
					"""A read-only property."""

				@overload
				def Scale(self, factor: int) -> None: ...

				def Scale(self, factor) -> None:
					"""A method."""

				def __str__(self) -> str:
					pass

				def __del__(self) -> None:
					"""A destructor."""

				class Inner:
					"""A nested class."""
		''')
		shape = module["Shape"]
		function = module["Function"]

		self.assertIs(ItemKind.Function, function.Kind)
		self.assertIs(ItemKind.Function, function["Nested"].Kind)
		self.assertIs(ItemKind.Class, function["Local"].Kind)
		self.assertIs(ItemKind.Method, function["Local"]["Method"].Kind)
		self.assertIs(ItemKind.Function, module["Coroutine"].Kind)
		self.assertIs(ItemKind.Enumeration, module["Color"].Kind)
		self.assertIs(ItemKind.Class, shape.Kind)
		self.assertEqual(
			[
				("__init__", ItemKind.Constructor, UNDOCUMENTED),
				("Name",     ItemKind.Property,    DOCUMENTED),
				("Name",     ItemKind.Property,    CoverageState.Ignored | UNDOCUMENTED),
				("Name",     ItemKind.Property,    CoverageState.Ignored | UNDOCUMENTED),
				("Size",     ItemKind.Property,    DOCUMENTED),
				("Scale",    ItemKind.Method,      CoverageState.Ignored | UNDOCUMENTED),
				("Scale",    ItemKind.Method,      DOCUMENTED),
				("__str__",  ItemKind.Method,      UNDOCUMENTED),
				("__del__",  ItemKind.Destructor,  DOCUMENTED),
				("Inner",    ItemKind.Class,       DOCUMENTED),
			],
			[(item.Name, item.Kind, item.Status) for item in shape]
		)

	def test_Lines(self) -> None:
		module = analyzeModule('''\
			"""A module."""

			@export
			class Shape:
				"""A class."""

				def Area(self) -> float:
					"""A method."""
					return 0.0
		''')

		self.assertEqual(3, module["Shape"].StartLine)
		self.assertEqual(9, module["Shape"].EndLine)
		self.assertEqual(7, module["Shape"]["Area"].StartLine)
		self.assertEqual(9, module["Shape"]["Area"].EndLine)
		self.assertIs(module.File, module["Shape"]["Area"].File)

	def test_Excuses(self) -> None:
		"""docstr_coverage's comment directly above a declaration - decorators and blank lines between - excuses it."""
		module = analyzeModule('''\
			"""A module."""

			class Shape:
				"""A class."""

				# docstr-coverage: inherited
				def Area(self) -> float:
					pass

				# docstr-coverage:excused `abstract`

				@abstractmethod
				@export
				def Perimeter(self) -> float:
					pass

				# docstr-coverage: inherited
				x = 1
				def Center(self) -> float:
					pass

			# docstr-coverage: excused without reason
			def Function() -> None:
				pass
		''')
		shape = module["Shape"]

		self.assertEqual(CoverageState.Inherited | CoverageState.Covered, shape["Area"].Status)
		self.assertEqual(CoverageState.Excused | CoverageState.Covered, shape["Perimeter"].Status)
		self.assertEqual(UNDOCUMENTED, shape["Center"].Status)
		self.assertEqual(UNDOCUMENTED, module["Function"].Status)


class Fields(Testcase):
	def test_Forms(self) -> None:
		module = analyzeModule('''\
			"""A module."""

			class Shape:
				"""A class."""

				__slots__ = ("_name", )
				_name: str                    #: A trailing comment.
				#: A comment line above.
				_size: int
				_counter: ClassVar[int] = 0
				"""A string literal after the statement."""
				_lookup: ClassVar[dict] = {   #: Behind an opening bracket.
					"a": 1,
				}
				_table: ClassVar[dict] = {
					"a": 1,
				}                             #: Behind a closing bracket.
				_empty: int                   #:
				_undocumented: int
				_initialized: int

				if True:
					_conditional: int
				else:
					_conditional: int           #: Documented in one branch.

				try:
					_guarded: int
				except ImportError:
					_handled: int

				def __init__(self) -> None:
					"""Initializes a shape."""
					self._initialized = 1       #: Documented in '__init__'.
					self._onlyInInit = 2        #: Not declared in the class' body.
					local = 3                   #: A local variable.
		''')

		self.assertEqual(
			[
				("__slots__",     CoverageState.Ignored | UNDOCUMENTED),
				("_name",         DOCUMENTED),
				("_size",         DOCUMENTED),
				("_counter",      DOCUMENTED),
				("_lookup",       UNDOCUMENTED),
				("_table",        DOCUMENTED),
				("_empty",        UNDOCUMENTED),
				("_undocumented", UNDOCUMENTED),
				("_initialized",  DOCUMENTED),
				("_conditional",  DOCUMENTED),
				("_guarded",      UNDOCUMENTED),
				("__init__",      DOCUMENTED),
			],
			[(item.Name, item.Status) for item in module["Shape"]]
		)
		self.assertTrue(all(item.Kind is ItemKind.Field for item in module["Shape"] if item.Name != "__init__"))
		self.assertEqual(15, module["Shape"]["_table"].StartLine)
		self.assertEqual(17, module["Shape"]["_table"].EndLine)

	def test_Enumeration(self) -> None:
		module = analyzeModule('''\
			"""A module."""

			class Color(Enum):
				"""An enumeration."""

				_ignore_ = ["Unused"]
				Red = 1                       #: Red.
				Green = 2
				_value_: int
		''')

		self.assertEqual(
			[
				("_ignore_", ItemKind.EnumerationMember, CoverageState.Ignored | UNDOCUMENTED),
				("Red",      ItemKind.EnumerationMember, DOCUMENTED),
				("Green",    ItemKind.EnumerationMember, UNDOCUMENTED),
				("_value_",  ItemKind.Field,             CoverageState.Ignored | UNDOCUMENTED),
			],
			[(item.Name, item.Kind, item.Status) for item in module["Color"]]
		)

	def test_ClassInFunction(self) -> None:
		"""The fields of a class declared in a function's body are no items; its methods are."""
		module = analyzeModule('''\
			"""A module."""

			def Function() -> None:
				"""A function."""
				class Local:
					_field: int               #: A field.

					def Method(self) -> None:
						"""A method."""
		''')

		self.assertEqual(["Method"], [item.Name for item in module["Function"]["Local"]])


class Variables(Testcase):
	def test_Kinds(self) -> None:
		module = analyzeModule('''\
			"""A module."""
			import sys
			from typing import Final, NewType, TypeAlias, TypeVar

			__all__ = ["T"]
			T = TypeVar("T")                  #: A type variable.
			P = typing.ParamSpec("P")
			Length = NewType("Length", float)
			Alias: TypeAlias = "int | str"
			MAXIMUM = 10
			minimum: Final = 0
			counter = 0
			counter += 1
			first, *rest = 1, 2, 3            #: A tuple.
			sys.flag = True
			table["a"] = 1
			_private = 2
		''')

		self.assertEqual(
			[
				("__all__",  ItemKind.Variable,     CoverageState.Ignored | UNDOCUMENTED),
				("T",        ItemKind.TypeVariable, DOCUMENTED),
				("P",        ItemKind.TypeVariable, UNDOCUMENTED),
				("Length",   ItemKind.Type,         UNDOCUMENTED),
				("Alias",    ItemKind.TypeAlias,    UNDOCUMENTED),
				("MAXIMUM",  ItemKind.Constant,     UNDOCUMENTED),
				("minimum",  ItemKind.Constant,     UNDOCUMENTED),
				("counter",  ItemKind.Variable,     UNDOCUMENTED),
				("first",    ItemKind.Variable,     DOCUMENTED),
				("rest",     ItemKind.Variable,     DOCUMENTED),
				("_private", ItemKind.Variable,     UNDOCUMENTED),
			],
			[(item.Name, item.Kind, item.Status) for item in module]
		)

	@skipIf(version_info < (3, 12), "The 'type' statement needs Python 3.12.")
	def test_TypeStatement(self) -> None:
		module = analyzeModule('''\
			"""A module."""

			type Number = int | float         #: A type alias.

			class Shape:
				"""A class."""

				type Point = tuple[int, int]
		''')

		self.assertIs(ItemKind.TypeAlias, module["Number"].Kind)
		self.assertEqual(DOCUMENTED, module["Number"].Status)
		self.assertIs(ItemKind.TypeAlias, module["Shape"]["Point"].Kind)
		self.assertEqual(UNDOCUMENTED, module["Shape"]["Point"].Status)

	def test_StringAfter(self) -> None:
		"""A string literal after the statement documents the first target; a string after an 'if' statement doesn't."""
		module = analyzeModule('''\
			"""A module."""

			chained = other = 1
			"""The first target."""

			if True:
				conditional = 1
			"""After the 'if' statement."""

			try:
				guarded = 1
			finally:
				pass
			empty = 1
			""" """
		''')

		self.assertEqual(
			[("chained", DOCUMENTED), ("other", UNDOCUMENTED), ("conditional", UNDOCUMENTED), ("guarded", UNDOCUMENTED),
			 ("empty", UNDOCUMENTED)],
			[(item.Name, item.Status) for item in module]
		)


class Counting(Testcase):
	SOURCE = '''\
		"""A module."""

		VERSION = "1.0"

		def _Protected() -> None:
			"""A function of a protected name."""

		class Shape:
			"""A class."""

			_name:  str                     #: A field of a protected name.
			__size: int                     #: A field of a private name.

			def __init__(self) -> None:
				pass

			def _Helper(self) -> None:
				pass

			def __Mangled(self) -> None:
				pass
	'''  #: A module with a variable, fields and callables of public, protected and private names.

	def test_Default(self) -> None:
		module = analyzeModule(self.SOURCE)
		shape = module["Shape"]

		self.assertEqual(UNDOCUMENTED, module["VERSION"].Status)
		self.assertEqual(DOCUMENTED, module["_Protected"].Status)
		self.assertEqual(DOCUMENTED, shape["_name"].Status)
		self.assertEqual(DOCUMENTED, shape["__size"].Status)
		self.assertEqual(UNDOCUMENTED, shape["_Helper"].Status)
		self.assertEqual(UNDOCUMENTED, shape["__Mangled"].Status)
		self.assertEqual(9, module.Counters.Expected)

	def test_Fields(self) -> None:
		"""Fields not counted are excluded."""
		module = analyzeModule(self.SOURCE, CountedItems.Default & ~CountedItems.Fields)

		self.assertEqual(CoverageState.Excluded | DOCUMENTED, module["Shape"]["_name"].Status)
		self.assertEqual(UNDOCUMENTED, module["VERSION"].Status)
		self.assertEqual(2, module.Counters.Excluded)

	def test_Variables(self) -> None:
		"""Variables not counted are excluded."""
		module = analyzeModule(self.SOURCE, CountedItems.Default & ~CountedItems.Variables)

		self.assertEqual(CoverageState.Excluded | UNDOCUMENTED, module["VERSION"].Status)
		self.assertEqual(DOCUMENTED, module["Shape"]["_name"].Status)
		self.assertEqual(1, module.Counters.Excluded)

	def test_Protected(self) -> None:
		"""Items of a protected name - one leading underscore - not counted are ignored, whatever their kind."""
		module = analyzeModule(self.SOURCE, CountedItems.Default & ~CountedItems.Protected)
		shape = module["Shape"]

		self.assertEqual(CoverageState.Ignored | DOCUMENTED, module["_Protected"].Status)
		self.assertEqual(CoverageState.Ignored | DOCUMENTED, shape["_name"].Status)
		self.assertEqual(CoverageState.Ignored | UNDOCUMENTED, shape["_Helper"].Status)
		self.assertEqual(DOCUMENTED, shape["__size"].Status)
		self.assertEqual(UNDOCUMENTED, shape["__init__"].Status)
		self.assertEqual(6, module.Counters.Expected)

	def test_Private(self) -> None:
		"""Items of a private name - two leading, but no trailing underscores - not counted are ignored."""
		module = analyzeModule(self.SOURCE, CountedItems.Default & ~CountedItems.Private)
		shape = module["Shape"]

		self.assertEqual(CoverageState.Ignored | DOCUMENTED, shape["__size"].Status)
		self.assertEqual(CoverageState.Ignored | UNDOCUMENTED, shape["__Mangled"].Status)
		self.assertEqual(DOCUMENTED, shape["_name"].Status)
		self.assertEqual(UNDOCUMENTED, shape["__init__"].Status)
		self.assertEqual(7, module.Counters.Expected)

	def test_ProtectedModule(self) -> None:
		"""A module of a protected name not counted is ignored."""
		package = analyzePackage({"_Internal.py": '"""A module."""\n'}, CountedItems.Fields).Items[0]

		self.assertEqual(CoverageState.Ignored | DOCUMENTED, package["_Internal"].Status)

	def test_ExcludePatterns(self) -> None:
		"""An item matching a pattern is excluded, and so are the items it contains."""
		module = analyzeModule(self.SOURCE, excludePatterns=[r"myPackage\.Module\.Shape", r".*\.VERSION"])
		shape = module["Shape"]

		self.assertEqual(CoverageState.Excluded | DOCUMENTED, shape.Status)
		self.assertEqual(CoverageState.Excluded | UNDOCUMENTED, shape["__init__"].Status)
		self.assertEqual(CoverageState.Excluded | UNDOCUMENTED, module["VERSION"].Status)
		self.assertEqual(DOCUMENTED, module.Status)
		self.assertEqual(2, module.Counters.Expected)
		self.assertEqual(7, module.Counters.Excluded)


class SourceFiles(Testcase):
	def test_SyntaxError(self) -> None:
		"""A file that can't be parsed is collected as a critical warning, its item excluded, and the analysis goes on."""
		with WarningCollector() as warnings:
			report = analyzePackage({"Broken.py": "def (:\n", "Shapes.py": '"""A module."""\n'})

		package = report.Items[0]
		self.assertEqual(1, len(warnings))
		self.assertIsInstance(warnings[0], SourceFileWarning)
		self.assertEqual("Source file 'Broken.py' can't be analyzed.", str(warnings[0]))
		self.assertIsInstance(warnings[0].__cause__, SyntaxError)
		self.assertIs(package["Broken"].File, warnings[0].File)
		self.assertEqual(Path("Broken.py"), warnings[0].File.Path)
		self.assertEqual(CoverageState.Excluded, package["Broken"].Status)
		self.assertEqual(DOCUMENTED, package["Shapes"].Status)
		self.assertEqual(1, report.Counters.Expected)
		self.assertEqual(1, report.Counters.Excluded)

	def test_SyntaxError_Uncollected(self) -> None:
		"""Without a warning collector, a file that can't be parsed stops the analysis."""
		with self.assertRaises(UnhandledCriticalWarningError) as context:
			_ = analyzePackage({"Broken.py": "def (:\n"})

		self.assertIsInstance(context.exception.__cause__, SourceFileWarning)

	def test_SourceFileWarning_MessageOnly(self) -> None:
		warning = SourceFileWarning("Source file can't be analyzed.")

		self.assertIsNone(warning.File)

	def test_Encoding(self) -> None:
		"""A file is read in its declared encoding; a file not encoded as declared is collected as a critical warning."""
		with TemporaryDirectory() as directory:
			(Path(directory) / "Latin1.py").write_bytes('# -*- coding: latin-1 -*-\n"""Bötzingen."""\n'.encode("latin-1"))
			(Path(directory) / "Invalid.py").write_bytes('"""Bötzingen."""\n'.encode("latin-1"))

			with WarningCollector() as warnings:
				report = Analyzer("myPackage", Path(directory)).Analyze()

		package = report.Items[0]
		self.assertEqual(DOCUMENTED, package["Latin1"].Status)
		self.assertEqual(CoverageState.Excluded, package["Invalid"].Status)
		self.assertEqual(1, len(warnings))
		self.assertIsInstance(warnings[0].__cause__, (SyntaxError, UnicodeDecodeError))

	def test_Read(self) -> None:
		sourceFile = SourceFile.Read(FIXTURE)

		self.assertEqual(FIXTURE, sourceFile.Path)
		self.assertEqual("from enum   import Enum", sourceFile.Lines[1])
		self.assertEqual(sourceFile.Tree.body[0].lineno, 1)
		self.assertGreaterEqual(sourceFile.ParsingDuration, timedelta(0))
		self.assertIs(timedelta, type(sourceFile.ParsingDuration))

		with self.assertRaises(ValueError) as context:
			_ = SourceFile.Read(None)
		self.assertEqual("Parameter 'path' is None.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = SourceFile.Read(str(FIXTURE))
		self.assertEqual("Parameter 'path' is not of type 'Path'.", str(context.exception))

	def test_Parameters(self) -> None:
		sourceFile = SourceFile.Read(FIXTURE)
		tokens = list(generate_tokens(iter(sourceFile.Lines).__next__))

		with self.assertRaises(ValueError) as context:
			_ = SourceFile(FIXTURE, sourceFile.Lines, None, tokens)
		self.assertEqual("Parameter 'tree' is None.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = SourceFile(FIXTURE, tuple(sourceFile.Lines), sourceFile.Tree, tokens)
		self.assertEqual("Parameter 'lines' is not of type 'list'.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = SourceFile(FIXTURE, sourceFile.Lines, sourceFile.Tree, tokens, parsingDuration=0.5)
		self.assertEqual("Parameter 'parsingDuration' is not of type 'timedelta'.", str(context.exception))

		self.assertIsNone(SourceFile(FIXTURE, sourceFile.Lines, sourceFile.Tree, tokens).ParsingDuration)
