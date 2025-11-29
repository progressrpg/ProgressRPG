// src/AppContent.jsx

import Navbar from './layout/Navbar/Navbar';
import NavDrawer from './layout/Nav-drawer/NavDrawer';
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

  return (
    <div className="app-container">
      <Navbar />
      <NavDrawer />
      <StaticBanner message={`${announcement} (Build ${buildNumber})`} />
      <AppRoutes />
      <Footer />
      {isAuthenticated && <FeedbackWidget />}
    </div>
  );
}
