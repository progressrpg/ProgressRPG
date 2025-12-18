// src/hooks/useCreateSkill.js
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createSkill } from "../api/skills";

export function useCreateSkill() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createSkill,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["skills"] });
    },
  });
}
