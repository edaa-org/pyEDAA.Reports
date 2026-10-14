.. _SCHEMAS/VSTest-TRX:

VSTest TRX
##########

Visual Studio test results (TRX) as written by VSTest's TRX logger (``dotnet test --logger trx``).

Read by :class:`pyEDAA.Reports.Unittesting.TRX.Document` - see :ref:`UNITTEST/SpecificDataModel/TRX`. The schema is
reverse engineered from the logger's source code in `microsoft/vstest <https://github.com/microsoft/vstest>`__
(directory :file:`src/Microsoft.TestPlatform.Extensions.TrxLogger`, MIT license). Visual Studio's own schema
:file:`vstst.xsd` ships with Visual Studio under its license and isn't redistributed.

.. grid:: 2

   .. grid-item::
      :columns: 6

      .. admonition:: Download

         :download:`VSTest-TRX.xsd <../../pyEDAA/Reports/Resources/VSTest-TRX.xsd>`

   .. grid-item::
      :columns: 6

      .. admonition:: Validate a report

         .. code-block:: bash

            xmllint --schema VSTest-TRX.xsd --noout report.trx

.. _SCHEMAS/VSTest-TRX/Source:

Source
******

.. literalinclude:: ../../pyEDAA/Reports/Resources/VSTest-TRX.xsd
   :language: xml
   :linenos:
