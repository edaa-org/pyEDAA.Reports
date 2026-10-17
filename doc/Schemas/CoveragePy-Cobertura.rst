.. _SCHEMAS/CoveragePy-Cobertura:

coverage.py Cobertura
#####################

Cobertura XML code coverage report as written by coverage.py 7.x (``coverage xml``).

Read by :class:`pyEDAA.Reports.CodeCoverage.Cobertura.CoveragePyCobertura.Document` - see
:ref:`CODECOV/Formats/Cobertura/CoveragePy`.

The schema was reverse-engineered from coverage.py's :file:`xmlreport.py` and accepts nothing else. coverage.py names
Cobertura's DTD ``coverage-04.dtd`` in a comment, not in a document type declaration. It writes every attribute the
DTD requires, but never a method or a condition, and adds ``missing-branches`` to a line: the target lines of the
branches never taken, ``exit`` for an exit of a function. A line's ``hits`` is ``0`` or ``1``, every ``complexity``
``0``.

.. grid:: 2

   .. grid-item::
      :columns: 6

      .. admonition:: Download

         :download:`CoveragePy-Cobertura.xsd <../../pyEDAA/Reports/Resources/CoveragePy-Cobertura.xsd>`

   .. grid-item::
      :columns: 6

      .. admonition:: Validate a report

         .. code-block:: bash

            xmllint --schema CoveragePy-Cobertura.xsd --noout coverage.xml

.. _SCHEMAS/CoveragePy-Cobertura/Source:

Source
******

.. literalinclude:: ../../pyEDAA/Reports/Resources/CoveragePy-Cobertura.xsd
   :language: xml
   :linenos:
