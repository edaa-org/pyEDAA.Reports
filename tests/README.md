# Testing pyEDAA.Reports

Run everything with:

```bash
python -m pytest tests/unit -q      # the unit tests
python -m pytest tests/app -q       # the installed command line entry points
```

Both are run from the repository root, so the checkout wins over an installed copy of the package.

## Two phases

1. **Instantiation** — construct one entity, first with the minimal set of required parameters, then with the
   optional ones. The assertions check the properties and the parent references. Deliberately per class and shallow.
2. **Combination** — compose many instances and test what only emerges from the combination: merging, aggregation,
   conversion between data models, and the dialect behaviour described below.

Overlap between the two is expected: phase 1 tests a class's own wiring, phase 2 tests what happens between
classes.

## Four structural levels

| Level      | Meaning                              | Here                                                           |
|------------|--------------------------------------|----------------------------------------------------------------|
| a) package | the capability under test            | `Unittesting/`, `DocumentationCoverage/`, `JUnitDialects/`     |
| b) module  | a feature group of that capability   | `DataModel.py`, `Merge.py`, `Hostname.py`, `RoundTrip.py`      |
| c) class   | one specific feature, or one dialect | `Merging`, `RoundTrip.PyTestJUnit`, `Translation.FromAnyJUnit` |
| d) method  | one *variant* of that feature        | `test_TwoHosts`, `test_ToCTestJUnit`                           |

A method is a variant, not a second assertion style: "merge two suites with different hostnames" is a variant,
"check the count as well" is not - that belongs in the same method or in another level.

Where a dialect or a data format is the thing under test, level (c) is one class per dialect, derived from a
**classic mixin** that holds the checks - `SchemaMixin`, `RoundTripMixin`, `TranslationMixin`. The checks are
written once and reported per dialect, and the mixin itself is not a `TestCase`, so it contributes no testcases of
its own.

The mixins are deliberately *not* created by `ExtendedType`: mixing it with `unittest.TestCase` raises
`BaseClassWithoutSlotsError`, because `TestCase` has no `__slots__`. A classic mixin is the right tool where the
foreign base class is out of our hands.

## The reference outputs are the ground truth

`tests/data/JUnit/**` holds reports produced by the frameworks themselves - Ant, CTest, GoogleTest, pytest, VUnit,
OSVVM. The XML schemas in `pyEDAA/Reports/Resources` were **reverse-engineered from those outputs**: JUnit has no
official schema, the format is whatever Ant emitted and everyone else imitated.

Two consequences the tests rely on:

* A schema that rejects a reference output describes the format wrongly - the file is not wrong, the schema is.
* A report *this package writes* that its own reader rejects is a defect, whatever the schema says. Writer and
  reader are the same claim about the format, written twice.

`JUnitDialects/Schemas.py` asserts the first, `JUnitDialects/RoundTrip.py` the second.

## Known gaps are asserted, not skipped

Some conversions cannot work yet. They are listed in `JUnitDialects/Translation.py::KNOWN_GAPS` with the reason,
and the test asserts that they **still fail**:

```python
("Any-JUnit", "pyTest-JUnit"):
    "The pyTest reader requires a timestamp, and the OSVVM report has none to carry over.",
```

A skip would go quiet forever; this way, fixing the gap turns the expectation red and the entry gets removed in the
same pull-request that fixes it. The same pattern documents that `Any-JUnit` does not accept a `<testsuite>`-rooted
report although it should.

## Layout

```
tests/
├── unit/
│   ├── Unittesting/          the unified data model: construction, merging, hostnames, JUnit reading
│   ├── DocumentationCoverage/
│   └── JUnitDialects/        behaviour between dialects
│       ├── __init__.py       the dialect table, and the read/write helpers the modules share
│       ├── Schemas.py        every reference output validates, and the reader agrees with the schema
│       ├── RoundTrip.py      read → write → validate → read back, per dialect
│       └── Translation.py    the 5×5 conversion matrix
├── app/                      the installed entry points, through subprocess
├── data/                     reference outputs (ground truth) - never edited to make a test pass
└── output/                   what the tests write; not committed
```

`tests/data` is evidence. If a test needs a report with particular content, it builds one in the test or writes it
to `tests/output` - it does not edit the reference outputs.
