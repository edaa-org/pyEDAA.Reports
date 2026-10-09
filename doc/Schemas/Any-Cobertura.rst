.. _SCHEMAS/Any-Cobertura:

Any Cobertura
#############

Cobertura XML code coverage report, read leniently as tools write it - e.g. coverage.py (``coverage xml``) or gcovr
(``--cobertura``).

Read by :class:`pyEDAA.Reports.CodeCoverage.Cobertura.Document` - see :ref:`CODECOV/Formats/Cobertura`.

The schema has the structure of Cobertura's DTD ``coverage-04.dtd``, but accepts the attributes tools add - e.g.
coverage.py's ``missing-branches`` - and requires only what a reader needs: a class' ``filename``, a line's
``number`` and ``hits``. :ref:`Cobertura-04.xsd <SCHEMAS/Cobertura-04>` is the DTD's strict translation, and
:ref:`CoveragePy-Cobertura.xsd <SCHEMAS/CoveragePy-Cobertura>` describes coverage.py's dialect strictly.
:ref:`NVC-Cobertura.xsd <SCHEMAS/NVC-Cobertura>` describes NVC's dialect, whose ``condition-coverage`` - e.g.
``50 %`` - this schema rejects.

.. grid:: 2

   .. grid-item::
      :columns: 6

      .. admonition:: Download

         :download:`Any-Cobertura.xsd <../../pyEDAA/Reports/Resources/Any-Cobertura.xsd>`

   .. grid-item::
      :columns: 6

      .. admonition:: Validate a report

         .. code-block:: bash

            xmllint --schema Any-Cobertura.xsd --noout coverage.xml

.. _SCHEMAS/Any-Cobertura/Source:

Source
******

.. literalinclude:: ../../pyEDAA/Reports/Resources/Any-Cobertura.xsd
   :language: xml
   :linenos:
