import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Input from './Input';

describe('Input', () => {
  it('renders input with label', () => {
    render(<Input id="test-input" label="Username" />);
    
    expect(screen.getByLabelText('Username')).toBeInTheDocument();
  });

  it('renders without label when not provided', () => {
    render(<Input id="test-input" />);
    
    const input = screen.getByRole('textbox');
    expect(input).toBeInTheDocument();
  });

  it('displays required indicator when required prop is true', () => {
    render(<Input id="test-input" label="Email" required />);
    
    expect(screen.getByText('*')).toBeInTheDocument();
  });

  it('renders with placeholder text', () => {
    render(<Input id="test-input" placeholder="Enter your name" />);
    
    expect(screen.getByPlaceholderText('Enter your name')).toBeInTheDocument();
  });

  it('displays help text when provided', () => {
    render(<Input id="test-input" helpText="This is a helpful message" />);
    
    expect(screen.getByText('This is a helpful message')).toBeInTheDocument();
  });

  it('displays error text and hides help text when error is provided', () => {
    render(
      <Input 
        id="test-input" 
        helpText="Help message" 
        error="This field is required" 
      />
    );
    
    expect(screen.getByText('This field is required')).toBeInTheDocument();
    expect(screen.queryByText('Help message')).not.toBeInTheDocument();
  });

  it('sets aria-invalid when error is present', () => {
    render(<Input id="test-input" error="Error message" />);
    
    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('aria-invalid', 'true');
  });

  it('calls onChange with value for text input', async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();
    
    render(<Input id="test-input" value="" onChange={handleChange} />);
    
    const input = screen.getByRole('textbox');
    await user.type(input, 'test');
    
    expect(handleChange).toHaveBeenCalled();
    expect(handleChange).toHaveBeenCalledWith('t');
  });

  it('renders checkbox input type correctly', () => {
    render(<Input id="test-checkbox" type="checkbox" label="Accept terms" />);
    
    const checkbox = screen.getByRole('checkbox');
    expect(checkbox).toBeInTheDocument();
  });

  it('calls onChange with boolean for checkbox input', async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();
    
    render(
      <Input 
        id="test-checkbox" 
        type="checkbox" 
        checked={false} 
        onChange={handleChange} 
      />
    );
    
    const checkbox = screen.getByRole('checkbox');
    await user.click(checkbox);
    
    expect(handleChange).toHaveBeenCalledWith(true);
  });

  it('applies custom className to input group', () => {
    const { container } = render(
      <Input id="test-input" className="custom-wrapper" />
    );
    
    const wrapper = container.firstChild;
    expect(wrapper.className).toMatch(/custom-wrapper/);
  });

  it('applies custom inputClassName to input element', () => {
    const { container } = render(
      <Input id="test-input" inputClassName="custom-input" />
    );
    
    const input = container.querySelector('input');
    expect(input.className).toMatch(/custom-input/);
  });

  it('applies minLength and maxLength attributes', () => {
    render(
      <Input 
        id="test-input" 
        minLength={3} 
        maxLength={10} 
      />
    );
    
    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('minLength', '3');
    expect(input).toHaveAttribute('maxLength', '10');
  });

  it('does not call onChange if onChange prop is not provided', async () => {
    const user = userEvent.setup();
    
    render(<Input id="test-input" value="" />);
    
    const input = screen.getByRole('textbox');
    // Should not throw error
    await user.type(input, 'test');
  });
});
