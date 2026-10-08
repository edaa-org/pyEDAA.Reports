.. _SCHEMAS/CoveragePy-2:

coverage.py JSON, format 2
##########################

The JSON report coverage.py 7.4.1 to 7.5 write with ``coverage json``, format version 2, as a JSON Schema.

Read by :class:`pyEDAA.Reports.CodeCoverage.CoveragePy.Document` for a report stating ``meta.format`` 2 - see
:ref:`CODECOV/Formats/CoveragePy`.

coverage.py publishes no schema of its JSON report. This one is reverse-engineered from coverage.py's
:file:`coverage/jsonreport.py` (version 7.16) and its change log: format 2 added ``meta.format``. A file has no regions
``functions`` and ``classes`` - format 3 adds them -, a summary no separate percentages of statements and branches -
coverage.py 7.12 adds them to format 3. An unknown field is rejected. Format 3 has its own schema:
:ref:`CoveragePy-3.schema.json <SCHEMAS/CoveragePy-3>`.

.. grid:: 2

   .. grid-item::
      :columns: 6

      .. admonition:: Download

         :download:`CoveragePy-2.schema.json <../../pyEDAA/Reports/Resources/CoveragePy-2.schema.json>`

   .. grid-item::
      :columns: 6

      .. admonition:: Validate a report

         .. code-block:: bash

            check-jsonschema --schemafile CoveragePy-2.schema.json coverage.json

.. _SCHEMAS/CoveragePy-2/Source:

Source
******

.. literalinclude:: ../../pyEDAA/Reports/Resources/CoveragePy-2.schema.json
   :language: json
   :linenos:
