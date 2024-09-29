.. _UNITTEST:

Unittesting
###########

*pyEDAA.Reports* provides a unified and generic unittest summary data model. The data model allows the description of
testcases grouped in testsuites. Testsuites can be nested in other testsuites. The data model's root element is a
special testsuite called testsuite summary. It contains only testsuites, but no testcases.

The data model can be filled from various sources like **Ant JUnit test reports** or **OSVVM testsuite summaries** (more
to be added). Many programming languages and/or unit testing frameworks support exporting results in the Ant JUnit
format. See below for supported formats and their variations (dialects).

.. attention::

   The so called JUnit XML format is the weakest file format and standard ever seen. At first was not created by JUnit
   (version 4). It was added by the built system Ant, but it's not called Ant XML format nor Ant JUnit XML format. The
   latest JUnit 5 uses a completely different format called :ref:`open test reporting <UNITTEST/FileFormats/OTR>`. As
   JUnit is not the formats author, no file format documentation nor XML schema was provided. Also Ant isn't providing
   any file format documentation or XML schema. Various Ant JUnit XML adopters have tried to reverse engineer a
   description and XML schemas, but unfortunately many are not even compatible to each other.


.. _UNITTEST/DataModel:

Unified data model
******************

The unified data model for test entities (test summary, test suite, test case) implements a super-set of all (so far
known) unit test result summary file formats. pyEDAA.Report's data model is a structural and functional cleanup of the
Ant JUnit data model. Naming has been cleaned up and missing features have been added.

As some of the JUnit XML dialects are too divergent from the original Ant + JUnit4 format, these dialects have an
independent test entity inheritance hierarchy. Nonetheless, instances of each data format can be converted to and from
the unified data model.

.. grid:: 2

   .. grid-item::
      :columns: 6

      .. grid:: 2

         .. grid-item-card::
            :columns: 6

            :ref:`UNITTEST/DataModel/Testcase`
            ^^^
            A :dfn:`test case` is the leaf-element in the test entity hierarchy and describes a single test run. Test
            cases are grouped by test suites.

         .. grid-item-card::
            :columns: 6

            :ref:`UNITTEST/DataModel/Testsuite`
            ^^^
            A :dfn:`test suite` is a group of test cases and/or test suites. Test suites itself can be grouped by test
            suites. The test suite hierarchy's root element is a test suite summary.

         .. grid-item-card::
            :columns: 6

            :ref:`UNITTEST/DataModel/TestsuiteSummary`
            ^^^
            The :dfn:`test suite summary` is derived from test suite and defines the root of the test suite hierarchy.

         .. grid-item-card::
            :columns: 6

            :ref:`UNITTEST/DataModel/Document`
            ^^^
            The :dfn:`document` is derived from a test suite summary and represents a file containing a test suite
            summary.

   .. grid-item::
      :columns: 6

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

           doc:::root -.-> sum:::summary
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

.. _UNITTEST/DataModel/Common:

Common
======

.. grid:: 2

   .. grid-item::
      :columns: 6

      The base-class for all test entities is :class:`pyEDAA.Reports.Unittesting.Base`. It implements the following
      properties and methods, which are common to all test entities:

      :data:`~pyEDAA.Reports.Unittesting.Base.Parent`
         Every test entity has a reference to it's parent test entity in the hierarchy.

      :data:`~pyEDAA.Reports.Unittesting.Base.Name`
         Every test entity has a name. This name must be unique per hierarchy parent, but can exist multiple times in the
         overall test hierarchy.

         In case the data format uses hierarchical names like ``pyEDAA.Reports.CLI.Application``, the name is split at
         the separator and multiple hierarchy levels (test suites) are created in the unified data model. To be able to
         recreate such an hierarchical name, :class:`~pyEDAA.Reports.Unittesting.TestsuiteKind` is applied accordingly to
         test suite's :data:`~pyEDAA.Reports.Unittesting.TestsuiteBase.Kind` field.

      :data:`~pyEDAA.Reports.Unittesting.Base.StartTime`
         Every test entity has a time when it was started. In case of a test case, it's the time when a single test was
         run. In case of a test suite, it's the time when the first test within this test suite was started. In case of a
         test suite summary, it's the time when the whole regression test was started.

         If the start time is unknown, set this value to ``None``.

      :data:`~pyEDAA.Reports.Unittesting.Base.SetupDuration`
         Every test entity has a field to capture the setup duration of a test run. In case of a test case, it's the time
         spend on setting up a single test run. In case of a test suite, it's the duration spend on preparing the group
         of tests for the first test run.

         If the setup duration can't be distinguished from the test's runtime, set this value to ``None``.

      :data:`~pyEDAA.Reports.Unittesting.Base.TestDuration`
         Every test entity has a field to capture the test's runtime.

         If the duration in unknown, set this value to ``None``.

      :data:`~pyEDAA.Reports.Unittesting.Base.TeardownDuration`
         Every test entity has a field to capture the teardown duration of a test run. In case of a test case, it's the
         time spend on tearing down a single test run. In case of a test suite, it's the duration spend on finalizing the
         group of tests after the last test run.

         If the teardown duration can't be distinguished from the test's runtime, set this value to ``None``.

      :data:`~pyEDAA.Reports.Unittesting.Base.TotalDuration`
         Every test entity has a field summing setup duration, test duration and teardown duration.

         If the duration in unknown, set this value to ``None``.

         .. math::

            TotalDuration := SetupDuration + TestDuration + TeardownDuration

      :data:`~pyEDAA.Reports.Unittesting.Base.WarningCount`
         Every test entity counts for warnings observed in a test run. In case of a test case, these are warnings while
         the test was executed. In case of a test suite, these warnings are an aggregate of all warnings within that
         group of test cases and test suites.

         .. todo:: Separate setup and teardown warnings from runtime warnings.

      :data:`~pyEDAA.Reports.Unittesting.Base.ErrorCount`
         Every test entity counts for errors observed in a test run. In case of a test case, these are errors while the
         test was executed. In case of a test suite, these errors are an aggregate of all errors within that group of
         test cases and test suites.

         .. todo:: Separate setup and teardown errors from runtime errors.

      :data:`~pyEDAA.Reports.Unittesting.Base.FatalCount`
         Every test entity counts for fatal errors observed in a test run. In case of a test case, these are fatal errors
         while the test was executed. In case of a test suite, these fatal errors are an aggregate of all fatal errors
         within that group of test cases and test suites.

         .. todo:: Separate setup and teardown fatal errors from runtime fatal errors.

      :meth:`~pyEDAA.Reports.Unittesting.Base.__len__`, :meth:`~pyEDAA.Reports.Unittesting.Base.__getitem__`, :meth:`~pyEDAA.Reports.Unittesting.Base.__setitem__`, :meth:`~pyEDAA.Reports.Unittesting.Base.__delitem__`, :meth:`~pyEDAA.Reports.Unittesting.Base.__contains__`, :meth:`~pyEDAA.Reports.Unittesting.Base.__iter__`
         Every test entity implements a dictionary interface, so arbitrary key-value pairs can be annotated per test
         entity.

      :meth:`~pyEDAA.Reports.Unittesting.Base.Aggregate`
         Aggregate (recalculate) all durations, warnings, errors, assertions, etc.


   .. grid-item::
      :columns: 6

      .. code-block:: Python

         @export
         class Base(metaclass=ExtendedType, slots=True):
            def __init__(
               self,
               name: str,
               startTime: Nullable[datetime] = None,
               setupDuration: Nullable[timedelta] = None,
               testDuration: Nullable[timedelta] = None,
               teardownDuration: Nullable[timedelta] = None,
               totalDuration:  Nullable[timedelta] = None,
               warningCount: int = 0,
               errorCount: int = 0,
               fatalCount: int = 0,
               parent: Nullable["Testsuite"] = None
            ):
              ...

            @readonly
            def Parent(self) -> Nullable["Testsuite"]:
              ...

            @readonly
            def Name(self) -> str:
              ...

            @readonly
            def StartTime(self) -> Nullable[datetime]:
              ...

            @readonly
            def SetupDuration(self) -> Nullable[timedelta]:
              ...

            @readonly
            def TestDuration(self) -> Nullable[timedelta]:
              ...

            @readonly
            def TeardownDuration(self) -> Nullable[timedelta]:
              ...

            @readonly
            def TotalDuration(self) -> Nullable[timedelta]:
              ...

            @readonly
            def WarningCount(self) -> int:
              ...

            @readonly
            def ErrorCount(self) -> int:
              ...

            @readonly
            def FatalCount(self) -> int:
              ...

            def __len__(self) -> int:
              ...

            def __getitem__(self, key: str) -> Any:
              ...

            def __setitem__(self, key: str, value: Any) -> None:
              ...

            def __delitem__(self, key: str) -> None:
              ...

            def __contains__(self, key: str) -> bool:
              ...

            def __iter__(self) -> Generator[Tuple[str, Any], None, None]:
              ...

            @abstractmethod
            def Aggregate(self):
              ...

.. _UNITTEST/DataModel/TestcaseStatus:

Testcase Status
===============

.. grid:: 2

   .. grid-item::
      :columns: 6

      :class:`~pyEDAA.Reports.Unittesting.TestcaseStatus` is a flag enumeration to describe the status of a test case.



   .. grid-item::
      :columns: 6

      .. code-block:: Python

         @export
         class TestcaseStatus(Flag):
            Unknown =    0                         #: Testcase status is uninitialized and therefore unknown.
            Excluded =   1                         #: Testcase was permanently excluded / disabled
            Skipped =    2                         #: Testcase was temporarily skipped (e.g. based on a condition)
            Weak =       4                         #: No assertions were recorded.
            Passed =     8                         #: A passed testcase, because all assertions were successful.
            Failed =    16                         #: A failed testcase due to at least one failed assertion.

            Mask = Excluded | Skipped | Weak | Passed | Failed

            Inverted = 128                         #: To mark inverted results
            UnexpectedPassed = Failed | Inverted
            ExpectedFailed =   Passed | Inverted

            Warned =  1024                         #: Runtime warning
            Errored = 2048                         #: Runtime error (mostly caught exceptions)
            Aborted = 4096                         #: Uncaught runtime exception

            SetupError =     8192                  #: Preparation / compilation error
            TearDownError = 16384                  #: Cleanup error / resource release error
            Inconsistent = 32768                   #: Dataset is inconsistent

            Flags = Warned | Errored | Aborted | SetupError | TearDownError | Inconsistent


.. _UNITTEST/DataModel/Testcase:

Testcase
========

.. grid:: 2

   .. grid-item::
      :columns: 6

      A :class:`~pyEDAA.Reports.Unittesting.Testcase` is the leaf-element in the test entity hierarchy and describes a
      single test run. Test cases are grouped by test suites.

      :data:`~pyEDAA.Reports.Unittesting.Testcase.Status`
         The overall status of a test case.

         See also: :ref:`UNITTEST/DataModel/TestcaseStatus`.

      :data:`~pyEDAA.Reports.Unittesting.Testcase.AssertionCount`
         The overall number of assertions (checks) in a test case.

         .. math::

            AssertionCount := PassedAssertionCount + FailedAssertionCount

      :data:`~pyEDAA.Reports.Unittesting.Testcase.FailedAssertionCount`
         The number of failed assertions in a test case.

      :data:`~pyEDAA.Reports.Unittesting.Testcase.PassedAssertionCount`
         The number of passed assertions in a test case.

      :meth:`~pyEDAA.Reports.Unittesting.Testcase.Copy`
        tbd

      :meth:`~pyEDAA.Reports.Unittesting.Testcase.Aggregate`
        tbd

      :meth:`~pyEDAA.Reports.Unittesting.Testcase.__str__`
        tbd

   .. grid-item::
      :columns: 6

      .. code-block:: Python

         @export
         class Testcase(Base):
            def __init__(
               self,
               name: str,
               startTime: Nullable[datetime] = None,
               setupDuration: Nullable[timedelta] = None,
               testDuration: Nullable[timedelta] = None,
               teardownDuration: Nullable[timedelta] = None,
               totalDuration:  Nullable[timedelta] = None,
               status: TestcaseStatus = TestcaseStatus.Unknown,
               assertionCount: Nullable[int] = None,
               failedAssertionCount: Nullable[int] = None,
               passedAssertionCount: Nullable[int] = None,
               warningCount: int = 0,
               errorCount: int = 0,
               fatalCount: int = 0,
               parent: Nullable["Testsuite"] = None
            ):
              ...

            @readonly
            def Status(self) -> TestcaseStatus:
              ...

            @readonly
            def AssertionCount(self) -> int:
              ...

            @readonly
            def FailedAssertionCount(self) -> int:
              ...

            @readonly
            def PassedAssertionCount(self) -> int:
              ...

            def Copy(self) -> "Testcase":
              ...

            def Aggregate(self, strict: bool = True) -> TestcaseAggregateReturnType:
              ...

            def __str__(self) -> str:
              ...

.. _UNITTEST/DataModel/Testsuite:

Testsuite
=========

.. grid:: 2

   .. grid-item::
      :columns: 6

      :class:`~pyEDAA.Reports.Unittesting.TestsuiteStatus`

      :class:`~pyEDAA.Reports.Unittesting.TestsuiteKind`

      :class:`~pyEDAA.Reports.Unittesting.Testsuite`


      :data:`~pyEDAA.Reports.Unittesting.Testsuite.Testcases`
        tbd

      :data:`~pyEDAA.Reports.Unittesting.Testsuite.TestcaseCount`
        tbd

      :data:`~pyEDAA.Reports.Unittesting.Testsuite.AssertionCount`
        tbd

      :meth:`~pyEDAA.Reports.Unittesting.Testsuite.Aggregate`
        tbd

      :meth:`~pyEDAA.Reports.Unittesting.Testsuite.Iterate`
        tbd

      :meth:`~pyEDAA.Reports.Unittesting.Testsuite.__str__`
        tbd

   .. grid-item::
      :columns: 6

      .. code-block:: Python

         @export
         class Testsuite(TestsuiteBase[TestsuiteType]):
            def __init__(
               self,
               name: str,
               kind: TestsuiteKind = TestsuiteKind.Logical,
               startTime: Nullable[datetime] = None,
               setupDuration: Nullable[timedelta] = None,
               testDuration: Nullable[timedelta] = None,
               teardownDuration: Nullable[timedelta] = None,
               totalDuration:  Nullable[timedelta] = None,
               status: TestsuiteStatus = TestsuiteStatus.Unknown,
               warningCount: int = 0,
               errorCount: int = 0,
               fatalCount: int = 0,
               testsuites: Nullable[Iterable[TestsuiteType]] = None,
               testcases: Nullable[Iterable["Testcase"]] = None,
               parent: Nullable[TestsuiteType] = None
            ):

            @readonly
            def Testcases(self) -> Dict[str, "Testcase"]:
              ...

            @readonly
            def TestcaseCount(self) -> int:
              ...

            @readonly
            def AssertionCount(self) -> int:
              ...

            def Aggregate(self, strict: bool = True) -> TestsuiteAggregateReturnType:
              ...

            def Iterate(self, scheme: IterationScheme = IterationScheme.Default) -> Generator[Union[TestsuiteType, Testcase], None, None]:
              ...

            def __str__(self) -> str:
              ...


.. _UNITTEST/DataModel/TestsuiteSummary:

TestsuiteSummary
================

.. grid:: 2

   .. grid-item::
      :columns: 6

      :class:`~pyEDAA.Reports.Unittesting.TestsuiteSummary`

      :meth:`~pyEDAA.Reports.Unittesting.TestsuiteSummary.Aggregate`
        tbd

      :meth:`~pyEDAA.Reports.Unittesting.TestsuiteSummary.Iterate`
        tbd

      :meth:`~pyEDAA.Reports.Unittesting.TestsuiteSummary.__str__`
        tbd

   .. grid-item::
      :columns: 6

      .. code-block:: Python

         @export
         class TestsuiteSummary(TestsuiteBase[TestsuiteType]):
            def __init__(
               self,
               name: str,
               startTime: Nullable[datetime] = None,
               setupDuration: Nullable[timedelta] = None,
               testDuration: Nullable[timedelta] = None,
               teardownDuration: Nullable[timedelta] = None,
               totalDuration:  Nullable[timedelta] = None,
               status: TestsuiteStatus = TestsuiteStatus.Unknown,
               warningCount: int = 0,
               errorCount: int = 0,
               fatalCount: int = 0,
               testsuites: Nullable[Iterable[TestsuiteType]] = None,
               parent: Nullable[TestsuiteType] = None
            ):
              ...

            def Aggregate(self) -> TestsuiteAggregateReturnType:
              ...

            def Iterate(self, scheme: IterationScheme = IterationScheme.Default) -> Generator[Union[TestsuiteType, Testcase], None, None]:
              ...

            def __str__(self) -> str:
              ...


