.. _SCHEMAS:

Schemas
#######

pyEDAA.Reports validates every file it reads against the **XML schema** of its format before converting it. It ships
the schemas of the JUnit dialects; the schema of pyTooling's test report comes with pyTooling. Each schema is listed
here, the shipped ones with their full source, ready to read, to copy, or to download.

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

   Any-JUnit
   Ant-JUnit4
   CTest-JUnit
   GoogleTest-JUnit
   PyTest-JUnit
   TestReport-v0.1
