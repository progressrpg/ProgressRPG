import { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import Button from '../../components/Button/Button';
import styles from './Home.module.scss';

const MAILCHIMP_ACTION_URL = import.meta.env.VITE_MAILCHIMP_ACTION_URL || '';
const MAILCHIMP_HONEYPOT_NAME = import.meta.env.VITE_MAILCHIMP_HONEYPOT_NAME || 'b_honeypot';

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
      const iframeName = `mc-submission-frame-${Date.now()}`;

      const iframe = document.createElement('iframe');
      iframe.style.display = 'none';
      iframe.name = iframeName;
      document.body.appendChild(iframe);

      const hiddenForm = document.createElement('form');
      hiddenForm.method = 'POST';
      hiddenForm.action = MAILCHIMP_ACTION_URL;
      hiddenForm.target = iframeName;

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
        if (document.body.contains(iframe)) {
          document.body.removeChild(iframe);
        }
        if (document.body.contains(hiddenForm)) {
          document.body.removeChild(hiddenForm);
        }
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
            for your list (format: b_<listid>_<tagid>). Configure it with
            VITE_MAILCHIMP_HONEYPOT_NAME when needed. */}
        <div style={{ position: 'absolute', left: '-5000px' }} aria-hidden="true">
          <input type="text" name={MAILCHIMP_HONEYPOT_NAME} tabIndex={-1} defaultValue="" readOnly />
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
    title: 'Helps you get started',
    description:
      'Whether it’s chores, admin, or the task you’ve been avoiding for weeks, Progress RPG gives you a gentle structure for taking the first step.',
  },
  {
    icon: '⚡',
    title: 'Build momentum',
    description:
      'Use a task timer, return to your routines, and watch your progress accumulate one session at a time.',
  },
  {
    icon: '🤝',
    title: 'Body doubling, reimagined',
    description:
      'Settle into shared sessions with a low-pressure sense of company that helps you keep going when it’s hard to focus alone.',
  },
  {
    icon: '🎯',
    title: 'Meaningful progress',
    description:
      'The current prototype already layers in quest storylines, experience points, and levels so everyday effort feels rewarding to come back to.',
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
            Turn effort into momentum
          </h1>
          <p className={styles.heroSubheading}>
            Progress RPG helps you take the first step and keep going with a task
            timer, gentle body doubling, and enough gameful progress to make
            everyday effort feel worthwhile.
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
              <strong>Name the next thing</strong>
              <p>Choose the task, chore, or tiny first step you want to tackle right now.</p>
            </div>
          </li>
          <li className={styles.step}>
            <span className={styles.stepNumber}>2</span>
            <div>
              <strong>Start a timer or shared session</strong>
              <p>Use the prototype’s task timer and body-doubling features to settle in and keep moving.</p>
            </div>
          </li>
          <li className={styles.step}>
            <span className={styles.stepNumber}>3</span>
            <div>
              <strong>Come back with more momentum</strong>
              <p>Your effort is recorded, your progress grows, and tomorrow feels easier to begin.</p>
            </div>
          </li>
        </ol>
      </section>

      <section className={styles.storySection} aria-labelledby="story-heading">
        <div className={styles.storyBox}>
          <h2 id="story-heading" className={styles.storyHeading}>
            Built to make getting things done feel better
          </h2>
          <p className={styles.storyLead}>
            What started as a small idea has grown into a project built with care,
            creativity, and a love of storytelling.
          </p>
          <p className={styles.storyText}>
            The goal is simple: make getting things done feel fun, shared, and
            rewarding — especially if starting or finishing tasks feels hard.
          </p>
          <p className={styles.storyText}>
            Today’s prototype already includes a task timer, body doubling, quest
            storylines, experience points, and levels, with more to come as the
            project grows.
          </p>
        </div>
      </section>

      {/* Signup / Waitlist */}
      <section className={styles.signupSection} aria-labelledby="signup-heading">
        <div className={styles.signupBox}>
          <h2 id="signup-heading" className={styles.signupHeading}>
            Join the waiting list
          </h2>
          <p className={styles.signupBody}>
            Sign up for the waiting list and newsletter for updates on early access,
            new features, and the next steps for Progress RPG.
          </p>
          <MailchimpSignupForm />
          <p className={styles.signupNote}>
            Want to try the prototype now?{' '}
            <Link to="/login">Log in</Link>
            {' · '}
            <Link to="/register">Create an account</Link>
          </p>
        </div>
      </section>
    </div>
  );
}
