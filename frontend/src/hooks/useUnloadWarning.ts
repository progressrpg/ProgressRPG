// hooks/useUnloadWarning.ts
import { useEffect } from "react";

// Warns the user before closing/refreshing/navigating away from the tab
// while `active` is true. No-op when `window` isn't available (e.g. native).
export default function useUnloadWarning(active: boolean): void {
  useEffect(() => {
    if (!active) return;
    if (typeof window === "undefined") return;

    const handler = (e: BeforeUnloadEvent): void => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [active]);
}
