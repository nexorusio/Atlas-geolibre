"""Provision one project account locally without displaying its bootstrap token."""

import getpass
import json
import sys
import urllib.error
import urllib.request


def main():
    username = input("Project username (lowercase): ").strip()
    email = input("Staff email: ").strip()
    password = getpass.getpass("New project password: ")
    if password != getpass.getpass("Repeat password: "):
        sys.exit("Passwords differ; account was not created.")
    request = urllib.request.Request(
        "http://127.0.0.1:18001/api/accounts",
        data=json.dumps({
            "username": username, "email": email, "password": password,
            "name": "Operator provisioning", "scopes": ["read:projects"],
            "expiresInDays": 1,
        }).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            response.read()  # Deliberately discard the short-lived bootstrap PAT.
    except urllib.error.HTTPError as error:
        sys.exit(f"Account creation failed (HTTP {error.code}); no secrets displayed.")
    except urllib.error.URLError:
        sys.exit("Local project API is unavailable. Check service health first.")
    print("Account created. Use this username/password in Atlas's project sign-in.")


if __name__ == "__main__":
    main()
