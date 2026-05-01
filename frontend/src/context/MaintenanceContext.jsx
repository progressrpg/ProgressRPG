// context/MaintenanceContext.js
import React, { createContext, useContext, useState } from 'react';

const MaintenanceContext = createContext();

export function MaintenanceProvider({ children }) {
  const [maintenance, setMaintenance] = useState({
    active: false,
    details: null,
    previousLocation: null,
    justEnded: false,
  });

  return (
    <MaintenanceContext.Provider value={{ maintenance, setMaintenance }}>
      {children}
    </MaintenanceContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useMaintenanceContext() {
  const context = useContext(MaintenanceContext);
  if (!context) {
    throw new Error('useMaintenanceContext must be used within a MaintenanceProvider');
  }
  return context;
}
