// src/AppContent.tsx
import { useState } from 'react';
import { useLocation } from 'react-router';
import Navbar from './layout/Navbar/Navbar';
import NavDrawer from './layout/NavDrawer/NavDrawer';
import StaticBanner from './components/StaticBanner/StaticBanner';
import AppRoutes from "./routes/AppRoutes";
import Footer from './layout/Footer/Footer';
import OnlineCountBadge from './components/OnlineCountBadge/OnlineCountBadge';
import FeatureToggle from './components/FeatureToggle';
import FeedbackWidget from './components/FeedbackWidget/FeedbackWidget';
import TutorialModal from './components/TutorialModal/TutorialModal';
import { useAuth } from './context/AuthContext';
import { useGame } from './hooks/useGame';
import { apiFetch } from './utils/api';

const announcement = `Progress RPG is in alpha status, and under active development. Bugs may appear, and data may be lost. Thank you for testing!`;

export default function AppContent(): React.ReactElement {
  const { isAuthenticated } = useAuth();
  const { player, fetchPlayerAndCharacter } = useGame();
  const location = useLocation();
  const [drawerOpen, setDrawerOpen] = useState(false);
  // Tracks whether the user has explicitly dismissed the tutorial this session.
  const [tutorialDismissed, setTutorialDismissed] = useState(false);
  // Tracks whether the user manually opened the tutorial via the help button.
  const [tutorialForced, setTutorialForced] = useState(false);
  const hideBanner = !isAuthenticated && location.pathname === '/';

  const hasUnseenSteps = (player?.unseen_tutorial_step_ids?.length ?? 0) > 0;

  // Auto-open for first-time users (not yet onboarded) or when there are unseen steps.
  // Also opens when forced via the help button.
  const tutorialOpen =
    tutorialForced ||
    (isAuthenticated && player && !player.onboarding_completed && !tutorialDismissed) ||
    (player?.onboarding_completed && hasUnseenSteps && !tutorialDismissed);

  const firstUnseenId = player?.unseen_tutorial_step_ids?.[0] ?? null;

  const handleTutorialComplete = async () => {
    if (!player?.onboarding_completed) {
      try {
        await apiFetch("/me/complete_onboarding/", { method: "POST" });
      } catch {
        // Non-fatal
      }
    }
    await fetchPlayerAndCharacter?.();
    setTutorialDismissed(false);
    setTutorialForced(false);
  };

  return (
    <div className="app-container">
      <Navbar
        onMenuClick={() => setDrawerOpen(true)}
        onHelpClick={() => { setTutorialDismissed(false); setTutorialForced(true); }}
      />
      <NavDrawer drawerOpen={drawerOpen} onClose={() => setDrawerOpen(false)}/>
      {!hideBanner && <StaticBanner message={`${announcement}`} />}
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <AppRoutes />
      </main>
      <FeatureToggle flag="onlinePlayerCount" fallback={null}>
        <OnlineCountBadge />
      </FeatureToggle>
      <Footer />
      {isAuthenticated && !tutorialOpen && <FeedbackWidget />}
      {tutorialOpen && (
        <TutorialModal
          startAtStepId={tutorialForced ? null : firstUnseenId}
          onClose={() => { setTutorialDismissed(true); setTutorialForced(false); }}
          onComplete={handleTutorialComplete}
        />
      )}
    </div>
  );
}
