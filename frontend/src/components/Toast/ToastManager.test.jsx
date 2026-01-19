import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import ToastManager from './ToastManager';

describe('ToastManager', () => {
  it('renders empty container when no messages', () => {
    const { container } = render(<ToastManager messages={[]} />);
    
    const toastContainer = container.querySelector('[aria-live="assertive"]');
    expect(toastContainer).toBeInTheDocument();
    expect(toastContainer).toBeEmptyDOMElement();
  });

  it('renders single toast message', () => {
    const messages = [
      { id: 1, message: 'Test message' }
    ];
    
    render(<ToastManager messages={messages} />);
    
    expect(screen.getByText('Test message')).toBeInTheDocument();
  });

  it('renders multiple toast messages', () => {
    const messages = [
      { id: 1, message: 'First message' },
      { id: 2, message: 'Second message' },
      { id: 3, message: 'Third message' }
    ];
    
    render(<ToastManager messages={messages} />);
    
    expect(screen.getByText('First message')).toBeInTheDocument();
    expect(screen.getByText('Second message')).toBeInTheDocument();
    expect(screen.getByText('Third message')).toBeInTheDocument();
  });

  it('renders toast with title and message', () => {
    const messages = [
      { id: 1, title: 'Success', message: 'Operation completed' }
    ];
    
    render(<ToastManager messages={messages} />);
    
    expect(screen.getByText('Success')).toBeInTheDocument();
    expect(screen.getByText('Operation completed')).toBeInTheDocument();
  });

  it('renders toast without title', () => {
    const messages = [
      { id: 1, message: 'Just a message' }
    ];
    
    render(<ToastManager messages={messages} />);
    
    expect(screen.getByText('Just a message')).toBeInTheDocument();
  });

  it('applies correct type class', () => {
    const messages = [
      { id: 1, message: 'Error message', type: 'error' }
    ];
    
    const { container } = render(<ToastManager messages={messages} />);
    
    const toast = container.querySelector('[class*="error"]');
    expect(toast).toBeInTheDocument();
  });

  it('defaults to info type when type is not provided', () => {
    const messages = [
      { id: 1, message: 'Info message' }
    ];
    
    const { container } = render(<ToastManager messages={messages} />);
    
    const toast = container.querySelector('[class*="info"]');
    expect(toast).toBeInTheDocument();
  });

  it('renders toast with role="status"', () => {
    const messages = [
      { id: 1, message: 'Status message' }
    ];
    
    const { container } = render(<ToastManager messages={messages} />);
    
    const toast = container.querySelector('[role="status"]');
    expect(toast).toBeInTheDocument();
  });

  it('uses unique keys for each toast', () => {
    const messages = [
      { id: 1, message: 'Message 1' },
      { id: 2, message: 'Message 2' }
    ];
    
    const { container } = render(<ToastManager messages={messages} />);
    
    const toasts = container.querySelectorAll('[role="status"]');
    expect(toasts).toHaveLength(2);
  });

  it('renders different toast types', () => {
    const messages = [
      { id: 1, message: 'Info', type: 'info' },
      { id: 2, message: 'Success', type: 'success' },
      { id: 3, message: 'Warning', type: 'warning' },
      { id: 4, message: 'Error', type: 'error' }
    ];
    
    render(<ToastManager messages={messages} />);
    
    expect(screen.getByText('Info')).toBeInTheDocument();
    expect(screen.getByText('Success')).toBeInTheDocument();
    expect(screen.getByText('Warning')).toBeInTheDocument();
    expect(screen.getByText('Error')).toBeInTheDocument();
  });
});
