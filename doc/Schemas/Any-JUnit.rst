.. _SCHEMAS/Any-JUnit:

Any JUnit
#########

The common denominator of the JUnit XML dialects, read when a file's dialect isn't known.

Read by :class:`pyEDAA.Reports.Unittesting.JUnit.Document` - see :ref:`UNITTEST/SpecificDataModel/JUnit/Dialect/AnyJUnit`.

.. grid:: 2

   .. grid-item::
      :columns: 6

      .. admonition:: Download

         :download:`Any-JUnit.xsd <../../pyEDAA/Reports/Resources/Any-JUnit.xsd>`

   .. grid-item::
      :columns: 6

      .. admonition:: Validate a report

         .. code-block:: bash

            xmllint --schema Any-JUnit.xsd --noout report.xml

.. _SCHEMAS/Any-JUnit/Source:

Source
******

.. literalinclude:: ../../pyEDAA/Reports/Resources/Any-JUnit.xsd
   :language: xml
   :linenos:
