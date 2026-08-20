import { act, renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { useSimpleCrudPanel } from "./useSimpleCrudPanel";

interface Item {
  id: number;
  name: string;
}

function setup(items: Item[] = [{ id: 1, name: "First" }]) {
  const createMutate = vi.fn();
  const updateMutate = vi.fn();
  const deleteMutate = vi.fn();

  const { result } = renderHook(() =>
    useSimpleCrudPanel<Item>({
      useList: () => ({ data: items, isLoading: false }),
      useCreate: () => ({ mutate: createMutate }),
      useUpdate: () => ({ mutate: updateMutate }),
      useDelete: () => ({ mutate: deleteMutate }),
    })
  );

  return { result, createMutate, updateMutate, deleteMutate };
}

describe("useSimpleCrudPanel", () => {
  it("exposes the list items via asArray", () => {
    const { result } = setup();
    expect(result.current.items).toEqual([{ id: 1, name: "First" }]);
  });

  it("falls back to an empty array when the list data is undefined", () => {
    const { result } = renderHook(() =>
      useSimpleCrudPanel<Item>({
        useList: () => ({ data: undefined, isLoading: true }),
        useCreate: () => ({ mutate: vi.fn() }),
        useUpdate: () => ({ mutate: vi.fn() }),
        useDelete: () => ({ mutate: vi.fn() }),
      })
    );
    expect(result.current.items).toEqual([]);
    expect(result.current.isLoading).toBe(true);
  });

  it("creates a trimmed item and resets the name field", () => {
    const { result, createMutate } = setup();

    act(() => {
      result.current.setNewName("  New item  ");
    });

    const preventDefault = vi.fn();
    act(() => {
      result.current.handleCreate({ preventDefault } as unknown as React.FormEvent<HTMLFormElement>);
    });

    expect(preventDefault).toHaveBeenCalled();
    expect(createMutate).toHaveBeenCalledWith({ name: "New item" });
    expect(result.current.newName).toBe("");
  });

  it("does not create when the trimmed name is empty", () => {
    const { result, createMutate } = setup();

    act(() => {
      result.current.setNewName("   ");
    });

    act(() => {
      result.current.handleCreate({ preventDefault: vi.fn() } as unknown as React.FormEvent<HTMLFormElement>);
    });

    expect(createMutate).not.toHaveBeenCalled();
  });

  it("edits an item, passing along optional callbacks", () => {
    const { result, updateMutate } = setup();
    const callbacks = { onSuccess: vi.fn() };

    act(() => {
      result.current.handleEdit({ id: 1, name: "First" }, "Renamed", callbacks);
    });

    expect(updateMutate).toHaveBeenCalledWith({ id: 1, data: { name: "Renamed" } }, callbacks);
  });

  it("deletes an item by id", () => {
    const { result, deleteMutate } = setup();

    act(() => {
      result.current.handleDelete({ id: 1, name: "First" });
    });

    expect(deleteMutate).toHaveBeenCalledWith(1);
  });
});
