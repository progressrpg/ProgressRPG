// RequireOnboardingComplete.jsx
import { Navigate } from 'react-router-dom';
import useOnboarding from '../hooks/useOnboarding';


const COMPLETE_STEP = 2;


export default function RequireOnboardingComplete({ children }) {
  const { step, loading } = useOnboarding();

  if (loading || step === undefined) return <p>Loading…</p>;

  return step >= COMPLETE_STEP ? children : <Navigate to="/onboarding" replace />;
}
