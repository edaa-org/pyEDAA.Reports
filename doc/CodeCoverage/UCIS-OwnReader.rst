.. _CODECOV/Formats/UCIS/WhyOwnReader:

Why pyEDAA.Reports reads UCIS XML itself
########################################

`pyucis <https://github.com/fvutils/pyucis>`__ is a Python implementation of the data model and API of the Accellera
Unified Coverage Interoperability Standard (UCIS). It reads and writes UCIS XML, too. So why does pyEDAA.Reports bring
its own reader - :class:`pyEDAA.Reports.CodeCoverage.UCIS.Document` - instead of building on pyucis?

The short answer: both read UCIS XML, but they serve different layers. pyucis is a coverage *database*. pyEDAA.Reports
needs a *format reader*, which models a report file as the standard specifies it and converts it into the common
code coverage model of pyEDAA.Reports.


.. _CODECOV/Formats/UCIS/WhyOwnReader/Comparison:

What each library is
********************

.. list-table::
   :header-rows: 1
   :widths: 22 39 39

   * - Aspect
     - pyEDAA.Reports UCIS reader
     - pyucis
   * - Purpose
     - Read a UCIS XML report and convert it into the common model of pyEDAA.Reports.
     - Create, manipulate, merge, convert and report UCIS coverage databases.
   * - Model
     - A format model mirroring the XML interchange format element by element: each element has a typed constructor,
       a ``Parse()`` classmethod and a parent.
     - The UCIS data model as an API in the style of the UCIS C API: scopes, cover items, handles, type flags,
       property getters.
   * - Direction
     - Read-only.
     - Read and write.
   * - Validation
     - Validates each report against the standard's schema - :ref:`UCIS-1.0.xsd <SCHEMAS/UCIS-1.0>` - or, for
       pyucis' output, against its namespace-less twin :ref:`PyUCIS-1.0.xsd <SCHEMAS/PyUCIS-1.0>`.
     - Validates UCIS XML against its own schema ``ucis.xsd``, which has no target namespace: a report in the
       standard's namespace ``UCIS`` fails the validation and isn't read.
   * - Input formats
     - UCIS XML (namespace ``UCIS``) and pyucis' dialect of it (no namespace).
     - UCIS XML without namespace, UCIS YAML, SQLite, NCDB, cocotb-coverage XML/YAML, AVL JSON, Verilator ``.dat``,
       and a tool's UCIS C library (loaded via :mod:`ctypes`).
   * - Output formats
     - The common code coverage model of pyEDAA.Reports (:class:`~pyEDAA.Reports.CodeCoverage.CoverageSummary`).
     - Its input formats, plus LCOV, Cobertura, JaCoCo and Clover; reports as text, JSON or HTML.
   * - Coverage kinds
     - Statement, block and branch coverage are converted; toggle, condition, expression, FSM, assertion and
       covergroup coverage are read into the format's model (:ref:`CODECOV/Formats/UCIS`), but not converted yet.
     - All UCIS coverage kinds in its model; which ones a format carries depends on the backend.
   * - Runtime dependencies
     - None beyond pyEDAA.Reports' own.
     - ``lxml``, ``jsonschema``, ``python-jsonschema-objects``, ``pyyaml``, ``rich``, ``mcp`` (MCP server for AI
       agents).


.. _CODECOV/Formats/UCIS/WhyOwnReader/Schema:

Where the schema comes from
***************************

A reader, which follows the standard, needs the standard's schema as a file. Accellera doesn't publish one:

* The `UCIS download page <https://www.accellera.org/downloads/standards/ucis>`__ offers a single item: the standard
  itself, *Unified Coverage Interoperability Standard Version 1.0* (June 2012), as PDF. The schema is printed in
  section 9.14 of that document.
* Accellera's `XML schema directory <https://www.accellera.org/XMLSchema/>`__ holds the schemas of IP-XACT and SPIRIT
  only - no UCIS.
* The only machine-readable copy in an Accellera project is ``ucis/UCIS.xsd`` of
  `accellera-official/fc4sc <https://github.com/accellera-official/fc4sc>`__, licensed under the Apache License 2.0.
  NVIDIA changed it in 2020 in four places, so it no longer matches the standard.

pyEDAA.Reports therefore ships its own schema - :ref:`UCIS-1.0.xsd <SCHEMAS/UCIS-1.0>` -: FC4SC's file with NVIDIA's
four changes reverted, structurally identical to section 9.14 of the standard, with the original notices kept and the
changes stated in its header. Where the standard's examples contradict its schema, the schema decides.

.. hint::

   A canonical, openly licensed schema file - published by Accellera, like the IP-XACT schemas, which are licensed under
   the Apache License 2.0 since IEEE Std 1685-2022 - would let all UCIS readers and writers validate against the same
   file.


.. _CODECOV/Formats/UCIS/WhyOwnReader/ProsCons:

pyucis as the lower layer of the reader
***************************************

pyucis could replace the format model: the reader would open a report with pyucis, walk its scopes and cover items -
statement bins, branch bins, later toggle and covergroup bins -, map their source information (file, line, token) to
lines and their design units to :class:`~pyEDAA.Reports.CodeCoverage.Module`\ s.

.. grid:: 2

   .. grid-item-card:: Pros
      :columns: 12 12 6 6

      * **More inputs.** Every format pyucis reads would be readable by pyEDAA.Reports: SQLite, NCDB, Verilator's
        ``.dat``, cocotb-coverage, AVL.
      * **Simulator databases.** pyucis loads a tool's UCIS C library (``LibFactory.load_ucis_library()``,
        ``LibFactory.create()``), so a tool's native database - e.g. a Questa UCDB - becomes readable from Python.
        Questa documents no command writing UCIS XML; its UCIS support is the C library.
      * **Coverage kinds.** pyucis' data model covers all UCIS coverage kinds, including covergroups.
      * **Shared maintenance.** Fixes to UCIS parsing would be made once, in one project.

   .. grid-item-card:: Cons
      :columns: 12 12 6 6

      * **Dependencies.** pyucis requires ``mcp``, which pulls in a web stack (pydantic, httpx, starlette, ...), and
        ``rich``. A library, which reads report files, mustn't require them.
      * **Fidelity to the standard.** pyucis writes its XML without the ``UCIS`` namespace, and its own schema has no
        target namespace: a report written as the standard specifies fails pyucis' validation. pyEDAA.Reports reads
        pyucis' dialect separately (:ref:`CODECOV/Formats/UCIS/PyUCIS`). Files following the standard must be read by
        the standard's schema, not by what one implementation writes - and since no official schema file exists
        (:ref:`CODECOV/Formats/UCIS/WhyOwnReader/Schema`), the reader has to bring a verified one itself.
      * **Abstraction.** pyucis presents the C API's view: handles, type flags, property queries. Details of the file -
        the structure of statement IDs, metric modes, user-defined attributes per element - are flattened or only
        reachable by property queries. pyEDAA.Reports' format models keep them as typed attributes, like for every
        other format.
      * **Consistency.** All format readers of pyEDAA.Reports follow one pattern: a format model, validated against a
        schema shipped as a resource, and a conversion into the common model. A UCIS reader on top of pyucis would be
        the exception.
      * **API stability.** pyucis is classified *Beta* and grows quickly (NCDB, test history, test plans, a TUI, an MCP
        server). Its API may change under a downstream reader.


.. _CODECOV/Formats/UCIS/WhyOwnReader/Decision:

Decision
********

pyEDAA.Reports reads UCIS XML with its own format reader:

* It reads the format as the standard's schema specifies it - validated against a schema file restored to the
  standard's text, as Accellera publishes none -, without runtime dependencies.
* It keeps the format's details in a typed model, like every other format reader of pyEDAA.Reports.
* It converts statement and branch coverage - later all coverage kinds - into the common code coverage model.

pyucis is not a competitor, but a complement: its value for pyEDAA.Reports is the access to *databases* - native
simulator databases via a tool's UCIS library, SQLite, NCDB - which aren't files in a documented format.


.. _CODECOV/Formats/UCIS/WhyOwnReader/Interop:

Using pyucis together with pyEDAA.Reports
*****************************************

.. _CODECOV/Formats/UCIS/WhyOwnReader/Interop/Database:

Converting a database to UCIS XML
=================================

:program:`pyucis` can write a database as UCIS XML, which pyEDAA.Reports reads with its pyucis dialect reader:

.. code-block:: bash

   pyucis convert --input-format sqlite --output-format xml coverage.cdb --out coverage.xml

.. code-block:: Python

   from pathlib import Path
   from pyEDAA.Reports.CodeCoverage.UCIS.PyUCIS import Document

   report = Document(Path("coverage.xml"), analyzeAndConvert=True)
   summary = report.ToCoverageSummary()

.. _CODECOV/Formats/UCIS/WhyOwnReader/Interop/Simulator:

Converting a simulator database
===============================

With a tool's UCIS C library, pyucis opens the tool's native database. The tool's library can also write the standard's
XML interchange format (``ucis_WriteToInterchangeFormat``), which pyEDAA.Reports reads with
:class:`~pyEDAA.Reports.CodeCoverage.UCIS.Document`.

.. code-block:: Python

   from ucis.lib.LibFactory import LibFactory

   LibFactory.load_ucis_library("/path/to/the/tools/libucis.so")
   db = LibFactory.create("coverage.ucdb")

.. note::

   Whether a tool ships a UCIS library, and under which name and license, depends on the tool and its version.

.. _CODECOV/Formats/UCIS/WhyOwnReader/Interop/Outlook:

Outlook: an adapter for the UCIS API
====================================

A future extension could convert any database, which implements pyucis' UCIS API, directly into the common model -
without writing XML in between. It would be an optional extra (e.g. ``pyEDAA.Reports[ucis]``), so pyucis and its
dependencies stay optional, and share the conversion rules of
:meth:`~pyEDAA.Reports.CodeCoverage.UCIS.Document.ToCoverageSummary` - e.g. *a line ran as often as its least often run
statement* -, so both paths produce the same summary for the same coverage.
