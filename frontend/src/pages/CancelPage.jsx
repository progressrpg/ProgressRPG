import React from "react";
import { Link } from "react-router-dom";

const CancelPage = () => {
  return (
    <div style={{ textAlign: "center", padding: "2rem" }}>
      <h1>Payment Cancelled</h1>
      <p>Your payment was not completed. You are still on the free plan.</p>
      <Link to="/checkout">Try Again</Link>
    </div>
  );
};

export default CancelPage;
