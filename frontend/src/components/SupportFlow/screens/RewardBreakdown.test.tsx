import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import RewardBreakdown from './RewardBreakdown';

describe('RewardBreakdown', () => {
  it('shows minutes and seconds in reward copy', () => {
    render(
      <RewardBreakdown
        activityName="Write tests"
        xpGained={27}
        baseXp={27}
        xpMultiplier={1}
        levelUps={[]}
        elapsedSeconds={90}
      />
    );

    expect(
      screen.getByText('Nice work ⚔️ You spent 1 minute 30 seconds on "Write tests".')
    ).toBeInTheDocument();
    expect(screen.getByText('1:30')).toBeInTheDocument();
    expect(screen.getByText('Total XP gained')).toBeInTheDocument();
    expect(screen.getByText('Time')).toBeInTheDocument();
    expect(screen.getByText('+27 XP')).toBeInTheDocument();
    expect(screen.queryByText('XP multipliers:')).not.toBeInTheDocument();
  });

  it('shows seconds-only durations in reward copy', () => {
    render(
      <RewardBreakdown
        activityName="Quick task"
        xpGained={21}
        baseXp={21}
        xpMultiplier={1}
        levelUps={[]}
        elapsedSeconds={21}
      />
    );

    expect(
      screen.getByText('Nice work ⚔️ You spent 21 seconds on "Quick task".')
    ).toBeInTheDocument();
    expect(screen.getByText('0:21')).toBeInTheDocument();
  });

  it('shows hours and minutes in reward copy', () => {
    render(
      <RewardBreakdown
        activityName="Deep work"
        xpGained={7500}
        baseXp={3750}
        xpMultiplier={2}
        levelUps={[]}
        elapsedSeconds={7500}
      />
    );

    expect(
      screen.getByText('Nice work ⚔️ You spent 2 hours 5 minutes on "Deep work".')
    ).toBeInTheDocument();
    expect(screen.getByText('2:05:00')).toBeInTheDocument();
  });

  it('shows the premium multiplier in the xp calculation breakdown', () => {
    render(
      <RewardBreakdown
        activityName="Write tests"
        xpGained={120}
        baseXp={60}
        xpMultiplier={2}
        levelUps={[2]}
        elapsedSeconds={60}
      />
    );

    expect(screen.getByText('Nice work ⚔️ You spent 1 minute on "Write tests".')).toBeInTheDocument();
    expect(screen.getByText('1:00')).toBeInTheDocument();
    expect(screen.getByText('Premium bonus')).toBeInTheDocument();
    expect(screen.getByText('x2')).toBeInTheDocument();
    expect(screen.getByText('+120 XP')).toBeInTheDocument();
    expect(screen.getByText('Level up! You reached level 2.')).toBeInTheDocument();
  });

  it('shows a task bonus multiplier line alongside a premium bonus', () => {
    render(
      <RewardBreakdown
        activityName="Ship it"
        xpGained={180}
        baseXp={60}
        xpMultiplier={3}
        taskXpMultiplier={1.5}
        levelUps={[]}
        elapsedSeconds={60}
      />
    );

    expect(screen.getByText('Premium bonus')).toBeInTheDocument();
    expect(screen.getByText('x2')).toBeInTheDocument();
    expect(screen.getByText('Task bonus')).toBeInTheDocument();
    expect(screen.getByText('x1.5')).toBeInTheDocument();
  });

  it('falls back to generic copy without an activity name, still showing XP', () => {
    render(
      <RewardBreakdown xpGained={15} baseXp={15} xpMultiplier={1} levelUps={[]} elapsedSeconds={30} />
    );

    expect(screen.getByText('Nice work ⚔️ You spent 30 seconds focused.')).toBeInTheDocument();
    expect(screen.getByText('You gained 15 XP!')).toBeInTheDocument();
  });

  it('renders a plain summary line when there is no elapsed time or XP', () => {
    render(<RewardBreakdown activityName="Just a note" />);

    expect(screen.getByText('Nice work ⚔️ You completed "Just a note".')).toBeInTheDocument();
    expect(screen.queryByText('Total XP gained')).not.toBeInTheDocument();
  });
});
