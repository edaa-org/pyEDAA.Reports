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
"""Unit tests of the documentation coverage model: kinds, states, both hierarchies, and aggregation."""
from pathlib                              import Path

from pyEDAA.Reports.DocumentationCoverage import CoverageCounters, CoverageState, Directory, DocCoverageError
from pyEDAA.Reports.DocumentationCoverage import DocumentationReport, File, Item, ItemCategory, ItemKind
from pyTooling.Testing                    import Testcase


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


DOCUMENTED =   CoverageState.Documented | CoverageState.Covered  #: State of a documented item.
UNDOCUMENTED = CoverageState.Undocumented                        #: State of an undocumented item.


class Kinds(Testcase):
	def test_ItemKind_Parse(self) -> None:
		self.assertIs(ItemKind.Method, ItemKind.Parse("method"))
		self.assertIs(ItemKind.EnumerationMember, ItemKind.Parse("enumeration-member"))
		self.assertIs(ItemKind.Other, ItemKind.Parse(None))
		self.assertIs(ItemKind.Other, ItemKind.DEFAULT)

		with self.assertRaises(ValueError) as context:
			_ = ItemKind.Parse("subroutine")

		self.assertEqual("'subroutine' is not a valid ItemKind.", str(context.exception))

	def test_ItemKind_Category(self) -> None:
		"""Every kind belongs to a category."""
		self.assertTrue(all(isinstance(kind.Category, ItemCategory) for kind in ItemKind))
		self.assertIs(ItemCategory.Container, ItemKind.Entity.Category)
		self.assertIs(ItemCategory.Type, ItemKind.TypeAlias.Category)
		self.assertIs(ItemCategory.Callable, ItemKind.Destructor.Category)
		self.assertIs(ItemCategory.Field, ItemKind.EnumerationMember.Category)
		self.assertIs(ItemCategory.Variable, ItemKind.Signal.Category)
		self.assertIs(ItemCategory.Variable, ItemKind.FileObject.Category)
		self.assertIs(ItemCategory.Constant, ItemKind.Constant.Category)
		self.assertIs(ItemCategory.Generic, ItemKind.Generic.Category)
		self.assertIs(ItemCategory.Generic, ItemKind.TypeParameter.Category)
		self.assertIs(ItemCategory.Parameter, ItemKind.Port.Category)
		self.assertIs(ItemCategory.Other, ItemKind.Other.Category)
		self.assertIs(ItemCategory.Other, ItemKind.DEFAULT.Category)

	def test_ItemCategory_Parse(self) -> None:
		self.assertIs(ItemCategory.Callable, ItemCategory.Parse("callable"))
		self.assertIs(ItemCategory.Other, ItemCategory.Parse(""))


class Counters(Testcase):
	def test_Zero(self) -> None:
		counters = CoverageCounters()

		self.assertEqual(0, counters.Total)
		self.assertEqual(0, counters.Expected)
		self.assertEqual(0, counters.Covered)
		self.assertEqual(0, counters.Uncovered)
		self.assertEqual(0, counters.Ignored)
		self.assertEqual(0, counters.Excluded)
		self.assertEqual(1.0, counters.Coverage)
		self.assertEqual("<CoverageCounters 0/0, ignored 0, excluded 0: 100.0%>", repr(counters))

	def test_States(self) -> None:
		"""Each state is counted once, as the flags read in order: empty, excluded, ignored, covered."""
		module = Item("module", ItemKind.Module, CoverageState.Empty)
		for name, state in (
			("documented",   DOCUMENTED),
			("undocumented", UNDOCUMENTED),
			("inherited",    CoverageState.Inherited | CoverageState.Covered),
			("excused",      CoverageState.Excused | CoverageState.Covered),
			("ignored",      CoverageState.Ignored | UNDOCUMENTED),
			("excluded",     CoverageState.Excluded | CoverageState.Ignored | DOCUMENTED),
			("empty",        CoverageState.Empty | CoverageState.Excluded),
		):
			Item(name, ItemKind.Function, state, parent=module)

		module.Aggregate()

		self.assertEqual(6, module.Counters.Total)
		self.assertEqual(4, module.Counters.Expected)
		self.assertEqual(3, module.Counters.Covered)
		self.assertEqual(1, module.Counters.Uncovered)
		self.assertEqual(1, module.Counters.Ignored)
		self.assertEqual(1, module.Counters.Excluded)
		self.assertEqual(0.75, module.Counters.Coverage)
		self.assertEqual("<CoverageCounters 3/4, ignored 1, excluded 1: 75.0%>", repr(module.Counters))


