.. _SCHEMAS/NVC-Cobertura:

NVC Cobertura
#############

Cobertura XML code coverage report as written by NVC 1.23 (``nvc --cover-export --format=cobertura``).

Read by :class:`pyEDAA.Reports.CodeCoverage.Cobertura.NVCCobertura.Document` - see
:ref:`CODECOV/Formats/Cobertura/NVC`.

The schema was reverse-engineered from NVC's :file:`src/cov/cov-export.c` and accepts nothing else. NVC names
Cobertura's DTD ``coverage-04.dtd`` in a document type declaration. It writes every attribute the DTD requires, one
package named after the top-level's library, a class per design unit named ``ENTITY(ARCHITECTURE)``, never a method,
and on a branching line one condition. A rate has six decimals, every ``complexity`` is ``0.0``, the timestamp is in
seconds. A line's ``condition-coverage`` and its condition's ``coverage`` are ``0 %``, ``50 %`` or ``100 %``.

.. grid:: 2

   .. grid-item::
      :columns: 6

      .. admonition:: Download

         :download:`NVC-Cobertura.xsd <../../pyEDAA/Reports/Resources/NVC-Cobertura.xsd>`

   .. grid-item::
      :columns: 6

      .. admonition:: Validate a report

         .. code-block:: bash

            xmllint --schema NVC-Cobertura.xsd --noout coverage.xml

.. _SCHEMAS/NVC-Cobertura/Source:

Source
******

.. literalinclude:: ../../pyEDAA/Reports/Resources/NVC-Cobertura.xsd
   :language: xml
   :linenos:
