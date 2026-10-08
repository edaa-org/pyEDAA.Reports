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

+------------------------+--------------+--------------+--------------+--------------------+------------------+---------------------+--------------+
| Feature                | Any JUnit    | Ant + JUnit4 | Catch2 JUnit | CTest JUnit        | GoogleTest JUnit | cargo-nextest JUnit | pyTest JUnit |
+========================+==============+==============+==============+====================+==================+=====================+==============+
| Root element           | testsuites   | testsuite    | testsuites   | testsuite          | testsuites       | testsuites          | testsuites   |
+------------------------+--------------+--------------+--------------+--------------------+------------------+---------------------+--------------+
| Supports properties    |     ☑        |     ☑        |     ☑        |                    |       ⸺          |                     |              |
+------------------------+--------------+--------------+--------------+--------------------+------------------+---------------------+--------------+
| Testcase status        | ...          | ...          | always run   | more status values |                  | reruns              |              |
+------------------------+--------------+--------------+--------------+--------------------+------------------+---------------------+--------------+

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


.. _UNITTEST/SpecificDataModel/JUnit/Dialect/nextest:

cargo-nextest JUnit
-------------------

.. grid:: 2

   .. grid-item::
      :columns: 6

      The JUnit format written by `cargo-nextest <https://github.com/nextest-rs/nextest>`__, the test runner for Rust,
      uses ``<testsuites>`` as a root element. nextest serializes it with the crate
      `quick-junit <https://github.com/nextest-rs/quick-junit>`__.

      .. rubric:: Mapping to the data model

      * ``<testsuites>``: its ``name`` is the profile's report name (``nextest-run`` by default), its ``uuid`` the run
        ID (:attr:`~pyEDAA.Reports.Unittesting.JUnit.NextestJUnit.Document.RunID`), ``timestamp`` and ``time`` the
        run's start time and duration.
      * ``<testsuite>``: one per test binary, named by its binary ID, e.g. ``counter`` for the unit tests of a library
        and ``counter::sequence`` for its integration test :file:`tests/sequence.rs`. A setup script gets a test suite
        ``@setup-script:<name>`` with one test case, and its command as ``<property>``. A ``<testsuite>`` has neither
        ``hostname``, nor ``timestamp``, nor ``time``.
      * ``<testcase>``: its ``name`` is the test's path in the binary, e.g. ``tests::failing``, its ``classname`` the
        binary ID again. In the unified data model, the test cases are therefore in a test suite (class) of the same
        name as the binary's test suite. The ``timestamp`` is kept as the test case's start time
        (:attr:`~pyEDAA.Reports.Unittesting.JUnit.NextestJUnit.Testcase.StartTime`).
      * Status: ``<failure>`` is *failed*, ``<error>`` is *errored* (e.g. the test process didn't start, or leaked
        handles), ``<skipped>`` is *skipped*, a test case without one of these *passed*.
      * Retries: a test which passed in a retry (*flaky*) has a ``<flakyFailure>`` (or ``<flakyError>``) per failed
        attempt, a test failing in every attempt a ``<rerunFailure>`` (or ``<rerunError>``) per retry. Their number is
        :attr:`~pyEDAA.Reports.Unittesting.JUnit.NextestJUnit.Testcase.RerunCount`; their output is not read. A
        failed test case carries the start time, duration and message of its first attempt, a flaky one those of its
        last attempt.

      .. rubric:: Known issues

      * A test marked ``#[ignore]`` is missing from the report, unless the profile sets ``junit.report-skipped`` to
        ``"ignored"`` or ``"all"``. The console reports ``12 tests run: 8 passed, 4 failed, 1 skipped``, the report
        ``tests="12" skipped="0"``. A reported skipped test has no ``timestamp`` and a ``time`` of zero.
      * Every failure of a Rust test is a ``<failure type="test failure with exit code 101">``: a failed assertion, a
        panic, an ``Err`` returned by the test and a ``#[should_panic]`` test which doesn't panic. Only the message (the
        first line of the error output) and the text tell them apart. The ``type`` is not kept in the data model.
      * A flaky test configured with ``flaky-result = "fail"`` is a ``<failure type="flaky failure">`` with the
        message ``test passed on attempt 2/2 but is configured to fail when flaky``.
      * A setup script counts as a test: ``tests="6"`` in a report, whose console summary is
        ``4 tests run: 2 passed (1 flaky), 2 failed, 1 skipped``.
      * The test cases are listed in the order they finished; reported skipped tests come first.
      * Writing: the run ID is written only for a document read from a nextest report, as the unified data model has no
        field for it. Reruns and the ``type`` of a ``<failure>`` are not written. The test suite summary needs a start
        time and a duration; the ``hostname``, start time and duration of a test suite are not written.

   .. grid-item::
      :columns: 6

      .. tab-set::

         .. tab-item:: Reading cargo-nextest JUnit
            :sync: ReadJUnit

            .. code-block:: Python

               from pyEDAA.Reports.Unittesting.JUnit.NextestJUnit import Document

               xmlReport = Path("target/nextest/ci/junit.xml")
               try:
                 doc = Document(xmlReport, analyzeAndConvert=True)
               except UnittestError as ex:
                 ...

         .. tab-item:: Convert to and from Unified Data Model
            :sync: ConvertToFrom

            .. code-block:: Python

               from pyEDAA.Reports.Unittesting.JUnit.NextestJUnit import Document

               # Convert to unified test data model
               summary = doc.ToTestsuiteSummary()

               # Convert back to a document
               newXmlReport = Path("New JUnit-Report.xml")
               newDoc = Document.FromTestsuiteSummary(newXmlReport, summary)

         .. tab-item:: Writing cargo-nextest JUnit
            :sync: WriteJUnit

            .. code-block:: Python

               from pyEDAA.Reports.Unittesting.JUnit.NextestJUnit import Document

               xmlReport = Path("Nextest-JUnit-Report.xml")
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
