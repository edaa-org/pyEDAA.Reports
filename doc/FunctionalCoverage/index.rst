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
     - :class:`Covergroup`             | e.g. ``DelayCov`` - weight, goal, testcases
       - :class:`Coverpoint`           | e.g. ``BurstLength`` - sampled expression, weight, goal
         - :class:`CoverpointBin`      | e.g. ``short`` - :class:`BinKind`, ranges of values, count, at least
       - :class:`Cross`                | e.g. ``LengthXDelay`` - the crossed items, weight, goal
         - :class:`CrossBin`           | :class:`BinKind`, ranges of values per crossed item, count, at least

* A :class:`Covergroup` holds its coverage items - :class:`Coverpoint` and :class:`Cross` objects - by name, both in
  one namespace. The names of covergroups needn't be unique: several instances of a covergroup may share a name, and
  so may OSVVM coverage models.
* A :class:`Coverpoint` counts the values of one sampled expression. Each :class:`CoverpointBin` counts the values of
  its :class:`ValueRange` objects - a range from a lowest to a highest value, both included; a single value is a range
  from and to the value.
* A :class:`Cross` counts combinations of values, one value per crossed item. It names the crossed items: the
  covergroup may contain them as coverpoints, as a SystemVerilog cross crosses coverpoints, or not, as an OSVVM
  coverage model has no coverpoints of its own. Each :class:`CrossBin` has one set of ranges per crossed item; a bin
  with another number of sets raises a :exc:`FunctionalCoverageError`.
* A bin's :class:`BinKind` says how it counts:

  .. list-table::
     :header-rows: 1
     :widths: 15 85

     * - Kind
       - Meaning
     * - ``Count``
       - Counts toward the coverage; covered, when its count reaches its *at least* count.
     * - ``Ignore``
       - Excluded from the coverage: its values aren't of interest.
     * - ``Illegal``
       - Excluded from the coverage: its values must not occur, a hit is an error.
     * - ``Default``
       - Excluded from the coverage: counts the values no other bin of the coverage item counts.

* A bin's *at least* count says how often it must be hit to be covered; ``0`` covers it without a hit.
* Covergroups, coverpoints and crosses have a weight - their share in the coverage of the element containing them,
  ``0`` excludes them - and a goal in percent.
* Every element knows the element containing it - :attr:`~Base.Parent` - and the report's root - :attr:`~Base.Root`.
  Assigning a parent, in the constructor or later, adds the element to it and passes the root on to the elements it
  contains. An element already part of a report raises an :exc:`AlreadyInFunctionalCoverageReportError`; a second
  coverpoint or cross of a name raises a :exc:`DuplicateCoverpointError` or :exc:`DuplicateCrossError` - each a
  :exc:`~pyTooling.Exceptions.DuplicateElementError` and a :exc:`FunctionalCoverageError`.
* Every element has key-value pairs for data the model doesn't name, e.g. a tool's settings:
  ``covergroup["Seeds"] = [56101531, 1187811199]``.
* The report iterates its covergroups, a covergroup its coverpoints and crosses, a coverage item its bins, optionally
  filtered by a predicate, e.g. :meth:`Covergroup.IterateCoverpoints`.


.. _FUNCCOV/Coverage:

Coverage
********

:meth:`FunctionalCoverageReport.Aggregate` computes the counters of every coverage item, covergroup and of the report:
bins counting toward the coverage, covered and missing bins, ignored, illegal and default bins, hits of illegal bins,
and two ratios, as the tools compute coverage in two ways:

* :attr:`~BaseWithCoverage.BinCoverage` - as SystemVerilog and UCIS compute it -: of a coverage item, its covered bins
  divided by its bins counting toward the coverage; of a covergroup, the mean of its coverage items' bin coverage,
  weighted by their weights; of the report, the same over the covergroups.
* :attr:`~BaseWithCoverage.HitCoverage` - as OSVVM computes it -: the hits counted toward the *at least* counts, divided
  by the sum of the *at least* counts. A bin's hits count up to its *at least* count, so extra hits of one bin don't
  make up for missing hits of another. A covergroup weights the hit counts of its coverage items by their weights, the
  report those of its covergroups.

Both ratios are ``1.0``, where there is nothing to cover, e.g. when every covergroup has weight ``0``.

.. code-block:: Python

   from pyEDAA.Reports.FunctionalCoverage import BinKind, Covergroup, Coverpoint, CoverpointBin, Cross, CrossBin, \
                                                 FunctionalCoverageReport, ValueRange

   report =     FunctionalCoverageReport("TbStream_SendGetRandom1")
   covergroup = Covergroup("DelayCov", testcases=["TbStream_SendGetRandom1"], parent=report)
   length =     Coverpoint("BurstLength", parent=covergroup)
   CoverpointBin("short", BinKind.Count,   [ValueRange(3, 11)],   19, 80, parent=length)
   CoverpointBin("long",  BinKind.Count,   [ValueRange(109, 131)], 3, 20, parent=length)
   CoverpointBin("zero",  BinKind.Illegal, [ValueRange(0, 0)],     0,  0, parent=length)

   delay = Cross("LengthXDelay", ["BurstLength", "BurstDelay"], parent=covergroup)
   CrossBin(None, BinKind.Count, [[ValueRange(3, 11)], [ValueRange(0, 0)]], 13, 10, parent=delay)
   CrossBin(None, BinKind.Count, [[ValueRange(3, 11)], [ValueRange(1, 7)]],  6, 10, parent=delay)

   report.Aggregate()
   for coverpoint in covergroup.IterateCoverpoints():
     bins = f"{coverpoint.CoveredBinCount}/{coverpoint.BinCount} bins"
     print(f"{coverpoint.Name}: {bins}, hits {coverpoint.HitCoverage:.1%}")
     for coverageBin in coverpoint.IterateBins(lambda coverageBin: coverageBin.Kind is BinKind.Count):
       print(f"  {coverageBin.Name}: {coverageBin.Count}/{coverageBin.AtLeast}")

   print(f"{covergroup.Name}: bins {covergroup.BinCoverage:.1%}, hits {covergroup.HitCoverage:.1%}")


.. _FUNCCOV/Formats:

Report Formats
**************

A reader of a functional coverage format derives its document from :class:`Document`: it analyzes the file
(:meth:`~Document.Analyze`), converts it to the format's model (:meth:`~Document.Convert`), then to this model
(:meth:`~Document.ConvertToFunctionalCoverageReport`), which it aggregates. The document states how long the analysis
and the conversion took.


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
   * - cross
     - :class:`Cross`
     - ``cross``
     - scope ``UCIS_CROSS``; XML ``<cross>``
     - model of 2 and more dimensions; field names = crossed items
   * - bin
     - :class:`CoverpointBin`, :class:`CrossBin`
     - bin of ``bins``, ``ignore_bins``, ``illegal_bins``
     - cover item ``UCIS_CVGBIN``; XML ``<coverpointBin>``, ``<crossBin>``
     - an item of ``Bins`` (``CovBinBaseType``)
   * - bin kind ``Count``
     - :attr:`BinKind.Count`
     - ``bins``
     - ``UCIS_CVGBIN``
     - ``COUNT`` (``COV_COUNT``)
   * - bin kind ``Ignore``
     - :attr:`BinKind.Ignore`
     - ``ignore_bins``
     - ``UCIS_IGNOREBIN``
     - ``IGNORE`` (``COV_IGNORE``)
   * - bin kind ``Illegal``
     - :attr:`BinKind.Illegal`
     - ``illegal_bins``
     - ``UCIS_ILLEGALBIN``
     - ``ILLEGAL`` (``COV_ILLEGAL``)
   * - bin kind ``Default``
     - :attr:`BinKind.Default`
     - ``bins ... = default``
     - ``UCIS_DEFAULTBIN``
     - (none)
   * - value range
     - :class:`ValueRange`
     - value, ``[low:high]``
     - XML ``<range from to>``
     - ``Range: {Min, Max}``, one per dimension
   * - count
     - :attr:`Bin.Count`
     - hit count
     - cover item count; XML ``<contents coverageCount>``
     - ``Count``
   * - at least
     - :attr:`Bin.AtLeast`
     - ``option.at_least`` of the coverpoint or covergroup
     - goal of a cover item; XML ``<options at_least>``
     - ``AtLeast``, per bin
   * - weight
     - :attr:`~BaseWithGoal.Weight`
     - ``option.weight``
     - weight; XML ``<options weight>``
     - ``CovWeight``, per model
   * - goal
     - :attr:`~BaseWithGoal.Goal`
     - ``option.goal``
     - goal; XML ``<options goal>``
     - ``Goal`` (``CovTarget``), per model
   * - bin coverage
     - :attr:`~BaseWithCoverage.BinCoverage`
     - ``get_coverage()``, ``get_inst_coverage()``
     - coverage computed by the tool
     - (none)
   * - hit coverage
     - :attr:`~BaseWithCoverage.HitCoverage`
     - (none)
     - (none)
     - ``Coverage`` of a model (``GetCov``); ``TotalCovCount`` / ``TotalCovGoal``; ``Coverage`` of the document
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
   * OSVVM's ``Goal`` scales the *at least* counts: with a goal of 50 %, a bin is covered with half its hits, and the
     model's coverage is relative to the scaled counts. The model keeps the goal as :attr:`~BaseWithGoal.Goal`; its
     ratios are relative to the *at least* counts as stated. Both agree for the default goal of 100 %.
   * Not modeled yet: SystemVerilog's transition bins (``bins t = (1 => 2 => 3)``) and wildcard bins, and OSVVM's bin
     weights for intelligent coverage, which OSVVM's YAML file doesn't write.
