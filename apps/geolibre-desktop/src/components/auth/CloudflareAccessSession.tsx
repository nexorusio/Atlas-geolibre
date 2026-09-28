import { Button } from "@geolibre/ui";
import { LogOut } from "lucide-react";
import { createContext, useContext, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

const CloudflareAccessContext = createContext(false);

/**
 * The reverse proxy and Cloudflare Tunnel secure all paths before this UI loads.
 * This control merely navigates to Cloudflare's documented session revocation
 * endpoint. Do not render it as a substitute for server-side authorization.
 */
export function CloudflareAccessSession({ children }: { children: ReactNode }) {
  return <CloudflareAccessContext.Provider value={true}>{children}</CloudflareAccessContext.Provider>;
}

/** Render the sign-out action as part of the toolbar instead of covering its controls. */
export function CloudflareAccessLogoutLink() {
  const enabled = useContext(CloudflareAccessContext);
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

  if (!enabled) return null;

  return (
    <Button asChild size="sm" variant="ghost" className="h-7 shrink-0 px-2 text-muted-foreground">
      <a
        href="/cdn-cgi/access/logout"
        onClick={(event) => void signOut(event)}
        aria-label={t("auth.signOut")}
        title={t("auth.signOut")}
      >
        <LogOut aria-hidden="true" className="h-3.5 w-3.5" />
        <span className="hidden lg:inline">{t("auth.signOut")}</span>
      </a>
    </Button>
  );
}
