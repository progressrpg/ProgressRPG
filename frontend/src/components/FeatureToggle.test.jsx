import { beforeEach, describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import FeatureToggle from './FeatureToggle';

const mockUseGame = vi.fn();
const mockUseAppConfig = vi.fn();

vi.mock('../context/GameContext', () => ({
  useGame: () => mockUseGame(),
}));

vi.mock('../hooks/useAppConfig', () => ({
  useAppConfig: () => mockUseAppConfig(),
}));

// Mock the featureFlags module
vi.mock('../featureFlags', () => ({
  default: {
    enabledFeature: 'all',
    disabledFeature: 'no',
    premiumFeature: 'premium',
    legacyBooleanFeature: true,
  }
}));

describe('FeatureToggle', () => {
  beforeEach(() => {
    mockUseGame.mockReturnValue({ player: { is_premium: false } });
    mockUseAppConfig.mockReturnValue({ data: { feature_flags: {} } });
  });

  it('renders children when feature flag is enabled', () => {
    render(
      <FeatureToggle flag="enabledFeature">
        <div>Enabled Feature Content</div>
      </FeatureToggle>
    );

    expect(screen.getByText('Enabled Feature Content')).toBeInTheDocument();
  });

  it('renders default fallback when feature flag is disabled', () => {
    render(
      <FeatureToggle flag="disabledFeature">
        <div>Feature Content</div>
      </FeatureToggle>
    );

    expect(screen.queryByText('Feature Content')).not.toBeInTheDocument();
    expect(screen.getByText(/this feature is coming soon/i)).toBeInTheDocument();
  });

  it('renders custom fallback when feature flag is disabled', () => {
    render(
      <FeatureToggle
        flag="disabledFeature"
        fallback={<div>Custom fallback message</div>}
      >
        <div>Feature Content</div>
      </FeatureToggle>
    );

    expect(screen.queryByText('Feature Content')).not.toBeInTheDocument();
    expect(screen.getByText('Custom fallback message')).toBeInTheDocument();
  });

  it('does not render children when feature is undefined', () => {
    render(
      <FeatureToggle flag="nonExistentFeature">
        <div>Feature Content</div>
      </FeatureToggle>
    );

    expect(screen.queryByText('Feature Content')).not.toBeInTheDocument();
    expect(screen.getByText(/this feature is coming soon/i)).toBeInTheDocument();
  });

  it('renders premium feature for premium users', () => {
    mockUseGame.mockReturnValue({ player: { is_premium: true } });

    render(
      <FeatureToggle flag="premiumFeature">
        <div>Premium Feature Content</div>
      </FeatureToggle>
    );

    expect(screen.getByText('Premium Feature Content')).toBeInTheDocument();
  });

  it('hides premium feature for non-premium users', () => {
    render(
      <FeatureToggle flag="premiumFeature">
        <div>Premium Feature Content</div>
      </FeatureToggle>
    );

    expect(screen.queryByText('Premium Feature Content')).not.toBeInTheDocument();
    expect(
      screen.getByText(/this feature is available to premium users/i)
    ).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: /upgrade to premium/i })
    ).toHaveAttribute('href', '/upgrade');
  });

  it('supports legacy boolean flags', () => {
    render(
      <FeatureToggle flag="legacyBooleanFeature">
        <div>Legacy Feature Content</div>
      </FeatureToggle>
    );

    expect(screen.getByText('Legacy Feature Content')).toBeInTheDocument();
  });

  it('uses app-config flag override when present', () => {
    mockUseAppConfig.mockReturnValue({
      data: { feature_flags: { enabledFeature: 'no' } },
    });

    render(
      <FeatureToggle flag="enabledFeature">
        <div>Enabled Feature Content</div>
      </FeatureToggle>
    );

    expect(screen.queryByText('Enabled Feature Content')).not.toBeInTheDocument();
    expect(screen.getByText(/this feature is coming soon/i)).toBeInTheDocument();
  });
});
