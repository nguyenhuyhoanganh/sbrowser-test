"""sbtest - automation base for Samsung Internet for Windows (Chromium fork).

    sbtest.config      layered configuration (default.yaml < local.yaml < env < CLI)
    sbtest.browser     start the browser and attach Playwright to it, profiles, Chromium version
    sbtest.web         web layer (Playwright): locators, waits, actions, reading, tabs, frames, JS dialogs
    sbtest.native      native layer (pywinauto/UIA): browser UI, prompts, Windows dialogs, Explorer, keys
    sbtest.pages       page objects of Samsung's internal pages (si-* components)
    sbtest.data        test data: builders, loaders, generated files
    sbtest.server      local HTTP site used as deterministic test content
    sbtest.reporting   failure evidence, results.json, report, share export
    sbtest.tools       CLIs: setup, doctor, dom, uia_dump, explore, coverage, case_overview, report, summary
"""
__version__ = "0.2.0"
