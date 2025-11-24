import React, { useEffect } from 'react';
import { MaintenanceProvider } from './context/MaintenanceContext';
import { ToastProvider } from './context/ToastContext';
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

function App() {
  useEffect(() => {
    initGA();
  }, [])

  return (
    <MaintenanceProvider>
      <ToastProvider>
        <GameProvider>
          <WebSocketProvider>
            <BrowserRouter>
              <RouteChangeTracker />
              <MaintenanceWatcher />
              <AppContent />
            </BrowserRouter>
          </WebSocketProvider>
        </GameProvider>
      </ToastProvider>
    </MaintenanceProvider>
  );
}

export default App;
