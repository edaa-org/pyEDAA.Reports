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

pyEDAA.Reports reads Cobertura XML - also coverage.py's and NVC's - and coverage.py's JSON.

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

Rust's coverage tools write Cobertura XML too, as the pipeline job ``Rust-Cargo`` shows: cargo-llvm-cov
(``cargo llvm-cov report --cobertura``) and grcov (``--output-types cobertura``). Both state ``complexity`` on a
``<method>``, which ``coverage-04.dtd`` doesn't declare, so only :ref:`Any-Cobertura.xsd <SCHEMAS/Any-Cobertura>`
accepts them. A library's function is compiled into the unit tests' binary and into each integration test's binary,
so it is a ``<method>`` per binary, each with the same name and an empty signature.

.. code-block:: Python

   from pathlib import Path
   from pyEDAA.Reports.CodeCoverage.Cobertura import Document

   report = Document(Path("coverage.xml"), analyzeAndConvert=True)
   print(f"{report.LinesCovered} of {report.LinesValid} lines, as the report states")

   summary = report.ToCoverageSummary()
   for file in summary.IterateFiles():
     print(f"{file.Path}: {file.LineCoverage:.1%}")

:meth:`~pyEDAA.Reports.CodeCoverage.Cobertura.Document.FromCoverageSummary` converts the common model - read from any
format - to the format's model, and :meth:`~pyEDAA.Reports.CodeCoverage.Cobertura.Document.Write` writes it as a
report following Cobertura's DTD, valid according to :ref:`Cobertura-04.xsd <SCHEMAS/Cobertura-04>`:

* A source file, a module or a class of the logical hierarchy becomes a ``<class>`` of its file, named by its qualified
  name below its packages, e.g. ``Shapes.Circle``. Its packages name its ``<package>``, e.g. ``myPackage``; without
  packages, the file's directories do, e.g. ``src.Utilities`` - or ``.`` for the report's root.
* Every line is listed once: by the innermost ``<class>`` spanning it, or - outside of every one - by a ``<class>``
  named after the file, e.g. ``main.c``.
* A function or a method becomes a ``<method>`` of the ``<class>`` of the unit containing it, listing its lines.
* A line's count is its ``hits``; a line without count has ``1`` hit, if it ran, else ``0``. A branching line states
  its taken and all branches in ``condition-coverage``, e.g. ``50% (1/2)``.
* The rates and figures are computed from the lines; the source directories are the summary's.
* The format has no excluded lines, no counts or targets of branches, and no calls of units: they are left out.

.. code-block:: Python

   from pathlib import Path
   from pyEDAA.Reports.CodeCoverage.Cobertura import Document

   report = Document.FromCoverageSummary(Path("Cobertura.xml"), summary)
   report.Write(regenerate=True)

A report read can be written again, too: :meth:`~pyEDAA.Reports.CodeCoverage.Cobertura.Document.Generate` builds the
XML document from the format's model, leaving out what the DTD doesn't define - e.g. coverage.py's
``missing-branches`` -, and computes the rates and figures the report doesn't state.

.. rubric:: Cobertura Dialects

Each tool writes Cobertura XML in a shape of its own - a dialect -, as the frameworks writing JUnit XML do. A dialect
has a module of its own in :mod:`pyEDAA.Reports.CodeCoverage.Cobertura`: a ``Document`` derived from the generic one,
which validates a report against the strict schema of the dialect and reads what the dialect adds. The class a report
is read with chooses the dialect.

.. list-table::
   :header-rows: 1
   :widths: 16 26 29 29

   * - Feature
     - Any Cobertura
     - coverage.py Cobertura
     - NVC Cobertura
   * - Schema
     - :ref:`Any-Cobertura.xsd <SCHEMAS/Any-Cobertura>`, lenient
     - :ref:`CoveragePy-Cobertura.xsd <SCHEMAS/CoveragePy-Cobertura>`, strict
     - :ref:`NVC-Cobertura.xsd <SCHEMAS/NVC-Cobertura>`, strict
   * - ``condition-coverage``
     - percentage, taken and all, e.g. ``50% (1/2)``
     - percentage, taken and all, e.g. ``50% (1/2)``
     - percentage only: ``0 %``, ``50 %`` or ``100 %``
   * - A line's ``hits``
     - count
     - ``0`` or ``1``: no count
     - count of the statements starting in the line, all instances added; ``0`` without a statement
   * - Branches
     - taken and all, from ``condition-coverage``
     - also the targets of those never taken, from ``missing-branches``
     - true and false of each ``<condition>``, taken from ``condition-coverage``
   * - Units
     - packages, classes and methods
     - packages and modules, from the file paths
     - library, entity and architecture

