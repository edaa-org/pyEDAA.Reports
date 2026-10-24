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
         - :class:`CoverpointBin`      | e.g. ``short`` - :class:`BinKind`, ranges of values, count, at least
       - :class:`Cross`                | e.g. ``LengthXDelay`` - the crossed items
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
* Every element knows the element containing it - :attr:`~Base.Parent` - and the report's root - :attr:`~Base.Root`.
  Assigning a parent, in the constructor or later, adds the element to it and passes the root on to the elements it
  contains. An element already part of a report raises an :exc:`AlreadyInFunctionalCoverageReportError`; a second
  coverpoint or cross of a name raises a :exc:`DuplicateCoverpointError` or :exc:`DuplicateCrossError` - each a
  :exc:`~pyTooling.Exceptions.DuplicateElementError` and a :exc:`FunctionalCoverageError`.
* Every element has key-value pairs for data the model doesn't name, e.g. a tool's settings:
  ``covergroup["Seeds"] = [56101531, 1187811199]``.
* The report iterates its covergroups, a covergroup its coverpoints and crosses, a coverage item its bins, optionally
  filtered by a predicate, e.g. :meth:`Covergroup.IterateCoverpoints`.


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
   * Not modeled yet: SystemVerilog's transition bins (``bins t = (1 => 2 => 3)``) and wildcard bins, and OSVVM's bin
     weights for intelligent coverage, which OSVVM's YAML file doesn't write.
