import { LogOut } from "lucide-react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

/**
 * The reverse proxy and Cloudflare Tunnel secure all paths before this UI loads.
 * This control merely navigates to Cloudflare's documented session revocation
 * endpoint. Do not render it as a substitute for server-side authorization.
 */
export function CloudflareAccessSession({ children }: { children: ReactNode }) {
  const { t } = useTranslation();

  async function signOut(event: React.MouseEvent<HTMLAnchorElement>) {
    event.preventDefault();
    // An older GeoLibre PWA worker may still intercept the logout navigation
    // and return its cached index.html. Retire workers and offline caches for
    // this dedicated Atlas origin before asking Cloudflare to revoke access.
    try {
      if ("serviceWorker" in navigator) {
        const registrations = await navigator.serviceWorker.getRegistrations();
        await Promise.all(registrations.map((registration) => registration.unregister()));
      }
      if ("caches" in window) {
        const keys = await caches.keys();
        await Promise.all(keys.map((key) => caches.delete(key)));
      }
    } catch (error) {
      console.warn("Could not clear Atlas offline cache before sign-out", error);
    } finally {
      window.location.assign("/cdn-cgi/access/logout");
    }
  }

  return (
    <>
      {children}
      <a
        href="/cdn-cgi/access/logout"
        onClick={(event) => void signOut(event)}
        className="fixed end-3 top-2 z-[100] inline-flex h-9 items-center gap-2 rounded-lg border border-[#50658f] bg-[#0c2245] px-3 text-sm font-medium text-white shadow-lg hover:bg-[#183969] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#a9bbff]"
      >
        <LogOut aria-hidden="true" className="h-4 w-4" />
        {t("auth.signOut")}
      </a>
    </>
  );
}
