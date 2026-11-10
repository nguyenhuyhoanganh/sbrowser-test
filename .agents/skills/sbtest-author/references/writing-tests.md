# Writing a test

## Contents

- Test shape
- Fixtures
- Markers
- Preconditions
- Data files
- Local site
- Generated files and the sample add-on

## Test shape

A new test file starts as a copy of this example:

```python
"""BM-004 Delete a bookmark and undo. Case: bookmarks.md"""
import pytest

from sbtest.steps import step


@pytest.mark.case("BM-004")
@pytest.mark.browser(bookmarks="seed_basic")
def test_delete_and_undo(pages):
    bm = pages.bookmarks
    with step("1. Open the bookmark manager"):
        bm.open()
    with step("2. Delete 'Static page 2'", expected="a snack bar '1 bookmark deleted' shows"):
        toast = bm.delete("Static page 2")
        assert "deleted" in toast.lower()
    with step("3. Undo", expected="'Static page 2' is listed again"):
        bm.undo()
        bm.wait_item("Static page 2")
```

- Module docstring: the ID, the case title, `Case: <feature>.md`.
- Test name: `test_<what_it_verifies>`, not the ID.
- One `with step(...)` per case step, titled with the case's step number and words: `"2. ..."`,
  `"2-3. ..."` for merged steps, `"2a. ..."` / `"2b. ..."` for a split step (a framework test
  checks the numbering). Never add a step the case does not have: preparation goes before the
  first step, and the actions needed to check an Expected (open the manager, read a list) go
  into the step whose outcome they check.
- `expected=` goes only on the steps whose outcome a bullet of the case's Expected describes,
  with the text of those bullets; the assertions of a bullet go into the same step. Steps
  without such a bullet get no `expected=`.
- Assert the result (list content, file on disk, URL, title, snack bar or toast text), not that
  a click happened. For a state that appears later, use a `wait_*` call: it raises with a
  message when the state does not appear.
- Act only through `web.*`, `native.*`, page objects and dialog helpers: only these actions are
  framed in step pictures and videos.
- No cleanup of browser data. Delete only what the test created outside the profile (files
  outside `tmp_path` and `downloads_dir`, windows of other applications).

Imports:

```python
import pytest
from sbtest.steps import step
from sbtest.utils import unique          # unique("Folder") -> "Folder_1a2b3c"
from sbtest.data import files            # generated files
from sbtest.web import Keys              # web.press(Keys.CONTROL, "a")
```

## Fixtures

| fixture | content |
|---|---|
| `web` | everything inside web content (`references/web-api.md`) |
| `native` | the browser's own UI and Windows (`references/native-ui.md`); the test is skipped where native UI is not available |
| `pages` | page objects: `pages.bookmarks`, `pages.history`, `pages.downloads`, `pages.extensions`, `pages.webstore` |
| `site` | the local web server (Local site) |
| `session` | the browser: `session.restart()` (same profile), `session.downloads_dir` |
| `downloads_dir` | the download folder of this test's profile |
| `data` | `data("addons")` -> `resources/data/addons.yaml` with `{site}` replaced |
| `cfg` | settings: `cfg.page_url("history")` (the URL `web.open` takes), `cfg.display_url("history")` (the URL the address bar shows) |
| `tmp_path` | pytest's temporary folder |

## Markers

- `@pytest.mark.case("<ID>")` - required on every test.
- `@pytest.mark.native` - the case's Type is `native` or `mixed`.
- `@pytest.mark.sanity` - only when the user or the source says the case is part of the sanity
  pass.
- `@pytest.mark.slow` - the test takes more than about 60 s.
- `@pytest.mark.browser(...)` - preconditions (below).
- The feature marker is set from the folder.

## Preconditions

| the case says | do |
|---|---|
| bookmarks or folders exist | `@pytest.mark.browser(bookmarks="seed_basic")` (a key of `resources/data/bookmarks.yaml`) or `bookmarks={"bookmark_bar": [{"name": "A", "url": "{site}/page?title=A"}]}` |
| a setting has a value | `@pytest.mark.browser(prefs={"download.prompt_for_download": True})` |
| an add-on is installed | `@pytest.mark.browser(extensions=["sample_addon"])` (unpacked, from `resources/extensions/`) |
| the browser starts with a switch | `@pytest.mark.browser(args=["--start-maximized"])` |
| the browser starts on an internal page | `@pytest.mark.browser(start_page="history")` |
| pages were visited (history has no seed) | before the first step: `web.open(site.page("Alpha")); web.wait_title("Alpha")` for each page |
| a file was downloaded | before the first step: `web.open(site.url("/downloads.html")); web.click("#dl-txt"); web.wait_file(downloads_dir, "sample.txt")` |
| a local file to upload or import | `files.text_file(tmp_path, "a.txt")`, `files.bookmarks_html(tmp_path, [...])` |

The browser window opens on the test's first page. A test whose first step is a `native` step
starts on the browser's home page.

## Data files

`resources/data/bookmarks.yaml`:

```yaml
seed_basic:
  bookmark_bar:
    - {name: Static page 1, url: "{site}/pages/page1.html"}
    - name: Work
      children:
        - {name: Form page, url: "{site}/form.html"}
  other:
    - {name: Other page, url: "{site}/pages/page3.html"}
new_bookmark: {name: My new bookmark, url: "{site}/page?title=New"}
```

`{site}` is replaced by the local server's address. Roots: `bookmark_bar`, `other`, `synced`.
Another set of bookmarks -> add a key. `resources/data/addons.yaml`: `sample` (name, unpacked
folder) and `webstore` (store id, name).

## Local site

| call | page |
|---|---|
| `site.page("Alpha")` | a page whose `<title>` and `h1#title` are `Alpha` |
| `site.url("/pages/page1.html")` | "Static page 1".."3", `#next` link, `#body` paragraph |
| `site.url("/form.html")` | all form controls and a file input; submits to `/upload` |
| `site.url("/inputs.html")` | text, number, date, range, multi-select, contenteditable, disabled; the last key in `#last-key` |
| `site.url("/mouse.html")` | click, double click, context menu, hover menu, far element |
| `site.url("/upload.html")` | `#file` input, `#pick` opens the Windows Open dialog (`#picked`), `#drop-zone` for files dragged from Explorer (`#dropped`) |
| `site.url("/dialogs.html")` | alert, confirm, prompt, beforeunload, print, `<dialog>` |
| `site.url("/dragdrop.html")` | HTML5 drag and drop, sortable list, mouse drag box |
| `site.url("/popups.html")` | `target=_blank` link, `window.open`, same-tab link |
| `site.url("/downloads.html")` | `#dl-txt` sample.txt 2 KB, `#dl-bin` data.bin 100 KB, `#dl-png` photo.png, `#dl-slow` slow.bin 10 MB (slow), `#dl-attr` link with a download attribute |
| `site.url("/frames.html")` | iframe `#inner` |
| `site.url("/permissions.html")` | notification and location requests |
| `site.url("/toast.html")` | in-page toast |
| `site.download("a.pdf", 4096, "application/pdf")` | a URL that downloads a file |
| `site.slow_download("big.bin", size, chunk, delay)` | a download that stays in progress |
| `site.url("/redirect", to="/page?title=X")`, `site.url("/status", code=404)` | redirect, error page |
| `site.url("/basic-auth")` | HTTP sign-in prompt (user and password `sbtest`) |
| `site.url("/delayed", ms=1500, text="Ready")` | `#late` appears after a delay |

A new page: an HTML file in `resources/site/` with an id on every element a test uses, or a
route in `sbtest/server/local_site.py`.

## Generated files and the sample add-on

```python
files.text_file(tmp_path, "a.txt", "content")
files.binary_file(tmp_path, "a.bin", 4096)
files.png_file(tmp_path, "img.png")
files.bookmarks_html(tmp_path, [("Title", url)])   # a file for "Import bookmarks"
```

`resources/extensions/sample_addon/` (manifest v3) has a popup, an options page and a content
script that sets `<html data-sb-addon="active">` on `http://127.0.0.1/*`.
