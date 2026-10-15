.. _DOCCOV:

Documentation Coverage
######################

Documentation coverage measures the presence of code documentation. It primarily counts for public language entities
like publicly visible constants and variables, parameters, types, functions, methods, classes, modules, packages, etc.
The documentation goal depends on the used coverage collection tool's settings. E.g. usually, private language entities
are not required to be documented.

The documentation coverage metric in percent is a ratio of documented language entity versus all documentation worthy
langauge entities. A coverage of <100% indicates undocumented code.


.. _DOCCOV/DataModel:

Data Model
**********

The documentation coverage model of :mod:`pyEDAA.Reports.DocumentationCoverage` is shared by all languages: a reader
of a language fills it. Like the :ref:`code coverage model <CODECOV/DataModel>`, it has two hierarchies over the same
items.

.. py:currentmodule:: pyEDAA.Reports.DocumentationCoverage

.. tree::

   - :class:`~Files.CoverageSummary`  | the analysis
     - physical hierarchy             | built from the source files analyzed
       - :class:`~Files.Directory`    | e.g. :file:`myPackage/Units/`
         - :class:`~Files.File`       | e.g. :file:`myPackage/Units/Length.py` - counts the items declared in it
     - logical hierarchy              | the documentable items - each: kind, state, file, first and last line
       - :class:`~Items.Item`         | e.g. package ``myPackage``
         - :class:`~Items.Item`       | e.g. module ``myPackage.Shapes``
           - :class:`~Items.Item`     | e.g. class ``myPackage.Shapes.Circle``
             - :class:`~Items.Item`   | e.g. field ``myPackage.Shapes.Circle._radius``

* An item's :class:`ItemKind` names the language construct, e.g. a class, a method or a VHDL entity. Languages share a
  kind where they share the construct. Each kind belongs to an :class:`ItemCategory` - container, type, callable,
  field, variable, parameter or other -, so the counters break down the same way for every language.
* An item's :class:`CoverageState` says how it is documented - documented, undocumented, or excused by a comment - and
  whether it is expected to be documented: an ignored or excluded item isn't; an item with nothing to document, e.g. an
  empty module, isn't counted at all.
* A container's own documentation, e.g. a module's or a class' doc-string, is the container's own state. So an item's
  counters count the item and every item below it.
* A file and a line range are optional: a reader that doesn't know them leaves them out. Such an item is counted by
  the analysis' root, but by no file.

:meth:`~Files.CoverageSummary.Aggregate` computes the :class:`CoverageCounters` - total, expected, covered, uncovered,
ignored and excluded items, and the coverage - of every item, file and directory, and per category in
:attr:`~Base.Categories`. The coverage is ``1.0`` where nothing is expected.


.. _DOCCOV/Python:

Python
******

:class:`~Python.Analyzer` reads a Python package from its source files - every :file:`*.py` file below the package's
directory, each read once in its declared encoding - into the model:

* Packages, modules, classes, functions, methods, constructors and properties are documented by a non-empty
  doc-string. A comment of docstr_coverage directly above a declaration - ``# docstr-coverage: inherited`` or
  ``# docstr-coverage: excused `reason``` - excuses a missing doc-string.
* Fields of a class and variables of a module are documented where Sphinx' autodoc finds their documentation: a ``#:``
  comment behind the statement, ``#:`` comment lines directly above it, or a string literal directly after it.
* A property's setter and deleter, an ``@overload`` stub, and fields or variables like ``__all__`` are ignored.

:class:`~Python.Options` switch the counting of fields and variables off, ignore private names, or exclude items by
regular expressions matching their qualified names. A source file, which can't be read or parsed, is reported as a
critical warning, :exc:`SourceFileWarning`, to the current :class:`~pyTooling.Warning.WarningCollector`; the analysis
continues.

.. code-block:: Python

   from pathlib import Path
   from pyTooling.Warning import WarningCollector
   from pyEDAA.Reports.DocumentationCoverage import ItemCategory
   from pyEDAA.Reports.DocumentationCoverage.Python import Analyzer, Options

   with WarningCollector() as warnings:
     summary = Analyzer("myPackage", Path("src/myPackage"), options=Options(skipPrivate=True)).Analyze()

   print(f"{summary.Counters.Coverage:.1%} of {summary.Counters.Expected} items")
   print(f"fields: {summary.Categories[ItemCategory.Field].Coverage:.1%}")

Without fields and variables, the counts equal those of
`docstr_coverage <https://github.com/HunterMcGushion/docstr_coverage>`__, except for ``@overload`` stubs, which
docstr_coverage expects to be documented. Its analysis can be converted to the model as well, by
:class:`~DocStrCoverage.DocStrCoverage`.
