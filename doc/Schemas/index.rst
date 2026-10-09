.. _SCHEMAS:

Schemas
#######

pyEDAA.Reports validates every file it reads against the schema of its format before converting it: an **XML schema**
or a **JSON Schema**. It ships the schemas of the code coverage formats - e.g. Cobertura's XML or coverage.py's JSON
report -, of the JUnit dialects and of Open Test Reporting; the schema of pyTooling's test report comes with pyTooling.
Each schema is listed here, the shipped ones with their full source, ready to read, to copy, or to download.

.. _SCHEMAS/Files:

Available schemas
*****************

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Schema
     - File
     - Read by
   * - :ref:`Any Cobertura <SCHEMAS/Any-Cobertura>`
     - :file:`Any-Cobertura.xsd`
     - :class:`pyEDAA.Reports.CodeCoverage.Cobertura.Document`
   * - :ref:`Cobertura 04 <SCHEMAS/Cobertura-04>`
     - :file:`Cobertura-04.xsd`
     - strict translation of Cobertura's DTD ``coverage-04.dtd``
   * - :ref:`coverage.py Cobertura <SCHEMAS/CoveragePy-Cobertura>`
     - :file:`CoveragePy-Cobertura.xsd`
     - :class:`pyEDAA.Reports.CodeCoverage.Cobertura.CoveragePyCobertura.Document`
   * - :ref:`NVC Cobertura <SCHEMAS/NVC-Cobertura>`
     - :file:`NVC-Cobertura.xsd`
     - :class:`pyEDAA.Reports.CodeCoverage.Cobertura.NVCCobertura.Document`
   * - :ref:`coverage.py JSON, format 2 <SCHEMAS/CoveragePy-2>`
     - :file:`CoveragePy-2.schema.json`
     - :class:`pyEDAA.Reports.CodeCoverage.CoveragePy.Document`
   * - :ref:`coverage.py JSON, format 3 <SCHEMAS/CoveragePy-3>`
     - :file:`CoveragePy-3.schema.json`
     - :class:`pyEDAA.Reports.CodeCoverage.CoveragePy.Document`
   * - :ref:`GHDL coverage 1.0.0 <SCHEMAS/GHDL-Coverage-1.0.0>`
     - :file:`GHDL-Coverage-1.0.0.schema.json`
     - :class:`pyEDAA.Reports.CodeCoverage.GHDL.Document`
   * - :ref:`UCIS 1.0 <SCHEMAS/UCIS-1.0>`
     - :file:`UCIS-1.0.xsd`
     - :class:`pyEDAA.Reports.CodeCoverage.UCIS.Document`, UCIS version 1.0
   * - :ref:`pyucis UCIS 1.0 <SCHEMAS/PyUCIS-1.0>`
     - :file:`PyUCIS-1.0.xsd`
     - :class:`pyEDAA.Reports.CodeCoverage.UCIS.PyUCIS.Document`, UCIS version 1.0
   * - :ref:`gcov JSON 1 <SCHEMAS/Gcov-1>`
     - :file:`Gcov-1.schema.json`
     - :class:`pyEDAA.Reports.CodeCoverage.Gcov.Document`, format version 1
   * - :ref:`gcov JSON 2 <SCHEMAS/Gcov-2>`
     - :file:`Gcov-2.schema.json`
     - :class:`pyEDAA.Reports.CodeCoverage.Gcov.Document`, format version 2
   * - :ref:`JaCoCo 1.1 <SCHEMAS/JaCoCo-1.1>`
     - :file:`JaCoCo-1.1.xsd`
     - :class:`pyEDAA.Reports.CodeCoverage.JaCoCo.Document`, format version 1.1
   * - :ref:`Any JUnit <SCHEMAS/Any-JUnit>`
     - :file:`Any-JUnit.xsd`
     - :class:`pyEDAA.Reports.Unittesting.JUnit.Document`
   * - :ref:`Ant + JUnit4 <SCHEMAS/Ant-JUnit4>`
     - :file:`Ant-JUnit4.xsd`
     - :class:`pyEDAA.Reports.Unittesting.JUnit.AntJUnit4.Document`
   * - :ref:`Catch2 JUnit <SCHEMAS/Catch2-JUnit>`
     - :file:`Catch2-JUnit.xsd`
     - :class:`pyEDAA.Reports.Unittesting.JUnit.Catch2JUnit.Document`
   * - :ref:`CTest JUnit <SCHEMAS/CTest-JUnit>`
     - :file:`CTest-JUnit.xsd`
     - :class:`pyEDAA.Reports.Unittesting.JUnit.CTestJUnit.Document`
   * - :ref:`go-junit-report JUnit <SCHEMAS/GoJUnitReport-JUnit>`
     - :file:`GoJUnitReport-JUnit.xsd`
     - :class:`pyEDAA.Reports.Unittesting.JUnit.GoJUnitReport.Document`
   * - :ref:`GoogleTest JUnit <SCHEMAS/GoogleTest-JUnit>`
     - :file:`GoogleTest-JUnit.xsd`
     - :class:`pyEDAA.Reports.Unittesting.JUnit.GoogleTestJUnit.Document`
   * - :ref:`cargo-nextest JUnit <SCHEMAS/Nextest-JUnit>`
     - :file:`Nextest-JUnit.xsd`
     - :class:`pyEDAA.Reports.Unittesting.JUnit.NextestJUnit.Document`
   * - :ref:`pytest JUnit <SCHEMAS/PyTest-JUnit>`
     - :file:`PyTest-JUnit.xsd`
     - :class:`pyEDAA.Reports.Unittesting.JUnit.PyTestJUnit.Document`
   * - :ref:`JunitXml.TestLogger JUnit <SCHEMAS/TestLogger-JUnit>`
     - :file:`TestLogger-JUnit.xsd`
     - :class:`pyEDAA.Reports.Unittesting.JUnit.TestLoggerJUnit.Document`
   * - :ref:`Open Test Reporting 0.2.0 <SCHEMAS/OpenTestReporting>`
     - :file:`OpenTestReporting/OpenTestReporting-0.2.0.xsd`
     - :class:`pyEDAA.Reports.Unittesting.OpenTestReporting.Events.Document`,
       :class:`pyEDAA.Reports.Unittesting.OpenTestReporting.Hierarchy.Document`
   * - :ref:`pyTooling TestReport v0.1 <SCHEMAS/TestReport-v0.1>`
     - :file:`TestReport-v0.1.xsd`
     - :class:`pyEDAA.Reports.Unittesting.pyTooling.Document`

