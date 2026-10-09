.. _SCHEMAS/JaCoCo-1.1:

JaCoCo 1.1
##########

JaCoCo XML code coverage report, version 1.1, as JaCoCo's DTD ``report.dtd`` defines it, translated to XML Schema.

Read by :class:`pyEDAA.Reports.CodeCoverage.JaCoCo.Document` - see :ref:`CODECOV/Formats/JaCoCo` - for a report naming
the DTD by its public identifier ``-//JACOCO//DTD Report 1.1//EN``.

JaCoCo publishes no XML Schema, only the DTD. The translation keeps the DTD's elements, attributes, their order and
which are required, and allows no other attribute. Where the DTD's ``CDATA`` holds a number, the attribute has a
numeric type: a count, a line number, a time stamp in milliseconds since the epoch. As the DTD, it allows either groups
or packages in a report or group, and a line without its counts.

.. grid:: 2

   .. grid-item::
      :columns: 6

      .. admonition:: Download

         :download:`JaCoCo-1.1.xsd <../../pyEDAA/Reports/Resources/JaCoCo-1.1.xsd>`

   .. grid-item::
      :columns: 6

      .. admonition:: Validate a report

         .. code-block:: bash

            xmllint --schema JaCoCo-1.1.xsd --noout jacoco.xml

.. _SCHEMAS/JaCoCo-1.1/Source:

Source
******

.. literalinclude:: ../../pyEDAA/Reports/Resources/JaCoCo-1.1.xsd
   :language: xml
   :linenos:
