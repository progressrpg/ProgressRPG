import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import List from './List';

describe('List', () => {
  it('renders empty list when no items are provided', () => {
    const { container } = render(<List items={[]} />);

    const list = container.querySelector('ul');
    expect(list).toBeInTheDocument();
    expect(list.children).toHaveLength(0);
  });

  it('renders list items', () => {
    const items = ['Apple', 'Banana', 'Cherry'];

    render(<List items={items} />);

    expect(screen.getByText('Apple')).toBeInTheDocument();
    expect(screen.getByText('Banana')).toBeInTheDocument();
    expect(screen.getByText('Cherry')).toBeInTheDocument();
  });

  it('uses renderItem function when provided', () => {
    const items = [{ name: 'Apple' }, { name: 'Banana' }];
    const renderItem = (item) => <span>{item.name.toUpperCase()}</span>;

    render(<List items={items} renderItem={renderItem} />);

    expect(screen.getByText('APPLE')).toBeInTheDocument();
    expect(screen.getByText('BANANA')).toBeInTheDocument();
  });

  it('uses getKey function for generating keys', () => {
    const items = [
      { id: 'a', name: 'Apple' },
      { id: 'b', name: 'Banana' }
    ];
    const getKey = (item) => item.id;

    const { container } = render(
      <List items={items} getKey={getKey} renderItem={(item) => item.name} />
    );

    const listItems = container.querySelectorAll('li');
    expect(listItems).toHaveLength(2);
  });

  it('handles items with id property', () => {
    const items = [
      { id: 1, name: 'Item 1' },
      { id: 2, name: 'Item 2' }
    ];

    render(<List items={items} renderItem={(item) => item.name} />);

    expect(screen.getByText('Item 1')).toBeInTheDocument();
    expect(screen.getByText('Item 2')).toBeInTheDocument();
  });

  it('calls onSelect when selectable item is clicked', async () => {
    const user = userEvent.setup();
    const items = ['Apple', 'Banana'];
    const handleSelect = vi.fn();

    render(
      <List
        items={items}
        canSelect={true}
        onSelect={handleSelect}
      />
    );

    await user.click(screen.getByText('Apple'));

    expect(handleSelect).toHaveBeenCalledWith('Apple');
  });

  it('does not call onSelect when selectable is false', async () => {
    const user = userEvent.setup();
    const items = ['Apple', 'Banana'];
    const handleSelect = vi.fn();

    render(
      <List
        items={items}
        canSelect={false}
        onSelect={handleSelect}
      />
    );

    await user.click(screen.getByText('Apple'));

    expect(handleSelect).not.toHaveBeenCalled();
  });

  it('applies selected class to selected item', () => {
    const items = ['Apple', 'Banana'];

    render(
      <List
        items={items}
        selectedItem="Apple"
        selectable={true}
      />
    );

    const appleItem = screen.getByText('Apple').closest('li');
    expect(appleItem.className).toMatch(/selected/);
  });

  it('applies custom className to list', () => {
    const { container } = render(
      <List items={['Apple']} className="custom-list" />
    );

    const list = container.querySelector('ul');
    expect(list.className).toMatch(/custom-list/);
  });

  it('applies custom sectionClass to section', () => {
    const { container } = render(
      <List items={['Apple']} sectionClass="custom-section" />
    );

    const section = container.querySelector('section');
    expect(section.className).toMatch(/custom-section/);
  });

  it('uses getItemClassName for custom item classes', () => {
    const items = ['Red', 'Green', 'Blue'];
    const getItemClassName = (item) => `color-${item.toLowerCase()}`;

    render(
      <List items={items} getItemClassName={getItemClassName} />
    );

    const redItem = screen.getByText('Red').closest('li');
    expect(redItem.className).toMatch(/color-red/);
  });

  it('applies hidden class to items with isHidden property', () => {
    const items = [
      { id: 1, name: 'Visible', isHidden: false },
      { id: 2, name: 'Hidden', isHidden: true }
    ];

    render(
      <List items={items} renderItem={(item) => item.name} />
    );

    const hiddenItem = screen.getByText('Hidden').closest('li');
    expect(hiddenItem.className).toMatch(/hidden/);
  });

  it('handles items with results property', () => {
    const itemsWithResults = {
      results: ['Apple', 'Banana', 'Cherry']
    };

    render(<List items={itemsWithResults} />);

    expect(screen.getByText('Apple')).toBeInTheDocument();
    expect(screen.getByText('Banana')).toBeInTheDocument();
    expect(screen.getByText('Cherry')).toBeInTheDocument();
  });

  it('handles non-array items gracefully', () => {
    const { container } = render(<List items={undefined} />);

    const list = container.querySelector('ul');
    expect(list.children).toHaveLength(0);
  });
});
