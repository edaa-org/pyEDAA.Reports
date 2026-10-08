"""
This package is a resource package containing various data files.

.. rubric:: XML Schema Files

The schemas the JUnit dialects are validated against. Each is shown, with its source, on a page of the
:ref:`schema overview <SCHEMAS>`. pyTooling's test report is validated against :file:`TestReport-v0.1.xsd`, which
pyTooling ships in :mod:`pyTooling.Resources`.

* :file:`Any-JUnit.xsd` - the common denominator of the JUnit dialects, read by
  :class:`pyEDAA.Reports.Unittesting.JUnit.Document`.
* :file:`Ant-JUnit4.xsd` - JUnit XML as written by Ant's JUnit 4 runner.
* :file:`CTest-JUnit.xsd` - JUnit XML as written by CTest.
* :file:`GoogleTest-JUnit.xsd` - JUnit XML as written by GoogleTest.
* :file:`PyTest-JUnit.xsd` - JUnit XML as written by pytest.

The schemas of Open Test Reporting are in the resource package :mod:`pyEDAA.Reports.Resources.OpenTestReporting`.

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
