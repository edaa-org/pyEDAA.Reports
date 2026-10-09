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
pyucis' dialect of the UCIS XML interchange format: the elements in no namespace.

`pyucis <https://github.com/fvutils/pyucis>`__ writes UCIS XML with ``pyucis convert`` and for tools, which use it -
e.g. PyVSC's ``vsc.write_coverage_db("coverage.xml")``. Its root ``<UCIS>`` binds the prefix ``ucis`` to the XML Schema
instance namespace, but no element uses it: the elements are in no namespace, not in the namespace ``UCIS`` the
standard's schema declares. A report is validated against :file:`PyUCIS-1.0.xsd`: the standard's schema without a
target namespace. The format's model and the conversion to the common model are those of
:mod:`pyEDAA.Reports.CodeCoverage.UCIS`.

.. rubric:: Example

.. code-block:: Python

   from pathlib import Path
   from pyEDAA.Reports.CodeCoverage.UCIS.PyUCIS import Document

   report = Document(Path("coverage.xml"), analyzeAndConvert=True)
   summary = report.ToCoverageSummary(mergeInstances=True)
   for file in summary.IterateFiles():
     print(f"{file.Path}: {file.LineCoverage:.1%}")
"""
from typing                           import ClassVar, Optional as Nullable

from pyTooling.Decorators             import export

from pyEDAA.Reports.CodeCoverage.UCIS import Document as ucis_Document, FormatVersion


__all__ = ["SCHEMAS"]

SCHEMAS: dict[FormatVersion, str] = {
	FormatVersion.Version1_0: "PyUCIS-1.0.xsd"
}  #: Per format version, the XML schema a report of that version is validated against.


@export
class Document(ucis_Document):
	"""
	A UCIS XML code coverage report as pyucis writes it: read into the format's model, and converted to the common
	model.
	"""

	_NAMESPACE: ClassVar[Nullable[str]] =            None     #: The elements are in no namespace.
	_SCHEMAS:   ClassVar[dict[FormatVersion, str]] = SCHEMAS  #: Per format version, the XML schema to validate with.
