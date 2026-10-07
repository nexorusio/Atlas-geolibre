import assert from "node:assert/strict";
import test from "node:test";
import { assertNoUnpatchedRuntimeDependencies } from "../apps/geolibre-desktop/vite-plugins/reject-unpatched-runtime-dependencies.ts";

test("browser geometry and Earth Engine modules stay available", () => {
  assert.doesNotThrow(() =>
    assertNoUnpatchedRuntimeDependencies([
      "/atlas/node_modules/@placemarkio/geojson-rewind/dist/rewind.es.mjs",
      "/atlas/node_modules/@google/earthengine/build/browser.js",
      "/atlas/apps/geolibre-desktop/src/App.tsx",
    ]),
  );
});

test("unpatched packages cannot enter web artifacts through hoisted or nested dependencies", () => {
  for (const id of [
    "/atlas/node_modules/braces/index.js",
    "/atlas/node_modules/google-p12-pem/node_modules/node-forge/lib/rsa.js",
    "/atlas/node_modules/.pnpm/braces@3.0.3/node_modules/braces/lib/parse.js",
    "C:\\atlas\\node_modules\\node-forge\\lib\\rsa.js",
  ]) {
    assert.throws(() => assertNoUnpatchedRuntimeDependencies([id]), /Unpatched dependency/);
  }
});
