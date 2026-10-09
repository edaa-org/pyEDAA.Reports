.. _SCHEMAS/Catch2-JUnit:

Catch2 JUnit
############

JUnit XML as written by Catch2's JUnit reporter (``--reporter JUnit``).

Read by :class:`pyEDAA.Reports.Unittesting.JUnit.Catch2JUnit.Document` - see
:ref:`UNITTEST/SpecificDataModel/JUnit/Dialect/Catch2`.

.. grid:: 2

   .. grid-item::
      :columns: 6

      .. admonition:: Download

         :download:`Catch2-JUnit.xsd <../../pyEDAA/Reports/Resources/Catch2-JUnit.xsd>`

   .. grid-item::
      :columns: 6

      .. admonition:: Validate a report

         .. code-block:: bash

            xmllint --schema Catch2-JUnit.xsd --noout report.xml

.. _SCHEMAS/Catch2-JUnit/Source:

Source
******

.. literalinclude:: ../../pyEDAA/Reports/Resources/Catch2-JUnit.xsd
   :language: xml
   :linenos:
