.. _SCHEMAS/PyTest-JUnit:

pytest JUnit
############

JUnit XML as written by pytest (``--junitxml``).

Read by :class:`pyEDAA.Reports.Unittesting.JUnit.PyTestJUnit.Document` - see :ref:`UNITTEST/SpecificDataModel/JUnit/Dialect/pyTest`.

.. grid:: 2

   .. grid-item::
      :columns: 6

      .. admonition:: Download

         :download:`PyTest-JUnit.xsd <../../pyEDAA/Reports/Resources/PyTest-JUnit.xsd>`

   .. grid-item::
      :columns: 6

      .. admonition:: Validate a report

         .. code-block:: bash

            xmllint --schema PyTest-JUnit.xsd --noout report.xml

.. _SCHEMAS/PyTest-JUnit/Source:

Source
******

.. literalinclude:: ../../pyEDAA/Reports/Resources/PyTest-JUnit.xsd
   :language: xml
   :linenos:
