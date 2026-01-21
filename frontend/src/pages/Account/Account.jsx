import { Link } from "react-router-dom";
import { useGame } from "../../context/GameContext";
import styles from "./Account.module.scss";

export default function Account() {
  const { player, character } = useGame();

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1>Account</h1>
      </div>

      <div className={styles.content}>
        {/* Quick Actions */}
        <section className={styles.section}>
          <div className={styles.actions}>
            <Link to="/edit-account" className={styles.actionButton}>
              Edit Player
            </Link>
          </div>
        </section>

        {/* Player Information */}
        <section className={styles.section}>
          <h2>Player</h2>
          <div className={styles.infoGrid}>
            <div className={styles.infoItem}>
              <span className={styles.label}>Username</span>
              <span className={styles.value}>{player?.name || "Loading..."}</span>
            </div>
            <div className={styles.infoItem}>
              <span className={styles.label}>Level</span>
              <span className={styles.value}>{player?.level || 0}</span>
            </div>
            <div className={styles.infoItem}>
              <span className={styles.label}>Experience</span>
              <span className={styles.value}>{player?.xp || 0} XP</span>
            </div>
            <div className={styles.infoItem}>
              <span className={styles.label}>Total Activities</span>
              <span className={styles.value}>{player?.total_activities || 0}</span>
            </div>
            <div className={styles.infoItem}>
              <span className={styles.label}>Total Time</span>
              <span className={styles.value}>
                {player?.total_time
                  ? `${Math.floor(player.total_time / 60)}h ${player.total_time % 60}m`
                  : "0h 0m"}
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
        {character && (
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
                <span className={styles.label}>Total Quests</span>
                <span className={styles.value}>{character.total_quests || 0}</span>
              </div>
            </div>
          </section>
        )}

        {/* Account Information */}
        <section className={styles.section}>
          <h2>Account Details</h2>
          {player?.bio && (
            <div className={styles.bioSection}>
              <span className={styles.label}>Bio</span>
              <p className={styles.bio}>{player.bio}</p>
            </div>
          )}
          <div className={styles.infoGrid}>
            <div className={styles.infoItem}>
              <span className={styles.label}>Account ID</span>
              <span className={styles.value}>{player?.id || "—"}</span>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
