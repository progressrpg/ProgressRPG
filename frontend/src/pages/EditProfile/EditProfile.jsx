import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useGame } from "../../context/GameContext";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { updateProfile, downloadUserData, deleteAccount } from "../../api/profile";
import styles from "./EditProfile.module.scss";

export default function EditProfile() {
  const { player } = useGame();
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const [playerName, setPlayerName] = useState("");
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState("");

  const updateProfileMutation = useMutation({
    mutationFn: updateProfile,
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

  // Update profile name when player data loads
  useEffect(() => {
    if (player?.name) {
      setPlayerName(player.name);
    }
  }, [player]);

  const handleUpdateProfile = (e) => {
    e.preventDefault();
    if (playerName.trim() && playerName !== player?.name) {
      updateProfileMutation.mutate({ name: playerName });
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
        <h1>Edit Profile</h1>
        <Link to="/profile" className={styles.backLink}>
          ← Back to Profile
        </Link>
      </div>

      <div className={styles.content}>
        {/* Profile Name Section */}
        <section className={styles.section}>
          <h2>Profile Information</h2>
          <div className={styles.currentInfo}>
            <p className={styles.currentLabel}>Current Username:</p>
            <p className={styles.currentValue}>{player?.name || "Loading..."}</p>
          </div>
          <form onSubmit={handleUpdateProfile} className={styles.form}>
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
              disabled={updateProfileMutation.isPending || playerName === player?.name}
            >
              {updateProfileMutation.isPending ? "Saving..." : "Save Changes"}
            </button>
            {updateProfileMutation.isSuccess && (
              <p className={styles.successMessage}>Profile updated successfully!</p>
            )}
            {updateProfileMutation.isError && (
              <p className={styles.errorMessage}>
                {updateProfileMutation.error?.response?.data?.username?.[0] ||
                 updateProfileMutation.error?.response?.data?.detail ||
                 "Failed to update profile. Username may already be taken."}
              </p>
            )}
          </form>
        </section>

        {/* Download Data Section */}
        <section className={styles.section}>
          <h2>Download Your Data</h2>
          <p className={styles.description}>
            Download a copy of all your data including activities, profile information, and progress.
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
