// hooks/useMaintenanceStatus.js
import { useMaintenanceContext } from '../context/MaintenanceContext';
import { useCallback } from 'react';
import { apiFetch } from "../utils/api";

export function useMaintenanceStatus() {
  const { maintenance, setMaintenance } = useMaintenanceContext();

  const fetchMaintenance = useCallback(async () => {
    try {
      const data = await apiFetch('/maintenance_status/');
      if (data.maintenance_active) {
        const payload = {
          active: true,
          details: {
            name: data.name,
            description: data.description,
            startTime: data.start_time,
            endTime: data.end_time,
          },
        };
        setMaintenance(payload);
        return payload;
      } else {
        setMaintenance({ active: false, details: null });
        return { active: false, details: null };
      }
    } catch (error) {
      console.error('Error fetching maintenance status:', error);
      setMaintenance({ active: false, details: null });
      return { active: false, details: null };
    }
  }, [setMaintenance]);

  return { ...maintenance, refetch: fetchMaintenance };
}
