.. _UNITTEST/Features:

Features
********


.. _UNITTEST/Feature/Create:

Create test entities
====================

.. grid:: 2

   .. grid-item::
      :columns: 6

      The hierarchy of test entities (test cases, test suites and test summaries) can be constructed top-down or
      bottom-up.

   .. grid-item::
      :columns: 6

      .. tab-set::

         .. tab-item:: Test Case
            :sync: Testcase

            .. code-block:: Python

               from pyEDAA.Reports.Unittesting import Testsuite, Testcase

               # Top-down
               ts1 = Testsuite("ts1")

               tc = Testcase("tc", parent=ts1)

               # Bottom-up
               tc1 = Testcase("tc1")
               tc2 = Testcase("tc2")

               ts2 = Testsuite("ts2", testcases=(tc1, tc2))

               # ts.AddTestcase(...)
               tc3 = Testcase("tc3")
               tc4 = Testcase("tc4")

               ts3 = Testsuite("ts3")
               ts3.AddTestcase(tc3)
               ts3.AddTestcase(tc4)

               # ts.AddTestcases(...)
               tc3 = Testcase("tc3")
               tc4 = Testcase("tc4")

               ts3 = Testsuite("ts3")
               ts3.AddTestcases((tc3, tc4))

         .. tab-item:: Test Suite
            :sync: Testsuite

            .. code-block:: Python

               from pyEDAA.Reports.Unittesting import Testsuite, TestsuiteSummary

               # Top-down
               ts = Testsuite("ts")

               ts1 = Testsuite("ts1", parent=ts)

               # Bottom-up
               ts2 = Testsuite("ts2")
               ts3 = Testsuite("ts3")

               ts4 = Testsuite("ts4", testsuites=(ts2, ts3))

               # ts.AddTestsuite(...)
               ts5 = Testsuite("ts5")
               ts6 = Testsuite("ts6")

               ts7 = Testsuite("ts7")
               ts7.AddTestsuite(ts5)
               ts7.AddTestsuite(ts6)

               # ts.AddTestsuites(...)
               ts8 = Testsuite("ts8")
               ts9 = Testsuite("ts9")

               ts10 = Testsuite("ts10")
               ts10.AddTestsuites((ts8, ts9))

         .. tab-item:: Test Suite Summary
            :sync: TestsuiteSummary

            .. code-block:: Python

               from pyEDAA.Reports.Unittesting import Testsuite, TestsuiteSummary

               # Top-down
               tss1 = TestsuiteSummary("tss1")

               ts1 = Testsuite("ts1", parent=tss1)

               # Bottom-up
               ts2 = Testsuite("ts2")
               ts3 = Testsuite("ts3")

               tss2 = TestsuiteSummary("tss2", testsuites=(ts2, ts3))

               # tss.AddTestsuite(...)
               ts4 = Testsuite("ts4")
               ts5 = Testsuite("ts5")

               tss3 = TestsuiteSummary("tss3")
               tss3.AddTestsuite(ts4)
               tss3.AddTestsuite(ts5)

               # tss.AddTestsuites(...)
               ts6 = Testsuite("ts6")
               ts7 = Testsuite("ts7")

               tss4 = TestsuiteSummary("tss4")
               tss4.AddTestsuites((ts6, ts7))


.. _UNITTEST/Feature/Read:

Reading unittest reports
========================

.. grid:: 2

   .. grid-item::
      :columns: 6

      A JUnit XML test report summary file can be read by creating an instance of the :class:`~pyEDAA.Reports.Unittesting.JUnit.Document`
      class. Because JUnit has so many dialects, a derived subclass for the dialect might be required. By choosing the
      right Document class, also the XML schema for XML schema validation gets pre-selected.

      A test report written by pyTooling's pytest plugin (``--pytooling-xml``) is read by
      :class:`pyEDAA.Reports.Unittesting.pyTooling.Document`. Its format version is taken from the report's
      ``xsi:noNamespaceSchemaLocation`` attribute.

      A TRX file written by ``dotnet test --logger trx`` is read by :class:`pyEDAA.Reports.Unittesting.TRX.Document`
      into a test run; :meth:`~pyEDAA.Reports.Unittesting.TRX.TestRun.ToTestsuiteSummary` converts it to the unified
      data model.

   .. grid-item::
      :columns: 6

      .. tab-set::

         .. tab-item:: Any JUnit
            :sync: AnyJUnit

            .. code-block:: Python

               from pathlib import Path
               from pyEDAA.Reports.Unittesting import UnittestError
               from pyEDAA.Reports.Unittesting.JUnit import Document

               xmlReport = Path("AnyJUnit-Report.xml")
               try:
                 doc = Document(xmlReport, analyzeAndConvert=True)
               except UnittestError as ex:
                 ...

         .. tab-item:: Ant + JUnit4
            :sync: AntJUnit4

            .. code-block:: Python

               from pathlib import Path
               from pyEDAA.Reports.Unittesting import UnittestError
               from pyEDAA.Reports.Unittesting.JUnit.AntJUnit4 import Document

               xmlReport = Path("AntJUnit4-Report.xml")
               try:
                 doc = Document(xmlReport, analyzeAndConvert=True)
               except UnittestError as ex:
                 ...

         .. tab-item:: Catch2 JUnit
            :sync: Catch2JUnit

            .. code-block:: Python

               from pathlib import Path
               from pyEDAA.Reports.Unittesting import UnittestError
               from pyEDAA.Reports.Unittesting.JUnit.Catch2JUnit import Document

               xmlReport = Path("Catch2-JUnit-Report.xml")
               try:
                 doc = Document(xmlReport, analyzeAndConvert=True)
               except UnittestError as ex:
                 ...

         .. tab-item:: CTest JUnit
            :sync: CTestJUnit

            .. code-block:: Python

               from pathlib import Path
               from pyEDAA.Reports.Unittesting import UnittestError
               from pyEDAA.Reports.Unittesting.JUnit.CTestJUnit import Document

               xmlReport = Path("CTest-JUnit-Report.xml")
               try:
                 doc = Document(xmlReport, analyzeAndConvert=True)
               except UnittestError as ex:
                 ...

         .. tab-item:: go-junit-report JUnit
            :sync: GoJUnitReport

            .. code-block:: Python

               from pyEDAA.Reports.Unittesting.JUnit.GoJUnitReport import Document

               xmlReport = Path("go-junit-report.xml")
               try:
                 doc = Document(xmlReport, analyzeAndConvert=True)
               except UnittestError as ex:
                 ...

         .. tab-item:: GoogleTest JUnit
            :sync: GTestJUnit

            .. code-block:: Python

               from pathlib import Path
               from pyEDAA.Reports.Unittesting import UnittestError
               from pyEDAA.Reports.Unittesting.JUnit.GoogleTestJUnit import Document

               xmlReport = Path("GoogleTest-JUnit-Report.xml")
               try:
                 doc = Document(xmlReport, analyzeAndConvert=True)
               except UnittestError as ex:
                 ...

         .. tab-item:: cargo-nextest JUnit
            :sync: NextestJUnit

            .. code-block:: Python

               from pathlib import Path
               from pyEDAA.Reports.Unittesting import UnittestError
               from pyEDAA.Reports.Unittesting.JUnit.NextestJUnit import Document

               xmlReport = Path("Nextest-JUnit-Report.xml")
               try:
                 doc = Document(xmlReport, analyzeAndConvert=True)
               except UnittestError as ex:
                 ...

         .. tab-item:: pyTest JUnit
            :sync: pyTestJUnit

            .. code-block:: Python

               from pathlib import Path
               from pyEDAA.Reports.Unittesting import UnittestError
               from pyEDAA.Reports.Unittesting.JUnit.PyTestJUnit import Document

               xmlReport = Path("pyTest-JUnit-Report.xml")
               try:
                 doc = Document(xmlReport, analyzeAndConvert=True)
               except UnittestError as ex:
                 ...

         .. tab-item:: JunitXml.TestLogger JUnit
            :sync: TestLoggerJUnit

            .. code-block:: Python

               from pyEDAA.Reports.Unittesting.JUnit.TestLoggerJUnit import Document

               xmlReport = Path("TestLogger-JUnit-Report.xml")
               try:
                 doc = Document(xmlReport, analyzeAndConvert=True)
               except UnittestError as ex:
                 ...

         .. tab-item:: pyTooling
            :sync: pyTooling

            .. code-block:: Python

               from pathlib import Path
               from pyEDAA.Reports.Unittesting import UnittestError
               from pyEDAA.Reports.Unittesting.pyTooling import Document

               xmlReport = Path("TestReport.xml")
               try:
                 doc = Document(xmlReport, analyzeAndConvert=True)
               except UnittestError as ex:
                 ...

         .. tab-item:: TRX
            :sync: TRX

            .. code-block:: Python

               from pyEDAA.Reports.Unittesting.TRX import Document

               trxReport = Path("TestResults/MyLibrary.Tests.trx")
               try:
                 doc = Document(trxReport, analyzeAndConvert=True)
               except UnittestError as ex:
                 ...

               summary = doc.ToTestsuiteSummary()



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

               from pathlib import Path
               from pyEDAA.Reports.Unittesting import UnittestError
               from pyEDAA.Reports.Unittesting.JUnit import Document

               # Read from XML file
               xmlReport = Path("JUnit-Report.xml")
               try:
                 doc = Document(xmlReport, analyzeAndConvert=True)
               except UnittestError as ex:
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

               from pathlib import Path
               from pyEDAA.Reports.Unittesting import UnittestError
               from pyEDAA.Reports.Unittesting.JUnit import Document

               # Convert a TestsuiteSummary back to a Document
               newXmlReport = Path("JUnit-Report.xml")
               newDoc = Document.FromTestsuiteSummary(newXmlReport, summary)

               # Write to XML file
               try:
                  newDoc.Write()
               except UnittestError as ex:
                 ...

         .. tab-item:: Ant + JUnit4
            :sync: AntJUnit4

            .. code-block:: Python

               from pathlib import Path
               from pyEDAA.Reports.Unittesting import UnittestError
               from pyEDAA.Reports.Unittesting.JUnit.AntJUnit4 import Document

               # Convert a TestsuiteSummary back to a Document
               newXmlReport = Path("JUnit-Report.xml")
               newDoc = Document.FromTestsuiteSummary(newXmlReport, summary)

               # Write to XML file
               try:
                  newDoc.Write()
               except UnittestError as ex:
                 ...

         .. tab-item:: Catch2 JUnit
            :sync: Catch2JUnit

            .. code-block:: Python

               from pathlib import Path
               from pyEDAA.Reports.Unittesting import UnittestError
               from pyEDAA.Reports.Unittesting.JUnit.Catch2JUnit import Document

               # Convert a TestsuiteSummary back to a Document
               newXmlReport = Path("JUnit-Report.xml")
               newDoc = Document.FromTestsuiteSummary(newXmlReport, summary)

               # Write to XML file
               try:
                  newDoc.Write()
               except UnittestError as ex:
                 ...

         .. tab-item:: CTest JUnit
            :sync: CTestJUnit

            .. code-block:: Python

               from pathlib import Path
               from pyEDAA.Reports.Unittesting import UnittestError
               from pyEDAA.Reports.Unittesting.JUnit.CTestJUnit import Document

               # Convert a TestsuiteSummary back to a Document
               newXmlReport = Path("JUnit-Report.xml")
               newDoc = Document.FromTestsuiteSummary(newXmlReport, summary)

               # Write to XML file
               try:
                  newDoc.Write()
               except UnittestError as ex:
                 ...

         .. tab-item:: go-junit-report JUnit
            :sync: GoJUnitReport

            .. code-block:: Python

               from pyEDAA.Reports.Unittesting.JUnit.GoJUnitReport import Document

               # Convert a TestsuiteSummary back to a Document
               newXmlReport = Path("JUnit-Report.xml")
               newDoc = Document.FromTestsuiteSummary(newXmlReport, summary)

               # Write to XML file
               try:
                  newDoc.Write()
               except UnittestError as ex:
                 ...

         .. tab-item:: GoogleTest JUnit
            :sync: GTestJUnit

            .. code-block:: Python

               from pathlib import Path
               from pyEDAA.Reports.Unittesting import UnittestError
               from pyEDAA.Reports.Unittesting.JUnit.GoogleTestJUnit import Document

               # Convert a TestsuiteSummary back to a Document
               newXmlReport = Path("JUnit-Report.xml")
               newDoc = Document.FromTestsuiteSummary(newXmlReport, summary)

               # Write to XML file
               try:
                  newDoc.Write()
               except UnittestError as ex:
                 ...

         .. tab-item:: cargo-nextest JUnit
            :sync: NextestJUnit

            .. code-block:: Python

               from pathlib import Path
               from pyEDAA.Reports.Unittesting import UnittestError
               from pyEDAA.Reports.Unittesting.JUnit.NextestJUnit import Document

               # Convert a TestsuiteSummary back to a Document
               newXmlReport = Path("JUnit-Report.xml")
               newDoc = Document.FromTestsuiteSummary(newXmlReport, summary)

               # Write to XML file
               try:
                  newDoc.Write()
               except UnittestError as ex:
                 ...

         .. tab-item:: pyTest JUnit
            :sync: pyTestJUnit

            .. code-block:: Python

               from pathlib import Path
               from pyEDAA.Reports.Unittesting import UnittestError
               from pyEDAA.Reports.Unittesting.JUnit.PyTestJUnit import Document

               # Convert a TestsuiteSummary back to a Document
               newXmlReport = Path("JUnit-Report.xml")
               newDoc = Document.FromTestsuiteSummary(newXmlReport, summary)

               # Write to XML file
               try:
                  newDoc.Write()
               except UnittestError as ex:
                 ...

         .. tab-item:: JunitXml.TestLogger JUnit
            :sync: TestLoggerJUnit

            .. code-block:: Python

               from pyEDAA.Reports.Unittesting.JUnit.TestLoggerJUnit import Document

               # Convert a TestsuiteSummary back to a Document
               newXmlReport = Path("JUnit-Report.xml")
               newDoc = Document.FromTestsuiteSummary(newXmlReport, summary)

               # Write to XML file
               try:
                  newDoc.Write()
               except UnittestError as ex:
                 ...
