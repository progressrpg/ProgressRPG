// src/hooks/useSkills.js

import { useMutation, useQueryClient, useQuery } from "@tanstack/react-query";
import { updateSkill, deleteSkill, fetchSkills, createSkill } from "../api/skills";


export function useSkills() {
  return useQuery({
    queryKey: ["skills"],
    queryFn: fetchSkills,
  });
}


export function useCreateSkill() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createSkill,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["skills"] });
    },
  });
}


export function useUpdateSkill() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }) => updateSkill(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["skills"] });
    },
  });
}

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
