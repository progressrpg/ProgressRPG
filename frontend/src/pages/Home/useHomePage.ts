import { useCallback, useEffect, useId, useState } from "react";
import { useNavigate } from "react-router";

import { useAuth } from "../../context/AuthContext";
import { trackEvent } from "../../utils/analytics";
import useWaitlistSignup from "../../hooks/useWaitlistSignup";

const DEFAULT_WAITLIST_SUCCESS_MESSAGE = "You're on the list! We'll be in touch soon.";

export type SignupStatus = "idle" | "submitting" | "success" | "error";

function getEmailValidationMessage(value: string): string {
  const trimmedValue = value.trim();

  if (!trimmedValue) {
    return "Enter an email address to join the waitlist.";
  }

  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedValue)) {
    return "Enter a valid email address, like name@example.com.";
  }

  return "";
}

export function useHomePage() {
  const { isAuthenticated, loading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!loading && isAuthenticated) {
      navigate("/timer", { replace: true });
    }
  }, [isAuthenticated, loading, navigate]);

  return {
    shouldRender: !loading && !isAuthenticated,
  };
}

export function useMailchimpSignupForm() {
  const { requestWaitlistSignup } = useWaitlistSignup();

  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<SignupStatus>("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState(DEFAULT_WAITLIST_SUCCESS_MESSAGE);

  const emailInputId = useId();
  const emailHelpId = useId();
  const emailErrorId = useId();

  useEffect(() => {
    if (status === "success") {
      trackEvent("waitlist_signup_submitted", {
        form_name: "mailchimp_waitlist",
        page: "home",
      });
    }
  }, [status]);

  const handleEmailChange = useCallback(
    (nextEmail: string) => {
      setEmail(nextEmail);
      if (status === "error") {
        setStatus("idle");
        setErrorMsg("");
      }
    },
    [status]
  );

  const handleSubmit = useCallback(
    async (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      const validationMessage = getEmailValidationMessage(email);

      if (validationMessage) {
        setStatus("error");
        setErrorMsg(validationMessage);
        return;
      }

      setStatus("submitting");
      setErrorMsg("");
      setSuccessMsg(DEFAULT_WAITLIST_SUCCESS_MESSAGE);

      const result = await requestWaitlistSignup(email.trim());
      if (!result.success) {
        setStatus("error");
        setErrorMsg(result.errorMessage);
        return;
      }

      setStatus("success");
      setSuccessMsg(result.message || DEFAULT_WAITLIST_SUCCESS_MESSAGE);
      setEmail("");
    },
    [email, requestWaitlistSignup]
  );

  const emailDescribedBy = status === "error" ? `${emailHelpId} ${emailErrorId}` : emailHelpId;

  return {
    email,
    status,
    errorMsg,
    successMsg,
    emailInputId,
    emailHelpId,
    emailErrorId,
    emailDescribedBy,
    setEmail: handleEmailChange,
    handleSubmit,
  };
}
