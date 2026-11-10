"""Layered configuration: default.yaml < local.yaml < env < CLI."""
import yaml

from sbtest.config import load_config


def test_config_layers(tmp_path, monkeypatch):
    (tmp_path / "default.yaml").write_text(yaml.safe_dump({"browser": {"exe": "", "headless": False},
                                                           "pages": {"scheme": "chrome", "history": "history"}}))
    (tmp_path / "local.yaml").write_text(yaml.safe_dump({"browser": {"exe": "C:/a.exe"}}))
    monkeypatch.setenv("SB_HEADLESS", "true")
    cfg = load_config({"browser.mode": "attach"}, config_dir=tmp_path)
    assert cfg.get("browser.exe") == "C:/a.exe"
    assert cfg.get("browser.headless") is True
    assert cfg.get("browser.mode") == "attach"
    assert cfg.page_url("history") == "chrome://history"
    assert cfg.page_url("internet://x") == "internet://x"


def test_local_yaml_layers(tmp_path, monkeypatch):
    monkeypatch.delenv("SB_EXE", raising=False)
    (tmp_path / "default.yaml").write_text(yaml.safe_dump(
        {"pages": {"scheme": "chrome", "display_scheme": "internet", "history": "history"}, "browser": {"exe": ""}}))
    (tmp_path / "local.yaml").write_text(yaml.safe_dump({"browser": {"exe": "a.exe"}}))
    assert load_config(config_dir=tmp_path).get("browser.exe") == "a.exe"
    assert load_config({"browser.exe": "cli.exe"}, config_dir=tmp_path).get("browser.exe") == "cli.exe"


def test_display_url_vs_navigation_url(tmp_path):
    (tmp_path / "default.yaml").write_text(yaml.safe_dump(
        {"pages": {"scheme": "chrome", "display_scheme": "internet", "history": "history"}}))
    cfg = load_config(config_dir=tmp_path)
    assert (cfg.page_url("history"), cfg.display_url("history")) == ("chrome://history", "internet://history")
