.. _UNITTEST/SpecificDataModel/JUnit:

JUnit Data Model
================

.. grid:: 2

   .. grid-item::
      :columns: 6

      .. grid:: 2

         .. grid-item-card::
            :columns: 6

            :ref:`UNITTEST/SpecificDataModel/JUnit/Testcase`
            ^^^
            A :dfn:`test case` is the leaf-element in the test entity hierarchy and describes an individual test run.
            Test cases are grouped by test classes.

         .. grid-item-card::
            :columns: 6

            :ref:`UNITTEST/SpecificDataModel/JUnit/Testclass`
            ^^^
            A :dfn:`test class` is the mid-level element in the test entity hierarchy and describes a group of test
            runs. Test classes are grouped by test suites.

         .. grid-item-card::
            :columns: 6

            :ref:`UNITTEST/SpecificDataModel/JUnit/Testsuite`
            ^^^
            A :dfn:`test suite` is a group of test classes. Test suites are grouped by a test suite summary.

         .. grid-item-card::
            :columns: 6

            :ref:`UNITTEST/SpecificDataModel/JUnit/TestsuiteSummary`
            ^^^
            The :dfn:`test suite summary` is derived from test suite and defines the root of the test suite hierarchy.

         .. grid-item-card::
            :columns: 6

            :ref:`UNITTEST/SpecificDataModel/JUnit/Document`
            ^^^
            The :dfn:`document` is derived from a test suite summary and represents a file containing a test suite
            summary.

         .. grid-item-card::
            :columns: 6

            :ref:`UNITTEST/SpecificDataModel/JUnit/Dialects`
            ^^^
            The JUnit format is not well defined, thus multiple dialects developed over time.

   .. grid-item::
      :columns: 6

      .. mermaid::

         graph TD;
           doc[Document]
           sum[Summary]
           ts1[Testsuite]
           ts11[Testsuite]
           ts2[Testsuite]

           tc111[Testclass]
           tc112[Testclass]
           tc23[Testclass]

           tc1111[Testcase]
           tc1112[Testcase]
           tc1113[Testcase]
           tc1121[Testcase]
           tc1122[Testcase]
           tc231[Testcase]
           tc232[Testcase]
           tc233[Testcase]

           doc:::root -.-> sum:::summary
           sum --> ts1:::suite
           sum ---> ts2:::suite
           ts1 --> ts11:::suite

           ts11 --> tc111:::cls
           ts11 --> tc112:::cls
           ts2  --> tc23:::cls

           tc111 --> tc1111:::case
           tc111 --> tc1112:::case
           tc111 --> tc1113:::case
           tc112 --> tc1121:::case
           tc112 --> tc1122:::case
           tc23 --> tc231:::case
           tc23 --> tc232:::case
           tc23 --> tc233:::case

           classDef root fill:#4dc3ff
           classDef summary fill:#80d4ff
           classDef suite fill:#b3e6ff
           classDef cls fill:#ff9966
           classDef case fill:#eeccff

.. _UNITTEST/SpecificDataModel/JUnit/Testcase:

Testcase
--------

.. _UNITTEST/SpecificDataModel/JUnit/Testclass:

Testclass
---------

.. _UNITTEST/SpecificDataModel/JUnit/Testsuite:

Testsuite
---------

.. _UNITTEST/SpecificDataModel/JUnit/TestsuiteSummary:

TestsuiteSummary
----------------

.. _UNITTEST/SpecificDataModel/JUnit/Document:

Document
--------

.. _UNITTEST/SpecificDataModel/JUnit/Dialects:

JUnit Dialects
==============

As the JUnit XML format was not well specified and no :acf:`XSD` was provided, many variants and
dialects (and simplifications) were created by the various frameworks emitting JUnit XML files.

.. rubric:: JUnit Dialect Comparison

