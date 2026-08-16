// src/api/auth.ts
import type { TokenPair } from "../types";
import { apiFetch } from "../utils/api";

/**
 * Logs in with a username/password pair. Unauthenticated by design: the
 * request must not go through the getValidAccessToken() refresh path (there
 * is no session yet to refresh), and a rejected login (401) is a normal
 * "wrong credentials" outcome, not a dead session — see apiFetch's skipAuth
 * option.
 */
export const loginUser = async (username: string, password: string): Promise<TokenPair> => {
  return apiFetch<TokenPair>("/auth/jwt/create/", {
    method: "POST",
    body: JSON.stringify({ username, password }),
    skipAuth: true,
  });
};
