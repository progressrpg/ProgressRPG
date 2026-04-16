// Temporary: self-serve registration is paused while concierge onboarding is in use.
// Replace this file with the original registration form once transactional emails are working.
export default function RegisterPage() {
  return (
    <div>
      <h1>📝 Join the Waiting List</h1>
      <p>
        We are currently onboarding new players via our waiting list rather than
        through self-serve registration.
      </p>
      <p>
        <a href="https://progressrpg.com/#signup" target="_blank" rel="noopener noreferrer">
          Sign up for early access at progressrpg.com
        </a>
      </p>
      <p>
        Already have an account?{' '}
        <a href="/login">Log in here</a>.
      </p>
    </div>
  );
}
