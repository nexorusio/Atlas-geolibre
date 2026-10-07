import importlib.util
import json
import stat
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("projects_configure", ROOT / "configure.py")
configure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(configure)


def test_private_configuration_matches_browser_oauth_callback(tmp_path):
    configure.create_environment(tmp_path, "https://atlas.example/", "registry.example/projects:sha-123", "atlas_proxy")
    path = tmp_path / ".env"
    values = dict(line.split("=", 1) for line in path.read_text().splitlines())
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert len(values["PROJECTS_DB_PASSWORD"]) == 64
    assert all(c in "0123456789abcdef" for c in values["PROJECTS_DB_PASSWORD"])
    clients = json.loads(values["PROJECTS_OAUTH_CLIENTS"].strip("'"))
    assert clients[0]["redirect_uris"] == ["https://atlas.example/oauth-callback.html"]
    assert "write:projects" in clients[0]["scopes"]


def test_rerun_never_rotates_an_existing_database_password(tmp_path):
    configure.create_environment(tmp_path, "https://atlas.example", "registry.example/projects:sha-123", "atlas_proxy")
    original = (tmp_path / ".env").read_bytes()
    with pytest.raises(FileExistsError):
        configure.create_environment(tmp_path, "https://atlas.example", "registry.example/projects:sha-456", "atlas_proxy")
    assert (tmp_path / ".env").read_bytes() == original


@pytest.mark.parametrize("origin", [
    "http://atlas.example", "https://atlas.example/projects", "https://user:secret@atlas.example",
    "https://atlas.example?token=secret", "https://atlas.example#fragment", "https://atlas.example\nOTHER=value",
])
def test_invalid_origin_cannot_create_a_secret_file(tmp_path, origin):
    with pytest.raises(ValueError):
        configure.create_environment(tmp_path, origin, "registry.example/projects:sha-123", "atlas_proxy")
    assert not (tmp_path / ".env").exists()