.. _CODECOV/Formats/Cobertura/CoveragePy:

coverage.py Cobertura
---------------------

coverage.py writes Cobertura XML with ``coverage xml``.
:class:`pyEDAA.Reports.CodeCoverage.Cobertura.CoveragePyCobertura.Document` validates a report against
:ref:`CoveragePy-Cobertura.xsd <SCHEMAS/CoveragePy-Cobertura>`, reverse-engineered from coverage.py 7.x, and reads it
into the generic format's model; a line also keeps the targets of its branches never taken, which coverage.py states in
``missing-branches``.

:meth:`~pyEDAA.Reports.CodeCoverage.Cobertura.CoveragePyCobertura.Document.ToCoverageSummary` converts it to the
common model:

* A line's ``hits`` - ``0`` or ``1`` - says whether it ran: a line, which ran, is covered - partially covered, if one of
  its branches wasn't taken -, otherwise uncovered. The format has no counts.
* A branch never taken names its target line - none for an exit of a function, which coverage.py states as ``exit`` -,
  a taken one doesn't.
* A file's directories become packages, the file a module spanning the whole file.
* The format has no excluded lines.

.. code-block:: Python

   from pathlib import Path
   from pyEDAA.Reports.CodeCoverage.Cobertura.CoveragePyCobertura import Document

   report = Document(Path("coverage.xml"), analyzeAndConvert=True)
   summary = report.ToCoverageSummary()
   for unit in summary.IterateUnits():
     print(f"{unit.QualifiedName}: {unit.LineCoverage:.1%}")


.. _CODECOV/Formats/Cobertura/NVC:

NVC Cobertura
-------------

NVC writes Cobertura XML with ``nvc --cover-export --format=cobertura``, from the coverage database (:file:`*.ncdb`) of
a simulation elaborated with ``--cover``, or of several merged with ``nvc --cover-merge``.
:class:`pyEDAA.Reports.CodeCoverage.Cobertura.NVCCobertura.Document` validates a report against
:ref:`NVC-Cobertura.xsd <SCHEMAS/NVC-Cobertura>`, reverse-engineered from NVC 1.23, and reads it into the generic
format's model; a class also keeps its entity and architecture.

The beginning of a report, of the simulation in :file:`tests/data/CodeCoverage/NVC`:

.. literalinclude:: ../../tests/data/CodeCoverage/NVC/Count.xml
   :language: xml
   :lines: 1-28

.. rubric:: What NVC writes

* A document type declaration naming ``coverage-04.dtd``, and every attribute the DTD requires: ``version`` is NVC's
  name and version, e.g. ``nvc 1.23.0``, ``timestamp`` in seconds, a rate has six decimals, every ``complexity`` is
  ``0.0``. The only ``<source>`` is ``.``; a file is named relative to the directory given by ``--relative``, or as it
  was given to the analysis.
* One package, named after the library of the top-level design unit, e.g. ``WORK`` - also for design units of other
  libraries.
* A class per design unit, named after its entity and architecture in upper case, e.g. ``COUNTER(RTL)``, with the file
  of its first coverage item. All instances of a design unit are one class, their counts added. The classes follow in
  the reverse order of elaboration, the lines in the order of their coverage items, not sorted; there are no methods.
  Subprograms of a package aren't measured.
* A line's ``hits`` adds how often each statement starting in the line ran: a line of two statements, e.g.
  ``State <= Idle;  Count <= (others => '0');``, counts ``2`` each time it runs. A line without a statement - e.g. an
  ``elsif``, a ``when`` of a ``case`` statement, the continuation of a conditional signal assignment - has hits ``0``,
  even when its condition was evaluated.
