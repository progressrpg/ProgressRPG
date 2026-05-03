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
          <p className={styles.subtitle}>Premium membership for focused progress.</p>

          <div className={styles.planGrid}>
            <div className={`${styles.planCard} ${styles.planCardActive}`}>
              <h2 className={styles.planHeading}>Premium membership</h2>
              <p className={styles.planPrice}>£5 / month</p>
              <p className={styles.planDescription}>Billed monthly. Cancel anytime.</p>
              <h3 className={styles.benefitsHeading}>Premium benefits</h3>
              <ul className={styles.benefitsList}>
                <li>Double XP on all activity rewards.</li>
                <li>Unlimited timer sessions.</li>
                <li>Early access to new features as they roll out.</li>
                <li>Help this project reach those in need quicker.</li>
              </ul>
            </div>
          </div>

          <Button onClick={handleCheckout} disabled={loading}>
            {loading ? "Redirecting..." : "Go to checkout"}
          </Button>
        </>
      )}
      {error ? <p className={styles.error}>{error}</p> : null}
    </div>
  );
}
