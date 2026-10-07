# Dependency audit decisions

Reviewed 2026-10-07 for the Nexorus Atlas Catalog branding release.
The audit still blocks unknown high/critical advisories and fails if the
registry does not return a usable report.

## Patched dependencies

- `@modelcontextprotocol/sdk`: 1.30.0 -> 1.31.0, pinned in the desktop
  workspace. This fixes [GHSA-6qxp-vccf-f47h](https://github.com/advisories/GHSA-6qxp-vccf-f47h).
- `proxy-addr`: 2.0.7 -> 2.0.8, pinned by a root override. This fixes
  [GHSA-jqcg-44mw-7w3h](https://github.com/advisories/GHSA-jqcg-44mw-7w3h).

## Unpatched dependencies outside the runtime graph

The following two advisory-specific exceptions meet the existing audit
policy: no published patched version and no reachable vulnerable runtime
path. They do not declare the packages fixed.

### braces 3.0.3 / GHSA-vfj7-8cjw-p6xm

[The advisory](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm) lists no fix.
The production lock graph includes it through the repository's install-time
`patch-package -> find-yarn-workspace-root -> micromatch` tooling, and through
`@osmix/geojson -> @placemarkio/geojson-rewind -> @changesets/cli`.
The published `@placemarkio/geojson-rewind` 1.0.3 geometry entry point
`dist/rewind.es.mjs` is self-contained and imports no Changesets or glob tools.
Install/release tooling operates on repository paths rather than dataset
input. Its dependency metadata does not describe the shipped browser graph.

### node-forge 1.4.0 / GHSA-86w9-cpqp-85rv

[The advisory](https://github.com/advisories/GHSA-86w9-cpqp-85rv) lists no fix.
It arrives through `@google/earthengine -> googleapis -> google-auth-library
-> gtoken -> google-p12-pem`. The locked Earth Engine 1.7.34 package declares
`build/browser.js` as its browser entry point. That published file has no
Node `googleapis` import; `build/main.js` does. Atlas's Earth Engine loader
uses the browser build and Google's browser OAuth flow. The Node P12 chain
is not shipped or executed by that flow. Additionally, google-p12-pem 3.1.4
converts a private P12 key to PEM and does not call the affected RSA signature
verification API.

## Enforced boundary

`reject-unpatched-runtime-dependencies.ts` is a Vite build plugin. It fails
the build if `braces` or `node-forge` enters the application module graph,
including nested dependency locations and Windows paths. Boundary tests
cover the permitted geometry/Earth Engine modules and prohibited packages.
The normal build, type checks and browser tests must also pass.

Reassess these exceptions when their parent dependencies or browser entry
points change. Remove them when patched versions become available; the audit
warns when an exception is no longer reported. A runtime dependency on either
package requires remediation before its exception can remain valid.
