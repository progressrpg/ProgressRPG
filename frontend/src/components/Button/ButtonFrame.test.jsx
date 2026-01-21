import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import ButtonFrame from './ButtonFrame';

describe('ButtonFrame', () => {
  it('renders children content', () => {
    render(
      <ButtonFrame>
        <button>Click me</button>
      </ButtonFrame>
    );
    
    expect(screen.getByRole('button', { name: 'Click me' })).toBeInTheDocument();
  });

  it('renders text children', () => {
    render(
      <ButtonFrame>
        Some text content
      </ButtonFrame>
    );
    
    expect(screen.getByText('Some text content')).toBeInTheDocument();
  });

  it('renders multiple children', () => {
    render(
      <ButtonFrame>
        <button>First Button</button>
        <button>Second Button</button>
      </ButtonFrame>
    );
    
    expect(screen.getByRole('button', { name: 'First Button' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Second Button' })).toBeInTheDocument();
  });

  it('renders with proper wrapper div', () => {
    const { container } = render(
      <ButtonFrame>
        <span>Content</span>
      </ButtonFrame>
    );
    
    const wrapper = container.firstChild;
    expect(wrapper.tagName).toBe('DIV');
  });

  it('applies buttonFrame class', () => {
    const { container } = render(
      <ButtonFrame>
        <span>Content</span>
      </ButtonFrame>
    );
    
    const wrapper = container.firstChild;
    expect(wrapper.className).toMatch(/buttonFrame/);
  });
});
