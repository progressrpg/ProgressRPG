import Navbar from './layout/Navbar/Navbar';
import StaticBanner from './components/StaticBanner/StaticBanner';
import AppRoutes from "./routes/AppRoutes";
import Footer from './layout/Footer/Footer';
import FeedbackWidget from './components/FeedbackWidget/FeedbackWidget';
import { useAuth } from './context/AuthContext';

const announcement = `Progress RPG is in alpha status, and under active development. Bugs may appear, and data may be lost. Thank you for testing!`;

export default function AppContent() {
  const { buildNumber } = useGame();
  const { isAuthenticated } = useAuth();

  return (
    <div className="app-container">
      <Navbar />
      <StaticBanner message={`${announcement} (Build ${buildNumber})`} />
      <AppRoutes />
      <Footer />
      {isAuthenticated && <FeedbackWidget />}
    </div>
  );
}
