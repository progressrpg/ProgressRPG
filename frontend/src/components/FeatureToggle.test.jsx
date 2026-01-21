import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import FeatureToggle from './FeatureToggle';

// Mock the featureFlags module
vi.mock('../featureFlags', () => ({
  default: {
    enabledFeature: true,
    disabledFeature: false,
  }
}));

describe('FeatureToggle', () => {
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
});
