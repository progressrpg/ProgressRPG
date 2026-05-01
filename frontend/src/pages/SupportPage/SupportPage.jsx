import styles from "../LegalPage/LegalPage.module.scss";

const supportEmail = "support@progressrpg.com";

export default function SupportPage() {
  return (
    <main className={styles.page}>
      <article className={styles.card}>
        <header className={styles.header}>
          <h1 className={styles.title}>Support</h1>
          <p className={styles.lead}>
            Need help with ProgressRPG? We are here to help.
          </p>
        </header>

        <div className={styles.content}>
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Contact</h2>
            <p>
              Email us at <a className={styles.contactLink} href={`mailto:${supportEmail}`}>{supportEmail}</a>.
            </p>
            <p>
              We aim to respond within 2 business days.
            </p>
          </section>

          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Billing Support</h2>
            <p>
              For subscription or payment questions, include the email address used on your account
              so we can assist you quickly.
            </p>
          </section>
        </div>
      </article>
    </main>
  );
}
