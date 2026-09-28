import type { ReactNode } from "react";
import "./nexorus-auth.css";

interface NexorusAuthShellProps {
  children: ReactNode;
  alert?: boolean;
}

/** Shared Nexorus presentation around GeoLibre's existing sign-in providers. */
export function NexorusAuthShell({ children, alert = false }: NexorusAuthShellProps) {
  return (
    <main className="nexorus-auth" {...(alert ? { role: "alert" } : {})}>
      <section className="nexorus-auth__panel" aria-label="Nexorus Atlas">
        <div className="nexorus-auth__brand">
          <img
            src={`${import.meta.env.BASE_URL}nexorus-wordmark.png`}
            alt="Nexorus"
            className="nexorus-auth__logo"
          />
          <span className="nexorus-auth__product">ATLAS</span>
        </div>
        <div className="nexorus-auth__content">{children}</div>
      </section>
    </main>
  );
}
