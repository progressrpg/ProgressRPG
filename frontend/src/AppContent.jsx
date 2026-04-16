// src/AppContent.jsx
import { useState } from 'react';
import { useLocation } from 'react-router-dom';
import Navbar from './layout/Navbar/Navbar';
import NavDrawer from './layout/NavDrawer/NavDrawer';
import Infobar from './layout/Infobar/Infobar';
import StaticBanner from './components/StaticBanner/StaticBanner';
import AppRoutes from "./routes/AppRoutes";
import Footer from './layout/Footer/Footer';
import FeedbackWidget from './components/FeedbackWidget/FeedbackWidget';
import { useAuth } from './context/AuthContext';
import { useGame } from './context/GameContext';

const announcement = `Progress RPG is in alpha status, and under active development. Bugs may appear, and data may be lost. Thank you for testing!`;

export default function AppContent() {
  const { buildNumber } = useGame();
  const { isAuthenticated } = useAuth();
  const location = useLocation();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const hideBanner = !isAuthenticated && location.pathname === '/';

  return (
    <div className="app-container">
      <Navbar onMenuClick={() => setDrawerOpen(true)}/>
      <NavDrawer drawerOpen={drawerOpen} onClose={() => setDrawerOpen(false)}/>
      {!hideBanner && <StaticBanner message={`${announcement} (Build ${buildNumber})`} />}
      {isAuthenticated && <Infobar />}
      <AppRoutes />
      <Footer />
      {isAuthenticated && <FeedbackWidget />}
    </div>
  );
}
