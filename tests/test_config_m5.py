from pathlib import Path
import pytest

import api.config as config


def test_dev_secret_key_est_persistee_entre_demarrages(tmp_path, monkeypatch):
    monkeypatch.delenv("API_SECRET_KEY", raising=False)
    monkeypatch.setenv("API_ENV", "development")
    cle_file = tmp_path / ".dev_secret_key"

    cle1 = config._resoudre_secret_key(cle_file)
    cle2 = config._resoudre_secret_key(cle_file)

    assert cle1
    assert cle1 == cle2
    assert cle_file.read_text(encoding="utf-8").strip() == cle1


def test_production_exige_secret_key_et_cors_origins(tmp_path, monkeypatch):
    monkeypatch.setenv("API_ENV", "production")
    monkeypatch.delenv("API_SECRET_KEY", raising=False)
    monkeypatch.delenv("API_CORS_ORIGINS", raising=False)

    with pytest.raises(RuntimeError):
        config._resoudre_secret_key(tmp_path / ".dev_secret_key")

    with pytest.raises(RuntimeError):
        config._resoudre_cors_origins("")


def test_cors_origins_sans_doublons(monkeypatch):
    assert len(config.CORS_ORIGINS) == len(set(config.CORS_ORIGINS))

    monkeypatch.setenv("API_ENV", "development")
    dedup = config._resoudre_cors_origins(
        "http://localhost:3000, http://127.0.0.1:3000, http://localhost:3000"
    )
    assert dedup == ["http://localhost:3000", "http://127.0.0.1:3000"]


def test_python_dotenv_present_dans_requirements():
    req = Path("requirements.txt").read_text(encoding="utf-8")
    assert "python-dotenv" in req