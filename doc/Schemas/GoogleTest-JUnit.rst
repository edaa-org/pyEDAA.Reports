.. _SCHEMAS/GoogleTest-JUnit:

GoogleTest JUnit
################

JUnit XML as written by GoogleTest (``--gtest_output=xml``).

Read by :class:`pyEDAA.Reports.Unittesting.JUnit.GoogleTestJUnit.Document` - see :ref:`UNITTEST/SpecificDataModel/JUnit/Dialect/GoogleTest`.

.. grid:: 2

   .. grid-item::
      :columns: 6

      .. admonition:: Download

         :download:`GoogleTest-JUnit.xsd <../../pyEDAA/Reports/Resources/GoogleTest-JUnit.xsd>`

   .. grid-item::
      :columns: 6

      .. admonition:: Validate a report

         .. code-block:: bash

            xmllint --schema GoogleTest-JUnit.xsd --noout report.xml

.. _SCHEMAS/GoogleTest-JUnit/Source:

Source
******

.. literalinclude:: ../../pyEDAA/Reports/Resources/GoogleTest-JUnit.xsd
   :language: xml
   :linenos:
