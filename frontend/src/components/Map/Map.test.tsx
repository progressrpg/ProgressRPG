import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ComponentProps } from 'react';
import { fromLngLat, toLngLat } from './utils';
import { colourForCharacter } from './characters/placement';

// MapLibre needs a real WebGL context, which jsdom doesn't provide - these
// fakes stand in for just enough of the maplibre-gl API surface for Map.tsx
// to wire itself up, so its own logic (scatter placement, walker
// interpolation, tooltip content, feature styling) can be exercised the
// same way it would be against a real map. `load` fires synchronously on
// registration (real MapLibre fires it async once its style/tiles are
// ready) so tests don't need to flush extra microtasks/timers to see the
// component's post-load state.
class FakeGeoJSONSource {
  data: unknown = { type: 'FeatureCollection', features: [] };
  setData(data: unknown) {
    this.data = data;
  }
}

class FakeMap {
  static instances: FakeMap[] = [];
  container: HTMLElement;
  sources = new Map<string, FakeGeoJSONSource>();
  images = new Map<string, unknown>();
  layers: { id: string }[] = [];
  handlers = new Map<string, { layerId?: string; handler: (e?: unknown) => void }[]>();
  fitBoundsCalls: unknown[] = [];

  constructor(options: { container: HTMLElement }) {
    this.container = options.container;
    FakeMap.instances.push(this);
  }

  addControl() {
    return this;
  }

  addSource(id: string) {
    this.sources.set(id, new FakeGeoJSONSource());
  }

  hasImage(id: string) {
    return this.images.has(id);
  }

  addImage(id: string, image: unknown) {
    this.images.set(id, image);
  }

  getSource(id: string) {
    return this.sources.get(id);
  }

  addLayer(layer: { id: string }) {
    this.layers.push(layer);
  }

  on(event: string, a: string | ((e?: unknown) => void), b?: (e?: unknown) => void) {
    const layerId = typeof a === 'string' ? a : undefined;
    const handler = typeof a === 'string' ? (b as (e?: unknown) => void) : a;
    const list = this.handlers.get(event) ?? [];
    list.push({ layerId, handler });
    this.handlers.set(event, list);
    if (event === 'load') handler();
  }

  off() {
    // Not exercised by these tests - move listeners are cleaned up per
    // tooltip open/close, which no test currently asserts on directly.
  }

  // Layer-scoped triggers only fire handlers registered for that exact
  // layer (mirroring `map.on(event, layerId, handler)`); a triggered event
  // with no layerId only fires map-wide handlers (`map.on(event, handler)`).
  // Real MapLibre would fire both for a click that hits a feature, using
  // queryRenderedFeatures to decide - these tests only need the layer-scoped
  // path, so the map-wide "click on empty space closes the tooltip" handler
  // (registered via the layerId-less overload) is exercised separately, not
  // implicitly by every layer click.
  trigger(event: string, payload?: unknown, layerId?: string) {
    for (const entry of this.handlers.get(event) ?? []) {
      if (entry.layerId === layerId) entry.handler(payload);
    }
  }

  fitBounds(bounds: unknown, options: unknown) {
    this.fitBoundsCalls.push({ bounds, options });
  }

  maxBoundsCalls: unknown[] = [];
  setMaxBounds(bounds: unknown) {
    this.maxBoundsCalls.push(bounds);
  }

  getBounds() {
    return { getWest: () => 0, getSouth: () => 0, getEast: () => 1, getNorth: () => 1 };
  }

  getCanvas() {
    return { style: {} as CSSStyleDeclaration };
  }

  queryRenderedFeatures() {
    return [];
  }

  project([lng, lat]: [number, number]) {
    return { x: lng, y: lat };
  }

  remove() {
    // no-op
  }
}

class FakeMarker {
  static instances: FakeMarker[] = [];
  element: HTMLElement;
  lngLat: [number, number] | null = null;
  private map: FakeMap | null = null;

  constructor(options: { element: HTMLElement }) {
    this.element = options.element;
    FakeMarker.instances.push(this);
  }

  setLngLat(lngLat: [number, number]) {
    this.lngLat = lngLat;
    return this;
  }

  addTo(map: FakeMap) {
    this.map = map;
    map.container.appendChild(this.element);
    return this;
  }

  remove() {
    this.map?.container.removeChild(this.element);
    return this;
  }

  // Convenience for assertions: the marker's position back in raw GIS units.
  get gisPosition(): [number, number] | null {
    return this.lngLat ? fromLngLat(this.lngLat) : null;
  }
}

class FakeNavigationControl {}
class FakeLngLatBounds {
  constructor(
    public sw: [number, number],
    public ne: [number, number]
  ) {}
}

vi.mock('maplibre-gl', () => ({
  Map: FakeMap,
  Marker: FakeMarker,
  NavigationControl: FakeNavigationControl,
  LngLatBounds: FakeLngLatBounds,
  setWorkerUrl: vi.fn(),
}));

// Imported after the mock so Map.tsx picks up the faked maplibre-gl module.
const { default: PopulationCentreMap } = await import('./Map');
const { TooltipProvider } = await import('../Tooltip/Tooltip');

function currentMap(): FakeMap {
  return FakeMap.instances[FakeMap.instances.length - 1];
}

function villageSourceFeatures(): { properties: Record<string, unknown> }[] {
  const data = currentMap().getSource('village')?.data as
    | { features?: { properties: Record<string, unknown> }[] }
    | undefined;
  return data?.features ?? [];
}

function characterMarkers(): { element: HTMLElement; gisPosition: [number, number] | null }[] {
  return villageSourceFeatures()
    .filter((feature) => feature.properties.feature_type === 'character')
    .map((feature) => {
      const id = feature.properties.id as number | undefined;
      const colour = colourForCharacter(id);
      const element = document.createElement('div');
      element.innerHTML = `
        <svg>
          <circle cx="0" cy="0" r="1" fill="${colour}"></circle>
        </svg>
      `;
      return {
        element,
        gisPosition: fromLngLat(feature.geometry.coordinates as [number, number]),
      };
    });
}

function positionAlongPathForTest(
  start: [number, number],
  path: [number, number][],
  distance: number
): [number, number] {
  let pos = start;
  let remaining = distance;

  for (const [nx, ny] of path) {
    const dx = nx - pos[0];
    const dy = ny - pos[1];
    const segmentDistance = Math.hypot(dx, dy);

    if (segmentDistance <= remaining) {
      pos = [nx, ny];
      remaining -= segmentDistance;
    } else {
      const factor = segmentDistance === 0 ? 0 : remaining / segmentDistance;
      pos = [pos[0] + dx * factor, pos[1] + dy * factor];
      break;
    }
  }

  return pos;
}

function renderMap(props: ComponentProps<typeof PopulationCentreMap>) {
  return render(
    <TooltipProvider>
      <PopulationCentreMap {...props} />
    </TooltipProvider>
  );
}

beforeEach(() => {
  FakeMap.instances = [];
  FakeMarker.instances = [];
});

const baseGeojson = {
  bbox: [0, 0, 100, 100] as [number, number, number, number],
  features: [
    {
      geometry: { type: 'Polygon', coordinates: [[[0, 0], [0, 100], [100, 100], [100, 0], [0, 0]]] },
      properties: { feature_type: 'boundary', name: 'Village Boundary' },
    },
    {
      geometry: { type: 'Point', coordinates: [10, 10] },
      properties: { feature_type: 'character', id: 1, name: 'Alice' },
    },
    {
      geometry: { type: 'Point', coordinates: [20, 20] },
      properties: { feature_type: 'character', id: 2, name: 'Bob' },
    },
  ],
};