* A branching line has ``branch="true"``, a ``condition-coverage`` and one ``<condition number="0" type="jump">`` of the
  same ``coverage``: ``0 %``, ``50 %`` or ``100 %``, whether its condition was never decided, decided one way, or both
  ways. A choice of a ``case`` statement is always ``0 %``, taken or not: NVC counts only the true and false directions
  of a branch.
* ``lines-valid`` counts the lines listed, ``lines-covered`` those with hits; ``branches-valid`` counts the branching
  lines, ``branches-covered`` those decided both ways.
* Only statement and branch coverage reach the export. Expression, toggle, FSM state and functional coverage
  (``--cover=expression``, ``toggle``, ``fsm-state``, ``functional``) add a line of hits ``0`` for each line with an
  item - e.g. a signal's declaration for toggle coverage, a PSL ``cover`` directive for functional coverage -, which
  can't be told from a statement that never ran.

.. rubric:: Differences from ``coverage-04.dtd`` and the generic reader

* ``condition-coverage`` is a percentage with a space before ``%``, without the taken and all branches the DTD's
  form ``50% (1/2)`` states. :ref:`Any-Cobertura.xsd <SCHEMAS/Any-Cobertura>` and
  :ref:`Cobertura-04.xsd <SCHEMAS/Cobertura-04>` reject it, so
  :class:`~pyEDAA.Reports.CodeCoverage.Cobertura.Document` doesn't read an NVC report with branch coverage.
* A class' ``name`` isn't a class, but a design unit: entity and architecture. ``branches-valid`` counts branching
  lines, not branches.
* A file is named per design unit, the file of its first coverage item. An entity's statements are listed in each of
  its architectures' classes; if the entity is in another file than the architecture, the architecture's lines are
  listed under the entity's file, with their line numbers in the architecture's file.

.. rubric:: Conversion to the common model

:meth:`~pyEDAA.Reports.CodeCoverage.Cobertura.NVCCobertura.Document.ToCoverageSummary` converts it to the common
model:

* A line's ``hits`` is its count. Classes of one file are one file; a line listed by several of them - e.g. an
  entity's statement - has their hits added.
* Each ``<condition>`` becomes two branches without count - its true and its false direction -, of which
  ``condition-coverage`` states how many were taken: ``50 %`` is one of two.
* A line, which ran or took a branch, is covered - partially covered, if one of its branches wasn't taken -, otherwise
  uncovered. A line without a statement, which took a branch, has no count.
* The library becomes a package, an entity a module in it, and an architecture a module in its entity, spanning its file
  from the first to the last line its class lists: ``WORK.COUNTER.RTL``.
* The format has no excluded lines.

So the common model counts other figures than NVC: two branches per branching line, and a line without a statement,
which took a branch, as covered. What the format doesn't state is lost: which direction of a ``50 %`` condition was
taken, the counts per instance - NVC's HTML report (``nvc --cover-report``) has them -, and the expression, toggle, FSM
state and functional coverage.

.. code-block:: Python

   from pathlib import Path
   from pyEDAA.Reports.CodeCoverage.Cobertura.NVCCobertura import Document

   report = Document(Path("coverage.xml"), analyzeAndConvert=True)
   summary = report.ToCoverageSummary()
   for unit in summary.IterateUnits():
     print(f"{unit.QualifiedName}: {unit.LineCoverage:.1%}")


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

The pipeline job ``Python-pytest`` measures the example in :file:`examples/Python/pytest` and writes both reports,
JSON and Cobertura XML; see :ref:`UNITTEST/Tool/pytest`.

.. hint::

   coverage.py writes Cobertura XML too, from the same measurement, naming the files relative to the measured source
   directory - e.g. ``Shapes.py`` -, while its JSON report names them relative to the directory coverage.py ran in -
   e.g. ``myPackage/Shapes.py``.

.. _CODECOV/Formats/GHDL:

GHDL coverage JSON
==================

GHDL writes a coverage file when simulating with ``ghdl -r --coverage``, by default to
:file:`coverage-<timestamp>.json`, or to the file named by ``--coverage-output=<file>``.
:class:`pyEDAA.Reports.CodeCoverage.GHDL.Document` validates it against the JSON Schema
:ref:`GHDL-Coverage.schema.json <SCHEMAS/GHDL-Coverage>` - format version 1.0.0 - and reads it into the
format's model: the source files, each with the directory it was analyzed in, its SHA-1 checksum, the kind of
coverage as a :class:`~pyEDAA.Reports.CodeCoverage.GHDL.CoverageMode` - GHDL writes only ``stmt``, statement
coverage -, and per line with a coverage point, whether a statement of the line ran.
GHDL instruments the design's sources, not the libraries ``ieee`` and ``std``.

:meth:`~pyEDAA.Reports.CodeCoverage.GHDL.Document.ToCoverageSummary` converts it to the common model, as
``ghdl coverage --format=lcov`` converts it to an lcov tracefile:

* A file's path is the name it was analyzed by, relative to the directory GHDL ran in. A file analyzed in another
  directory is prefixed by that directory.
* A line that ran is covered, a line that didn't uncovered. The format states a flag per line, not a count: lcov's
  count ``1`` means the line ran, at least once.
* The format has no branches and no excluded lines, and names no units: no design units, processes or subprograms.

:class:`~pyEDAA.Reports.CodeCoverage.GHDL.MergedReport` merges the coverage files of several simulation runs: a line
ran, if it ran in one of the runs. The files must agree on each source file's checksum.

.. code-block:: Python

   from pathlib import Path
   from pyEDAA.Reports.CodeCoverage.GHDL import Document, MergedReport

   documents = []
   for path in sorted(Path(".").glob("coverage-*.json")):
     documents.append(Document(path, analyzeAndConvert=True))

   summary = MergedReport("Counter", documents).ToCoverageSummary()
   for file in summary.IterateFiles():
     print(f"{file.Path}: {file.LineCoverage:.1%}")

.. hint::

   ``ghdl coverage`` reads several coverage files too, but a line's result there is the result of the last file naming
   the line, so the merged coverage depends on the order of the files.


.. _CODECOV/Formats/Gcov:

gcov JSON
=========

GCC's gcov writes its JSON report with ``gcov --json-format``, for any language GCC compiles - e.g. C, C++, Fortran,
Ada, or VHDL with GHDL's GCC backend: gzip-compressed to a :file:`*.gcov.json.gz` file per data file, or - with
``--stdout`` - as plain JSON, one line per data file. :class:`pyEDAA.Reports.CodeCoverage.Gcov.Document` reads either,
validates each JSON object against the JSON Schema of the format version it states -
:ref:`Gcov-1.schema.json <SCHEMAS/Gcov-1>` for format 1 (GCC 9 to 13), :ref:`Gcov-2.schema.json <SCHEMAS/Gcov-2>` for
format 2 (GCC 14 and later) - and reads it into the format's model: the data files, their source files, functions and
lines - in format 2 with the IDs of the basic blocks of a line. An object stating another format version is rejected.

:meth:`~pyEDAA.Reports.CodeCoverage.Gcov.Document.ToCoverageSummary` converts it to the common model:

* A file's path is relative to the directory the compiler ran in, which becomes a source directory.
* A line's ``count`` is its count. A line several functions share - e.g. the instantiations of a template - or
  several data files state - e.g. a header - becomes one line, its counts added. gcov's own summary counts the lines
  of a template once per instantiation.
* A file becomes a :class:`~pyEDAA.Reports.CodeCoverage.SourceFile`, its functions - by demangled name, e.g.
  ``Containers::Stack::Pop()`` - become functions, each spanning its first to its last line, with its execution count.
  A demangled name doesn't tell a class from a namespace, so there are no classes and methods.
* Basic blocks have no counterpart in the common model; the format's model keeps them. The format has no excluded
  lines.

.. code-block:: Python

   from pathlib import Path
   from pyEDAA.Reports.CodeCoverage.Gcov import Document

   report = Document(Path("main.gcov.json.gz"), analyzeAndConvert=True)
   summary = report.ToCoverageSummary()
   for unit in summary.IterateUnits():
     print(f"{unit.QualifiedName}: {unit.LineCoverage:.1%}")

The pipeline jobs ``Cpp-GoogleTest`` and ``Cpp-Catch2`` write gcov JSON for the examples in
:file:`examples/Cpp/GoogleTest` and :file:`examples/Cpp/Catch2`, see :ref:`UNITTEST/Tool/GoogleTest`. A source file
outside the directory the compiler ran in keeps its absolute path.


.. _CODECOV/Formats/LCOV:

lcov Tracefile
==============

lcov writes its tracefile with ``lcov --capture``; many tools write the format too - e.g. llvm-cov
(``llvm-cov export -format=lcov``), coverage.py (``coverage lcov``) or GHDL (``ghdl coverage --format=lcov``). The
format is specified by lcov's manual page
`geninfo(1) <https://github.com/linux-test-project/lcov/blob/v2.3.1/man/geninfo.1>`__, section *TRACEFILE FORMAT*: a
text file of records, one per line, e.g. ``DA:<line number>,<execution count>``.
:class:`pyEDAA.Reports.CodeCoverage.LCOV.Document` reads it with a strict line parser - an unknown, malformed or
misplaced record raises an exception noting its line - into the format's model: a section per source file and test,
with its functions and their aliases, its lines with counts and checksums, its branches, its MC/DC conditions, and the
summaries it states.

:meth:`~pyEDAA.Reports.CodeCoverage.LCOV.Document.ToCoverageSummary` converts it to the common model:

* A section names its source file in ``SF``. The sections of one file - one per test, named by ``TN`` - become one file,
  their counts added.
* A line's ``DA`` count is its count. A branch - ``BRDA`` - is covered, if it was taken; a branch never evaluated -
  ``-`` - is uncovered without count. A line is partially covered, if one of its branches wasn't taken.
* A file becomes a :class:`~pyEDAA.Reports.CodeCoverage.SourceFile` unit, its functions - ``FN``, or ``FNL`` with its
  aliases ``FNA`` - :class:`~pyEDAA.Reports.CodeCoverage.Function` units, each spanning its start to its end line. A
  function without end line names its start line only.
* The format has no excluded lines - lcov leaves them out -, no branch targets and no units but functions. The MC/DC
  conditions - ``MCDC`` - stay in the format's model.

.. code-block:: Python

   from pathlib import Path
   from pyEDAA.Reports.CodeCoverage.LCOV import Document

   tracefile = Document(Path("coverage.info"), analyzeAndConvert=True)
   summary = tracefile.ToCoverageSummary()
   for unit in summary.IterateUnits():
     print(f"{unit.QualifiedName}: {unit.Status.name}, {unit.LineCoverage:.1%}")

The tools write different parts of the format:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Tool
     - Tracefile
   * - lcov 2.3 (GCC)
     - ``TN`` from ``--test-name``. Functions as ``FNL`` leader with end line and ``FNA`` aliases. Branches never
       evaluated as ``-``. ``MCDC`` conditions with ``--mcdc-coverage``, summarized by ``MCF`` and ``MCH`` - the manual
       page names them ``MRF`` and ``MRH``, while lcov writes and reads ``MCF`` and ``MCH``. Checksums with
       ``--checksum``.
   * - llvm-cov 19
     - No ``TN``. Functions as ``FN`` without end line and ``FNDA``; a static function of a header named after its
       translation unit, e.g. ``Classify.c:Clamp``. No branch as ``-``.
   * - coverage.py 7.16
     - No ``TN``. Functions as ``FN`` with end line, named by qualified names like ``Circle.Area``. Branches named after
       their target, e.g. ``jump to line 8``. A section without records for an empty file.
   * - GHDL 7.0
     - ``TN`` only before the first section. Each file as one function ``file`` at line 1. No summaries. Lines of a
       subprogram, which was never called, aren't listed.


.. _CODECOV/Formats/GoCoverProfile:

Go Cover Profile
================

``go test -coverprofile=coverage.out -covermode=count`` writes Go's cover profile: a text format, whose first line
names the mode and every further line a block of a source file. pyEDAA.Reports doesn't read it yet.

.. code-block:: text

   mode: count
   github.com/edaa-org/pyEDAA.Reports/examples/Go/testing/counter/counter.go:34.44,35.18 1 2
   github.com/edaa-org/pyEDAA.Reports/examples/Go/testing/counter/counter.go:35.18,37.3 1 1

* The mode is ``set`` - whether a block ran: ``0`` or ``1`` -, ``count`` - how often - or ``atomic`` - how often,
  counted thread-safe.
