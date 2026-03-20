import React from "react";
import { Link } from "react-router-dom";

export default function SuccessPage() {
  return (
    <div style={{ maxWidth: "720px", margin: "0 auto", padding: "2rem" }}>
      <h1>Payment Successful</h1>
      <p>Thank you for upgrading. Your subscription is being activated.</p>
      <Link to="/account">Go to account</Link>
    </div>
  );
}