describe('PopulationCentreMap', () => {
  it('renders nothing when geojson is absent', () => {
    renderMap({ geojson: null });
    expect(characterMarkers()).toHaveLength(0);
  });

  it('renders one character marker per character feature', () => {
    renderMap({ geojson: baseGeojson });
    expect(characterMarkers()).toHaveLength(2);
  });

  it('applies worldBounds as the map maxBounds, converted to the map projection', () => {
    renderMap({ geojson: baseGeojson, worldBounds: [-1000, -1000, 2000, 2000] });
    const map = currentMap();
    expect(map.maxBoundsCalls).toHaveLength(1);
    const bounds = map.maxBoundsCalls[0] as { sw: [number, number]; ne: [number, number] };
    expect(bounds.sw[0]).toBeCloseTo(toLngLat([-1000, -1000])[0]);
    expect(bounds.sw[1]).toBeCloseTo(toLngLat([-1000, -1000])[1]);
    expect(bounds.ne[0]).toBeCloseTo(toLngLat([2000, 2000])[0]);
    expect(bounds.ne[1]).toBeCloseTo(toLngLat([2000, 2000])[1]);
  });

  it('gives the same character id the same colour across renders', () => {
    renderMap({ geojson: baseGeojson });
    const firstFill = characterMarkers()[0].element.querySelector('circle')?.getAttribute('fill');
    FakeMap.instances = [];
    FakeMarker.instances = [];
    renderMap({ geojson: baseGeojson });
    const secondFill = characterMarkers()[0].element.querySelector('circle')?.getAttribute('fill');
    expect(firstFill).toBe(secondFill);
  });

  it('gives different character ids different colours (for the placeholder palette)', () => {
    renderMap({ geojson: baseGeojson });
    const [a, b] = characterMarkers();
    expect(a.element.querySelector('circle')?.getAttribute('fill')).not.toBe(
      b.element.querySelector('circle')?.getAttribute('fill')
    );
  });

  it('positions each marker at its GIS coordinates converted to the map projection', () => {
    renderMap({ geojson: baseGeojson });
    const [alice, bob] = characterMarkers();
    expect(alice.gisPosition?.[0]).toBeCloseTo(10);
    expect(alice.gisPosition?.[1]).toBeCloseTo(10);
    expect(bob.gisPosition?.[0]).toBeCloseTo(20);
    expect(bob.gisPosition?.[1]).toBeCloseTo(20);
  });

  it('places characters at random points inside their building footprint, not clustered at its centre', () => {
    const geojsonWithHousehold = {
      bbox: [0, 0, 20, 20] as [number, number, number, number],
      features: [
        {
          geometry: {
            type: 'Polygon',
            coordinates: [[[0, 0], [0, 20], [20, 20], [20, 0], [0, 0]]],
          },
          properties: {
            feature_type: 'building',
            name: 'House',
            building_type: 'residential',
          },
        },
        ...[10, 11, 12, 13, 14].map((id) => ({
          geometry: { type: 'Point', coordinates: [10, 10] },
          properties: { feature_type: 'character', id, name: `Resident ${id}` },
        })),
      ],
    };

    renderMap({ geojson: geojsonWithHousehold });
    const points = characterMarkers().map((m) => m.gisPosition as [number, number]);
    expect(points).toHaveLength(5);

    // Every character should land inside the 0-20 footprint (inset from the
    // walls a little), not stacked at the shared (10, 10) entrance point.
    points.forEach(([x, y]) => {
      expect(x).toBeGreaterThan(0);
      expect(x).toBeLessThan(20);
      expect(y).toBeGreaterThan(0);
      expect(y).toBeLessThan(20);
    });

    const exactlyAtSharedPoint = points.filter(([x, y]) => x === 10 && y === 10);
    expect(exactlyAtSharedPoint.length).toBeLessThan(points.length);

    const uniquePoints = new Set(points.map(([x, y]) => `${x.toFixed(3)},${y.toFixed(3)}`));
    expect(uniquePoints.size).toBe(5);
  });

  it('keeps a minimum distance between housemates scattered in the same building', () => {
    const geojsonWithCrowdedHousehold = {
      bbox: [0, 0, 10, 10] as [number, number, number, number],
      features: [
        {
          geometry: {
            type: 'Polygon',
            coordinates: [[[0, 0], [0, 10], [10, 10], [10, 0], [0, 0]]],
          },
          properties: {
            feature_type: 'building',
            name: 'House',
            building_type: 'residential',
          },
        },
        ...[20, 21, 22, 23, 24].map((id) => ({
          geometry: { type: 'Point', coordinates: [5, 5] },
          properties: { feature_type: 'character', id, name: `Resident ${id}` },
        })),
      ],
    };

    renderMap({ geojson: geojsonWithCrowdedHousehold });
    const points = characterMarkers().map((m) => m.gisPosition as [number, number]);
    expect(points).toHaveLength(5);

    for (let i = 0; i < points.length; i++) {
      for (let j = i + 1; j < points.length; j++) {
        const dx = points[i][0] - points[j][0];
        const dy = points[i][1] - points[j][1];
        const dist = Math.sqrt(dx * dx + dy * dy);
        expect(dist).toBeGreaterThan(1.5);
      }
    }
  });

  it('places characters at a shared point on the footprint boundary (e.g. the entrance node) inside the house, not clustered at the door', () => {
    const geojsonWithResidentsAtEntrance = {
      bbox: [0, 0, 20, 20] as [number, number, number, number],
      features: [
        {
          geometry: {
            type: 'Polygon',
            coordinates: [[[0, 0], [0, 20], [20, 20], [20, 0], [0, 0]]],
          },
          properties: {
            feature_type: 'building',
            name: 'House',
            building_type: 'residential',
          },
        },
        ...[30, 31, 32, 33, 34].map((id) => ({
          geometry: { type: 'Point', coordinates: [10, 0] }, // midpoint of the bottom wall
          properties: { feature_type: 'character', id, name: `Resident ${id}` },
        })),
      ],
    };

    renderMap({ geojson: geojsonWithResidentsAtEntrance });
    const points = characterMarkers().map((m) => m.gisPosition as [number, number]);
    expect(points).toHaveLength(5);

    points.forEach(([x, y]) => {
      expect(x).toBeGreaterThan(0);
      expect(x).toBeLessThan(20);
      expect(y).toBeGreaterThan(0);
      expect(y).toBeLessThan(20);
    });

    const exactlyAtDoor = points.filter(([x, y]) => x === 10 && y === 0);
    expect(exactlyAtDoor.length).toBe(0);
  });

  it('assigns a ready-to-harvest crops subzone a gold fill, distinct from the default grey building fill', () => {
    const geojsonWithCropSubzone = {
      ...baseGeojson,
      features: [
        ...baseGeojson.features,
        {
          geometry: { type: 'Polygon', coordinates: [[[50, 50], [50, 60], [60, 60], [60, 50], [50, 50]]] },
          properties: {
            feature_type: 'building',
            name: 'House 2 of (Driftmoor village)',
            building_type: 'residential',
          },
        },
        {
          geometry: { type: 'Polygon', coordinates: [[[5, 5], [5, 40], [40, 40], [40, 5], [5, 5]]] },
          properties: {
            feature_type: 'subzone',
            name: 'Driftmoor village Farmland - Crops',
            usage: 'crops',
            crop_stage: 'ready',
            crop_progress: null,
          },
        },
      ],
    };
    renderMap({ geojson: geojsonWithCropSubzone });
    const fills = villageSourceFeatures().map((f) => f.properties.fillColor);

    expect(fills).toContain('#E4C158');
    expect(fills).toContain('#ddd');
  });

  it('assigns a fallow or not-yet-planted crops subzone a bare-soil fill, distinct from ready gold', () => {
    const geojsonFallow = {
      ...baseGeojson,
      features: [
        ...baseGeojson.features,
        {
          geometry: { type: 'Polygon', coordinates: [[[5, 5], [5, 40], [40, 40], [40, 5], [5, 5]]] },
          properties: {
            feature_type: 'subzone',
            name: 'Farmland - Crops',
            usage: 'crops',
            crop_stage: 'fallow',
            crop_progress: null,
          },
        },
      ],
    };
    renderMap({ geojson: geojsonFallow });
    const fills = villageSourceFeatures().map((f) => f.properties.fillColor);

    expect(fills).toContain('#c2a878');
    expect(fills).not.toContain('#E4C158');
  });

  it('assigns a growing crops subzone a green fill that darkens as growth progress increases', () => {
    const cropFeature = (progress: number) => ({
      geometry: { type: 'Polygon', coordinates: [[[5, 5], [5, 40], [40, 40], [40, 5], [5, 5]]] },
      properties: {
        feature_type: 'subzone',
        name: 'Farmland - Crops',
        usage: 'crops',
        crop_stage: 'growing',
        crop_progress: progress,
      },
    });

    renderMap({ geojson: { ...baseGeojson, features: [...baseGeojson.features, cropFeature(0.1)] } });
    const earlyFill = villageSourceFeatures().find((f) => f.properties.feature_type === 'subzone')
      ?.properties.fillColor;

    FakeMap.instances = [];
    FakeMarker.instances = [];
    renderMap({ geojson: { ...baseGeojson, features: [...baseGeojson.features, cropFeature(0.9)] } });
    const lateFill = villageSourceFeatures().find((f) => f.properties.feature_type === 'subzone')
      ?.properties.fillColor;

    expect(earlyFill).toMatch(/^hsl\(/);
    expect(lateFill).toMatch(/^hsl\(/);
    expect(earlyFill).not.toBe(lateFill);
  });

  it('assigns field_shelter buildings the default grey fill, not gold', () => {
    const geojsonWithShelter = {
      ...baseGeojson,
      features: [
        ...baseGeojson.features,
        {
          geometry: { type: 'Polygon', coordinates: [[[5, 5], [5, 15], [15, 15], [15, 5], [5, 5]]] },
          properties: {
            feature_type: 'building',
            name: 'Field Shelter of (Driftmoor village)',
            building_type: 'field_shelter',
          },
        },
      ],
    };
    renderMap({ geojson: geojsonWithShelter });
    const fills = villageSourceFeatures().map((f) => f.properties.fillColor);

    expect(fills).not.toContain('#E4C158');
    expect(fills).toContain('#ddd');
  });

  it('reopens a tooltip after it was closed by an outside click', async () => {
    const geojsonWithBuilding = {
      ...baseGeojson,
      features: [
        ...baseGeojson.features,
        {
          geometry: { type: 'Polygon', coordinates: [[[5, 5], [5, 10], [10, 10], [10, 5], [5, 5]]] },
          properties: {
            feature_type: 'building',
            name: 'House 2 of (Driftmoor village)',
            building_type: 'residential',
          },
        },
      ],
    };
    renderMap({ geojson: geojsonWithBuilding });
    const feature = villageSourceFeatures().find((f) => f.properties.feature_type === 'building');

    act(() => {
      currentMap().trigger('click', { features: [feature], lngLat: { lng: 0, lat: 0 } }, 'buildings-fill');
    });
    expect(await screen.findByRole('tooltip')).toHaveTextContent('House');

    act(() => {
      currentMap().trigger('click', { point: { x: 0, y: 0 }, lngLat: { lng: 50, lat: 50 } }, undefined);
    });
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();

    act(() => {
      currentMap().trigger('click', { features: [feature], lngLat: { lng: 0, lat: 0 } }, 'buildings-fill');
    });
    expect(await screen.findByRole('tooltip')).toHaveTextContent('House');
  });

  it('shows just the building type in the tooltip, not the full backend name', async () => {
    const geojsonWithBuilding = {
      ...baseGeojson,
      features: [
        ...baseGeojson.features,
        {
          geometry: { type: 'Polygon', coordinates: [[[5, 5], [5, 10], [10, 10], [10, 5], [5, 5]]] },
          properties: {
            feature_type: 'building',
            name: 'House 2 of (Driftmoor village)',
            building_type: 'residential',
          },
        },
      ],
    };
    renderMap({ geojson: geojsonWithBuilding });
    const feature = villageSourceFeatures().find((f) => f.properties.feature_type === 'building');

    act(() => {
      currentMap().trigger('click', { features: [feature], lngLat: { lng: 0, lat: 0 } }, 'buildings-fill');
    });

    const tooltip = await screen.findByRole('tooltip');
    expect(tooltip).toHaveTextContent('House');
    expect(tooltip).not.toHaveTextContent('Driftmoor village');
  });

  it('shows workers and in-stock goods in a building tooltip', async () => {
    const geojsonWithBuilding = {
      ...baseGeojson,
      features: [
        ...baseGeojson.features,
        {
          geometry: { type: 'Polygon', coordinates: [[[5, 5], [5, 10], [10, 10], [10, 5], [5, 5]]] },
          properties: {
            feature_type: 'building',
            name: 'Bakery of (Driftmoor village)',
            building_type: 'bakery',
            workers: 2,
            goods: [
              { good_type: 'flour', display: '3 sacks' },
              { good_type: 'bread', display: '18.0 loaves' },
              { good_type: 'wheat', display: '0.0kg' },
            ],
          },
        },
      ],
    };
    renderMap({ geojson: geojsonWithBuilding });
    const feature = villageSourceFeatures().find((f) => f.properties.feature_type === 'building');

    act(() => {
      currentMap().trigger('click', { features: [feature], lngLat: { lng: 0, lat: 0 } }, 'buildings-fill');
    });

    const tooltip = await screen.findByRole('tooltip');
    expect(tooltip).toHaveTextContent('Workers: 2');
    expect(tooltip).toHaveTextContent('Flour: 3 sacks');
    expect(tooltip).toHaveTextContent('Bread: 18.0 loaves');
  });

  it('shows residents rather than workers for a residential building', async () => {
    const geojsonWithHouse = {
      ...baseGeojson,
      features: [
        ...baseGeojson.features,
        {
          geometry: { type: 'Polygon', coordinates: [[[5, 5], [5, 10], [10, 10], [10, 5], [5, 5]]] },
          properties: {
            feature_type: 'building',
            name: 'House 2 of (Driftmoor village)',
            building_type: 'residential',
            workers: 0,
            residents: 3,
          },
        },
      ],
    };
    renderMap({ geojson: geojsonWithHouse });
    const feature = villageSourceFeatures().find((f) => f.properties.feature_type === 'building');

    act(() => {
      currentMap().trigger('click', { features: [feature], lngLat: { lng: 0, lat: 0 } }, 'buildings-fill');
    });

    const tooltip = await screen.findByRole('tooltip');
    expect(tooltip).toHaveTextContent('Residents: 3');
    expect(tooltip).not.toHaveTextContent('Workers');
  });

  it('shows home, workplace, and hunger in a character tooltip', async () => {
    const geojsonWithCharacter = {
      ...baseGeojson,
      features: [
        {
          geometry: { type: 'Point', coordinates: [10, 10] },
          properties: {
            feature_type: 'character',
            id: 1,
            name: 'Alice',
            home: 'Rose Cottage',
            work: 'Village Bakery',
            hunger_label: 'Well fed',
          },
        },
      ],
    };
    renderMap({ geojson: geojsonWithCharacter });
    const feature = villageSourceFeatures().find((f) => f.properties.feature_type === 'character');

    act(() => {
      currentMap().trigger('click', { features: [feature], lngLat: { lng: 10, lat: 10 } }, 'characters');
    });

    const tooltip = await screen.findByRole('tooltip');
    expect(tooltip).toHaveTextContent('Alice');
    expect(tooltip).toHaveTextContent('Lives at: Rose Cottage');
    expect(tooltip).toHaveTextContent('Works at: Village Bakery');
    expect(tooltip).toHaveTextContent('Well fed');
  });

  it('shows the crop stage in a field tooltip instead of the literal word "Crops"', async () => {
    const geojsonWithReadyField = {
      ...baseGeojson,
      features: [
        ...baseGeojson.features,
        {
          geometry: { type: 'Polygon', coordinates: [[[5, 5], [5, 40], [40, 40], [40, 5], [5, 5]]] },
          properties: {
            feature_type: 'subzone',
            name: 'Farmland - Crops',
            usage: 'crops',
            crop_stage: 'ready',
            crop_progress: null,
          },
        },
      ],
    };
    renderMap({ geojson: geojsonWithReadyField });
    const feature = villageSourceFeatures().find((f) => f.properties.feature_type === 'subzone');

    act(() => {
      currentMap().trigger('click', { features: [feature], lngLat: { lng: 0, lat: 0 } }, 'subzones-fill');
    });

    const tooltip = await screen.findByRole('tooltip');
    expect(tooltip).toHaveTextContent('Ready to harvest');
  });

  it('fans out characters sharing the same coordinate instead of stacking them', () => {
    const geojsonWithSharedHouse = {
      ...baseGeojson,
      features: [
        ...baseGeojson.features,
        {
          geometry: { type: 'Point', coordinates: [50, 50] },
          properties: { feature_type: 'character', id: 3, name: 'Carol' },
        },
        {
          geometry: { type: 'Point', coordinates: [50, 50] },
          properties: { feature_type: 'character', id: 4, name: 'Dave' },
        },
        {
          geometry: { type: 'Point', coordinates: [50, 50] },
          properties: { feature_type: 'character', id: 5, name: 'Eve' },
        },
      ],
    };
    renderMap({ geojson: geojsonWithSharedHouse });
    const points = characterMarkers()
      .slice(2)
      .map((m) => m.gisPosition as [number, number]);

    const uniquePoints = new Set(points.map(([x, y]) => `${x.toFixed(3)},${y.toFixed(3)}`));
    expect(uniquePoints.size).toBe(3);
  });

  it('renders path lines invisibly (line-opacity 0)', () => {
    const geojsonWithPath = {
      ...baseGeojson,
      features: [
        ...baseGeojson.features,
        {
          geometry: { type: 'LineString', coordinates: [[0, 0], [10, 10]] },
          properties: { feature_type: 'path', name: 'Main Street' },
        },
      ],
    };
    renderMap({ geojson: geojsonWithPath });
    const pathsLayer = currentMap().layers.find((l) => l.id === 'paths-line') as
      | { paint?: { 'line-opacity'?: number } }
      | undefined;
    expect(pathsLayer?.paint?.['line-opacity']).toBe(0);

    const feature = villageSourceFeatures().find((f) => f.properties.feature_type === 'path');
    expect(feature).toBeDefined();
  });
});

describe('PopulationCentreMap path-aware interpolation (#615)', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  const walkingGeojson = {
    bbox: [0, 0, 100, 100] as [number, number, number, number],
    features: [
      {
        geometry: { type: 'Point', coordinates: [0, 0] },
        properties: {
          feature_type: 'character',
          id: 1,
          name: 'Walker',
          path: [
            [10, 0],
            [10, 10],
          ] as [number, number][],
          effective_speed: 5,
        },
      },
    ],
  };

  it('walks a moving character along its path over time instead of staying put', () => {
    renderMap({ geojson: walkingGeojson });
    const [x, y] = positionAlongPathForTest([0, 0], [[10, 0], [10, 10]], 5);
    expect(x).toBeGreaterThan(0);
    expect(x).toBeLessThanOrEqual(10);
    expect(y).toBeCloseTo(0);
  });

  it('continues onto the next path segment after reaching a waypoint, without stalling', () => {
    renderMap({ geojson: walkingGeojson });
    const [x, y] = positionAlongPathForTest([0, 0], [[10, 0], [10, 10]], 15);
    expect(x).toBeCloseTo(10);
    expect(y).toBeGreaterThan(0);
    expect(y).toBeLessThan(10);
  });

  it('holds position at the end of its known path instead of extrapolating past it', () => {
    renderMap({ geojson: walkingGeojson });
    const [x, y] = positionAlongPathForTest([0, 0], [[10, 0], [10, 10]], 100);
    expect(x).toBeCloseTo(10);
    expect(y).toBeCloseTo(10);
  });

  it('does not animate an idle character (no active journey)', () => {
    const idleGeojson = {
      ...walkingGeojson,
      features: [
        {
          geometry: { type: 'Point', coordinates: [50, 50] },
          properties: { feature_type: 'character', id: 2, name: 'Idle', path: null },
        },
      ],
    };
    renderMap({ geojson: idleGeojson });
    const marker = characterMarkers()[0];
    expect(marker.gisPosition?.[0]).toBeCloseTo(50);
    expect(marker.gisPosition?.[1]).toBeCloseTo(50);

    act(() => {
      vi.advanceTimersByTime(5000);
    });

    expect(marker.gisPosition?.[0]).toBeCloseTo(50);
    expect(marker.gisPosition?.[1]).toBeCloseTo(50);
  });

  it('adopts a fresh poll as the new authoritative checkpoint rather than extrapolating from the previous one (#615 follow-up)', () => {
    const { rerender } = renderMap({ geojson: walkingGeojson });
    const midX = positionAlongPathForTest([0, 0], [[10, 0], [10, 10]], 2.5)[0];
    expect(midX).toBeGreaterThan(0);
    expect(midX).toBeLessThan(10);

    const correctedGeojson = {
      bbox: [0, 0, 100, 100] as [number, number, number, number],
      features: [
        {
          geometry: { type: 'Point', coordinates: [50, 50] },
          properties: {
            feature_type: 'character',
            id: 1,
            name: 'Walker',
            path: [[60, 50]] as [number, number][],
            effective_speed: 5,
          },
        },
      ],
    };
    rerender(
      <TooltipProvider>
        <PopulationCentreMap geojson={correctedGeojson} />
      </TooltipProvider>
    );

    const justAfter = positionAlongPathForTest([50, 50], [[60, 50]], 0.08);
    expect(Math.hypot(justAfter[0] - 50, justAfter[1] - 50)).toBeLessThan(0.5);

    const later = positionAlongPathForTest(justAfter, [[60, 50]], 2.5);
    expect(later[0]).toBeGreaterThan(justAfter[0]);
    expect(later[1]).toBeCloseTo(50, 5);
  });

  it('recomputes position fresh each frame instead of accumulating step-to-step error (#615 follow-up)', () => {
    renderMap({ geojson: walkingGeojson });
    const singleStepMarker = characterMarkers()[0];
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    const singleStepPos = singleStepMarker.gisPosition as [number, number];

    FakeMap.instances = [];
    FakeMarker.instances = [];
    renderMap({ geojson: walkingGeojson });
    const manyStepsMarker = characterMarkers()[0];
    act(() => {
      for (let i = 0; i < 50; i++) {
        vi.advanceTimersByTime(20);
      }
    });
    const manyStepsPos = manyStepsMarker.gisPosition as [number, number];

    expect(manyStepsPos[0]).toBeCloseTo(singleStepPos[0], 1);
    expect(manyStepsPos[1]).toBeCloseTo(singleStepPos[1], 1);
  });
});
