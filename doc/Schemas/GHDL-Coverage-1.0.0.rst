.. _SCHEMAS/GHDL-Coverage-1.0.0:

GHDL coverage 1.0.0
###################

The coverage file GHDL writes when simulating with ``ghdl -r --coverage``, format version 1.0.0, as a JSON Schema.

Read by :class:`pyEDAA.Reports.CodeCoverage.GHDL.Document`, for a coverage file stating ``"version": "1.0.0"`` - see
:ref:`CODECOV/Formats/GHDL`.

GHDL publishes no schema of its coverage file. This one is reverse-engineered from GHDL's writer
:file:`src/ghdldrv/ghdlcovout.adb` and its reader :file:`src/ghdldrv/ghdlcov.adb`: every field GHDL writes is
required, a ``result`` is ``0`` or ``1`` per line number, and an unknown field is rejected.

.. grid:: 2

   .. grid-item::
      :columns: 6

      .. admonition:: Download

         :download:`GHDL-Coverage-1.0.0.schema.json <../../pyEDAA/Reports/Resources/GHDL-Coverage-1.0.0.schema.json>`

   .. grid-item::
      :columns: 6

      .. admonition:: Validate a coverage file

         .. code-block:: bash

            check-jsonschema --schemafile GHDL-Coverage-1.0.0.schema.json coverage-*.json

.. _SCHEMAS/GHDL-Coverage-1.0.0/Source:

Source
******

.. literalinclude:: ../../pyEDAA/Reports/Resources/GHDL-Coverage-1.0.0.schema.json
   :language: json
   :linenos:
