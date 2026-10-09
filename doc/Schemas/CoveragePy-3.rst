.. _SCHEMAS/CoveragePy-3:

coverage.py JSON, format 3
##########################

The JSON report coverage.py 7.6 and later write with ``coverage json``, format version 3, as a JSON Schema.

Read by :class:`pyEDAA.Reports.CodeCoverage.CoveragePy.Document` for a report stating ``meta.format`` 3 - see
:ref:`CODECOV/Formats/CoveragePy`.

coverage.py publishes no schema of its JSON report. This one is reverse-engineered from coverage.py's
:file:`coverage/jsonreport.py` (version 7.16): format 3 adds the regions ``functions`` and ``classes`` to a file. A
field a later coverage.py added - e.g. ``percent_statements_covered`` - is optional; an unknown field is rejected.
Format 2 has its own schema: :ref:`CoveragePy-2.schema.json <SCHEMAS/CoveragePy-2>`.

.. grid:: 2

   .. grid-item::
      :columns: 6

      .. admonition:: Download

         :download:`CoveragePy-3.schema.json <../../pyEDAA/Reports/Resources/CoveragePy-3.schema.json>`

   .. grid-item::
      :columns: 6

      .. admonition:: Validate a report

         .. code-block:: bash

            check-jsonschema --schemafile CoveragePy-3.schema.json coverage.json

.. _SCHEMAS/CoveragePy-3/Source:

Source
******

.. literalinclude:: ../../pyEDAA/Reports/Resources/CoveragePy-3.schema.json
   :language: json
   :linenos:
