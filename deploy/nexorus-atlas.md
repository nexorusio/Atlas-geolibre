# Nexorus Atlas deployment

This fork builds the web image from the repository root Dockerfile. The existing
`Publish Container Image` workflow tests pull requests and publishes
`ghcr.io/nexorusio/atlas-geolibre` after a push to `main` or a `v*` tag.
Actions must be enabled for this fork. The GHCR package must be public, or the
Droplet must authenticate to GHCR before pulling.

## Update the current Compose deployment

On the Droplet, edit only the `geolibre.image` line in
`/srv/atlas-geolibre/compose.yaml` after a tagged image has been published:

```yaml
image: ghcr.io/nexorusio/atlas-geolibre:v3.1.0-nexorus.1
```

Then run:

```sh
cd /srv/atlas-geolibre
sudo docker compose pull geolibre
sudo docker compose up -d --no-deps geolibre
sudo docker compose ps
```

The Caddy container and the `./work` and `./data` mounts stay in place. A
GitHub commit does not automatically change the running container: publish an
image and explicitly pull/recreate the `geolibre` service for each release.
Keep a copy of the previous image line for rollback.

## Sign-in

The branded screen wraps GeoLibre's built-in Clerk sign-in when
`GEOLIBRE_CLERK_PUBLISHABLE_KEY` is configured. Create a Clerk application
named Nexorus Atlas, allow `atlas.nexorus.io`, and restrict registration to
approved users. Set the publishable key on the `geolibre` service only after
the Clerk application is ready. Auth0's built-in gate receives the same
Nexorus shell, but its actual credential form is hosted by Auth0 and must be
branded there.

The in-app sign-in is a client-side gate. It does not protect `/data/*`,
`/sidecar/*`, or other server URLs. Leave the current Caddy `basic_auth`
enabled until a server-side session-aware auth proxy protects the entire
hostname. With both enabled, visitors see the Caddy popup first and then the
branded sign-in. Do not remove Caddy authentication based solely on the
appearance of the new login screen.

See GeoLibre's self-hosting guide for the supported server-side proxy options:
https://geolibre.app/self-hosting/
