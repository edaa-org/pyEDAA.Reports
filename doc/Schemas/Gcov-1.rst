.. _SCHEMAS/Gcov-1:

gcov JSON 1
###########

The JSON report GCC's gcov writes with ``gcov --json-format``, format version 1, as a JSON Schema.

Read by :class:`pyEDAA.Reports.CodeCoverage.Gcov.Document` - see :ref:`CODECOV/Formats/Gcov` - for a JSON object
stating ``"format_version": "1"``.

gcov documents its JSON report in its manual, but publishes no schema. This one is reverse-engineered from GCC's
:file:`gcc/gcov.cc` (GCC 9 to 13): format 1 is written by GCC 9 to 13. It knows no basic blocks, calls or conditions
of a line - :ref:`format 2 <SCHEMAS/Gcov-2>` added them -, so a field of format 2 is rejected, like any unknown field.
The schema describes one JSON object: gcov's standard output holds one per data file, each validated on its own.

.. grid:: 2

   .. grid-item::
      :columns: 6

      .. admonition:: Download

         :download:`Gcov-1.schema.json <../../pyEDAA/Reports/Resources/Gcov-1.schema.json>`

   .. grid-item::
      :columns: 6

      .. admonition:: Validate a report

         .. code-block:: bash

            gunzip --keep main.gcov.json.gz
            check-jsonschema --schemafile Gcov-1.schema.json main.gcov.json

.. _SCHEMAS/Gcov-1/Source:

Source
******

.. literalinclude:: ../../pyEDAA/Reports/Resources/Gcov-1.schema.json
   :language: json
   :linenos:
