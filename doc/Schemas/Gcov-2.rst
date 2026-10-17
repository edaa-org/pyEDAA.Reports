.. _SCHEMAS/Gcov-2:

gcov JSON 2
###########

The JSON report GCC's gcov writes with ``gcov --json-format``, format version 2, as a JSON Schema.

Read by :class:`pyEDAA.Reports.CodeCoverage.Gcov.Document` - see :ref:`CODECOV/Formats/Gcov` - for a JSON object
stating ``"format_version": "2"``.

gcov documents its JSON report in its manual, but publishes no schema. This one is reverse-engineered from GCC's
:file:`gcc/gcov.cc` (GCC 14 and 15) and the manual of GCC 14: format 2 is written by GCC 14 and later. It adds to
:ref:`format 1 <SCHEMAS/Gcov-1>` the IDs of the basic blocks of a line and of a branch, a line's calls and its
conditions; gcov writes them always, the lists empty unless asked for. GCC 15 adds the prime paths of a function,
written with ``gcov --prime-paths`` only, so they are optional. An unknown field is rejected. The schema describes one
JSON object: gcov's standard output holds one per data file, each validated on its own.

.. grid:: 2

   .. grid-item::
      :columns: 6

      .. admonition:: Download

         :download:`Gcov-2.schema.json <../../pyEDAA/Reports/Resources/Gcov-2.schema.json>`

   .. grid-item::
      :columns: 6

      .. admonition:: Validate a report

         .. code-block:: bash

            gunzip --keep main.gcov.json.gz
            check-jsonschema --schemafile Gcov-2.schema.json main.gcov.json

.. _SCHEMAS/Gcov-2/Source:

Source
******

.. literalinclude:: ../../pyEDAA/Reports/Resources/Gcov-2.schema.json
   :language: json
   :linenos:
