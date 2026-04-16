import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import Form from './Form';

describe('Form', () => {
  it('does not show a required error for a checked required checkbox', () => {
    render(
      <Form
        title="Register"
        onSubmit={vi.fn()}
        fields={[
          {
            name: 'agree_to_terms',
            label: 'Agree to terms',
            type: 'checkbox',
            checked: true,
            onChange: vi.fn(),
            required: true,
          },
        ]}
      />
    );

    const checkbox = screen.getByRole('checkbox', { name: /agree to terms/i });
    fireEvent.blur(checkbox);

    expect(screen.queryByText('This field is required')).not.toBeInTheDocument();
  });
});
