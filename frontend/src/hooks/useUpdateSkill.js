// src/hooks/useUpdateSkill.js
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { updateSkill } from "../api/skills";

export function useUpdateSkill() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }) => updateSkill(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["skills"] });
    },
  });
}