* A block is ``<file>:<start line>.<start column>,<end line>.<end column> <statements> <count>``: the file named by its
  package's import path, the block's start and end - columns in bytes, starting at 1, the end exclusive -, the number of
  its statements and its count.
* A block is a sequence of statements, not a line: it starts and ends inside a line, two blocks share the line, where a
  branch starts. The format has no branches, functions or excluded lines.
* Each package's test binary adds the blocks of its package. A package without tests is listed with count ``0``; a
  package, whose test binary panicked, is missing.

Converters write it in the formats other tools read:

gocover-cobertura
  ``gocover-cobertura < coverage.out > cobertura.xml`` writes :ref:`Cobertura XML <CODECOV/Formats/Cobertura>` after
  ``coverage-04.dtd``. A package is named by its import path, a class by its receiver type - ``-`` for the package's
  functions -, a method by its function; so several classes name the same file, relative to the module's directory in
  ``<source>``. Every line from a block's start to its end line gets the block's count - also a blank line or a comment
  line -, a line shared by two blocks the sum of their counts. ``version`` is empty, ``timestamp`` in milliseconds and
  the branch figures are ``0``. ``-ignore-non-code-lines`` leaves out lines without code, ``-by-files`` writes a class
  per file.

gcov2lcov
  ``gcov2lcov -infile coverage.out -outfile coverage.info`` writes an lcov tracefile: per file a record of ``TN:``
  (empty), ``SF:``, ``DA:``, ``LF:`` and ``LH:``, but no function or branch records. A line's count is figured as by
  gocover-cobertura. ``SF:`` is relative to the repository, if a ``.git`` directory is found above the file, otherwise
  absolute. The order of the records changes from run to run.

The pipeline job ``Go-Test`` writes all three for the example in :file:`examples/Go/testing`, see
:ref:`UNITTEST/Tool/Go`.


.. _CODECOV/Formats/OpenCover:

OpenCover XML
=============

OpenCover's XML format - written e.g. by coverlet (``opencover``) for .NET - has a root ``<CoverageSession>`` and a
``<Summary>`` on each level: the numbers of sequence and branch points and of the visited ones, the coverage ratios and
the cyclomatic complexity. A ``<Module>`` (assembly) lists its source files (``<File uid="..." fullPath="..."/>``) and
classes, a class its methods. A method states its ``<SequencePoints>`` - visit count ``vc``, the source range from
``sl``/``sc`` to ``el``/``ec``, branch exits ``bec`` and visited ones ``bev`` - and its ``<BranchPoints>`` - visit
count, IL offsets of the branch and its target, and the line. coverlet writes no real columns.

There is no reader yet.


.. _CODECOV/Formats/CoverletJSON:

coverlet JSON
=============

coverlet's own JSON report nests objects by assembly (e.g. ``MyLibrary.dll``), absolute source file path, class and
method (IL signature, e.g. ``System.Void MyLibrary.Counter::Decrement()``). A method has ``Lines`` - the count of
each line - and ``Branches`` - a list of ``Line``, IL ``Offset`` and ``EndOffset``, ``Path``, ``Ordinal`` and ``Hits``.
The report states no figures and no ratios.

There is no reader yet.


.. _CODECOV/CLI:

Command Line
************

The command ``coverage`` of :program:`pyedaa-reports` reads a report of any format above, which a reader exists for,
shows its line and branch figures and, with ``--output``, writes it as Cobertura XML - so any format becomes the format
most tools read (see :ref:`References/cli`):

.. code-block:: console

   $ pyedaa-reports coverage --input=Gcov-JSON:main.gcov.json.gz --output=Cobertura:coverage.xml
   Reading code coverage report 'main.gcov.json.gz' (Gcov-JSON) ...
   Lines:    26 of 27 covered (96.3%)
   Writing Cobertura XML report 'coverage.xml' ...

``--input`` names the format and the file: ``Any-Cobertura``, ``CoveragePy-Cobertura``, ``CoveragePy-JSON``,
``Gcov-JSON``, ``GHDL-JSON`` or ``LCOV``, spelled as here (:class:`~pyEDAA.Reports.CLI.Coverage.InputFormat`). A file
without format is read as ``Any-Cobertura``. ``--output`` names the format ``Cobertura``
(:class:`~pyEDAA.Reports.CLI.Coverage.OutputFormat`, also the default) and the file. ``-v`` adds the figures of each
file.


