// src/api/gameData.ts
import type { FetchInfoResponse } from "../types";
import { apiFetch } from "../utils/api";

/** The bootstrap payload: player/character/timer/login-state/settings state. */
export function fetchInfo(): Promise<FetchInfoResponse> {
  return apiFetch<FetchInfoResponse>("/fetch_info/");
}
