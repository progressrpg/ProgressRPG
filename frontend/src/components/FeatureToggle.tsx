// src/components/FeatureToggle.tsx
import React from 'react';
import Button from './Button/Button';
import { getFeatureGroups, useFeatureFlag } from '../hooks/useFeatureFlag';
import { useAppConfig } from '../hooks/useAppConfig';
import styles from './FeatureToggle.module.scss';
import type { FeatureFlagKey } from '../types';

interface FeatureToggleProps {
  flag: FeatureFlagKey;
  children: React.ReactNode;
  fallback?: React.ReactNode;
  // OR'd into the cohort-flag check - lets a per-player condition (e.g. a
  // progressive-unlock milestone, see ProgressiveUnlockGate) grant access
  // alongside the existing flag, without the flag's cohort logic needing
  // to know about it.
  alsoEnabledWhen?: boolean;
}

export default function FeatureToggle({
  flag,
  children,
  fallback,
  alsoEnabledWhen = false,
}: FeatureToggleProps) {
  const { data: appConfig } = useAppConfig();
  const remoteFeatureFlags = appConfig?.feature_flags ?? {};
  const groups = getFeatureGroups(flag, remoteFeatureFlags);

  const isEnabled = useFeatureFlag(flag) || alsoEnabledWhen;

  const isPremiumGated = !groups.includes('all') && groups.includes('premium');
  const defaultFallback = isPremiumGated ? (
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

  const resolvedFallback = fallback !== undefined ? fallback : defaultFallback;

  return isEnabled ? <>{children}</> : <>{resolvedFallback}</>;
}
