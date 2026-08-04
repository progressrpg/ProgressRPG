import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import TodayPointsBadge from './TodayPointsBadge';

const mockUseTodayPoints = vi.fn<() => { data: { points_today: number | null } | undefined }>(
  () => ({ data: { points_today: 12 } })
);

vi.mock('../../hooks/usePlayer', () => ({
  useTodayPoints: () => mockUseTodayPoints(),
}));

describe('TodayPointsBadge', () => {
  it("shows the player's points earned today", () => {
    mockUseTodayPoints.mockReturnValue({ data: { points_today: 12 } });

    render(<TodayPointsBadge />);

    expect(screen.getByText('You contributed 12 today')).toBeInTheDocument();
  });

  it('renders nothing when the player has no active character link', () => {
    mockUseTodayPoints.mockReturnValue({ data: { points_today: null } });

    const { container } = render(<TodayPointsBadge />);

    expect(container).toBeEmptyDOMElement();
  });

  it('renders nothing (not a zero) while the query has no data yet', () => {
    mockUseTodayPoints.mockReturnValue({ data: undefined });

    const { container } = render(<TodayPointsBadge />);

    expect(container).toBeEmptyDOMElement();
  });

  it('shows zero points as a real value, not treating it as "no link"', () => {
    mockUseTodayPoints.mockReturnValue({ data: { points_today: 0 } });

    render(<TodayPointsBadge />);

    expect(screen.getByText('You contributed 0 today')).toBeInTheDocument();
  });
});