:file:`TestReport-v0.1.xsd` is pyTooling's: the reader takes it from :mod:`pyTooling.Resources`, and its source is on
:ref:`pyTooling's schema page <pyTool:SCHEMAS/TestReport-v0.1>`.

.. _SCHEMAS/Programmatically:

Reaching a schema from Python
*****************************

The schemas are shipped in the resource package :mod:`pyEDAA.Reports.Resources`. Two functions of pyTooling reach a
resource file, whether pyEDAA.Reports is installed, inside a wheel, or a checkout:
:func:`~pyTooling.Common.getResourceFile` returns its **path**, for handing the file to another tool, and
:func:`~pyTooling.Common.readResourceFile` returns its **content**, for reading it directly.

.. admonition:: ``example.py``

   .. code-block:: python

      from pathlib          import Path
      from pyTooling.Common import getResourceFile, readResourceFile

      from pyEDAA.Reports   import Resources  # Declare a module name that can be handed over.

      schemaPath:    Path = getResourceFile(Resources, "PyTest-JUnit.xsd")
      schemaContent: str  = readResourceFile(Resources, "PyTest-JUnit.xsd")

.. toctree::
   :hidden:

   Any-Cobertura
   Cobertura-04
   CoveragePy-Cobertura
   NVC-Cobertura
   CoveragePy-2
   CoveragePy-3
   GHDL-Coverage-1.0.0
   UCIS-1.0
   PyUCIS-1.0
   Gcov-1
   Gcov-2
   JaCoCo-1.1
   Any-JUnit
   Ant-JUnit4
   Catch2-JUnit
   CTest-JUnit
   GoJUnitReport-JUnit
   GoogleTest-JUnit
   Nextest-JUnit
   PyTest-JUnit
   TestLogger-JUnit
   OpenTestReporting
   TestReport-v0.1
