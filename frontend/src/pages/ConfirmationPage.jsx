import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useAuth } from "../context/useAuth";
import { API_BASE_URL } from "../config";

const API_URL = `${API_BASE_URL}/api/v1`;

export default function ConfirmationPage() {
  const { key } = useParams();
  const navigate = useNavigate();
  const { login } = useAuth();
  const alreadyConfirmed = Boolean(key) && sessionStorage.getItem("confirmedKey") === key;

  const [status, setStatus] = useState(() => {
    if (!key) {
      return "error";
    }

    return alreadyConfirmed ? "success" : "loading";
  }); // loading | success | error
  const [message, setMessage] = useState(() => {
    if (!key) {
      return "Invalid confirmation link.";
    }

    return alreadyConfirmed ? "Email already confirmed! Redirecting..." : "";
  });

  useEffect(() => {
    if (!key) {
      return;
    }

    if (alreadyConfirmed) {
      setTimeout(() => navigate("/onboarding"), 2000);
      return;
    }
    async function confirmEmail() {
      try {
        const res = await fetch(`${API_URL}/auth/confirm_email/${encodeURIComponent(key)}/`);
        const data = await res.json();

        if (res.ok) {
          setStatus("success");
          setMessage("Email confirmed! Logging you in...");

          // Auto-login
          if (data.access && data.refresh && login) {
            await login(data.access, data.refresh);
          }

          sessionStorage.setItem("confirmedKey", key);
          setTimeout(() => navigate("/onboarding"), 2000);
        } else if (res.status === 400 && data?.code === "already_confirmed") {
          // Handle already confirmed message
          setStatus("success");
          setMessage("Email already confirmed! Redirecting...");
          setTimeout(() => navigate("/onboarding"), 2000);


        } else {
          setStatus("error");
          setMessage(data?.message || "Confirmation failed.");
        }
      } catch {
        setStatus("error");
        setMessage("Something went wrong.");
      }
    }

    confirmEmail();
  }, [alreadyConfirmed, key, navigate, login]);

  return (
    <div>
      {status === "loading" && <p>Just a moment...</p>}
      {status === "success" && <p style={{ color: "green" }}>{message}</p>}
      {status === "error" && <p style={{ color: "red" }}>{message}</p>}
    </div>
  );
}