.. _UNITTEST/DataModel/Document:

Document
========

.. grid:: 2

   .. grid-item::
      :columns: 6

      :class:`~pyEDAA.Reports.Unittesting.Document`

      :data:`~pyEDAA.Reports.Unittesting.Document.Path`
        tbd

      :data:`~pyEDAA.Reports.Unittesting.Document.AnalysisDuration`
        tbd

      :data:`~pyEDAA.Reports.Unittesting.Document.ModelConversionDuration`
        tbd

      :meth:`~pyEDAA.Reports.Unittesting.Document.Read`
        tbd

      :meth:`~pyEDAA.Reports.Unittesting.Document.Parse`
        tbd

   .. grid-item::
      :columns: 6

      .. code-block:: Python

         @export
         class Document(metaclass=ExtendedType, mixin=True):
            def __init__(self, path: Path):
              ...

            @readonly
            def Path(self) -> Path:
              ...

            @readonly
            def AnalysisDuration(self) -> timedelta:
              ...

            @readonly
            def ModelConversionDuration(self) -> timedelta:
              ...

            @abstractmethod
            def Read(self) -> None:
              ...

            @abstractmethod
            def Parse(self):
              ...


.. _UNITTEST/SpecificDataModels:

Specific Data Models
********************

.. _UNITTEST/SpecificDataModel/AnyJUnit4:

Any JUnit4
==========


.. _UNITTEST/SpecificDataModel/AntJUnit4:

Ant + JUnit4
============


.. _UNITTEST/SpecificDataModel/CTest:

CTest JUnit
===========


.. _UNITTEST/SpecificDataModel/GoogleTest:

GoogleTest JUnit
================


.. _UNITTEST/SpecificDataModel/pyTest:

pyTest JUnit
============




.. _UNITTEST/Features:

Features
********


.. _UNITTEST/Feature/Read:

Reading unittest reports
========================

.. grid:: 2

   .. grid-item::
      :columns: 6

      A JUnit XML test report summary file can be read by creating an instance of the :class:`~pyEDAA.Reports.Unittesting.JUnit.Document`
      class. Because JUnit has so many dialects, a derived subclass for the dialect might be required. By choosing the
      right Document class, also the XML schema for XML schema validation gets pre-selected.

   .. grid-item::
      :columns: 6

      .. tab-set::

         .. tab-item:: Any JUnit
            :sync: AnyJUnit

            .. code-block:: Python

               from pyEDAA.Reports.Unittesting.JUnit import Document

               xmlReport = Path("AnyJUnit-Report.xml")
               try:
                 doc = Document(xmlReport, parse=True)
               except UnittestException as ex:
                 ...

         .. tab-item:: Ant + JUnit4
            :sync: AntJUnit4

            .. code-block:: Python

               from pyEDAA.Reports.Unittesting.JUnit.AntJUnit import Document

               xmlReport = Path("AntJUnit4-Report.xml")
               try:
                 doc = Document(xmlReport, parse=True)
               except UnittestException as ex:
                 ...

         .. tab-item:: CTest JUnit
            :sync: CTestJUnit

            .. code-block:: Python

               from pyEDAA.Reports.Unittesting.JUnit.CTestJUnit import Document

               xmlReport = Path("CTest-JUnit-Report.xml")
               try:
                 doc = Document(xmlReport, parse=True)
               except UnittestException as ex:
                 ...

         .. tab-item:: GoogleTest JUnit
            :sync: GTestJUnit

            .. code-block:: Python

               from pyEDAA.Reports.Unittesting.JUnit.GoogleTestJUnit import Document

               xmlReport = Path("GoogleTest-JUnit-Report.xml")
               try:
                 doc = Document(xmlReport, parse=True)
               except UnittestException as ex:
                 ...

         .. tab-item:: pyTest JUnit
            :sync: pyTestJUnit

            .. code-block:: Python

               from pyEDAA.Reports.Unittesting.JUnit.PyTestJUnit import Document

               xmlReport = Path("pyTest-JUnit-Report.xml")
               try:
                 doc = Document(xmlReport, parse=True)
               except UnittestException as ex:
                 ...



.. _UNITTEST/Feature/Convert:

Converting unittest reports
===========================

.. grid:: 2

   .. grid-item::
      :columns: 6

      Any JUnit dialect specific data model can be converted to the generic hierarchy of test entities.


      .. note::

         This conversion is identical for all derived dialects.

   .. grid-item::
      :columns: 6

      .. tab-set::

         .. tab-item:: Document
            :sync: Document

            .. code-block:: Python

               from pyEDAA.Reports.Unittesting.JUnit import Document

               # Read from XML file
               xmlReport = Path("JUnit-Report.xml")
               try:
                 doc = Document(xmlReport, parse=True)
               except UnittestException as ex:
                 ...

               # Convert to unified test data model
               summary = doc.ToTestsuiteSummary()

               # Convert to a tree
               rootNode = doc.ToTree()

               # Convert back to a document
               newXmlReport = Path("New JUnit-Report.xml")
               newDoc = Document.FromTestsuiteSummary(newXmlReport, summary)

               # Write to XML file
               newDoc.Write()


.. _UNITTEST/Feature/Annotation:

Annotations
===========

.. grid:: 2

   .. grid-item::
      :columns: 6

      Every test entity can be annotated with arbitrary key-value pairs.

   .. grid-item::
      :columns: 6

      .. tab-set::

         .. tab-item:: Testcase
            :sync: Testcase

            .. code-block:: Python

               # Add annotate a key-value pair
               testcase["key"] = value

               # Update existing annotation with new value
               testcase["key"] = newValue

               # Check if key exists
               if "key" in testcase:
                 pass

               # Access annoation by key
               value = testcase["key"]

               # Get number of annotations
               annotationCount = len(testcase)

               # Delete annotation
               del testcase["key"]

               # Iterate annotations
               for key, value in testcases:
                  pass

         .. tab-item:: Testsuite
            :sync: Testsuite

            .. code-block:: Python

               # Add annotate a key-value pair
               testsuite["key"] = value

               # Update existing annotation with new value
               testsuite["key"] = newValue

               # Check if key exists
               if "key" in testsuite:
                 pass

               # Access annoation by key
               value = testsuite["key"]

               # Get number of annotations
               annotationCount = len(testsuite)

               # Delete annotation
               del testsuite["key"]

               # Iterate annotations
               for key, value in testsuite:
                  pass

         .. tab-item:: TestsuiteSummary
            :sync: TestsuiteSummary

            .. code-block:: Python

               # Add annotate a key-value pair
               testsuiteSummary["key"] = value

               # Update existing annotation with new value
               testsuiteSummary["key"] = newValue

               # Check if key exists
               if "key" in testsuiteSummary:
                 pass

               # Access annoation by key
               value = testsuiteSummary["key"]

               # Get number of annotations
               annotationCount = len(testsuiteSummary)

               # Delete annotation
               del testsuiteSummary["key"]

               # Iterate annotations
               for key, value in testsuiteSummary:
                  pass



.. _UNITTEST/Feature/Merge:

Merging unittest reports
========================

.. grid:: 2

   .. grid-item::
      :columns: 6

      add description here

   .. grid-item::
      :columns: 6

      .. tab-set::

         .. tab-item:: Testcase
            :sync: Testcase

            .. code-block:: Python

               # add code here

.. _UNITTEST/Feature/Concat:

Concatenate unittest reports
============================

.. todo:: Planned feature.

.. _UNITTEST/Feature/Transform:

Transforming the reports' hierarchy
===================================

.. _UNITTEST/Feature/Transform/pytest:

pytest specific transformations
-------------------------------

.. grid:: 2

   .. grid-item::
      :columns: 6

      add description here

   .. grid-item::
      :columns: 6

      .. tab-set::

         .. tab-item:: Testcase
            :sync: Testcase

            .. code-block:: Python

               # add code here

.. _UNITTEST/Feature/Write:

Writing unittest reports
========================

