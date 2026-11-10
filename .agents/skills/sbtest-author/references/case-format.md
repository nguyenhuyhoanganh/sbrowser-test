# Case docs and test files

## Files and names

```
tests/features/<feature>/<feature>.md      all cases of the feature, in ID order; first line "# <Feature> cases"
tests/features/<feature>/test_<id>.py      the test of one case: one test function
tests/features/_inbox/<source title>.md    raw copy of an imported source (no tool reads it)
```

- `<feature>`: `addons`, `bookmarks`, `downloads`, `history`, `general` (pages, tabs,
  navigation, context menus). A new product part (e.g. `settings`) -> a new folder, its name
  in `FEATURES` of `sbtest/pytest_plugin.py` and a row in `FEATURES` of
  `sbtest/tools/case_overview.py`.
- `<id>`: the case ID in lower case with `-` replaced by `_`: `BM-001` -> `test_bm_001.py`,
  `SI-ADD-012` -> `test_si_add_012.py`.
- All cases of a feature go into `<feature>.md`, whether sanity or not, web or native.

An ID is groups of upper-case letters and digits joined by `-`, ending in a number (`BM-001`,
`SI-ADD-012`), and unique across all features.

## Format of a case

```markdown
## <ID> <Title: what the case verifies>
- Source: <link> (section / row)
- Priority: High
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
- `Source`: for an imported case - its link (section / row), or "pasted by the user".
- `Priority`: only when the user or the source gives one.
- `Type`: as SKILL.md, "web or native", defines it.
- `Precondition`: the start state as data ("Bookmarks bar contains X", "a finished download of
  sample.txt"); the test prepares it before the steps.
- `Steps`: numbered, one action each, in the author's wording.
- `Expected`: one bullet per outcome that can be observed.
- `Automated`: added when the test passes: `<test file>::<test name>`; not automatable ->
  `- Automated: no (<reason>)`.
