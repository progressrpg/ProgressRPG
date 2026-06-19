import React, { useState } from "react";

import Button from "../../components/Button/Button";
import { useGame } from "../../context/GameContext";
import { useAppConfig } from "../../hooks/useAppConfig";
import { apiFetch } from "../../utils/api";
import styles from "./UpgradePage.module.scss";

export default function UpgradePage() {
  const { player } = useGame();
  const { data: appConfig } = useAppConfig();
  const isStripeSandbox = appConfig?.stripe_live_mode === false;
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const checkoutPlan = "monthly";

  const handleCheckout = async () => {
    setLoading(true);
    setError("");

    try {
      const data = await apiFetch("/payments/create-checkout-session/", {
        method: "POST",
        body: JSON.stringify({ plan: checkoutPlan }),
      });

      if (!data?.url) {
        throw new Error("No checkout URL was returned.");
      }

      window.location.href = data.url;
    } catch (err) {
      console.error("[Checkout] Failed to create checkout session", err);
      setError("Could not open checkout right now. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const trialDays = appConfig?.trial_period_days ?? 0;
  const hasPreviousSubscription = Boolean(player?.has_previous_subscription);
  const hasTrial = trialDays > 0 && !hasPreviousSubscription;
  const isAlreadyPremium = Boolean(player?.is_premium);

  return (
    <div className={styles.page}>
      {isStripeSandbox && (
        <div className={styles.sandboxBanner}>
          Test mode - Stripe is in sandbox mode. No real payments will be taken. To make a test payment, use card number "4242 4242 4242 4242", and any future expiration date and CVC.
        </div>
      )}
      <h1>Upgrade to Premium</h1>
      {isAlreadyPremium ? (
        <p className={styles.subscribedNotice}>You are already subscribed!</p>
      ) : (
        <>
          <p className={styles.subtitle}>Focused progress, unlocked.</p>

          <div className={styles.planGrid}>
            <div className={`${styles.planCard} ${styles.planCardActive}`}>
              <ul className={styles.benefitsList}>
                <li>Double XP on all activity rewards</li>
                <li>Unlimited timer sessions</li>
                <li>Early access to new features</li>
                <li>Help reach more people who need this</li>
              </ul>
              <p className={styles.planDescription}>
                {hasTrial
                  ? `£5/month — ${trialDays}-day free trial, no card required. Cancel anytime.`
                  : "£5/month — cancel anytime."}
              </p>
            </div>
          </div>

          <Button onClick={handleCheckout} disabled={loading}>
            {loading ? "Redirecting..." : hasTrial ? `Start ${trialDays}-day free trial` : "Go to checkout"}
          </Button>

          {hasTrial && (
            <p className={styles.trialSmallPrint}>
              Today: trial starts. Day {trialDays}: reminder. Day {trialDays + 1}: billing begins if you continue.
            </p>
          )}
        </>
      )}
      {error ? <p className={styles.error}>{error}</p> : null}
    </div>
  );
}