.. grid:: 2

   .. grid-item::
      :columns: 6

      A test suite summary can be converted to a document of any JUnit dialect. Internally a deep-copy is created to
      convert from a hierarchy of the unified test entities to a hierarchy of specific test entities (e.g. JUnit
      entities).

      When the document was created, it can be written to disk.

   .. grid-item::
      :columns: 6

      .. tab-set::

         .. tab-item:: Any JUnit
            :sync: AnyJUnit

            .. code-block:: Python

               from pyEDAA.Reports.Unittesting.JUnit import Document

               # Convert a TestsuiteSummary back to a Document
               newXmlReport = Path("JUnit-Report.xml")
               newDoc = Document.FromTestsuiteSummary(newXmlReport, summary)

               # Write to XML file
               try:
                  newDoc.Write()
               except UnittestException as ex:
                 ...

         .. tab-item:: Ant + JUnit4
            :sync: AntJUnit4

            .. code-block:: Python

               from pyEDAA.Reports.Unittesting.JUnit.AntJUnit import Document

               # Convert a TestsuiteSummary back to a Document
               newXmlReport = Path("JUnit-Report.xml")
               newDoc = Document.FromTestsuiteSummary(newXmlReport, summary)

               # Write to XML file
               try:
                  newDoc.Write()
               except UnittestException as ex:
                 ...

         .. tab-item:: CTest JUnit
            :sync: CTestJUnit

            .. code-block:: Python

               from pyEDAA.Reports.Unittesting.JUnit.CTestJUnit import Document

               # Convert a TestsuiteSummary back to a Document
               newXmlReport = Path("JUnit-Report.xml")
               newDoc = Document.FromTestsuiteSummary(newXmlReport, summary)

               # Write to XML file
               try:
                  newDoc.Write()
               except UnittestException as ex:
                 ...

         .. tab-item:: GoogleTest JUnit
            :sync: GTestJUnit

            .. code-block:: Python

               from pyEDAA.Reports.Unittesting.JUnit.GoogleTestJUnit import Document

               # Convert a TestsuiteSummary back to a Document
               newXmlReport = Path("JUnit-Report.xml")
               newDoc = Document.FromTestsuiteSummary(newXmlReport, summary)

               # Write to XML file
               try:
                  newDoc.Write()
               except UnittestException as ex:
                 ...

         .. tab-item:: pyTest JUnit
            :sync: pyTestJUnit

            .. code-block:: Python

               from pyEDAA.Reports.Unittesting.JUnit.PyTestJUnit import Document

               # Convert a TestsuiteSummary back to a Document
               newXmlReport = Path("JUnit-Report.xml")
               newDoc = Document.FromTestsuiteSummary(newXmlReport, summary)

               # Write to XML file
               try:
                  newDoc.Write()
               except UnittestException as ex:
                 ...


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

Many issues arise because the Ant + JUnit4 format is specific to unit testing with Java. Other languages and frameworks
were lazy and didn't derive an own format, but rather stuffed there language into the limitations of the Ant + JUnit4
XML format.

.. rubric:: JUnit Dialects

* 🚧 Bamboo JUnit (planned)
* ✅ CTest JUnit format
* ✅ GoogleTest JUnit format
* 🚧 Jenkins JUnit (planned)
* ✅ pyTest JUnit format

.. rubric:: JUnit Dialect Comparison

+------------------------+--------------+--------------------+------------------+--------------+
| Feature                | Ant + JUnit4 | CTest JUnit        | GoogleTest JUnit | pyTest JUnit |
+========================+==============+====================+==================+==============+
| Root element           |              | testsuite          |                  |              |
+------------------------+--------------+--------------------+------------------+--------------+
| Testcase status        | ...          | more status values |                  |              |
+------------------------+--------------+--------------------+------------------+--------------+


.. _UNITTEST/FileFormats/JUnit5:

JUnit 5 XML
===========

JUnit5 uses a new format called :ref:`UNITTEST/FileFormats/OTR` (see the following section for details). This format
isn't specific to Java (packages, classes, methods, ...), but describes a generic data model. Of cause an extension for
Java specifics is provided too.


.. _UNITTEST/FileFormats/OTR:

Open Test Reporting
===================


`Open Test Alliance <https://github.com/ota4j-team>`__

https://github.com/ota4j-team/open-test-reporting


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
