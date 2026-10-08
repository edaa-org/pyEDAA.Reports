.. _SCHEMAS/Cobertura-04:

Cobertura 04
############

Cobertura XML code coverage report, as Cobertura's DTD ``coverage-04.dtd`` defines it, translated to XML Schema.

Cobertura publishes no XML Schema, only DTDs; ``coverage-04.dtd`` is the latest. The translation keeps the DTD's
elements, attributes, their order and which are required, and allows no other attribute. Where the DTD's ``CDATA``
holds a number, the attribute has a numeric type: a rate in range 0..1, a count, a complexity.

A report a tool writes may not follow the DTD - coverage.py adds the attribute ``missing-branches`` to a line -, so a
report is read with the lenient :ref:`Any-Cobertura.xsd <SCHEMAS/Any-Cobertura>`, or with the strict schema of its
dialect, e.g. :ref:`CoveragePy-Cobertura.xsd <SCHEMAS/CoveragePy-Cobertura>`.

A report :meth:`Document.Write <pyEDAA.Reports.CodeCoverage.Cobertura.Document.Write>` writes is valid according to it.

.. grid:: 2

   .. grid-item::
      :columns: 6

      .. admonition:: Download

         :download:`Cobertura-04.xsd <../../pyEDAA/Reports/Resources/Cobertura-04.xsd>`

   .. grid-item::
      :columns: 6

      .. admonition:: Validate a report

         .. code-block:: bash

            xmllint --schema Cobertura-04.xsd --noout coverage.xml

.. _SCHEMAS/Cobertura-04/Source:

Source
******

.. literalinclude:: ../../pyEDAA/Reports/Resources/Cobertura-04.xsd
   :language: xml
   :linenos:
