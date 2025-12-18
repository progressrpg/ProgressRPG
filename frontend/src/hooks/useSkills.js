// src/hooks/useSkills.js
import { useQuery } from "@tanstack/react-query";
import { fetchSkills } from "../api/skills";

export function useSkills() {
  return useQuery({
    queryKey: ["skills"],
    queryFn: fetchSkills,
  });
}
