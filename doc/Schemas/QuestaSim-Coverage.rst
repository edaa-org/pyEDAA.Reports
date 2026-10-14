.. _SCHEMAS/QuestaSim-Coverage:

QuestaSim Coverage
##################

QuestaSim's code coverage report XML, as ``vcover report -xml -details`` or ``coverage report -xml -details`` writes it.

Read by :class:`pyEDAA.Reports.CodeCoverage.QuestaSim.Document` - see :ref:`CODECOV/Formats/QuestaSim`.

Questa states neither a namespace nor a format version, and publishes no XML Schema. The schema is built from three
sources:

* A report of Questa 2026.2, written with ``vcover report -xml -details -code bcesf``: the root's attributes
  ``questa_version`` and ``command``; ``lines``, ``byInstance``, ``<instanceData>`` with ``<sourceTable>`` and
  ``<fileMap>``, the coverage statistics ``<branches>``, ``<states>``, ``<transitions>`` and ``<statements>``, and the
  coverage items ``<stmt>``, ``<if>``/``<ielem>``, ``<case>``/``<celem>``, ``<state>`` and ``<trans>``.
* The example of Questa's User's Manual and a report of Questa 2023.3 by design unit: ``byDU``, ``<DuData>``.
* ModelSim's DTD ``covreport.dtd`` for the elements no Questa report shows yet: the summary records, ``<fileData>``, and
  the details of conditions, expressions and toggles.

A scope's ``<sourceTable>`` comes first; its statistics and coverage items follow in any order - Questa 2026.2 writes
them in another order than the DTD -, except a finite state machine's: ``<states>``, ``<transitions>``, then each
``<state>`` and each ``<trans>``. A file number must be one of the scope's source table; ``<state>`` and ``<trans>``
name none. Attributes are typed: counts are non-negative integers, line numbers positive, a percentage is a decimal from
0 to 100. Functional coverage reports (``-cvg``, ``-directive``) aren't covered.

.. grid:: 2

   .. grid-item::
      :columns: 6

      .. admonition:: Download

         :download:`QuestaSim-Coverage.xsd <../../pyEDAA/Reports/Resources/QuestaSim-Coverage.xsd>`

   .. grid-item::
      :columns: 6

      .. admonition:: Validate a report

         .. code-block:: bash

            xmllint --schema QuestaSim-Coverage.xsd --noout CoverageReport.xml

.. _SCHEMAS/QuestaSim-Coverage/Source:

Source
******

.. literalinclude:: ../../pyEDAA/Reports/Resources/QuestaSim-Coverage.xsd
   :language: xml
   :linenos:
