.. image:: _static/logo.svg
   :height: 90 px
   :align: center
   :target: https://GitHub.com/edaa-org/pyEDAA.Reports

.. raw:: html

    <br>

.. raw:: latex

   \part{Introduction}

.. shields::
   :github:        edaa-org/pyEDAA.Reports
   :gitter:        hdl/community
   :codacy:        f8142b422c1742bdba38e8ac1893870c
   :github-action: Pipeline.yml
   :documentation: github-pages

   github, ghp-doc, gitter
   github-action, codacy-quality

The pyEDAA.Reports Documentation
################################

A collection of various (EDA tool-specific) report data formats.

.. _GOALS:

Main Goals
**********

This package provides abstract data models and specific implementations for report formats. The supported report formats
are commonly used for any programming language or have a specifc context with Electronic Design Automation (EDA) tools.
Examples are unit test summaries (like Ant JUnit XML), code coverage (like Cobertura) and documentation coverage reports.

While the data models and file format implementations can be used as a library, a CLI program ``pyedaa-report`` will be
provided too. It allows reading, converting, concatenating, merging, transforming and writing report files.

.. admonition:: Roadmap

   It's also planned to support console outputs from simulators and synthesis/implementation tools to create structured
   logs and reports for filtering and data extraction.






Report Formats
**************

.. grid:: 3

   .. grid-item-card::
      :columns: 4

      :ref:`🚧 Code Coverage <CODECOV>`
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

      :ref:`🚧 Documentation Coverage <DOCCOV>`
      ^^^

      Documentation coverage measures the presence of code documentation. It primarily counts for public language
      entities like publicly visible constants and variables, parameters, types, functions, methods, classes, modules,
      packages, etc. The documentation goal depends on the used coverage collection tool's settings. E.g. usually,
      private language entities are not required to be documented.

      The documentation coverage metric in percent is a ratio of documented language entity versus all documentation
      worthy langauge entities. A coverage of <100% indicates undocumented code.

      .. rubric:: Supported tools

      * `docstr_coverage <https://github.com/HunterMcGushion/docstr_coverage>`__
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

      * :ref:`Read Ant JUnit XML files (and various dialects) <UNITTEST/Feature/Read>`
      * :ref:`Merge Ant JUnit reports <UNITTEST/Feature/Merge>`
      * :ref:`Concatenate Ant JUnit reports <UNITTEST/Feature/Concat>`
      * :ref:`Transform the hierarchy of reports <UNITTEST/Feature/Transform>`
      * :ref:`Write Ant JUnit reports (also to other dialects) <UNITTEST/Feature/Write>`

      .. rubric:: Supported file formats

      * :ref:`Ant JUnit4 XML format and various dialects <UNITTEST/FileFormats/AntJUnit4>`
      * :ref:`JUnit5 XML format (Open Test Reporting) <UNITTEST/FileFormats/JUnit5>`

      .. rubric:: Supported tools

      * :ref:`Catch2 <UNITTEST/Tool/Catch2>`
      * :ref:`CTest <UNITTEST/Tool/CTest>`
      * :ref:`GoogleTest <UNITTEST/Tool/GoogleTest>`
      * :ref:`Ant + JUnit4 <UNITTEST/Tool/JUnit4>`
      * :ref:`JUnit5 <UNITTEST/Tool/JUnit5>`
      * :ref:`OSVVM <UNITTEST/Tool/OSVVM>`
      * :ref:`pyTest <UNITTEST/Tool/pytest>`

      .. note::

         OSVVM YAML format
           The YAML format for test results of OSVVM has been moved to `pyEDAA.OSVVM <https://edaa-org.github.io/pyEDAA.OSVVM/>`__
           to group with other OSVVM specific formats.

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


.. _CONSUMERS:

Consumers
*********

This layer is used by:

* `pyTooling/Actions → PublishTestResults <https://github.com/pyTooling/Actions/>`__
* 🚧 `pyTooling/Sphinx-Reports <https://github.com/pyTooling/sphinx-reports>`__
* 🚧 `pyTooling/pyTooling.Sphinx <https://github.com/pyTooling/pyTooling.Sphinx>`__ - its domain ``report``


.. _CONTRIBUTORS:

Contributors
************

* :gh:`Patrick Lehmann <Paebbels>` (Maintainer)
* :gh:`Unai Martinez-Corral <umarcor>`
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
   Logging/index


.. #toctree::
   :caption: Tools
   :hidden:

   Converting
   Merging


.. raw:: latex

   \part{References and Reports}

.. toctree::
   :caption: References and Reports
   :hidden:

   CommandLineInterface
   Python Class Reference <pyEDAA.Reports/pyEDAA.Reports>
   unittests/index
   coverage/index
   CodeCoverage
   Doc. Coverage Report <DocCoverage>
   Static Type Check Report ➚ <typing/index>
   Schemas/index

.. raw:: latex

   \part{Appendix}

.. toctree::
   :caption: Appendix
   :hidden:

   License
   Doc-License
   Abbreviations
   Glossary
   genindex
   Python Module Index <modindex>
   TODO


.. toctree::
   :caption: Old Content
   :hidden:

   old/Introduction
   old/FunctionalCoverage
   old/LineCoverage
   old/Resources
   old/RichLogging
   old/Tracking
   old/Frontends
