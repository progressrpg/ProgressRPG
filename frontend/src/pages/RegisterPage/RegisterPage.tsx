import React, { useCallback, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import Form from '../../components/Form/Form';
import Input from '../../components/Input/Input';
import Turnstile from '../../components/Turnstile/Turnstile';
import WaitlistForm from '../../components/WaitlistForm/WaitlistForm';
import useRegister from '../../hooks/useRegister';
import { useRegistrationStatus } from '../../hooks/useRegistrationStatus';
import styles from './RegisterPage.module.scss';

// The site key comes from the backend (see /registration_status/) so rotating
// it or turning Turnstile on doesn't need a frontend rebuild. The build-time
// env var stays supported as a local override.
function resolveTurnstileSiteKey(apiSiteKey?: string): string | undefined {
  return apiSiteKey || (import.meta.env.VITE_TURNSTILE_SITE_KEY as string | undefined) || undefined;
}

function RegistrationForm({
  inviteToken,
  selfServe,
  turnstileSiteKey,
}: {
  inviteToken?: string;
  selfServe?: boolean;
  turnstileSiteKey?: string;
}): React.ReactElement {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState<Record<string, string[]>>({});
  const [turnstileToken, setTurnstileToken] = useState('');
  const navigate = useNavigate();
  const { register, characterAvailable } = useRegister();
  const [inviteCode, setInviteCode] = useState('');
  const [agreeToTerms, setAgreeToTerms] = useState(false);
  const [formState, setFormState] = useState<'default' | 'submitted'>('default');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleTurnstileToken = useCallback((token: string) => {
    setTurnstileToken(token);
  }, []);

  const handleRegister = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError('');
    setFieldErrors({});
    const browserTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

    if (password !== confirmPassword) {
      setError("Passwords don't match");
      return;
    }

    if (!agreeToTerms) {
      setError('Please agree to the Terms of Service and Privacy Policy.');
      return;
    }

    // Without a site key there is no widget to complete, so don't gate on a
    // token the user has no way of producing (the backend still verifies).
    if (turnstileSiteKey && !turnstileToken) {
      setError('Please complete the security check.');
      return;
    }

    setIsSubmitting(true);
    const result = await register(
      email,
      password,
      confirmPassword,
      inviteToken ? { token: inviteToken } : { code: inviteCode },
      agreeToTerms,
      turnstileToken,
      browserTimezone
    );
    setIsSubmitting(false);

    if (result.success) {
      setEmail('');
      setPassword('');
      setConfirmPassword('');
      setInviteCode('');
      setAgreeToTerms(false);

      if (result.confirmationRequired) {
        setFormState('submitted');
      } else {
        navigate('/game');
      }
    } else {
      setError(result.errorMessage);
      setFieldErrors((result.errors as Record<string, string[]>) || {});
    }
  };

  if (formState === 'submitted') {
    return (
      <div>
        <p>
          Thanks for registering! Please check your email and follow the confirmation link
          before logging in.
        </p>
        {!characterAvailable && (
          <p>
            We don&apos;t currently have any characters available for you to link with! Please
            still confirm your email, and we will let you know as soon as a character becomes
            available.
          </p>
        )}
      </div>
    );
  }

  return (
    <div>
      <Form
        title="📝 Register"
        onSubmit={handleRegister}
        submitLabel="Create Account"
        isSubmitting={isSubmitting}
        fieldErrors={fieldErrors}
      >
        <Input
          id="email"
          label="Email:"
          type="email"
          placeholder="Email"
          autoComplete="email"
          value={email}
          onChange={(v) => setEmail(v as string)}
          required
        />
        <Input
          id="password"
          label="Password:"
          type="password"
          placeholder="Password"
          autoComplete="new-password"
          value={password}
          onChange={(v) => setPassword(v as string)}
          required
        />
        <Input
          id="confirmPassword"
          label="Confirm password:"
          type="password"
          placeholder="Confirm Password"
          autoComplete="new-password"
          value={confirmPassword}
          onChange={(v) => setConfirmPassword(v as string)}
          required
        />
        {!inviteToken && (
          <Input
            id="invite_code"
            label={selfServe ? 'Invite Code (optional):' : 'Invite Code:'}
            type="text"
            placeholder="e.g. TESTER"
            value={inviteCode}
            onChange={(v) => setInviteCode(v as string)}
            required={!selfServe}
          />
        )}
        <div className={styles.agreeToTerms}>
          <input
            id="agree_to_terms"
            type="checkbox"
            checked={agreeToTerms}
            onChange={(e) => setAgreeToTerms(e.target.checked)}
            required
            aria-invalid={!!error && !agreeToTerms}
          />
          <label htmlFor="agree_to_terms">
            I agree to the{' '}
            <a href="https://progressrpg.com/terms-of-service/" target="_blank" rel="noopener noreferrer">
              Terms of Service
            </a>{' '}
            and{' '}
            <a href="https://progressrpg.com/privacy-policy-2/" target="_blank" rel="noopener noreferrer">
              Privacy Policy
            </a>
            .
          </label>
        </div>
        {turnstileSiteKey && (
          <Turnstile sitekey={turnstileSiteKey} onToken={handleTurnstileToken} />
        )}
      </Form>
      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

export default function RegisterPage(): React.ReactElement {
  const { data, isLoading } = useRegistrationStatus();
  const location = useLocation();
  const { token: inviteToken } = useParams<{ token?: string }>();

  if (isLoading) {
    return (
      <div className={styles.page}>
        <div className={styles.formFrame}>
          <p>Loading…</p>
        </div>
      </div>
    );
  }

  // The kill switch is an emergency stop and applies unconditionally, even to
  // invited users — unlike the cap check below, which they bypass.
  if (data && !data.registration_enabled) {
    return (
      <div className={styles.page}>
        <div className={styles.formFrame}>
          <h1 className={styles.title}>Registration is currently unavailable</h1>
          <div className={styles.content}>
            <p>We&apos;ve temporarily paused new registrations. Please check back later.</p>
            <p className={styles.footer}>
              Already have an account? <a href="/login">Log in here</a>.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Invited users always get the registration form, even if the cap has
  // since been reached again, or self-serve is off — their invite is proof
  // of a slot at invite time.
  if (!inviteToken && data && (!data.registration_open || !data.self_serve_registration)) {
    const title = !data.registration_open
      ? 'Registration is temporarily full'
      : 'Registration is by invite only';
    const body = !data.registration_open
      ? "We've reached our current capacity for new players. Join the waitlist and we'll be in touch."
      : "We're inviting new players from the waitlist. Join the waitlist and we'll be in touch.";
    return (
      <div className={styles.page}>
        <div className={styles.formFrame}>
          <h1 className={styles.title}>{title}</h1>
          <div className={styles.content}>
            <p>{body}</p>
            <WaitlistForm />
            <p className={styles.footer}>
              Already have an account? <a href="/login">Log in here</a>.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <div className={styles.formFrame}>
        <RegistrationForm
          key={location.key}
          inviteToken={inviteToken}
          selfServe={data?.self_serve_registration}
          turnstileSiteKey={resolveTurnstileSiteKey(data?.turnstile_site_key)}
        />
      </div>
    </div>
  );
}
