.. _SCHEMAS/UCIS-1.0:

UCIS 1.0
########

XML interchange format of the Accellera Unified Coverage Interoperability Standard (UCIS), version 1.0: the schema of
chapter 9 of the standard (June 2012), section 9.14.

Read by :class:`pyEDAA.Reports.CodeCoverage.UCIS.Document` - see :ref:`CODECOV/Formats/UCIS` - for a report, whose root
``<UCIS>`` of namespace ``UCIS`` states ``ucisVersion="1.0"``.

Accellera publishes the standard, but not its schema as a file; Accellera's FC4SC repository does, under the Apache
License 2.0, with four changes. This schema is derived from that file (``ucis/UCIS.xsd`` of
`accellera-official/fc4sc <https://github.com/accellera-official/fc4sc>`__): the four changes are reverted - so it has
the standard's complex types, elements, attributes, their order, occurrences, types and defaults -, the definitions are
reformatted and grouped by coverage kind. Where the standard's tables and examples contradict its schema - e.g. an
example's ``branchStatement`` for ``statement``, ``exprBin`` for ``bin``, or a ``coverpointBin`` with ``name`` and
``key`` -, the schema decides.

.. grid:: 2

   .. grid-item::
      :columns: 6

      .. admonition:: Download

         :download:`UCIS-1.0.xsd <../../pyEDAA/Reports/Resources/UCIS-1.0.xsd>`

   .. grid-item::
      :columns: 6

      .. admonition:: Validate a report

         .. code-block:: bash

            xmllint --schema UCIS-1.0.xsd --noout coverage.xml

.. _SCHEMAS/UCIS-1.0/Source:

Source
******

.. literalinclude:: ../../pyEDAA/Reports/Resources/UCIS-1.0.xsd
   :language: xml
   :linenos:
