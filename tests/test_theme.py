import json

from modules import theme


def test_theme_load_save_and_current_name_use_config_path(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    monkeypatch.setattr(theme, "_CONFIG_PATH", str(config_path))

    config_path.write_text(json.dumps({"theme": "bleu_nuit"}), encoding="utf-8")

    assert theme.get_current_theme_name() == "bleu_nuit"
    assert theme.load_theme()["ACCENT"] == theme.THEMES["bleu_nuit"]["ACCENT"]

    assert theme.save_theme("emeraude")
    assert json.loads(config_path.read_text(encoding="utf-8"))["theme"] == "emeraude"
