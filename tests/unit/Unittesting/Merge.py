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
# Copyright 2024-2024 Electronic Design Automation Abstraction (EDA²)                                                  #
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
from pathlib  import Path
from time     import perf_counter_ns
from typing   import List
from unittest import TestCase as ut_TestCase

from pyEDAA.Reports.Unittesting import Testsuite, MergedTestsuiteSummary
from pyEDAA.Reports.Unittesting.JUnit import JUnitDocument


class PyTooling(ut_TestCase):
	def merge(self, junitDocuments: List[JUnitDocument], parsingDuration: float):
		print()
		print(f"Merging generic testsuites ...")
		startMerging = perf_counter_ns()
		merged = MergedTestsuiteSummary("PlatformTesting")
		for summary in junitDocuments:
			print(f"  merging {summary.Path}")
			merged.Merge(summary)
		endMerging = perf_counter_ns()
		mergingDuration = (endMerging - startMerging) / 1e9

		print()
		print(f"Aggregating datapoints in testsuite ...")
		startAggregate = perf_counter_ns()
		merged.Aggregate()
		endAggregate = perf_counter_ns()
		aggregateDuration = (endAggregate - startAggregate) / 1e9

		print()
		print(f"Parsing:    {parsingDuration:.3f} ms")
		print(f"Merging:    {mergingDuration:.3f} ms")
		print(f"Aggregate:  {aggregateDuration:.3f} ms")

	def test_PlatformTesting(self) -> None:
		print()

		junitDocuments: List[JUnitDocument] = []

		directory = Path("tests/data/JUnit/pytest.pyTooling")
		print(f"Reading platform testing summary files from '{directory}' ...")
		files = directory.glob("PlatformTesting-*.xml")
		startParsing = perf_counter_ns()
		for file in files:
			print(f"  Parsing {file}")
			junitDocuments.append(JUnitDocument(file))
		endParsing = perf_counter_ns()
		parsingDuration = (endParsing - startParsing) / 1e9

		self.merge(junitDocuments, parsingDuration)

	def test_Unittesting(self) -> None:
		print()

		junitDocuments: List[JUnitDocument] = []

		directory = Path("tests/data/JUnit/pytest.pyTooling")
		print(f"Reading platform testing summary files from '{directory}' ...")
		files = directory.glob("Unittesting-*.xml")
		startParsing = perf_counter_ns()
		for file in files:
			print(f"  Parsing {file}")
			junitDocuments.append(JUnitDocument(file))
		endParsing = perf_counter_ns()
		parsingDuration = (endParsing - startParsing) / 1e9

		self.merge(junitDocuments, parsingDuration)
