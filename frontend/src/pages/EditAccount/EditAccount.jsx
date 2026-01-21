import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useGame } from "../../context/GameContext";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { updatePlayer, downloadUserData, deleteAccount } from "../../api/player";
import styles from "./EditAccount.module.scss";

export default function EditAccount() {
  const { player } = useGame();
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const [playerName, setPlayerName] = useState("");
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState("");

  const updatePlayerMutation = useMutation({
    mutationFn: updatePlayer,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["user"] });
    },
  });

  const downloadUserDataMutation = useMutation({
    mutationFn: downloadUserData,
  });

  const deleteAccountMutation = useMutation({
    mutationFn: deleteAccount,
    onSuccess: () => {
      // Clear all cached data
      localStorage.clear();
      sessionStorage.clear();
      // Redirect to home page
      navigate("/");
    },
  });

  // Update player name when player data loads
  useEffect(() => {
    if (player?.name) {
      setPlayerName(player.name);
    }
  }, [player]);

  const handleUpdatePlayer = (e) => {
    e.preventDefault();
    if (playerName.trim() && playerName !== player?.name) {
      updatePlayerMutation.mutate({ name: playerName });
    }
  };

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
        <h1>Edit Player</h1>
        <Link to="/account" className={styles.backLink}>
          ← Back to Account
        </Link>
      </div>

      <div className={styles.content}>
        {/* Player Name Section */}
        <section className={styles.section}>
          <h2>Player Information</h2>
          <div className={styles.currentInfo}>
            <p className={styles.currentLabel}>Current Username:</p>
            <p className={styles.currentValue}>{player?.name || "Loading..."}</p>
          </div>
          <form onSubmit={handleUpdatePlayer} className={styles.form}>
            <div className={styles.formGroup}>
              <label htmlFor="playerName">Change your name</label>
              <input
                type="text"
                id="playerName"
                value={playerName}
                onChange={(e) => setPlayerName(e.target.value)}
                className={styles.input}
                placeholder="Enter your username"
              />
            </div>
            <button
              type="submit"
              className={styles.primaryButton}
              disabled={updatePlayerMutation.isPending || playerName === player?.name}
            >
              {updatePlayerMutation.isPending ? "Saving..." : "Save Changes"}
            </button>
            {updatePlayerMutation.isSuccess && (
              <p className={styles.successMessage}>Info updated successfully!</p>
            )}
            {updatePlayerMutation.isError && (
              <p className={styles.errorMessage}>
                {updatePlayerMutation.error?.response?.data?.username?.[0] ||
                 updatePlayerMutation.error?.response?.data?.detail ||
                 "Failed to update player. Username may already be taken."}
              </p>
            )}
          </form>
        </section>

        {/* Download Data Section */}
        <section className={styles.section}>
          <h2>Download Your Data</h2>
          <p className={styles.description}>
            Download a copy of all your data including activities, player information, and progress.
          </p>
          <button
            onClick={handleDownloadData}
            className={styles.secondaryButton}
            disabled={downloadUserDataMutation.isPending}
          >
            {downloadUserDataMutation.isPending ? "Preparing Download..." : "Download My Data"}
          </button>
        </section>

        {/* Delete Account Section */}
        <section className={styles.section}>
          <h2>Delete Account</h2>
          <p className={styles.description}>
            Permanently delete your account and all associated data. This action cannot be undone.
          </p>

          {!showDeleteConfirm ? (
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className={styles.dangerButton}
            >
              Delete My Account
            </button>
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
                <button
                  onClick={handleDeleteAccount}
                  className={styles.dangerButton}
                  disabled={deleteConfirmText !== "DELETE" || deleteAccountMutation.isPending}
                >
                  {deleteAccountMutation.isPending ? "Deleting..." : "Confirm Delete"}
                </button>
                <button
                  onClick={() => {
                    setShowDeleteConfirm(false);
                    setDeleteConfirmText("");
                  }}
                  className={styles.secondaryButton}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