.. _CODECOV/Tools:

Tools
*****

.. _CODECOV/Tool/DotNet:

.NET: coverlet, Microsoft's code coverage collector, ReportGenerator
====================================================================

* https://github.com/coverlet-coverage/coverlet
* https://github.com/microsoft/codecoverage
* https://github.com/danielpalme/ReportGenerator

The example in :file:`examples/CSharp/xUnit` is built and run by the pipeline job ``CSharp-xUnit`` (see
:ref:`UNITTEST/Tool/DotNetTest`). Its tests run twice:

* with coverlet (``coverlet.collector``, ``dotnet test --collect "XPlat Code Coverage"``), writing Cobertura XML, an
  lcov tracefile, OpenCover XML and coverlet's JSON. ``coverlet.msbuild`` writes the same reports.
* with Microsoft's code coverage collector (part of ``Microsoft.NET.Test.Sdk``,
  ``dotnet test --collect "Code Coverage;Format=cobertura"``), writing Cobertura XML.

ReportGenerator converts coverlet's Cobertura report to Cobertura XML and an lcov tracefile of its own.

The three Cobertura reports differ:

.. list-table::
   :header-rows: 1
   :widths: 22 26 26 26

   * - Feature
     - coverlet
     - Microsoft
     - ReportGenerator
   * - A line's ``branch``
     - ``True``, ``False``
     - ``True``, ``False``
     - ``true``, ``false``
   * - Read by :class:`~pyEDAA.Reports.CodeCoverage.Cobertura.Document`
     - no: ``True`` isn't an XML Schema boolean
     - no: ``True`` isn't an XML Schema boolean
     - yes
   * - ``version`` of ``<coverage>``
     - ``1.9``
     - ``1.9``
     - ``0``, with a DOCTYPE naming ``coverage-04.dtd``
   * - ``filename`` of ``<class>``
     - relative to the only ``<source>``
     - absolute, no ``<sources>``
     - absolute, and a ``<source>``
   * - A line's ``hits``
     - count
     - ``0`` or ``1``
     - count
   * - ``<conditions>``
     - one per branching line, ``number`` is the IL offset
     - one per branching line, ``number`` is ``0``
     - none
   * - Compiler-generated classes, e.g. of an ``async`` method
     - own class, nested by ``/``: ``Counter/<IncrementAsync>d__6``
     - own class, nested by ``.``: ``Counter.<IncrementAsync>d__6``; also a lambda's class ``<>c``
     - merged into the declaring class and method
   * - Test assembly
     - excluded
     - included
     - excluded
   * - ``signature`` of ``<method>``
     - ``(System.Int32,System.Int32)``
     - ``(int, int)``
     - ``(System.Int32,System.Int32)``

All three name a class with its namespace, e.g. ``MyLibrary.Calculator`` in package ``MyLibrary``, and state
``complexity`` on ``<method>``, which ``coverage-04.dtd`` doesn't declare; coverlet's ``<coverage>`` lacks the
``complexity`` the DTD requires.

The two lcov tracefiles differ too:

.. list-table::
   :header-rows: 1
   :widths: 22 39 39

   * - Feature
     - coverlet
     - ReportGenerator
   * - ``TN:``
     - none
     - an empty one at the start
   * - ``FN:`` line number
     - the line before the function's first line
     - the function's first line
   * - ``FN:`` function name
     - IL signature with commas, e.g. ``System.Int32 MyLibrary.Calculator::Add(System.Int32,System.Int32)``
     - method name and parameter types, e.g. ``Add(System.Int32,System.Int32)``
   * - ``BRDA:`` block
     - IL offset of the branch, e.g. ``BRDA:11,7,0,2``
     - line number, e.g. ``BRDA:11,11,0,1``
   * - ``BRDA:`` branch
     - ``0`` and ``1`` per block
     - numbered through the file
   * - ``BRDA:`` taken
     - count
     - ``1``, or ``-`` for a branch not taken
   * - ``DA:`` order
     - by function; a state machine's lines follow the lines of its class
     - ascending

Both use the function records of lcov before version 2.2 (``FN``, ``FNDA``); coverlet's tracefile doesn't end with a
newline.
