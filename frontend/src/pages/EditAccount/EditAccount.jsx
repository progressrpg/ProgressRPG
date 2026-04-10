import { Link } from "react-router-dom";
import styles from "./EditAccount.module.scss";

export default function EditAccount() {
  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1>Edit Account</h1>
        <Link to="/account" className={styles.backLink}>
          ← Back to Account
        </Link>
      </div>

      <div className={styles.content}>
        <section className={styles.section}>
          <h2>Coming Soon</h2>
          <p className={styles.stubMessage}>
            This page is temporarily a stub. Username editing and account actions are available from the account page.
          </p>
        </section>
      </div>
    </div>
  );
}
