.. _UNITTEST:

Unittesting
###########

*pyEDAA.Reports* provides a unified and generic unittest summary data model. The data model allows the description of
testcases grouped in testsuites. Testsuites can be nested in other testsuites. The data model's root element is a
special testsuite called testsuite summary. It contains only testsuites, but no testcases.

The data model can be filled from various sources like **Ant JUnit test reports**, **Open Test Reporting files**,
**pyTooling test reports** or **OSVVM testsuite summaries** (more to be added). Many programming languages and/or unit
testing frameworks support exporting results in the Ant JUnit format. See below for supported formats and their
variations (dialects).

.. attention::

   The so called JUnit XML format is the weakest file format and standard ever seen. At first was not created by JUnit
   (version 4). It was added by the built system Ant, but it's not called Ant XML format nor Ant JUnit XML format. The
   latest JUnit 5 uses a completely different format called :ref:`open test reporting <UNITTEST/FileFormats/OTR>`. As
   JUnit is not the formats author, no file format documentation nor XML schema was provided. Also Ant isn't providing
   any file format documentation or XML schema. Various Ant JUnit XML adopters have tried to reverse engineer a
   description and XML schemas, but unfortunately many are not even compatible to each other.


.. include:: DataModel.rst

.. _UNITTEST/SpecificDataModels:

Specific Data Models
********************

.. include:: JUnitDataModel.rst
.. include:: OpenTestReportingDataModel.rst
.. include:: OSVVMDataModel.rst


.. include:: Features.rst



.. _UNITTEST/CLI:

Command Line Tool
*****************

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

The so-called JUnit XML format was defined by Ant when running JUnit4 test suites. Because the format was not specified
by JUnit4, many dialects spread out. Many tools and test frameworks have minor or major differences compared to the
original format. While some modifications seam logical additions or adjustments to the needs of the respective
framework, others undermine the ideas and intents of the data format.

Many issues arise because the :ref:`Ant + JUnit4 <UNITTEST/SpecificDataModel/JUnit/Dialect/AntJUnit4>` format is
specific to unit testing with Java. Other languages and frameworks were lazy and didn't derive their own format, but
rather stuffed their language constructs into the concepts and limitations of the Ant + JUnit4 XML format.

.. rubric:: JUnit Dialects

* 🚧 Bamboo JUnit (planned)
* 🚧 Catch2 JUnit (planned)
* ✅ :ref:`CTest JUnit format <UNITTEST/SpecificDataModel/JUnit/Dialect/CTest>`
* ✅ :ref:`GoogleTest JUnit format <UNITTEST/SpecificDataModel/JUnit/Dialect/GoogleTest>`
* 🚧 Jenkins JUnit (planned)
* 🚧 :ref:`JunitXml.TestLogger <UNITTEST/Tool/DotNetTest>` for ``dotnet test`` (planned)
* 🚧 nextest JUnit (planned)
* ✅ :ref:`pyTest JUnit format <UNITTEST/SpecificDataModel/JUnit/Dialect/PyTest>`


.. _UNITTEST/FileFormats/JUnit5:

JUnit 5 XML
===========

JUnit5 uses a new format called :ref:`UNITTEST/FileFormats/OTR` (see the following section for details). This format
isn't specific to Java (packages, classes, methods, ...), but describes a generic data model. Of cause an extension for
Java specifics is provided too.

The JUnit Platform writes this format only on request (``junit.platform.reporting.open.xml.enabled=true``). Build tools
like Gradle write :ref:`Ant + JUnit4 XML <UNITTEST/FileFormats/AntJUnit4>` for JUnit 5 and 6 tests by default, see
:ref:`UNITTEST/Tool/JUnit5`.


.. _UNITTEST/FileFormats/OTR:

Open Test Reporting
===================

The `Open Test Alliance <https://github.com/ota4j-team>`__ created a new format called
`Open Test Reporting <https://github.com/ota4j-team/open-test-reporting>`__ (OTR) to overcome the shortcommings of a
missing file format for JUnit5 as well as the problems of Ant + JUnit4.

OTR defines a structure of test groups and tests, but no specifics of a certain programming languge. The logical
structure of tests and test groups is decoupled from language specifics like namespaces, packages or classes hosting the
individual tests.

The JUnit Platform writes OTR's event-based format into :file:`open-test-report.xml`:

* The root element ``<e:events>`` holds an ``<infrastructure>`` element (host name, user name, operating system, Java
  version, ...) and one event element per state change.
