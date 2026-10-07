# Nexorus Atlas Catalog frontend

Builds GeoLens v1.22.0 at commit `40b8473cf7506a44cd6f52201366d41d19b44f3a`
with the existing Nexorus logo, favicon and PWA icons from this repository.
Changes the header/login logo, accessible app name, browser title and dark-mode
surface colors. The normal GeoLens footer attribution stays visible.

The build runs the upstream frontend build, lint, typecheck and coverage suite.
It retains the official frontend runtime, nginx template and entrypoint. Backend,
dataset authorization, schema, OAuth/OIDC and Cloudflare configuration do not
change. The Sign In control still requires a real GeoLens application session;
Cloudflare Access admission alone does not issue a GeoLens token.

After the PR is merged and the Atlas Catalog frontend workflow succeeds, publish
tags are `ghcr.io/nexorusio/atlas-geolibre:catalog-main` and
`ghcr.io/nexorusio/atlas-geolibre:catalog-sha-<full GitHub commit SHA>`.
Use the immutable commit tag for deployment.

On the Droplet, back up `docker-compose.atlas.yml`. Add only an `image:` value
under its existing `services.frontend` map, preserving both networks and the
`atlas-geolens-catalog` alias. Pull and recreate only `frontend` with
`docker compose up -d --no-deps --wait frontend` in `/srv/atlas-geolens`.
No Caddy reload or database migration is required. Rollback uses the previous
frontend image and the same Compose networks and volumes.

Verify header branding, login page, browser tab title and favicon in a fresh
browser session at `https://catalog.nexorus.io`. Also verify sign-in succeeds,
the authenticated user menu replaces Sign In, and Atlas still opens separately.
