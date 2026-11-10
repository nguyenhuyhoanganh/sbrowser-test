"""Scratch exploration test (tests/_scratch/ is git-ignored)."""
import pytest

from sbtest.tools.explore import Explorer

pytestmark = pytest.mark.native                      # remove for an exploration that uses only `web`


@pytest.mark.browser(bookmarks="seed_basic", extensions=["sample_addon"])   # the data the steps need
def test_explore(web, native, pages, site):
    x = Explorer(web, native, "topic")              # output folder: artifacts/explore/topic/

    web.open(site.url("/index.html"))               # or pages.bookmarks.open(), site.page("Title")
    x.snap("start")                                 # saves NN_start.png + DOM, accessibility and UIA dumps

    # one try_step per user action: it runs the action, saves a picture, and continues after an error
    x.try_step("open the toolbar menu", lambda: native.click("extensions_button"))
    x.find_native("(?i)sb sample|pin|more options")  # prints exact UIA names and classes (for the ui map)
    x.esc()                                          # presses Esc

    x.try_step("internal page", lambda: pages.extensions.open())
    x.find_web("SB Sample Addon")                     # prints DOM lines with ready-to-use locators
