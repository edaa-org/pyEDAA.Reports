Unittesting
###########

*pyEDAA.Reports* provides a unified and generic unittest summary data model. The data model allows the description of
testcases grouped in testsuites. Testsuites can be nested in other testsuites. The data model's root element is a
special testsuite called testsuite summary. It contains only testsuites, but no testcases.

.. todo:: UNIT:: Add data model diagram

The data model can be filled from various sources like **Ant JUnit test reports** or **OSVVM testsuite summaries** (more
to be added). Many programming languages and/or unit testing frameworks support exporting results in the Ant JUnit
format. See below for supported formats and their variations.

.. attention::

   The so called JUnit XML format is the weakest file format and standard ever seen. At first it was not created. At
   first was not created by JUnit (version 4). It was added by the built system Ant, but it's not called Ant XML format
   nor Ant JUnit XML format. The latest JUnit 5 uses a completely different format called open test reporting. As JUnit
   is not the formats author, no file format documentation nor XML schema was provided. Also Ant isn't providing any
   file format documentation or XML schema. Various Ant JUnit XML adopters have tried to reverse engineer a description
   and XML schemas, but unfortunately many are not even compatible to each other.

   .. todo::

      https://github.com/ota4j-team/open-test-reporting

.. admonition:: default box

   test text

.. rubric:: Supported Ant JUnit XMl file outputs

* pytest
* VUnit
* OSVVM (OSVVM's YAML format should be preferred due to more content and meta information)

.. rubric:: Supported proprietary file formats

* OSVVM (YAML files)


File Formats
************

Ant and JUnit 4 XML
===================


JUnit 5 XML
===========


OSVVM YAML
==========


Frameworks
**********

JUnit
=====


OSVVM
=====


pytest
======


VUnit
=====


Consumers
*********

Jenkins
=======


Dorney
======
