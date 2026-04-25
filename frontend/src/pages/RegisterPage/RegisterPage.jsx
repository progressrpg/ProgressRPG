import styles from './RegisterPage.module.scss';

// Temporary: self-serve registration is paused while concierge onboarding is in use.
// Replace this file with the original registration form once transactional emails are working.
export default function RegisterPage() {
  return (
    <div className={styles.page}>
      <div className={styles.formFrame}>
        <h1 className={styles.title}>📝 Join the Waiting List</h1>
        <div className={styles.content}>
          <p>
            We are currently onboarding new players via our waiting list rather than
            through self-serve registration.
          </p>
          <p>
            <a href="https://progressrpg.com/#signup" target="_blank" rel="noopener noreferrer">
              Sign up for early access at progressrpg.com
            </a>
          </p>
          <p className={styles.footer}>
            Already have an account?{' '}
            <a href="/login">Log in here</a>.
          </p>
        </div>
      </div>
    </div>
  );
}
