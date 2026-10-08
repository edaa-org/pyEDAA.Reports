.. _SCHEMAS/Gcov:

gcov JSON
#########

The JSON report GCC's gcov writes with ``gcov --json-format``, format versions 1 and 2, as a JSON Schema.

Read by :class:`pyEDAA.Reports.CodeCoverage.Gcov.Document` - see :ref:`CODECOV/Formats/Gcov`.

gcov documents its JSON report in its manual, but publishes no schema. This one is reverse-engineered from GCC's
:file:`gcc/gcov.cc` (GCC 9 to 15) and the manual of GCC 14: format 1 is written by GCC 9 to 13, format 2 by GCC 14 and
later; format 2 added the basic blocks of a line and a branch, the calls and the conditions, GCC 15 the prime paths of
a function. A field a later version added is optional; an unknown field is rejected. The schema describes one JSON
object: gcov's standard output holds one per data file, each validated on its own.

.. grid:: 2

   .. grid-item::
      :columns: 6

      .. admonition:: Download

         :download:`Gcov.schema.json <../../pyEDAA/Reports/Resources/Gcov.schema.json>`

   .. grid-item::
      :columns: 6

      .. admonition:: Validate a report

         .. code-block:: bash

            gunzip --keep main.gcov.json.gz
            check-jsonschema --schemafile Gcov.schema.json main.gcov.json

.. _SCHEMAS/Gcov/Source:

Source
******

.. literalinclude:: ../../pyEDAA/Reports/Resources/Gcov.schema.json
   :language: json
   :linenos:
