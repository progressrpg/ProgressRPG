import React, { useEffect } from 'react';
import { MaintenanceProvider } from './context/MaintenanceContext';
import { ToastProvider } from './context/ToastContext';
import { AuthProvider, useAuth } from './context/AuthContext';
import { GameProvider } from './context/GameContext';
import { OnlineCountProvider } from './context/OnlineCountContext';
import { BrowserRouter, useLocation } from 'react-router';
import { WebSocketProvider } from './context/WebSocketContext';

import MaintenanceWatcher from './components/MaintenanceWatcher';
import { TooltipProvider } from './components/Tooltip/Tooltip';
import AppContent from "./AppContent";

import { initGA, logPageView } from './utils/analytics';

function RouteChangeTracker(): null {
  const location = useLocation();

  useEffect(() => {
    logPageView(location.pathname + location.search);
  }, [location]);

  return null;
}

// New wrapper to handle loading states
function AppWithAuth(): React.ReactElement {
  const { loading: authLoading } = useAuth();

  // Show loading screen until auth is resolved
  if (authLoading) {
    return (
      <main
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '100vh',
          padding: '1rem',
        }}
      >
        <div role="status" aria-live="polite" aria-busy="true" style={{ fontSize: '1.2rem' }}>
          <h1 className="sr-only">Loading Progress RPG</h1>
          <span>Loading page...</span>
        </div>
      </main>
    );
  }

  return (
    <GameProvider>
      <OnlineCountProvider>
        <ToastProvider>
          <WebSocketProvider>
            <BrowserRouter>
              <RouteChangeTracker />
              <MaintenanceWatcher />
              <AppContent />
            </BrowserRouter>
          </WebSocketProvider>
        </ToastProvider>
      </OnlineCountProvider>
    </GameProvider>
  );
}

function App(): React.ReactElement {
  useEffect(() => {
    initGA();
  }, []);

  return (
    <MaintenanceProvider>
      <TooltipProvider>
        <AuthProvider>
          <AppWithAuth />
        </AuthProvider>
      </TooltipProvider>
    </MaintenanceProvider>
  );
}

export default App;
