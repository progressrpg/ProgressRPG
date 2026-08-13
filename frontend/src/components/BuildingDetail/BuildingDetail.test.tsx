import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import BuildingDetail from './BuildingDetail';

describe('BuildingDetail', () => {
  it('shows residents out of capacity for a residential building', () => {
    render(
      <BuildingDetail
        buildingType="residential"
        residents={[{ id: 1, name: 'Alice' }, { id: 2, name: 'Bob' }]}
        residentialCapacity={6}
      />
    );

    expect(screen.getByText('2 / 6')).toBeInTheDocument();
    expect(screen.queryByText(/Workers/)).not.toBeInTheDocument();
  });

  it('omits the capacity suffix when capacity is unknown', () => {
    render(
      <BuildingDetail
        buildingType="residential"
        residents={[{ id: 1, name: 'Alice' }]}
        residentialCapacity={null}
      />
    );

    expect(screen.getByText('1')).toBeInTheDocument();
  });

  it('shows a worker count instead of residents for a non-residential building', () => {
    render(
      <BuildingDetail buildingType="bakery" residents={[]} workerCount={2} />
    );

    expect(screen.getByText('Workers')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.queryByText('Residents')).not.toBeInTheDocument();
  });

  it('lists in-stock goods, skipping zero-quantity entries', () => {
    render(
      <BuildingDetail
        buildingType="bakery"
        residents={[]}
        goods={[
          { good_type: 'flour', display: '3 sacks' },
          { good_type: 'wheat', display: '' },
        ]}
      />
    );

    expect(screen.getByText('Flour: 3 sacks')).toBeInTheDocument();
    expect(screen.queryByText(/Wheat/)).not.toBeInTheDocument();
  });

  it('shows each resident by name only', () => {
    render(
      <BuildingDetail
        buildingType="residential"
        residents={[
          { id: 1, name: 'Alice', currentActivity: 'idle' },
          { id: 2, name: 'Bob', currentActivity: 'sleeping', isMoving: true },
        ]}
      />
    );

    expect(screen.getByText('Alice')).toBeInTheDocument();
    expect(screen.getByText('Bob')).toBeInTheDocument();
  });

  it('calls onSelectResident when a resident row is clicked', async () => {
    const user = userEvent.setup();
    const onSelectResident = vi.fn();
    render(
      <BuildingDetail
        buildingType="residential"
        residents={[{ id: 7, name: 'Alice' }]}
        onSelectResident={onSelectResident}
      />
    );

    await user.click(screen.getByText('Alice'));

    expect(onSelectResident).toHaveBeenCalledWith(7);
  });

  it('renders residents as non-interactive when onSelectResident is omitted', () => {
    render(
      <BuildingDetail
        buildingType="residential"
        residents={[{ id: 7, name: 'Alice' }]}
      />
    );

    expect(screen.queryByRole('option')).not.toBeInTheDocument();
  });
});
