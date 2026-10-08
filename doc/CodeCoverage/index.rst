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
   └─ logical hierarchy        the language units the report names - each: file, first and last line
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
  :class:`~pyEDAA.Reports.CodeCoverage.Function`, :class:`~pyEDAA.Reports.CodeCoverage.Method` - spans its file from
  its first to its last line, both :class:`~pyEDAA.Reports.CodeCoverage.Line` objects of the file: a language construct
  wraps the constructs nested in it. So both hierarchies count the same lines. A unit without lines, e.g. a package of
  several files, counts the lines of the units it contains. A unit can state how often it was called.
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

A line a report doesn't list - a comment, a declaration - isn't executable and has no line object. A file keeps its
lines in a list indexed by line number, with ``None`` for such a line;
:meth:`~pyEDAA.Reports.CodeCoverage.File.IterateLines` walks the lines in order and
:meth:`~pyEDAA.Reports.CodeCoverage.File.GetLine` looks one up.

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

Code coverage tools write their results in XML, JSON or text formats, and many keep the raw data in a database or
binary format of their own, which only the tool itself or its API reads.

.. list-table::
   :header-rows: 1
   :widths: 16 21 21 21 21

   * - Tool / Framework
     - XML
     - JSON
     - Text
     - Proprietary
   * - `Cobertura <https://cobertura.github.io/cobertura/>`__ (Java)
     - Cobertura XML (``coverage-04.dtd``)
     - —
     - —
     - :file:`cobertura.ser`
   * - `JaCoCo <https://www.jacoco.org/jacoco/>`__ (Java)
     - JaCoCo XML (``report.dtd``)
     - —
     - CSV
     - :file:`*.exec`
   * - `coverage.py <https://coverage.readthedocs.io/>`__ (Python)
     - Cobertura dialect (``coverage xml``)
     - ``coverage json``
     - lcov (``coverage lcov``), ``coverage report``
     - :file:`.coverage` (SQLite)
   * - `GCC <https://gcc.gnu.org/onlinedocs/gcc/Gcov.html>`__ (``gcov``)
     - —
     - gcov JSON (``gcov --json-format``)
     - :file:`*.gcov`
     - :file:`*.gcno`, :file:`*.gcda`
   * - `gcovr <https://gcovr.com/>`__
     - Cobertura (``--cobertura``), JaCoCo (``--jacoco``), SonarQube (``--sonarqube``), Clover (``--clover``)
     - gcovr JSON (``--json``), Coveralls (``--coveralls``)
     - lcov (``--lcov``), ``--txt``
     - — (reads GCC's data)
   * - `lcov <https://github.com/linux-test-project/lcov>`__
     - —
     - —
     - lcov tracefile (:file:`*.info`)
     - — (reads GCC's data)
   * - `LLVM <https://llvm.org/docs/CommandGuide/llvm-cov.html>`__ (``llvm-cov``)
     - —
     - ``llvm-cov export -format=text``
     - lcov (``llvm-cov export -format=lcov``), :file:`*.gcov` (``llvm-cov gcov``), ``llvm-cov report``
     - :file:`*.profraw`, :file:`*.profdata`
   * - `cargo-llvm-cov <https://github.com/taiki-e/cargo-llvm-cov>`__ (Rust)
     - Cobertura (``--cobertura``)
     - LLVM's export format (``--json``)
     - lcov (``--lcov``), ``--text``
     - — (reads LLVM's data)
   * - `grcov <https://github.com/mozilla/grcov>`__ (Rust)
     - Cobertura (``-t cobertura``)
     - covdir (``-t covdir``), Coveralls (``-t coveralls``)
     - lcov (``-t lcov``)
     - — (reads LLVM's or GCC's data)
   * - `Go <https://pkg.go.dev/cmd/cover>`__ (``go test``)
     - —
     - —
     - cover profile (``go test -coverprofile``)
     - :file:`covmeta.*`, :file:`covcounters.*` (``GOCOVERDIR``)
   * - `gocover-cobertura <https://github.com/boumenot/gocover-cobertura>`__ (Go)
     - Cobertura
     - —
     - —
     - — (reads a cover profile)
   * - `gcov2lcov <https://github.com/jandelgado/gcov2lcov>`__ (Go)
     - —
     - —
     - lcov
     - — (reads a cover profile)
   * - `coverlet <https://github.com/coverlet-coverage/coverlet>`__ (.NET)
     - Cobertura, OpenCover
     - coverlet JSON
     - lcov
     - —
   * - `Microsoft Code Coverage <https://learn.microsoft.com/dotnet/core/additional-tools/dotnet-coverage>`__ (.NET)
     - Cobertura
     - —
     - —
     - :file:`*.coverage`
   * - `ReportGenerator <https://reportgenerator.io/>`__ (.NET)
     - Cobertura, among others
     - —
     - lcov, among others
     - — (reads other reports)
   * - `GHDL <https://github.com/ghdl/ghdl>`__ (VHDL)
     - —
     - :file:`coverage-*.json` (``ghdl -r --coverage``), gcovr JSON (``ghdl coverage --format=gcovr``)
     - lcov, :file:`*.gcov` (``ghdl coverage --format=lcov|gcov``)
     - — (GCC backend: GCC's data)
   * - `NVC <https://www.nickg.me.uk/nvc/>`__ (VHDL)
     - Cobertura (``nvc --cover-export --format=cobertura``); an undocumented internal dump (``--format=xml``)
     - —
     - —
     - :file:`*.ncdb`
   * - Aldec Active-HDL, Riviera-PRO
     - UCIS XML (``acdb2xml``)
     - —
     - —
     - ACDB
   * - Siemens QuestaSim
     - UCIS XML (`Accellera UCIS <https://www.accellera.org/downloads/standards/ucis>`__)
     - —
     - —
     - UCDB (read via the UCIS API)

pyEDAA.Reports reads Cobertura XML - also coverage.py's - and coverage.py's JSON.

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

.. _CODECOV/Formats/CoveragePy:

coverage.py JSON
================

coverage.py writes its JSON report with ``coverage json``. :class:`pyEDAA.Reports.CodeCoverage.CoveragePy.Document`
validates a report against the JSON Schema :ref:`CoveragePy-JSON.schema.json <SCHEMAS/CoveragePy-JSON>` - format
versions 2 and 3 - and reads it into the format's model: the measured files, their executed, missing and excluded
lines, the branches as pairs of source and destination line, the summaries coverage.py computed, and - in format 3 -
the functions and classes of each file.

:meth:`~pyEDAA.Reports.CodeCoverage.CoveragePy.Document.ToCoverageSummary` converts it to the common model:

* A file's path is relative to the directory coverage.py ran in.
* Executed lines are covered - partially covered, if one of their branches wasn't taken -, missing lines uncovered,
  excluded lines excluded. The format has no counts.
* A branch becomes a branch of its source line, naming its target line; an exit of a function - a negative number -
  has none.
* A file's directories become packages, the file a module spanning the whole file; its classes and functions -
  qualified names like ``Circle.Area`` - become classes, methods and functions, each spanning its ``class`` or ``def``
  line to its last line. coverage.py's own summary of a function counts the ``def`` line for the enclosing scope.

.. code-block:: Python

   from pathlib import Path
   from pyEDAA.Reports.CodeCoverage.CoveragePy import Document

   report = Document(Path("coverage.json"), analyzeAndConvert=True)
   summary = report.ToCoverageSummary()
   for unit in summary.IterateUnits():
     print(f"{unit.QualifiedName}: {unit.LineCoverage:.1%}")

.. hint::

   coverage.py writes Cobertura XML too, from the same measurement, naming the files relative to the measured source
   directory - e.g. ``Shapes.py`` -, while its JSON report names them relative to the directory coverage.py ran in -
   e.g. ``myPackage/Shapes.py``.
