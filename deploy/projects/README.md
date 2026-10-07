# Retain GeoLibre projects alongside an existing GeoLens catalog

This additive deployment connects the native Share/Gallery project workflow to
a PostgreSQL database and persistent project objects. The existing Atlas web
service remains the main map canvas. GeoLens remains the dataset catalog; its
API is also reachable through the Atlas origin so the built-in plugin can read
layers and write authorized feature edits without a second browser origin.

It does not deploy GeoServer, add automatic server autosave, or replace the
existing Cloudflare tunnel or Access policy. Shared application SSO is a later
change: email OTP at the proxy does not create a native project or GeoLens
identity. This version uses each person's project account and GeoLens API key.

## Persistence and permissions

| Item | Retained by | How it is saved |
| --- | --- | --- |
| Project JSON, embedded data, map settings, styles and layout serialized by GeoLibre | Native projects API: `projects_pgdata` and `projects_objects` | Share, then reopen in Gallery and save later revisions |
| Browser's unsaved workspace/history | Browser IndexedDB | Local autosave; it is not a server backup |
| Catalog vectors and managed rasters | Existing GeoLens PostgreSQL and managed object volume | GeoLens imports; permitted feature edits through its API |
| New analysis output created in GeoLibre | Project JSON if embedded; GeoLens after explicit import | Save the project and export/import a reusable dataset |
| External layer URLs | Their original source | Project saving does not copy every referenced service or file |

The project database is separate from the GeoLens database. The three new
services have memory ceilings of 512 MiB (database), 512 MiB (API), and 64 MiB
(gateway). These are initial bounds, not a performance guarantee; measure real
imports and saves on the existing host before resizing it.

Project objects use a named volume at `/data/objects`; the existing API image
initializes that path for uid/gid 1000. No recursive ownership changes are made
to existing Atlas or GeoLens data. Do not run `docker compose down -v` on a
deployed stack. Public/unlisted projects still mean what native GeoLibre defines:
use **private** for individual work and organization/group permissions for team
work. Cloudflare Access must cover the Atlas host, including `/projects`, `/api`
and the OAuth callback/discovery paths.

## Before deployment

Run every host command yourself. Record running image tags/digests, free disk
and available RAM. Preserve private copies of the existing compose files,
environment files, Caddyfile, and tunnel settings. Make a current GeoLens
database/managed-object backup and preserve the existing Atlas data/work paths.
Verify those backups before changing routing. Do not paste raw compose output,
`.env` files, tunnel tokens or application credentials into a PR or chat.

Confirm that:

- The Atlas compose service is `geolibre`, with Caddy on an existing Docker network.
- The catalog frontend is on that same network with alias `atlas-geolens-catalog`.
- `127.0.0.1:18001` is unused.
- Both `projects-sha-<full-merge-commit>` and `web-sha-<full-merge-commit>` images
  have finished publishing in the existing GHCR package. A merged PR alone does
  not mean those images exist. Pull both before changing any running service.

The projects publisher builds and tests linux/amd64, matching this deployment's
host. Do not use that image on an ARM host without adding an ARM build/test.

## Deploy in short steps

1. Check out the merged commit, or download this `deploy/projects` directory
   from that exact commit, into a separate directory. Keep the existing Atlas
   and GeoLens directories intact. All following project commands run from the
   new directory; they do not use the repository's root compose example.

2. Create the new private environment once:

   ```sh
   python3 configure.py --origin https://atlas.example --network EXISTING_CADDY_NETWORK --image ghcr.io/OWNER/REPOSITORY:projects-sha-FULL_MERGE_COMMIT
   ```

   Replace the example origin, network and image. The matching `web-sha` image is
   selected automatically. For a different image scheme, pass `--web-image`.
   The script generates a URL-safe database password in a mode-600 `.env` and
   refuses to overwrite it. Never regenerate that password against an existing
   database volume; later upgrades only change the image entries in `.env`.

3. Pull the project image, validate without printing secrets, and start it:

   ```sh
   docker compose config --quiet
   docker compose pull
   docker compose up -d --wait
   docker compose ps
   ```

   The API's loopback port is for operator account provisioning. The database
   has no host port; Caddy reaches the gateway through the existing network.

4. Create an account for each staff member, choosing their own username and
   password. The helper prompts privately and discards its one-day bootstrap
   PAT; no shared browser token is distributed:

   ```sh
   python3 create-account.py
   ```

5. Add the contents of `Caddyfile.routes` inside the existing Atlas host block,
   before its catch-all `handle`. Preserve the `/data/*` handler and the catalog
   host block. Replace `catalog.example` in the dataset-details redirect with
   the existing catalog's HTTPS hostname. Validate with Caddy before
   reloading/recreating its container.
   Requests to `/projects/*` reach the native API after stripping the prefix;
   OAuth discovery has its own RFC 8414 path. Requests to `/api/*` reach the
   existing catalog frontend's GeoLens proxy.
   Dataset-detail navigation redirects to that catalog UI; `/` stays Atlas.

6. Combine `atlas.override.yaml` with the existing Atlas compose configuration.
   Supply **both** the existing environment file (if there is one) and the new
   projects `.env`; the latter adds settings without dropping existing tokens.
   Keep every existing compose override that the deployment already uses.
   Validate with `config --quiet`, pull the new `geolibre` image, and recreate
   only `geolibre`. This sets `GEOLIBRE_SHARE_URL` to the Atlas `/projects` URL
   and `GEOLIBRE_GEOLENS_URL` to the Atlas origin. It does not alter GeoLens's
   catalog image or database.

## Required acceptance checks

1. Open Atlas and confirm the main canvas, existing `/data` links and separate
   catalog still work. In Share or Gallery, sign in with the project account.
2. Create a small map containing styles and a layout. Share it as **private**.
   Reopen it through Gallery → My projects in another browser/device, signing
   in as the same user. Check the map and layout, edit it, and save a second
   version. Another account must not be able to open the private URL.
3. Recreate `projects-api` **and** `projects-gateway` and repeat the reopen check.
   Recreate both together on upgrades so nginx resolves the current API address.
4. In the built-in GeoLens plugin, use the **Atlas origin**, not `/projects` or
   `localhost`. Existing saved plugin settings can override a changed default;
   update the connection if it still points to the catalog origin. Use that
   person's GeoLens API key for private layers and enabled feature editing.
   Verify vector and raster loading and one permitted vector edit in GeoLens.
5. Export one new analysis result from GeoLibre, import it into GeoLens, then
   load the retained dataset back through the plugin. A project save does not
   automatically create a new GeoLens dataset. Project exports omit credentials;
   a reopened private catalog layer needs the new user's own authorization.

The CI test verifies actual Caddy/nginx routing, native PKCE sign-in, private
ownership, two project revisions, container reconstruction and an isolated
PostgreSQL/object restore. Its catalog fixture verifies the proxy destination
and HTTPS forwarding; actual GeoLens layer rendering/editing still requires the
host acceptance checks above.

## Backup and rollback

Run from this directory, with a new absolute backup directory:

```sh
sh backup.sh /ABSOLUTE/BACKUP/projects-YYYYMMDD-HHMM
```

This briefly stops the project API/gateway, takes a custom-format PostgreSQL
dump and the matching project-object archive, copies private configuration, and
restarts the services even on failure. It does not back up GeoLens or existing
Atlas files. Copy the backup off-host and test restore in an isolated stack
before treating it as disaster recovery.

For an isolated restore: use a different compose project name, a separate proxy
network, and a different loopback API port; start only the fresh database,
restore `projects.dump` using `pg_restore --exit-on-error`, extract `objects.tar`
into the fresh objects volume as uid/gid 1000, then start API/gateway. Keep the
saved environment's database password consistent with the restored stack.
`tests/container_smoke.py` demonstrates and verifies this process on disposable
CI volumes. **Do not run that CI script against production.**

To roll back routing, restore the saved Caddyfile and original Atlas compose
configuration/image, and recreate the original affected services. Stop this
new project stack without removing its volumes. Existing GeoLens/Atlas data
stays in its original locations, and saved project data remains available for
recovery. GeoServer, shared SSO and full off-host recovery are subsequent stages.
