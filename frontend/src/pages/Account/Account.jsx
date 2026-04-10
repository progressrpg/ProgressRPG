import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useGame } from "../../context/GameContext";
import { useMutation } from "@tanstack/react-query";
import { downloadUserData, deleteAccount } from "../../api/player";
import Button from "../../components/Button/Button";
import styles from "./Account.module.scss";

export default function Account() {
  const { player, character, loading } = useGame();
  const navigate = useNavigate();
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState("");

  const downloadUserDataMutation = useMutation({
    mutationFn: downloadUserData,
  });

  const deleteAccountMutation = useMutation({
    mutationFn: deleteAccount,
    onSuccess: () => {
      localStorage.clear();
      sessionStorage.clear();
      navigate("/");
    },
  });

  const currentXp = player?.xp ?? 0;
  const nextLevelXp = player?.xp_next_level ?? 0;
  const totalTimeSeconds = player?.total_time ?? 0;
  const totalHours = Math.floor(totalTimeSeconds / 3600);
  const totalMinutes = Math.floor((totalTimeSeconds % 3600) / 60);
  const usernameDisplay = loading
    ? "Loading..."
    : (player?.name?.trim() || "Unnamed player");

  const handleDownloadData = () => {
    downloadUserDataMutation.mutate();
  };

  const handleDeleteAccount = () => {
    if (deleteConfirmText === "DELETE") {
      deleteAccountMutation.mutate();
    }
  };

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1>Account</h1>
      </div>

      <div className={styles.content}>
        {/* Player Information */}
        <section className={styles.section}>
          <h2>Player</h2>
          <div className={styles.infoGrid}>
            <div className={`${styles.infoItem} ${styles.usernameItem}`}>
              <span className={styles.label}>Username</span>
              <div className={styles.usernameRow}>
                <span className={styles.value}>{usernameDisplay}</span>
                <Link to="/edit-account" className={styles.inlineButtonLink}>
                  <Button variant="secondary" className={styles.inlineButton}>
                    Edit Username
                  </Button>
                </Link>
              </div>
            </div>
            <div className={styles.infoItem}>
              <span className={styles.label}>Level</span>
              <span className={styles.value}>{player?.level || 0}</span>
            </div>
            <div className={styles.infoItem}>
              <span className={styles.label}>Experience points</span>
              <span className={styles.value}>{currentXp} / {nextLevelXp}</span>
            </div>
            <div className={styles.infoItem}>
              <span className={styles.label}>Total Activities</span>
              <span className={styles.value}>{player?.total_activities || 0}</span>
            </div>
            <div className={styles.infoItem}>
              <span className={styles.label}>Total Time</span>
              <span className={styles.value}>
                {`${totalHours}h ${totalMinutes}m`}
              </span>
            </div>
            <div className={styles.infoItem}>
              <span className={styles.label}>Premium</span>
              <span className={styles.value}>
                {player?.is_premium ? "Yes" : "No"}
              </span>
            </div>
          </div>
        </section>

        {/* Character Information */}
        {/* {character && (
          <section className={styles.section}>
            <h2>Character</h2>
            <div className={styles.infoGrid}>
              <div className={styles.infoItem}>
                <span className={styles.label}>Name</span>
                <span className={styles.value}>{character.first_name} {character.last_name}</span>
              </div>
              <div className={styles.infoItem}>
                <span className={styles.label}>Level</span>
                <span className={styles.value}>{character.level || 0}</span>
              </div>
              <div className={styles.infoItem}>
                <span className={styles.label}>Total Activities</span>
                <span className={styles.value}>{character.total_activities || 0}</span>
              </div>
            </div>
          </section>
        )} */}

        <section className={styles.section}>
          <h2>Download Your Data</h2>
          <p className={styles.description}>
            Download a copy of all your data including activities, player information, and progress.
          </p>
          <Button
            onClick={handleDownloadData}
            variant="secondary"
            disabled={downloadUserDataMutation.isPending}
          >
            {downloadUserDataMutation.isPending ? "Preparing Download..." : "Download My Data"}
          </Button>
        </section>

        <section className={styles.section}>
          <h2>Delete Account</h2>
          <p className={styles.description}>
            Permanently delete your account and all associated data. This action cannot be undone.
          </p>

          {!showDeleteConfirm ? (
            <Button
              onClick={() => setShowDeleteConfirm(true)}
              variant="danger"
            >
              Delete My Account
            </Button>
          ) : (
            <div className={styles.deleteConfirmation}>
              <p className={styles.warningText}>
                ⚠️ This will permanently delete your account and all data. Type "DELETE" to confirm:
              </p>
              <input
                type="text"
                value={deleteConfirmText}
                onChange={(e) => setDeleteConfirmText(e.target.value)}
                className={styles.input}
                placeholder="Type DELETE to confirm"
              />
              <div className={styles.buttonGroup}>
                <Button
                  onClick={handleDeleteAccount}
                  variant="danger"
                  disabled={deleteConfirmText !== "DELETE" || deleteAccountMutation.isPending}
                >
                  {deleteAccountMutation.isPending ? "Deleting..." : "Confirm Delete"}
                </Button>
                <Button
                  onClick={() => {
                    setShowDeleteConfirm(false);
                    setDeleteConfirmText("");
                  }}
                  variant="secondary"
                >
                  Cancel
                </Button>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
