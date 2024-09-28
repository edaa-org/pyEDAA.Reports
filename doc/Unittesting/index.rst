.. _UNITTEST:

Unittesting
###########

*pyEDAA.Reports* provides a unified and generic unittest summary data model. The data model allows the description of
testcases grouped in testsuites. Testsuites can be nested in other testsuites. The data model's root element is a
special testsuite called testsuite summary. It contains only testsuites, but no testcases.

The data model can be filled from various sources like **Ant JUnit test reports** or **OSVVM testsuite summaries** (more
to be added). Many programming languages and/or unit testing frameworks support exporting results in the Ant JUnit
format. See below for supported formats and their variations (dialects).

.. topic:: Unit Test Summary Report - Data Model

   .. mermaid::

      graph TD;
        doc[Document]
        sum[Summary]
        ts1[Testsuite]
        ts2[Testsuite]
        ts21[Testsuite]
        tc11[Testcase]
        tc12[Testcase]
        tc13[Testcase]
        tc21[Testcase]
        tc22[Testcase]
        tc211[Testcase]
        tc212[Testcase]
        tc213[Testcase]

        doc:::root --> sum:::summary
        sum --> ts1:::suite
        sum --> ts2:::suite
        ts2 --> ts21:::suite
        ts1 --> tc11:::case
        ts1 --> tc12:::case
        ts1 --> tc13:::case
        ts2 --> tc21:::case
        ts2 --> tc22:::case
        ts21 --> tc211:::case
        ts21 --> tc212:::case
        ts21 --> tc213:::case

        classDef root fill:#4dc3ff
        classDef summary fill:#80d4ff
        classDef suite fill:#b3e6ff
        classDef case fill:#eeccff


.. attention::

   The so called JUnit XML format is the weakest file format and standard ever seen. At first was not created by JUnit
   (version 4). It was added by the built system Ant, but it's not called Ant XML format nor Ant JUnit XML format. The
   latest JUnit 5 uses a completely different format called open test reporting. As JUnit is not the formats author, no
   file format documentation nor XML schema was provided. Also Ant isn't providing any file format documentation or XML
   schema. Various Ant JUnit XML adopters have tried to reverse engineer a description and XML schemas, but
   unfortunately many are not even compatible to each other.

   .. todo::

      https://github.com/ota4j-team/open-test-reporting

.. _UNITTEST/Features:

Features
********

Unified data model
==================

Reading unittest reports
========================


Merging unittest reports
========================

Concatenate unittest reports
============================


Transforming the reports' hierarchy
===================================

pytest specific transformations
-------------------------------


Writing unittest reports
========================


Command Line Tool
=================

.. code-block:: bash

   pyedaa-reports unittest --input=Ant-JUnit:data/JUnit.xml


.. _UNITTEST/FileFormats:

File Formats
************

Unittest summary reports can be stored in various file formats. Usually these files are XML based. Due to missing
(clear) specifications and XML schema definitions, some file formats have developed dialects. Either because the
specification was unclear/not existing or because the format was specific for a single programming language, so tools
added extensions or misused XML attributes instead of designing their own file format.

.. _UNITTEST/FileFormats/AntJUnit4:

Ant and JUnit 4 XML
===================

.. rubric:: Dialects

* CTest JUnit format
* GoogleTest JUnit format
* pyTest JUnit format


.. _UNITTEST/FileFormats/JUnit5:

JUnit 5 XML
===========

https://github.com/ota4j-team/open-test-reporting


.. _UNITTEST/FileFormats/OSVVM:

OSVVM YAML
==========

https://github.com/OSVVM/OSVVM-Scripts


.. _UNITTEST/Tools:

Frameworks / Tools
******************

.. _UNITTEST/Tool/CTest:

CTest
=====

* https://github.com/bvdberg/ctest


.. _UNITTEST/Tool/GoogleTest:

GoogleTest (gtest)
==================

* https://github.com/google/googletest


.. _UNITTEST/Tool/JUnit4:

JUnit4
======

* https://github.com/apache/ant
* https://github.com/junit-team/junit4


.. _UNITTEST/Tool/JUnit5:

JUnit5
======


.. _UNITTEST/Tool/OSVVM:

OSVVM
=====

* https://github.com/OSVVM/OSVVM
* https://github.com/OSVVM/OSVVM-Scripts


.. _UNITTEST/Tool/pytest:

pytest
======

* https://github.com/pytest-dev/pytest


.. _UNITTEST/Tool/VUnit:

VUnit
=====

* https://github.com/VUnit/vunit


.. _UNITTEST/Consumers:


Consumers
*********

.. _UNITTEST/Consumer/GitLab:

GitLab
======

.. _UNITTEST/Consumer/Jenkins:

Jenkins
=======


.. _UNITTEST/Consumer/Dorney:

Dorney (GitHub Action)
======================

* https://github.com/dorny/test-reporter
