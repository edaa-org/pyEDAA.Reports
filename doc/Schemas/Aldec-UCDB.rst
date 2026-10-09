.. _SCHEMAS/Aldec-UCDB:

Aldec UCDB
##########

Aldec UCDB XML code coverage report, as Aldec's tool ``acdb2xml`` exports a coverage database (ACDB) of Riviera-PRO
or Active-HDL.

Read by :class:`pyEDAA.Reports.CodeCoverage.AldecUCDB.Document` - see :ref:`CODECOV/Formats/AldecUCDB`.

Aldec publishes no schema. This one was reverse-engineered from reports of Riviera-PRO 2021.10 and 2022.04 and from
what pyEDAA.UCIS read: every element and attribute these reports state is required, in their order, and no other is
allowed. The kinds of scopes and bins and the source languages are the names the UCIS standard defines in its C API,
without the prefix ``UCIS_`` - e.g. ``DU_MODULE``, ``STMTBIN``, ``VLOG`` -; a kind of bin without a name is stated by
its value in hexadecimal: ``1000000`` is ``UCIS_BLOCKBIN``. The flags of scopes and bins are eight hexadecimal digits,
the root's ``version`` names the tool and its version, e.g. ``Riviera-PRO 2022.04``. An element states an attribute key
once.

.. grid:: 2

   .. grid-item::
      :columns: 6

      .. admonition:: Download

         :download:`Aldec-UCDB.xsd <../../pyEDAA/Reports/Resources/Aldec-UCDB.xsd>`

   .. grid-item::
      :columns: 6

      .. admonition:: Validate a report

         .. code-block:: bash

            xmllint --schema Aldec-UCDB.xsd --noout ucdb.xml

.. _SCHEMAS/Aldec-UCDB/Source:

Source
******

.. literalinclude:: ../../pyEDAA/Reports/Resources/Aldec-UCDB.xsd
   :language: xml
   :linenos:
