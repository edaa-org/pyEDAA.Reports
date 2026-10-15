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
A Python source file, read once for the documentation coverage: its lines, syntax tree and tokens.

The tokens hold the comments, which document a field or variable for Sphinx' autodoc, or excuse a missing doc-string
for docstr_coverage.
"""
from __future__                                 import annotations

from ast                                        import AsyncFunctionDef, ClassDef, FunctionDef, Module, get_docstring
from ast                                        import parse, stmt
from io                                         import StringIO
from pathlib                                    import Path
from re                                         import Pattern, compile as re_compile
from tokenize                                   import COMMENT, ENDMARKER, NAME, NEWLINE, NL, NUMBER, OP, STRING
from tokenize                                   import TokenInfo, generate_tokens, open as tokenize_open
from typing                                     import ClassVar

from pyTooling.Common                           import getFullyQualifiedName
from pyTooling.Decorators                       import export, readonly
from pyTooling.MetaClasses                      import ExtendedType

from pyEDAA.Reports.DocumentationCoverage       import CoverageState


@export
class SourceFile(metaclass=ExtendedType, slots=True):
	"""
	A Python source file, read once: its lines, its syntax tree, and its tokens, which hold the comments.
	"""

	_COMMENT:   ClassVar[Pattern[str]] = re_compile(r"^\s*#: ?(.*)\r?\n?$")                         #: Sphinx' comment.
	_INHERITED: ClassVar[Pattern[str]] = re_compile(r"#\s*docstr-coverage\s*:\s*inherit(ed)?\s*")    #: Inherited.
	_EXCUSED:   ClassVar[Pattern[str]] = re_compile(r"#\s*docstr-coverage\s*:\s*excuse(d)?\s* `.*`\s*")  #: Excused.

	_path:       Path                        #: Path to the source file.
	_lines:      list[str]                   #: The source's lines, without line endings.
	_tree:       Module                      #: The source's syntax tree.
	_tokens:     list[TokenInfo]             #: The source's tokens.
	_positions:  dict[tuple[int, int], int]  #: The index of the token starting at a line and column.
	_lineStarts: dict[int, int]              #: The index of the first token starting in a line.
	_closings:   dict[int, int]              #: The index of the closing bracket of an opening bracket.

	def __init__(self, path: Path, lines: list[str], tree: Module, tokens: list[TokenInfo]) -> None:
		"""
		Initializes a read source file, and indexes its tokens.

		:param path:        Path to the source file.
		:param lines:       The source's lines, without line endings.
		:param tree:        The source's syntax tree.
		:param tokens:      The source's tokens.
		:raises ValueError: If parameter ``path`` is ``None``.
		:raises TypeError:  If parameter ``path`` isn't of type :class:`~pathlib.Path`.
		:raises ValueError: If parameter ``lines`` is ``None``.
		:raises TypeError:  If parameter ``lines`` isn't of type :class:`list`.
		:raises ValueError: If parameter ``tree`` is ``None``.
		:raises TypeError:  If parameter ``tree`` isn't of type :class:`ast.Module`.
		:raises ValueError: If parameter ``tokens`` is ``None``.
		:raises TypeError:  If parameter ``tokens`` isn't of type :class:`list`.
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

		self._path =       path
		self._lines =      lines
		self._tree =       tree
		self._tokens =     tokens
		self._positions =  {}
		self._lineStarts = {}
		self._closings =   {}

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
		Read a source file in its declared encoding, and parse it.

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
			raise ValueError(f"Parameter 'path' is None.")
		elif not isinstance(path, Path):
			ex = TypeError(f"Parameter 'path' is not of type 'Path'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(path)}'.")
			raise ex

		with tokenize_open(path) as file:
			source = file.read()

		tree = parse(source, filename=str(path))
		tokens = list(generate_tokens(StringIO(source).readline))

		return cls(path, source.split("\n"), tree, tokens)

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

	def DocumentationState(self, node: Module | ClassDef | FunctionDef | AsyncFunctionDef) -> CoverageState:
		"""
		Return how a module, class or function is documented: by a non-empty doc-string, or excused by a comment.

		docstr_coverage's comment, which excuses a class or function, is the first comment above its declaration,
		skipping blank lines and the lines of decorators.

		:param node: The module, class or function.
		:returns:    :attr:`~pyEDAA.Reports.DocumentationCoverage.CoverageState.Documented`,
		             :attr:`~pyEDAA.Reports.DocumentationCoverage.CoverageState.Inherited` or
		             :attr:`~pyEDAA.Reports.DocumentationCoverage.CoverageState.Excused`, each with
		             :attr:`~pyEDAA.Reports.DocumentationCoverage.CoverageState.Covered`; otherwise
		             :attr:`~pyEDAA.Reports.DocumentationCoverage.CoverageState.Undocumented`.
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
