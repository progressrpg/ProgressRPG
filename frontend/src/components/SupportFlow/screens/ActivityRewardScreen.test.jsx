import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import ActivityRewardScreen from './ActivityRewardScreen';

describe('ActivityRewardScreen', () => {
  it('shows minutes and seconds in reward copy', () => {
    render(
      <ActivityRewardScreen
        activityName="Write tests"
        xpGained={27}
        baseXp={27}
        xpMultiplier={1}
        levelUps={[]}
        elapsedSeconds={90}
        onContinue={vi.fn()}
        onSupport={vi.fn()}
      />
    );

    expect(
      screen.getByText('You spent 1 minute 30 seconds on "Write tests".')
    ).toBeInTheDocument();
    expect(screen.getByText('Time')).toBeInTheDocument();
    expect(screen.getByText('1:30')).toBeInTheDocument();
    expect(screen.getByText('Total XP gained')).toBeInTheDocument();
    expect(screen.getByText('27 XP')).toBeInTheDocument();
    expect(screen.queryByText('XP multipliers:')).not.toBeInTheDocument();
  });

  it('shows seconds-only durations in reward copy', () => {
    render(
      <ActivityRewardScreen
        activityName="Quick task"
        xpGained={21}
        baseXp={21}
        xpMultiplier={1}
        levelUps={[]}
        elapsedSeconds={21}
        onContinue={vi.fn()}
        onSupport={vi.fn()}
      />
    );

    expect(
      screen.getByText('You spent 21 seconds on "Quick task".')
    ).toBeInTheDocument();
    expect(screen.getByText('0:21')).toBeInTheDocument();
  });

  it('shows hours and minutes in reward copy', () => {
    render(
      <ActivityRewardScreen
        activityName="Deep work"
        xpGained={7500}
        baseXp={3750}
        xpMultiplier={2}
        levelUps={[]}
        elapsedSeconds={7500}
        onContinue={vi.fn()}
        onSupport={vi.fn()}
      />
    );

    expect(
      screen.getByText('You spent 2 hours 5 minutes on "Deep work".')
    ).toBeInTheDocument();
    expect(screen.getByText('2:05:00')).toBeInTheDocument();
  });

  it('shows the premium multiplier in the xp calculation breakdown', () => {
    render(
      <ActivityRewardScreen
        activityName="Write tests"
        xpGained={120}
        baseXp={60}
        xpMultiplier={2}
        levelUps={[2]}
        elapsedSeconds={60}
        onContinue={vi.fn()}
        onSupport={vi.fn()}
      />
    );

    expect(
      screen.getByText('You spent 1 minute on "Write tests".')
    ).toBeInTheDocument();
    expect(screen.getByText('1:00')).toBeInTheDocument();
    expect(screen.getByText('Premium bonus')).toBeInTheDocument();
    expect(screen.getByText('x2')).toBeInTheDocument();
    expect(screen.getByText('120 XP')).toBeInTheDocument();
    expect(screen.getByText('Level up! You reached level 2.')).toBeInTheDocument();
  });

  it('shows auto-stop upgrade prompt and button for free users', () => {
    render(
      <ActivityRewardScreen
        activityName="Write tests"
        xpGained={27}
        baseXp={27}
        xpMultiplier={1}
        levelUps={[]}
        elapsedSeconds={90}
        isAutoStopped
        showUpgradePrompt
        onContinue={vi.fn()}
        onSupport={vi.fn()}
      />
    );

    expect(
      screen.getByText('Need more time? Upgrade to Premium for unlimited timer sessions.')
    ).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: 'Upgrade to Premium' })
    ).toHaveAttribute('href', '/upgrade');
  });

  it('shows manual-stop premium XP prompt and button for free users', () => {
    render(
      <ActivityRewardScreen
        activityName="Write tests"
        xpGained={27}
        baseXp={27}
        xpMultiplier={1}
        levelUps={[]}
        elapsedSeconds={90}
        isAutoStopped={false}
        showUpgradePrompt
        onContinue={vi.fn()}
        onSupport={vi.fn()}
      />
    );

    expect(
      screen.getByText('Want even more rewards? Upgrade to Premium for double XP on activities.')
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Upgrade to Premium' })).toBeInTheDocument();
  });

  it('does not show upgrade prompt when upgrade CTA is disabled', () => {
    render(
      <ActivityRewardScreen
        activityName="Write tests"
        xpGained={27}
        baseXp={27}
        xpMultiplier={1}
        levelUps={[]}
        elapsedSeconds={90}
        isAutoStopped
        showUpgradePrompt={false}
        onContinue={vi.fn()}
        onSupport={vi.fn()}
      />
    );

    expect(
      screen.queryByText(/Upgrade to Premium/)
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole('link', { name: 'Upgrade to Premium' })
    ).not.toBeInTheDocument();
  });
});
