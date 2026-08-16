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
The schemas describe what the frameworks emit.

Each schema in :file:`pyEDAA/Reports/Resources` was reverse-engineered from real output, so the reference reports in
:file:`tests/data/JUnit` are the ground truth: a schema that rejects one of them describes the format wrongly. The
reader has to agree with the schema too - it is the same claim about the format, written twice.
"""
from typing   import ClassVar
from unittest import TestCase as ut_TestCase

from pyTooling.Decorators import readonly

from . import DIALECTS, TESTSUITE_ROOTED_FILES, Dialect


class SchemaMixin:
	"""
	Classic mixin: the schema of a dialect accepts every report that framework produced.

	It is not created by :class:`~pyTooling.MetaClasses.ExtendedType`, because :class:`~unittest.TestCase` isn't
	either and mixing the two requires ``__slots__`` on every base class.
	"""

	_dialectName: ClassVar[str]

	@readonly
	def Dialect(self) -> Dialect:
		"""
		Read-only property to return the dialect under test, looked up by :attr:`_dialectName`.

		:returns: The dialect under test.
		"""
		return DIALECTS[self._dialectName]

	def test_ReferenceOutputIsValid(self) -> None:
		dialect = self.Dialect
		schema = dialect.Schema()

		for referenceFile in dialect.ReferenceFiles:
			with self.subTest(file=referenceFile.name):
				self.assertTrue(referenceFile.exists(), f"Reference file '{referenceFile}' is missing.")
				schema.validate(str(referenceFile))

	def test_TheReaderAcceptsWhatTheSchemaAccepts(self) -> None:
		dialect = self.Dialect

		for referenceFile in dialect.ReferenceFiles:
			with self.subTest(file=referenceFile.name):
				dialect.DocumentClass(referenceFile, analyzeAndConvert=True)


class AntJUnit4(SchemaMixin, ut_TestCase):
	_dialectName = "Ant-JUnit4"


class CTestJUnit(SchemaMixin, ut_TestCase):
	_dialectName = "CTest-JUnit"


class GoogleTestJUnit(SchemaMixin, ut_TestCase):
	_dialectName = "GoogleTest-JUnit"


class PyTestJUnit(SchemaMixin, ut_TestCase):
	_dialectName = "pyTest-JUnit"


class AnyJUnit(SchemaMixin, ut_TestCase):
	"""
	``Any-JUnit`` is the permissive dialect, so it has to accept what the specific ones accept.

	It currently does not: its schema declares only ``<testsuites>`` as a root element, while ``Ant-JUnit4`` and
	``CTest-JUnit`` are rooted at ``<testsuite>`` - and so are VUnit's reports.
	"""

	_dialectName = "Any-JUnit"

	def test_ATestsuiteRootedReportIsStillRejected(self) -> None:
		"""Known gap: when this starts failing, Any-JUnit has been widened and the expectation can go."""
		schema = self.Dialect.Schema()
		rejected = [*TESTSUITE_ROOTED_FILES, DIALECTS["Ant-JUnit4"].ReferenceFiles[0]]

		for referenceFile in rejected:
			with self.subTest(file=referenceFile.name):
				with self.assertRaises(Exception, msg="Any-JUnit accepts a <testsuite> root now - drop this expectation."):
					schema.validate(str(referenceFile))

	def test_TheReaderRejectsATestsuiteRootedReportToo(self) -> None:
		"""Known gap, reader side: it agrees with the schema, so both move together."""
		for referenceFile in TESTSUITE_ROOTED_FILES:
			with self.subTest(file=referenceFile.name):
				with self.assertRaises(Exception):
					self.Dialect.DocumentClass(referenceFile, analyzeAndConvert=True)
