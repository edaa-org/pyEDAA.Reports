.. _UNITTEST/SpecificDataModel/TRX:

TRX Data Model
==============

.. grid:: 2

   .. grid-item::
      :columns: 6

      The package :mod:`pyEDAA.Reports.Unittesting.TRX` mirrors the elements of a
      :ref:`TRX file <UNITTEST/FileFormats/TRX>`, as VSTest's TRX logger writes it (``dotnet test --logger trx``). A
      :class:`~pyEDAA.Reports.Unittesting.TRX.Document` reads a file into a
      :class:`~pyEDAA.Reports.Unittesting.TRX.TestRun`;
      :meth:`~pyEDAA.Reports.Unittesting.TRX.TestRun.ToTestsuiteSummary` converts it to the
      :ref:`unified data model <UNITTEST/DataModel>`.

   .. grid-item::
      :columns: 6

      .. mermaid::

         graph TD;
           doc[Document]
           run[TestRun]
           ut1[UnitTest]
           ut2[UnitTest]
           res1[UnitTestResult]
           res2[UnitTestResult]

           doc:::root -.-> run:::summary
           run --> ut1:::cls
           run --> ut2:::cls
           run --> res1:::case
           run --> res2:::case
           res1 -. testId .-> ut1
           res2 -. testId .-> ut2

           classDef root fill:#4dc3ff
           classDef summary fill:#80d4ff
           classDef cls fill:#ff9966
           classDef case fill:#eeccff

.. _UNITTEST/SpecificDataModel/TRX/TestRun:

TestRun
-------

A :class:`~pyEDAA.Reports.Unittesting.TRX.TestRun` is the root element ``<TestRun>``: the run's identifier, name, start
and finish time, and from ``<ResultSummary>`` the run's outcome, its counters (by attribute name) and the messages of
the test framework for the whole run. It holds the test lists (``<TestLists>``) by identifier, the test definitions by
identifier and the test results in the order of the file.

.. _UNITTEST/SpecificDataModel/TRX/UnitTest:

UnitTest
--------

A :class:`~pyEDAA.Reports.Unittesting.TRX.UnitTest` is a test definition (``<UnitTest>`` in ``<TestDefinitions>``):
the test's name, the fully qualified name of its class, the name of its method, the path to its assembly and the test
adapter running it. Each data row of a parameterized test is a test definition of its own. Its parent is the test
run.

.. _UNITTEST/SpecificDataModel/TRX/UnitTestResult:

UnitTestResult
--------------

A :class:`~pyEDAA.Reports.Unittesting.TRX.UnitTestResult` is a test's result (``<UnitTestResult>`` in ``<Results>``):
the identifiers of the execution, the test definition and the test list, the test's name, the computer it ran on, its
outcome, start and end time and duration. ``<ErrorInfo>``'s message and stack trace are provided as ``Message`` and
``Details``, ``<StdOut>`` and ``<StdErr>`` as ``StandardOutput`` and ``StandardError``. A data-driven test or an ordered
test lists the results of its rows or tests as inner results. A result's parent is the test run; an inner result's
parent is its container.

.. _UNITTEST/SpecificDataModel/TRX/Document:

Document
--------

A :class:`~pyEDAA.Reports.Unittesting.TRX.Document` is a test run read from a file. The file is validated against
:ref:`VSTest-TRX.xsd <SCHEMAS/VSTest-TRX>`, an XML schema reverse engineered from the logger's source code.

.. _UNITTEST/SpecificDataModel/TRX/Conversion:

Conversion to the unified data model
------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - TRX
     - Unified data model
   * - ``<TestRun>``
     - :class:`~pyEDAA.Reports.Unittesting.TestsuiteSummary`, named after the test run; start time and duration from
       ``<Times>``.
   * - ``codeBase`` of ``<TestMethod>``
     - A :class:`~pyEDAA.Reports.Unittesting.Testsuite` per test assembly, named after the assembly's file (e.g.
       ``MyLibrary.Tests.dll``); its host name is the result's ``computerName``.
   * - ``className`` of ``<TestMethod>``
     - A test suite per namespace (kind ``Namespace``) and per test class (kind ``Class``).
   * - ``<UnitTestResult>``
     - A :class:`~pyEDAA.Reports.Unittesting.Testcase`, named after ``testName`` without the class name; start time,
       duration, message, details and output of the result.
   * - inner results
     - A test case per inner result; the container itself isn't a test case.
   * - ``<ResultSummary>``
     - Not converted: the summary's counters are computed from the test cases.

An outcome maps to a test case status:

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Outcome
     - Status
   * - ``Passed``, ``PassedButRunAborted``, ``Warning``, ``Completed``
     - ``Passed``
   * - ``Failed``, ``Timeout``
     - ``Failed``
   * - ``Error``, ``Aborted``, ``NotRunnable``, ``Disconnected``
     - ``Errored``
   * - ``NotExecuted``, ``Inconclusive``
     - ``Skipped``
   * - ``InProgress``, ``Pending``
     - ``Inconsistent``

Not converted: the identifiers (GUIDs), the test lists, the end time of a result, the test adapter, the run's
counters, outcome and messages, and what the reader doesn't read at all - test settings, owners, categories,
priorities and work items of a test definition, debug traces, text messages, result files and the attachments of data
collectors.

.. _UNITTEST/SpecificDataModel/TRX/Quirks:

Quirks of VSTest's TRX logger
-----------------------------

* The counters contradict the results: the logger counts every result in ``total``, but only passed and failed ones
  in ``executed``, and writes ``0`` for every other counter. The xUnit.net example's file states ``total="11"
  executed="10" passed="7" failed="3" notExecuted="0"``: its skipped test is counted in ``total`` only. The reader
  keeps the counters as written in :data:`~pyEDAA.Reports.Unittesting.TRX.TestRun.Counters` and counts the results.
* VSTest knows the outcomes passed, failed, skipped, not found and none. A skipped, not found or outcome-less test is
  ``NotExecuted``; an exception escaping a test is ``Failed``. Each skipped test is also announced in the run's
  output: ``Test 'MyLibrary.Tests.CalculatorTests.Multiply' was skipped in the test run.``
* A result's ``outcome`` attribute is omitted, if it's ``Error`` (the enumeration's default value).
* Test adapters name a test differently: xUnit.net with its class (``MyLibrary.Tests.CalculatorTests.Absolute(value:
  3, expected: 3)``), MSTest (``Rows (1,1)``) and NUnit (``Rows(1,1)``) without.
* xUnit.net rounds a test's duration to milliseconds.
* The logger omits a zero duration: MSTest's ignored test has no ``duration``. The rows of an MSTest data-driven test
  whose data is folded (``UnfoldingStrategy = TestDataSourceUnfoldingStrategy.Fold``) are results of the same test
  definition.
* NUnit reports an inconclusive test, an explicit test and a test raising a warning as ``NotExecuted`` and repeats the
  message as the test's output. ``dotnet test`` doesn't count the inconclusive and the explicit test in its console
  summary; the TRX file lists them.
