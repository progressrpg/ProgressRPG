import { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import Button from '../../components/Button/Button';
import styles from './Home.module.scss';

const MAILCHIMP_ACTION_URL = import.meta.env.VITE_MAILCHIMP_ACTION_URL || '';

// Time (ms) to leave the hidden iframe alive so Mailchimp can finish processing
// the POST before we clean it up from the DOM.
const MAILCHIMP_CLEANUP_DELAY_MS = 3000;

function MailchimpSignupForm() {
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState('idle'); // 'idle' | 'submitting' | 'success' | 'error'
  const [errorMsg, setErrorMsg] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email) return;

    setStatus('submitting');
    setErrorMsg('');

    if (!MAILCHIMP_ACTION_URL) {
      // Graceful degradation when not configured
      setStatus('error');
      setErrorMsg('Signup is temporarily unavailable. Please try again later.');
      return;
    }

    try {
      // Use a hidden iframe to avoid CORS issues with Mailchimp
      const form = e.target;
      const data = new FormData(form);

      const params = new URLSearchParams();
      for (const [key, value] of data.entries()) {
        params.append(key, value);
      }

      // Mailchimp requires a JSONP-style request from the browser.
      // We submit via a temporary form to bypass CORS restrictions.
      const iframe = document.createElement('iframe');
      iframe.style.display = 'none';
      iframe.name = 'mc-submission-frame';
      document.body.appendChild(iframe);

      const hiddenForm = document.createElement('form');
      hiddenForm.method = 'POST';
      hiddenForm.action = MAILCHIMP_ACTION_URL.replace('/post?', '/post-json?') + '&c=__mailchimp_noop__';
      hiddenForm.target = 'mc-submission-frame';

      for (const [key, value] of data.entries()) {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = key;
        input.value = value;
        hiddenForm.appendChild(input);
      }

      document.body.appendChild(hiddenForm);
      hiddenForm.submit();

      setTimeout(() => {
        document.body.removeChild(iframe);
        document.body.removeChild(hiddenForm);
      }, MAILCHIMP_CLEANUP_DELAY_MS);

      setStatus('success');
      setEmail('');
    } catch {
      setStatus('error');
      setErrorMsg('Something went wrong. Please try again.');
    }
  };

  if (status === 'success') {
    return (
      <div className={styles.signupSuccess} role="status" aria-live="polite">
        <p>🎉 You&rsquo;re on the list! We&rsquo;ll be in touch soon.</p>
      </div>
    );
  }

  return (
    <form
      className={styles.signupForm}
      onSubmit={handleSubmit}
      aria-label="Join the waitlist"
      noValidate
    >
      <div className={styles.signupFields}>
        <input
          id="mc-email"
          type="email"
          name="EMAIL"
          className={styles.signupInput}
          placeholder="your@email.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          aria-label="Email address"
          autoComplete="email"
          disabled={status === 'submitting'}
        />
        {/* Honeypot field – name must match the auto-generated Mailchimp bot-field
            for your list (format: b_<listid>_<tagid>). Update this name to
            match the value from your Mailchimp embedded form code. */}
        <div style={{ position: 'absolute', left: '-5000px' }} aria-hidden="true">
          <input type="text" name="b_honeypot" tabIndex={-1} defaultValue="" readOnly />
        </div>
        <Button
          type="submit"
          variant="primary"
          disabled={status === 'submitting'}
          ariaLabel={status === 'submitting' ? 'Submitting your email' : 'Join the waitlist'}
        >
          {status === 'submitting' ? 'Joining…' : 'Join the waitlist'}
        </Button>
      </div>
      {status === 'error' && (
        <p className={styles.signupError} role="alert">{errorMsg}</p>
      )}
    </form>
  );
}

const features = [
  {
    icon: '✅',
    title: 'Stay on task',
    description:
      'Log what you\'re working on and keep a steady rhythm. Progress RPG turns your real-world effort into in-game momentum.',
  },
  {
    icon: '⚡',
    title: 'Build momentum',
    description:
      'Every session counts. Track streaks, watch your progress accumulate, and feel the satisfaction of consistent effort.',
  },
  {
    icon: '🤝',
    title: 'Body-doubling, reimagined',
    description:
      'Work alongside in-game companions who progress at the same time you do — a gentle, low-pressure presence to keep you moving.',
  },
  {
    icon: '🎯',
    title: 'Meaningful progress',
    description:
      'Your activities translate into real skill growth in-game. The more you do the things you care about, the further you go.',
  },
];

export default function Home() {
  const { isAuthenticated, loading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!loading && isAuthenticated) {
      navigate('/game', { replace: true });
    }
  }, [isAuthenticated, loading, navigate]);

  if (loading || isAuthenticated) {
    return null;
  }

  return (
    <div className={styles.page}>
      {/* Hero */}
      <section className={styles.hero} aria-labelledby="hero-heading">
        <div className={styles.heroContent}>
          <h1 id="hero-heading" className={styles.heroHeading}>
            Your productivity,<br />levelled up
          </h1>
          <p className={styles.heroSubheading}>
            Progress RPG is an early-access multiplayer game that helps you stay
            focused, build habits, and track real-world effort — one session at a time.
          </p>
          <div className={styles.heroCta}>
            <Link to="/register">
              <Button variant="primary">Create your account</Button>
            </Link>
            <Link to="/login">
              <Button variant="secondary">Log in</Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className={styles.features} aria-labelledby="features-heading">
        <h2 id="features-heading" className={styles.sectionHeading}>
          Why Progress RPG?
        </h2>
        <ul className={styles.featureGrid} role="list">
          {features.map((f) => (
            <li key={f.title} className={styles.featureCard}>
              <span className={styles.featureIcon} aria-hidden="true">{f.icon}</span>
              <h3 className={styles.featureTitle}>{f.title}</h3>
              <p className={styles.featureDescription}>{f.description}</p>
            </li>
          ))}
        </ul>
      </section>

      {/* How it works */}
      <section className={styles.howItWorks} aria-labelledby="how-heading">
        <h2 id="how-heading" className={styles.sectionHeading}>How it works</h2>
        <ol className={styles.stepsList}>
          <li className={styles.step}>
            <span className={styles.stepNumber}>1</span>
            <div>
              <strong>Choose an activity</strong>
              <p>Pick something you want to work on — studying, writing, coding, exercise, anything.</p>
            </div>
          </li>
          <li className={styles.step}>
            <span className={styles.stepNumber}>2</span>
            <div>
              <strong>Start a session</strong>
              <p>Log your time and let the game track your effort as you work.</p>
            </div>
          </li>
          <li className={styles.step}>
            <span className={styles.stepNumber}>3</span>
            <div>
              <strong>Watch yourself grow</strong>
              <p>Real-world effort earns in-game progress. Keep the streak going and see how far you can go.</p>
            </div>
          </li>
        </ol>
      </section>

      {/* Signup / Waitlist */}
      <section className={styles.signupSection} aria-labelledby="signup-heading">
        <div className={styles.signupBox}>
          <h2 id="signup-heading" className={styles.signupHeading}>
            Get early access
          </h2>
          <p className={styles.signupBody}>
            Progress RPG is in early access. Sign up for updates and be among the
            first to play as we roll out new features.
          </p>
          <MailchimpSignupForm />
          <p className={styles.signupNote}>
            Already have an account?{' '}
            <Link to="/login">Log in</Link>
            {' · '}
            <Link to="/register">Register</Link>
          </p>
        </div>
      </section>
    </div>
  );
}
