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
"""Regression tests of the reader of Python source code: compared with docstr_coverage and Sphinx' autodoc."""
from importlib.util                              import find_spec
from pathlib                                     import Path
from sys                                         import version_info
from tempfile                                    import TemporaryDirectory
from unittest                                    import skipIf

from pyEDAA.Reports.DocumentationCoverage        import CoverageState, ItemKind
from pyEDAA.Reports.DocumentationCoverage.Python import Analyzer, CountedItems
from pyTooling.Testing                           import Testcase


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


FIXTURE =    Path("tests/data/DocumentationCoverage/Attributes.py")  #: Fields and variables for the oracle.
ATTRIBUTES = (ItemKind.Field, ItemKind.EnumerationMember, ItemKind.Variable, ItemKind.Constant, ItemKind.TypeAlias,
              ItemKind.TypeVariable, ItemKind.Type)                  #: The kinds of fields and variables.


class Regression(Testcase):
	@skipIf(find_spec("docstr_coverage") is None, "docstr_coverage isn't installed.")
	def test_DocStrCoverage(self) -> None:
		"""Without fields and variables, the reader counts per file what docstr_coverage counts."""
		from docstr_coverage import analyze

		directory = Path("pyEDAA/Reports")
		report = Analyzer("pyEDAA.Reports", directory, countedItems=CountedItems.Protected | CountedItems.Private).Analyze()
		result = analyze(sorted(directory.rglob("*.py")), show_progress=False)

		for path, fileResult in result.files():
			count = fileResult.count_aggregate()
			file = report.GetOrAddFile(Path(path).relative_to(directory))
			self.assertEqual(count.needed, file.Counters.Expected, f"{file.Path}: expected")
			self.assertEqual(count.found, file.Counters.Covered, f"{file.Path}: covered")

		self.assertEqual(len(result.files()), report.FileCount)

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
		items = list(module.IterateDescendants(lambda item: item.Kind in ATTRIBUTES))
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