+------------------------+--------------+--------------+--------------+--------------------+------------------+--------------+
| Feature                | Any JUnit    | Ant + JUnit4 | Catch2 JUnit | CTest JUnit        | GoogleTest JUnit | pyTest JUnit |
+========================+==============+==============+==============+====================+==================+==============+
| Root element           | testsuites   | testsuite    | testsuites   | testsuite          | testsuites       | testsuites   |
+------------------------+--------------+--------------+--------------+--------------------+------------------+--------------+
| Supports properties    |     ☑        |     ☑        |     ☑        |                    |       ⸺          |              |
+------------------------+--------------+--------------+--------------+--------------------+------------------+--------------+
| Testcase status        | ...          | ...          | always run   | more status values |                  |              |
+------------------------+--------------+--------------+--------------+--------------------+------------------+--------------+

.. _UNITTEST/SpecificDataModel/JUnit/Dialect/AnyJUnit:

Any JUnit
---------

.. grid:: 2

   .. grid-item::
      :columns: 6

      The Any JUnit format uses a relaxed XML schema definition aiming to parse many JUnit XML dialects, which use a
      ``<testsuites>`` root element.

   .. grid-item::
      :columns: 6

      .. tab-set::

         .. tab-item:: Reading Any JUnit
            :sync: ReadJUnit

            .. code-block:: Python

               from pyEDAA.Reports.Unittesting.JUnit import Document

               xmlReport = Path("AnyJUnit-Report.xml")
               try:
                 doc = Document(xmlReport, parse=True)
               except UnittestError as ex:
                 ...

         .. tab-item:: Convert to and from Unified Data Model
            :sync: ConvertToFrom

            .. code-block:: Python

               from pyEDAA.Reports.Unittesting.JUnit import Document

               # Convert to unified test data model
               summary = doc.ToTestsuiteSummary()

               # Convert back to a document
               newXmlReport = Path("New JUnit-Report.xml")
               newDoc = Document.FromTestsuiteSummary(newXmlReport, summary)

         .. tab-item:: Writing Any JUnit
            :sync: WriteJUnit

            .. code-block:: Python

               from pyEDAA.Reports.Unittesting.JUnit import Document

               xmlReport = Path("AnyJUnit-Report.xml")
               try:
                 newDoc.Write(xmlReport)
               except UnittestError as ex:
                 ...


.. _UNITTEST/SpecificDataModel/JUnit/Dialect/AntJUnit4:

Ant + JUnit4
------------

.. grid:: 2

   .. grid-item::
      :columns: 6

      The original JUnit format created by `Ant <https://github.com/apache/ant>`__ for `JUnit4 <https://github.com/junit-team/junit4>`__
      uses ``<testsuite>`` as a root element.

      :ref:`Gradle <UNITTEST/Tool/Gradle>` writes this format too, when it runs JUnit4 tests.

   .. grid-item::
      :columns: 6

      .. tab-set::

         .. tab-item:: Reading Ant + JUnit4
            :sync: ReadJUnit

            .. code-block:: Python

               from pyEDAA.Reports.Unittesting.JUnit.AntJUnit4 import Document

               xmlReport = Path("AntJUnit4-Report.xml")
               try:
                 doc = Document(xmlReport, parse=True)
               except UnittestError as ex:
                 ...

         .. tab-item:: Convert to and from Unified Data Model
            :sync: ConvertToFrom

            .. code-block:: Python

               from pyEDAA.Reports.Unittesting.JUnit.AntJUnit4 import Document

               # Convert to unified test data model
               summary = doc.ToTestsuiteSummary()

               # Convert back to a document
               newXmlReport = Path("New JUnit-Report.xml")
               newDoc = Document.FromTestsuiteSummary(newXmlReport, summary)

         .. tab-item:: Writing Ant + JUnit4
            :sync: WriteJUnit

            .. code-block:: Python

               from pyEDAA.Reports.Unittesting.JUnit.AntJUnit4 import Document

               xmlReport = Path("AnyJUnit-Report.xml")
               try:
                 newDoc.Write(xmlReport)
               except UnittestError as ex:
                 ...



.. _UNITTEST/SpecificDataModel/JUnit/Dialect/Catch2:

Catch2 JUnit
------------

.. grid:: 2

   .. grid-item::
      :columns: 6

      The Catch2 JUnit format written by the JUnit reporter of `Catch2 <https://github.com/catchorg/Catch2>`__
      (version 3) uses ``<testsuites>`` as a root element. It holds exactly one ``<testsuite>``, named after the test
      executable.

      * Each test case and each path of nested sections is a ``<testcase>``, named by its section path
        (``TestCase/Section/Subsection``). A test case or section containing sections is a ``<testcase>`` of its own.
      * The ``classname`` is ``<executable>.global``, or ``<executable>.<fixture class>`` for a test case of a fixture
        class (``::`` becomes ``.``).
      * ``SKIP()`` writes a ``<skipped>`` element, a failed assertion a ``<failure>`` element, an unexpected exception
        an ``<error>`` element. Only the first of them per ``<testcase>`` is written.
      * Each ``<testcase>`` carries ``status="run"``.

      .. rubric:: Known issues

      * The ``tests``, ``failures``, ``errors`` and ``skipped`` attributes of ``<testsuite>`` count assertions, not test
        cases. Written by pyEDAA.Reports, they count test cases.
      * The ``hostname`` attribute is always ``tbd``.
      * A test case without assertions and without output is missing.
      * A failure in a section is reported on the section's ``<testcase>`` only; the ``<testcase>`` of the enclosing
        test case passes.
      * A failure expected by ``[!mayfail]`` or ``[!shouldfail]`` writes a ``<skipped>`` element followed by a
        ``<failure>`` element. Its test case is read as skipped.
      * A ``[!shouldfail]`` test case passing unexpectedly fails for Catch2, but passes in the report.
      * The properties ``random-seed`` and ``filters`` aren't read.

   .. grid-item::
      :columns: 6

      .. tab-set::

         .. tab-item:: Reading Catch2 JUnit
            :sync: ReadJUnit

            .. code-block:: Python

               from pyEDAA.Reports.Unittesting.JUnit.Catch2JUnit import Document

               xmlReport = Path("Catch2JUnit-Report.xml")
               try:
                 doc = Document(xmlReport, parse=True)
               except UnittestError as ex:
                 ...

         .. tab-item:: Convert to and from Unified Data Model
            :sync: ConvertToFrom

            .. code-block:: Python

               from pyEDAA.Reports.Unittesting.JUnit.Catch2JUnit import Document

               # Convert to unified test data model
               summary = doc.ToTestsuiteSummary()

               # Convert back to a document
               newXmlReport = Path("New JUnit-Report.xml")
               newDoc = Document.FromTestsuiteSummary(newXmlReport, summary)

         .. tab-item:: Writing Catch2 JUnit
            :sync: WriteJUnit

            .. code-block:: Python

               from pyEDAA.Reports.Unittesting.JUnit.Catch2JUnit import Document

               xmlReport = Path("AnyJUnit-Report.xml")
               try:
                 newDoc.Write(xmlReport)
               except UnittestError as ex:
                 ...


.. _UNITTEST/SpecificDataModel/JUnit/Dialect/CTest:

CTest JUnit
-----------

.. grid:: 2

   .. grid-item::
      :columns: 6

      The CTest JUnit format written by `CTest <https://github.com/bvdberg/ctest>`__ uses ``<testsuite>`` as a root
      element.

   .. grid-item::
      :columns: 6

      .. tab-set::

         .. tab-item:: Reading CTest JUnit
            :sync: ReadJUnit

            .. code-block:: Python

               from pyEDAA.Reports.Unittesting.JUnit.CTestJUnit import Document

               xmlReport = Path("CTestJUnit-Report.xml")
               try:
                 doc = Document(xmlReport, parse=True)
               except UnittestError as ex:
                 ...

         .. tab-item:: Convert to and from Unified Data Model
            :sync: ConvertToFrom

            .. code-block:: Python

               from pyEDAA.Reports.Unittesting.JUnit.CTestJUnit import Document

               # Convert to unified test data model
               summary = doc.ToTestsuiteSummary()

               # Convert back to a document
               newXmlReport = Path("New JUnit-Report.xml")
               newDoc = Document.FromTestsuiteSummary(newXmlReport, summary)

         .. tab-item:: Writing CTest JUnit
            :sync: WriteJUnit

            .. code-block:: Python

               from pyEDAA.Reports.Unittesting.JUnit.CTestJUnit import Document

               xmlReport = Path("AnyJUnit-Report.xml")
               try:
                 newDoc.Write(xmlReport)
               except UnittestError as ex:
                 ...


