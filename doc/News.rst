.. _NEWS:

News
####

See :gh:`pyEDAA.Reports Release Pages <edaa-org/pyEDAA.Reports/releases>` for detail release notes on every release.


Version 0.20 (2026)
*******************

.. topic:: :gh:`v0.20.0 - unreleased <edaa-org/pyEDAA.Reports/releases/v0.20.0>`

   Since v0.19.1, the package grew from 74 to 359 classes in 15 to 59 modules, and the testsuite from 132 to 1110
   test methods. pyEDAA.Reports requires pyTooling 10.

   .. rubric:: New Features

   * :mod:`pyEDAA.Reports.CodeCoverage` is a new **code coverage data model in two layers**: a model per report
     format, converted to a common model.

     * The common model has a physical hierarchy - :class:`~pyEDAA.Reports.CodeCoverage.CoverageSummary` (the
       report's root) |rarr| :class:`~pyEDAA.Reports.CodeCoverage.Directory` |rarr|
       :class:`~pyEDAA.Reports.CodeCoverage.File` |rarr| :class:`~pyEDAA.Reports.CodeCoverage.Line` |rarr|
       :class:`~pyEDAA.Reports.CodeCoverage.Branch` - and a logical one of language units -
       :class:`~pyEDAA.Reports.CodeCoverage.Package`, :class:`~pyEDAA.Reports.CodeCoverage.Module`,
       :class:`~pyEDAA.Reports.CodeCoverage.SourceFile`, :class:`~pyEDAA.Reports.CodeCoverage.Class`,
       :class:`~pyEDAA.Reports.CodeCoverage.Function` and :class:`~pyEDAA.Reports.CodeCoverage.Method` -, each
       spanning its file from ``StartLine`` to ``EndLine``. Every element knows its ``Parent`` and the report's
       ``Root``.
     * A line, a branch and a unit carry a :class:`~pyEDAA.Reports.CodeCoverage.LineCoverageStatus` and, if the
       report says, a coverage count; a branch names its target line.
     * A file keeps its lines in a list indexed by line number: :meth:`~pyEDAA.Reports.CodeCoverage.File.GetLine`,
       :meth:`~pyEDAA.Reports.CodeCoverage.File.IterateLines`, :attr:`~pyEDAA.Reports.CodeCoverage.File.LastLineNumber`.
     * :meth:`Directory.IterateFiles() <pyEDAA.Reports.CodeCoverage.Directory.IterateFiles>`,
       :meth:`CoverageSummary.IterateUnits() <pyEDAA.Reports.CodeCoverage.CoverageSummary.IterateUnits>` and
       :meth:`Unit.IterateUnits() <pyEDAA.Reports.CodeCoverage.Unit.IterateUnits>` take an optional predicate and
       yield the elements in the order they were added.
     * :meth:`CoverageSummary.Aggregate() <pyEDAA.Reports.CodeCoverage.CoverageSummary.Aggregate>` computes the
       counters of every file, directory and unit - lines, branches, partial lines, and the line, branch and combined
       coverage.
     * :class:`~pyEDAA.Reports.CodeCoverage.Document` is the abstract base of a report file, read in two steps
       (``Analyze()``, ``Convert()``) and converted by ``ToCoverageSummary()``. A report that can't be read, decoded
       or parsed raises :exc:`~pyEDAA.Reports.CodeCoverage.CodeCoverageError`, chained to the cause.
     * A report format's model is one module; a package holds a format's dialects, a module each.

   * Readers for **ten code coverage formats**, each with a format model converted to the common model:

     * :mod:`pyEDAA.Reports.CodeCoverage.Cobertura`: the Cobertura XML format, after Cobertura's DTD. A report is
       validated against the new :file:`Any-Cobertura.xsd`; :file:`Cobertura-04.xsd` is the strict translation of
       the DTD. :mod:`~pyEDAA.Reports.CodeCoverage.Cobertura.CoveragePyCobertura` reads coverage.py's dialect
       strictly, :mod:`~pyEDAA.Reports.CodeCoverage.Cobertura.NVCCobertura` NVC's dialect
       (``nvc --cover-export --format=cobertura``), each with a schema of its own.
     * :mod:`pyEDAA.Reports.CodeCoverage.LCOV`: lcov's tracefile format, also written by llvm-cov, coverage.py and
       GHDL - a strict line parser. Branches (``BRDA``) and MC/DC conditions (``MCDC``) become branches of their
       line.
     * :mod:`pyEDAA.Reports.CodeCoverage.CoveragePy`: coverage.py's JSON format (``coverage json``, formats 2 and
       3). The stated format version chooses the JSON Schema, reverse-engineered from coverage.py.
     * :mod:`pyEDAA.Reports.CodeCoverage.GHDL`: GHDL's own coverage JSON (``ghdl -r --coverage``, statement
       coverage). :class:`~pyEDAA.Reports.CodeCoverage.GHDL.MergedReport` merges several simulation runs: a line ran
       if it ran in any run.
     * :mod:`pyEDAA.Reports.CodeCoverage.Gcov`: the JSON report GCC's gcov writes (``gcov --json-format``),
       gzip-compressed or plain, with branches, calls and MC/DC conditions (``gcc -fcondition-coverage``). Each JSON
       object is validated against the schema of its format version (GCC 9 to 13, GCC 14 and later).
     * :mod:`pyEDAA.Reports.CodeCoverage.JaCoCo`: JaCoCo's XML report (``jacococli.jar report --xml``, Maven, Ant,
       Gradle), validated against a translation of JaCoCo's DTD.
     * :mod:`pyEDAA.Reports.CodeCoverage.LLVM`: LLVM's JSON code coverage export (``llvm-cov export -format=text``,
       from Clang, rustc or Swift), format versions 2.0.0 to 3.1.0. Line counts are derived from the segments as
       ``llvm-cov show`` derives them.
     * :mod:`pyEDAA.Reports.CodeCoverage.AldecUCDB`: the XML Aldec's ``acdb2xml`` exports from a coverage database
       of Riviera-PRO or Active-HDL, with a schema reverse-engineered from Riviera-PRO reports. Only statement
       coverage is converted. Transferred from pyEDAA.UCIS, contributed by Aldec.
     * :mod:`pyEDAA.Reports.CodeCoverage.UCIS`: the XML interchange format of the Accellera UCIS 1.0 standard.
       Statements and branches are converted; toggle, condition, FSM, assertion and covergroup coverage are read into
       the format's model only. :mod:`~pyEDAA.Reports.CodeCoverage.UCIS.PyUCIS` reads pyucis' dialect.
     * :mod:`pyEDAA.Reports.CodeCoverage.QuestaSim`: the XML report Questa SIM writes from its coverage database
       with ``vcover report -xml -details``. A report without details or a functional coverage report raises
       :exc:`~pyEDAA.Reports.CodeCoverage.CodeCoverageError` with a hint.

   * :mod:`pyEDAA.Reports.CodeCoverage.Cobertura` writes the common model - read from any format - as Cobertura XML:
     :meth:`Document.FromCoverageSummary() <pyEDAA.Reports.CodeCoverage.Cobertura.Document.FromCoverageSummary>`,
     ``Generate()``, ``Write()``, valid according to :file:`Cobertura-04.xsd`.

   * :program:`pyedaa-reports` ``coverage`` is a new command: it reads a code coverage report in one of thirteen
     formats (``--input=[<format>:]<file>``), shows its line and branch figures and writes it as Cobertura XML
     (``--output=[Cobertura:]<file>``).

   * :mod:`pyEDAA.Reports.DocumentationCoverage` is a **language-neutral documentation coverage model**, filled by
     a reader per language - Python for now.

     * :class:`~pyEDAA.Reports.DocumentationCoverage.ItemKind` names an item's language construct, e.g. ``Class``,
       ``Method``, ``Entity``, ``Port``; each kind belongs to an
       :class:`~pyEDAA.Reports.DocumentationCoverage.ItemCategory`.
     * :class:`~pyEDAA.Reports.DocumentationCoverage.CoverageCounters` counts total, expected, covered, uncovered,
       ignored and excluded items and computes the coverage;
       :class:`~pyEDAA.Reports.DocumentationCoverage.CoverageState` has the new flag ``Excused``.
     * The physical hierarchy - :class:`~pyEDAA.Reports.DocumentationCoverage.DocumentationReport` |rarr|
       :class:`~pyEDAA.Reports.DocumentationCoverage.Directory` |rarr|
       :class:`~pyEDAA.Reports.DocumentationCoverage.File` - and the logical one of
       :class:`~pyEDAA.Reports.DocumentationCoverage.Item`\ s, whose counters count the item and every item below
       it.
     * :class:`~pyEDAA.Reports.DocumentationCoverage.SourceFileWarning` is a critical warning for a source file that
       can't be read or parsed.

   * :class:`pyEDAA.Reports.DocumentationCoverage.Python.Analyzer` reads a package's Python source code and returns
     its aggregated documentation report. It counts what docstr_coverage counts, plus class fields and module
     variables documented in the forms Sphinx' autodoc reads, and honours docstr_coverage's ``inherited`` and
     ``excused`` comments. :class:`~pyEDAA.Reports.DocumentationCoverage.Python.CountedItems` chooses fields,
     variables, protected and private items; regular expressions exclude items. Files are read in the same order on
     every platform.

   * :mod:`pyEDAA.Reports.Requirements` is a new data model for requirements management: a
     :class:`~pyEDAA.Reports.Requirements.RequirementSpecification` with registries of persons, personas, labels,
     documents and layers; :class:`~pyEDAA.Reports.Requirements.Requirement`\ s with a
     :class:`~pyEDAA.Reports.Requirements.RequirementKind` (after ISO/IEC/IEEE 29148), an
     :class:`~pyEDAA.Reports.Requirements.Obligation` and an :class:`~pyEDAA.Reports.Requirements.ItemState`;
     specification items in an N:M relation to the requirements; :class:`~pyEDAA.Reports.Requirements.Link`\ s
     between items; an item's history, rationale, verification methods and acceptance criteria; and traces along the
     links, transitive and safe in cycles.

   * :mod:`pyEDAA.Reports.RiskManagement` is a new data model of a risk register: a
     :class:`~pyEDAA.Reports.RiskManagement.Risk` with probability, impact and state; implications and mitigations,
     shared by risks; links between risks of a kind; a risk's score and level, owner and next review.

   * :mod:`pyEDAA.Reports` holds what the data models share: :class:`~pyEDAA.Reports.KeyValuePairsMixin` attaches
     key-value pairs to an element, accessed with the dictionary syntax; :class:`~pyEDAA.Reports.Person` is a real
     person - user ID, name, e-mail address.
   * The data models' errors derive from pyTooling's common bases :exc:`~pyTooling.Exceptions.DuplicateElementError`,
     :exc:`~pyTooling.Exceptions.AlreadyInHierarchyError` and :exc:`~pyTooling.Exceptions.NotInSameHierarchyError`. Each
     model raises one error per duplicate element kind, e.g.
     :exc:`~pyEDAA.Reports.CodeCoverage.DuplicateFileError`, and an error named after its root, e.g.
     :exc:`~pyEDAA.Reports.RiskManagement.AlreadyInRiskRegisterError`.

   * :mod:`pyEDAA.Reports.Unittesting`

     * A testcase keeps the message and details explaining its status and its captured standard output and standard
       error: the new :class:`~pyEDAA.Reports.Unittesting.TestcaseOutputMixin` with the read-only properties
       ``Message``, ``Details``, ``StandardOutput`` and ``StandardError``.
     * Every test entity carries a ``Title``, a ``Summary`` and a ``Description``, written for a reader; copies,
       conversions and merges keep them.

   * :mod:`pyEDAA.Reports.Unittesting.JUnit`: the reader keeps the ``message`` attribute and the text of
     ``<failure>``, ``<error>`` and ``<skipped>``, and the text of ``<system-out>`` and ``<system-err>``, for every
     dialect; the writers emit them again.

   * New JUnit dialects, each read, validated by a new strict schema, converted and written, and available in
     :program:`pyedaa-reports` ``unittest``:

     * :mod:`~pyEDAA.Reports.Unittesting.JUnit.Catch2JUnit`: Catch2's JUnit reporter (v3), as ``Catch2-JUnit``.
     * :mod:`~pyEDAA.Reports.Unittesting.JUnit.NextestJUnit`: cargo-nextest's report, as ``nextest-JUnit``. A flaky
       test is passed with a rerun count above zero.
     * :mod:`~pyEDAA.Reports.Unittesting.JUnit.GoJUnitReport`: go-junit-report (v2), as ``GoJUnitReport-JUnit``.
     * :mod:`~pyEDAA.Reports.Unittesting.JUnit.TestLoggerJUnit`: the .NET test logger JunitXml.TestLogger
       (``dotnet test --logger junit``), as ``TestLogger-JUnit``.

   * :mod:`pyEDAA.Reports.Unittesting.pyTooling` reads the XML test report pyTooling's pytest plugin writes
     (``--pytooling-xml``) - nested test suites, the texts, the message and the runner's node ID. The file is
     validated against the schema pyTooling 10 ships.

   * :mod:`pyEDAA.Reports.Unittesting.OpenTestReporting` reads
     `Open Test Reporting <https://github.com/ota4j-team/open-test-reporting>`__ 0.2.0, the XML format the JUnit
     Platform (JUnit 5 and 6) writes: :mod:`~pyEDAA.Reports.Unittesting.OpenTestReporting.Events` the event-based
     format, :mod:`~pyEDAA.Reports.Unittesting.OpenTestReporting.Hierarchy` the hierarchical one. Open Test
     Reporting's XSDs are bundled unmodified.

   * :program:`pyedaa-reports` ``unittest``: the format is optional. A file without format is read as ``Any-JUnit``
     (``--input=[<format>:]<file>``, ``--merge=[<format>:]<pattern>``) and written as ``pyTest-JUnit``
     (``--output=[<format>:]<file>``). An unsupported format notes the supported ones and the default. A value may
     hold a Windows drive letter.

   .. rubric:: Breaking Changes

   * ⚠️ pyEDAA.Reports requires pyTooling 10: ``pyTooling[terminal] >= 10.0.0rc2, < 11.0``. The JUnit dialects
     merge their doc-strings with ``DocStringMergeStrategy.BaseLast``, as pyTooling 10 replaced
     ``InheritDocString``'s ``merge``.

   * ⚠️ :exc:`~pyEDAA.Reports.ReportException` derives from :exc:`pyTooling.Exceptions.ExceptionBase` instead of the
     builtin :exc:`Exception`. ``ex.args`` of any exception of this package is now empty; ``str(ex)`` is unchanged.
     Read ``ex.message`` or ``str(ex)`` instead of ``ex.args[0]``.

   * ⚠️ The exception classes carry the ``***Error`` suffix. ``***Exception`` is reserved for
     :exc:`~pyEDAA.Reports.ReportException`, the package-wide base. No aliases are kept - rename at the use site.
     The four dialect-specific variants in :mod:`~pyEDAA.Reports.Unittesting.JUnit` are renamed with them.

     .. list-table::
        :header-rows: 1

        * - Old name
          - New name
        * - ``UnittestException``
          - :exc:`~pyEDAA.Reports.Unittesting.UnittestError`
        * - ``AlreadyInHierarchyException``
          - :exc:`~pyEDAA.Reports.Unittesting.AlreadyInTestsuiteError`
        * - ``DuplicateTestsuiteException``
          - :exc:`~pyEDAA.Reports.Unittesting.DuplicateTestsuiteError`
        * - ``DuplicateTestcaseException``
          - :exc:`~pyEDAA.Reports.Unittesting.DuplicateTestcaseError`
        * - ``DocCoverageException``
          - :exc:`~pyEDAA.Reports.DocumentationCoverage.DocCoverageError`
        * - ``JUnitException``
          - :exc:`~pyEDAA.Reports.Unittesting.JUnit.JUnitErrorMixin`

   * ⚠️ ``parent`` is a keyword-only parameter: a positional ``parent`` raises :exc:`TypeError`. Pass ``parent=...``
     to the constructors of :mod:`pyEDAA.Reports.Unittesting`, :mod:`pyEDAA.Reports.Unittesting.JUnit` and
     :class:`~pyEDAA.Reports.DocumentationCoverage.Base`.

   * ⚠️ :mod:`pyEDAA.Reports.Unittesting`: ``title``, ``summary`` and ``description`` follow ``name`` in the
     constructors of :class:`~pyEDAA.Reports.Unittesting.Testcase`, :class:`~pyEDAA.Reports.Unittesting.Testsuite`,
     :class:`~pyEDAA.Reports.Unittesting.TestsuiteSummary` and their base classes, so every positional argument
     after ``name`` is bound three parameters off. Pass the parameters after ``name`` as keyword arguments.

   * ⚠️ :program:`pyedaa-reports` ``unittest`` matches format names case-sensitively: ``pytest-junit`` is rejected.
     Write the names as listed (``pyTest-JUnit``, ``Any-JUnit``, ...).

   * ⚠️ :mod:`pyEDAA.Reports.DocumentationCoverage`: ``Class``, ``Module``, ``Package``, ``_Type`` and ``_Unit`` are
     removed; :class:`~pyEDAA.Reports.DocumentationCoverage.Base` is the base of the new model. Use
     :class:`~pyEDAA.Reports.DocumentationCoverage.Item` with an
     :class:`~pyEDAA.Reports.DocumentationCoverage.ItemKind`.

   * ⚠️ :mod:`pyEDAA.Reports.DocumentationCoverage.Python`: ``Coverage``, ``AggregatedCoverage``,
     ``ClassCoverage``, ``ModuleCoverage`` and ``PackageCoverage`` are removed. Use
     :class:`~pyEDAA.Reports.DocumentationCoverage.Item` and its counters; a package's own :file:`__init__.py`
     figures are its file's counters.

   * ⚠️ :class:`~pyEDAA.Reports.DocumentationCoverage.DocStrCoverage.DocStrCoverage` and
     :exc:`~pyEDAA.Reports.DocumentationCoverage.DocStrCoverage.DocStrCoverageError` moved from
     :mod:`~pyEDAA.Reports.DocumentationCoverage.Python` to :mod:`pyEDAA.Reports.DocumentationCoverage.DocStrCoverage`;
     ``SearchDirectories`` is renamed ``SearchDirectory``. Import from the new module; there is no alias.

   .. rubric:: Changes

   * ⚠️ :mod:`pyEDAA.Reports.DocumentationCoverage`: the class-per-construct model is replaced by the
     language-neutral model of :class:`~pyEDAA.Reports.DocumentationCoverage.Item`,
     :class:`~pyEDAA.Reports.DocumentationCoverage.DocumentationReport`,
     :class:`~pyEDAA.Reports.DocumentationCoverage.Directory` and
     :class:`~pyEDAA.Reports.DocumentationCoverage.File`.
   * ⚠️ :mod:`pyEDAA.Reports.DocumentationCoverage.DocStrCoverage` is a new module holding
     :class:`~pyEDAA.Reports.DocumentationCoverage.DocStrCoverage.DocStrCoverage`, formerly in ``.Python``.
     ``Convert()`` returns an aggregated documentation report with an item per doc-string docstr_coverage expects;
     before, it only set per-file counters.
   * ⚠️ :exc:`~pyEDAA.Reports.ReportException` - and with it every exception of this package - joins the pyTooling
     exception hierarchy, so ``except ExceptionBase`` covers this package like it covers ``pyEDAA.CLITool``,
     ``pyEDAA.OSVVM``, ``pyEDAA.OutputFilter`` and ``pyEDAA.ToolSetup``.
   * ⚠️ The exception names follow :pep:`8` - *"you should use the suffix Error on your exception names"* - instead
     of the package's older ``***Exception`` convention.
   * ⚠️ :program:`pyedaa-reports` ``unittest``: the format names are matched case-sensitively, as ``coverage``
     matches them.
   * ⚠️ :mod:`pyEDAA.Reports.Unittesting`: ``title``, ``summary`` and ``description`` follow ``name`` in the
     constructors of :class:`~pyEDAA.Reports.Unittesting.Testcase`, :class:`~pyEDAA.Reports.Unittesting.Testsuite`
     and :class:`~pyEDAA.Reports.Unittesting.TestsuiteSummary`; ``message``, ``details``, ``standardOutput`` and
     ``standardError`` follow ``keyValuePairs`` in :class:`~pyEDAA.Reports.Unittesting.Testcase`'s.
   * ⚠️ ``parent`` is a keyword-only parameter in every constructor taking one. A positional ``parent`` raises
     :exc:`TypeError` instead of landing in another parameter.
   * ⚠️ Requirements: ``pyTooling[terminal] >= 10.0.0rc2, < 11.0`` instead of ``>= 9.0, < 10.0``. The build
     requires ``pyTooling >= 10.0.0rc2, < 11.0``: pip ignores pre-releases unless a requirement names one.
   * :mod:`pyEDAA.Reports.CLI`: :func:`~pyEDAA.Reports.CLI.main` catches :exc:`~pyEDAA.Reports.ReportException`
     and reports it. Before, every error of this package but ``UnittestException`` was announced as *"an unknown or
     unhandled exception"* with an invitation to file a bug.
   * :mod:`pyEDAA.Reports.Unittesting.JUnit`: the reader reads the file, then parses its bytes, each step reporting
     its own error, like the other readers. Before, every exception became *Couldn't open '...'*.
   * :class:`pyEDAA.Reports.Unittesting.JUnit.Document` takes ``name``, ``startTime``, ``duration``, ``status`` and
     ``testsuites`` as keyword parameters; :meth:`~pyEDAA.Reports.Unittesting.JUnit.Document.FromTestsuiteSummary`
     constructs the document from them and computes the counters; the dialects inherit it.
   * The generic JUnit reader ignores ``<flakyFailure>``, ``<flakyError>``, ``<rerunFailure>`` and ``<rerunError>``
     in a ``<testcase>``, like ``<properties>``; it raised *Unknown element ... in junit file*. A dialect's schema
     decides whether they are allowed.
   * :meth:`Testsuite.Aggregate() <pyEDAA.Reports.Unittesting.Testsuite.Aggregate>` counts a testcase with status
     ``ExpectedFailed`` as passed and ``UnexpectedPassed`` as failed instead of raising
     :exc:`~pyEDAA.Reports.Unittesting.UnittestError`.
   * Every module with code carries ``from __future__ import annotations`` and writes forward references unquoted.
   * New requirement ``jsonschema ~= 4.26`` for the JSON Schemas of JSON report formats.
   * The ``test`` extra describes every test level: :file:`tests/requirements.txt` includes
     :file:`tests/app/requirements.txt`.
   * Python 3.15 is supported and listed in the classifiers.
   * The report readers store a measured duration as a :class:`~datetime.timedelta`, as pyTooling's
     :class:`~pyTooling.Stopwatch.Stopwatch` hands it out from pyTooling 10.0.0rc4 on; ``AnalysisDuration`` and
     ``ModelConversionDuration`` return it unchanged instead of converting seconds. A duration not measured yet is
     a negative :class:`~datetime.timedelta`, as before.
   * Dependencies: ``wheel ~= 0.48.0``, ``lxml >= 6.1.3``, ``Coverage ~= 7.16``, ``mypy ~= 2.4``.

   .. rubric:: Bug Fixes

   * :meth:`Testsuite.AddTestcase() <pyEDAA.Reports.Unittesting.Testsuite.AddTestcase>` raised a :exc:`ValueError`
     for a test case of another test suite instead of the documented
     :exc:`~pyEDAA.Reports.Unittesting.AlreadyInTestsuiteError`.
   * :mod:`pyEDAA.Reports.Unittesting.JUnit` and its dialects:

     * ``TestsuiteSummary.FromTestsuiteSummary()`` raised :exc:`AttributeError` for every summary with a test suite.
     * The Any-JUnit, Ant + JUnit4 and pyTest readers rejected a schema-valid ``<testcase>`` without ``time``.
     * ``Testsuite.Aggregate()`` never counted the test cases, so an aggregated document wrote ``tests="0"`` on its
       root element.
     * ``Document.Write()`` and the dialects' ``Write()`` truncated the file before serializing - a serialization
       error left an existing report empty. The document is serialized before the file is opened now.

   * :mod:`pyEDAA.Reports.Unittesting`:

     * The ``keyValuePairs`` constructor parameter unpacked a mapping's keys (``{"ab": 1}`` became ``{'a': 'b'}``).
     * ``TestsuiteBase`` ignored its ``status`` parameter, so a converted or merged test suite had status
       ``Unknown``.
     * ``Aggregate(strict=False)`` wasn't passed below the first level, and
       ``TestsuiteSummary.Aggregate()`` returned 12 of its 15 annotated values.
     * ``str(Testcase)`` always raised :exc:`TypeError`; a total duration below setup + teardown gave a negative test
       duration (now :exc:`ValueError`).
     * ``Testcase.Copy()`` passed the counters positionally from the warning count on, so every counter landed in
       the wrong field.

   * :mod:`pyEDAA.Reports.DocumentationCoverage`: a package's documentation coverage figures were wrong - everything
     below the second package level, nested classes and a package's own classes were missing, and excluded and
     ignored items were counted as expected. The new model counts every item once, into each level above it.
   * :program:`pyedaa-reports` ``unittest``: an unreadable or missing input file crashed with a :exc:`TypeError`, a
     fatal error ended with exit code 0, an absolute file pattern raised :exc:`NotImplementedError`, and a failed
     write was announced as written. They end with a message and a non-zero exit code now.

   .. rubric:: Documentation

   * The documentation is rendered with the extension pyTooling.Sphinx instead of sphinx_reports. The
     :ref:`dependency tables <DEP>` are generated from the requirements files. New page :ref:`ABBREVIATIONS`.
   * :ref:`CODECOV` describes the two layers, both hierarchies of the common model, the states and the counters, and
     per format its model and its conversion. :ref:`CODECOV/Formats` is a table of the formats 19 coverage tools
     write. A new page explains why pyEDAA.Reports reads UCIS XML itself.
   * New section :ref:`SCHEMAS`: an overview and 26 schema pages, each with a download link, a validation command and
     the source.
   * New toctree *Data Models* with the pages :ref:`REQ` and :ref:`RISK`.
   * :ref:`DOCCOV` describes the language-neutral data model and the Python reader.
   * The JUnit data model has sections on the cargo-nextest, go-junit-report and JunitXml.TestLogger dialects. New
     page on the Open Test Reporting data model.
   * The :ref:`CLI reference <CLI>` renders the commands and options of :program:`pyedaa-reports`.
   * An optional parameter's doc-string description opens with *Optional,*.
   * The section labels of the dependency page follow the ``DEP/`` hierarchy.

   .. rubric:: Unit Tests

   * Example projects in seven languages - Java, C++, Python, Rust, Go, C# and VHDL - run in the pipeline; their
     reports are test fixtures.
   * The unit and application tests run with pytest-xdist workers.

.. topic:: :gh:`v0.20.0-rc1 - 17.10.2026 <edaa-org/pyEDAA.Reports/releases/v0.20.0-rc1>`

   Release candidate published on PyPI; its changes are listed in v0.20.0.


Version 0.17.3 - 0.19.1 (2026)
******************************

.. topic:: :gh:`v0.19.1 - 12.10.2026 <edaa-org/pyEDAA.Reports/releases/v0.19.1>`

   A maintenance release of v0.19.0, keeping pyEDAA.Reports 0.19 installable once pyTooling 10.0.0 is on PyPI.

   .. rubric:: Breaking Changes

   * ⚠️ pyTooling is capped at ``< 10.0``, in the requirements and the build requirements.

.. topic:: :gh:`v0.19.0 - 21.08.2026 <edaa-org/pyEDAA.Reports/releases/v0.19.0>`

   .. rubric:: New Features

   * :mod:`pyEDAA.Reports.Unittesting`: :class:`~pyEDAA.Reports.Unittesting.Testsuite` records the host a test suite
     was executed on - a new optional ``hostname`` parameter and the read-only property
     :attr:`~pyEDAA.Reports.Unittesting.Testsuite.Hostname`. Merging keeps the common value while every input agrees
     on it, and ``"various"`` once two inputs disagree.

   .. rubric:: Breaking Changes

   * ⚠️ ``Testsuite.__init__`` takes ``hostname`` as its third parameter, before ``startTime``.
   * ⚠️ pyTooling ``>= 9.0, < 11.0`` is required.

   .. rubric:: Bug Fixes

   * A merged report could not be read back with the dialect it was written in, as the ``hostname`` was lost.
     ``Ant-JUnit4`` and ``CTest-JUnit`` dropped the ``hostname`` of their root element, and ``CTestJUnit`` wrote
     ``hostname="None"``.
   * A writer refuses a report its format can't express; merging keeps the earliest start time of its inputs.
   * ``Testsuite.Copy()`` raised a :exc:`TypeError` for any test suite carrying a status, and
     ``MergedTestsuite.__init__()`` lost its ``parent``.

   .. rubric:: Unit Tests

   * :file:`tests/app` is a new test level: the dialect conversion matrix driven through the installed command line.

.. topic:: :gh:`v0.18.0 - 31.07.2026 <edaa-org/pyEDAA.Reports/releases/v0.18.0>`

   .. rubric:: New Features

   * :program:`pyedaa-reports` ``version`` prints the full version information: authors, email, project URL,
     documentation URL, issue-tracker URL and whether a newer release is available.

   .. rubric:: Changes

   * ``pyEDAA.Reports.CLI.ProgramBase`` is removed; :class:`~pyEDAA.Reports.CLI.Application` derives from
     ``TerminalApplication`` directly.
   * Requires pyTooling 8.18 or later.

   .. rubric:: Bug Fixes

   * :program:`pyedaa-reports` failed to start with pyTooling 8.18 or later (``DuplicateFieldInSlotsError``).
   * ``DocStrCoverage`` raised a :exc:`NameError` when its annotations were evaluated on Python 3.14.

   .. rubric:: Documentation

   * All 110 properties carry a doc-string with a ``:returns:`` field.

.. topic:: :gh:`v0.17.4 - 05.07.2026 <edaa-org/pyEDAA.Reports/releases/v0.17.4>`

   .. rubric:: Changes

   * Bumped dependencies and added dunder variables.

   .. rubric:: Documentation

   * Sphinx configuration for LuaLaTeX and Unicode font support; fixed shields URLs.

