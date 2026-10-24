.. _FUNCCOV:

Functional Coverage
###################

Functional coverage measures, which values - and which combinations of values - a testbench sampled, compared to
the values the verification plan asks for. Unlike code coverage, it isn't derived from the code: the verification
engineer declares what is of interest, e.g. every burst length of a bus transfer, or each operation crossed with each
operand size. A coverage of less than 100 % names the values, which were never or not often enough sampled, so
more or other stimuli are needed.


.. _FUNCCOV/DataModel:

Data Model
**********

The functional coverage model of :mod:`pyEDAA.Reports.FunctionalCoverage` is tool-neutral: it follows the terms of
SystemVerilog covergroups and of the Accellera UCIS standard, and an OSVVM coverage model maps to it too - see
:ref:`FUNCCOV/Terms`.

.. py:currentmodule:: pyEDAA.Reports.FunctionalCoverage

.. tree::

   - :class:`FunctionalCoverageReport` | the report, e.g. of a testcase - name, key-value pairs
     - :class:`Covergroup`             | e.g. ``DelayCov`` - testcases
       - :class:`Coverpoint`           | e.g. ``BurstLength`` - sampled expression

* A :class:`Covergroup` holds its coverage items - :class:`Coverpoint` objects - by name. The names of covergroups
  needn't be unique: several instances of a covergroup may share a name, and so may OSVVM coverage models.
* Every element knows the element containing it - :attr:`~Base.Parent` - and the report's root - :attr:`~Base.Root`.
  Assigning a parent, in the constructor or later, adds the element to it and passes the root on to the elements it
  contains. An element already part of a report raises an :exc:`AlreadyInFunctionalCoverageReportError`; a second
  coverpoint of a name raises a :exc:`DuplicateCoverpointError` - a :exc:`~pyTooling.Exceptions.DuplicateElementError`
  and a :exc:`FunctionalCoverageError`.
* Every element has key-value pairs for data the model doesn't name, e.g. a tool's settings:
  ``covergroup["Seeds"] = [56101531, 1187811199]``.
* The report iterates its covergroups, a covergroup its coverpoints, optionally filtered by a predicate, e.g.
  :meth:`Covergroup.IterateCoverpoints`.


.. _FUNCCOV/Terms:

Terms
*****

The model's terms and what the tools call them. SystemVerilog is IEEE Std 1800 (covergroups), UCIS the Accellera
Unified Coverage Interoperability Standard 1.0 (its API and XML interchange format), OSVVM the ``CoveragePkg`` of
OSVVM and its YAML report file (:file:`<testcase>_cov.yml`).

.. list-table::
   :header-rows: 1
   :widths: 19 21 20 20 20

   * - Concept
     - pyEDAA.Reports
     - SystemVerilog
     - UCIS
     - OSVVM
   * - report
     - :class:`FunctionalCoverageReport`
     - (simulation run)
     - database; XML ``<UCIS>``
     - YAML document: ``Version``, ``Coverage``, ``Settings``, ``Models``
   * - covergroup
     - :class:`Covergroup`
     - ``covergroup`` instance
     - scope ``UCIS_COVERGROUP``, ``UCIS_COVERINSTANCE``; XML ``<cgInstance>``
     - coverage model (``CoverageIDType``); an item of ``Models``
   * - coverage item
     - :class:`CoverageItem`
     - coverage item: coverpoint or cross
     - scope of a coverpoint or cross
     - (a coverage model is one coverage item)
   * - coverpoint
     - :class:`Coverpoint`
     - ``coverpoint``
     - scope ``UCIS_COVERPOINT``; XML ``<coverpoint>``
     - model of 1 dimension (``BinInfo.Dimensions``); expression: its field name (``FieldNames``)
   * - testcases
     - :attr:`Covergroup.Testcases`
     - (none)
     - history nodes (test records)
     - ``TestCases``
   * - settings
     - key-value pairs
     - further options, e.g. ``option.comment``, ``option.auto_bin_max``
     - further options and user attributes
     - ``Settings``: ``Seeds``, ``WeightMode``, ``CountMode``, ``IllegalMode``, ``Threshold``, ...

.. note::

   * UCIS calls a bin a *cover item*, SystemVerilog calls a coverpoint or a cross a *coverage item*. The model follows
     SystemVerilog.