.. _UNITTEST/SpecificDataModel/JUnit/Dialect/GoogleTest:

GoogleTest JUnit
----------------

.. grid:: 2

   .. grid-item::
      :columns: 6

      The GoogleTest JUnit format written by `GoogleTest <https://github.com/google/googletest>`__ (sometimes GTest)
      uses ``<testsuites>`` as a root element.

   .. grid-item::
      :columns: 6

      .. tab-set::

         .. tab-item:: Reading GoogleTest JUnit
            :sync: ReadJUnit

            .. code-block:: Python

               from pyEDAA.Reports.Unittesting.JUnit.GoogleTestJUnit import Document

               xmlReport = Path("GoogleTestJUnit-Report.xml")
               try:
                 doc = Document(xmlReport, parse=True)
               except UnittestError as ex:
                 ...

         .. tab-item:: Convert to and from Unified Data Model
            :sync: ConvertToFrom

            .. code-block:: Python

               from pyEDAA.Reports.Unittesting.JUnit.GoogleTestJUnit import Document

               # Convert to unified test data model
               summary = doc.ToTestsuiteSummary()

               # Convert back to a document
               newXmlReport = Path("New JUnit-Report.xml")
               newDoc = Document.FromTestsuiteSummary(newXmlReport, summary)

         .. tab-item:: Writing GoogleTest JUnit
            :sync: WriteJUnit

            .. code-block:: Python

               from pyEDAA.Reports.Unittesting.JUnit.GoogleTestJUnit import Document

               xmlReport = Path("AnyJUnit-Report.xml")
               try:
                 newDoc.Write(xmlReport)
               except UnittestError as ex:
                 ...


.. _UNITTEST/SpecificDataModel/JUnit/Dialect/pyTest:

pyTest JUnit
------------

.. grid:: 2

   .. grid-item::
      :columns: 6

      The pyTest JUnit format written by `pyTest <https://github.com/pytest-dev/pytest>`__ uses ``<testsuites>`` as a
      root element.

   .. grid-item::
      :columns: 6

      .. tab-set::

         .. tab-item:: Reading pyTest JUnit
            :sync: ReadJUnit

            .. code-block:: Python

               from pyEDAA.Reports.Unittesting.JUnit.PyTestJUnit import Document

               xmlReport = Path("PyTestJUnit-Report.xml")
               try:
                 doc = Document(xmlReport, parse=True)
               except UnittestError as ex:
                 ...

         .. tab-item:: Convert to and from Unified Data Model
            :sync: ConvertToFrom

            .. code-block:: Python

               from pyEDAA.Reports.Unittesting.JUnit.PyTestJUnit import Document

               # Convert to unified test data model
               summary = doc.ToTestsuiteSummary()

               # Convert back to a document
               newXmlReport = Path("New JUnit-Report.xml")
               newDoc = Document.FromTestsuiteSummary(newXmlReport, summary)

         .. tab-item:: Writing pyTest JUnit
            :sync: WriteJUnit

            .. code-block:: Python

               from pyEDAA.Reports.Unittesting.JUnit.PyTestJUnit import Document

               xmlReport = Path("AnyJUnit-Report.xml")
               try:
                 newDoc.Write(xmlReport)
               except UnittestError as ex:
                 ...
