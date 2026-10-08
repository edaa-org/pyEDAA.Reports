.. _UNITTEST/SpecificDataModel/TRX:

TRX Data Model
==============

.. grid:: 2

   .. grid-item::
      :columns: 6

      The package :mod:`pyEDAA.Reports.Unittesting.TRX` mirrors the elements of a
      :ref:`TRX file <UNITTEST/FileFormats/TRX>`, as VSTest's TRX logger writes it (``dotnet test --logger trx``). A
      :class:`~pyEDAA.Reports.Unittesting.TRX.Document` reads a file into a
      :class:`~pyEDAA.Reports.Unittesting.TRX.TestRun`: the run, its test lists and its summary.

   .. grid-item::
      :columns: 6

      .. mermaid::

         graph TD;
           doc[Document]
           run[TestRun]

           doc:::root -.-> run:::summary

           classDef root fill:#4dc3ff
           classDef summary fill:#80d4ff

.. _UNITTEST/SpecificDataModel/TRX/TestRun:

TestRun
-------

A :class:`~pyEDAA.Reports.Unittesting.TRX.TestRun` is the root element ``<TestRun>``: the run's identifier, name, start
and finish time, and from ``<ResultSummary>`` the run's outcome, its counters (by attribute name) and the messages of
the test framework for the whole run. It holds the test lists (``<TestLists>``) by identifier.

.. _UNITTEST/SpecificDataModel/TRX/Document:

Document
--------

A :class:`~pyEDAA.Reports.Unittesting.TRX.Document` is a test run read from a file. The file is validated against
:ref:`VSTest-TRX.xsd <SCHEMAS/VSTest-TRX>`, an XML schema reverse engineered from the logger's source code.

.. _UNITTEST/SpecificDataModel/TRX/Quirks:

Quirks of VSTest's TRX logger
-----------------------------

* The counters contradict the results: the logger counts every result in ``total``, but only passed and failed ones
  in ``executed``, and writes ``0`` for every other counter. The xUnit.net example's file states ``total="11"
  executed="10" passed="7" failed="3" notExecuted="0"``: its skipped test is counted in ``total`` only. The reader
  keeps the counters as written in :data:`~pyEDAA.Reports.Unittesting.TRX.TestRun.Counters`.
* VSTest knows the outcomes passed, failed, skipped, not found and none. A skipped, not found or outcome-less test is
  ``NotExecuted``; an exception escaping a test is ``Failed``. Each skipped test is also announced in the run's
  output: ``Test 'MyLibrary.Tests.CalculatorTests.Multiply' was skipped in the test run.``
* A result's ``outcome`` attribute is omitted, if it's ``Error`` (the enumeration's default value).
