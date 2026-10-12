import json
from pathlib import Path

from contextpack.models import PackConfig
from contextpack.pipeline import pack
from contextpack.secrets import redact


def test_redact_assignment_and_private_key() -> None:
    source = (
        'api_key = "sk-live-abcdefghijklmnopqrstuvwxyz"\n'
        "-----BEGIN PRIVATE KEY-----\n"
        "MIIBVwIBADANBgkqhkiG9w0BAQEFAASCAT8wggE7AgEAAkEA\n"
        "-----END PRIVATE KEY-----\n"
        "name = 'visible'\n"
    )
    cleaned = redact(source)
    assert "sk-live" not in cleaned
    assert "MIIBVwIBADANBgkqhkiG9w0BAQEFAASCAT8wggE7AgEAAkEA" not in cleaned
    assert "name = 'visible'" in cleaned
    assert "[REDACTED]" in cleaned


def test_pack_redacts_before_digest(tmp_path: Path) -> None:
    (tmp_path / "settings.py").write_text(
        'token = "ghp_abcdefghijklmnopqrstuvwxyz123456"\n',
        encoding="utf-8",
    )
    result = pack(PackConfig(root=tmp_path))
    assert "ghp_" not in result.markdown
    assert "[REDACTED]" in result.files[0].content


def test_json_document(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    result = pack(PackConfig(root=tmp_path, format="json"))
    payload = json.loads(result.markdown)
    assert payload["summary"]["files"] == 1
    assert payload["files"][0]["path"] == "app.py"
    assert "VALUE = 1" in payload["files"][0]["content"]


def test_xml_document(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    result = pack(PackConfig(root=tmp_path, format="xml"))
    assert result.markdown.startswith("<?xml")
    assert 'path="app.py"' in result.markdown
    assert "VALUE = 1" in result.markdown


def test_no_redact_flag(tmp_path: Path) -> None:
    secret = 'api_key = "abcdefghij1234567890"\n'
    (tmp_path / "settings.py").write_text(secret, encoding="utf-8")
    result = pack(PackConfig(root=tmp_path, redact_secrets=False))
    assert "abcdefghij1234567890" in result.files[0].content