// RequireOnboardingComplete.jsx
import { Navigate } from 'react-router-dom';
import { useGame } from '../context/GameContext';

export default function RequireOnboardingComplete({ children }) {
  const { player, loading } = useGame();

  const completed = Boolean(player?.onboarding_completed);

  if (loading || !player) return <p>Loading…</p>;

  return completed
    ? children
    : <Navigate to="/onboarding" replace />;
}
