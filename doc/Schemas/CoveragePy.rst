.. _SCHEMAS/CoveragePy:

coverage.py JSON
################

The JSON report coverage.py writes with ``coverage json``, format versions 2 and 3, as a JSON Schema.

Read by :class:`pyEDAA.Reports.CodeCoverage.CoveragePy.Document` - see :ref:`CODECOV/Formats/CoveragePy`.

coverage.py publishes no schema of its JSON report. This one is reverse-engineered from coverage.py's
:file:`coverage/jsonreport.py` (version 7.16): format 2 added ``meta.format``, format 3 the regions ``functions`` and
``classes``. A field a later coverage.py added - e.g. ``percent_statements_covered`` - is optional; an unknown field
is rejected.

.. grid:: 2

   .. grid-item::
      :columns: 6

      .. admonition:: Download

         :download:`CoveragePy.schema.json <../../pyEDAA/Reports/Resources/CoveragePy.schema.json>`

   .. grid-item::
      :columns: 6

      .. admonition:: Validate a report

         .. code-block:: bash

            check-jsonschema --schemafile CoveragePy.schema.json coverage.json

.. _SCHEMAS/CoveragePy/Source:

Source
******

.. literalinclude:: ../../pyEDAA/Reports/Resources/CoveragePy.schema.json
   :language: json
   :linenos:
