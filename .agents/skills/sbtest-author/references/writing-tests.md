# Writing a test: shape, fixtures, markers, preconditions

## Contents

- Test shape
- Fixtures
- Markers
- Preconditions as data: `@pytest.mark.browser(...)`
- Data files `resources/data/<name>.yaml`
- Local site (`site` fixture)
- Files, unique values, settings, add-ons, profile templates

## Test shape

Which test file: `references/case-format.md`, "Files and names". A new file starts from
`templates/test_template.py`.

```python
"""Bookmark manager page of bookmarks. Cases: page.md (the case doc next to this file)"""
import pytest

from sbtest.steps import step
from sbtest.utils import unique


@pytest.mark.case("<ID>")
@pytest.mark.browser(bookmarks="seed_basic")      # preconditions as data
def test_delete_and_undo(pages):
    bm = pages.bookmarks
    with step("1. Open the bookmark manager"):
        bm.open()
    with step("2. Delete 'Static page 2'", expected="item gone + snack bar"):
        toast = bm.delete("Static page 2")
        assert "deleted" in toast.lower()
    with step("3. Undo", expected="item is back"):
        bm.undo()
        bm.wait_item("Static page 2")
```

- Module docstring: the area + `Cases: <area>.md`.
- Test name: `test_<what_it_verifies>` in snake case, not the ID. One test function per case
  ID; product checks always carry an ID.
- Step titles start with the case's step number(s): `"2-3. ..."` when merged, `"2a. ..."` /
  `"2b. ..."` when one case step is split (a framework test enforces the numbering).
- `expected=` copies the case's Expected for that step; the checks of that Expected go inside
  the step they verify.
- Assertions: plain `assert` with a clear left side; for "eventually" use a `wait_*` (it
  raises with a message), never `assert` + retry loops or `time.sleep`.
- Check the *result*, not that the click happened: list content, pref value, file on disk,
  URL / title, text of the snack bar or toast.
- Act only through `web.*`, `native.*`, page objects and dialog helpers: they record each
  interaction, so `--screenshot-steps` and `--record` frame it. A raw `click_input()`,
  `invoke()`, `send_keys` or `ActionChains` gets no frame.
- Keep a test under ~60 s; longer -> `@pytest.mark.slow`.
- No cleanup of browser data: each test has its own profile. Clean only what you created
  outside it (files outside `tmp_path` / `downloads_dir`, windows of other apps).

Imports a test may need:

```python
import pytest
from sbtest.steps import step
from sbtest.utils import unique
from sbtest.data import files                      # generated files
from sbtest.web import Keys                       # web.press(Keys.CONTROL, "a")
```

## Fixtures

| fixture | what |
|---------|------|
| `web` | `Web` of the current tab: everything inside web content (`references/web-api.md`) |
| `native` | `NativeBrowser`: the browser's own UI and Windows (`references/native-ui.md`); the test is skipped where native UI cannot work |
| `pages` | page objects: `pages.bookmarks`, `pages.history`, `pages.downloads`, `pages.extensions`, `pages.webstore`; `pages.of(other_web)` after a restart |
| `site` | local web server: `site.page("Title")`, `site.url("/upload.html")`, `site.download("a.txt", 2048)` |
| `session` | `BrowserSession`: `restart()`, `profile`, `driver`, `downloads_dir` |
| `downloads_dir` | download folder of this profile |
| `data` | `data("addons")` -> `resources/data/addons.yaml` with `{site}` resolved |
| `cfg` | configuration: `cfg.page_url("history")`, `cfg.display_url("history")` |
| `tmp_path` | pytest temp folder |

## Markers

- `@pytest.mark.case("<ID>")` - required on product tests; links the test to its case.
- `@pytest.mark.native` - any step uses `native`.
- `@pytest.mark.browser(...)` - preconditions, below.
- `@pytest.mark.sanity` - only when the user or the source says the case is in the sanity
  pass; `@pytest.mark.slow` - over ~60 s.
- The feature marker (`bookmarks`, ...) comes from the folder by itself.

## Preconditions as data: `@pytest.mark.browser(...)`

Preconditions are created **before** the browser starts (profile seeding) or with the cheapest
reliable action (visiting a local page). Only the behaviour under test goes through the UI.
Everything is local - no internet.

```python
@pytest.mark.browser(bookmarks="seed_basic")                 # key in resources/data/bookmarks.yaml
@pytest.mark.browser(bookmarks="bookmarks:seed_many")        # explicit file:key
@pytest.mark.browser(bookmarks={"bookmark_bar": [{"name": "A", "url": "{site}/page?title=A"}]})
@pytest.mark.browser(prefs={"download.prompt_for_download": True})
@pytest.mark.browser(extensions=["sample_addon"])             # resources/extensions/<dir>, unpacked
@pytest.mark.browser(args=["--start-maximized"])              # extra switches
@pytest.mark.browser(profile="with_passwords")                # copy resources/profiles/<name>/ first
@pytest.mark.browser(start_page="history")                   # first tab opens it while chromedriver attaches
```

A test with `browser(...)` always gets its own fresh browser.

## Data files `resources/data/<name>.yaml`

```yaml
seed_basic:                     # Bookmarks file structure
  bookmark_bar:
    - {name: Static page 1, url: "{site}/pages/page1.html"}
    - name: Work
      children:
        - {name: Form page, url: "{site}/form.html"}
  other:
    - {name: Other page, url: "{site}/pages/page3.html"}
new_bookmark: {name: My new bookmark, url: "{site}/page?title=New"}
```

`{site}` becomes the local server's base URL. Roots: `bookmark_bar`, `other`, `synced`. In a
test: `data("bookmarks")["new_bookmark"]["url"]`. Need another set -> add a key to the file.

History has no seed file: visit pages, `web.open(site.page(t)); web.wait_title(t)`.

## Local site (`site` fixture)

| URL | Use |
|-----|-----|
| `site.page("Alpha")` | page whose `<title>` and `h1#title` are `Alpha` - unique history / bookmark entries |
| `site.url("/pages/page1.html")` | static pages 1..3 ("Static page 1".."3") with `#next` links, `#body` paragraph |
| `site.url("/form.html")` | all form controls + file input, submits multipart to `/upload` |
| `site.url("/inputs.html")` | text / number / date / range / multi-select / contenteditable / disabled, key log `#last-key` |
| `site.url("/mouse.html")` | click, double click, page context menu, hover menu, far element |
| `site.url("/upload.html")` | `#file` input, `#pick` button -> OS Open dialog (`#picked`), `#drop-zone` for Explorer drags (`#dropped`) |
| `site.url("/dialogs.html")` | alert / confirm / prompt / beforeunload / print (async) / `<dialog>` |
| `site.url("/dragdrop.html")` | HTML5 DnD, sortable list, mouse drag box |
| `site.url("/popups.html")` | target=_blank link, window.open, same-tab link |
| `site.url("/downloads.html")` | `#dl-txt` 2 KB, `#dl-bin` 100 KB, `#dl-slow` 10 MB slow, `#dl-attr` download attribute |
| `site.url("/frames.html")` | iframe `#inner` with input / button posting to the parent |
| `site.url("/permissions.html")` | notification and location permission requests |
| `site.url("/toast.html")` | in-page toast |
| `site.url("/shadow.html")` | nested custom elements (locator practice) |
| `site.download("a.pdf", 4096, "application/pdf")` | any attachment |
| `site.slow_download("big.bin", size, chunk, delay)` | in-progress downloads (pause / cancel) |
| `site.url("/redirect", to="/page?title=X")` / `site.url("/status", code=404)` | redirects / error pages |
| `site.url("/basic-auth")` | HTTP sign-in prompt, user `sbtest` / password `sbtest` |
| `site.url("/delayed", ms=1500, text="Ready")` | `#late` appears after a delay |
| `/echo` (GET / POST form), `/upload` (POST multipart) | the server echoes what it received as JSON |

A new page: an HTML file under `resources/site/` (static) or a route in
`sbtest/server/local_site.py` (dynamic), with ids on everything a test touches.

## Files, unique values, settings, add-ons, profile templates

```python
from sbtest.data import files
files.text_file(tmp_path, "a.txt", "content")
files.binary_file(tmp_path, "a.bin", 4096)
files.png_file(tmp_path, "img.png")
files.bookmarks_html(tmp_path, [("Title", url)])   # Netscape file for "Import bookmarks"
```

- Unique values: `unique("Folder")` -> `Folder_1a2b3c`, for every name a test creates.
- Settings: a fresh profile has the defaults + `browser.prefs` of `config/default.yaml`; another
  start state -> `browser(prefs=...)` (pref names: `chrome://prefs-internals` in the browser).
- Add-ons: `resources/data/addons.yaml` has `sample` (name, unpacked folder) and `webstore`
  (id, name). Unpacked add-ons live in `resources/extensions/<name>/` (manifest v3);
  `sample_addon` has a popup, an options page and a content script that sets
  `<html data-sb-addon="active">` on `http://127.0.0.1/*`. Store installs need internet
  through the proxy.
- Profile templates (rare - prefer seeding): a folder `resources/profiles/<name>/` is copied
  into the fresh profile when a test uses `browser(profile="<name>")`. Make one by running the
  exe with `--user-data-dir=<that folder>`, preparing the state by hand, closing the browser,
  then deleting caches (`Default/Cache`, `Default/Code Cache`, `GrShaderCache`,
  `ShaderCache`, crash dumps).
