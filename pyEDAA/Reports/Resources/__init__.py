"""
This package is a resource package containing various data files.

.. rubric:: XML Schema Files

The schemas the JUnit dialects and pyTooling's test report are validated against. Each is shown, with its source, on
a page of the :ref:`schema overview <SCHEMAS>`.

* :file:`Any-JUnit.xsd` - the common denominator of the JUnit dialects, read by
  :class:`pyEDAA.Reports.Unittesting.JUnit.Document`.
* :file:`Ant-JUnit4.xsd` - JUnit XML as written by Ant's JUnit 4 runner.
* :file:`CTest-JUnit.xsd` - JUnit XML as written by CTest.
* :file:`GoogleTest-JUnit.xsd` - JUnit XML as written by GoogleTest.
* :file:`PyTest-JUnit.xsd` - JUnit XML as written by pytest.
* :file:`TestReport-v0.1.xsd` - pyTooling's test report format, read by
  :class:`pyEDAA.Reports.Unittesting.pyTooling.Document`. The file name carries the format's version.

.. rubric:: Usage

.. admonition:: ``example.py``

   .. code-block:: python

      from pathlib          import Path
      from pyEDAA.Reports   import Resources
      from pyTooling.Common import getResourceFile

      schemaPath: Path = getResourceFile(Resources, "PyTest-JUnit.xsd")
"""
