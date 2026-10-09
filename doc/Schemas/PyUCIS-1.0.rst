.. _SCHEMAS/PyUCIS-1.0:

pyucis UCIS 1.0
###############

UCIS 1.0 XML interchange format as `pyucis <https://github.com/fvutils/pyucis>`__ writes it: the elements in no
namespace.

Read by :class:`pyEDAA.Reports.CodeCoverage.UCIS.PyUCIS.Document` - see :ref:`CODECOV/Formats/UCIS/PyUCIS` - for a
report, whose root ``<UCIS>`` of no namespace states ``ucisVersion="1.0"``.

pyucis' ``XmlWriter`` binds the prefix ``ucis`` to the XML Schema instance namespace, but uses it for no element. This
schema is :ref:`UCIS-1.0.xsd <SCHEMAS/UCIS-1.0>` without a target namespace: the same complex types, elements,
attributes, their order, occurrences, types and defaults.

.. grid:: 2

   .. grid-item::
      :columns: 6

      .. admonition:: Download

         :download:`PyUCIS-1.0.xsd <../../pyEDAA/Reports/Resources/PyUCIS-1.0.xsd>`

   .. grid-item::
      :columns: 6

      .. admonition:: Validate a report

         .. code-block:: bash

            xmllint --schema PyUCIS-1.0.xsd --noout coverage.xml

.. _SCHEMAS/PyUCIS-1.0/Source:

Source
******

.. literalinclude:: ../../pyEDAA/Reports/Resources/PyUCIS-1.0.xsd
   :language: xml
   :linenos:
