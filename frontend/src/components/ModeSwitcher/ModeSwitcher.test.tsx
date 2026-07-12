import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import ModeSwitcher from './ModeSwitcher';

const twoModes = [
  { key: 'doing', label: 'Doing' },
  { key: 'planning', label: 'Planning' },
];

const threeModes = [
  ...twoModes,
  { key: 'reviewing', label: 'Reviewing' },
];

describe('ModeSwitcher', () => {
  it('renders one chip per mode with the active one checked', () => {
    render(<ModeSwitcher modes={twoModes} activeKey="doing" onSelect={vi.fn()} />);

    const doing = screen.getByRole('radio', { name: 'Doing' });
    const planning = screen.getByRole('radio', { name: 'Planning' });

    expect(doing).toHaveAttribute('aria-checked', 'true');
    expect(doing).toHaveAttribute('tabIndex', '0');
    expect(planning).toHaveAttribute('aria-checked', 'false');
    expect(planning).toHaveAttribute('tabIndex', '-1');
  });

  it('renders correctly for 3+ modes', () => {
    render(<ModeSwitcher modes={threeModes} activeKey="reviewing" onSelect={vi.fn()} />);

    expect(screen.getAllByRole('radio')).toHaveLength(3);
    expect(screen.getByRole('radio', { name: 'Reviewing' })).toHaveAttribute('aria-checked', 'true');
  });

  it('calls onSelect with the clicked chip key', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<ModeSwitcher modes={twoModes} activeKey="doing" onSelect={onSelect} />);

    await user.click(screen.getByRole('radio', { name: 'Planning' }));

    expect(onSelect).toHaveBeenCalledWith('planning');
  });

  it('ArrowRight moves selection to the next chip and wraps at the end', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<ModeSwitcher modes={twoModes} activeKey="planning" onSelect={onSelect} />);

    screen.getByRole('radio', { name: 'Planning' }).focus();
    await user.keyboard('{ArrowRight}');

    expect(onSelect).toHaveBeenCalledWith('doing');
  });

  it('ArrowLeft moves selection to the previous chip and wraps at the start', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<ModeSwitcher modes={twoModes} activeKey="doing" onSelect={onSelect} />);

    screen.getByRole('radio', { name: 'Doing' }).focus();
    await user.keyboard('{ArrowLeft}');

    expect(onSelect).toHaveBeenCalledWith('planning');
  });

  it('Home and End jump to the first and last chip', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<ModeSwitcher modes={threeModes} activeKey="planning" onSelect={onSelect} />);

    screen.getByRole('radio', { name: 'Planning' }).focus();
    await user.keyboard('{End}');
    expect(onSelect).toHaveBeenLastCalledWith('reviewing');

    onSelect.mockClear();
    screen.getByRole('radio', { name: 'Planning' }).focus();
    await user.keyboard('{Home}');
    expect(onSelect).toHaveBeenLastCalledWith('doing');
  });
});
