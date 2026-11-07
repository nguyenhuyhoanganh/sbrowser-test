"""Rules every product test under tests/features must follow."""
import ast
import re

from sbtest.config import ROOT
from sbtest.tools.coverage import automated_cases, doc_cases


def test_every_automated_case_is_documented():
    docs, auto = doc_cases(), automated_cases()
    assert not set(auto) - set(docs), "case ids used in tests but missing from the case docs"


def test_step_titles_start_with_the_case_step_number():
    """``with step("2. Add a bookmark", ...)`` - the report maps each step to the case doc by its
    number ("1-3." for merged steps); a check of the Expected belongs to the step it verifies."""
    bad = []
    for py in sorted((ROOT / "tests" / "features").rglob("test_*.py")):
        for node in ast.walk(ast.parse(py.read_text(encoding="utf-8"))):
            if (isinstance(node, ast.Call) and getattr(node.func, "id", None) == "step" and node.args
                    and isinstance(node.args[0], ast.Constant) and not re.match(r"\d+[a-z]?(-\d+[a-z]?)?\. ", node.args[0].value)):
                bad.append(f"{py.relative_to(ROOT).as_posix()}:{node.lineno} {node.args[0].value!r}")
    assert not bad, "step titles must start with the case step number:\n" + "\n".join(bad)