* ``<e:started>`` opens a container (test engine, class, nested class, parameterized test) or a test with an ``id``, a
  ``parentId`` and a ``name`` - the display name. Its ``<metadata>`` carries tags and JUnit's unique ID, its
  ``<sources>`` the Java class or method.
* ``<e:reported>`` adds attachments while it runs: ``TestReporter`` entries and captured output on STDOUT and STDERR.
* ``<e:finished>`` closes it with a ``<result>`` of status ``SUCCESSFUL``, ``FAILED``, ``ABORTED`` (a failed
  assumption) or ``SKIPPED`` (a disabled test), with the exception or the reason.
* Every event has a ``time`` in UTC with nanoseconds, e.g. ``2026-10-08T10:56:04.172060276Z``.

The event-based format is read by :class:`pyEDAA.Reports.Unittesting.OpenTestReporting.Events.Document` and converted
into the unified data model, see :ref:`UNITTEST/SpecificDataModel/OTR`. The file is validated against the
:ref:`schemas <SCHEMAS/OpenTestReporting>`, which Open Test Reporting publishes for each namespace.

OTR's command line tool converts the event-based format into its hierarchical format. *pyEDAA.Reports* doesn't read the
hierarchical format yet.


.. _UNITTEST/FileFormats/pyTooling:

pyTooling Test Report
=====================

`pyTooling <https://github.com/pyTooling/pyTooling>`__ provides a pytest plugin writing a test report in a format of
its own (pytest option ``--pytooling-xml=PATH``). Unlike JUnit XML, test suites nest, and every test suite and test case
can carry a title, a summary and a description besides its name. The format is defined by an XML schema; its version is
part of the schema's file name (e.g. ``TestReport-v0.1.xsd``), which every report names in its
``xsi:noNamespaceSchemaLocation`` attribute.

The report is read by :class:`pyEDAA.Reports.Unittesting.pyTooling.Document` into the unified data model.


.. _UNITTEST/FileFormats/TRX:

Visual Studio Test Results (TRX)
================================

Visual Studio and ``dotnet test`` (VSTest) write a test run's results as TRX file (``--logger trx``): XML in namespace
``http://microsoft.com/schemas/VisualStudio/TeamTest/2010`` with root ``<TestRun>``. Its children are:

``<Times>``
  Creation, start and finish of the test run.

``<Results>``
  A ``<UnitTestResult>`` per test: name, duration, start and end time, and its ``outcome`` (e.g. ``Passed``,
  ``Failed``, ``NotExecuted``). ``<Output>`` holds the test's standard output and, in ``<ErrorInfo>``, the message and
  stack trace of a failed test or the reason of a skipped one.

``<TestDefinitions>``
  A ``<UnitTest>`` per test, naming the assembly, the class and the method of a test in ``<TestMethod>``. Each data
  row of a parameterized test is a test of its own.

``<TestEntries>``, ``<TestLists>``
  Link results and definitions by GUIDs.

``<ResultSummary>``
  The run's outcome and ``<Counters>`` (``total``, ``executed``, ``passed``, ``failed``, ``notExecuted``, ...), the
  run's output and the attachments of data collectors, e.g. code coverage reports.

There is no reader yet.


.. _UNITTEST/FileFormats/OSVVM:

OSVVM YAML
==========

The `Open Source VHDL Verification Methodology (OSVVM) <https://github.com/OSVVM>`__ defines its own test report format
in YAML. While OSVVM is able to convert its own YAML files to JUnit XML files, it's recommended to use the YAML files as
data source, because these contain additional information, which can't be expressed with JUnit XML.

The YAML files are created when OSVVM-based testbenches are executed with OSVVM's embedded TCL scripting environment
`OSVVM-Scripts <https://github.com/OSVVM/OSVVM-Scripts>`__.

.. hint::

   YAML was chosen instead of JSON or XML, because a YAML document isn't corrupted in case of a runtime error. The
   document might be incomplete (content), but not corrupted (structural). Such a scenario is possible if a VHDL
   simulator stops execution, then the document structure can't be finalized.




.. _UNITTEST/Tools:

Frameworks / Tools
******************

.. _UNITTEST/Tool/nextest:

cargo-nextest
=============

* https://github.com/nextest-rs/nextest

