import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { API_BASE_URL } from "../config";

const API_URL = `${API_BASE_URL}/api/v1`;

export default function ConfirmationPage() {
  const { key } = useParams();
  const navigate = useNavigate();
  const { login } = useAuth();

  const [status, setStatus] = useState("loading"); // loading | success | error
  const [message, setMessage] = useState("");

  useEffect(() => {
    async function confirmEmail() {
      if (!key) {
        setStatus("error");
        setMessage("Invalid confirmation link.");
        return;
      }

      const confirmedKey = sessionStorage.getItem("confirmedKey");
      if (confirmedKey === key) {
        setStatus("success");
        setMessage("Email already confirmed! Redirecting...");
        setTimeout(() => navigate("/onboarding"), 2000);
        return;
      }

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
  }, [key, navigate, login]);

  return (
    <div>
      {status === "loading" && <p>Just a moment...</p>}
      {status === "success" && <p style={{ color: "green" }}>{message}</p>}
      {status === "error" && <p style={{ color: "red" }}>{message}</p>}
    </div>
  );
}
