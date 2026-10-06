.. _SCHEMAS/TestReport-v0.1:

pyTooling TestReport v0.1
#########################

pyTooling's own test report format, which pyTooling's pytest plugin writes. Unlike JUnit XML, test suites nest,
and every test suite and test case carries a title, a summary and a description. This file is a copy of the one
pyTooling ships in ``pyTooling.Resources``.

Read by :class:`pyEDAA.Reports.Unittesting.pyTooling.Document` - see :ref:`UNITTEST/FileFormats/pyTooling`.

.. grid:: 2

   .. grid-item::
      :columns: 6

      .. admonition:: Download

         :download:`TestReport-v0.1.xsd <../../pyEDAA/Reports/Resources/TestReport-v0.1.xsd>`

   .. grid-item::
      :columns: 6

      .. admonition:: Validate a report

         .. code-block:: bash

            xmllint --schema TestReport-v0.1.xsd --noout report.xml

.. _SCHEMAS/TestReport-v0.1/Source:

Source
******

.. literalinclude:: ../../pyEDAA/Reports/Resources/TestReport-v0.1.xsd
   :language: xml
   :linenos:
