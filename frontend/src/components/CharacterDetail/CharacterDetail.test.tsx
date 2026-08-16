import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import CharacterDetail from './CharacterDetail';
import type { MapCharacterDetail } from '../../api/map';

const mockUseMapCharacterDetail = vi.fn();

vi.mock('../../hooks/useMap', () => ({
  useMapCharacterDetail: (...args: unknown[]) => mockUseMapCharacterDetail(...args),
}));

function detail(overrides: Partial<MapCharacterDetail> = {}): MapCharacterDetail {
  return {
    id: 1,
    name: 'Alice',
    age: 32,
    sex: 'Female',
    home_type: 'residential',
    home_id: 5,
    work_type: 'bakery',
    work_id: 8,
    current_activity: 'delivering goods to neighbours',
    is_moving: false,
    relationships: [],
    ...overrides,
  };
}

describe('CharacterDetail', () => {
  it('shows a loading state while the fetch is in flight', () => {
    mockUseMapCharacterDetail.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    });

    render(<CharacterDetail characterId={1} />);

    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('shows an error message when the fetch fails', () => {
    mockUseMapCharacterDetail.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    });

    render(<CharacterDetail characterId={1} />);

    expect(screen.getByText(/couldn't load/i)).toBeInTheDocument();
  });

  it('shows age, sex, home, work, and current activity', () => {
    mockUseMapCharacterDetail.mockReturnValue({
      data: detail(),
      isLoading: false,
      isError: false,
    });

    render(<CharacterDetail characterId={1} />);

    expect(screen.getByText('32, Female')).toBeInTheDocument();
    expect(screen.getByText('delivering goods to neighbours')).toBeInTheDocument();
    expect(screen.getByText('House')).toBeInTheDocument();
    expect(screen.getByText('Bakery')).toBeInTheDocument();
  });

  it('shows "walking" instead of the scheduled activity while moving', () => {
    mockUseMapCharacterDetail.mockReturnValue({
      data: detail({ is_moving: true, current_activity: 'delivering goods to neighbours' }),
      isLoading: false,
      isError: false,
    });

    render(<CharacterDetail characterId={1} />);

    expect(screen.getByText('walking')).toBeInTheDocument();
    expect(screen.queryByText('delivering goods to neighbours')).not.toBeInTheDocument();
  });

  it('lists household relationships in "name — label" form', () => {
    mockUseMapCharacterDetail.mockReturnValue({
      data: detail({
        relationships: [
          { character_id: 2, name: 'Thomas', label: 'husband' },
          { character_id: 3, name: 'Emily', label: 'daughter' },
        ],
      }),
      isLoading: false,
      isError: false,
    });

    render(<CharacterDetail characterId={1} />);

    expect(screen.getByText('Relationships')).toBeInTheDocument();
    expect(screen.getByText('Thomas — husband')).toBeInTheDocument();
    expect(screen.getByText('Emily — daughter')).toBeInTheDocument();
  });

  it('omits the relationships section when there are none', () => {
    mockUseMapCharacterDetail.mockReturnValue({
      data: detail({ relationships: [] }),
      isLoading: false,
      isError: false,
    });

    render(<CharacterDetail characterId={1} />);

    expect(screen.queryByText('Relationships')).not.toBeInTheDocument();
  });
});
