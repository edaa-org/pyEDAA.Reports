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
from importlib.util                                     import find_spec
from pathlib                                            import Path
from sys                                                import version_info
from tempfile                                           import TemporaryDirectory
from textwrap                                           import dedent
from tokenize                                           import generate_tokens
from typing                                             import Optional as Nullable
from unittest                                           import skipIf

from pyEDAA.Reports.DocumentationCoverage               import CoverageState, DocCoverageError, ItemKind
from pyEDAA.Reports.DocumentationCoverage               import SourceFileWarning
from pyEDAA.Reports.DocumentationCoverage.Files         import CoverageSummary
from pyEDAA.Reports.DocumentationCoverage.Items         import Item
from pyEDAA.Reports.DocumentationCoverage.Python        import Analyzer, Options
from pyEDAA.Reports.DocumentationCoverage.Python.Source import SourceFile
from pyTooling.Warning                                  import UnhandledCriticalWarningError, WarningCollector
from pyTooling.Testing                                  import Testcase


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


DOCUMENTED =   CoverageState.Documented | CoverageState.Covered                 #: State of a documented item.
UNDOCUMENTED = CoverageState.Undocumented                                       #: State of an undocumented item.
FIXTURE =      Path("tests/data/DocumentationCoverage/Attributes.py")           #: Fields and variables for the oracle.
ATTRIBUTES =   (ItemKind.Field, ItemKind.EnumerationMember, ItemKind.Variable, ItemKind.Constant, ItemKind.TypeAlias,
                ItemKind.TypeVariable, ItemKind.Type)                           #: The kinds of fields and variables.


def analyzePackage(files: dict[str, str], options: Nullable[Options] = None) -> CoverageSummary:
	"""
	Write a package ``myPackage`` into a temporary directory and analyze it.

	:param files:   The source of each file, by its path in the package; the source is dedented.
	:param options: Optional, the options of the analysis. Default: the defaults.
	:returns:       The analysis' root.
	"""
	with TemporaryDirectory() as directory:
		for path, source in files.items():
			file = Path(directory) / path
			file.parent.mkdir(parents=True, exist_ok=True)
			file.write_text(dedent(source), encoding="utf-8")

		return Analyzer("myPackage", Path(directory), options=options).Analyze()


def analyzeModule(source: str, options: Nullable[Options] = None) -> Item:
	"""
	Analyze a package ``myPackage`` of a module ``Module``.

	:param source:  The module's source; it is dedented.
	:param options: Optional, the options of the analysis. Default: the defaults.
	:returns:       The module's item.
	"""
	return analyzePackage({"Module.py": source}, options).Items[0]["Module"]


