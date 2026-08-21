import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  useInitialMapCentre,
  useMapCharacterDetail,
  useMapViewport,
  useMapWorldBounds,
  usePopulationCentres,
  useTargetCentreMap,
} from "./useMap";

const mockFetchInitialMapCentre = vi.fn();
const mockFetchMapCharacterDetail = vi.fn();
const mockFetchMapViewport = vi.fn();
const mockFetchMapWorldBounds = vi.fn();
const mockFetchPopulationCentreMap = vi.fn();
const mockFetchPopulationCentres = vi.fn();

vi.mock("../api/map", () => ({
  fetchInitialMapCentre: (...args: unknown[]) => mockFetchInitialMapCentre(...args),
  fetchMapCharacterDetail: (...args: unknown[]) => mockFetchMapCharacterDetail(...args),
  fetchMapViewport: (...args: unknown[]) => mockFetchMapViewport(...args),
  fetchMapWorldBounds: (...args: unknown[]) => mockFetchMapWorldBounds(...args),
  fetchPopulationCentreMap: (...args: unknown[]) => mockFetchPopulationCentreMap(...args),
  fetchPopulationCentres: (...args: unknown[]) => mockFetchPopulationCentres(...args),
}));

function makeWrapper() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  return wrapper;
}

describe("useMap", () => {
  beforeEach(() => {
    mockFetchInitialMapCentre.mockReset();
    mockFetchMapCharacterDetail.mockReset();
    mockFetchMapViewport.mockReset();
    mockFetchMapWorldBounds.mockReset();
    mockFetchPopulationCentreMap.mockReset();
    mockFetchPopulationCentres.mockReset();
  });

  it("fetches the initial map centre", async () => {
    mockFetchInitialMapCentre.mockResolvedValue({ id: 1 });
    const wrapper = makeWrapper();

    const { result } = renderHook(() => useInitialMapCentre(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual({ id: 1 });
  });

  it("fetches world bounds", async () => {
    mockFetchMapWorldBounds.mockResolvedValue({ bbox: "0,0,1,1" });
    const wrapper = makeWrapper();

    const { result } = renderHook(() => useMapWorldBounds(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual({ bbox: "0,0,1,1" });
  });

  it("fetches all population centres", async () => {
    mockFetchPopulationCentres.mockResolvedValue([{ id: 1 }]);
    const wrapper = makeWrapper();

    const { result } = renderHook(() => usePopulationCentres(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual([{ id: 1 }]);
  });

  it("does not fetch the target centre map when centreId is null", () => {
    const wrapper = makeWrapper();
    renderHook(() => useTargetCentreMap(null), { wrapper });
    expect(mockFetchPopulationCentreMap).not.toHaveBeenCalled();
  });

  it("fetches the target centre map when centreId is provided", async () => {
    mockFetchPopulationCentreMap.mockResolvedValue({ id: 5 });
    const wrapper = makeWrapper();

    const { result } = renderHook(() => useTargetCentreMap(5), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockFetchPopulationCentreMap).toHaveBeenCalledWith(5);
  });

  it("does not fetch the map viewport when bbox is null", () => {
    const wrapper = makeWrapper();
    renderHook(() => useMapViewport(null), { wrapper });
    expect(mockFetchMapViewport).not.toHaveBeenCalled();
  });

  it("fetches the map viewport when bbox is provided", async () => {
    mockFetchMapViewport.mockResolvedValue({ characters: [] });
    const wrapper = makeWrapper();

    const { result } = renderHook(() => useMapViewport("0,0,1,1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockFetchMapViewport).toHaveBeenCalledWith("0,0,1,1");
  });

  it("does not fetch character detail when characterId is null", () => {
    const wrapper = makeWrapper();
    renderHook(() => useMapCharacterDetail(null), { wrapper });
    expect(mockFetchMapCharacterDetail).not.toHaveBeenCalled();
  });

  it("fetches character detail when characterId is provided", async () => {
    mockFetchMapCharacterDetail.mockResolvedValue({ id: 9 });
    const wrapper = makeWrapper();

    const { result } = renderHook(() => useMapCharacterDetail(9), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockFetchMapCharacterDetail).toHaveBeenCalledWith(9);
  });
});
