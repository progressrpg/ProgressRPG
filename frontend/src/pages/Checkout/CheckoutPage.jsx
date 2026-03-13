import React, { useState } from "react";

import Button from "../../components/Button/Button";
import { apiFetch } from "../../../utils/api";

export default function CheckoutPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleCheckout = async () => {
    setLoading(true);
    setError("");

    try {
      const data = await apiFetch("/payments/create-checkout-session/", {
        method: "POST",
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

  return (
    <div style={{ maxWidth: "720px", margin: "0 auto", padding: "2rem" }}>
      <h1>Upgrade to Premium</h1>
      <p>Unlock premium features and support ProgressRPG development.</p>
      <Button onClick={handleCheckout} disabled={loading}>
        {loading ? "Redirecting..." : "Go to Checkout"}
      </Button>
      {error ? <p style={{ marginTop: "1rem", color: "#c0392b" }}>{error}</p> : null}
    </div>
  );
}
