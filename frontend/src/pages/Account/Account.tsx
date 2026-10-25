import React, { useState } from "react";

import Achievements from "../../components/Achievements/Achievements";
import Button from "../../components/Button/Button";
import * as Tabs from "../../components/Tabs/Tabs";
import TimezoneSelect from "../../components/TimezoneSelect/TimezoneSelect";
import {
  PLAYER_NAME_MAX_LENGTH,
} from "../../utils/playerNameValidation";
import { useAccountPage } from "./useAccountPage";
import { usePreferencesTab } from "./usePreferencesTab";
import { useTimezonePreference } from "./useTimezonePreference";
import styles from "./Account.module.scss";

export default function Account(): React.ReactElement {
  const {
    player,
    billingPortalUrl,
    currentXp,
    nextLevelXp,
    totalHours,
    totalMinutes,
    achievements,
    nameDisplay,
    isTrialing,
    trialDaysRemaining,
    isEditingName,
    draftName,
    nameError,
    nameValidation,
    updateNameMutation,
    isSaveDisabled,
    handleStartEditingName,
    handleCancelEditingName,
    handleDraftNameChange,
    handleSaveName,
    downloadUserDataMutation,
    handleDownloadData,
    showDeleteConfirm,
    deleteConfirmText,
    deleteAccountMutation,
    openDeleteConfirm,
    closeDeleteConfirm,
    handleDeleteConfirmTextChange,
    handleDeleteAccount,
  } = useAccountPage();

  const {
    preferences,
    isLoading: preferencesLoading,
    isError: preferencesError,
    handleToggle,
    pendingKey,
  } = usePreferencesTab();

  const {
    timezones,
    timezonesLoading,
    timezonesError,
    currentTimezone,
    detectedTimezone,
    showDetectedTimezoneHint,
    handleTimezoneChange,
    isUpdating: isUpdatingTimezone,
    updateError: timezoneUpdateError,
  } = useTimezonePreference();

  const [activeTab, setActiveTab] = useState("account");

  return (
    <div className={styles.page}>
      <div className={styles.content}>
        <h1 className="sr-only">Account</h1>

        <Tabs.Root
          className={styles.tabsRoot}
          value={activeTab}
          onValueChange={setActiveTab}
        >
          <Tabs.List className={styles.tabBar} aria-label="Account sections">
            <Tabs.Trigger value="account" className={styles.tab}>
              Account
            </Tabs.Trigger>
            <Tabs.Trigger value="preferences" className={styles.tab}>
              Preferences
            </Tabs.Trigger>
          </Tabs.List>

          <Tabs.Content value="account" className={styles.tabContent}>
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
                        Edit name
                      </Button>
                    </div>
                  ) : (
                    <form className={styles.nameEditor} onSubmit={handleSaveName}>
                      <input
                        type="text"
                        value={draftName}
                        onChange={(event) => handleDraftNameChange(event.target.value)}
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
                  <span className={styles.label}>Player level</span>
                  <span className={styles.value}>{player?.level || 0}</span>
                </div>
                <div className={styles.infoItem}>
                  <span className={styles.label}>Experience points</span>
                  <span className={styles.value}>{currentXp} / {nextLevelXp}</span>
                </div>
                <div className={styles.infoItem}>
                  <span className={styles.label}>Total activities</span>
                  <span className={styles.value}>{player?.total_activities || 0}</span>
                </div>
                <div className={styles.infoItem}>
                  <span className={styles.label}>Total time</span>
                  <span className={styles.value}>
                    {`${totalHours}h ${totalMinutes}m`}
                  </span>
                </div>
              </div>
            </section>

            <Achievements achievements={achievements} />

            <section className={styles.section}>
              <h2>Billing</h2>
              <div className={styles.billingRow}>
                <div className={styles.infoItem}>
                  <span className={styles.label}>Account type</span>
                  {player?.is_premium ? (
                    <span className={styles.premiumBadge}>Premium</span>
                  ) : (
                    <span className={styles.value}>Free</span>
                  )}
                  {isTrialing && (
                    <p className={styles.description}>
                      Free trial &mdash; {trialDaysRemaining}{" "}
                      {trialDaysRemaining === 1 ? "day" : "days"} remaining
                    </p>
                  )}
                </div>
                <div className={styles.billingAction}>
                  {player?.is_premium ? (
                    <>
                      <p className={styles.description}>
                        Manage your subscription and billing details in the Stripe customer portal.
                      </p>
                      <Button
                        as="a"
                        href={billingPortalUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        variant="secondary"
                        disabled={!billingPortalUrl}
                      >
                        Open billing portal
                      </Button>
                    </>
                  ) : (
                    <>
                      <p className={styles.description}>
                        Ready for more focus tools and rewards?
                      </p>
                      <Button as="a" href="/upgrade">
                        Upgrade
                      </Button>
                    </>
                  )}
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
                    <span className={styles.value}>{character.name}</span>
                  </div>
                  <div className={styles.infoItem}>
                    <span className={styles.label}>Level</span>
                    <span className={styles.value}>{character.level || 0}</span>
                  </div>
                  <div className={styles.infoItem}>
                    <span className={styles.label}>Total activities</span>
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
                  onClick={openDeleteConfirm}
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
                    onChange={(e) => handleDeleteConfirmTextChange(e.target.value)}
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
                      onClick={closeDeleteConfirm}
                      variant="secondary"
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              )}
            </section>
          </Tabs.Content>

          <Tabs.Content value="preferences" className={styles.tabContent}>
            <section className={styles.section}>
              <h2>Timezone</h2>
              <p className={styles.description}>
                Used to work out when your day rolls over.
              </p>
              {timezonesLoading && (
                <p className={styles.description}>Loading timezones...</p>
              )}
              {timezonesError && (
                <p className={styles.fieldError} role="alert">
                  Couldn't load the timezone list. Please try again later.
                </p>
              )}
              {!timezonesLoading && !timezonesError && (
                <div className={styles.infoItem}>
                  <label className={styles.label} htmlFor="account-timezone">
                    Timezone
                  </label>
                  <TimezoneSelect
                    id="account-timezone"
                    options={timezones}
                    value={currentTimezone}
                    onChange={handleTimezoneChange}
                    disabled={isUpdatingTimezone}
                    ariaLabel="Timezone"
                  />
                  {showDetectedTimezoneHint && detectedTimezone && (
                    <Button
                      variant="secondary"
                      className={styles.inlineButton}
                      disabled={isUpdatingTimezone}
                      onClick={() => handleTimezoneChange(detectedTimezone)}
                    >
                      Use detected timezone ({detectedTimezone})
                    </Button>
                  )}
                  {timezoneUpdateError && (
                    <p className={styles.fieldError} role="alert">
                      Couldn't update your timezone. Please try again.
                    </p>
                  )}
                </div>
              )}
            </section>

            <section className={styles.section}>
              <h2>Notifications</h2>
              {preferencesLoading && (
                <p className={styles.description}>Loading preferences...</p>
              )}
              {preferencesError && (
                <p className={styles.fieldError} role="alert">
                  Couldn't load preferences. Please try again later.
                </p>
              )}
              {!preferencesLoading && !preferencesError && (
                <div className={styles.preferenceList}>
                  {preferences.map((preference) => (
                    <label key={preference.key} className={styles.preferenceItem}>
                      <span className={styles.preferenceText}>
                        <span className={styles.preferenceName}>
                          {preference.verbose_name}
                        </span>
                        <span className={styles.preferenceHelp}>
                          {preference.help_text}
                        </span>
                      </span>
                      <span className={styles.switch}>
                        <input
                          type="checkbox"
                          role="switch"
                          checked={preference.value}
                          disabled={pendingKey === preference.key}
                          onChange={(event) =>
                            handleToggle(preference.key, event.target.checked)
                          }
                          className={styles.switchInput}
                        />
                        <span className={styles.switchTrack} aria-hidden="true" />
                      </span>
                    </label>
                  ))}
                </div>
              )}
            </section>
          </Tabs.Content>
        </Tabs.Root>
      </div>
    </div>
  );
}