.. topic:: :gh:`v0.17.3 - 24.02.2026 <edaa-org/pyEDAA.Reports/releases/v0.17.3>`

   .. rubric:: Changes

   * Bumped dependencies; ``pyproject.toml`` settings updated for pytest 9.0.

   .. rubric:: Bug Fixes

   * Fixed the dependency to ``pyTooling[terminal]`` and added missing type hints.
   * Required versions are written as ``0.X.0``, so the ``~=`` operator works correctly.


Version 0.15.0 - 0.17.2 (2025)
******************************

.. topic:: :gh:`v0.17.2 - 29.10.2025 <edaa-org/pyEDAA.Reports/releases/v0.17.2>`

   Maintenance release: pipeline changes only.

.. topic:: :gh:`v0.17.1 - 27.10.2025 <edaa-org/pyEDAA.Reports/releases/v0.17.1>`

   .. rubric:: New Features

   * Support for Python 3.14; Python 3.9 and 3.10 are no longer supported.

   .. rubric:: Changes

   * Improved exception printing for ``XMLSyntaxError``.

   .. rubric:: Bug Fixes

   * The CLI argument ``--output`` is optional.
   * Removed ``assert`` statements.

.. topic:: :gh:`v0.17.0 - 09.06.2025 <edaa-org/pyEDAA.Reports/releases/v0.17.0>`

   .. rubric:: New Features

   * A counter for weak tests.
   * Expected counts for warnings, errors and fatal errors: the read-only properties ``ExpectedWarningCount``,
     ``ExpectedErrorCount`` and ``ExpectedFatalCount``.

   .. rubric:: Bug Fixes

   * Removed the ``Aggregate`` overrides of the base-class implementation in ``AntJUnit4``, ``CTestJUnit``,
     ``GoogleTestJUnit`` and ``PyTestJUnit``.

