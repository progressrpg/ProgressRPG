import { useQuery } from "@tanstack/react-query";
import { fetchAppConfig } from "../api/appConfig";

export function useAppConfig() {
  return useQuery({
    queryKey: ["appConfig"],
    queryFn: fetchAppConfig,
    staleTime: 5 * 60 * 1000,
  });
}
