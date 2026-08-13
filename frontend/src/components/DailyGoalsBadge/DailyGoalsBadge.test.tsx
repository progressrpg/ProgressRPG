import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import DailyGoalsBadge from './DailyGoalsBadge';
import type { DailyGoalsResponse } from '../../api/player';

const mockUseDailyGoals = vi.fn<() => { data: DailyGoalsResponse | undefined }>(
  () => ({ data: { goals: null } })
);

vi.mock('../../hooks/usePlayer', () => ({
  useDailyGoals: () => mockUseDailyGoals(),
}));

const baseGoals = {
  logged_in_today: false,
  completed_activity_today: false,
  activity_minutes_today: 0,
  minutes_goal_threshold: 3,
  minutes_goal_met: false,
  all_goals_met: false,
  bonus_awarded_today: false,
  bonus_ap: 0,
};

describe('DailyGoalsBadge', () => {
  it('renders nothing when the player has no active character link', () => {
    mockUseDailyGoals.mockReturnValue({ data: { goals: null } });

    const { container } = render(<DailyGoalsBadge />);

    expect(container).toBeEmptyDOMElement();
  });

  it('renders nothing while the query has no data yet', () => {
    mockUseDailyGoals.mockReturnValue({ data: undefined });

    const { container } = render(<DailyGoalsBadge />);

    expect(container).toBeEmptyDOMElement();
  });

  it('shows all three goals as unmet', () => {
    mockUseDailyGoals.mockReturnValue({ data: { goals: baseGoals } });

    render(<DailyGoalsBadge />);

    expect(screen.getByText('Logged in today')).toBeInTheDocument();
    expect(screen.getByText('Completed an activity')).toBeInTheDocument();
    expect(screen.getByText('3+ minutes recorded')).toBeInTheDocument();
    expect(screen.queryByText(/AP bonus earned/)).not.toBeInTheDocument();
    expect(screen.queryByText('All goals cleared!')).not.toBeInTheDocument();
  });

  it('shows the awarded bonus once all goals are cleared and the bonus has paid out', () => {
    mockUseDailyGoals.mockReturnValue({
      data: {
        goals: {
          ...baseGoals,
          logged_in_today: true,
          completed_activity_today: true,
          activity_minutes_today: 5,
          minutes_goal_met: true,
          all_goals_met: true,
          bonus_awarded_today: true,
          bonus_ap: 50,
        },
      },
    });

    render(<DailyGoalsBadge />);

    expect(screen.getByText('+50 AP bonus earned!')).toBeInTheDocument();
  });

  it('shows a generic "cleared" message if goals are met but the bonus has not landed yet', () => {
    mockUseDailyGoals.mockReturnValue({
      data: {
        goals: {
          ...baseGoals,
          logged_in_today: true,
          completed_activity_today: true,
          activity_minutes_today: 5,
          minutes_goal_met: true,
          all_goals_met: true,
          bonus_awarded_today: false,
          bonus_ap: 0,
        },
      },
    });

    render(<DailyGoalsBadge />);

    expect(screen.getByText('All goals cleared!')).toBeInTheDocument();
  });
});
