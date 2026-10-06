.. _SCHEMAS:

Overview
########

pyEDAA.Reports ships the **XML schemas** of the file formats it reads, and validates every file against the schema
of its format before converting it. Each schema is listed here with its full source, ready to read, to copy, or to
download.

.. _SCHEMAS/Files:

Available schemas
*****************

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Schema
     - File
     - Read by
   * - :ref:`Any JUnit <SCHEMAS/Any-JUnit>`
     - :file:`Any-JUnit.xsd`
     - :class:`pyEDAA.Reports.Unittesting.JUnit.Document`
   * - :ref:`Ant + JUnit4 <SCHEMAS/Ant-JUnit4>`
     - :file:`Ant-JUnit4.xsd`
     - :class:`pyEDAA.Reports.Unittesting.JUnit.AntJUnit4.Document`
   * - :ref:`CTest JUnit <SCHEMAS/CTest-JUnit>`
     - :file:`CTest-JUnit.xsd`
     - :class:`pyEDAA.Reports.Unittesting.JUnit.CTestJUnit.Document`
   * - :ref:`GoogleTest JUnit <SCHEMAS/GoogleTest-JUnit>`
     - :file:`GoogleTest-JUnit.xsd`
     - :class:`pyEDAA.Reports.Unittesting.JUnit.GoogleTestJUnit.Document`
   * - :ref:`pytest JUnit <SCHEMAS/PyTest-JUnit>`
     - :file:`PyTest-JUnit.xsd`
     - :class:`pyEDAA.Reports.Unittesting.JUnit.PyTestJUnit.Document`
   * - :ref:`pyTooling TestReport v0.1 <SCHEMAS/TestReport-v0.1>`
     - :file:`TestReport-v0.1.xsd`
     - :class:`pyEDAA.Reports.Unittesting.pyTooling.Document`

.. _SCHEMAS/Programmatically:

Reaching a schema from Python
*****************************

The schemas are shipped in the resource package :mod:`pyEDAA.Reports.Resources`:

.. admonition:: ``example.py``

   .. code-block:: python

      from pathlib          import Path
      from pyEDAA.Reports   import Resources
      from pyTooling.Common import getResourceFile

      schemaPath: Path = getResourceFile(Resources, "PyTest-JUnit.xsd")

.. toctree::
   :hidden:

   Any-JUnit
   Ant-JUnit4
   CTest-JUnit
   GoogleTest-JUnit
   PyTest-JUnit
   TestReport-v0.1
