import React from "react";
import { Link } from "react-router-dom";

const SuccessPage = () => {
  return (
    <div style={{ textAlign: "center", padding: "2rem" }}>
      <h1>Payment Successful!</h1>
      <p>Thank you for upgrading to Progress RPG Premium.</p>
      <Link to="/">Go back to Dashboard</Link>
    </div>
  );
};

export default SuccessPage;