Rust's test harness (``libtest``, run by ``cargo test``) writes JUnit XML only on a nightly compiler
(``-Z unstable-options --format junit``), one document per test binary on standard output. The test runner
cargo-nextest writes one JUnit XML report per run, if the profile in :file:`.config/nextest.toml` names it, e.g.
``[profile.ci.junit]`` with ``path = "junit.xml"``; ``cargo nextest run --profile ci`` writes it to
:file:`target/nextest/ci/junit.xml`.

The report has a ``<testsuites>`` root named ``nextest-run`` with a ``uuid`` attribute, and a ``<testsuite>`` per test
binary, named after the crate - ``counter`` for the unit tests in the library, ``counter::sequence`` for the
integration test :file:`tests/sequence.rs`. A ``<testcase>``'s name is the test's path in its crate, e.g.
``tests::increment``, its ``classname`` the ``<testsuite>``'s name. Each ``<testcase>`` carries its start time in a
``timestamp`` attribute, and the test's output in ``<system-out>`` and ``<system-err>``. A failed assertion, a panic,
an ``Err`` returned by a test and a ``#[should_panic]`` test that doesn't panic are each a ``<failure>`` of type
``test failure with exit code 101``. Its message is the first line of the test's error output, e.g.
``thread 'tests::failing' (554412) panicked at src/lib.rs:100:9`` or ``Error: Underflow``.

Unlike Ant JUnit4, a test marked ``#[ignore]`` isn't in the report at all, the ``<testsuite>`` has neither
``timestamp``, ``time`` nor ``hostname``, and the test cases are listed in the order they finished. Doc-tests aren't
run by cargo-nextest. Except for ``uuid`` on ``<testsuites>`` and ``timestamp`` on ``<testcase>``, the report is
:ref:`Any JUnit <UNITTEST/SpecificDataModel/JUnit/Dialect/AnyJUnit>`; no dialect reads it yet.

The example in :file:`examples/Rust/Cargo` is run by the pipeline job ``Rust-Cargo``. It measures the code coverage by
Rust's source-based coverage (``-C instrument-coverage``) with cargo-llvm-cov, and writes it as LLVM JSON
(``llvm-cov export`` format), lcov tracefile and Cobertura XML by cargo-llvm-cov, and as lcov tracefile, Cobertura XML
and covdir JSON by grcov.


.. _UNITTEST/Tool/Catch2:

Catch2
======

* https://github.com/catchorg/Catch2

Catch2 (version 3) writes a report per reporter given on its command line, e.g.
``--reporter JUnit::out=catch2-junit.xml --reporter XML::out=catch2.xml``:

JUnit reporter
  A ``<testsuites>`` root without attributes, holding one ``<testsuite>`` named after the test executable. Each test
  case and each path of nested sections (``TestCase/Section/Subsection``) is a ``<testcase>``; its ``classname`` is
  ``<executable>.global``, or ``<executable>.<fixture class>`` for a test case of a fixture class. ``SKIP()`` writes a
  ``<skipped>`` element, an exception escaping a test case an ``<error>`` element. Unlike Ant JUnit4, the
  ``<testsuite>``'s ``tests`` attribute counts assertions (skips included), not test cases, ``hostname`` is ``tbd``,
  and each ``<testcase>`` carries ``status="run"``. Except for this ``status`` attribute, the report is
  :ref:`Any JUnit <UNITTEST/SpecificDataModel/JUnit/Dialect/AnyJUnit>`; no dialect reads it yet.

XML reporter
  Catch2's own format (root ``<Catch2TestRun>``, ``xml-format-version="3"``): nested ``<TestCase>`` and ``<Section>``
  elements with tags, source file and line, every failed expression and the result counts. It isn't JUnit XML.

The example in :file:`examples/Cpp/Catch2` is built and run by the pipeline job ``Cpp-Catch2``. It measures the code
coverage of the tested library with GCC (``--coverage``) and writes it as gcov JSON (``gcov --json-format``) and as
lcov tracefile (``lcov --capture``).


.. _UNITTEST/Tool/CTest:

CTest
=====

* https://github.com/bvdberg/ctest


.. _UNITTEST/Tool/DotNetTest:

dotnet test (VSTest)
====================

* https://learn.microsoft.com/en-us/dotnet/core/tools/dotnet-test
* https://github.com/spekt/junit.testlogger
* https://xunit.net/

``dotnet test`` runs the tests of a .NET test project with VSTest, whatever test framework the tests are written in
(e.g. xUnit.net, NUnit, MSTest). Each logger given on its command line writes a report:

``--logger trx``
  A :ref:`TRX file <UNITTEST/FileFormats/TRX>`, Visual Studio's own format.

