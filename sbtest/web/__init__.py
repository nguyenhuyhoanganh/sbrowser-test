"""Web layer: everything inside web content (Playwright, attached to the session's browser)."""
from sbtest.web.actions import Keys
from sbtest.web.locators import Element
from sbtest.web.web import Web

__all__ = ["Element", "Keys", "Web"]
