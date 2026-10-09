"""
This package is a resource package containing various data files.

Each schema is shown, with its source, on a page of the :ref:`schema overview <SCHEMAS>`.

.. rubric:: Unit Test Report Schemas

The XML schemas the JUnit dialects are validated against. pyTooling's test report is validated against
:file:`TestReport-v0.1.xsd`, which pyTooling ships in :mod:`pyTooling.Resources`.

* :file:`Any-JUnit.xsd` - the common denominator of the JUnit dialects, read by
  :class:`pyEDAA.Reports.Unittesting.JUnit.Document`.
* :file:`Ant-JUnit4.xsd` - JUnit XML as written by Ant's JUnit 4 runner.
* :file:`Catch2-JUnit.xsd` - JUnit XML as written by Catch2.
* :file:`CTest-JUnit.xsd` - JUnit XML as written by CTest.
* :file:`GoJUnitReport-JUnit.xsd` - JUnit XML as written by go-junit-report.
* :file:`GoogleTest-JUnit.xsd` - JUnit XML as written by GoogleTest.
* :file:`Nextest-JUnit.xsd` - JUnit XML as written by cargo-nextest.
* :file:`PyTest-JUnit.xsd` - JUnit XML as written by pytest.
* :file:`TestLogger-JUnit.xsd` - JUnit XML as written by the .NET test logger ``JunitXml.TestLogger``.

The schemas of Open Test Reporting are in the resource package :mod:`pyEDAA.Reports.Resources.OpenTestReporting`.

.. rubric:: Code Coverage Report Schemas

The XML schemas and JSON Schemas the code coverage formats are validated against.

* :file:`Any-Cobertura.xsd` - Cobertura XML of any writer, read by
  :class:`pyEDAA.Reports.CodeCoverage.Cobertura.Document`.
* :file:`Cobertura-04.xsd` - strict translation of Cobertura's DTD ``coverage-04.dtd``.
* :file:`CoveragePy-Cobertura.xsd` - Cobertura XML as written by coverage.py.
* :file:`NVC-Cobertura.xsd` - Cobertura XML as written by NVC.
* :file:`CoveragePy-2.schema.json` - coverage.py JSON, format 2.
* :file:`CoveragePy-3.schema.json` - coverage.py JSON, format 3.
* :file:`GHDL-Coverage-1.0.0.schema.json` - GHDL's JSON coverage file, version 1.0.0.
* :file:`Gcov-1.schema.json` - gcov JSON, format 1.
* :file:`Gcov-2.schema.json` - gcov JSON, format 2.
* :file:`JaCoCo-1.1.xsd` - JaCoCo XML, format 1.1.

.. rubric:: Usage

:func:`~pyTooling.Common.getResourceFile` returns a resource file's **path**, for handing the file to another tool, and
:func:`~pyTooling.Common.readResourceFile` returns its **content**, for reading it directly.

.. admonition:: ``example.py``

   .. code-block:: python

      from pathlib          import Path
      from pyTooling.Common import getResourceFile, readResourceFile

      from pyEDAA.Reports   import Resources  # Declare a module name that can be handed over.

      schemaPath:    Path = getResourceFile(Resources, "PyTest-JUnit.xsd")
      schemaContent: str  = readResourceFile(Resources, "PyTest-JUnit.xsd")
"""
