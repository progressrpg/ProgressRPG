import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import ErrorFallback from './ErrorFallback';

describe('ErrorFallback', () => {
  it('renders error message', () => {
    const error = new Error('Test error message');
    render(<ErrorFallback error={error} resetErrorBoundary={() => {}} />);
    
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
    expect(screen.getByText('Test error message')).toBeInTheDocument();
  });

  it('renders reset button', () => {
    const error = new Error('Test error');
    render(<ErrorFallback error={error} resetErrorBoundary={() => {}} />);
    
    const button = screen.getByRole('button', { name: /try again/i });
    expect(button).toBeInTheDocument();
  });

  it('displays error message in pre element', () => {
    const error = new Error('Formatted error');
    const { container } = render(<ErrorFallback error={error} resetErrorBoundary={() => {}} />);
    
    const preElement = container.querySelector('pre');
    expect(preElement).toHaveTextContent('Formatted error');
    expect(preElement).toHaveStyle({ color: 'red' });
  });
});
