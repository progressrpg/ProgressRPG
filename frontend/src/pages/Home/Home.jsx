import { useEffect, useId, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import BackToTopButton from '../../components/BackToTopButton/BackToTopButton';
import Button from '../../components/Button/Button';
import Seo from '../../components/Seo/Seo';
import styles from './Home.module.scss';

const MAILCHIMP_ACTION_URL =
  import.meta.env.VITE_MAILCHIMP_ACTION_URL ||
  'https://progressrpg.us13.list-manage.com/subscribe/post?u=ca98ca16970fc3d18b18a655b&id=4d402738e3&f_id=0050ede1f0';
const MAILCHIMP_HONEYPOT_NAME =
  import.meta.env.VITE_MAILCHIMP_HONEYPOT_NAME ||
  'b_ca98ca16970fc3d18b18a655b_4d402738e3';
const MAILCHIMP_TAGS_VALUE =
  import.meta.env.VITE_MAILCHIMP_TAGS_VALUE || '1560484';
const HOME_URL = 'https://progressrpg.com/';
const HOME_TITLE = 'Progress RPG | ADHD-Friendly Productivity Support Game';
const HOME_DESCRIPTION =
  'Progress RPG is an ADHD-friendly productivity game with task timers, supportive check-ins, and rewarding progress that helps you start and keep going.';
const HOME_STRUCTURED_DATA = {
  '@context': 'https://schema.org',
  '@type': 'SoftwareApplication',
  name: 'Progress RPG',
  applicationCategory: 'ProductivityApplication',
  operatingSystem: 'Web',
  url: HOME_URL,
  description: HOME_DESCRIPTION,
  offers: {
    '@type': 'Offer',
    price: '0',
    priceCurrency: 'GBP',
  },
  creator: {
    '@type': 'Organization',
    name: 'Progress RPG',
    url: HOME_URL,
  },
};
const heroHighlights = [
  'Start with one task instead of trying to organise everything at once.',
  'Use the support flow to choose a task, write the tiniest first step, or reset before you begin.',
  'Watch your effort build into progress you can return to tomorrow.',
];

// Time (ms) to leave the hidden iframe alive so Mailchimp can finish processing
// the POST before we clean it up from the DOM.
const MAILCHIMP_CLEANUP_DELAY_MS = 3000;

function getEmailValidationMessage(value) {
  const trimmedValue = value.trim();

  if (!trimmedValue) {
    return 'Enter an email address to join the waitlist.';
  }

  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedValue)) {
    return 'Enter a valid email address, like name@example.com.';
  }

  return '';
}

function MailchimpSignupForm() {
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState('idle'); // 'idle' | 'submitting' | 'success' | 'error'
  const [errorMsg, setErrorMsg] = useState('');
  const emailInputId = useId();
  const emailHelpId = useId();
  const emailErrorId = useId();

  const handleSubmit = async (e) => {
    e.preventDefault();
    const validationMessage = getEmailValidationMessage(email);

    if (validationMessage) {
      setStatus('error');
      setErrorMsg(validationMessage);
      return;
    }

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
      aria-labelledby="signup-heading"
      noValidate
    >
      <div className={styles.signupFieldGroup}>
        <label className={styles.signupLabel} htmlFor={emailInputId}>
          Email address
        </label>
        <p id={emailHelpId} className={styles.signupHelp}>
          Only your email is required. We will use it for early-access and product updates.
        </p>
      </div>
      <div className={styles.signupFields}>
        <input
          id={emailInputId}
          type="email"
          name="EMAIL"
          className={styles.signupInput}
          placeholder="your@email.com"
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
            if (status === 'error') {
              setStatus('idle');
              setErrorMsg('');
            }
          }}
          required
          aria-describedby={status === 'error' ? `${emailHelpId} ${emailErrorId}` : emailHelpId}
          aria-invalid={status === 'error' ? 'true' : 'false'}
          autoComplete="email"
          inputMode="email"
          disabled={status === 'submitting'}
        />
        <input type="hidden" name="tags" value={MAILCHIMP_TAGS_VALUE} />
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
        <p id={emailErrorId} className={styles.signupError} role="alert">{errorMsg}</p>
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
    title: 'Support when you feel stuck',
    description:
      'Check in with how you are feeling, choose whether you are ready, and get help picking a task or resetting before you start.',
  },
  {
    icon: '🎯',
    title: 'Meaningful progress',
    description:
      'Timers, support steps, storylines, and progression all work together so everyday effort feels rewarding to come back to.',
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
    <main className={styles.page}>
      <Seo
        title={HOME_TITLE}
        description={HOME_DESCRIPTION}
        canonical={HOME_URL}
        robots="index,follow"
        structuredData={HOME_STRUCTURED_DATA}
      />
      <a className={styles.skipLink} href="#signup-heading">
        Skip to waitlist form
      </a>
      {/* Hero */}
      <section className={styles.hero} aria-labelledby="hero-heading">
        <div className={styles.heroContent}>
          <h1 id="hero-heading" className={styles.heroHeading}>
            Turn effort into momentum
          </h1>
          <p className={styles.heroSubheading}>
            Progress RPG helps you take the first step and keep going with a task
            timer, supportive check-ins, and clear next-step prompts that help
            you choose an activity, reset when overwhelmed, and keep everyday
            effort moving forward.
          </p>
          <ul className={styles.heroHighlights} aria-label="Quick summary">
            {heroHighlights.map((highlight) => (
              <li key={highlight} className={styles.heroHighlightItem}>
                {highlight}
              </li>
            ))}
          </ul>
          <nav className={styles.jumpLinks} aria-label="Quick links">
            <a href="#features-heading">Features</a>
            <a href="#how-heading">How it works</a>
            <a href="#story-heading">Story</a>
          </nav>
          <div className={styles.heroSignupBox}>
            <h2 id="signup-heading" className={styles.signupHeading} tabIndex="-1">
              Join the waiting list
            </h2>
            <p className={styles.heroSignupBody}>
              Sign up for the waiting list and newsletter for updates on early
              access, new features, and the next steps for Progress RPG.
            </p>
            <MailchimpSignupForm />
            <p className={styles.heroSignupNote}>
              Already have access? <Link to="/login">Log in</Link>
            </p>
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
        <h2 id="how-heading" className={styles.sectionHeading} tabIndex="-1">How it works</h2>
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
              <strong>Choose support that fits the moment</strong>
              <p>Use the support flow to pick a task, write the tiniest first step, or take a short reset before you begin.</p>
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
          <h2 id="story-heading" className={styles.storyHeading} tabIndex="-1">
            Built to make getting things done feel better
          </h2>
          <p className={styles.storyLead}>
            What started as a small idea has grown over four years into a project
            built with care, creativity, and a love of storytelling.
          </p>
          <p className={styles.storyText}>
            The goal is simple: make getting things done feel fun, shared, and
            rewarding — especially if starting or finishing tasks feels hard.
          </p>
          <p className={styles.storyText}>
            Every task session is meant to help you work, rest, and play without
            guilt or overwhelm, with more support added as the project grows.
          </p>
          <p className={styles.storyText}>
            Progress RPG is a one-person passion project run as a social
            enterprise: profits are reinvested into improving the app or donated
            to charity.
          </p>
        </div>
      </section>
      <BackToTopButton />
    </main>
  );
}
