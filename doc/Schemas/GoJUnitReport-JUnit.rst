.. _SCHEMAS/GoJUnitReport-JUnit:

go-junit-report JUnit
#####################

JUnit XML as written by go-junit-report (``go-junit-report -in go-test.log -out report.xml``). The schema is derived
from the structs in go-junit-report's
`junit/junit.go <https://github.com/jstemmer/go-junit-report/blob/v2.1.0/junit/junit.go>`__.

Read by :class:`pyEDAA.Reports.Unittesting.JUnit.GoJUnitReport.Document` - see
:ref:`UNITTEST/SpecificDataModel/JUnit/Dialect/GoJUnitReport`.

.. grid:: 2

   .. grid-item::
      :columns: 6

      .. admonition:: Download

         :download:`GoJUnitReport-JUnit.xsd <../../pyEDAA/Reports/Resources/GoJUnitReport-JUnit.xsd>`

   .. grid-item::
      :columns: 6

      .. admonition:: Validate a report

         .. code-block:: bash

            xmllint --schema GoJUnitReport-JUnit.xsd --noout report.xml

.. _SCHEMAS/GoJUnitReport-JUnit/Source:

Source
******

.. literalinclude:: ../../pyEDAA/Reports/Resources/GoJUnitReport-JUnit.xsd
   :language: xml
   :linenos:
