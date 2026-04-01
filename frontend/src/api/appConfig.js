import { apiFetch } from "../../utils/api";

export async function fetchAppConfig() {
  return apiFetch("/app_config/");
}
