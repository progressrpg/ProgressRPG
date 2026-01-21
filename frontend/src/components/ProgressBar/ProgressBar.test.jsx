import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import ProgressBar from './ProgressBar';

describe('ProgressBar', () => {
  it('renders progress bar with default values', () => {
    const { container } = render(<ProgressBar />);
    
    const progressFill = container.querySelector('[style*="width"]');
    expect(progressFill).toBeInTheDocument();
  });

  it('calculates percentage correctly', () => {
    const { container } = render(<ProgressBar value={50} max={100} />);
    
    const progressFill = container.querySelector('[style*="width"]');
    expect(progressFill).toHaveStyle({ width: '50%' });
  });

  it('caps percentage at 100%', () => {
    const { container } = render(<ProgressBar value={150} max={100} />);
    
    const progressFill = container.querySelector('[style*="width"]');
    expect(progressFill).toHaveStyle({ width: '100%' });
  });

  it('handles zero values correctly', () => {
    const { container } = render(<ProgressBar value={0} max={100} />);
    
    const progressFill = container.querySelector('[style*="width"]');
    expect(progressFill).toHaveStyle({ width: '0%' });
  });

  it('renders label when provided', () => {
    render(<ProgressBar value={50} max={100} label="50/100 XP" />);
    
    // Label might be inside or outside the progress bar, use getAllByText since there's a hidden copy
    const labels = screen.getAllByText('50/100 XP');
    expect(labels.length).toBeGreaterThan(0);
  });

  it('applies custom color class', () => {
    const { container } = render(<ProgressBar value={50} max={100} color="warning" />);
    
    const progressFill = container.querySelector('[class*="warning"]');
    expect(progressFill).not.toBeNull();
  });

  it('applies paused class when paused is true', () => {
    const { container } = render(<ProgressBar value={50} max={100} paused={true} />);
    
    const progressFill = container.querySelector('[class*="paused"]');
    expect(progressFill).toBeInTheDocument();
  });

  it('does not apply paused class when paused is false', () => {
    const { container } = render(<ProgressBar value={50} max={100} paused={false} />);
    
    const progressFill = container.querySelector('[class*="paused"]');
    expect(progressFill).toBeNull();
  });

  it('renders hidden label for measurement', () => {
    render(<ProgressBar value={50} max={100} label="Test Label" />);
    
    // There should be a hidden element used for measuring
    const hiddenLabel = screen.getAllByText('Test Label').find(el => 
      el.getAttribute('aria-hidden') === 'true'
    );
    expect(hiddenLabel).toBeInTheDocument();
  });

  it('handles different max values correctly', () => {
    const { container } = render(<ProgressBar value={25} max={50} />);
    
    const progressFill = container.querySelector('[style*="width"]');
    expect(progressFill).toHaveStyle({ width: '50%' });
  });
});
