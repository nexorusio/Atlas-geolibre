import type { Plugin } from "vite";

// Audit exceptions are valid only while these packages stay outside runtime
// bundles. Build tools can use them; application modules must not import them.
export function assertNoUnpatchedRuntimeDependencies(ids: Iterable<string>): void {
  for (const id of ids) {
    const normalized = id.replaceAll("\\", "/");
    if (/\/node_modules\/(braces|node-forge)(?:\/|$)/.test(normalized)) {
      throw new Error(
        `Unpatched dependency entered the runtime bundle: ${id}. ` +
          "Resolve its advisory and remove the corresponding audit exception.",
      );
    }
  }
}

export function rejectUnpatchedRuntimeDependencies(): Plugin {
  return {
    name: "reject-unpatched-runtime-dependencies",
    apply: "build",
    generateBundle() {
      assertNoUnpatchedRuntimeDependencies(this.getModuleIds());
    },
  };
}