class ItemInstantiation(Testcase):
	def test_Item(self) -> None:
		item = Item("Circle", ItemKind.Class, DOCUMENTED)

		self.assertIsNone(item.Parent)
		self.assertIsNone(item.Root)
		self.assertEqual("Circle", item.Name)
		self.assertIs(ItemKind.Class, item.Kind)
		self.assertIs(ItemCategory.Type, item.Category)
		self.assertEqual(DOCUMENTED, item.Status)
		self.assertIsNone(item.File)
		self.assertIsNone(item.StartLine)
		self.assertIsNone(item.EndLine)
		self.assertEqual(0, len(item))
		self.assertEqual("Circle", item.QualifiedName)
		self.assertEqual("<Item class Circle: 100.0%>", repr(item))

	def test_Item_Lines(self) -> None:
		file = File(Path("Shapes.py"))
		item = Item("Circle", ItemKind.Class, DOCUMENTED, file=file, startLine=3, endLine=10)

		self.assertIs(file, item.File)
		self.assertEqual(3, item.StartLine)
		self.assertEqual(10, item.EndLine)
		self.assertEqual([item], file.Items)

	def test_Name(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = Item(None, ItemKind.Class, DOCUMENTED)
		self.assertEqual("Parameter 'name' is None.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = Item(1, ItemKind.Class, DOCUMENTED)
		self.assertEqual("Parameter 'name' is not of type 'str'.", str(context.exception))

		with self.assertRaises(ValueError) as context:
			_ = Item("", ItemKind.Class, DOCUMENTED)
		self.assertEqual("Parameter 'name' is empty.", str(context.exception))

	def test_Kind(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = Item("Circle", None, DOCUMENTED)
		self.assertEqual("Parameter 'kind' is None.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = Item("Circle", "class", DOCUMENTED)
		self.assertEqual("Parameter 'kind' is not of type 'ItemKind'.", str(context.exception))

	def test_Status(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = Item("Circle", ItemKind.Class, None)
		self.assertEqual("Parameter 'status' is None.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = Item("Circle", ItemKind.Class, 8)
		self.assertEqual("Parameter 'status' is not of type 'CoverageState'.", str(context.exception))

		with self.assertRaises(ValueError) as context:
			_ = Item("Circle", ItemKind.Class, CoverageState.Documented & CoverageState.Covered)
		self.assertEqual("Parameter 'status' is 'Unknown'.", str(context.exception))

	def test_File(self) -> None:
		with self.assertRaises(TypeError) as context:
			_ = Item("Circle", ItemKind.Class, DOCUMENTED, file=Path("Shapes.py"))
		self.assertEqual("Parameter 'file' is not of type 'File'.", str(context.exception))

	def test_Lines(self) -> None:
		with self.assertRaises(TypeError) as context:
			_ = Item("Circle", ItemKind.Class, DOCUMENTED, startLine="3")
		self.assertEqual("Parameter 'startLine' is not of type 'int'.", str(context.exception))

		with self.assertRaises(ValueError) as context:
			_ = Item("Circle", ItemKind.Class, DOCUMENTED, startLine=0)
		self.assertEqual("Parameter 'startLine' is less than 1.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = Item("Circle", ItemKind.Class, DOCUMENTED, endLine=10.0)
		self.assertEqual("Parameter 'endLine' is not of type 'int'.", str(context.exception))

		with self.assertRaises(ValueError) as context:
			_ = Item("Circle", ItemKind.Class, DOCUMENTED, startLine=10, endLine=3)
		self.assertEqual("Parameter 'endLine' is before parameter 'startLine', or less than 1.", str(context.exception))

		with self.assertRaises(ValueError) as context:
			_ = Item("Circle", ItemKind.Class, DOCUMENTED, endLine=0)
		self.assertEqual("Parameter 'endLine' is before parameter 'startLine', or less than 1.", str(context.exception))

	def test_Parent(self) -> None:
		with self.assertRaises(TypeError) as context:
			_ = Item("Circle", ItemKind.Class, DOCUMENTED, parent=File(Path("Shapes.py")))
		self.assertEqual("Parameter 'parent' is not of type 'Item' or 'DocumentationReport'.", str(context.exception))


class ItemHierarchy(Testcase):
	def test_Children(self) -> None:
		report = DocumentationReport(Path("myPackage"))
		package = Item("myPackage", ItemKind.Package, DOCUMENTED, parent=report)
		module = Item("Shapes", ItemKind.Module, DOCUMENTED, parent=package)
		getter = Item("Radius", ItemKind.Property, DOCUMENTED, parent=module)
		setter = Item("Radius", ItemKind.Property, CoverageState.Ignored | UNDOCUMENTED, parent=module)

		self.assertEqual([package], report.Items)
		self.assertIs(report, package.Root)
		self.assertIs(report, setter.Root)
		self.assertEqual("myPackage.Shapes.Radius", setter.QualifiedName)
		self.assertEqual(2, len(module))
		self.assertEqual([getter, setter], list(module))
		self.assertIn("Radius", module)
		self.assertNotIn("Diameter", module)
		self.assertIs(getter, module["Radius"])

		with self.assertRaises(KeyError) as context:
			_ = module["Diameter"]
		self.assertEqual("\"Item 'myPackage.Shapes' contains no item 'Diameter'.\"", str(context.exception))

	def test_IterateDescendants(self) -> None:
		package = Item("myPackage", ItemKind.Package, DOCUMENTED)
		module =  Item("Shapes", ItemKind.Module, DOCUMENTED, parent=package)
		circle =  Item("Circle", ItemKind.Class, DOCUMENTED, parent=module)
		getter =  Item("Radius", ItemKind.Property, DOCUMENTED, parent=circle)
		square =  Item("Square", ItemKind.Class, UNDOCUMENTED, parent=module)

		self.assertEqual([module, circle, getter, square], list(package.IterateDescendants()))
		self.assertEqual([circle, square], list(package.IterateDescendants(lambda item: item.Kind is ItemKind.Class)))
		self.assertEqual([getter], list(package.IterateDescendants(lambda item: item.Kind is ItemKind.Property)))
		self.assertEqual([], list(getter.IterateDescendants()))

	def test_ParentSetter(self) -> None:
		report = DocumentationReport(Path("myPackage"))
		package = Item("myPackage", ItemKind.Package, DOCUMENTED)
		module = Item("Shapes", ItemKind.Module, DOCUMENTED, parent=package)

		package.Parent = report

		self.assertIs(report, package.Parent)
		self.assertIs(report, package.Root)
		self.assertIs(report, module.Root)
		self.assertEqual([package], report.Items)

		with self.assertRaises(ValueError) as context:
			module.Parent = None
		self.assertEqual("Parameter 'parent' is None.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			module.Parent = Directory(Path("myPackage"))
		self.assertEqual("Parameter 'parent' is not of type 'Item' or 'DocumentationReport'.", str(context.exception))

	def test_RootHasNoParent(self) -> None:
		report = DocumentationReport(Path("myPackage"))

		with self.assertRaises(TypeError) as context:
			report.Parent = Directory(Path("other"))
		self.assertEqual(
			"A 'pyEDAA.Reports.DocumentationCoverage.DocumentationReport' has no parent.", str(context.exception)
		)


class Files(Testcase):
	def test_GetOrAddFile(self) -> None:
		report = DocumentationReport(Path("myPackage"))
		file = report.GetOrAddFile(Path("Units/Length.py"))

		self.assertIs(file, report.GetOrAddFile(Path("Units/Length.py")))
		self.assertEqual(Path("Units/Length.py"), file.Path)
		self.assertEqual(Path("."), report.Path)
		self.assertIs(report, file.Root)
		self.assertEqual(1, report.FileCount)
		self.assertEqual([Path("Units")], list(report.Directories))
		self.assertEqual(Path("Length.py"), file.Name)
		self.assertEqual("<File Units/Length.py: 0 items, 100.0%>", repr(file))
		self.assertEqual("<Directory Units: 1 files, 100.0%>", repr(report.Directories[Path("Units")]))

	def test_ParentSetter(self) -> None:
		report =   DocumentationReport(Path("myPackage"))
		units =    Directory(Path("Units"))
		length =   units.GetOrAddFile(Path("Length.py"))
		imperial = units.GetOrAddFile(Path("Imperial/Mile.py"))

		self.assertIsNone(length.Root)
		self.assertIsNone(imperial.Root)

		units.Parent = report

		self.assertIs(report, units.Parent)
		self.assertIs(units, report.Directories[Path("Units")])
		self.assertIs(report, units.Root)
		self.assertIs(report, units.Directories[Path("Imperial")].Root)
		self.assertIs(report, length.Root)
		self.assertIs(report, imperial.Root)
		self.assertEqual(Path("Units/Imperial/Mile.py"), imperial.Path)

	def test_IterateFiles(self) -> None:
		report = DocumentationReport(Path("myPackage"))
		for path in ("Units/Length.py", "__init__.py", "Units/__init__.py", "Shapes.py"):
			report.GetOrAddFile(Path(path))

		self.assertEqual(
			[Path("Shapes.py"), Path("__init__.py"), Path("Units/Length.py"), Path("Units/__init__.py")],
			[file.Path for file in report.IterateFiles()]
		)

	def test_GetOrAddFile_Errors(self) -> None:
		report = DocumentationReport(Path("myPackage"))
		report.GetOrAddFile(Path("Shapes.py"))

		with self.assertRaises(ValueError) as context:
			report.GetOrAddFile(None)
		self.assertEqual("Parameter 'path' is None.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			report.GetOrAddFile("Shapes.py")
		self.assertEqual("Parameter 'path' is not of type 'Path'.", str(context.exception))

		with self.assertRaises(ValueError) as context:
			report.GetOrAddFile(Path("."))
		self.assertEqual("Parameter 'path' names no file.", str(context.exception))

		with self.assertRaises(DocCoverageError) as context:
			report.GetOrAddFile(Path("Shapes.py/Circle.py"))
		self.assertEqual("'Shapes.py' is a file, not a directory.", str(context.exception))

	def test_DuplicateName(self) -> None:
		directory = Directory(Path("myPackage"))
		File(Path("Shapes.py"), parent=directory)

		with self.assertRaises(DocCoverageError) as context:
			_ = Directory(Path("Shapes.py"), parent=directory)
		self.assertEqual("Directory 'myPackage' already contains 'Shapes.py'.", str(context.exception))

	def test_Name(self) -> None:
		self.assertEqual(Path("Units"), Directory(Path("Units")).Name)

		with self.assertRaises(ValueError) as context:
			_ = File(None)
		self.assertEqual("Parameter 'name' is None.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = Directory("Units")
		self.assertEqual("Parameter 'name' is not of type 'Path'.", str(context.exception))

		for name in ("", "."):
			with self.subTest(name=name), self.assertRaises(ValueError) as context:
				_ = DocumentationReport(Path(name))
			self.assertEqual("Parameter 'name' is empty.", str(context.exception))

		with self.assertRaises(ValueError) as context:
			_ = File(Path("Units/Length.py"))
		self.assertEqual("Parameter 'name' has more than one component.", str(context.exception))


class Aggregation(Testcase):
	def _Build(self) -> DocumentationReport:
		"""
		Build an analysis of a package ``myPackage`` with a module ``Shapes``.

		* ``myPackage/__init__.py``: the documented package and an undocumented variable.
		* ``myPackage/Shapes.py``: the documented module, a documented class with a documented method, an undocumented
		  field and an ignored setter, and a nested class with an excluded field.
		* A namespace package ``myPackage.Plugins`` without a file, and nothing to document.

		:returns: The report, aggregated.
		"""
		report = DocumentationReport(Path("myPackage"))
		initFile = report.GetOrAddFile(Path("__init__.py"))
		shapesFile = report.GetOrAddFile(Path("Shapes.py"))

		package = Item("myPackage", ItemKind.Package, DOCUMENTED, file=initFile, parent=report)
		Item("VERSION", ItemKind.Constant, UNDOCUMENTED, file=initFile, parent=package)
		module = Item("Shapes", ItemKind.Module, DOCUMENTED, file=shapesFile, parent=package)
		circle = Item("Circle", ItemKind.Class, DOCUMENTED, file=shapesFile, parent=module)
		Item("Area", ItemKind.Method, DOCUMENTED, file=shapesFile, parent=circle)
		Item("_radius", ItemKind.Field, UNDOCUMENTED, file=shapesFile, parent=circle)
		Item("Radius", ItemKind.Property, CoverageState.Ignored | UNDOCUMENTED, file=shapesFile, parent=circle)
		nested = Item("Center", ItemKind.Class, UNDOCUMENTED, file=shapesFile, parent=circle)
		Item("_x", ItemKind.Field, CoverageState.Excluded | UNDOCUMENTED, file=shapesFile, parent=nested)
		Item("Plugins", ItemKind.Package, CoverageState.Empty, parent=package)

		report.Aggregate()
		return report

	def test_Item(self) -> None:
		"""An item counts itself and the items below it; a nested class aggregates into its class."""
		report = self._Build()
		circle = report.Items[0]["Shapes"]["Circle"]
		nested = circle["Center"]

		self.assertEqual(1, nested.Counters.Expected)
		self.assertEqual(0, nested.Counters.Covered)
		self.assertEqual(1, nested.Counters.Excluded)

		self.assertEqual(6, circle.Counters.Total)
		self.assertEqual(4, circle.Counters.Expected)
		self.assertEqual(2, circle.Counters.Covered)
		self.assertEqual(1, circle.Counters.Ignored)
		self.assertEqual(1, circle.Counters.Excluded)
		self.assertEqual(0.5, circle.Counters.Coverage)

	def test_Package(self) -> None:
		"""A package counts its own items and its modules; a package with nothing to document isn't counted."""
		report = self._Build()
		package = report.Items[0]

		self.assertEqual(9, package.Counters.Total)
		self.assertEqual(7, package.Counters.Expected)
		self.assertEqual(4, package.Counters.Covered)
		self.assertEqual(3, package.Counters.Uncovered)
		self.assertEqual(0, package["Plugins"].Counters.Total)

	def test_Files(self) -> None:
		"""A file counts the own states of the items declared in it; a directory sums its files."""
		report = self._Build()
		initFile = report.Files[Path("__init__.py")]
		shapesFile = report.Files[Path("Shapes.py")]

		self.assertEqual(2, initFile.Counters.Expected)
		self.assertEqual(1, initFile.Counters.Covered)
		self.assertEqual(7, shapesFile.Counters.Total)
		self.assertEqual(5, shapesFile.Counters.Expected)
		self.assertEqual(3, shapesFile.Counters.Covered)

	def test_Report(self) -> None:
		"""The report sums its top-level items, which here equals the sum of its files; nothing measured its analysis."""
		report = self._Build()

		self.assertEqual(9, report.Counters.Total)
		self.assertEqual(7, report.Counters.Expected)
		self.assertEqual(4, report.Counters.Covered)
		self.assertAlmostEqual(4 / 7, report.Counters.Coverage)
		self.assertEqual(2, report.FileCount)
		self.assertIsNone(report.AnalysisDuration)

	def test_ReportWithoutFiles(self) -> None:
		"""The report counts an item without a file, its files don't."""
		report = DocumentationReport(Path("Design"))
		library = Item("work", ItemKind.Library, DOCUMENTED, parent=report)
		Item("Counter", ItemKind.Entity, UNDOCUMENTED, parent=library)

		report.Aggregate()

		self.assertEqual(2, report.Counters.Expected)
		self.assertEqual(1, report.Counters.Covered)
		self.assertEqual(0, report.FileCount)

	def test_Categories(self) -> None:
		"""The counters break down by the category of the items' kinds."""
		report = self._Build()
		categories = report.Categories

		self.assertEqual(
			{ItemCategory.Container, ItemCategory.Constant, ItemCategory.Type, ItemCategory.Callable, ItemCategory.Field},
			set(categories)
		)
		self.assertEqual(2, categories[ItemCategory.Container].Expected)
		self.assertEqual(2, categories[ItemCategory.Container].Covered)
		self.assertEqual(1, categories[ItemCategory.Constant].Uncovered)
		self.assertEqual(2, categories[ItemCategory.Type].Expected)
		self.assertEqual(1, categories[ItemCategory.Callable].Expected)
		self.assertEqual(1, categories[ItemCategory.Callable].Ignored)
		self.assertEqual(1, categories[ItemCategory.Field].Expected)
		self.assertEqual(1, categories[ItemCategory.Field].Excluded)
		self.assertEqual(
			report.Counters.Expected, sum(counters.Expected for counters in categories.values())
		)

		shapesFile = report.Files[Path("Shapes.py")]
		self.assertNotIn(ItemCategory.Constant, shapesFile.Categories)
		self.assertEqual(2, shapesFile.Categories[ItemCategory.Field].Total)

	def test_Reaggregate(self) -> None:
		"""Aggregating again computes the same counters."""
		report = self._Build()
		report.Aggregate()

		self.assertEqual(7, report.Counters.Expected)
		self.assertEqual(7, report.Items[0].Counters.Expected)
		self.assertEqual(5, report.Files[Path("Shapes.py")].Counters.Expected)