``--logger junit`` (NuGet package ``JunitXml.TestLogger``)
  A ``<testsuites>`` root without attributes, holding one ``<testsuite>`` per test assembly, named after the
  assembly's file (e.g. ``MyLibrary.Tests.dll``). Each test is a ``<testcase>``; its ``classname`` is the test class,
  its ``name`` the method, followed by the arguments of a parameterized test, e.g. ``Absolute(value: -4, expected: 5)``.
  The test cases follow in the order they finished, not grouped by class. Compared to Ant + JUnit4, the logger writes:

  * the additional attributes ``id`` and ``package`` on ``<testsuite>``. Only these keep the
    :ref:`Any JUnit <UNITTEST/SpecificDataModel/JUnit/Dialect/AnyJUnit>` and
    :ref:`pyTest JUnit <UNITTEST/SpecificDataModel/JUnit/Dialect/pyTest>` dialects from reading the report.
  * an exception escaping a test as ``<failure>``, never as ``<error>``: VSTest knows failed tests only. The
    exception's type and message are in the ``message`` attribute, the stack trace is the element's text.
  * a skipped test as an empty ``<skipped/>``, without its reason. The TRX file keeps the reason.
  * the test framework's messages of the whole run into ``<system-out>`` and ``<system-err>`` of the ``<testsuite>``.

The example in :file:`examples/CSharp/xUnit` - a class library and its xUnit.net test project - is built and run by
the pipeline job ``CSharp-xUnit``. It writes both reports and measures the code coverage with coverlet and with
Microsoft's code coverage collector (see :ref:`CODECOV/Tool/DotNet`).


.. _UNITTEST/Tool/Go:

Go (go test)
============

* https://pkg.go.dev/testing
* https://github.com/gotestyourself/gotestsum
* https://github.com/jstemmer/go-junit-report

``go test`` writes no JUnit XML: it prints text, or with ``-json`` a stream of JSON events (``test2json``), one object
per line. Converters translate it to JUnit XML:

gotestsum
  ``gotestsum --junitfile gotestsum.xml --jsonfile go-test.json -- ./...`` runs ``go test -json`` and writes a
  ``<testsuites>`` root with a ``<testsuite>`` per package - also for a package without tests -, each with the property
  ``go.version``. Each test, subtest (``TestName/Subtest``) and example is a ``<testcase>``; a parent test is a test
  case of its own beside its subtests. ``classname`` is the package's import path. A failure and a panic write a
  ``<failure>`` with the test's output, ``t.Skip`` a ``<skipped>`` with the test's output in its ``message`` attribute.
  Unlike Ant JUnit4, a ``<testsuite>`` has no ``hostname`` and ``errors``, and ``skipped`` only if a test was skipped.
  ``--junitfile-testsuite-name`` and ``--junitfile-testcase-classname`` shorten the import path to its last element
  (``short``) or to the path relative to the module (``relative``), ``--junitfile-project-name`` names the
  ``<testsuites>``. The report is :ref:`Any JUnit <UNITTEST/SpecificDataModel/JUnit/Dialect/AnyJUnit>`.

go-junit-report
  ``go-junit-report -parser gojson -in go-test.json -out go-junit-report.xml`` converts the JSON events - by default
  ``go test -v``'s text output. It writes the same tree, but a test's log in the test case's ``<system-out>``, a panic's
  stack trace in the package's ``<system-out>``, and ``id``, ``hostname`` and ``timestamp`` - of the conversion - on
  each ``<testsuite>``; a package without tests is a ``<testsuite>`` with an empty name. Except for the ``id``
  attribute, the report is :ref:`Any JUnit <UNITTEST/SpecificDataModel/JUnit/Dialect/AnyJUnit>`; no dialect reads it
  yet.

A panic ends the package's test binary: the package's later tests don't run, and its code coverage is lost.

The example in :file:`examples/Go/testing` is built and run by the pipeline job ``Go-Test``. It measures the code
coverage as Go cover profile and converts it to Cobertura XML and lcov tracefile, see
:ref:`CODECOV/Formats/GoCoverProfile`.


.. _UNITTEST/Tool/GoogleTest:

GoogleTest (gtest)
==================

* https://github.com/google/googletest

The pipeline job ``Cpp-GoogleTest`` runs the tests in :file:`examples/Cpp/GoogleTest` directly and by CTest, writing
GoogleTest's and CTest's JUnit XML reports. The library is compiled with ``--coverage``; gcov writes the
:ref:`gcov JSON <CODECOV/Formats/Gcov>` report of the direct run.