.. topic:: :gh:`v0.16.0 - 04.05.2025 <edaa-org/pyEDAA.Reports/releases/v0.16.0>`

   .. rubric:: Changes

   * The OSVVM report handling (YAML files) moved to `pyEDAA.OSVVM <https://github.com/edaa-org/pyEDAA.OSVVM>`__.

   .. rubric:: Bug Fixes

   * Fixed the exception handling when an exception reaches the top-most exception handler.

.. topic:: :gh:`v0.15.0 - 13.03.2025 <edaa-org/pyEDAA.Reports/releases/v0.15.0>`

   No release notes were published. The tag's commits modify the ``TestcaseStatus`` resolution function and bump
   dependencies.


Version 0.1.0 - 0.14.2 (2024)
*****************************

.. topic:: :gh:`v0.14.2 - 09.11.2024 <edaa-org/pyEDAA.Reports/releases/v0.14.2>`

   Maintenance release: bumped dependencies.

.. topic:: :gh:`v0.14.1 - 03.11.2024 <edaa-org/pyEDAA.Reports/releases/v0.14.1>`

   .. rubric:: Changes

   * Uses ``@InheritDocString`` from pyTooling; bumped dependencies.

   .. rubric:: Unit Tests

   * Application tests for outputs generated by jobs running on GitHub Actions.

