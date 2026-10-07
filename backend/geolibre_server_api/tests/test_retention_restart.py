"""Retain opaque workspace contents and ownership across API reconstruction."""

import json
from urllib.parse import urlsplit

from fastapi.testclient import TestClient
from geolibre_server_api.main import FileStorage, create_app
from helpers import account, auth


def test_private_workspace_and_versions_survive_server_reconstruction(tmp_path, monkeypatch):
    monkeypatch.delenv("GEOLIBRE_OAUTH_CLIENTS", raising=False)
    database = f"sqlite:///{tmp_path / 'retained.db'}"
    issuer = "https://atlas.example/projects"
    objects = tmp_path / "objects"
    workspace = {
        "version": "1.0", "title": "Retained workspace",
        "layers": [{"id": "local-result", "type": "geojson", "data": {"type": "FeatureCollection", "features": []}}],
        "mapView": {"center": [106.8, -6.2], "zoom": 9},
        "layout": {"title": "Field report"},
    }
    initial = create_app(database, public_url=issuer, storage=FileStorage(str(objects)))
    with TestClient(initial) as client:
        owner = account(client)
        other = account(client, "grace")
        response = client.post("/api/projects", headers=auth(owner), json={
            "filename": "retained.geolibre.json", "content": json.dumps(workspace), "visibility": "private",
        })
        assert response.status_code == 201
        project = response.json()["project"]
        assert project["rawJsonUrl"].startswith(issuer + "/")
        updated = {**workspace, "title": "Second revision"}
        assert client.put(f"/api/projects/{project['id']}/content", headers=auth(owner), json={"content": json.dumps(updated)}).status_code == 201
    initial.state.engine.dispose()

    reopened = create_app(database, public_url=issuer, storage=FileStorage(str(objects)))
    with TestClient(reopened) as client:
        # The gateway removes /projects; authorization is still required.
        raw_path = urlsplit(project["rawJsonUrl"]).path.removeprefix("/projects")
        assert client.get(raw_path).status_code == 404
        assert client.get(raw_path, headers=auth(other)).status_code == 404
        assert client.get(raw_path, headers=auth(owner)).json() == updated
        history = f"/api/projects/{project['id']}/versions/1"
        assert client.get(history, headers=auth(owner)).json() == workspace
        assert client.get(history, headers=auth(other)).status_code == 404
        mine = client.get("/api/projects?mine=true", headers=auth(owner)).json()["projects"]
        assert [item["id"] for item in mine] == [project["id"]]
        assert mine[0]["versionCount"] == 2
    reopened.state.engine.dispose()
