.. _SCHEMAS/CTest-JUnit:

CTest JUnit
###########

JUnit XML as written by CTest (``ctest --output-junit``).

Read by :class:`pyEDAA.Reports.Unittesting.JUnit.CTestJUnit.Document` - see :ref:`UNITTEST/SpecificDataModel/JUnit/Dialect/CTest`.

.. grid:: 2

   .. grid-item::
      :columns: 6

      .. admonition:: Download

         :download:`CTest-JUnit.xsd <../../pyEDAA/Reports/Resources/CTest-JUnit.xsd>`

   .. grid-item::
      :columns: 6

      .. admonition:: Validate a report

         .. code-block:: bash

            xmllint --schema CTest-JUnit.xsd --noout report.xml

.. _SCHEMAS/CTest-JUnit/Source:

Source
******

.. literalinclude:: ../../pyEDAA/Reports/Resources/CTest-JUnit.xsd
   :language: xml
   :linenos:
