.. _CODECOV:

Code Coverage
#############

Code coverage measures used and unused code lines, statements, branches, etc. Depending on the programming language this
is measured by instrumenting the code/binary and running the program, it's test cases or simulating the code. In
generate code coverage is a measure of test coverage. Unused code is not (yet) covered by tests.

The code coverage metric in percent is a ratio of used code versus all possibly usable code. A coverage of <100%
indicates unused code. This can be dead code (unreachable) or untested code (⇒ needs more test cases).


.. rubric:: Code Coverage Kinds

* Coverage

  * Code coverage

    * statement coverage / line coverage
    * branch coverage
    * expression coverage
    * toggle coverage
    * state coverage (of state machines)
    * transition coverage (of state machines)

  * Functional coverage
  * Documentation coverage
  * Test coverage


.. _CODECOV/DataModel:

Data Model
**********

pyEDAA.Reports reads a code coverage report in two layers: a model of the **report format**, which keeps what the
report states, and the **common model** of :mod:`pyEDAA.Reports.CodeCoverage`, which every format converts to - as
the JUnit dialects convert to the unified unit test model.

The common model is a superset: it has two hierarchies over the same lines.

.. code-block:: text

   CoverageSummary             the report
   │
   ├─ physical hierarchy       built from the file paths the report names
   │  ├── Directory            e.g. myPackage/
   │  │   └── File             e.g. myPackage/Shapes.py
   │  │       └── Line         line number, LineCoverageStatus, coverage count
   │  │           └── Branch   LineCoverageStatus, coverage count, target
   │  └── File
   │
   └─ logical hierarchy        the language units the report names - each: file, first and last line, lines
      └── Package              e.g. myPackage
          ├── Module           e.g. myPackage.Shapes
          │   ├── Class        e.g. myPackage.Shapes.Circle
          │   │   └── Method   e.g. myPackage.Shapes.Circle.Area
          │   └── Function     e.g. myPackage.Shapes.Distance
          └── SourceFile       e.g. main.c - for languages, where the file is the unit
              └── Function     e.g. main

* Every format has files and lines, so lines, branches and their counts live in the **physical** hierarchy.
* A **unit** - :class:`~pyEDAA.Reports.CodeCoverage.Package`, :class:`~pyEDAA.Reports.CodeCoverage.Module`,
  :class:`~pyEDAA.Reports.CodeCoverage.SourceFile`, :class:`~pyEDAA.Reports.CodeCoverage.Class`,
  :class:`~pyEDAA.Reports.CodeCoverage.Function`, :class:`~pyEDAA.Reports.CodeCoverage.Method` - names its file, its
  first and last line and its lines, which are the file's :class:`~pyEDAA.Reports.CodeCoverage.Line` objects. So both
  hierarchies count the same lines. A unit can state how often it was called.
* A :class:`~pyEDAA.Reports.CodeCoverage.SourceFile` is the unit of a language without modules or classes, where the
  file is the unit: e.g. a C translation unit, a Bash or TCL script.
* Every element knows the element containing it - :attr:`~pyEDAA.Reports.CodeCoverage.Base.Parent` - and the report's
  root - :attr:`~pyEDAA.Reports.CodeCoverage.Base.Root`. Assigning a parent, in the constructor or later, adds the
  element to it and passes the root on to the elements it contains.

A line, a branch and a unit carry a :class:`~pyEDAA.Reports.CodeCoverage.LineCoverageStatus` and - if the report
says - a count: how often the line ran, the branch was taken, the unit was called. A count of ``0`` is uncovered, a
positive count covered.

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Status
     - Meaning
   * - ``Covered``
     - The line ran, the branch was taken, the unit was called.
   * - ``PartiallyCovered``
     - The line ran, but not all of its branches were taken.
   * - ``Uncovered``
     - The line never ran, the branch was never taken, the unit was never called.
   * - ``Excluded``
     - Excluded from the measurement, e.g. by a pragma comment.
   * - ``Unknown``
     - The report doesn't say.

A line a report doesn't list - a comment, a declaration - isn't executable and has no line object.

:meth:`~pyEDAA.Reports.CodeCoverage.CoverageSummary.Aggregate` computes the counters of a file from its lines, of a
directory from its directories and files, and of a unit from its lines and those of its units, each line counted
once: executable, covered, missing, excluded and partially covered lines, branches, covered and missing branches. The
ratios :attr:`~pyEDAA.Reports.CodeCoverage.CoverageCountersMixin.LineCoverage`,
:attr:`~pyEDAA.Reports.CodeCoverage.CoverageCountersMixin.BranchCoverage` and
:attr:`~pyEDAA.Reports.CodeCoverage.CoverageCountersMixin.Coverage` (lines and branches combined, as coverage.py
computes it) are ``1.0`` where there is nothing to cover.


.. _CODECOV/Formats:

Report Formats
**************

.. _CODECOV/Formats/Cobertura:

Cobertura XML
=============

Cobertura's XML format is written by many tools - e.g. coverage.py (``coverage xml``) or gcovr (``--cobertura``) - for
any language they measure. :class:`pyEDAA.Reports.CodeCoverage.Cobertura.Document` validates a report against
:ref:`Any-Cobertura.xsd <SCHEMAS/Any-Cobertura>` and reads it into the format's model, after Cobertura's DTD
``coverage-04.dtd``: packages, classes, methods, lines and conditions, and the figures and rates the report states.
:ref:`Cobertura-04.xsd <SCHEMAS/Cobertura-04>` is the DTD's strict translation.

:meth:`~pyEDAA.Reports.CodeCoverage.Cobertura.Document.ToCoverageSummary` converts it to the common model:

* A ``<class>`` names its source file in ``filename``, relative to one of the ``<source>`` directories. Several classes
  of one file - e.g. Java's nested classes - become one file, their lines merged.
* A ``<line>``'s ``hits`` is its count; a branching line's ``condition-coverage`` - e.g. ``50% (1/2)`` - states its
  taken and all branches.
* Packages, classes and methods become units; a package's name is split at ``.`` into nested packages.
* The format has no excluded lines.

.. code-block:: Python

   from pathlib import Path
   from pyEDAA.Reports.CodeCoverage.Cobertura import Document

   report = Document(Path("coverage.xml"), analyzeAndConvert=True)
   print(f"{report.LinesCovered} of {report.LinesValid} lines, as the report states")

   summary = report.ToCoverageSummary()
   for file in summary.IterateFiles():
     print(f"{file.Path}: {file.LineCoverage:.1%}")
