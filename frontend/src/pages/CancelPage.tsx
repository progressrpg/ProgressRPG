import React from "react";
import { Link } from "react-router";

export default function CancelPage(): React.ReactElement {
  return (
    <div style={{ maxWidth: "720px", margin: "0 auto", padding: "2rem" }}>
      <h1>Payment Cancelled</h1>
      <p>Your checkout was cancelled. No changes were made.</p>
      <Link to="/upgrade">Try again</Link>
    </div>
  );
}
