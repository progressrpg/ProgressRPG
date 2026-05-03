import { act, fireEvent, render, screen } from '@testing-library/react';
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
      screen.getByText('Nice work ⚔️ You spent 1 minute 30 seconds on "Write tests".')
    ).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Reward' })).not.toBeInTheDocument();
    expect(screen.getByText('1:30')).toBeInTheDocument();
    expect(screen.getByText('Total XP gained')).toBeInTheDocument();
    expect(screen.getByText('Time')).toBeInTheDocument();
    expect(screen.getByText('+27 XP')).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Next action' })).not.toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Continue with support in 3..' })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Back to timer' })
    ).toBeInTheDocument();
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
      screen.getByText('Nice work ⚔️ You spent 21 seconds on "Quick task".')
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
      screen.getByText('Nice work ⚔️ You spent 2 hours 5 minutes on "Deep work".')
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
      screen.getByText('Nice work ⚔️ You spent 1 minute on "Write tests".')
    ).toBeInTheDocument();
    expect(screen.getByText('1:00')).toBeInTheDocument();
    expect(screen.getByText('Premium bonus')).toBeInTheDocument();
    expect(screen.getByText('x2')).toBeInTheDocument();
    expect(screen.getByText('+120 XP')).toBeInTheDocument();
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
    expect(screen.queryByRole('heading', { name: 'Upgrade' })).not.toBeInTheDocument();
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
    expect(screen.queryByRole('heading', { name: 'Upgrade' })).not.toBeInTheDocument();
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
    expect(
      screen.queryByRole('heading', { name: 'Upgrade' })
    ).not.toBeInTheDocument();
  });

  it('does not show upgrade prompt for premium users', () => {
    render(
      <ActivityRewardScreen
        activityName="Write tests"
        xpGained={54}
        baseXp={27}
        xpMultiplier={2}
        levelUps={[]}
        elapsedSeconds={90}
        isAutoStopped
        showUpgradePrompt
        onContinue={vi.fn()}
        onSupport={vi.fn()}
      />
    );

    expect(
      screen.queryByText(/Need more time\? Upgrade to Premium/)
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole('link', { name: 'Upgrade to Premium' })
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Continue with support in 3..' })
    ).toBeInTheDocument();
  });

  it('auto-starts supported session after 3 seconds', () => {
    vi.useFakeTimers();
    const onSupport = vi.fn();

    render(
      <ActivityRewardScreen
        activityName="Write tests"
        xpGained={27}
        baseXp={27}
        xpMultiplier={1}
        levelUps={[]}
        elapsedSeconds={90}
        onContinue={vi.fn()}
        onSupport={onSupport}
      />
    );

    expect(onSupport).not.toHaveBeenCalled();

    act(() => {
      vi.advanceTimersByTime(3000);
    });

    expect(onSupport).toHaveBeenCalledTimes(1);
    vi.useRealTimers();
  });

  it('pauses countdown while hovering support panel and resumes after pointer leaves', () => {
    vi.useFakeTimers();
    const onSupport = vi.fn();

    const { container } = render(
      <ActivityRewardScreen
        activityName="Write tests"
        xpGained={27}
        baseXp={27}
        xpMultiplier={1}
        levelUps={[]}
        elapsedSeconds={90}
        onContinue={vi.fn()}
        onSupport={onSupport}
      />
    );

    const supportPanel = container.querySelector('[class*="supportPanel"]');
    expect(supportPanel).not.toBeNull();

    act(() => {
      fireEvent.pointerEnter(supportPanel);
    });
    act(() => {
      vi.advanceTimersByTime(3000);
    });
    expect(onSupport).not.toHaveBeenCalled();

    act(() => {
      fireEvent.pointerLeave(supportPanel);
    });
    act(() => {
      vi.advanceTimersByTime(3000);
    });
    expect(onSupport).toHaveBeenCalledTimes(1);
    vi.useRealTimers();
  });

  it('shows static support button and does not auto-continue when countdown is disabled', () => {
    vi.useFakeTimers();
    const onSupport = vi.fn();

    render(
      <ActivityRewardScreen
        activityName="Write tests"
        xpGained={27}
        baseXp={27}
        xpMultiplier={1}
        levelUps={[]}
        elapsedSeconds={90}
        enableAutoSupportCountdown={false}
        onContinue={vi.fn()}
        onSupport={onSupport}
      />
    );

    expect(
      screen.getByRole('button', { name: 'Continue with support' })
    ).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: /Continue with support in/i })
    ).not.toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(5000);
    });
    expect(onSupport).not.toHaveBeenCalled();

    vi.useRealTimers();
  });
});
