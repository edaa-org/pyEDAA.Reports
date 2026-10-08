.. _SCHEMAS/GHDL-Coverage-JSON:

GHDL coverage JSON
##################

The coverage file GHDL writes when simulating with ``ghdl -r --coverage``, format version 1.0.0, as a JSON Schema.

Read by :class:`pyEDAA.Reports.CodeCoverage.GHDL.Document` - see :ref:`CODECOV/Formats/GHDL`.

GHDL publishes no schema of its coverage file. This one is reverse-engineered from GHDL's writer
:file:`src/ghdldrv/ghdlcovout.adb` and its reader :file:`src/ghdldrv/ghdlcov.adb`: every field GHDL writes is
required, a ``result`` is ``0`` or ``1`` per line number, and an unknown field is rejected.

.. grid:: 2

   .. grid-item::
      :columns: 6

      .. admonition:: Download

         :download:`GHDL-Coverage-JSON.schema.json <../../pyEDAA/Reports/Resources/GHDL-Coverage-JSON.schema.json>`

   .. grid-item::
      :columns: 6

      .. admonition:: Validate a coverage file

         .. code-block:: bash

            check-jsonschema --schemafile GHDL-Coverage-JSON.schema.json coverage-*.json

.. _SCHEMAS/GHDL-Coverage-JSON/Source:

Source
******

.. literalinclude:: ../../pyEDAA/Reports/Resources/GHDL-Coverage-JSON.schema.json
   :language: json
   :linenos:
