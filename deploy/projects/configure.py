"""Create a private projects environment; never replace existing credentials."""

import argparse
import json
import os
import re
import secrets
from pathlib import Path
from urllib.parse import urlsplit


def create_environment(directory: Path, origin: str, image: str, network: str, web_image: str | None = None):
    parsed = urlsplit(origin)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
        or any(c.isspace() for c in origin)
    ):
        raise ValueError("Use an HTTPS origin without a path, credentials or query")
    origin = origin.rstrip("/")
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._/:@-]+", image):
        raise ValueError("Use an image tag or digest without shell metacharacters")
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", network):
        raise ValueError("Use an existing Docker network name")
    if web_image is None and re.fullmatch(r".+:projects-sha-[a-f0-9]{40}", image):
        web_image = image.replace(":projects-sha-", ":web-sha-")
    if web_image is not None and not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._/:@-]+", web_image):
        raise ValueError("Use a web image tag or digest without shell metacharacters")
    clients = [{
        "client_id": "geolibre-web",
        "name": "Atlas Projects",
        "redirect_uris": [f"{origin}/oauth-callback.html"],
        "scopes": ["read:projects", "write:projects", "share:public", "manage:sessions"],
    }]
    contents = (
        f"ATLAS_ORIGIN={origin}\n"
        f"ATLAS_PROXY_NETWORK={network}\n"
        f"PROJECTS_IMAGE={image}\n"
        f"PROJECTS_DB_PASSWORD={secrets.token_hex(32)}\n"
        f"PROJECTS_OAUTH_CLIENTS='{json.dumps(clients, separators=(',', ':'))}'\n"
    )
    if web_image is not None:
        contents += f"ATLAS_WEB_IMAGE={web_image}\n"
    # O_EXCL prevents both accidental replacement and following a pre-existing
    # symlink. The generated hex password is safe in the PostgreSQL URL.
    descriptor = os.open(directory / ".env", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        stream.write(contents)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--network", required=True)
    parser.add_argument("--web-image", help="Defaults to the matching web-sha tag for published projects-sha images")
    args = parser.parse_args()
    try:
        create_environment(Path(__file__).resolve().parent, args.origin, args.image, args.network, args.web_image)
    except (ValueError, FileExistsError) as error:
        parser.exit(1, f"{error}\n")
    print("Created private .env. No existing Atlas configuration was changed.")


if __name__ == "__main__":
    main()
