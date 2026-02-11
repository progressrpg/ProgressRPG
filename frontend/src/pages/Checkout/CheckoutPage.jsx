import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { loadStripe } from "@stripe/stripe-js";
import { apiFetch } from "../../../utils/api";
import Button from "../../components/Button/Button";

// const stripePromise = loadStripe(
//     "pk_test_51SzfKmQCFC8LlZgCgE79s5sQMKoKBNWsJdgg8Xg8l3mXH4SzU8o5Pxk0n5guF8OTpykQOWbe7N8kpliZoffVoaxQ00ZiY1nMDO"
// ); // your Stripe publishable key

const CheckoutPage = () => {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleCheckout = async () => {
    setLoading(true);

    try {
      const token = localStorage.getItem('accessToken');
      const data = await apiFetch("/payments/create-checkout-session/", {
        method: "POST",
        credentials: "include", // if using session auth
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
      });
      console.log("Checkout session data:", data);
      window.location.href = data.url;
    } catch (err) {
      console.error(err);
      alert("Failed to create checkout session.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ textAlign: "center", padding: "2rem" }}>
      <h1>Upgrade to Progress RPG Premium</h1>
      <p>Unlock premium features, perks, and more!</p>
      <Button onClick={handleCheckout} disabled={loading}>
        {loading ? "Redirecting..." : "Go to Checkout"}
      </Button>
    </div>
  );
};

export default CheckoutPage;
