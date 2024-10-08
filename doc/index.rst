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

Proposal to define an abstract model for outputs from EDA tools and logging libraries.

.. image:: _static/work-in-progress.png
   :height: 275 px
   :align: center
   :target: https://GitHub.com/edaa-org/pyEDAA.Reports

.. raw:: html

    <br>


.. rubric:: Supported Ant JUnit XMl file outputs

* pytest
* VUnit
* OSVVM (OSVVM's YAML format should be preferred due to more content and meta information)

.. rubric:: Supported proprietary file formats

* OSVVM (YAML files)


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
