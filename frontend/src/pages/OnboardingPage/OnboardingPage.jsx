//src/pages/OnboardingPage/OnboardingPage.jsx
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import styles from './OnboardingPage.module.scss';
import Button from '../../components/Button/Button';
import { apiFetch } from '../../../utils/api';
import useOnboarding from '../../hooks/useOnboarding';

export default function OnboardingPage() {
  const navigate = useNavigate();
  const {
    completeOnboarding,
    error,
    loading,
  } = useOnboarding();

  const enter = async () => {
    const ok = await completeOnboarding();
    if (ok) navigate("/game", { replace: true});
  };

  return (
    <div>
      <h1>Welcome</h1>
        {error && <p>{error}</p>}
        <Button
          onClick={enter}
          disabled={loading}
        >
          Enter the game
        </Button>

    </div>
  );
}
