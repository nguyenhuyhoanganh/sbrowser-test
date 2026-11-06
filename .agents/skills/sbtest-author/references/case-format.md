# Case docs: where they go and their format

## Contents

- Files and names
- IDs
- Format of a case
- Tools that read the case docs

## Files and names

One case doc per feature lists all its cases; every case has its own test file next to it:

```
tests/features/<feature>/<feature>.md      every case of the feature, in ID order
tests/features/<feature>/test_<id>.py      the test of one case (one test function)
```

- `<feature>`: the product part the case tests - `addons`, `bookmarks`, `downloads`,
  `history`, `general` (browsing: pages, tabs, navigation, context menus). A new product part
  (e.g. `settings`) -> new folder + `FEATURES` in `sbtest/pytest_plugin.py` + a row in
  `FEATURES` of `sbtest/tools/case_overview.py`.
- `<id>`: the case ID in lower case with `-` turned into `_` (`BM-001` -> `test_bm_001.py`,
  `SI-ADD-012` -> `test_si_add_012.py`).
- No other grouping: a "Sanity" section of the source, web or native, toolbar or page - all
  go into `<feature>.md`; a sanity case is only marked `@pytest.mark.sanity` in its test.

Example: BM-001 and BM-002 -> both in `bookmarks/bookmarks.md`, tests
`bookmarks/test_bm_001.py` and `bookmarks/test_bm_002.py`.

Raw copies of a source (Confluence page, export, pasted text) go to
`tests/features/_inbox/<source title>.md` first (workflow A); only the case docs above are read
by the tools and the report.

## IDs

IDs come from the team with each case (their own scheme): use them as they are, never invent,
renumber or change one. A case without an ID -> ask the user. An ID is upper-case letter/digit
groups joined by `-`, ending in a number (`BM-001`, `SI-ADD-012`), unique across all features.
The test carries the same ID: `@pytest.mark.case("<ID>")`.

## Format of a case

```markdown
## <ID> <Title: what the case verifies>
- Source: <link> (section / row)            (when it came from a document)
- Priority: High                            (only when the user or the source gives one)
- Type: web | native | mixed
- Precondition: Bookmarks bar contains "Static page 1" and "Static page 2"
- Steps:
  1. Open the bookmark manager
  2. Select "Static page 1" and click Delete
- Expected:
  - "Static page 1" is no longer listed
  - A snack bar "1 bookmark deleted" with Undo shows
- Automated: tests/features/bookmarks/test_bm_001.py::test_delete_bookmark
```

- Heading: `##`, the ID, one space, the title.
- `Type`: `web` = only page content (internal pages too); `native` = browser UI (toolbar,
  address bar, menus, bubbles, shortcuts) or Windows dialogs; `mixed` = both.
- `Precondition`: data as data ("Bookmarks bar contains X", "a finished download of
  data.csv") - the test seeds it, it does not click it together.
- `Steps`: numbered, one action each, in the author's wording.
- `Expected`: one bullet per observable outcome.
- `Automated`: added when the test is green (B5d of the skill): `<test file>::<test name>`.
  Not automatable -> `- Automated: no (<reason>)`.
- Fields are read by `sbtest/reporting/cases.py`: `Priority`, `Type`, `Precondition`,
  `Steps`, `Expected`, `Automated` (others such as `Source` are kept for people).

## Tools that read the case docs

```
python -m sbtest.tools.coverage [--feature <feature>] [--missing]   # automated / missing / orphaned IDs
python -m sbtest.tools.case_overview                                  # rewrites tests/features/TESTCASES.md
```

The run's report takes each case's title, steps and expected results from its case doc.
