.. _SCHEMAS/LLVM-Coverage-JSON:

LLVM coverage JSON
##################

The JSON report ``llvm-cov export -format=text`` writes - type ``llvm.coverage.json.export``, format versions 2.0.0 to
3.1.0 - as a JSON Schema.

Read by :class:`pyEDAA.Reports.CodeCoverage.LLVM.Document` - see :ref:`CODECOV/Formats/LLVM`.

LLVM publishes no schema of its JSON export. This one is reverse-engineered from llvm-cov's
:file:`llvm/tools/llvm-cov/CoverageExporterJson.cpp`, LLVM 4 to 23:

.. list-table::
   :header-rows: 1
   :widths: 15 15 70

   * - Version
     - LLVM
     - Change
   * - 2.0.0
     - 4
     - Files with segments, expansions and summary; functions with regions; totals.
   * - 2.0.1
     - 11
     - A segment's ``isGapRegion``.
   * -
     - 12
     - Branch regions of files, expansions and functions, and the summaries' ``branches``.
   * -
     - 18
     - MC/DC records of files and functions, and the summaries' ``mcdc``.
   * - 3.0.0
     - 21
     - An MC/DC record's numbers of true and false decisions.
   * - 3.0.1
     - 21
     - An MC/DC record's ``fileID``.
   * - 3.1.0
     - 22
     - An MC/DC record's test vectors; LLVM 23 lists the missing ones too, with ``-show-mcdc-non-executed-vectors``.

A field a later LLVM added is optional; an MC/DC record matches one of its three shapes, by its length. An unknown
field or version is rejected.

.. grid:: 2

   .. grid-item::
      :columns: 6

      .. admonition:: Download

         :download:`LLVM-Coverage-JSON.schema.json <../../pyEDAA/Reports/Resources/LLVM-Coverage-JSON.schema.json>`

   .. grid-item::
      :columns: 6

      .. admonition:: Validate a report

         .. code-block:: bash

            check-jsonschema --schemafile LLVM-Coverage-JSON.schema.json coverage.json

.. _SCHEMAS/LLVM-Coverage-JSON/Source:

Source
******

.. literalinclude:: ../../pyEDAA/Reports/Resources/LLVM-Coverage-JSON.schema.json
   :language: json
   :linenos:
