import sqlite3
import pytest
from fastapi.testclient import TestClient

from api import config
from api.deps import get_db
from api.main import app
from api.rate_limit import _echecs
from api.schema import init_schema
from api.security import hash_password


@pytest.fixture
def api_client():
    _echecs.clear()
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    init_schema(conn)
    conn.execute(
        "INSERT INTO clients(code, nom, portail_actif, password_hash) VALUES ('CLT-1', 'Client', 1, ?)",
        (hash_password("Secret123"),),
    )
    conn.commit()

    def override_get_db():
        yield conn

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
    _echecs.clear()
    conn.close()


def test_x_forwarded_for_forge_ne_contourne_plus_le_rate_limit(api_client, monkeypatch):
    monkeypatch.setattr(config, "TRUSTED_PROXIES", ())
    statuts = []
    for i in range(6):
        r = api_client.post(
            "/auth/login",
            json={"code_client": "CLT-1", "password": "faux"},
            headers={"X-Forwarded-For": f"203.0.113.{i + 1}", "X-Real-IP": f"198.51.100.{i + 1}"},
        )
        statuts.append(r.status_code)
    assert statuts[:5] == [401] * 5
    assert statuts[5] == 429


def test_proxy_de_confiance_resout_ip_reelle_de_droite_a_gauche(api_client, monkeypatch):
    monkeypatch.setattr(config, "TRUSTED_PROXIES", ("testclient", "10.0.0.0/8"))
    for _ in range(5):
        r = api_client.post(
            "/auth/login",
            json={"code_client": "CLT-1", "password": "faux"},
            headers={"X-Forwarded-For": "1.1.1.1, 198.51.100.50, 10.0.0.5"},
        )
        assert r.status_code == 401
    # Même IP réelle derrière le proxy -> bloquée à la 6e tentative
    r6 = api_client.post(
        "/auth/login",
        json={"code_client": "CLT-1", "password": "faux"},
        headers={"X-Forwarded-For": "9.9.9.9, 198.51.100.50, 10.0.0.8"},
    )
    assert r6.status_code == 429
    # Une autre IP réelle légitime passant par le même proxy n'est pas bloquée
    autre = api_client.post(
        "/auth/login",
        json={"code_client": "CLT-1", "password": "faux"},
        headers={"X-Forwarded-For": "198.51.100.99, 10.0.0.8"},
    )
    assert autre.status_code == 401