.. _UNITTEST/Tool/Gradle:

Gradle
======

* https://github.com/gradle/gradle
* https://docs.gradle.org/current/userguide/java_testing.html

Gradle's ``test`` task writes one Ant + JUnit4 XML file per test class into :file:`build/test-results/test/`, named
:file:`TEST-<class>.xml` like Ant's. The
:ref:`Ant + JUnit4 dialect <UNITTEST/SpecificDataModel/JUnit/Dialect/AntJUnit4>` reads them. The example
:file:`examples/Java/Gradle-JUnit4` runs JUnit 4 tests by Gradle in the pipeline. Compared to Ant's ``<junit>`` task,
Gradle writes:

* an exception other than a failed assertion as ``<failure>``, never as ``<error>``. ``errors`` is always ``0``.
* an empty ``<properties/>`` element. Ant lists the JVM's system properties and the build's properties.
* ``timestamp`` in UTC with milliseconds, e.g. ``2026-10-08T10:41:52.384Z``. Ant writes the local time without
  fraction or time zone.
* an ignored test (``@Ignore``) as an empty ``<skipped/>``, without the reason, and a failed assumption as
  ``<skipped>`` with ``message``, ``type`` and the stack trace. Ant writes both as ``<skipped message="..."/>``.
* the exception's class name and message into ``message`` of ``<failure>``, and the unfiltered stack trace as its text.
  Ant writes the exception's message only and removes JUnit's and Ant's stack frames.


.. _UNITTEST/Tool/JUnit4:

JUnit4
======

* https://github.com/apache/ant
* https://github.com/junit-team/junit4


.. _UNITTEST/Tool/JUnit5:

JUnit5
======

* https://github.com/junit-team/junit-framework
* https://docs.junit.org/

JUnit 5 and its successor JUnit 6 run tests on the JUnit Platform. The examples :file:`examples/Java/Gradle-JUnit5`
and :file:`examples/Java/Gradle-JUnit6` run JUnit 5 and JUnit 6 tests by `Gradle <https://github.com/gradle/gradle>`__
in the pipeline and write both: Gradle's Ant + JUnit4 XML files, read by the
:ref:`Ant + JUnit4 dialect <UNITTEST/SpecificDataModel/JUnit/Dialect/AntJUnit4>`, and the JUnit Platform's
:ref:`Open Test Reporting <UNITTEST/FileFormats/OTR>` file, read by
:class:`~pyEDAA.Reports.Unittesting.OpenTestReporting.Events.Document`. Compared to JUnit 4 tests, Gradle's files
differ:

* The test suite is named by the test class' display name (``@DisplayName``), the file by the class' name.
* A test case is named by its display name: the method name with its parameter types, e.g. ``testReturnTrue()``, or
  ``@DisplayName``. An invocation of a parameterized test is named by its index and arguments only, e.g.
  ``[1] 5, 5``, so the invocations of two parameterized tests of one class can have the same names.
* A nested test class (``@Nested``) is a test suite in a file of its own, e.g.
  :file:`TEST-my.pack.MyClassTest$Divide.xml`.
* ``TestReporter`` entries and, if the JUnit Platform captures the output, STDOUT and STDERR are ``<property>``
  elements of the ``<testcase>``.
* A disabled test (``@Disabled``) is an empty ``<skipped/>``, without the reason. A failed assumption is a
  ``<skipped>`` with ``message``, ``type`` and the stack trace.
* The JUnit Platform removes JUnit's and Gradle's stack frames calling the test method from stack traces; the JDK's
  frames remain.
* Compared to JUnit 5, JUnit 6 quotes the arguments in the display name of a parameterized test (``[1] "5", "5"``
  instead of ``[1] 5, 5``), and removes the JDK's frames calling the test method and the assertion's internal frames
  from stack traces too.


.. _UNITTEST/Tool/OSVVM:

OSVVM
=====

* https://github.com/OSVVM/OSVVM
* https://github.com/OSVVM/OSVVM-Scripts


.. _UNITTEST/Tool/pytest:

pytest
======

* https://github.com/pytest-dev/pytest

The pipeline job ``Python-pytest`` runs the tests in :file:`examples/Python/pytest` and writes pytest's JUnit XML
report, measured by coverage.py, which writes its :ref:`JSON <CODECOV/Formats/CoveragePy>` and
:ref:`Cobertura XML <CODECOV/Formats/Cobertura>` reports.


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
