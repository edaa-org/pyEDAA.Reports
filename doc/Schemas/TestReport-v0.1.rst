.. _SCHEMAS/TestReport-v0.1:

pyTooling TestReport v0.1
#########################

pyTooling's own test report format, which pyTooling's pytest plugin writes. Unlike JUnit XML, test suites nest,
and every test suite and test case carries a title, a summary and a description.

Read by :class:`pyEDAA.Reports.Unittesting.pyTooling.Document` - see :ref:`UNITTEST/FileFormats/pyTooling`. The
schema is pyTooling's: the reader takes :file:`TestReport-v0.1.xsd` from :mod:`pyTooling.Resources`, the package
pyTooling ships it in, so pyEDAA.Reports carries no copy of it.

.. seealso::

   :ref:`TestReport v0.1 <pyTool:SCHEMAS/TestReport-v0.1>`
      |rarr| pyTooling's page of the schema: download, validation, diagram and source.
