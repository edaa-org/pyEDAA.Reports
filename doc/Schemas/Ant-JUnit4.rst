.. _SCHEMAS/Ant-JUnit4:

Ant + JUnit4
############

JUnit XML as written by Ant's ``junit`` task running JUnit 4 tests.

Read by :class:`pyEDAA.Reports.Unittesting.JUnit.AntJUnit4.Document` - see :ref:`UNITTEST/SpecificDataModel/JUnit/Dialect/AntJUnit4`.

.. grid:: 2

   .. grid-item::
      :columns: 6

      .. admonition:: Download

         :download:`Ant-JUnit4.xsd <../../pyEDAA/Reports/Resources/Ant-JUnit4.xsd>`

   .. grid-item::
      :columns: 6

      .. admonition:: Validate a report

         .. code-block:: bash

            xmllint --schema Ant-JUnit4.xsd --noout report.xml

.. _SCHEMAS/Ant-JUnit4/Source:

Source
******

.. literalinclude:: ../../pyEDAA/Reports/Resources/Ant-JUnit4.xsd
   :language: xml
   :linenos:
