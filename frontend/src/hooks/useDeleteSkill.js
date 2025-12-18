// src/hooks/useDeleteSkill.js
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { deleteSkill } from "../api/skills";

export function useDeleteSkill() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteSkill,
    onMutate: async (skillId) => {
      await queryClient.cancelQueries({ queryKey: ["skills"] });

      const previousSkills = queryClient.getQueryData(["skills"]);

      queryClient.setQueryData(["skills"], (old) =>
        old.filter((skill) => skill.id !== skillId)
      );

      return { previousSkills };
    },
    // Rollback on error
    onError: (err, skillId, context) => {
      if (context?.previousSkills) {
        queryClient.setQueryData(["skills"], context.previousSkills);
      }
    },
    // Ensure the cache is in sync with backend
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["skills"] });
    },
  });
}
