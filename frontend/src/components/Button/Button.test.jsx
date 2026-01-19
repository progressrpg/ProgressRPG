import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import Button from './Button';

describe('Button', () => {
  it('renders children content', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByRole('button')).toHaveTextContent('Click me');
  });

  it('renders as a button by default', () => {
    render(<Button>Default</Button>);
    const element = screen.getByRole('button');
    expect(element.tagName).toBe('BUTTON');
  });

  it('renders as an anchor when as="a" is provided', () => {
    render(<Button as="a" href="/test">Link Button</Button>);
    const element = screen.getByRole('link');
    expect(element.tagName).toBe('A');
    expect(element).toHaveAttribute('href', '/test');
  });

  it('applies primary variant class by default', () => {
    const { container } = render(<Button>Primary</Button>);
    const button = container.querySelector('button');
    expect(button.className).toMatch(/primary/);
  });

  it('applies custom variant class', () => {
    const { container } = render(<Button variant="secondary">Secondary</Button>);
    const button = container.querySelector('button');
    expect(button.className).toMatch(/secondary/);
  });

  it('renders icon when provided', () => {
    const icon = <span data-testid="test-icon">🔥</span>;
    render(<Button icon={icon}>With Icon</Button>);
    expect(screen.getByTestId('test-icon')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(<Button className="custom-class">Custom</Button>);
    const button = container.querySelector('button');
    expect(button.className).toMatch(/custom-class/);
  });

  it('passes through additional props', () => {
    render(<Button disabled data-testid="btn">Disabled</Button>);
    const button = screen.getByTestId('btn');
    expect(button).toBeDisabled();
  });
});
