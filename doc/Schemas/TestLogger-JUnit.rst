.. _SCHEMAS/TestLogger-JUnit:

JunitXml.TestLogger JUnit
#########################

JUnit XML as written by the .NET test logger ``JunitXml.TestLogger`` (``dotnet test --logger junit``).

Read by :class:`pyEDAA.Reports.Unittesting.JUnit.TestLoggerJUnit.Document` - see
:ref:`UNITTEST/SpecificDataModel/JUnit/Dialect/TestLogger`.

.. grid:: 2

   .. grid-item::
      :columns: 6

      .. admonition:: Download

         :download:`TestLogger-JUnit.xsd <../../pyEDAA/Reports/Resources/TestLogger-JUnit.xsd>`

   .. grid-item::
      :columns: 6

      .. admonition:: Validate a report

         .. code-block:: bash

            xmllint --schema TestLogger-JUnit.xsd --noout report.xml

.. _SCHEMAS/TestLogger-JUnit/Source:

Source
******

.. literalinclude:: ../../pyEDAA/Reports/Resources/TestLogger-JUnit.xsd
   :language: xml
   :linenos:
