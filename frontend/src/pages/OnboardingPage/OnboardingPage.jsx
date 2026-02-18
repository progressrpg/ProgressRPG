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
      <div className={styles.content}>
        <h1>Welcome</h1>
        <p>Welcome to Progress RPG ✨</p>
        <p>This is a space where your real-world effort becomes in-game progress.</p>
        <p>When you start timing an activity, two things happen at the same time:</p>
        <ul>
          <li><strong>You</strong> work on a real task, at your own pace.</li>
          <li><strong>Your character</strong> trains, explores, and grows in the game world.</li>
        </ul>
        <p>Even small actions count.</p>
        <p>Starting is enough.</p>
        <p>Progress RPG is designed to help reduce overwhelm, build momentum, and make effort feel meaningful.</p>
        <p>Take your time exploring — and when you’re ready, start your first activity.</p>
        <p>We’re still building and improving the experience, so <a href="https://forms.gle/9EtaqxQoNwTATDMBA" target="_blank" rel="noopener noreferrer">your feedback</a> is incredibly valuable.</p>

        {error && <p role="alert">{error}</p>}
        <Button
          onClick={enter}
          disabled={loading}
        >
          Enter the game
        </Button>
      </div>
    </div>
  );
}
