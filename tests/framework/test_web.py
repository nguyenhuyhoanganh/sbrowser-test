"""Web layer and page objects: locator syntax, the pages factory."""
from types import SimpleNamespace

from sbtest.pages import ExtensionsPage, Pages
from sbtest.web.actions import Keys, key_combos
from sbtest.web.locators import Locator, parse, to_selector


def test_default_is_css():
    assert parse("#a .b") == Locator("css", "#a .b")


def test_prefixes():
    assert parse("xpath=//a").kind == "xpath"
    assert parse("//a").kind == "xpath"
    assert parse("(//a)[1]").kind == "xpath"
    assert parse("id=x") == Locator("id", "x")
    assert parse("text=Delete") == Locator("text", "Delete")
    assert parse("text~=del") == Locator("textc", "del")
    assert parse("aria=Search") == Locator("aria", "Search")
    assert parse("deepcss=cr-toast") == Locator("deepcss", "cr-toast")


def test_shadow_path():
    assert parse("a-app >>> #x >>> input") == Locator("deep", ("a-app", "#x", "input"))
    assert parse("deep=#only") == Locator("deep", ("#only",))
    assert parse("css=a >>> b").kind == "deep"


def test_playwright_selectors():
    assert to_selector("#a .b") == "css=#a .b"
    assert to_selector("a-app >>> #x >>> input") == "css=a-app >> css=#x >> css=input"
    assert to_selector("deepcss=si-snack-bar", visible=True) == "css=si-snack-bar >> visible=true"
    assert to_selector('text=Say "hi"') == 'text="Say \\"hi\\""'
    assert to_selector("text~=a.b") == "text=/a\\.b/i"
    assert to_selector("id=x") == 'css=[id="x"]'
    assert to_selector("aria=Search").startswith('css=[aria-label="Search"], [title="Search"]')
    assert to_selector('role=button[name="Save"]') == 'role=button[name="Save"]'
    assert to_selector("pw=internal:label=Name") == "internal:label=Name"


def test_key_names():
    assert key_combos((Keys.CONTROL, "a")) == ["Control+a"]
    assert key_combos(("ENTER",)) == ["Enter"] and key_combos(("Delete",)) == ["Delete"]
    assert key_combos((Keys.CONTROL, Keys.SHIFT, "Delete")) == ["Control+Shift+Delete"]


def test_pages_factory():
    web = SimpleNamespace(cfg=SimpleNamespace(get=lambda k, d=None: d))
    assert isinstance(Pages(web).extensions, ExtensionsPage)
