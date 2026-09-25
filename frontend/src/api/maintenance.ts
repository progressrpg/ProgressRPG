// src/api/maintenance.ts
import { apiFetch } from "../utils/api";

export interface MaintenanceStatusApiResponse {
  maintenance_active: boolean;
  name?: string;
  description?: string;
  start_time?: string | null;
  end_time?: string | null;
}

export function fetchMaintenanceStatus(): Promise<MaintenanceStatusApiResponse> {
  return apiFetch<MaintenanceStatusApiResponse>("/maintenance_status/");
}
