import { useCallback, useState } from "react";
import type { UseMutationResult, UseQueryResult } from "@tanstack/react-query";

import { asArray } from "../utils/arrayUtils";

interface Entity {
  id: number;
  name: string;
}

interface SaveCallbacks {
  onSuccess?: () => void;
  onError?: () => void;
}

interface UseSimpleCrudPanelOptions<T extends Entity> {
  useList: () => Pick<UseQueryResult<T[]>, "data" | "isLoading">;
  useCreate: () => Pick<UseMutationResult<unknown, unknown, Partial<T>>, "mutate">;
  useUpdate: () => Pick<UseMutationResult<unknown, unknown, { id: number; data: Partial<T> }>, "mutate">;
  useDelete: () => Pick<UseMutationResult<unknown, unknown, number>, "mutate">;
}

export function useSimpleCrudPanel<T extends Entity>({
  useList,
  useCreate,
  useUpdate,
  useDelete,
}: UseSimpleCrudPanelOptions<T>) {
  const { data, isLoading } = useList();
  const create = useCreate();
  const update = useUpdate();
  const del = useDelete();

  const [newName, setNewName] = useState("");
  const items = asArray(data);

  const handleCreate = useCallback(
    (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      const trimmedName = newName.trim();
      if (!trimmedName) return;
      create.mutate({ name: trimmedName } as Partial<T>);
      setNewName("");
    },
    [create, newName],
  );

  const handleEdit = useCallback(
    (item: T, name: string, callbacks?: SaveCallbacks) => {
      update.mutate({ id: item.id, data: { name } as Partial<T> }, callbacks);
    },
    [update],
  );

  const handleDelete = useCallback(
    (item: T) => {
      del.mutate(item.id);
    },
    [del],
  );

  return { isLoading, items, newName, setNewName, handleCreate, handleEdit, handleDelete, update };
}
