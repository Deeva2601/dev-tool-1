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
    assert response.status_code in (400, 422)
    assert "detail" in response.json()

def test_local_path_blocked_when_disabled(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CONTEXTPACK_ALLOW_LOCAL", "0")
    (tmp_path / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    response = client.post("/pack", json={"source": str(tmp_path)})
    assert response.status_code == 400
    assert "Local paths" in response.json()["detail"]

def test_public_mode_rejects_local_and_file_url(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CONTEXTPACK_ALLOW_LOCAL", "0")
    (tmp_path / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    local = client.post("/pack", json={"source": str(tmp_path)})
    assert local.status_code == 400
    file_url = client.post("/pack", json={"source": "file:///tmp/repo"})
    assert file_url.status_code == 400
    other_host = client.post("/pack", json={"source": "https://example.com/a/b.git"})
    assert other_host.status_code == 400


def test_public_mode_accepts_github_shape(monkeypatch) -> None:
    monkeypatch.setenv("CONTEXTPACK_ALLOW_LOCAL", "0")
    response = client.post("/pack", json={"source": "https://github.com/octocat/Hello-World"})
    # Clone may fail without network. Shape check must not be the 400 used for non-GitHub URLs.
    assert response.status_code != 400 or "Only https://github.com" not in response.json()["detail"]


def test_rate_limit(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CONTEXTPACK_ALLOW_LOCAL", "1")
    (tmp_path / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    statuses = [
        client.post("/pack", json={"source": str(tmp_path)}).status_code
        for _ in range(12)
    ]
    assert 429 in statuses

def test_limiter_blocks_the_eleventh_hit() -> None:
    from contextpack.limits import RateLimiter

    gate = RateLimiter(limit=2, window=60)
    assert gate.allow("a")
    assert gate.allow("a")
    assert not gate.allow("a")
    assert gate.allow("b")