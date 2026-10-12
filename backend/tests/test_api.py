from pathlib import Path

from fastapi.testclient import TestClient

from contextpack.api import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_pack_local_directory(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CONTEXTPACK_ALLOW_LOCAL", "1")
    (tmp_path / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    response = client.post(
        "/pack",
        json={"source": str(tmp_path), "mode": "full", "format": "markdown"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_tokens"] > 0
    assert body["files"][0]["path"] == "app.py"
    assert "VALUE = 1" in body["document"]


def test_pack_rejects_missing_directory() -> None:
    response = client.post("/pack", json={"source": "D:/does/not/exist"})
    assert response.status_code == 400


def test_pack_rejects_bad_rule() -> None:
    response = client.post(
        "/pack",
        json={"source": ".", "rules": ["not-a-rule"]},
    )
    assert response.status_code == 422


def test_local_path_blocked_when_disabled(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CONTEXTPACK_ALLOW_LOCAL", "0")
    (tmp_path / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    response = client.post("/pack", json={"source": str(tmp_path)})
    assert response.status_code == 400
    assert "Local paths" in response.json()["detail"]