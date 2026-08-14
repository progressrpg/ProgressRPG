import { act, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useEffect } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import MapPage from './MapPage';

const mockFetchInitialMapCentre = vi.fn();
const mockFetchPopulationCentreMap = vi.fn();
const mockFetchMapViewport = vi.fn();
const mockFetchMapWorldBounds = vi.fn();
const mockFetchPopulationCentres = vi.fn();

vi.mock('../../api/map', () => ({
  fetchInitialMapCentre: (...args: unknown[]) => mockFetchInitialMapCentre(...args),
  fetchPopulationCentreMap: (...args: unknown[]) => mockFetchPopulationCentreMap(...args),
  fetchMapViewport: (...args: unknown[]) => mockFetchMapViewport(...args),
  fetchMapWorldBounds: (...args: unknown[]) => mockFetchMapWorldBounds(...args),
  fetchPopulationCentres: (...args: unknown[]) => mockFetchPopulationCentres(...args),
}));

// Map.tsx owns a real MapLibre instance, which needs a WebGL context jsdom
// doesn't provide - out of scope for MapPage's own tests (Map.test.tsx
// covers MapLibre wiring with maplibre-gl mocked). This stub simulates the
// one behaviour MapPage depends on: once "mounted" (its camera has fitted
// an initial view), it reports a settled viewport bbox back up.
function MapStub({
  geojson,
  onViewportChange,
}: {
  geojson: { meta?: { population_centre_name?: string } } | null;
  onViewportChange?: (bbox: string) => void;
}) {
  useEffect(() => {
    onViewportChange?.('0,0,100,100');
    // Only fire once, mirroring the real component's one-time initial fit.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return <div data-testid="map-stub">{geojson?.meta?.population_centre_name}</div>;
}

vi.mock('../../components/Map/Map', () => ({
  default: MapStub,
}));

function renderMapPage(queryClient?: QueryClient) {
  const client = queryClient ?? new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={client}>
      <MapPage />
    </QueryClientProvider>
  );
}

describe('MapPage', () => {
  beforeEach(() => {
    mockFetchInitialMapCentre.mockReset();
    mockFetchPopulationCentreMap.mockReset();
    mockFetchMapViewport.mockReset();
    mockFetchMapWorldBounds.mockReset();
    mockFetchPopulationCentres.mockReset();
    mockFetchInitialMapCentre.mockResolvedValue({
      id: 1,
      name: 'Driftmoor',
      bbox: [0, 0, 100, 100],
    });
    mockFetchPopulationCentreMap.mockResolvedValue({
      meta: { population_centre_name: 'Driftmoor' },
      bbox: [0, 0, 100, 100],
    });
    mockFetchMapViewport.mockResolvedValue({ meta: { population_centre_name: 'Driftmoor' } });
    mockFetchMapWorldBounds.mockResolvedValue({ bbox: [-1000, -1000, 1000, 1000] });
    mockFetchPopulationCentres.mockResolvedValue([
      { id: 1, name: 'Driftmoor village', location: [0, 0] },
    ]);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders the map once the initial map centre has loaded', async () => {
    renderMapPage();

    expect(await screen.findByTestId('map-stub')).toHaveTextContent('Driftmoor');
  });

  it('reuses cached viewport data when the page is remounted within the cache window', async () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });

    const { unmount } = renderMapPage(queryClient);

    expect(await screen.findByTestId('map-stub')).toHaveTextContent('Driftmoor');
    await waitFor(() => {
      expect(mockFetchMapViewport).toHaveBeenCalledTimes(1);
    });

    unmount();
    renderMapPage(queryClient);

    expect(await screen.findByTestId('map-stub')).toHaveTextContent('Driftmoor');
    await waitFor(() => {
      expect(mockFetchMapViewport).toHaveBeenCalledTimes(1);
    });
  });

  it('prefetches the next village map data once the village list is available', async () => {
    mockFetchPopulationCentres.mockResolvedValue([
      { id: 1, name: 'Driftmoor village', location: [0, 0] },
      { id: 2, name: 'Cedar Hollow', location: [100, 100] },
    ]);

    renderMapPage();

    await waitFor(() => {
      expect(mockFetchPopulationCentreMap).toHaveBeenCalledTimes(2);
    });
  });

  it('does not issue a second viewport request while the previous poll is still in flight (#624)', async () => {
    vi.useFakeTimers();
    const pending: { resolve: (value: unknown) => void }[] = [];
    mockFetchMapViewport.mockImplementation(
      () =>
        new Promise((resolve) => {
          pending.push({ resolve });
        })
    );

    renderMapPage();

    // Flush the initial-centre fetch, then the stub's onViewportChange call,
    // so the first viewport fetch fires. This is a chain of several
    // dependent async hops (initial centre -> Map mounts -> onViewportChange
    // -> viewport query starts), each of which may need its own microtask
    // turn under fake timers, so flush repeatedly rather than assuming one
    // pass covers it.
    await act(async () => {
      await vi.runOnlyPendingTimersAsync();
    });
    await act(async () => {
      await vi.runOnlyPendingTimersAsync();
    });
    await act(async () => {
      await vi.runOnlyPendingTimersAsync();
    });
    expect(mockFetchMapViewport).toHaveBeenCalledTimes(1);

    // Advance past when a poll would normally re-fire. TanStack Query
    // deduplicates fetches for the same query key while one is already in
    // flight, so no second network call should go out until this one
    // settles - this is what makes the old manual-polling race (#624),
    // where a stale response could land after and overwrite a newer one,
    // structurally impossible here rather than something to guard against
    // after the fact.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });
    expect(mockFetchMapViewport).toHaveBeenCalledTimes(1);

    await act(async () => {
      pending[0].resolve({ meta: { population_centre_name: 'Driftmoor' } });
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(screen.getByTestId('map-stub').textContent).toBe('Driftmoor');

    // Now that the in-flight fetch has settled, the next interval tick is
    // free to fire a new one.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });
    expect(mockFetchMapViewport).toHaveBeenCalledTimes(2);
  });
});
