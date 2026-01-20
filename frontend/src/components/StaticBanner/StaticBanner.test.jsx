import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import StaticBanner from './StaticBanner';

describe('StaticBanner', () => {
  it('renders message when provided', () => {
    render(<StaticBanner message="This is a banner message" />);
    
    expect(screen.getByText('This is a banner message')).toBeInTheDocument();
  });

  it('does not render when message is not provided', () => {
    const { container } = render(<StaticBanner />);
    
    expect(container.firstChild).toBeNull();
  });

  it('does not render when message is empty string', () => {
    const { container } = render(<StaticBanner message="" />);
    
    expect(container.firstChild).toBeNull();
  });

  it('does not render when message is null', () => {
    const { container } = render(<StaticBanner message={null} />);
    
    expect(container.firstChild).toBeNull();
  });

  it('renders multiple words correctly', () => {
    render(<StaticBanner message="Welcome to Progress RPG!" />);
    
    expect(screen.getByText('Welcome to Progress RPG!')).toBeInTheDocument();
  });

  it('renders special characters correctly', () => {
    render(<StaticBanner message="Alert: System maintenance at 10:00 PM!" />);
    
    expect(screen.getByText('Alert: System maintenance at 10:00 PM!')).toBeInTheDocument();
  });
});
