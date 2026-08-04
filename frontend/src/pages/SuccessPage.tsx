import React, { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { apiFetch } from "../utils/api";
import { useGame } from "../hooks/useGame";
import Button from "../components/Button/Button";
import styles from "./SuccessPage.module.scss";

const PERKS = [
  {
    icon: "⚡",
    label: "Double XP",
    description: "Every completed activity earns twice the experience.",
  },
  {
    icon: "∞",
    label: "Unlimited timers",
    description: "No session cap — run as long as you need.",
  },
  {
    icon: "🔭",
    label: "Early access",
    description: "New features reach you first, as they ship.",
  },
  {
    icon: "🌱",
    label: "Supporting the mission",
    description: "You're helping this reach people who need it most.",
  },
];

type SyncStatus = "syncing" | "active" | "trialing" | "error";

export default function SuccessPage(): React.ReactElement {
  const [status, setStatus] = useState<SyncStatus>("syncing");
  const { fetchPlayerAndCharacter } = useGame();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  useEffect(() => {
    if (!searchParams.get("session_id")) {
      navigate("/", { replace: true });
      return;
    }
    apiFetch<{ status: string }>("/payments/sync-subscription/", { method: "POST" })
      .then((data) => {
        const resolved: SyncStatus =
          data.status === "active" || data.status === "trialing"
            ? (data.status as "active" | "trialing")
            : "error";
        if (resolved !== "error") fetchPlayerAndCharacter();
        setStatus(resolved);
      })
      .catch(() => setStatus("error"));
  }, []);

  const isSuccess = status === "active" || status === "trialing";

  return (
    <div className={styles.page}>
      {status === "syncing" && (
        <p className={styles.syncingState}>Confirming your subscription…</p>
      )}

      {isSuccess && (
        <>
          <div className={styles.hero}>
            <div className={styles.heroBadge}>Premium member</div>
            <h1 className={styles.heroHeading}>You're premium.</h1>
            <p className={styles.heroSubheading}>
              Thanks for supporting Progress RPG. Let's get to work.
            </p>
          </div>

          <p className={styles.sectionHeading}>What you've unlocked</p>
          <ul className={styles.perkGrid} role="list">
            {PERKS.map(({ icon, label, description }) => (
              <li key={label} className={styles.perkCard}>
                <span className={styles.perkIcon} aria-hidden="true">
                  {icon}
                </span>
                <div>
                  <p className={styles.perkLabel}>{label}</p>
                  <p className={styles.perkDescription}>{description}</p>
                </div>
              </li>
            ))}
          </ul>

          <div className={styles.ctaRow}>
            <Button variant="primary" onClick={() => navigate("/")}>
              Go to timer
            </Button>
            <Button variant="secondary" onClick={() => navigate("/account")}>
              View your account
            </Button>
          </div>
        </>
      )}

      {status === "error" && (
        <div className={styles.errorSection}>
          <p>
            Your payment was received but we couldn&rsquo;t confirm the
            subscription right away. It will activate automatically &mdash;
            check your account in a few minutes.
          </p>
        </div>
      )}
    </div>
  );
}
