import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import TimerDisplay from './TimerDisplay';

describe('TimerDisplay', () => {
  it('renders with default props', () => {
    render(<TimerDisplay />);
    
    expect(screen.getByText(/Timer:/)).toBeInTheDocument();
    expect(screen.getByText('00:00')).toBeInTheDocument();
  });

  it('renders custom label', () => {
    render(<TimerDisplay label="Activity Timer" />);
    
    expect(screen.getByText(/Activity Timer:/)).toBeInTheDocument();
  });

  it('renders custom time', () => {
    render(<TimerDisplay time="05:30" />);
    
    expect(screen.getByText('05:30')).toBeInTheDocument();
  });

  it('renders status when provided', () => {
    render(<TimerDisplay label="Timer" status="Running" />);
    
    expect(screen.getByText(/Running/)).toBeInTheDocument();
  });

  it('renders complete timer with all props', () => {
    render(
      <TimerDisplay 
        label="Activity" 
        time="12:45" 
        status="Active"
      />
    );
    
    expect(screen.getByText(/Activity:/)).toBeInTheDocument();
    expect(screen.getByText(/Active/)).toBeInTheDocument();
    expect(screen.getByText('12:45')).toBeInTheDocument();
  });

  it('displays label and status together', () => {
    render(<TimerDisplay label="Countdown" status="Paused" />);
    
    const statusText = screen.getByText(/Countdown: Paused/);
    expect(statusText).toBeInTheDocument();
  });

  it('handles various time formats', () => {
    const { rerender } = render(<TimerDisplay time="01:30" />);
    expect(screen.getByText('01:30')).toBeInTheDocument();
    
    rerender(<TimerDisplay time="00:00:45" />);
    expect(screen.getByText('00:00:45')).toBeInTheDocument();
    
    rerender(<TimerDisplay time="23:59:59" />);
    expect(screen.getByText('23:59:59')).toBeInTheDocument();
  });

  it('renders without status', () => {
    render(<TimerDisplay label="Timer" time="03:20" />);
    
    // Should render label with colon but without status text
    const labelElement = screen.getByText(/Timer:/);
    expect(labelElement).toBeInTheDocument();
  });
});
