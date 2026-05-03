// src/components/FeatureToggle.jsx
import React from 'react';
import Button from './Button/Button';
import featureFlags from '../featureFlags';
import { useGame } from '../context/GameContext';
import { useAppConfig } from '../hooks/useAppConfig';
import styles from './FeatureToggle.module.scss';

const ACCESS_NONE = 'no';
const ACCESS_ALL = 'all';
const ACCESS_PREMIUM = 'premium';

const hasOwn = (obj, key) => Object.prototype.hasOwnProperty.call(obj, key);

export default function FeatureToggle({ flag, children, fallback }) {
  const { player } = useGame() ?? {};
  const { data: appConfig } = useAppConfig();
  const remoteFeatureFlags = appConfig?.feature_flags ?? {};
  const accessLevel = hasOwn(remoteFeatureFlags, flag)
    ? remoteFeatureFlags[flag]
    : featureFlags[flag];
  const isPremiumUser = Boolean(player?.is_premium);

  const isEnabled = (() => {
    // Backward compatibility for existing boolean flags.
    if (typeof accessLevel === 'boolean') {
      return accessLevel;
    }

    if (accessLevel === ACCESS_ALL) {
      return true;
    }

    if (accessLevel === ACCESS_PREMIUM) {
      return isPremiumUser;
    }

    if (accessLevel === ACCESS_NONE || accessLevel === undefined) {
      return false;
    }

    return false;
  })();

  const defaultFallback = accessLevel === ACCESS_PREMIUM ? (
    <div className={styles.fallbackPage}>
      <div className={styles.fallbackCard}>
        <p className={styles.fallbackTitle}>Premium feature</p>
        <p>This feature is available to Premium users.</p>
        <Button as="a" href="/upgrade">Upgrade to premium</Button>
      </div>
    </div>
  ) : (
    <div className={styles.fallbackPage}>
      <div className={styles.fallbackCard}>
        <p className={styles.fallbackTitle}>Coming soon</p>
        <p>This feature is coming soon! Stay tuned.</p>
      </div>
    </div>
  );

  return isEnabled ? children : (fallback ?? defaultFallback);
}
