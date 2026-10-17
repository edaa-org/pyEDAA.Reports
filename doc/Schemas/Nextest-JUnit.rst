.. _SCHEMAS/Nextest-JUnit:

cargo-nextest JUnit
###################

JUnit XML as written by cargo-nextest (``[profile.<name>.junit]`` in :file:`.config/nextest.toml`).

Read by :class:`pyEDAA.Reports.Unittesting.JUnit.NextestJUnit.Document` - see
:ref:`UNITTEST/SpecificDataModel/JUnit/Dialect/nextest`.

.. grid:: 2

   .. grid-item::
      :columns: 6

      .. admonition:: Download

         :download:`Nextest-JUnit.xsd <../../pyEDAA/Reports/Resources/Nextest-JUnit.xsd>`

   .. grid-item::
      :columns: 6

      .. admonition:: Validate a report

         .. code-block:: bash

            xmllint --schema Nextest-JUnit.xsd --noout report.xml

.. _SCHEMAS/Nextest-JUnit/Source:

Source
******

.. literalinclude:: ../../pyEDAA/Reports/Resources/Nextest-JUnit.xsd
   :language: xml
   :linenos:
