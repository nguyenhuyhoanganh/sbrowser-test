# Case docs: where they go and their format

## Contents

- Files and names
- IDs
- Format of a case
- Tools that read the case docs

## Files and names

Every case lives in a Markdown case doc; its test lives next to it. One case doc <-> one test
file, with the same `<area>`:

```
tests/features/<feature>/<area>.md                  case doc (one or more cases)
tests/features/<feature>/test_<feature>_<area>.py   the tests of those cases
```

- `<feature>`: the product part the case tests - `addons`, `bookmarks`, `downloads`,
  `history`, `general` (browsing: pages, tabs, navigation, context menus). A new product part
  (e.g. `settings`) -> new folder + `FEATURES` in `sbtest/pytest_plugin.py` + a row in
  `FEATURES` of `sbtest/tools/case_overview.py`.
- `<area>`, in this order:
  1. the source splits its cases into named groups below the feature (sections or pages
     such as "Sanity", "Sync") -> that group's name in snake case (`sanity`);
  2. otherwise - also a source that is just the feature ("Bookmarks") or one case - from the
     case's Type: `web` -> `page`, `native` or `mixed` -> `toolbar`.
- A case doc with that name already exists -> add the case to it (and its test to the
  matching test file). Never a second doc for the same `<area>`.

Examples: a web case of the bookmark manager -> `bookmarks/page.md` +
`bookmarks/test_bookmarks_page.py`; Ctrl+D on a page -> `bookmarks/toolbar.md` +
`bookmarks/test_bookmarks_toolbar.py`; a source page "Downloads sanity" ->
`downloads/sanity.md` + `downloads/test_downloads_sanity.py`.

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
- Automated: tests/features/bookmarks/test_bookmarks_page.py::test_delete_bookmark
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
