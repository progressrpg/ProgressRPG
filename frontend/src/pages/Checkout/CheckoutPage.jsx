import React, { useState } from "react";

import Button from "../../components/Button/Button";
import { apiFetch } from "../../../utils/api";
import styles from "./CheckoutPage.module.scss";

export default function CheckoutPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selectedPlan, setSelectedPlan] = useState("monthly");

  const handleCheckout = async () => {
    setLoading(true);
    setError("");

    try {
      const data = await apiFetch("/payments/create-checkout-session/", {
        method: "POST",
        body: JSON.stringify({ plan: selectedPlan }),
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

  const monthlyActive = selectedPlan === "monthly";
  const annualActive = selectedPlan === "annual";
  const checkoutButtonLabel =
    selectedPlan === "monthly" ? "Go to Monthly Checkout" : "Go to Annual Checkout";

  return (
    <div className={styles.page}>
      <h1>Upgrade to Premium</h1>
      <p className={styles.subtitle}>Choose the plan that fits you best.</p>

      <div className={styles.planGrid}>
        <button
          type="button"
          onClick={() => setSelectedPlan("monthly")}
          className={`${styles.planCard} ${monthlyActive ? styles.planCardActive : ""}`}
        >
          <h2 className={styles.planHeading}>Monthly</h2>
          <p className={styles.planPrice}>£5 / month</p>
          <p className={styles.planDescription}>Flexible monthly billing.</p>
        </button>

        <button
          type="button"
          onClick={() => setSelectedPlan("annual")}
          className={`${styles.planCard} ${annualActive ? styles.planCardActive : ""}`}
        >
          <h2 className={styles.planHeading}>Annual</h2>
          <p className={styles.planPrice}>£50 / year</p>
          <p className={styles.planDescription}>
            Save 17% compared with monthly.
          </p>
        </button>
      </div>

      <p className={styles.selectedPlanSummary}>
        {selectedPlan === "monthly"
          ? "You selected Monthly: £5 billed every month."
          : "You selected Annual: £50 billed yearly (17% discount)."}
      </p>

      <Button onClick={handleCheckout} disabled={loading}>
        {loading ? "Redirecting..." : checkoutButtonLabel}
      </Button>
      {error ? <p className={styles.error}>{error}</p> : null}
    </div>
  );
}
