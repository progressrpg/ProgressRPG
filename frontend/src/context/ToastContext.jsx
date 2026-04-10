// context/ToastContext.jsx

import React, { createContext, useContext, useState, useCallback } from 'react';
import { useToasts } from '../hooks/useToasts';
// ToastManager is temporarily deactivated
// import ToastManager from '../components/Toast/ToastManager';

const ToastContext = createContext();

export function ToastProvider({ children, duration }) {
  const { toasts, showToast } = useToasts(duration);

  return (
    <ToastContext.Provider value={{ toasts, showToast }}>
      {children}
      {/* <ToastManager messages={toasts} /> */}
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}
