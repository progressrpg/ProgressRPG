import { afterEach, describe, expect, it, vi } from "vitest";

import {
  fetchInitialMapCentre,
  fetchMapCharacterDetail,
  fetchMapViewport,
  fetchMapWorldBounds,
  fetchPopulationCentreMap,
  fetchPopulationCentres,
} from "./map";
import { apiFetch } from "../utils/api";

vi.mock("../utils/api", () => ({
  apiFetch: vi.fn(),
}));

const mockedApiFetch = apiFetch as ReturnType<typeof vi.fn>;

afterEach(() => {
  vi.clearAllMocks();
});

describe("fetchInitialMapCentre", () => {
  it("fetches the initial map centre", async () => {
    const centre = { id: 1, name: "Village", bbox: [0, 0, 1, 1] };
    mockedApiFetch.mockResolvedValueOnce(centre);

    const result = await fetchInitialMapCentre();

    expect(mockedApiFetch).toHaveBeenCalledWith("/map/initial-centre/");
    expect(result).toBe(centre);
  });
});

describe("fetchPopulationCentres", () => {
  it("unwraps a paginated {results} response", async () => {
    const centres = [{ id: 1, name: "A", location: [1, 2] }];
    mockedApiFetch.mockResolvedValueOnce({ results: centres });

    const result = await fetchPopulationCentres();

    expect(result).toEqual(centres);
  });

  it("accepts a bare array response", async () => {
    const centres = [{ id: 1, name: "A", location: [1, 2] }];
    mockedApiFetch.mockResolvedValueOnce(centres);

    const result = await fetchPopulationCentres();

    expect(result).toEqual(centres);
  });

  it("filters out centres with a missing location", async () => {
    mockedApiFetch.mockResolvedValueOnce({
      results: [
        { id: 1, name: "Valid", location: [1, 2] },
        { id: 2, name: "NoLocation" },
      ],
    });

    const result = await fetchPopulationCentres();

    expect(result).toEqual([{ id: 1, name: "Valid", location: [1, 2] }]);
  });

  it("filters out centres with a malformed location array", async () => {
    mockedApiFetch.mockResolvedValueOnce({
      results: [
        { id: 1, name: "Valid", location: [1, 2] },
        { id: 2, name: "TooShort", location: [1] },
        { id: 3, name: "NonNumeric", location: [1, "y"] },
        { id: 4, name: "NonFinite", location: [1, Infinity] },
      ],
    });

    const result = await fetchPopulationCentres();

    expect(result).toEqual([{ id: 1, name: "Valid", location: [1, 2] }]);
  });

  it("returns an empty array when the response has no results", async () => {
    mockedApiFetch.mockResolvedValueOnce({});

    const result = await fetchPopulationCentres();

    expect(result).toEqual([]);
  });
});

describe("fetchPopulationCentreMap", () => {
  it("fetches map data for a population centre by id", async () => {
    const data = { type: "FeatureCollection", features: [] };
    mockedApiFetch.mockResolvedValueOnce(data);

    const result = await fetchPopulationCentreMap(42);

    expect(mockedApiFetch).toHaveBeenCalledWith("/population-centres/42/map/");
    expect(result).toBe(data);
  });
});

describe("fetchMapViewport", () => {
  it("URL-encodes the bbox query param", async () => {
    const data = { type: "FeatureCollection", features: [] };
    mockedApiFetch.mockResolvedValueOnce(data);

    const result = await fetchMapViewport("0,0,100,100");

    expect(mockedApiFetch).toHaveBeenCalledWith("/map/viewport/?bbox=0%2C0%2C100%2C100");
    expect(result).toBe(data);
  });
});

describe("fetchMapCharacterDetail", () => {
  it("fetches character detail by id", async () => {
    const detail = { id: 7, name: "Someone" };
    mockedApiFetch.mockResolvedValueOnce(detail);

    const result = await fetchMapCharacterDetail(7);

    expect(mockedApiFetch).toHaveBeenCalledWith("/map/characters/7/");
    expect(result).toBe(detail);
  });
});

describe("fetchMapWorldBounds", () => {
  it("fetches the world bounds", async () => {
    const bounds = { bbox: [0, 0, 1, 1] };
    mockedApiFetch.mockResolvedValueOnce(bounds);

    const result = await fetchMapWorldBounds();

    expect(mockedApiFetch).toHaveBeenCalledWith("/map/world-bounds/");
    expect(result).toBe(bounds);
  });
});