.. topic:: :gh:`v0.14.0 - 13.10.2024 <edaa-org/pyEDAA.Reports/releases/v0.14.0>`

   .. rubric:: New Features

   * :program:`pyedaa-reports` writes other dialects than Ant + JUnit4: CTest, GoogleTest and pyTest.

   .. rubric:: Changes

   * Reduced duplicate code introduced by the JUnit dialects.

.. topic:: :gh:`v0.13.1 - 13.10.2024 <edaa-org/pyEDAA.Reports/releases/v0.13.1>`

   .. rubric:: Bug Fixes

   * The XSD files are packaged in the wheel again.

.. topic:: :gh:`v0.13.0 - 12.10.2024 <edaa-org/pyEDAA.Reports/releases/v0.13.0>`

   .. rubric:: New Features

   * A ``keyValuePairs`` parameter on the initializers of the unified test entity classes.

   .. rubric:: Changes

   * Renamed ``pyEDAA.Reports.Unittesting.JUnit.AntJUnit`` to ``AntJUnit4``, ``Document.Read()`` to ``Analyze()``,
     ``Document.Parse()`` to ``Convert()`` and the parameter ``parse`` to ``analyzeAndConvert``.
   * More checks on the input parameters of the data models; some ``ValueError``\ s became
     ``AlreadyInHierarchyException``.

   .. rubric:: Bug Fixes

   * Raise errors on empty names; more checks of the parent reference; catch exceptions of ``path.open()``.
   * Each dialect generated the pyTest dialect when written.

   .. rubric:: Documentation

   * Restructured documentation; the unified test entity data model, the JUnit data model, its dialects and the
     dialect conversions are documented.

.. topic:: :gh:`v0.12.1 - 28.09.2024 <edaa-org/pyEDAA.Reports/releases/v0.12.1>`

   .. rubric:: New Features

   * :program:`pyedaa-reports` ``unittest``: the option ``--input`` reads a JUnit XML file; ``--merge`` reads the
     new dialect ``Any-JUnit``, a generic XML dialect with a relaxed XML schema; ``--pytest`` has the new rewrite
     option ``split``.
   * First CLI documentation.

   .. rubric:: Bug Fixes

   * Fixed type hints for tuples.

.. topic:: :gh:`v0.11.0 - 23.06.2024 <edaa-org/pyEDAA.Reports/releases/v0.11.0>`

   .. rubric:: New Features

   * pyTest JUnit: multiple ``system-out`` and ``system-err`` tags.
   * Generic JUnit: properties on the root element ``testsuites``.

   .. rubric:: Changes

   * A validation fault names the XSD schema used.

.. topic:: :gh:`v0.10.0 - 03.06.2024 <edaa-org/pyEDAA.Reports/releases/v0.10.0>`

   .. rubric:: New Features

   * Post-processing for pytest rewrites ``__init__`` in class names.
   * Safer parsing of YAML contents and improved error messages.

   .. rubric:: Bug Fixes

   * Fixed ``assertionCount`` vs. ``passedAssertionCount``.

.. topic:: :gh:`v0.9.0 - 02.06.2024 <edaa-org/pyEDAA.Reports/releases/v0.9.0>`

   .. rubric:: New Features

   * Reworked command line interface with the main command ``unittest`` and the arguments ``--name``, ``--merge``,
     ``--pytest``, ``--render`` and ``--output``.
   * JUnit dialects ``ant-junit``, ``ctest-junit``, ``gtest-junit`` and ``pytest-junit``, with example files
     produced by example projects in the pipeline.
   * Post-processing for pytest; rendering of test suites and test cases as a tree.
   * Reading OSVVM's AlertLogs from YAML files.

   .. rubric:: Changes

   * The JUnit schema files and classes are split into dialects.

   .. rubric:: Bug Fixes

   * A parameter that is ``None`` raises a :exc:`ValueError`, not a :exc:`TypeError`.
   * The encoding is specified when reading or writing files.

.. topic:: :gh:`v0.8.0 - 06.05.2024 <edaa-org/pyEDAA.Reports/releases/v0.8.0>`

   .. rubric:: New Features

   * The property ``TestDuration`` on test suites and test suite summaries; setup, test and teardown durations are
     checked, total durations aggregated.

.. topic:: :gh:`v0.7.2 - 06.05.2024 <edaa-org/pyEDAA.Reports/releases/v0.7.2>`

   .. rubric:: Bug Fixes

   * Avoid deleting already deleted items.

.. topic:: :gh:`v0.7.1 - 05.05.2024 <edaa-org/pyEDAA.Reports/releases/v0.7.1>`

   .. rubric:: New Features

   * Multiple pytest cleanup rules at once, with verbose and debug messages.

.. topic:: :gh:`v0.7.0 - 05.05.2024 <edaa-org/pyEDAA.Reports/releases/v0.7.0>`

   .. rubric:: New Features

   * Strip the overhead pytest creates from unit test reports: the new CLI parameter ``--pytest``.

   .. rubric:: Changes

   * Converting a ``Testclass`` creates one ``Testsuite`` per package, module and class level.
   * Renamed ``TestClass`` to ``Testclass``.

   .. rubric:: Bug Fixes

   * Moved the read-only property ``Kind`` to ``TestsuiteBase``.

.. topic:: :gh:`v0.6.0 - 05.05.2024 <edaa-org/pyEDAA.Reports/releases/v0.6.0>`

   .. rubric:: New Features

   * A data model for Ant JUnit summary files, with conversions to and from the generic unit testing data model.
   * A ``TestClass`` layer in the JUnit data model and a ``Kind`` field on test suites.

   .. rubric:: Changes

   * Nested test suites are removed from the JUnit data model.

.. topic:: :gh:`v0.5.2 - 25.04.2024 <edaa-org/pyEDAA.Reports/releases/v0.5.2>`

   .. rubric:: Bug Fixes

   * A JUnit XML document derived from a test suite summary copies the summary's fields.

.. topic:: :gh:`v0.5.1 - 25.04.2024 <edaa-org/pyEDAA.Reports/releases/v0.5.1>`

   .. rubric:: Changes

   * Test suites emit aggregated statistics.

.. topic:: :gh:`v0.5.0 - 24.04.2024 <edaa-org/pyEDAA.Reports/releases/v0.5.0>`

   .. rubric:: New Features

   * The command line tool :program:`pyedaa-reports`, merging JUnit test files.
   * A basic abstraction for Python requirements.

   .. rubric:: Bug Fixes

   * Added the missing field ``_tests``.

.. topic:: :gh:`v0.4.1 - 17.03.2024 <edaa-org/pyEDAA.Reports/releases/v0.4.1>`

   .. rubric:: Bug Fixes

   * The wheel contains :file:`Unittesting.xsd` and :file:`py.typed`.

.. topic:: :gh:`v0.4.0 - 16.03.2024 <edaa-org/pyEDAA.Reports/releases/v0.4.0>`

   .. rubric:: New Features

   * An XML schema to validate JUnit-like XML files, as a local resource.
   * Merging test suite summaries, test suites and test cases into ``MergedTestsuiteSummary``, ``MergedTestsuite``
     and ``MergedTestcase``; copying them.

   .. rubric:: Changes

   * Python 3.8 is no longer supported.
   * XML is parsed with ``lxml.etree`` instead of ``xml.dom.minidom``.

.. topic:: :gh:`v0.3.1 - 25.02.2024 <edaa-org/pyEDAA.Reports/releases/v0.3.1>`

   Same functional content as v0.3.0, released for a missing version increment.

.. topic:: :gh:`v0.3.0 - 25.02.2024 <edaa-org/pyEDAA.Reports/releases/v0.3.0>`

   .. rubric:: New Features

   * Documents are read, parsed, generated and written in two steps each.
   * Iterators over test suites and test cases, timing and counter properties, and key-value pairs on all classes.
   * Merging unit test summaries: ``MergedTestcase``, ``MergedTestsuite`` and ``MergedTestsuiteSummary``.

   .. rubric:: Changes

   * The generic unit test data model and the JUnit data model are unified into a single data model.
   * Renamed ``TestcaseState`` to ``TestcaseStatus`` (``State`` |rarr| ``Status``).

.. topic:: :gh:`v0.2.0 - 22.02.2024 <edaa-org/pyEDAA.Reports/releases/v0.2.0>`

   .. rubric:: New Features

   * A rudimentary data model for documentation coverage, and a Python documentation coverage model.

.. topic:: :gh:`v0.1.0 - 22.02.2024 <edaa-org/pyEDAA.Reports/releases/v0.1.0>`

   .. rubric:: New Features

   * An exception hierarchy.
   * A generic data model for unit test results, a reader of JUnit test summary files and of OSVVM's test report
     summary files (YAML).

   .. rubric:: Documentation

   * Reworked installation instructions; a glossary and a ToDo list.
