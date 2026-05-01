import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useGame } from "../../context/GameContext";
import { useMutation } from "@tanstack/react-query";
import { updatePlayer, downloadUserData, deleteAccount } from "../../api/player";
import Button from "../../components/Button/Button";
import {
  PLAYER_NAME_MAX_LENGTH,
  getPlayerNameErrorMessage,
  getPlayerNameValidation,
} from "../../utils/playerNameValidation";
import styles from "./Account.module.scss";

export default function Account() {
  const { player, loading, fetchPlayerAndCharacter } = useGame();
  const navigate = useNavigate();
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState("");
  const [isEditingName, setIsEditingName] = useState(false);
  const [draftName, setDraftName] = useState("");
  const [nameError, setNameError] = useState("");

  const nameValidation = useMemo(
    () => getPlayerNameValidation(draftName),
    [draftName]
  );

  const downloadUserDataMutation = useMutation({
    mutationFn: downloadUserData,
  });

  const updateNameMutation = useMutation({
    mutationFn: updatePlayer,
    onSuccess: async () => {
      setNameError("");
      setIsEditingName(false);
      await fetchPlayerAndCharacter();
    },
    onError: (error) => {
      setNameError(getPlayerNameErrorMessage(error));
    },
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
  const nameDisplay = loading
    ? "Loading..."
    : (player?.name?.trim() || "Unnamed player");
  const currentPlayerName = player?.name?.trim() || "";
  const accountType = player?.is_premium ? "Premium" : "Free";
  const isSaveDisabled = (
    updateNameMutation.isPending
    || !nameValidation.isValid
    || nameValidation.normalized === currentPlayerName
  );

  const handleDownloadData = () => {
    downloadUserDataMutation.mutate();
  };

  const handleDeleteAccount = () => {
    if (deleteConfirmText === "DELETE") {
      deleteAccountMutation.mutate();
    }
  };

  const handleStartEditingName = () => {
    setDraftName(currentPlayerName);
    setNameError("");
    setIsEditingName(true);
  };

  const handleCancelEditingName = () => {
    setDraftName(currentPlayerName);
    setNameError("");
    setIsEditingName(false);
  };

  const handleSaveName = (event) => {
    event.preventDefault();
    if (isSaveDisabled) {
      return;
    }

    updateNameMutation.mutate({ name: nameValidation.normalized });
  };

  return (
    <div className={styles.page}>
      <div className={styles.content}>
        {/* Player Information */}
        <section className={styles.section}>
          <h2>Player</h2>
          <div className={styles.infoGrid}>
            <div className={`${styles.infoItem} ${styles.nameItem}`}>
              <span className={styles.label}>Name</span>
              {!isEditingName ? (
                <div className={styles.nameRow}>
                  <span className={styles.value}>{nameDisplay}</span>
                  <Button
                    variant="secondary"
                    className={styles.inlineButton}
                    onClick={handleStartEditingName}
                  >
                    Edit Name
                  </Button>
                </div>
              ) : (
                <form className={styles.nameEditor} onSubmit={handleSaveName}>
                  <input
                    type="text"
                    value={draftName}
                    onChange={(event) => {
                      setDraftName(event.target.value);
                      if (nameError) {
                        setNameError("");
                      }
                    }}
                    className={styles.input}
                    placeholder="Enter your name"
                    maxLength={PLAYER_NAME_MAX_LENGTH}
                    autoFocus
                  />
                  <ul className={styles.rulesList}>
                    {nameValidation.rules.map((rule) => (
                      <li
                        key={rule.id}
                        className={
                          rule.valid ? styles.ruleValid : styles.ruleInvalid
                        }
                      >
                        {rule.label}
                      </li>
                    ))}
                  </ul>
                  {nameError && (
                    <p className={styles.fieldError} role="alert">
                      {nameError}
                    </p>
                  )}
                  <div className={styles.buttonGroup}>
                    <Button type="submit" disabled={isSaveDisabled}>
                      {updateNameMutation.isPending ? "Saving..." : "Save Name"}
                    </Button>
                    <Button
                      variant="secondary"
                      onClick={handleCancelEditingName}
                    >
                      Cancel
                    </Button>
                  </div>
                </form>
              )}
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
          </div>
        </section>

        <section className={styles.section}>
          <h2>Billing</h2>
          <div className={styles.infoGrid}>
            <div className={styles.infoItem}>
              <span className={styles.label}>Account Type</span>
              <span className={styles.value}>{accountType}</span>
            </div>
          </div>
          <p className={styles.description}>
            Manage your subscription and billing details in the Stripe customer portal.
          </p>
          <Button
            as="a"
            href="https://billing.stripe.com/p/login/test_fZucN7dm23whgwNf3N4ow00"
            target="_blank"
            rel="noopener noreferrer"
            variant="secondary"
          >
            Open Billing Portal
          </Button>
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
                This will permanently delete your account and all data. Type "DELETE" to confirm:
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
