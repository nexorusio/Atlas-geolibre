# Atlas: one login and a real Log out button

This runbook is for the existing one-Droplet installation at
`/srv/atlas-geolibre`. Cloudflare Access supplies the login session; a
`cloudflared` container on the same Droplet connects it to Caddy. This is an
alternative to GeoLibre's optional Clerk/Auth0 *client-side* gates. The app
shows a **Log out** link only when `GEOLIBRE_CLOUDFLARE_ACCESS=1`; Cloudflare
revokes the session at `/cdn-cgi/access/logout`. The link is a UI convenience,
not an authorization check.

Do not disable the current Caddy `basic_auth` or expose GeoLibre directly until
the tunnel is running, Access has an exact-email Allow policy, and the public
origin ports are unpublished. Otherwise `/data/*`, `/sidecar/*`, and `/ai/*`
would be accessible without a session. Do not set Clerk/Auth0 at the same time.

## 1. Prepare Cloudflare Access (no change to the Droplet)

1. In [Cloudflare dashboard](https://dash.cloudflare.com/), open **Zero Trust →
   Access controls → Applications → Create new application → Self-hosted and
   private**. Add public hostname `atlas.nexorus.io` with **no path restriction**.
2. Add an **Allow** policy with only the exact email addresses of authorized
   users. Enable the **One-time PIN** identity provider, or the existing company
   identity provider. Avoid `Everyone` and broad email domains. Set the
   application session duration (for example, 8 hours).
3. In **Zero Trust → Reusable components → Custom pages → Access login page**,
   set organization name `Nexorus Atlas`, upload/use a publicly reachable
   Nexorus logo, and choose dark blue `#08172f` for the background. This page
   is owned by Cloudflare; the old browser popup will be removed at cutover.
4. Under **Networking → Tunnels**, create a remotely managed tunnel named
   `atlas`. Copy **only the tunnel token** from the Docker command into a
   private password manager. Never commit it to Git or send it in chat.

Cloudflare's Access application must exist *before* publishing a route: a
tunnel route without an Access policy can make the site public.

## 2. Add the tunnel container without switching DNS

Connect via PowerShell `ssh atlas`, then `cd /srv/atlas-geolibre`. Edit with
`sudo nano /srv/atlas-geolibre/compose.yaml` (save: Ctrl+O, Enter, Ctrl+X).
First make local rollback copies:

```sh
cd /srv/atlas-geolibre
sudo cp compose.yaml compose.yaml.pre-access
sudo cp Caddyfile Caddyfile.pre-access
```

Add a sibling service below `caddy` and `geolibre` (indent two spaces):

```yaml
  cloudflared:
    image: cloudflare/cloudflared:latest
    command: tunnel --no-autoupdate run
    environment:
      TUNNEL_TOKEN: ${CLOUDFLARE_TUNNEL_TOKEN:?set CLOUDFLARE_TUNNEL_TOKEN in .env}
    restart: unless-stopped
```

Store the token in `/srv/atlas-geolibre/.env`, with mode 600. Do this locally
in the SSH session and never paste the resulting file into a support chat:

```sh
cd /srv/atlas-geolibre
sudo nano .env
sudo chmod 600 .env
sudo docker compose config --quiet
sudo docker compose up -d cloudflared
sudo docker compose ps
```

The `.env` file needs a single line
`CLOUDFLARE_TUNNEL_TOKEN=the-token-from-Cloudflare` (no spaces or quotes).
This container shares the Compose network, so the dashboard route can reach
`caddy` without exposing a new host port. Keep `basic_auth` for now.

## 3. Publish and verify the protected tunnel

In Cloudflare's **Networking → Tunnels → atlas → Routes**, add a public route
for `atlas.nexorus.io` pointing at `https://caddy:443`. Under its TLS origin
settings set **Origin Server Name** to `atlas.nexorus.io` so Caddy's existing
certificate is verified. Turn on **Protect with Access** and select the Atlas
Access application. Do not use `No TLS Verify`.

The existing `atlas` A record points to the Droplet. The tunnel route will
require a CNAME to `<tunnel-id>.cfargotunnel.com`. Cloudflare may report a DNS
conflict: remove **only** the old `atlas` A/AAAA record, then save the tunnel
route, which creates the new proxied CNAME. This may cause a short outage.

In a private window, check these three observations before proceeding:

1. `https://atlas.nexorus.io/` shows Cloudflare's Nexorus sign-in first.
2. An email outside the Allow policy cannot enter. An allowed email receives
   its PIN and can continue to the **old** Caddy password prompt. That second
   prompt is expected during this transition.
3. `https://atlas.nexorus.io/data/` and `/sidecar/` also require Access; do not
   create a Bypass policy for either route. Confirm the tunnel route shows
   **Protect with Access** enabled.

If Access does not appear, keep Caddy's password prompt and stop the cutover.

## 4. Close the direct route to Caddy

Only after step 3 passes: in `/srv/atlas-geolibre/compose.yaml`, remove the
`ports:` entries from the **caddy** service. Do not change the SSH service or
Droplet firewall. The tunnel reaches `caddy:443` over Compose's internal
network. Then run:

```sh
cd /srv/atlas-geolibre
sudo docker compose config --quiet
sudo docker compose up -d --no-deps caddy
sudo docker compose ps
```

`docker compose ps` should show **no** `0.0.0.0:80` or `0.0.0.0:443` mapping
for Caddy, and `atlas.nexorus.io` should still work through Access. The old
Droplet IP may remain discoverable, but it must not serve Atlas on 80/443.

## 5. Remove the popup and enable Log out

Open `sudo nano /srv/atlas-geolibre/Caddyfile`. Change only the site address
from `atlas.nexorus.io {` to `http://atlas.nexorus.io {`, then delete the full
`basic_auth { ... }` block. Preserve the existing `/data/*` handler and the
`reverse_proxy geolibre:80` handler. Caddy now listens on plain HTTP inside
the private Compose network; Cloudflare serves HTTPS to visitors.

In Cloudflare's tunnel route, change the service URL to `http://caddy:80`
(no TLS origin setting is needed for this private hop). Validate and reload
Caddy on the Droplet:

```sh
cd /srv/atlas-geolibre
sudo docker compose exec caddy caddy validate --config /etc/caddy/Caddyfile
sudo docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile
```

Add the following line under the `geolibre:` service's existing `environment:`
block in `compose.yaml`:

```yaml
      GEOLIBRE_CLOUDFLARE_ACCESS: "1"
```

Use the merged fork image (`ghcr.io/nexorusio/atlas-geolibre:main`). The
commit must be merged and the GitHub package publish workflow completed before
pulling. Then:

```sh
cd /srv/atlas-geolibre
sudo docker compose config --quiet
sudo docker compose pull geolibre
sudo docker compose up -d --no-deps geolibre
sudo docker compose ps
```

Visit Atlas in a private window, sign in, and click **Log out** at the top
right. It should open Cloudflare's logout endpoint; reloading Atlas requires
sign-in again. Cloudflare currently revokes the session across applications
in that Cloudflare Access team, not just Atlas. Check `/data/*` and
`/sidecar/*` after logout as well. Cloudflare may take 20–30 seconds to reject
already issued tokens.

## Rollback

Keep the old Caddyfile and `compose.yaml` backup before the cutover. If the
tunnel or login fails, restore Caddy's original site address and `basic_auth`,
validate/reload Caddy, restore its original port mappings and restart Caddy,
then change only the `atlas` DNS record back to the original A record. Do not
remove the Caddy password while the old A record or public port mappings are
active.

References: [Cloudflare self-hosted Access](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/self-hosted-public-app/),
[Cloudflare session logout](https://developers.cloudflare.com/cloudflare-one/access-controls/access-settings/session-management/),
[Cloudflare login branding](https://developers.cloudflare.com/cloudflare-one/reusable-components/custom-pages/access-login-page/).
