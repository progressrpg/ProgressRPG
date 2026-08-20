import { useState, useCallback } from 'react';
import type { ReactElement, ReactNode } from 'react';
import { ToastProvider as TamaguiToastProvider } from 'tamagui';
import { v4 as uuidv4 } from 'uuid';
import { ToastContext } from './toastContextDef';
import type { Toast } from './toastContextDef';
import { useFeatureFlag } from '../hooks/useFeatureFlag';
import ToastManager from '../components/Toast/ToastManager';

interface ProviderProps {
  children: ReactNode;
  duration?: number;
}

export function ToastProvider({ children, duration = 3300 }: ProviderProps): ReactElement {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const showToast = useCallback((message: string): void => {
    setToasts((prev) => [...prev, { id: uuidv4(), message: String(message) }]);
  }, []);

  const dismissToast = useCallback((id: string): void => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toastsEnabled = useFeatureFlag('toastsFeature');

  return (
    <TamaguiToastProvider duration={duration}>
      <ToastContext.Provider value={{ toasts, showToast }}>
        {children}
        {toastsEnabled && <ToastManager messages={toasts} onDismiss={dismissToast} />}
      </ToastContext.Provider>
    </TamaguiToastProvider>
  );
}
