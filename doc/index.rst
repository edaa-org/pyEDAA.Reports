.. include:: shields.inc

.. image:: _static/logo.svg
   :height: 90 px
   :align: center
   :target: https://GitHub.com/edaa-org/pyEDAA.Reports

.. raw:: html

    <br>

.. raw:: latex

   \part{Introduction}

.. only:: html

   |  |SHIELD:svg:Reports-github| |SHIELD:svg:Reports-ghp-doc| |SHIELD:svg:Reports-gitter|
   |  |SHIELD:svg:Reports-gha-test| |SHIELD:svg:Reports-codacy-quality|

.. Disabled shields: |SHIELD:svg:Reports-src-license| |SHIELD:svg:Reports-doc-license| |SHIELD:svg:Reports-pypi-tag| |SHIELD:svg:Reports-pypi-status| |SHIELD:svg:Reports-pypi-python| |SHIELD:svg:Reports-lib-status| |SHIELD:svg:Reports-codacy-coverage| |SHIELD:svg:Reports-codecov-coverage| |SHIELD:svg:Reports-lib-dep| |SHIELD:svg:Reports-req-status| |SHIELD:svg:Reports-lib-rank|

.. only:: latex

   |SHIELD:png:Reports-github| |SHIELD:png:Reports-ghp-doc| |SHIELD:png:Reports-gitter|
   |SHIELD:png:Reports-gha-test| |SHIELD:png:Reports-codacy-quality|

.. Disabled shields: |SHIELD:png:Reports-src-license| |SHIELD:png:Reports-doc-license| |SHIELD:png:Reports-pypi-tag| |SHIELD:png:Reports-pypi-status| |SHIELD:png:Reports-pypi-python| |SHIELD:png:Reports-lib-status| |SHIELD:png:Reports-codacy-coverage| |SHIELD:png:Reports-codecov-coverage| |SHIELD:png:Reports-lib-dep| |SHIELD:png:Reports-req-status| |SHIELD:png:Reports-lib-rank|

The pyEDAA.Reports Documentation
################################

This project provides abstract data models and specific implementations for report formats. Examples are unit test
summaries (like Ant JUnit XML), code coverage (like Cobertura) and documentation coverage reports.

While the data models and file format implementations can be used as a library, a CLI program will be provided too. It
allows reading, converting, concatenating, merging, transforming and writing report files.

It's also planned to support console outputs from simulators and synthesis/implementation tools to create structured
logs and reports for filtering and data extraction.


Report Formats
**************

.. grid:: 3

   .. grid-item-card::
      :columns: 4

      :ref:`Code Coverage <CODECOV>`
      ^^^

      Code coverage measures used and unused code lines, statements, branches, etc. Depending on the programming
      language this is measured by instrumenting the code/binary and running the program, it's test cases or simulating
      the code. In generate code coverage is a measure of test coverage. Unused code is not (yet) covered by tests.

      The code coverage metric in percent is a ratio of used code versus all possibly usable code. A coverage of <100%
      indicates unused code. This can be dead code (unreachable) or untested code (⇒ needs more test cases).

      **Supported tools**

      * Coverage.py / pytest-cov
      * Aldec Riviera-PRO
      * others tbd. (GHDL with enabled coverage)

      .. #  (via ACDB conversion of UCDB to UCIS format and then converted to Cobertura)

      **Supported file formats**

      * Cobertura
      * others tbd. (gcov)


   .. grid-item-card::
      :columns: 4

      :ref:`Documentation Coverage <DOCCOV>`
      ^^^

      Documentation coverage measures the presence of code documentation. It primarily counts for public language
      entities like publicly visible constants and variables, parameters, types, functions, methods, classes, modules,
      packages, etc. The documentation goal depends on the used coverage collection tool's settings. E.g. usually,
      private language entities are not required to be documented.

      The documentation coverage metric in percent is a ratio of documented language entity versus all documentation
      worthy langauge entities. A coverage of <100% indicates undocumented code.

      .. rubric:: Supported tools

      * docstr_coverage
      * others tbd. (GHDL)

      .. rubric:: Supported file formats

      * tbd.


   .. grid-item-card::
      :columns: 4

      :ref:`Unit Test Summaries <UNITTEST>`
      ^^^

      Results of (unit) tests (also regression tests) are collected in machine readable summary files. Test cases are
      usually grouped by one or more test suites. Besides the test's result (passed, failed, skipped, ...) also the
      test's outputs and durations are collected. Results can be visualized as a expandable tree structure.

      The total number of testcases indicates the spend effort in testing and applying many test vectors. In combination
      with code coverage, it can be judged if the code has untested sections.

      .. rubric:: Supported features

      * Read Ant JUnit XML files (and various dialects)
      * Merge Ant JUnit reports
      * Concatenate Ant JUnit reports
      * Transform the hierarchy of reports
      * Write Ant JUnit reports (also to other dialects)

      .. rubric:: Supported tools

      * Ant + JUnit4
      * CTest
      * GoogleTest
      * OSVVM
      * pyTest

      .. rubric:: Supported file formats

      * Ant JUnit4 XML format and various dialects
      * OSVVM YAML format


   .. #grid-item-card::
      :columns: 4

      :ref:`Tool Outputs <TOOLOUT>`
      ^^^

      .. rubric:: Supported tools

      * planned: Vivado synthesis
      * planned: Vivado implementation
      * others tbd. (GHDL)

      .. rubric:: Supported file formats

      * tbd.


.. _CONTRIBUTORS:

Contributors
************

* `Patrick Lehmann <https://GitHub.com/Paebbels>`__ (Maintainer)
* `Unai Martinez-Corral <https://GitHub.com/umarcor/>`__
* `and more... <https://GitHub.com/edaa-org/pyEDAA.Reports/graphs/contributors>`__


.. _LICENSE:

.. todo:: add license texts here

.. toctree::
   :hidden:

   Used as a layer of EDA² ➚ <https://edaa-org.github.io/>

.. toctree::
   :caption: Introduction
   :hidden:

   Installation
   Dependency


.. toctree::
   :caption: Report Formats
   :hidden:

   CodeCoverage/index
   DocCoverage/index
   Unittesting/index


.. #toctree::
   :caption: Tools
   :hidden:

   Converting
   Merging

.. toctree::
   :caption: About
   :hidden:

   Introduction
   FunctionalCoverage
   LineCoverage
   Resources
   RichLogging
   Tracking
   Frontends


.. raw:: latex

   \part{References and Reports}

.. toctree::
   :caption: References and Reports
   :hidden:

   CommandLineInterface
   pyEDAA.Reports/pyEDAA.Reports
   reports/unittests
   reports/coverage/index
   Doc. Coverage Report <reports/doccoverage>
   Static Type Check Report ➚ <reports/typing/index>


.. raw:: latex

   \part{Appendix}

.. toctree::
   :caption: Appendix
   :hidden:

   License
   Doc-License
   Glossary
   genindex
   Python Module Index <modindex>
   TODO
