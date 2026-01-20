//src/pages/OnboardingPage/OnboardingPage.jsx
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import styles from './OnboardingPage.module.scss';
import Button from '../../components/Button/Button';
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
    <div className={styles.page}>
      <h1>Welcome</h1>
      <p>Welcome to Progress RPG ✨</p>
      <p>Here, your real tasks become in-game progress.</p>
      <p>Start an activity (as small as you like) and feel the anxiety reduce as you make progress.</p>

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
