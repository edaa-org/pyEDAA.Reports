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
"""Unit tests of the functional coverage model: the base-class of a report format's document."""
from pathlib                           import Path

from pyTooling.MetaClasses             import AbstractClassError
from pyTooling.Testing                 import Testcase

from pyEDAA.Reports.FunctionalCoverage import Document, FunctionalCoverageReport


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


class FormatDocument(Document):
	"""A report format's document, which converts to an empty report."""

	def Analyze(self) -> None:
		"""Nothing to read."""

	def Convert(self) -> None:
		"""Nothing to convert."""

	def ConvertToFunctionalCoverageReport(self) -> FunctionalCoverageReport:
		"""
		Return an empty report named after the file.

		:returns: The report.
		"""
		return FunctionalCoverageReport(self._path.stem)


class Documents(Testcase):
	def test_Abstract(self) -> None:
		with self.assertRaises(AbstractClassError):
			_ = Document(Path("TbStream_SendGetRandom1_cov.yml"))

	def test_Document(self) -> None:
		document = FormatDocument(Path("TbStream_SendGetRandom1_cov.yml"))

		self.assertEqual(Path("TbStream_SendGetRandom1_cov.yml"), document.ReportFile)
		self.assertIsNone(document.AnalysisDuration)
		self.assertIsNone(document.ModelConversionDuration)
		self.assertEqual("TbStream_SendGetRandom1_cov", document.ConvertToFunctionalCoverageReport().Name)

	def test_ReportFile(self) -> None:
		with self.assertRaises(ValueError) as context:
			_ = FormatDocument(None)
		self.assertEqual("Parameter 'reportFile' is None.", str(context.exception))

		with self.assertRaises(TypeError) as context:
			_ = FormatDocument("TbStream_SendGetRandom1_cov.yml")
		self.assertEqual("Parameter 'reportFile' is not of type 'Path'.", str(context.exception))
		self.assertEqual(["Got type 'str'."], context.exception.__notes__)
