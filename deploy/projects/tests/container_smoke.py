"""CI-only proof of proxying, OAuth, private retention and isolated restore."""

import argparse
import base64
import hashlib
import json
import re
import secrets
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx
import yaml

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://atlas.example"
ISSUER = ORIGIN + "/projects"
PASSWORD = secrets.token_urlsafe(24)
COMPOSE = ["docker", "compose", "-f", str(ROOT / "compose.yaml"), "-f", str(ROOT / "tests/compose.ci.yaml")]


class LoopbackProxyTransport(httpx.HTTPTransport):
    """Model HTTPS at the tunnel while the proxy hop is HTTP on loopback.

    The browser sees the canonical HTTPS URL, so secure OAuth cookies follow
    browser rules. Only the underlying socket destination changes.
    """

    def __init__(self, port):
        super().__init__()
        self.port = port

    def handle_request(self, request):
        assert request.url.host == "atlas.example" and request.url.scheme == "https"
        forwarded = httpx.Request(
            request.method,
            request.url.copy_with(scheme="http", host="127.0.0.1", port=self.port),
            headers=request.headers, stream=request.stream, extensions=request.extensions,
        )
        return super().handle_request(forwarded)


def run(command, **kwargs):
    return subprocess.run(command, cwd=ROOT, check=True, **kwargs)


def expect(response, status=200):
    # Avoid dumping response bodies containing tokens on assertion failures.
    assert response.status_code == status, f"{response.request.method} {response.request.url.path}: HTTP {response.status_code}, expected {status}"
    return response


def provision(username):
    with httpx.Client(base_url="http://127.0.0.1:18001", timeout=15) as operator:
        response = expect(operator.post("/api/accounts", json={
            "username": username, "password": PASSWORD,
        }), 201)
        return response.json()["token"]


def oauth(browser, username):
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(32)
    page = expect(browser.get("/projects/oauth/authorize", params={
        "client_id": "geolibre-web", "redirect_uri": ORIGIN + "/oauth-callback.html",
        "response_type": "code", "scope": "read:projects write:projects share:public",
        "state": state, "code_challenge": challenge, "code_challenge_method": "S256",
    }))
    interaction = re.search(r"name='interaction' value='([^']+)'", page.text).group(1)
    csrf = re.search(r"name='csrf' value='([^']+)'", page.text).group(1)
    approved = expect(browser.post("/projects/oauth/authorize", headers={"Origin": ORIGIN}, data={
        "interaction": interaction, "csrf": csrf, "username": username,
        "password": PASSWORD, "decision": "allow", "label": "Retention test",
    }), 303)
    location = urlsplit(approved.headers["location"])
    assert f"{location.scheme}://{location.netloc}{location.path}" == ORIGIN + "/oauth-callback.html"
    params = parse_qs(location.query)
    assert params["iss"] == [ISSUER] and params["state"] == [state]
    token = expect(browser.post("/projects/oauth/token", data={
        "grant_type": "authorization_code", "client_id": "geolibre-web",
        "redirect_uri": ORIGIN + "/oauth-callback.html", "code": params["code"][0],
        "code_verifier": verifier,
    })).json()
    assert token["refresh_token"]
    return token["access_token"]


def authorized(token):
    return {"Authorization": f"Bearer {token}"}


def check_retained(browser, project, content, original, other_token):
    token = oauth(browser, "owner")
    assert project["rawJsonUrl"].startswith(ISSUER + "/")
    raw = urlsplit(project["rawJsonUrl"]).path
    expect(browser.get(raw), 404)
    expect(browser.get(raw, headers=authorized(other_token)), 404)
    assert expect(browser.get(raw, headers=authorized(token))).json() == content
    history = f"/projects/api/projects/{project['id']}/versions/1"
    assert expect(browser.get(history, headers=authorized(token))).json() == original
    expect(browser.get(history, headers=authorized(other_token)), 404)
    mine = expect(browser.get("/projects/api/projects?mine=true", headers=authorized(token))).json()["projects"]
    assert [item["id"] for item in mine] == [project["id"]]
    assert mine[0]["versionCount"] == 2


def isolated_restore(backup, project, content, original, other_token):
    with tempfile.TemporaryDirectory(prefix="projects-restore-") as temp:
        target = Path(temp)
        shutil.copy(ROOT / ".env", target / ".env")
        shutil.copy(ROOT / "nginx.conf", target / "nginx.conf")
        compose = yaml.safe_load((ROOT / "compose.yaml").read_text())
        compose["name"] = "geolibre-projects-restore-test"
        compose["services"]["projects-api"]["ports"] = ["127.0.0.1:18011:8000"]
        compose["services"]["projects-gateway"]["ports"] = ["127.0.0.1:18012:8080"]
        compose["networks"]["atlas_proxy"] = {}
        (target / "compose.yaml").write_text(yaml.safe_dump(compose))
        restore = ["docker", "compose", "--project-directory", str(target), "-f", str(target / "compose.yaml")]
        try:
            run(restore + ["up", "-d", "--wait", "projects-db"])
            with (backup / "projects.dump").open("rb") as dump:
                run(restore + ["exec", "-T", "projects-db", "pg_restore", "-U", "geolibre_projects", "-d", "geolibre_projects", "--exit-on-error"], stdin=dump)
            with (backup / "objects.tar").open("rb") as objects:
                run(restore + ["run", "--rm", "-T", "--no-deps", "--entrypoint", "python", "projects-api", "-c",
                    'import sys,tarfile; t=tarfile.open(fileobj=sys.stdin.buffer,mode="r|"); t.extractall("/data",filter="data")'], stdin=objects)
            run(restore + ["up", "-d", "--wait"])
            with httpx.Client(base_url=ORIGIN, transport=LoopbackProxyTransport(18012), timeout=15) as browser:
                check_retained(browser, project, content, original, other_token)
        finally:
            # Only the separately named disposable restore stack is removed.
            run(restore + ["down", "-v", "--remove-orphans"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ci", action="store_true", required=True)
    parser.parse_args()
    values = dict(line.split("=", 1) for line in (ROOT / ".env").read_text().splitlines())
    assert values["ATLAS_ORIGIN"] == ORIGIN, "This smoke test is for a disposable CI stack only"
    owner_pat, other_pat = provision("owner"), provision("other")
    with httpx.Client(base_url=ORIGIN, transport=LoopbackProxyTransport(18000), timeout=15) as browser:
        assert expect(browser.get("/")).text == "existing Atlas canvas"
        assert expect(browser.get("/data/example")).text == "existing data route"
        assert expect(browser.get("/api/routing-test")).json() == {"service": "catalog-test", "proto": "https"}
        expect(browser.post("/projects/api/accounts", json={}), 403)
        expect(browser.post("/projects/api/accounts/", json={}), 403)
        expect(browser.get("/projects/health"))
        discovery = expect(browser.get("/.well-known/oauth-authorization-server/projects")).json()
        assert discovery["issuer"] == ISSUER
        assert discovery["authorization_endpoint"] == ISSUER + "/oauth/authorize"
        token = oauth(browser, "owner")
        original = {"version": "1.0", "title": "Retained map", "layers": [], "mapView": {"zoom": 9}}
        project = expect(browser.post("/projects/api/projects", headers=authorized(token), json={
            "filename": "retained.geolibre.json", "content": json.dumps(original), "visibility": "private",
        }), 201).json()["project"]
        content = {**original, "title": "Second revision", "layout": {"title": "Report"}}
        expect(browser.put(f"/projects/api/projects/{project['id']}/content", headers=authorized(token), json={"content": json.dumps(content)}), 201)
        check_retained(browser, project, content, original, other_pat)
        run(COMPOSE + ["up", "-d", "--wait", "--force-recreate", "projects-api", "projects-gateway"])
        check_retained(browser, project, content, original, other_pat)
        with tempfile.TemporaryDirectory(prefix="projects-backup-test-") as temp:
            backup = Path(temp) / "backup"
            run(["sh", str(ROOT / "backup.sh"), str(backup)])
            assert (backup / ".env").stat().st_mode & 0o077 == 0
            isolated_restore(backup, project, content, original, other_pat)
        # Exercise the real gateway's password-hashing limit after lifecycle checks.
        statuses = [browser.post("/projects/api/auth/token", json={"username": "owner", "password": "wrong password"}).status_code for _ in range(25)]
        assert 429 in statuses, "Password login rate limit did not activate"
        expect(browser.get(project["rawJsonUrl"].removeprefix(ORIGIN), headers=authorized(owner_pat)))
    print("PASS: Caddy routing, OAuth, private ownership, versions, container recreation and isolated backup restore")


if __name__ == "__main__":
    main()
