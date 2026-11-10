"""Command line tools: setup, summary, case overview, coverage."""
import json

import yaml

from sbtest.reporting.cases import parse_file
from sbtest.tools import case_overview as co, summary
from sbtest.tools.coverage import native_mismatch
from sbtest.tools.setup import ensure_exe, save_exe
from sbtest.tools.summary import collect


def test_setup_saves_the_exe_keeping_local_yaml(tmp_path):
    example = tmp_path / "local.example.yaml"
    example.write_text("# comment kept\nbrowser:\n  exe: 'C:/build/SamsungInternet.exe'\n  # headless: x\n"
                       "network:\n  # download_proxy: y\n", encoding="utf-8")
    local = tmp_path / "local.yaml"
    save_exe(r"D:\sb\SamsungInternet.exe", local)          # new file: starts from the example
    text = local.read_text(encoding="utf-8")
    assert "# comment kept" in text and "# headless: x" in text
    assert yaml.safe_load(text)["browser"]["exe"] == r"D:\sb\SamsungInternet.exe"
    save_exe(r"E:\new\SamsungInternet.exe", local)         # existing file: only that line changes
    assert yaml.safe_load(local.read_text(encoding="utf-8"))["browser"]["exe"] == r"E:\new\SamsungInternet.exe"
    assert local.read_text(encoding="utf-8").count("exe:") == 1

    other = tmp_path / "other" / "local.yaml"
    other.parent.mkdir()
    other.write_text("network:\n  browser_proxy: http://p:8080\n", encoding="utf-8")
    save_exe(r"C:\x\SamsungInternet.exe", other)           # no browser: section -> appended
    data = yaml.safe_load(other.read_text(encoding="utf-8"))
    assert data == {"network": {"browser_proxy": "http://p:8080"}, "browser": {"exe": r"C:\x\SamsungInternet.exe"}}


def test_setup_save_makes_the_exe_the_default(tmp_path):
    exe = tmp_path / "SamsungInternet.exe"
    exe.write_bytes(b"")
    local = tmp_path / "local.yaml"
    assert ensure_exe(str(exe), local=local) == str(exe) and not local.exists()   # check only
    assert ensure_exe(str(exe), save=True, local=local) == str(exe)
    assert yaml.safe_load(local.read_text(encoding="utf-8"))["browser"]["exe"] == str(exe)
    assert ensure_exe(str(tmp_path / "missing.exe"), save=True, local=local) is None


def test_summary_lists_failures_with_evidence(tmp_path, monkeypatch):
    doc = tmp_path / "page.md"   # the case doc that gives the failure its title
    doc.write_text("## DL-003 Clear all\n- Steps:\n  1. Open downloads\n", encoding="utf-8")
    monkeypatch.setattr(summary, "load_cases",
                        lambda: {c.id: c for c in parse_file(doc, "downloads", "tests/features/downloads/page.md")})
    ev = tmp_path / "failures" / "t2"
    ev.mkdir(parents=True)
    tests = [
        {"nodeid": "tests/features/general/test_navigation.py::test_back_forward", "name": "test_back_forward",
         "feature": "general", "cases": ["GEN-001"], "outcome": "passed", "duration": 1.0},
        {"nodeid": "tests/features/downloads/test_downloads.py::test_clear_all", "name": "test_clear_all",
         "feature": "downloads", "cases": ["DL-003"], "outcome": "failed", "duration": 2.0,
         "failed_step": "3. Clear all", "message": "Timed out", "evidence_dir": str(ev)},
    ]
    (tmp_path / "results.json").write_text(json.dumps({"meta": {"selection": "all"}, "tests": tests}))
    data = collect(tmp_path)
    assert data["verdict"] == "BUILD FAILED"
    assert data["per_feature"] == {"downloads": {"failed": 1}, "general": {"passed": 1}}
    assert data["failures"] == [{"case": "DL-003", "title": "Clear all", "outcome": "failed",
                                 "test": tests[1]["nodeid"], "failed_step": "3. Clear all", "error": "Timed out",
                                 "evidence": str(ev / "failure.txt")}]


def test_summary_markdown_lists_every_case(tmp_path, monkeypatch):
    tests = [{"nodeid": "tests/features/bookmarks/test_bm_001.py::test_a", "name": "test_a", "feature": "bookmarks",
              "cases": ["BM-001"], "outcome": "passed", "duration": 1.0},
             {"nodeid": "tests/features/bookmarks/test_bm_002.py::test_b", "name": "test_b", "feature": "bookmarks",
              "cases": ["BM-002"], "outcome": "failed", "duration": 1.0, "failed_step": "2. Delete",
              "message": "Timed out\nmore"}]
    (tmp_path / "results.json").write_text(json.dumps({"meta": {"selection": "--feature=bookmarks",
                                                                "started": "2026-11-07T10:00:00"}, "tests": tests}))
    monkeypatch.setattr(summary, "load_cases", lambda: {})
    md = summary.markdown(summary.collect(tmp_path))
    assert "**BUILD FAILED** - passed 1, failed 1" in md and "2026-11-07 10:00" in md
    assert "| BM-001 |" in md and "| BM-002 |" in md and '- **BM-002** at "2. Delete": Timed out' in md


def test_overview_keeps_results_of_cases_not_rerun(tmp_path):
    md = tmp_path / "TESTCASES.md"
    md.write_text("| BM-001 | A | High | web |  | x.md | ✅ Pass |\n| DL-003 | B | Medium | native |  | y.md | ⏳ Not run |\n",
                  encoding="utf-8")
    assert co.previous_results(md) == {"BM-001": "passed", "DL-003": None}
    assert co.previous_results(tmp_path / "missing.md") == {}


def test_coverage_flags_a_type_that_disagrees_with_the_native_marker():
    rows = [{"id": "A-1", "type": "native", "tests": ["t.py::a"]},
            {"id": "A-2", "type": "web", "tests": ["t.py::b"]},
            {"id": "A-3", "type": "mixed", "tests": ["t.py::c"]},
            {"id": "A-4", "type": "native", "tests": []}]                   # not automated: no check
    marks = {"A-1": {"native": True}, "A-2": {"native": True}, "A-3": {"native": False}}
    assert [m.split(":")[0] for m in native_mismatch(rows, marks)] == ["A-2", "A-3"]
