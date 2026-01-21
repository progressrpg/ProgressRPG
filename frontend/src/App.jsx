import React, { useEffect } from 'react';
import { MaintenanceProvider } from './context/MaintenanceContext';
import { ToastProvider } from './context/ToastContext';
import { AuthProvider, useAuth } from './context/AuthContext';
import { GameProvider } from './context/GameContext';
import { BrowserRouter, useLocation } from 'react-router-dom';
import { WebSocketProvider } from './context/WebSocketContext';

import MaintenanceWatcher from './components/MaintenanceWatcher';
import AppContent from "./AppContent";

import { initGA, logPageView } from '../utils/analytics';

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
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        minHeight: '100vh',
        fontSize: '1.2rem'
      }}>
        Loading...
      </div>
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
