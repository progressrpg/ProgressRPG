import React, { useEffect } from 'react';
import { MaintenanceProvider } from './context/MaintenanceContext';
import { ToastProvider } from './context/ToastContext';
import { AuthProvider } from './context/AuthContext';
import { useAuth } from './context/useAuth';
import { GameProvider } from './context/GameContext';
import { BrowserRouter, useLocation } from 'react-router-dom';
import { WebSocketProvider } from './context/WebSocketContext';

import MaintenanceWatcher from './components/MaintenanceWatcher';
import AppContent from "./AppContent";

import { initGA, logPageView } from './utils/analytics';

function RouteChangeTracker() {
  const location = useLocation();

  useEffect(() => {
    logPageView(location.pathname + location.search);
  }, [location]);

  return null;
}

// New wrapper to handle loading states
function AppWithAuth() {
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
      <WebSocketProvider>
        <BrowserRouter>
          <RouteChangeTracker />
          <MaintenanceWatcher />
          <AppContent />
        </BrowserRouter>
      </WebSocketProvider>
    </GameProvider>
  );
}

function App() {
  useEffect(() => {
    initGA();
  }, []);

  return (
    <MaintenanceProvider>
      <ToastProvider>
        <AuthProvider>
          <AppWithAuth />
        </AuthProvider>
      </ToastProvider>
    </MaintenanceProvider>
  );
}

export default App;