class Modules(Testcase):
	def test_Package(self) -> None:
		summary = analyzePackage({
			"__init__.py":          '"""A package."""\n',
			"Shapes.py":            '"""A module."""\n',
			"Empty.py":             "# A comment only.\n",
			"Undocumented.py":      "import sys\n",
			"Units/__init__.py":    "",
			"Units/Length.py":      '"""A module of a sub-package."""\n',
			"Plugins/Loader.py":    '"""A module of a namespace package."""\n',
			"Resources/README.txt": "No Python file.\n",
		})
		package = summary.Items[0]

		self.assertEqual("myPackage", summary.Name)
		self.assertEqual([package], summary.Items)
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

		self.assertEqual(7, summary.FileCount)
		self.assertEqual(5, summary.Counters.Expected)
		self.assertEqual(4, summary.Counters.Covered)

	def test_Parameters(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = Analyzer("", Path("."))
		self.assertEqual("Parameter 'packageName' is empty.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = Analyzer("myPackage", ".")
		self.assertEqual("Parameter 'directory' is not of type 'Path'.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = Analyzer("myPackage", Path("."), options={"countFields": False})
		self.assertEqual("Parameter 'options' is not of type 'Options'.", str(context.exception))

		analyzer = Analyzer("myPackage", Path("src"))
		self.assertEqual("myPackage", analyzer.PackageName)
		self.assertEqual(Path("src"), analyzer.Directory)
		self.assertTrue(analyzer.Options.CountFields)

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


class AnalysisOptions(Testcase):
	SOURCE = '''\
		"""A module."""

		VERSION = "1.0"

		class Shape:
			"""A class."""

			_name: str                      #: A field.

			def __init__(self) -> None:
				pass

			def _Helper(self) -> None:
				pass
	'''  #: A module with a variable, a field, a constructor and a private method.

	def test_Defaults(self) -> None:
		options = Options()

		self.assertTrue(options.CountFields)
		self.assertTrue(options.CountVariables)
		self.assertFalse(options.SkipPrivate)
		self.assertEqual([], options.ExcludePatterns)

		module = analyzeModule(self.SOURCE)
		self.assertEqual(UNDOCUMENTED, module["VERSION"].Status)
		self.assertEqual(DOCUMENTED, module["Shape"]["_name"].Status)
		self.assertEqual(UNDOCUMENTED, module["Shape"]["_Helper"].Status)
		self.assertEqual(6, module.Counters.Expected)

	def test_CountFields(self) -> None:
		module = analyzeModule(self.SOURCE, Options(countFields=False))

		self.assertEqual(CoverageState.Excluded | DOCUMENTED, module["Shape"]["_name"].Status)
		self.assertEqual(UNDOCUMENTED, module["VERSION"].Status)
		self.assertEqual(1, module.Counters.Excluded)

	def test_CountVariables(self) -> None:
		module = analyzeModule(self.SOURCE, Options(countVariables=False))

		self.assertEqual(CoverageState.Excluded | UNDOCUMENTED, module["VERSION"].Status)
		self.assertEqual(DOCUMENTED, module["Shape"]["_name"].Status)

	def test_SkipPrivate(self) -> None:
		module = analyzeModule(self.SOURCE, Options(skipPrivate=True))
		shape = module["Shape"]

		self.assertEqual(CoverageState.Ignored | DOCUMENTED, shape["_name"].Status)
		self.assertEqual(CoverageState.Ignored | UNDOCUMENTED, shape["_Helper"].Status)
		self.assertEqual(UNDOCUMENTED, shape["__init__"].Status)
		self.assertEqual(4, module.Counters.Expected)

	def test_ExcludePatterns(self) -> None:
		"""An item matching a pattern is excluded, and so are the items it contains."""
		module = analyzeModule(self.SOURCE, Options(excludePatterns=[r"myPackage\.Module\.Shape", r".*\.VERSION"]))
		shape = module["Shape"]

		self.assertEqual(CoverageState.Excluded | DOCUMENTED, shape.Status)
		self.assertEqual(CoverageState.Excluded | UNDOCUMENTED, shape["__init__"].Status)
		self.assertEqual(CoverageState.Excluded | UNDOCUMENTED, module["VERSION"].Status)
		self.assertEqual(DOCUMENTED, module.Status)
		self.assertEqual(1, module.Counters.Expected)
		self.assertEqual(5, module.Counters.Excluded)

	def test_Parameters(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = Options(countFields=None)
		self.assertEqual("Parameter 'countFields' is None.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = Options(skipPrivate=1)
		self.assertEqual("Parameter 'skipPrivate' is not of type 'bool'.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = Options(excludePatterns=1)
		self.assertEqual("Parameter 'excludePatterns' is not iterable.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = Options(excludePatterns=[1])
		self.assertEqual("Parameter 'excludePatterns' contains an element not of type 'str'.", str(context.exception))

		with self.assertRaises(ValueError) as context:
			_ = Options(excludePatterns=["myPackage.("])
		self.assertEqual("Parameter 'excludePatterns' contains an invalid regular expression.", str(context.exception))


class SourceFiles(Testcase):
	def test_SyntaxError(self) -> None:
		"""A file that can't be parsed is collected as a critical warning, its item excluded, and the analysis goes on."""
		with WarningCollector() as warnings:
			summary = analyzePackage({"Broken.py": "def (:\n", "Shapes.py": '"""A module."""\n'})

		package = summary.Items[0]
		self.assertEqual(1, len(warnings))
		self.assertIsInstance(warnings[0], SourceFileWarning)
		self.assertEqual("Source file 'Broken.py' can't be analyzed.", str(warnings[0]))
		self.assertIsInstance(warnings[0].__cause__, SyntaxError)
		self.assertEqual(CoverageState.Excluded, package["Broken"].Status)
		self.assertEqual(DOCUMENTED, package["Shapes"].Status)
		self.assertEqual(1, summary.Counters.Expected)
		self.assertEqual(1, summary.Counters.Excluded)

	def test_SyntaxError_Uncollected(self) -> None:
		"""Without a warning collector, a file that can't be parsed stops the analysis."""
		with self.assertRaises(UnhandledCriticalWarningError) as context:
			_ = analyzePackage({"Broken.py": "def (:\n"})

		self.assertIsInstance(context.exception.__cause__, SourceFileWarning)

	def test_Encoding(self) -> None:
		"""A file is read in its declared encoding; a file not encoded as declared is collected as a critical warning."""
		with TemporaryDirectory() as directory:
			(Path(directory) / "Latin1.py").write_bytes('# -*- coding: latin-1 -*-\n"""Bötzingen."""\n'.encode("latin-1"))
			(Path(directory) / "Invalid.py").write_bytes('"""Bötzingen."""\n'.encode("latin-1"))

			with WarningCollector() as warnings:
				summary = Analyzer("myPackage", Path(directory)).Analyze()

		package = summary.Items[0]
		self.assertEqual(DOCUMENTED, package["Latin1"].Status)
		self.assertEqual(CoverageState.Excluded, package["Invalid"].Status)
		self.assertEqual(1, len(warnings))
		self.assertIsInstance(warnings[0].__cause__, (SyntaxError, UnicodeDecodeError))

	def test_Read(self) -> None:
		sourceFile = SourceFile.Read(FIXTURE)

		self.assertEqual(FIXTURE, sourceFile.Path)
		self.assertEqual("from enum   import Enum", sourceFile.Lines[1])
		self.assertEqual(sourceFile.Tree.body[0].lineno, 1)

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


class Regression(Testcase):
	@skipIf(find_spec("docstr_coverage") is None, "docstr_coverage isn't installed.")
	def test_DocStrCoverage(self) -> None:
		"""Without fields and variables, the reader counts per file what docstr_coverage counts."""
		from docstr_coverage import analyze

		directory = Path("pyEDAA/Reports")
		summary = Analyzer("pyEDAA.Reports", directory, options=Options(countFields=False, countVariables=False)).Analyze()
		result = analyze(sorted(directory.rglob("*.py")), show_progress=False)

		for path, fileResult in result.files():
			count = fileResult.count_aggregate()
			file = summary.GetOrAddFile(Path(path).relative_to(directory))
			self.assertEqual(count.needed, file.Counters.Expected, f"{file.Path}: expected")
			self.assertEqual(count.found, file.Counters.Covered, f"{file.Path}: covered")

		self.assertEqual(len(result.files()), summary.FileCount)

	@skipIf(find_spec("sphinx") is None, "Sphinx isn't installed.")
	def test_SphinxAutodoc(self) -> None:
		"""A field or variable is documented, if Sphinx' autodoc finds non-empty documentation for it."""
		from sphinx.pycode import ModuleAnalyzer

		with TemporaryDirectory() as directory:
			(Path(directory) / "Attributes.py").write_bytes(FIXTURE.read_bytes())
			module = Analyzer("Attributes", Path(directory)).Analyze().Items[0]["Attributes"]

		oracle = {
			key for key, lines in ModuleAnalyzer.for_file(str(FIXTURE), "Attributes").find_attr_docs().items()
			if any(line.strip() != "" for line in lines)
		}
		items = [item for item in module.IterateElements() if item.Kind in ATTRIBUTES]
		for item in items:
			scope = item.Parent.QualifiedName.removeprefix("Attributes.Attributes").removeprefix(".")
			with self.subTest(item=item.QualifiedName):
				self.assertEqual((scope, item.Name) in oracle, CoverageState.Documented in item.Status)

		self.assertEqual(
			{
				"T", "Length", "MAXIMUM", "first", "second", "chained", "table", "afterSemicolon", "conditional", "guarded",
				"Red", "_name", "_size", "_initialized", "_value"
			} | ({"formatted"} if version_info < (3, 12) else set()),
			{item.Name for item in items if CoverageState.Documented in item.Status}
		)
		self.assertEqual(27, len(items))
