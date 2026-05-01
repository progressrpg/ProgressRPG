// components/MaintenanceWatcher.jsx
import { useEffect, useRef } from "react";
import { useNavigate, Navigate, useLocation } from "react-router-dom";
import { useMaintenanceContext } from "../context/MaintenanceContext";

export default function MaintenanceWatcher() {
  const { maintenance, setMaintenance } = useMaintenanceContext();
  const navigate = useNavigate();
  const location = useLocation();

  const wasActiveRef = useRef(false);
  const timeoutRef = useRef(null);

  useEffect(() => {
    if (maintenance.active && !wasActiveRef.current) {
      // store previous location
      const previous = location.pathname;
      setMaintenance((prev) => ({
        ...prev,
        previousLocation: previous,
        justEnded: false,
      }));
    }

    // When maintenance ends: set justEnded in context and optionally auto-redirect back
    if (!maintenance.active && wasActiveRef.current) {
      // maintenance just ended
      setMaintenance((prev) => ({ ...prev, justEnded: true }));

      if (timeoutRef.current) clearTimeout(timeoutRef.current);

      timeoutRef.current = setTimeout(() => {
        const returnTo = (
          maintenance.previousLocation &&
          maintenance.previousLocation !== "/ maintenance"
        )
          ? maintenance.previousLocation
          : "/timer";

          // clear justEnded and previousLocation
        setMaintenance((prev) => ({ ...prev, justEnded: false, previousLocation: null }));

        // only navigate if we're still on the maintenance page
        if (
          window.location.pathname === "/maintenance" ||
          window.location.pathname === "/maintenance/"
        ) {
          navigate(returnTo, { replace: true });
        }
      }, 10000);
    }

    wasActiveRef.current = maintenance.active;

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
    };
  }, [maintenance.active, location.pathname, navigate, setMaintenance, maintenance.previousLocation]);

  // Now all hooks are called, conditional rendering comes after
  return maintenance.active &&
    location.pathname !== "/maintenance" &&
    location.pathname !== "/maintenance/"
    ? <Navigate to="/maintenance" replace />
    : null;
}
